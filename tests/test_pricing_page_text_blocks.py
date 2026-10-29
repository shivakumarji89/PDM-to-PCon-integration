"""Text Block columns of the Pricing table, and their link to the export results."""
from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication

from core.application_context import ApplicationContext
from core.modules import WorkbenchModule
from models.price_record import PriceRecord
from models.option import Option
from models.product import Product
from models.snapshot import Snapshot
from models.text_block import TextBlock
from ui.dialogs.price_export_preview_dialog import PriceExportPreviewDialog, summary_lines
from ui.pages import pricing_page as pp
from ui.pages.pricing_page import PricingPage
from repositories.pdm_repository import PDMRepository
from services.pricing_service import PricingService, pricing_requires_recompute
from services.snapshot_serialization import snapshot_from_dict, snapshot_to_dict

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


def test_colour_family_preview_displays_preserved_ids_for_computed_conditions():
    from tests.test_pricing_fabric_targets import records, target_mdb

    computed = records()
    page = _page(computed)
    preview = _export_dry(target_mdb(computed), computed)
    page._apply_text_results(preview)
    shown = _rows(page)
    assert [r[1] for r in shown] == [r.variant_condition for r in computed]
    assert [r[4] for r in shown] == [str(1101 + i * 2) for i in range(4)]
    assert all(r[5].startswith("28=") and "(proposed)" not in r[5] for r in shown)


def test_new_colour_family_preview_and_result_show_option_label_and_real_generated_id():
    from tests.test_pricing_fabric_targets import records, new_target_mdb

    computed = records()
    mdb = new_target_mdb()
    preview = _export_dry(mdb, computed)
    page = _page(computed)
    page._apply_text_results(preview)
    assert {r[4] for r in _rows(page)} == {"New (not written)"}
    assert all("Surcharge 28" in r[5] for r in _rows(page))
    dialog = PriceExportPreviewDialog(preview, allow_export=True)
    assert dialog.export_button.isEnabled()
    for i in range(4):
        assert dialog.table.item(i, 5).text() == "insert"
        assert dialog.table.item(i, 7).text() == "New (not written)"
        assert "Surcharge 28" in dialog.table.item(i, 8).text()
    result = _export(mdb, computed)
    page._apply_text_results(result)
    assert {r[4] for r in _rows(page)} == {"501"}
    assert all("Surcharge 28" in r[5] for r in _rows(page))


def _old_fabric_page():
    from tests.test_pricing_fabric_targets import ITEM, records

    old = [replace(r, variant_condition=r.variant_condition.replace(" 28=", " 8="),
                   pricing_revision=0) for r in records()]
    page = _page(old)
    snap = page._context.active_snapshot
    snap.options = [Option(id="8", name="Fabric type", is_fabric=True)]
    snap.product = Product(catalogue_id="658")
    snap.article_components = {"parent": [{"sub_item": ITEM}]}
    # Exercise an old saved snapshot with no revision or generation-program settings.
    serialized = snapshot_to_dict(snap)
    for row in serialized["price_records"]:
        row.pop("pricing_revision")
    restored = snapshot_from_dict(serialized)
    page._context.register_pdm_snapshot(restored)
    page.refresh()
    return page


def test_old_fabric_snapshot_is_explicitly_stale_and_cannot_open_export(monkeypatch):
    from tests.test_pricing_fabric_targets import ITEM, FAMILIES

    page = _old_fabric_page()
    snap = page._context.active_snapshot
    assert pricing_requires_recompute(snap)
    assert "outdated" in page._summary.text()
    assert not page._preview_btn.isEnabled() and not page._export_btn.isEnabled()
    assert [r[1] for r in _rows(page)] == [f"{ITEM} 8={f[0]}" for f in FAMILIES]
    warnings = []
    monkeypatch.setattr(pp.QMessageBox, "warning", lambda *args: warnings.append(args[-1]))
    monkeypatch.setattr(pp.QFileDialog, "getOpenFileName",
                        lambda *a: pytest.fail("stale prices must not open MDB selection"))
    page._on_preview_export()
    page._on_export_prices()
    assert len(warnings) == 2
    assert snap.price_records[0].pricing_revision == 0  # no historical migration


@pytest.mark.parametrize("mapped", [True, False])
def test_actual_compute_refresh_and_snapshot_roundtrip_display_resolved_conditions(monkeypatch, mapped):
    from tests.test_pricing_fabric_targets import ITEM, FAMILIES, relation, source_rows
    from tests.test_pricing_export_workflow import _Sync

    page = _old_fabric_page()
    snap = page._context.active_snapshot
    assert snap.generation_program == ""
    snap.generation_program = "revive"  # Maintenance requires an explicit program; Revive keeps 28= routing
    rows = source_rows()
    monkeypatch.setattr(pp.QThreadPool, "globalInstance", staticmethod(lambda: _Sync()))
    monkeypatch.setattr(PDMRepository, "get_connection",
                        lambda self: SimpleNamespace(close=lambda: None))
    monkeypatch.setattr(PDMRepository, "fetch_item_base_prices", lambda *a, **kw: [])
    monkeypatch.setattr(PricingService, "_attach_product_codes", lambda *a: None)

    def execute(self, query, params, connection=None):
        if "AS TargetOptionId" in query:
            return [relation(vid, colour) for _, vid, colour, _, _ in FAMILIES] if mapped else []
        if "AS NewPrice" in query:
            return [SimpleNamespace(Item=ITEM, NewPrice=next(r.IncPrice for r in rows
                                                            if r.OptionValueId == params[6]))]
        return [SimpleNamespace(Item=r.Item, OptionId=r.OptionId, OptionValueId=r.OptionValueId,
                                OrderCodeValue=r.SourceCode, RawIncrement=r.RawIncrement,
                                PriceBand=None) for r in rows]

    monkeypatch.setattr(PDMRepository, "_execute", execute)
    shown = []  # compute warnings open a modal information box; capture it instead of blocking
    monkeypatch.setattr(pp.QMessageBox, "information", lambda *args: shown.append(args[-1]))
    batches = []
    append = page._append_batch

    def append_and_refresh(batch):
        append(batch)
        page.refresh()  # navigation must not restore old stored records mid-stream
        batches.extend(batch)
        assert [r[1] for r in _rows(page)] == [r.variant_condition for r in batches]

    monkeypatch.setattr(page, "_append_batch", append_and_refresh)
    page._on_compute()
    assert not page._pricing_running
    assert not shown  # explicit program: no blank-program routing warning
    option = 28 if mapped else 8
    expected = [f"{ITEM} {option}={f[0]}" for _ in ("EUR", "GBP") for f in FAMILIES]
    assert [r[1] for r in _rows(page)] == expected
    assert [r.value for r in snap.price_records] == [89, 44, 133, 89] * 2
    assert [r.pdm_lookup_code for r in snap.price_records] == [
        f"{ITEM} 8={f[0]}#" for _ in ("EUR", "GBP") for f in FAMILIES
    ]
    assert page._preview_btn.isEnabled() and page._export_btn.isEnabled()
    restored = snapshot_from_dict(snapshot_to_dict(snap))
    assert restored.price_records == snap.price_records
    assert not pricing_requires_recompute(restored)
    page._context.register_pdm_snapshot(restored)
    page.refresh()
    assert [r[1] for r in _rows(page)] == expected
    assert "outdated" not in page._summary.text()


def test_failed_recompute_restores_historical_rows_without_enabling_export(monkeypatch):
    page = _old_fabric_page()
    old = _rows(page)
    page._pricing_running = True
    page._records = []
    monkeypatch.setattr(pp.QMessageBox, "critical", lambda *args: None)
    page._on_pricing_failed("PDM unavailable")
    assert _rows(page) == old
    assert not page._preview_btn.isEnabled() and not page._export_btn.isEnabled()
    assert "outdated" in page._summary.text()


def test_pricing_staleness_does_not_rewrite_mdb_or_other_program_records():
    page = _old_fabric_page()
    snap = page._context.active_snapshot
    snap.generation_program = "embody"
    assert not pricing_requires_recompute(snap)
    snap.generation_program = ""
    snap.metadata.source = "MDB"
    assert not pricing_requires_recompute(snap)
    assert all(r.pricing_revision == 0 for r in snap.price_records)


def test_previously_resolved_snapshots_do_not_require_recomputation():
    from tests.test_pricing_fabric_targets import records

    page = _old_fabric_page()
    snap = page._context.active_snapshot
    snap.price_records = [replace(r, pricing_revision=0) for r in records()]
    assert not pricing_requires_recompute(snap)
    page.refresh()
    assert page._preview_btn.isEnabled() and page._export_btn.isEnabled()


@pytest.mark.parametrize("dry_run", [True, False])
def test_export_service_rejects_stale_fabric_prices_before_accessing_mdb(tmp_path, dry_run):
    from services.price_mdb_export_service import PriceMdbExportService

    page = _old_fabric_page()
    mdb_path = tmp_path / "existing.mdb"
    mdb_path.touch()
    # No MDB service exists: rejection must happen before even opening a connection.
    result = PriceMdbExportService(SimpleNamespace()).export(
        page._context.active_snapshot, mdb_path, dry_run=dry_run,
    )
    assert not result["ok"] and "Compute prices again" in result["error"]
    assert mdb_path.read_bytes() == b""


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



def test_refresh_during_stream_preserves_accumulated_records():
    stored = _rec(1.0, "EUR")
    streamed = _rec(9.0, "EUR")
    page = _page([stored])

    # The worker streams into the page before the completed result is committed
    # to snapshot.price_records. A page refresh must render the stream, not the
    # stale snapshot.
    page._records = [streamed]
    page._pricing_running = True
    page.refresh()

    assert page._records == [streamed]
    assert len(_rows(page)) == 1
    assert page._context.active_snapshot.price_records == [stored]
    assert page._summary.text().startswith("Computing prices...")


@pytest.mark.parametrize("program", ["", "aeron"])
def test_maintenance_compute_with_blank_or_unsupported_program_is_blocked(monkeypatch, program):
    page = _old_fabric_page()
    page._context.active_snapshot.generation_program = program
    warnings = []
    monkeypatch.setattr(pp.QMessageBox, "warning", lambda *args: warnings.append(args[-1]))
    started = []
    monkeypatch.setattr(PricingService, "compute_streaming", lambda *a, **k: started.append(1))
    page._on_compute()
    assert warnings and "Program" in warnings[0]
    assert not started and not getattr(page, "_pricing_running", False)
