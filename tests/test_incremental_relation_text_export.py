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
