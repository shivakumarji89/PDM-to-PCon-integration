from copy import deepcopy
from types import SimpleNamespace

from services.relation_mdb_export_service import RelationMdbExportService
from services.text_mdb_export_service import TextMdbExportService


def test_relation_export_requires_selected_articles_before_database_access():
    service = RelationMdbExportService(SimpleNamespace())
    result = service.export_to_session(
        SimpleNamespace(product=object()),
        SimpleNamespace(),
        selected_article_ids=set(),
    )
    assert result["ok"] is False
    assert "Select one or more articles" in result["error"]


def test_text_export_requires_selected_articles_before_database_access():
    service = TextMdbExportService(SimpleNamespace())
    result = service.export_to_session(
        SimpleNamespace(product=object()),
        SimpleNamespace(),
        selected_article_ids=set(),
    )
    assert result["ok"] is False
    assert "Select one or more articles" in result["error"]


def test_incremental_export_id_helpers_advance_past_existing_rows():
    rows = [{"com_RelObjID": 2}, {"com_RelObjID": 17}]
    assert RelationMdbExportService._next_id(rows, "com_RelObjID") == 18
    assert TextMdbExportService._next_id(
        [{"com_TextID": 4}, {"com_TextID": 9}], "com_TextID"
    ) == 10



def test_varcond_incremental_export_requires_complete_prefix_groups():
    from types import SimpleNamespace

    from ui.dialogs.varcond_generation_dialog import VarCondGenerationPanel

    panel = SimpleNamespace(
        _maintenance_load_task=None,
        _article_rows=[
            ("ABC100", "Article 1", "a1"),
            ("ABC200", "Article 2", "a2"),
            ("XYZ100", "Article 3", "a3"),
        ],
        _relation_length=SimpleNamespace(value=lambda: 3),
        _maintenance_check=lambda: False,
        _maintenance_service=None,
        _context=SimpleNamespace(xocd_export_service=None),
        _snapshot=object(),
        _exclusions=SimpleNamespace(text=lambda: ""),
        _substitutions=SimpleNamespace(text=lambda: ""),
    )

    try:
        VarCondGenerationPanel.prepare_relation_export(panel, {"a1"})
    except RuntimeError as exc:
        assert "Select every article" in str(exc)
    else:
        raise AssertionError("A partial shared VARCOND group must be rejected.")

    plan = VarCondGenerationPanel.prepare_relation_export(panel, {"a1", "a2"})
    assert [name for name, _rows in plan.groups] == ["PA_ABC"]
    assert {article_id for _code, article_id in plan.groups[0][1]} == {"a1", "a2"}


class _FakeMdb:
    def __init__(self, rows):
        self.rows = rows
        self.operations = []

    @staticmethod
    def is_available():
        return True

    def read_tables(self, _path, queries):
        return {name: [dict(row) for row in self.rows.get(name, [])] for name in queries}

    def execute_batch(self, _path, operations, transaction=False):
        assert transaction is True
        self.operations.extend(operations)
        table_keys = {
            "tCOMd_RelObj": "objects",
            "tCOMd_Relation": "relations",
            "tCOMd_RelObjRel": "links",
            "tCOMd_Article": "articles",
            "tCOMd_Text": "texts",
            "tCOMd_Property": "properties",
            "tCOMd_PropValue": "values",
        }
        primary_keys = {
            "tCOMd_RelObj": "com_RelObjID",
            "tCOMd_Relation": "com_RelationID",
            "tCOMd_RelObjRel": "com_RelObjRelID",
            "tCOMd_Article": "com_ArticleID",
            "tCOMd_Text": "com_TextID",
            "tCOMd_Property": "com_PropertyID",
            "tCOMd_PropValue": "com_ValueID",
        }
        for operation in operations:
            key = table_keys[operation["table"]]
            if operation["op"] == "insert":
                self.rows.setdefault(key, []).extend(dict(row) for row in operation["rows"])
            else:
                identity = operation["where"][primary_keys[operation["table"]]]
                for row in self.rows.setdefault(key, []):
                    if str(row.get(primary_keys[operation["table"]])) == str(identity):
                        row.update(operation["set"])
        return SimpleNamespace(ok=True, first_error=lambda: None)


def _incremental_context(db, session, snapshot):
    class_sessions = SimpleNamespace(
        product_key=lambda _snapshot: session.product_key,
        record_workflow=lambda *_args, **_kwargs: None,
        save=lambda *_args, **_kwargs: None,
    )
    xocd = SimpleNamespace(
        base_code_entries=lambda _snapshot: [("a1", "BASE")],
        _value_code_map=lambda _snapshot: {},
    )
    return SimpleNamespace(
        mdb_export_session_service=class_sessions,
        mdb_service=db,
        xocd_export_service=xocd,
        engineering_class_service=SimpleNamespace(get_classes=lambda _snapshot: []),
        engineering_relation_service=SimpleNamespace(
            ensure_relation_objects=lambda current: current.relation_objects
        ),
        engineering_text_service=SimpleNamespace(
            ensure_text_blocks=lambda current: current.text_blocks
        ),
        product_type_name=lambda _product_id: "",
    )


def _session(path, prototypes):
    from models.mdb_export_session import MdbExportSession

    return MdbExportSession(
        product_key="id:p1",
        mdb_path=str(path),
        package_id=10,
        prototypes=prototypes,
        article_map={"BASE": {"mdb_id": 5}},
    )


def test_relation_export_inserts_only_missing_rows_and_links_selected_article(tmp_path):
    from models.relation_object import RelationObject

    path = tmp_path / "relations.mdb"
    path.touch()
    rows = {
        "package": [{"com_PackageID": 10}],
        "objects": [],
        "relations": [],
        "links": [],
        "articles": [{
            "com_ArticleID": 5, "com_ArticleCode": "BASE",
            "com_RelObjID": None, "com_PackageID": 10,
        }],
        "article_classes": [],
        "classes": [],
        "properties": [],
        "values": [],
        "object_max": [{"max_id": 0}],
        "relation_max": [{"max_id": 0}],
        "link_max": [{"max_id": 0}],
    }
    db = _FakeMdb(rows)
    snapshot = SimpleNamespace(
        product=SimpleNamespace(id="p1"),
        articles=[SimpleNamespace(id="a1")],
        properties=[], options=[], property_values=[], option_values=[],
        article_property_value_ids={}, product_property_value_ids={},
        product_option_value_ids={}, product_range={}, attribute_range={},
        article_sets=[], split_classes_by_group=False, class_group_basis="range",
        relation_objects=[RelationObject(
            name="A_Test", relation_name="AA_Test", type_code="3",
            domain="C", order=100, body="X = 'Y'", article_codes=["BASE"],
        )],
    )
    session = _session(path, {
        "tCOMd_RelObj": {"com_RelObjName": None, "com_PackageID": None},
        "tCOMd_Relation": {
            "com_RelationName": None, "com_RelationBody": None, "com_PackageID": None,
        },
        "tCOMd_RelObjRel": {
            "com_RelObjID": None, "com_RelationID": None,
            "com_RelObjTypeCode": None, "com_RelObjDomainCode": None,
            "com_RelationOrder": None,
        },
    })
    context = _incremental_context(db, session, snapshot)

    result = RelationMdbExportService(context).export_to_session(
        snapshot, session, {"a1"},
    )

    assert result["ok"], result
    assert result["verified"] is True
    assert result["counts"]["relation_objects_inserted"] == 1
    assert result["counts"]["relations_inserted"] == 1
    assert result["counts"]["relation_links_inserted"] == 1
    assert rows["articles"][0]["com_RelObjID"] == 1
    assert len(rows["objects"]) == len(rows["relations"]) == len(rows["links"]) == 1

    before = deepcopy(rows)
    repeated = RelationMdbExportService(context).export_to_session(
        snapshot, session, {"a1"},
    )
    assert repeated["ok"], repeated
    assert repeated["verified"] is True
    assert repeated["counts"]["relation_objects_inserted"] == 0
    assert repeated["counts"]["relations_inserted"] == 0
    assert repeated["counts"]["relation_links_inserted"] == 0
    assert rows == before


def test_text_export_inserts_text_and_links_selected_base_article(tmp_path):
    from models.text_block import TextBlock

    path = tmp_path / "text.mdb"
    path.touch()
    rows = {
        "package": [{"com_PackageID": 10}],
        "texts": [],
        "text_max": [{"max_id": 0}],
        "articles": [{
            "com_ArticleID": 5, "com_ArticleCode": "BASE", "com_PackageID": 10,
            "com_ShortTextID": None, "com_LongTextID": None,
        }],
        "classes": [], "properties": [], "values": [],
    }
    db = _FakeMdb(rows)
    member = SimpleNamespace(
        article_id="a1", short_description="Desk short", long_description="Desk long",
    )
    snapshot = SimpleNamespace(
        product=SimpleNamespace(id="p1"),
        articles=[SimpleNamespace(id="a1", product_id="p1", code="BASE", name="Desk", description="Desk")],
        properties=[], options=[], property_values=[], option_values=[],
        article_property_value_ids={}, product_property_value_ids={},
        product_option_value_ids={}, product_range={}, attribute_range={},
        article_sets=[], split_classes_by_group=False, class_group_basis="range",
        engineering=SimpleNamespace(families=[SimpleNamespace(members=[member])]),
        text_blocks=[
            TextBlock(name="BASE", type_code="artshort", en="Desk short"),
            TextBlock(name="BASE", type_code="artlong", en="Desk long"),
        ],
    )
    session = _session(path, {
        "tCOMd_Text": {
            "com_TextName": None, "com_TextTypeCode": None,
            "com_PackageID": None, "com_Text_1_en": None,
        },
    })
    context = _incremental_context(db, session, snapshot)

    result = TextMdbExportService(context).export_to_session(
        snapshot, session, {"a1"},
    )

    assert result["ok"], result
    assert result["verified"] is True
    assert result["counts"]["texts_inserted"] == 2
    assert rows["articles"][0]["com_ShortTextID"] == 1
    assert rows["articles"][0]["com_LongTextID"] == 2
    assert {row["com_TextName"] for row in rows["texts"]} == {"BASE"}
    assert {row["com_TextTypeCode"] for row in rows["texts"]} == {"artshort", "artlong"}

    before = deepcopy(rows)
    repeated = TextMdbExportService(context).export_to_session(
        snapshot, session, {"a1"},
    )
    assert repeated["ok"], repeated
    assert repeated["verified"] is True
    assert repeated["counts"]["texts_inserted"] == 0
    assert rows == before


def test_text_value_lookup_finds_the_code_with_the_ocd_hash_that_properties_values_stored():
    """Real Lino: Properties & Values stored 'Fabric_Type=1FD#'; Text looked for '1FD' and refused."""
    rows = {("7", "1fd#"): [{"com_ValueID": 1}], ("7", "1fd01"): [{"com_ValueID": 2}]}
    find = TextMdbExportService._value_rows
    assert find(rows, 7, "1FD#", "1FD") == [{"com_ValueID": 1}]      # stored with '#'
    assert find(rows, 7, "1FD01", "1FD01") == [{"com_ValueID": 2}]   # plain code unchanged
    assert find(rows, 7, "1FD", "1FD") == []                         # nothing stored: still reported
    plain = {("7", "1fd"): [{"com_ValueID": 3}]}
    assert find(plain, 7, "1FD#", "1FD") == [{"com_ValueID": 3}]     # stored without '#': stripped fallback
