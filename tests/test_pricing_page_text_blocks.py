"""Text Block columns of the Pricing table, and their link to the export results."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from core.application_context import ApplicationContext
from core.modules import WorkbenchModule
from models.price_record import PriceRecord
from models.snapshot import Snapshot
from models.text_block import TextBlock
from ui.dialogs.price_export_preview_dialog import PriceExportPreviewDialog, summary_lines
from ui.pages import pricing_page as pp
from ui.pages.pricing_page import PricingPage

from tests.test_price_mdb_export_service import (
    _OptimizedFake, _eur_gbp_lists, _export, _export_dry, _global, _rec,
)


@pytest.fixture(scope="module", autouse=True)
def _app():
    return QApplication.instance() or QApplication([])


def _page(records, text_blocks=()):
    snap = Snapshot()
    snap.metadata.source = "PDM"
    snap.price_records = list(records)
    snap.text_blocks = list(text_blocks)
    ctx = ApplicationContext()
    ctx.register_pdm_snapshot(snap)
    ctx.activate_snapshot_source("pdm")
    page = PricingPage(ctx)
    page._active_module = WorkbenchModule.MAINTENANCE
    page.refresh()
    return page


def _rows(page):
    t = page._table
    return [[(t.item(r, c).text() if t.item(r, c) else "") for c in range(t.columnCount())]
            for r in range(t.rowCount())]


def _headers(page):
    t = page._table
    return [t.horizontalHeaderItem(c).text() for c in range(t.columnCount())]


def test_text_block_columns_sit_between_currency_and_change():
    page = _page([_rec(1.0, "EUR")])
    assert _headers(page) == ["Article", "Variant Condition", "Value", "Currency",
                              "Text Block ID", "Text Block", "Change"]


def test_unchecked_global_is_proposed_and_article_has_no_text_block():
    page = _page([_global("GE2HBS.", 5.0), _rec(9.0, "EUR")])
    by_vc = {r[1]: r for r in _rows(page)}
    assert by_vc["GE2HBS."][4] == "Not checked"          # never an id before an MDB was read
    assert "(proposed)" in by_vc["GE2HBS."][5]
    article = next(r for r in _rows(page) if r[0] == "A1")
    assert article[4] == "—" and article[5] == ""


def test_preview_shows_new_text_as_not_written_and_existing_with_its_id():
    mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22],
                         texts=[{"com_TextID": 88, "com_TextName": "OLD.", "com_Text_1_en": "OLD.  (P)"}])
    records = [_global("OLD."), _global("NEW.1"), _global("NEW.1", 8, "GBP"), _rec(9.0, "EUR")]
    page = _page(records)
    result = _export_dry(mdb, records)
    page._apply_text_results(result)
    rows = {(r[1], r[3]): r for r in _rows(page)}
    assert rows[("OLD.", "EUR")][4] == "88"
    assert rows[("NEW.1", "EUR")][4] == "New (not written)"
    assert rows[("NEW.1", "GBP")][4] == "New (not written)"
    assert not any(r[4].isdigit() for k, r in rows.items() if k[0] == "NEW.1")
    assert mdb.ops == []


def test_table_shows_the_same_ids_the_export_wrote(monkeypatch):
    """UI values equal the MDB read-back: the ids come from the verified export result."""
    mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22],
                         texts=[{"com_TextID": 88, "com_TextName": "OLD."}])
    records = [_global("OLD."), _global("NEW.1", product_code="P-1"), _global("NEW.1", 8, "GBP", product_code="P-1")]
    page = _page(records)
    result = _export(mdb, records)
    assert result["ok"] and result["verified"]
    page._apply_text_results(result)
    written = {r["com_VariantCondition"] + "|" + r["sys_ISOCurrencyCode"]: r["com_TextID"]
               for op in mdb.ops if op["table"] == "tCOMd_GlobalPrice" and op["op"] == "insert"
               for r in op["rows"]}
    shown = {r[1] + "|" + r[3]: r[4] for r in _rows(page)}
    assert {k: int(v) for k, v in shown.items()} == written
    new_text = next(op for op in mdb.ops if op["table"] == "tCOMd_Text")["rows"][0]
    assert shown["NEW.1|EUR"] == str(new_text["com_TextID"])


def test_unverified_text_is_never_shown_as_an_id():
    mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22])
    base = mdb._readback
    mdb._readback = lambda name, sql="": [] if name.startswith("texts:") else base(name, sql)
    records = [_global("NEW.1")]
    page = _page(records)
    result = _export(mdb, records)
    page._apply_text_results(result)
    assert _rows(page)[0][4] == "Unverified"


def test_filter_and_search_cover_text_blocks():
    globals_ = [{"com_GlobalPriceID": 100, "com_PackageID": 1, "com_PriceListID": 21, "com_VariantCondition": "U.1",
                 "com_PriceLevelCode": "X", "sys_ISOCurrencyCode": "EUR", "com_PriceValue": 1.0, "com_TextID": None}]
    mdb = _OptimizedFake(_eur_gbp_lists(), globals_=globals_, linked=[21, 22],
                         texts=[{"com_TextID": 88, "com_TextName": "OLD.", "com_Text_1_en": "Old thing"}])
    records = [_global("U.1", 5.0), _global("OLD."), _rec(9.0, "EUR")]
    page = _page(records)
    page._apply_text_results(_export_dry(mdb, records))
    page._filter.setCurrentText(pp._FILTER_TEXT_ISSUES)
    assert [r[1] for r in _rows(page)] == ["U.1"]          # only the unlinked existing row
    assert _rows(page)[0][4] == "Missing"
    page._filter.setCurrentText(pp._FILTER_ALL)
    page._search.setText("old thing")                       # search matches text content
    page._apply_filter()                                    # (typing is debounced)
    assert [r[1] for r in _rows(page)] == ["OLD."]
    page._search.setText("88")                              # ... and the text id
    page._apply_filter()
    assert [r[1] for r in _rows(page)] == ["OLD."]


def test_sorting_by_text_block_id_does_not_scramble_rows():
    mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22],
                         texts=[{"com_TextID": 88, "com_TextName": "A."}, {"com_TextID": 70, "com_TextName": "B."}])
    records = [_global("A."), _global("B.")]
    page = _page(records)
    page._apply_text_results(_export_dry(mdb, records))
    page._table.sortItems(pp._COL_TEXT_ID)
    rows = _rows(page)
    assert {r[1]: r[4] for r in rows} == {"A.": "88", "B.": "70"}
    assert all(r[2] for r in rows)                           # price column still populated


def test_imported_mdb_rows_show_their_stored_text_reference():
    snap = Snapshot()
    snap.metadata.source = "MDB"
    snap.price_records = [
        PriceRecord(is_global=True, variant_condition="OLD.", value=3.0, currency="EUR", text_id="88"),
        PriceRecord(is_global=True, variant_condition="LOST.", value=3.0, currency="EUR"),
    ]
    snap.text_blocks = [TextBlock(name="OLD.", type_code="price", en="OLD.  (P)")]
    ctx = ApplicationContext()
    ctx.register_pdm_snapshot(Snapshot())
    ctx.register_mdb_import_snapshot(snap)
    ctx.activate_snapshot_source("pdm")
    page = PricingPage(ctx)
    page._active_module = WorkbenchModule.MAINTENANCE
    page._source_tabs.set_source("mdb")
    rows = {r[1]: r for r in _rows(page)}
    assert rows["OLD."][4] == "88" and "OLD.  (P)" in rows["OLD."][5]
    assert rows["LOST."][4] == "Missing"


def test_refresh_clears_previous_text_results():
    page = _page([_global("A.")])
    page._text_results = {("x",): {"action": "reuse", "text_id": 1}}
    page.refresh()  # reloading from the snapshot discards results of an earlier MDB comparison
    assert page._text_results == {}


def test_preview_dialog_reports_planned_totals_and_rows():
    mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22],
                         texts=[{"com_TextID": 88, "com_TextName": "OLD."}])
    result = _export_dry(mdb, [_global("OLD."), _global("NEW.1"), _rec(9.0, "EUR")])
    text = "\n".join(summary_lines(result))
    for needle in ("Price rows to update: 0", "Price rows to insert: 3", "Text blocks to reuse: 1",
                   "Text blocks to create: 1", "Missing or ambiguous text mappings: 0"):
        assert needle in text
    dialog = PriceExportPreviewDialog(result)
    assert dialog.table.rowCount() == 3
    ids = [dialog.table.item(r, 7).text() for r in range(3)]
    assert "New (not written)" in ids and "88" in ids


def test_export_result_dialog_reports_actual_counts():
    mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22])
    result = _export(mdb, [_global("NEW.1"), _global("NEW.1", 8, "GBP")])
    text = "\n".join(summary_lines(result))
    assert "Text blocks created: 1" in text
    assert "Price rows linked to text blocks: 2" in text
    assert "Failed text operations: 0" in text
    assert "Read-back verification failures: 0" in text
