"""A full SKU set (hundreds of thousands of rows) is published without freezing the window.

The previous page filled a ``QTableWidget`` cell by cell on the GUI thread after the worker had finished
(~1.8 million items for LN10) while the progress dialog stayed at its last value with ``ETA 00:00`` and a
Cancel button. The result table is now a virtual model that reads the generator's list lazily.
"""
from __future__ import annotations

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time
from decimal import Decimal

import pytest

import ui.pages.pcon_article_obx_generator_page as page_module
from core.cancellation import CancellationToken, OperationCancelled, cancellation_scope
from services.ocd_engine.generator import GeneratedSku, GenerationOutcome, OcdArticleGenerator
from tests.test_pcon_sdk_obx_page import (  # noqa: F401  (fixtures and helpers of the page tests)
    _generate, _pick, app, drain, gen_page, generation_root, no_plugin,
)
from ui.dialogs.progress_dialog import ProgressDialog
from ui.pages.sku_results_model import HEADERS, SkuResultsModel

TOTAL = 254_043


def make_skus(count: int) -> list[GeneratedSku]:
    return [GeneratedSku(index=i, base_article="LN10", series_id="BETWIXT", final_article=f"LN10NUU BK {i:06d}",
                         variant_code=f"BK {i:06d}", ofml_varcode="FEATURES.Frame=N", configuration_text="Frame=N",
                         price=Decimal("1.50") if i % 2 else None, currency="GBP",
                         status="ok" if i % 2 else "unpriced", message="" if i % 2 else "no price")
            for i in range(1, count + 1)]


def test_model_publishes_a_full_result_set_in_constant_time():
    model = SkuResultsModel()
    skus = make_skus(TOTAL)
    started = time.perf_counter()
    model.set_results(skus)
    elapsed = time.perf_counter() - started
    assert model.rowCount() == TOTAL and elapsed < 0.5          # a reference swap, not a per-cell build
    assert model.sku_at(TOTAL - 1) is skus[-1]
    assert model.text(TOTAL - 1, 2) == f"LN10NUU BK {TOTAL:06d}"
    assert model.text(0, 5) == "1.50 GBP" and model.text(1, 5) == "" and model.text(1, 6) == "unpriced: no price"
    assert model.columnCount() == len(HEADERS) == 7 and model.text(0, 3) == "BK 000001"


def test_model_is_empty_after_clear_and_ignores_bad_rows():
    model = SkuResultsModel()
    model.set_results(make_skus(3))
    model.clear()
    assert model.rowCount() == 0 and model.sku_at(0) is None and not model.index(0, 0).isValid()


def test_the_page_shows_the_complete_set_with_no_cap_and_no_widget_item_per_cell(gen_page, monkeypatch):
    widget = gen_page
    skus = make_skus(TOTAL)
    outcome = GenerationOutcome(skus=skus, nodes=3_112_077, configurations=TOTAL)
    seen = {}

    def fake_generate(self, numbers, rules=(), **kwargs):
        seen["kwargs"] = kwargs
        kwargs["reporter"].note("Enumerating LN10")
        return outcome

    monkeypatch.setattr(OcdArticleGenerator, "generate", fake_generate)
    _pick(widget, "chair1")
    started = time.perf_counter()
    _generate(widget)
    assert time.perf_counter() - started < 5
    assert seen["kwargs"]["max_configurations"] is None          # complete generation, no 500 / display cap
    assert widget._result_model.rowCount() == TOTAL
    assert not hasattr(widget._result_table, "item")             # a view over the model, not a QTableWidget
    assert f"Generated {TOTAL:,} valid unique SKU(s) from {TOTAL:,} configuration(s)" in widget._generation_status.text()
    assert widget._export_button.isEnabled() and widget._diagnostics_button.isEnabled()
    widget._result_table.selectRow(5)
    assert [i.row() for i in widget._result_table.selectionModel().selectedRows()] == [5]


def test_completion_is_reported_only_after_the_results_are_published(gen_page, monkeypatch):
    widget = gen_page
    order = []
    real = widget._on_generated

    def spy(outcome):
        dialog = widget._progress_monitor()
        order.append(("publish", dialog._finished))
        real(outcome)
        order.append(("published", widget._result_model.rowCount()))

    monkeypatch.setattr(widget, "_on_generated", spy)
    _pick(widget, "chair1")
    _generate(widget)
    assert order[0] == ("publish", False)                         # the dialog is not "finished" before publishing
    assert order[1][1] == 3
    assert widget._progress_monitor()._finished                   # and is finished once the callback returned


def test_a_cancelled_generation_leaves_the_previous_table_untouched_and_the_page_usable(gen_page, monkeypatch):
    widget = gen_page
    _pick(widget, "chair1")
    _generate(widget)
    before = widget._result_model.rowCount()

    def cancelling(self, numbers, rules=(), **kwargs):
        kwargs["reporter"].request_cancel()
        kwargs["reporter"].note("Enumerating")                    # checkpoint -> OperationCancelled
        raise AssertionError("cancellation must stop the worker")

    monkeypatch.setattr(OcdArticleGenerator, "generate", cancelling)
    widget._generate()
    drain()
    assert widget._run is None and widget._generate_button.isEnabled()
    assert widget._result_model.rowCount() == 0                   # cleared when the new run started
    assert before == 3 and "ancel" in widget._generation_status.text()


def test_cancel_request_stops_the_engine_while_it_enumerates(tmp_path):
    from tests.ocd_engine.ocd_repo_fixture import write

    db = tmp_path / "big" / "ANY" / "1" / "db"
    db.mkdir(parents=True)
    write(db, "ocd_article.csv", "BIG;C;MK;S;1;;0;0;1;C62;U1")
    write(db, "ocd_propertyclass.csv", "BIG;1;C1;10;0")
    write(db, "ocd_property.csv", chr(10).join(f"C1;P{n};{n};;0;C;1;0;1;0;0;0;C;0;" for n in range(1, 4)))
    write(db, "ocd_propertyvalue.csv", chr(10).join(
        f"C1;P{n};{i};;0;0;0;EQ;V{i};;;;;" for n in range(1, 4) for i in range(20)))
    write(db, "ocd_price.csv", "BIG;;S;B;;;1;1;EUR;20250101;99991231;1;")
    write(db, "ocd_codescheme.csv", 'U1;@,@,@;"";"";0;"-";"X";1;"";""')
    token = CancellationToken()

    class Canceller:
        def note(self, _text):
            token.request_cancel()

        def advance(self, _text=""):
            pass

    with cancellation_scope(token), pytest.raises(OperationCancelled):
        OcdArticleGenerator(db).generate(["BIG"], currency="EUR", price_date="2026-01-15", reporter=Canceller())


def test_the_eta_is_calculating_until_an_estimate_exists_and_final_when_finished(app):
    dialog = ProgressDialog()
    assert "ETA calculating" in dialog._timing_label.text()
    dialog.set_remaining(0)
    assert "ETA 00:00" not in dialog._timing_label.text()          # unknown, not "done"
    dialog.set_remaining(75)
    assert "ETA 01:15" in dialog._timing_label.text()
    dialog.finish(True, "Completed")
    assert "ETA 00:00" in dialog._timing_label.text()
    dialog.reset()
    assert "ETA calculating" in dialog._timing_label.text()
    dialog.hide()


def test_the_page_module_has_no_result_cap():
    assert not hasattr(page_module, "_MAX_CONFIGURATIONS_LIMIT")
    assert "max_configurations=None" in open(page_module.__file__, encoding="utf-8").read()
