"""Integration-contract tests for selected-article incremental Class Creation export."""

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from models.mdb_export_session import MdbExportSession
from services.class_creation_mdb_export_service import ClassCreationMdbExportService


class _FakeMdb:
    def __init__(self, data):
        self.data = data
        self.batches = []

    @staticmethod
    def is_available():
        return True

    def read_tables(self, _path, queries):
        return {
            name: deepcopy(self.data.get(name, []))
            for name in queries
        }

    def execute_batch(self, _path, operations, transaction=False):
        assert transaction is True
        self.batches.append(deepcopy(operations))
        table_names = {
            "tCOMd_Class": "classes",
            "tCOMd_ArticleClass": "article_classes",
            "tCOMd_CodeScheme": "schemes",
        }
        primary_keys = {
            "tCOMd_Class": "com_ClassID",
            "tCOMd_ArticleClass": "com_ArticleClassID",
            "tCOMd_CodeScheme": "com_CodeSchemeID",
        }
        for operation in operations:
            table = operation["table"]
            target = self.data.setdefault(table_names[table], [])
            if operation["op"] == "insert":
                target.extend(deepcopy(operation["rows"]))
            else:
                key = primary_keys[table]
                identity = operation["where"][key]
                for row in target:
                    if str(row.get(key)) == str(identity):
                        row.update(operation["set"])
        return SimpleNamespace(ok=True, first_error=lambda: None)


def _fixture(tmp_path):
    mdb_path = tmp_path / "product.mdb"
    mdb_path.touch()
    data = {
        "package": [{"com_PackageID": 10}],
        "classes": [],
        "articles": [
            {"com_ArticleID": 5, "com_ArticleCode": "BASE", "com_PackageID": 10},
        ],
        "article_classes": [],
        "schemes": [{
            "com_CodeSchemeID": 1,
            "com_CodeSchemeName": "BASE",
            "com_CodeSchemeBody": "@,@,@,@",
            "com_PackageID": 10,
        }],
    }
    db = _FakeMdb(data)
    session = MdbExportSession(
        product_key="id:p1",
        mdb_path=str(mdb_path),
        package_id=10,
        article_map={"BASE": {"mdb_id": 5, "source_ids": ["a1", "a2"]}},
        prototypes={
            "tCOMd_Class": {},
            "tCOMd_ArticleClass": {},
            "tCOMd_CodeScheme": {},
        },
    )
    sessions = SimpleNamespace(
        product_key=lambda _snapshot: "id:p1",
        record_workflow=lambda current, workflow, counts: current.workflow_status.update({
            workflow: {"status": "exported", "counts": dict(counts)}
        }),
        save=lambda _session: None,
    )
    xocd = SimpleNamespace(
        base_code_entries=lambda _snapshot: [("a1", "BASE"), ("a2", "BASE")],
        _value_code_map=lambda _snapshot: {},
    )
    classes = [
        SimpleNamespace(
            id="c1", name="Desk_Attribute",
            properties=[SimpleNamespace(property_id="p1")],
        ),
        SimpleNamespace(
            id="c2", name="Desk_Options",
            properties=[SimpleNamespace(property_id="o1")],
        ),
    ]
    snapshot = SimpleNamespace(
        product=SimpleNamespace(id="p1", category="Desk", range_name="Desk"),
        articles=[
            SimpleNamespace(id="a1", product_id="prod1"),
            SimpleNamespace(id="a2", product_id="prod2"),
        ],
        properties=[SimpleNamespace(id="p1", values=[SimpleNamespace(id="pv1")])],
        property_values=[SimpleNamespace(id="pv1", property_id="p1")],
        options=[SimpleNamespace(id="o1", values=[SimpleNamespace(id="ov1")])],
        option_values=[SimpleNamespace(id="ov1", option_id="o1")],
        article_property_value_ids={"a1": ["pv1"], "a2": []},
        product_property_value_ids={},
        product_option_value_ids={"prod1": [], "prod2": ["ov1"]},
        product_range={"prod1": "Desks", "prod2": "Desks"},
        attribute_range={"p1": ["Desks"]},
        article_sets=[],
        split_classes_by_group=False,
        class_group_basis="range",
    )
    ocd_export = SimpleNamespace(
        _code_schemes=lambda _snapshot, _package, _codes, selected_classes, _map, _proto: (
            [{
                "com_CodeSchemeBody": "@,@,@," + ",".join(
                    f"{assignment.property_id}:X"
                    for cls in selected_classes
                    for assignment in cls.properties
                )
            }],
            {},
            {},
        )
    )
    context = SimpleNamespace(
        mdb_export_session_service=sessions,
        mdb_service=db,
        xocd_export_service=xocd,
        engineering_class_service=SimpleNamespace(get_classes=lambda _snapshot: classes),
        ocd_export_service=ocd_export,
    )
    return snapshot, session, context, db, classes


def test_one_selected_article_exports_only_its_class(tmp_path):
    snapshot, session, context, db, source_classes = _fixture(tmp_path)

    result = ClassCreationMdbExportService(context).export_to_session(
        snapshot, session, {"a1"},
    )

    assert result["ok"], result
    assert result["verified"] is True
    assert result["counts"]["classes_inserted"] == 1
    assert result["counts"]["article_classes_inserted"] == 1
    assert [row["com_ClassName"] for row in db.data["classes"]] == ["Desk_Attribute"]
    assert [row["com_ClassID"] for row in db.data["article_classes"]] == [1]
    assert db.data["schemes"][0]["com_CodeSchemeBody"] == "@,@,@,@,p1:X"
    # Export selection and unioning must not mutate the engineering source.
    assert [len(cls.properties) for cls in source_classes] == [1, 1]


def test_multiple_selected_variants_sharing_a_base_union_their_classes_once(tmp_path):
    snapshot, session, context, db, source_classes = _fixture(tmp_path)

    result = ClassCreationMdbExportService(context).export_to_session(
        snapshot, session, {"a1", "a2"},
    )

    assert result["ok"], result
    assert result["verified"] is True
    assert result["counts"]["selected_articles"] == 2
    assert result["counts"]["base_articles"] == 1
    assert result["counts"]["classes_inserted"] == 2
    assert result["counts"]["article_classes_inserted"] == 2
    assert {row["com_ClassName"] for row in db.data["classes"]} == {
        "Desk_Attribute", "Desk_Options",
    }
    assert len({row["com_ArticleID"] for row in db.data["article_classes"]}) == 1
    assert db.data["schemes"][0]["com_CodeSchemeBody"] == "@,@,@,@,p1:X,o1:X"
    assert [len(cls.properties) for cls in source_classes] == [1, 1]


def test_repeated_class_creation_export_does_not_duplicate_rows(tmp_path):
    snapshot, session, context, db, _source_classes = _fixture(tmp_path)
    service = ClassCreationMdbExportService(context)

    first = service.export_to_session(snapshot, session, {"a1", "a2"})
    assert first["ok"], first
    before = deepcopy(db.data)

    second = service.export_to_session(snapshot, session, {"a1", "a2"})

    assert second["ok"], second
    assert second["verified"] is True
    assert second["operations"] == 0
    assert db.data == before
    assert len(db.batches) == 1
