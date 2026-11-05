"""Article OBX Generator -> temporary OBX snapshot -> unchanged OBX Validator workflow.

The Validator is driven through its real entry point (``ObxValidationPage._load_paths`` ->
``ObxValidationService.parse_obx``). Nothing in it is patched except the PDM pricing service that
``ObxValidationService.validate`` delegates to, which is replaced by a deterministic stub.
"""
from __future__ import annotations

import dataclasses
import hashlib
import os
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from services.article_obx.ocd_repository_obx import ObxExportError, export_obx  # noqa: E402
from services.article_obx.validator_handoff import SNAPSHOT_FILE_NAME, ValidatorHandoff  # noqa: E402
from services.obx_validation_service import ObxValidationService  # noqa: E402
from services.ocd_engine.generator import GeneratedSku  # noqa: E402
from services.sif_validation_service import SifResult  # noqa: E402
from ui.pages.obx_validation_page import ObxValidationPage  # noqa: E402

DATE = "2026-11-04"


@pytest.fixture(scope="module")
def qapp():
    # Never own or quit the application: other test modules share the process-wide instance.
    return QApplication.instance() or QApplication([])


_PAGES: list = []


@pytest.fixture(autouse=True)
def _dispose_pages():
    """Every ObxValidationPage a test builds is closed and deleted before the next test runs."""
    yield
    while _PAGES:
        page = _PAGES.pop()
        page.close()
        page.deleteLater()
    app = QApplication.instance()
    if app is not None:
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()


def _sku(i: int, *, fabric=("Fabric_Type", "CHAR"), colour=("Fabric_Colour", "BK"), price="100.50",
         base="LN10", currency="EUR") -> GeneratedSku:
    final = f"{base} {fabric[1]} {colour[1]} {i:05d}"
    return GeneratedSku(
        index=i, base_article=base, series_id="BETWIXT", final_article=final, variant_code="",
        ofml_varcode=f"BETWIXT_OPT.{fabric[0]}={fabric[1]};BETWIXT_OPT.{colour[0]}={colour[1]}",
        configuration_text="", label=f"Lounge chair {i}",
        values=(("BETWIXT_OPT", fabric[0], fabric[1], fabric[1]), ("BETWIXT_OPT", colour[0], colour[1], colour[1]),
                ("BETWIXT_OPT", "Frame", f"F{i % 3}", f"F{i % 3}")),
        price=Decimal(price) + i, currency=currency,
    )


def _page(qapp):
    session: dict = {}
    context = SimpleNamespace(
        workflow_session=lambda name: session,
        obx_validation_service=ObxValidationService(None),
    )
    page = ObxValidationPage(context)
    _PAGES.append(page)
    return page


def _load(page, path) -> dict:
    page._load_paths([str(path)])
    return {
        "currency": page._currency,
        "lines": [dataclasses.asdict(line) for line in page._lines],
        "skipped": page._skipped_count,
        "duplicates": page._duplicate_count,
        "duplicate_seqs": set(page._duplicate_seq_set),
        "date": page._validation_date.date().toString("dd-MMM-yyyy"),
    }


class _StubPricing:
    """Stands in for the PDM-backed pricing service the Validator delegates to."""

    def validate(self, currency, lines, site=None, obx=False, validation_date=None, progress=None, stage=None,
                 on_result=None, **_):
        results = []
        for line in lines:
            pdm = float(line.sif_price) if line.seq % 4 else float(line.sif_price) + 1.0
            result = SifResult(seq=line.seq, sku=line.final_article, currency=line.currency, plc=line.plc,
                               qty=line.qty, source_date=line.source_date, sif_price=line.sif_price,
                               pdm_price=pdm, status="ok", message="")
            results.append(result)
            if on_result:
                on_result(result)
        return {currency: site}, results


def _validate(lines):
    service = ObxValidationService(SimpleNamespace(sif_validation_service=_StubPricing()))
    sites, results = service.validate("EUR", lines, site=1, validation_date=DATE)
    return sites, [dataclasses.asdict(r) for r in results]


def _both(qapp, tmp_path, skus, handoff=None):
    normal = tmp_path / "user_export.obx"
    export_obx(skus, normal, manufacturer_id="HM", price_date=DATE, series_id="BETWIXT")
    handoff = handoff or ValidatorHandoff(tmp_path / "handoff_root")
    snapshot = handoff.create(skus, manufacturer_id="HM", price_date=DATE, series_id="BETWIXT")
    return normal, snapshot, handoff


def test_snapshot_is_isolated_from_user_export_and_other_data(qapp, tmp_path):
    skus = [_sku(i) for i in range(3)]
    normal = tmp_path / "exports" / "mine.obx"
    export_obx(skus, normal, manufacturer_id="HM", price_date=DATE)
    before = hashlib.sha256(normal.read_bytes()).hexdigest()
    other = tmp_path / "pdm_snapshot.db"
    other.write_text("pdm")

    handoff = ValidatorHandoff(tmp_path / "handoff_root")
    snapshot = handoff.create(skus, manufacturer_id="HM", price_date=DATE)

    assert snapshot.path.name == SNAPSHOT_FILE_NAME
    assert snapshot.path != normal and tmp_path / "handoff_root" in snapshot.path.parents
    assert hashlib.sha256(normal.read_bytes()).hexdigest() == before
    assert other.read_text() == "pdm"
    assert sorted(p.name for p in (tmp_path / "exports").iterdir()) == ["mine.obx"]


def test_replace_and_clear_only_touch_the_snapshot(qapp, tmp_path):
    keep = tmp_path / "handoff_root" / "unrelated.txt"
    keep.parent.mkdir()
    keep.write_text("keep")
    foreign = tmp_path / "exports" / "mine.obx"
    export_obx([_sku(1)], foreign, manufacturer_id="HM", price_date=DATE)

    handoff = ValidatorHandoff(tmp_path / "handoff_root")
    first = handoff.create([_sku(1)], manufacturer_id="HM", price_date=DATE)
    second = handoff.create([_sku(1), _sku(2)], manufacturer_id="HM", price_date=DATE)
    assert not first.path.exists() and second.path.exists() and handoff.current is second
    assert second.article_count == 2

    handoff.clear()
    assert handoff.current is None and not second.path.exists()
    assert keep.read_text() == "keep" and foreign.exists()


def test_unpriced_only_selection_is_rejected(qapp, tmp_path):
    unpriced = dataclasses.replace(_sku(1), price=None)
    with pytest.raises(ObxExportError):
        ValidatorHandoff(tmp_path / "h").create([unpriced], manufacturer_id="HM", price_date=DATE)


def test_validator_input_parity_with_normal_obx(qapp, tmp_path):
    skus = [_sku(i) for i in range(1, 8)] + [_sku(3)]  # a duplicate final article
    normal, snapshot, _ = _both(qapp, tmp_path, skus)
    assert snapshot.ok

    page = _page(qapp)
    from_normal = _load(page, normal)
    from_snapshot = _load(_page(qapp), snapshot.path)

    assert from_snapshot == from_normal
    lines = from_snapshot["lines"]
    assert [l["seq"] for l in lines] == list(range(1, len(skus) + 1))
    assert [l["final_article"] for l in lines] == [s.final_article for s in skus]  # order preserved
    assert all(l["base_article"] == "LN10" and l["currency"] == "EUR" and l["qty"] == 1 for l in lines)
    assert [l["obx_price"] for l in lines] == [float(s.price) for s in skus]
    assert from_snapshot["duplicates"] == from_normal["duplicates"] > 0
    assert from_snapshot["date"] == "04-Nov-2026"  # the OBX priceDate, as for a normal load


def test_every_validator_field_is_populated(qapp, tmp_path):
    skus = [_sku(1)]
    _, snapshot, _ = _both(qapp, tmp_path, skus)
    _, lines = ObxValidationService(None).parse_obx(snapshot.path.read_text(encoding="utf-8"))
    (line,) = lines
    assert line.final_article == skus[0].final_article and line.base_article == "LN10"
    assert line.currency == "EUR" and line.obx_price == float(skus[0].price) and line.qty == 1
    assert line.source_date == DATE and line.source_index == 0
    assert line.features["Fabric_Type"] == "CHAR" and line.features["Fabric_Colour"] == "BK"
    # Not produced by the generator: PLC lives only in pCon/PDM exports, so it stays empty exactly as in the
    # normal Article OBX export.
    assert line.plc == ""


def test_shared_fabric_selections_are_preserved(qapp, tmp_path):
    skus = [
        _sku(1, fabric=("Fabric_Type", "CHAR"), colour=("Fabric_Colour", "BK")),
        _sku(2, fabric=("Fabric_Type", "CHAR"), colour=("Fabric_Colour", "BK"), base="LN20"),
        _sku(3, fabric=("Fabric_Type", "WOOL"), colour=("Fabric_Colour", "GY")),
    ]
    normal, snapshot, _ = _both(qapp, tmp_path, skus)
    from_snapshot = _load(_page(qapp), snapshot.path)
    assert from_snapshot == _load(_page(qapp), normal)
    features = [l["features"] for l in from_snapshot["lines"]]
    assert [(f["Fabric_Type"], f["Fabric_Colour"]) for f in features] == [
        ("CHAR", "BK"), ("CHAR", "BK"), ("WOOL", "GY")]


def test_validation_results_and_diagnostics_match(qapp, tmp_path):
    skus = [_sku(i) for i in range(1, 11)] + [_sku(2)]
    normal, snapshot, _ = _both(qapp, tmp_path, skus)
    service = ObxValidationService(None)
    _, normal_lines = service.parse_obx(normal.read_text(encoding="utf-8"))
    normal_skipped = service.last_parse_skipped_count
    _, snap_lines = service.parse_obx(snapshot.path.read_text(encoding="utf-8"))
    assert service.last_parse_skipped_count == normal_skipped
    assert service.last_parse_recovered is False

    assert _validate(snap_lines) == _validate(normal_lines)
    sites, results = _validate(snap_lines)
    assert sites == {"EUR": 1} and len(results) == len(skus)
    # The stub makes some PDM prices differ, so both outcomes (and their messages) are compared above.
    assert {r["status"] for r in results} == {"ok", "price_mismatch"}

    assert service.duplicate_count(snap_lines) == service.duplicate_count(normal_lines) == 1


def test_loading_snapshot_does_not_change_other_workflows(qapp, tmp_path):
    skus = [_sku(i) for i in range(1, 4)]
    normal, snapshot, handoff = _both(qapp, tmp_path, skus)
    before = hashlib.sha256(normal.read_bytes()).hexdigest()
    page = _page(qapp)
    _load(page, snapshot.path)
    handoff.clear()
    # A normal OBX still loads exactly as before once the snapshot is gone.
    again = _load(page, normal)
    assert len(again["lines"]) == 3 and hashlib.sha256(normal.read_bytes()).hexdigest() == before
    assert page._paths == [str(normal)]


def test_large_selection_loads_through_the_validator(qapp, tmp_path):
    skus = [_sku(i) for i in range(1, 2001)]
    _, snapshot, _ = _both(qapp, tmp_path, skus)
    assert snapshot.ok and snapshot.article_count == 2000
    loaded = _load(_page(qapp), snapshot.path)
    assert len(loaded["lines"]) == 2000 and loaded["skipped"] == 0


def test_shared_fabric_selection_is_kept_in_both_encoded_positions(qapp, tmp_path):
    """A shared fabric choice appears twice in the final article ("... R39 1HA01 1HA01") and must survive."""
    final = "NOHAN350W2 R39 1HA01 1HA01"
    sku = GeneratedSku(
        index=0, base_article="NOHAN350W2", series_id="HANNA", final_article=final, variant_code="",
        ofml_varcode="HANNA_OPT.Fabric=1HA01", configuration_text="", label="Hanna",
        values=(("HANNA_OPT", "Seat_Fabric", "1HA01", "1HA01"), ("HANNA_OPT", "Back_Fabric", "1HA01", "1HA01")),
        price=Decimal("250"), currency="EUR",
    )
    normal, snapshot, _ = _both(qapp, tmp_path, [sku])
    loaded = _load(_page(qapp), snapshot.path)
    assert loaded == _load(_page(qapp), normal)
    (line,) = loaded["lines"]
    assert line["final_article"] == final
    assert line["final_article"].split()[-2:] == ["1HA01", "1HA01"]
    assert line["features"]["Seat_Fabric"] == line["features"]["Back_Fabric"] == "1HA01"
    assert [o.code for o in ObxValidationService(None).parse_obx(snapshot.path.read_text("utf-8"))[1][0].options]         == ["R39", "1HA01", "1HA01"]


def test_snapshot_leaves_no_files_behind_after_clear(qapp, tmp_path):
    handoff = ValidatorHandoff(tmp_path / "root")
    handoff.create([_sku(1)], manufacturer_id="HM", price_date=DATE)
    handoff.create([_sku(2)], manufacturer_id="HM", price_date=DATE)
    handoff.clear()
    assert list((tmp_path / "root").iterdir()) == []


# ---------------------------------------------------------------- Validator "Load from Article OBX Generator"
import services.article_obx.validator_handoff as handoff_module  # noqa: E402
from unittest.mock import Mock  # noqa: E402

import ui.pages.obx_validation_page as validation_page_module  # noqa: E402

OPTION = "Load from Article OBX Generator"


@pytest.fixture
def shared(tmp_path, monkeypatch):
    """A private shared handoff so no test touches the real temp folder."""
    handoff = ValidatorHandoff(tmp_path / "shared_root")
    monkeypatch.setattr(handoff_module, "_SHARED", handoff)
    return handoff


def _option(page):
    (action,) = [a for a in page._load_btn.menu().actions() if a.text() == OPTION]
    return action


def test_validator_offers_the_option_next_to_the_existing_ones(qapp):
    texts = [a.text() for a in _page(qapp)._load_btn.menu().actions()]
    assert texts[:2] == ["Select file(s)...", "Select folder (including subfolders)..."]
    assert OPTION in texts


def test_option_passes_the_generated_obx_path_to_the_existing_load_path(qapp, shared, monkeypatch):
    snapshot = shared.create([_sku(i) for i in range(1, 4)], manufacturer_id="HM", price_date=DATE, series_id="BETWIXT")
    page = _page(qapp)
    original = page._load_paths
    spy = Mock(side_effect=original)
    monkeypatch.setattr(page, "_load_paths", spy)

    _option(page).trigger()

    spy.assert_called_once_with([str(snapshot.path)])
    assert page._paths == [str(snapshot.path)] and len(page._lines) == 3
    normal = snapshot.path.parent.parent / "ordinary.obx"
    export_obx([_sku(i) for i in range(1, 4)], normal, manufacturer_id="HM", price_date=DATE, series_id="BETWIXT")
    assert [dataclasses.asdict(l) for l in page._lines] == _load(_page(qapp), normal)["lines"]


def test_generated_file_survives_loading_and_a_second_load(qapp, shared):
    snapshot = shared.create([_sku(1)], manufacturer_id="HM", price_date=DATE)
    page = _page(qapp)
    _option(page).trigger()
    assert snapshot.path.is_file()            # not deleted after the path was handed over
    _option(page).trigger()
    assert snapshot.path.is_file() and len(page._lines) == 1


@pytest.mark.parametrize("expire", [False, True])
def test_missing_or_expired_generated_obx_gives_a_clear_message(qapp, shared, monkeypatch, expire):
    info = Mock()
    monkeypatch.setattr(validation_page_module.QMessageBox, "information", info)
    if expire:
        snapshot = shared.create([_sku(1)], manufacturer_id="HM", price_date=DATE)
        snapshot.path.unlink()
    page = _page(qapp)
    _option(page).trigger()
    info.assert_called_once()
    assert "no generated OBX" in info.call_args.args[2] and "expired" in info.call_args.args[2]
    assert page._lines == [] and getattr(page, "_paths", []) == []


def test_ordinary_file_loading_is_untouched_by_the_option(qapp, shared, tmp_path):
    shared.create([_sku(9)], manufacturer_id="HM", price_date=DATE)
    mine = tmp_path / "mine.obx"
    export_obx([_sku(1), _sku(2)], mine, manufacturer_id="HM", price_date=DATE)
    page = _page(qapp)
    loaded = _load(page, mine)
    assert page._paths == [str(mine)] and len(loaded["lines"]) == 2
    assert shared.current_path() is not None       # an ordinary load never touches the handoff


def test_cleanup_only_removes_handoff_owned_stale_folders(qapp, tmp_path):
    root = tmp_path / "root"
    handoff = ValidatorHandoff(root)
    old = handoff.create([_sku(1)], manufacturer_id="HM", price_date=DATE)
    unrelated_dir = root / "someone_elses_folder"
    unrelated_dir.mkdir()
    (unrelated_dir / "keep.obx").write_text("x")
    user_file = tmp_path / "user.obx"
    user_file.write_text("x")
    stale_old = root / "handoff_previous_session"
    stale_old.mkdir()
    (stale_old / SNAPSHOT_FILE_NAME).write_text("x")
    past = old.path.stat().st_mtime - 10 * 24 * 3600
    os.utime(stale_old, (past, past))

    handoff.purge_stale()

    assert not stale_old.exists()                                    # an earlier session's leftover
    assert old.path.is_file()                                        # the live snapshot
    assert (unrelated_dir / "keep.obx").is_file() and user_file.is_file()


def test_shared_handoff_is_a_process_wide_singleton(monkeypatch):
    monkeypatch.setattr(handoff_module, "_SHARED", None)
    monkeypatch.setattr(handoff_module.atexit, "register", Mock())
    assert handoff_module.shared_handoff() is handoff_module.shared_handoff()


# ---------------------------------------------------------------- output beyond the parser's 2 GiB document limit
def test_oversized_snapshot_is_split_into_complete_parts_loaded_through_the_validator(qapp, shared, monkeypatch):
    skus = [_sku(i) for i in range(1, 61)]
    one = shared.root.parent / "single.obx"
    export_obx(skus, one, manufacturer_id="HM", price_date=DATE, series_id="BETWIXT")
    monkeypatch.setattr(handoff_module, "MAX_PART_BYTES", one.stat().st_size // 4)

    snapshot = shared.create(skus, manufacturer_id="HM", price_date=DATE, series_id="BETWIXT")

    assert snapshot.ok and len(snapshot.files) > 1 and snapshot.article_count == 60
    assert snapshot.path == snapshot.files[0]
    assert all(p.stat().st_size <= handoff_module.MAX_PART_BYTES for p in snapshot.files)
    assert {p.parent for p in snapshot.files} == {snapshot.path.parent}

    page = _page(qapp)
    _option(page).trigger()
    assert page._paths == [str(p) for p in snapshot.files]
    reference = _load(_page(qapp), one)["lines"]
    loaded = [dataclasses.asdict(l) for l in page._lines]
    strip = lambda rows: [{k: v for k, v in r.items() if k not in ("seq", "source_index")} for r in rows]
    assert strip(loaded) == strip(reference) and [l["seq"] for l in loaded] == list(range(1, 61))

    shared.clear()
    assert not snapshot.path.parent.exists()


def test_small_snapshot_stays_a_single_file(qapp, shared):
    snapshot = shared.create([_sku(i) for i in range(1, 4)], manufacturer_id="HM", price_date=DATE)
    assert snapshot.files == (snapshot.path,) and snapshot.path.name == SNAPSHOT_FILE_NAME
    assert shared.current_paths() == [snapshot.path]


def test_read_back_overflow_is_reported_with_context_not_raised(qapp, shared, monkeypatch):
    def overflow(self, text):
        raise OverflowError("size does not fit in an int")

    monkeypatch.setattr(ObxValidationService, "parse_obx", overflow)
    snapshot = shared.create([_sku(1)], manufacturer_id="HM", price_date=DATE)
    assert not snapshot.ok
    message = snapshot.problems[0]
    assert "part 1 of 1" in message and "bytes" in message and "size does not fit in an int" in message
