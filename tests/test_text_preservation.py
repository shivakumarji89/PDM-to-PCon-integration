"""Attached-workspace Text preservation (existing production text must not be overwritten silently)."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from models.mdb_export_session import MdbExportSession
from models.text_block import TextBlock
from services.text_mdb_export_service import TextMdbExportService
from services.text_preservation_policy import decide_text
from test_incremental_relation_text_export import _FakeMdb, _incremental_context, _session

PROTO = {"tCOMd_Text": {"com_TextName": None, "com_TextTypeCode": None, "com_PackageID": None,
                        "com_Text_1_en": None, "com_Text_1_de": None}}


def _rows(long_en="Dalby Circular Coffee Table / 650mm", long_de="Kaffeetisch", extra=True):
    texts = [
        {"com_TextID": 7, "com_TextName": "BASE", "com_TextTypeCode": "artlong", "com_PackageID": 10,
         "com_Text_1_en": long_en, "com_Text_1_de": long_de},
        {"com_TextID": 8, "com_TextName": "BASE", "com_TextTypeCode": "artshort", "com_PackageID": 10,
         "com_Text_1_en": "", "com_Text_1_de": None},
    ]
    if extra:
        texts.append({"com_TextID": 9, "com_TextName": "UNRELATED", "com_TextTypeCode": "property",
                      "com_PackageID": 10, "com_Text_1_en": "keep me", "com_Text_1_de": "bleib"})
    return {
        "package": [{"com_PackageID": 10}], "texts": texts, "text_max": [{"max_id": 9}],
        "articles": [{"com_ArticleID": 5, "com_ArticleCode": "BASE", "com_PackageID": 10,
                      "com_ShortTextID": 8, "com_LongTextID": 7}],
        "classes": [], "properties": [], "values": [],
    }


def _snapshot(long_en="NODLE100", short_en="Coffee table"):
    member = SimpleNamespace(article_id="a1", short_description=short_en, long_description=long_en)
    return SimpleNamespace(
        product=SimpleNamespace(id="p1"),
        articles=[SimpleNamespace(id="a1", product_id="p1", code="BASE", name="Desk", description="Desk")],
        properties=[], options=[], property_values=[], option_values=[],
        article_property_value_ids={}, product_property_value_ids={}, product_option_value_ids={},
        product_range={}, attribute_range={}, article_sets=[], split_classes_by_group=False,
        class_group_basis="range",
        engineering=SimpleNamespace(families=[SimpleNamespace(members=[member])]),
        text_blocks=[TextBlock(name="BASE", type_code="artshort", en=short_en),
                     TextBlock(name="BASE", type_code="artlong", en=long_en)],
    )


def _run(tmp_path, rows, attached, snapshot=None, db_cls=_FakeMdb, **kwargs):
    path = tmp_path / "t.mdb"
    path.touch()
    snapshot = snapshot or _snapshot()
    session = _session(path, PROTO)
    session.attached_existing = attached
    db = db_cls(rows)
    service = TextMdbExportService(_incremental_context(db, session, snapshot))
    return service.export_to_session(snapshot, session, {"a1"}, **kwargs)


def _text(rows, text_id):
    return next(r for r in rows["texts"] if r["com_TextID"] == text_id)


def test_attached_preserves_populated_text_and_reports_conflict(tmp_path):
    rows = _rows()
    result = _run(tmp_path, rows, attached=True)
    assert result["ok"], result
    assert _text(rows, 7)["com_Text_1_en"] == "Dalby Circular Coffee Table / 650mm"
    conflicts = [c for c in result["conflicts"] if c["kind"] == "text"]
    assert len(conflicts) == 1
    c = conflicts[0]
    assert (c["entity"], c["text_id"], c["action"]) == ("artlong/BASE", 7, "preserved")
    assert (c["existing"], c["incoming"]) == ("Dalby Circular Coffee Table / 650mm", "NODLE100")
    assert any("PRESERVED" in w and "NODLE100" in w and "Dalby Circular" in w for w in result["warnings"])
    assert result["counts"]["texts_preserved"] == 1


def test_dry_run_reports_the_same_conflict_and_writes_nothing(tmp_path):
    rows = _rows()
    before = deepcopy(rows)
    result = _run(tmp_path, rows, attached=True, dry_run=True)
    assert result["ok"] and result["dry_run"]
    assert rows == before
    assert result["counts"]["texts_preserved"] == 1


def test_empty_text_is_populated_and_ids_languages_and_unrelated_rows_survive(tmp_path):
    rows = _rows()
    result = _run(tmp_path, rows, attached=True)
    assert result["ok"], result
    short = _text(rows, 8)
    assert short["com_Text_1_en"] == "Coffee table"          # empty -> populated
    assert _text(rows, 7)["com_Text_1_de"] == "Kaffeetisch"  # other language untouched
    assert _text(rows, 9)["com_Text_1_en"] == "keep me"      # unrelated
    assert [r["com_TextID"] for r in rows["texts"]] == [7, 8, 9]  # no new rows, IDs kept
    assert rows["articles"][0]["com_ShortTextID"] == 8 and rows["articles"][0]["com_LongTextID"] == 7


def test_missing_text_is_created_in_attached_workspace(tmp_path):
    rows = _rows()
    rows["texts"] = [r for r in rows["texts"] if r["com_TextID"] != 7]
    rows["articles"][0]["com_LongTextID"] = None
    result = _run(tmp_path, rows, attached=True)
    assert result["ok"], result
    created = [r for r in rows["texts"] if r["com_TextTypeCode"] == "artlong"]
    assert len(created) == 1 and created[0]["com_Text_1_en"] == "NODLE100"
    assert created[0]["com_TextID"] == 10
    assert rows["articles"][0]["com_LongTextID"] == 10


def test_replacement_requires_explicit_authorization(tmp_path):
    rows = _rows()
    assert _run(tmp_path, rows, attached=True)["ok"]
    assert _text(rows, 7)["com_Text_1_en"] != "NODLE100"          # default: disabled
    result = _run(tmp_path, rows, attached=True, replace_existing_text=True)
    assert result["ok"], result
    assert _text(rows, 7)["com_Text_1_en"] == "NODLE100"
    assert _text(rows, 7)["com_TextID"] == 7
    assert result["counts"]["texts_replaced"] == 1


def test_repeated_attached_export_is_idempotent(tmp_path):
    rows = _rows()
    assert _run(tmp_path, rows, attached=True)["ok"]
    after_first = deepcopy(rows)
    second = _run(tmp_path, rows, attached=True)
    assert second["ok"] and rows == after_first
    assert second["counts"]["texts_preserved"] == 1               # still reported, never written


def test_template_initialized_session_keeps_previous_overwrite_behaviour(tmp_path):
    rows = _rows()
    result = _run(tmp_path, rows, attached=False)
    assert result["ok"], result
    assert _text(rows, 7)["com_Text_1_en"] == "NODLE100"
    assert result["conflicts"] == []


def test_failed_transaction_leaves_no_partial_write(tmp_path):
    class Failing(_FakeMdb):
        def execute_batch(self, *_a, **_k):
            return SimpleNamespace(ok=False, first_error=lambda: "boom")

    rows = _rows()
    before = deepcopy(rows)
    result = _run(tmp_path, rows, attached=True, db_cls=Failing)
    assert result["ok"] is False and "boom" in result["error"]
    assert rows == before


def test_existing_valid_text_link_is_preserved_in_attached_workspace(tmp_path):
    rows = _rows()
    rows["articles"][0]["com_LongTextID"] = 9       # production links the article to another valid text
    result = _run(tmp_path, rows, attached=True)
    assert result["ok"], result
    assert rows["articles"][0]["com_LongTextID"] == 9
    assert any(c["kind"] == "text_link" and c["action"] == "preserved" for c in result["conflicts"])
    rows2 = _rows()
    rows2["articles"][0]["com_LongTextID"] = 9
    assert _run(tmp_path, rows2, attached=False)["ok"]
    assert rows2["articles"][0]["com_LongTextID"] == 7        # template: incoming wins


def test_decide_text_matrix():
    assert decide_text("x", "x", attached=True) == ("x", "same")
    assert decide_text("", "n", attached=True) == ("n", "filled")
    assert decide_text(None, "n", attached=False) == ("n", "filled")
    assert decide_text("x", "", attached=True) == ("x", "skipped")
    assert decide_text("x", "n", attached=True) == ("x", "preserved")
    assert decide_text("x", "n", attached=True, replace_existing=True) == ("n", "replaced")
    assert decide_text("x", "n", attached=False) == ("n", "replaced")


def test_legacy_session_without_flag_is_flagged_unknown_and_declaration_is_explicit(tmp_path):
    legacy = {"product_key": "id:p1", "mdb_path": "x.mdb"}
    assert MdbExportSession.from_dict(legacy).attached_flag_known is False
    assert MdbExportSession.from_dict({**legacy, "attached_existing": True}).attached_flag_known is True
    # a legacy file re-saved by the app keeps "unknown" (the persisted marker wins)
    s = MdbExportSession.from_dict(legacy)
    assert MdbExportSession.from_dict(s.to_dict()).attached_flag_known is False

    from services.mdb_export_session_service import ExportSessionError, MdbExportSessionService
    svc = MdbExportSessionService(SimpleNamespace())
    svc.store_dir = tmp_path
    svc.declare_attachment(s, True)
    assert s.attached_existing and s.attached_flag_known
    with pytest.raises(ExportSessionError):
        svc.declare_attachment(s, False)


def test_unknown_flag_session_warns_in_text_preview(tmp_path):
    rows = _rows()
    path = tmp_path / "t.mdb"
    path.touch()
    snapshot = _snapshot()
    session = _session(path, PROTO)
    session.attached_flag_known = False
    ctx = _incremental_context(_FakeMdb(rows), session, snapshot)
    result = TextMdbExportService(ctx).export_to_session(snapshot, session, {"a1"}, dry_run=True)
    assert result["ok"] and "saved before attached-workspace tracking" in result["warnings"][0]
