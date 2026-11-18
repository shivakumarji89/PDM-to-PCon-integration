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
