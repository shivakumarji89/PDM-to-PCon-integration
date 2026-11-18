from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from models.mdb_export_session import MdbExportSession

from services.properties_values_mdb_export_service import PropertiesValuesMdbExportService


def _snapshot_and_classes():
    p1 = SimpleNamespace(
        id="p1",
        values=[
            SimpleNamespace(id="pv1", property_id="p1", value="One", code="A"),
            SimpleNamespace(id="pv2", property_id="p1", value="Two", code="B"),
        ],
    )
    p2 = SimpleNamespace(
        id="p2",
        values=[SimpleNamespace(id="pv3", property_id="p2", value="Three", code="C")],
    )
    a1 = SimpleNamespace(
        id="a1",
        properties=[
            SimpleNamespace(property_id="p1", property_name="Type",
                            values=[SimpleNamespace(value_id="pv1", code="A", value="One")]),
        ],
    )
    a2 = SimpleNamespace(
        id="a2",
        properties=[
            SimpleNamespace(property_id="p2", property_name="Finish",
                            values=[SimpleNamespace(value_id="pv3", code="C", value="Three")]),
        ],
    )
    classes = [
        SimpleNamespace(id="class1", name="Desk_Attribute", properties=a1.properties),
        SimpleNamespace(id="class1", name="Desk_Attribute", properties=a2.properties),
    ]
    snapshot = SimpleNamespace(
        product=SimpleNamespace(category="Desk", range_name="Desk"),
        articles=[
            SimpleNamespace(id="a1", product_id="prod1"),
            SimpleNamespace(id="a2", product_id="prod2"),
        ],
        properties=[p1, p2],
        property_values=[*p1.values, *p2.values],
        options=[],
        option_values=[],
        article_property_value_ids={"a1": ["pv1"], "a2": ["pv3"]},
        product_property_value_ids={},
        product_option_value_ids={},
        product_range={},
        attribute_range={},
        article_sets=[],
        split_classes_by_group=False,
        class_group_basis="range",
    )
    return snapshot, classes


def test_assignment_union_for_one_article_keeps_only_its_related_property():
    snapshot, classes = _snapshot_and_classes()
    result = PropertiesValuesMdbExportService._assignment_union(snapshot, classes, {"a1"})
    assert list(result) == ["Desk_Attribute"]
    assert set(result["Desk_Attribute"]) == {"p1"}


def test_assignment_union_for_multiple_articles_unions_properties():
    snapshot, classes = _snapshot_and_classes()
    result = PropertiesValuesMdbExportService._assignment_union(snapshot, classes, {"a1", "a2"})
    assert list(result) == ["Desk_Attribute"]
    assert set(result["Desk_Attribute"]) == {"p1", "p2"}


def test_assignment_union_does_not_mutate_source_classes():
    snapshot, classes = _snapshot_and_classes()
    before = [
        (cls.name, [assignment.property_id for assignment in cls.properties])
        for cls in classes
    ]
    PropertiesValuesMdbExportService._assignment_union(snapshot, classes, {"a1", "a2"})
    after = [
        (cls.name, [assignment.property_id for assignment in cls.properties])
        for cls in classes
    ]
    assert after == before


class _ExportFakeMdb:
    def __init__(self, data):
        self.data = data
        self.batches = []

    @staticmethod
    def is_available():
        return True

    def read_tables(self, _path, queries):
        return {name: deepcopy(self.data.get(name, [])) for name in queries}

    def execute_batch(self, _path, operations, transaction=False):
        assert transaction is True
        self.batches.append(deepcopy(operations))
        tables = {
            "tCOMd_Property": "properties",
            "tCOMd_PropValue": "values",
        }
        for operation in operations:
            target = self.data.setdefault(tables[operation["table"]], [])
            if operation["op"] == "insert":
                target.extend(deepcopy(operation["rows"]))
        return SimpleNamespace(ok=True, first_error=lambda: None)


def test_export_to_session_inserts_selected_property_and_value_once(tmp_path):
    mdb_path = tmp_path / "properties.mdb"
    mdb_path.touch()
    data = {
        "package": [{"com_PackageID": 10}],
        "classes": [{
            "com_ClassID": 20, "com_ClassName": "Desk_Attribute",
            "com_PackageID": 10,
        }],
        "articles": [{
            "com_ArticleID": 5, "com_ArticleCode": "BASE", "com_PackageID": 10,
        }],
        "properties": [],
        "values": [],
        "texts": [],
        "relobjs": [],
    }
    db = _ExportFakeMdb(data)
    session = MdbExportSession(
        product_key="id:p1",
        mdb_path=str(mdb_path),
        package_id=10,
        article_map={"BASE": {"mdb_id": 5}},
        prototypes={"tCOMd_Property": {"com_StatusInfoID": 3}, "tCOMd_PropValue": {"com_StatusInfoID": 3}},
    )
    sessions = SimpleNamespace(
        product_key=lambda _snapshot: "id:p1",
        record_workflow=lambda current, workflow, counts: current.workflow_status.update({
            workflow: {"status": "exported", "counts": dict(counts)}
        }),
        save=lambda _session: None,
    )
    value = SimpleNamespace(id="pv1", property_id="p1", value="Red", code="R")
    source_property = SimpleNamespace(
        id="p1", name="Colour", code="COL", data_type="C", values=[value],
    )
    assignment = SimpleNamespace(
        property_id="p1", property_name="Colour", values=[
            SimpleNamespace(value_id="pv1", code="R", value="Red"),
        ],
        text_block="Colour", usage="Configuration", type="C", placement=0,
        relation_object="",
    )
    engineering_classes = [SimpleNamespace(
        id="c1", name="Desk_Attribute", properties=[assignment],
    )]
    snapshot = SimpleNamespace(
        product=SimpleNamespace(id="p1", category="Desk", range_name="Desk"),
        articles=[SimpleNamespace(id="a1", product_id="prod1")],
        properties=[source_property],
        property_values=[value],
        options=[], option_values=[],
        article_property_value_ids={"a1": ["pv1"]},
        product_property_value_ids={}, product_option_value_ids={},
        product_range={"prod1": "Desks"}, attribute_range={"p1": ["Desks"]},
        article_sets=[], split_classes_by_group=False, class_group_basis="range",
    )
    xocd = SimpleNamespace(
        base_code_entries=lambda _snapshot: [("a1", "BASE")],
        _value_code_map=lambda _snapshot: {"pv1": "R"},
        _value_lengths=lambda _snapshot: {"p1": 1},
        _prop_ident=lambda name: str(name).replace(" ", "_"),
    )
    context = SimpleNamespace(
        mdb_export_session_service=sessions,
        mdb_service=db,
        xocd_export_service=xocd,
        engineering_class_service=SimpleNamespace(
            get_classes=lambda _snapshot: engineering_classes,
        ),
    )
    service = PropertiesValuesMdbExportService(context)

    first = service.export_to_session(snapshot, session, {"a1"})

    assert first["ok"], first
    assert first["verified"] is True
    assert first["counts"]["properties_inserted"] == 1
    assert first["counts"]["values_inserted"] == 1
    assert data["properties"][0]["com_ClassID"] == 20
    assert data["properties"][0]["com_PropName"] == "Colour"
    assert data["values"][0]["com_PropertyID"] == data["properties"][0]["com_PropertyID"]
    assert data["values"][0]["com_PropValueFrom"] == "R"

    before = deepcopy(data)
    second = service.export_to_session(snapshot, session, {"a1"})

    assert second["ok"], second
    assert second["verified"] is True
    assert second["counts"]["properties_inserted"] == 0
    assert second["counts"]["values_inserted"] == 0
    assert data == before
    assert len(db.batches) == 1
