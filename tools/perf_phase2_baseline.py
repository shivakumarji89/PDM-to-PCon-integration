"""Micro-benchmarks for the Phase 2 work (navigation refresh, background exports, Development VARCOND).

Offline and non-destructive: synthetic snapshots, an offscreen Qt application, fake PDM repositories and a
scratch MDB in a temporary folder. No live PDM connection is opened.

    python tools/perf_phase2_baseline.py --only navigation --articles 2000 --prices 20000
    python tools/perf_phase2_baseline.py --only exports,varcond --out phase2.json

Sections: ``navigation``, ``exports``, ``varcond``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def bench_navigation(articles: int, prices: int, order=("legacy", "new")):
    from PySide6.QtWidgets import QApplication
    from core.enums import WorkflowStep
    from models.price_record import PriceRecord
    from tests.test_navigation_refresh import (
        PAGES, _build, _count_refreshes, _legacy_activate,
    )

    QApplication.instance() or QApplication([])
    rows = []
    steps = (WorkflowStep.PRICING, WorkflowStep.CLASS_CREATION, WorkflowStep.ARTICLES,
             WorkflowStep.REVIEW, WorkflowStep.ENGINEERING, WorkflowStep.TEXT, WorkflowStep.RELATION)
    for step in steps:
        entry = {"page": step.name, "articles": articles}
        for label in order:
            ctx, _stack, host, pages = _build(count=articles, steps=(step, WorkflowStep.PRICING_RELATION))
            ctx.active_snapshot.price_records = [
                PriceRecord(is_global=False, article_code=f"DSK{i % 500:03d}", variant_condition=f"{i} 1=X",
                            level="X", value=float(i), currency="GBP")
                for i in range(prices)
            ]
            host.activate(WorkflowStep.PRICING_RELATION)          # make ``step`` a hidden page first
            counts = _count_refreshes(pages)
            started = time.perf_counter()
            (_legacy_activate if label == "legacy" else (lambda h, s: h.activate(s)))(host, step)
            entry[f"{label}_s"] = round(time.perf_counter() - started, 3)
            entry[f"{label}_refreshes"] = counts[step]
        rows.append(entry)
        print("navigation", entry, flush=True)
    return rows


def bench_exports(xocd_articles: int, excel_articles: int):
    """How long the GUI thread is blocked by an export: synchronous service call (what the UI used to
    do) vs. the background runner (copy + hand-off) with the worst gap between 10 ms timer ticks."""
    import copy
    import tempfile
    from PySide6.QtCore import QCoreApplication, QSettings, QTimer
    from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox
    from core.modules import WorkbenchModule
    from models.product import Product
    from services.snapshot_excel_export_service import SnapshotExcelExportService
    from tests.perf_synthetic import build_class_creation_snapshot

    app = QApplication.instance() or QApplication([])
    tmp = Path(tempfile.mkdtemp(prefix="perf_exports_"))
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp / "settings"))
    from ui.main_window import MainWindow

    window = MainWindow()
    window._active_module = WorkbenchModule.DEVELOPMENT
    ctx = window._context
    rows = []

    def load(count):
        snapshot = build_class_creation_snapshot(count, structures=3, members_per_family=200)
        snapshot.product = Product(id="p1", code="DSK", name="Desk", category="Desks", range_name="Desk range")
        ctx.register_pdm_snapshot(snapshot)
        ctx.activate_snapshot_source("pdm")
        ctx.engineering_initialization_service.initialize(snapshot)
        ctx.engineering_reduction_service.materialize_class_creation_article_sets(snapshot)
        return snapshot

    def measure_async(start, finished):
        gaps, last = [], [time.perf_counter()]
        timer = QTimer()

        def tick():
            now = time.perf_counter()
            gaps.append(now - last[0])
            last[0] = now

        timer.timeout.connect(tick)
        timer.start(10)
        t0 = time.perf_counter()
        start()
        returned = time.perf_counter() - t0
        while not finished():
            QCoreApplication.processEvents()
            time.sleep(0.002)
        total = time.perf_counter() - t0
        timer.stop()
        return returned, max(gaps) if gaps else 0.0, total

    # -- XOCD ---------------------------------------------------------------------------
    snapshot = load(xocd_articles)
    window._xocd_publish_path = tmp / "xocd"
    window._xocd_publish_service = type("S", (), {"status_args": staticmethod(lambda p: ["x"])})()
    window._start_xocd_svn_process = lambda args: None
    window._xocd_publish_failed = lambda m: print("xocd failed", m)
    window._xocd_publish_progress = type("D", (), {"set_files": lambda s, n: None, "append_output": lambda s, t: None,
                                                    "set_stage": lambda s, *a: None, "set_busy": lambda s, *a: None})()
    t0 = time.perf_counter()
    ctx.xocd_export_service.export_series(snapshot, tmp / "sync", force=True)
    sync_s = time.perf_counter() - t0
    done = []
    returned, worst_gap, total = measure_async(
        lambda: window._run_xocd_export(snapshot, tmp / "async", lambda r: done.append(r), print),
        lambda: bool(done))
    rows.append({"export": "XOCD", "articles": xocd_articles, "sync_gui_blocked_s": round(sync_s, 3),
                 "async_gui_blocked_s": round(returned, 3), "async_worst_event_gap_s": round(worst_gap, 3),
                 "async_total_s": round(total, 3)})
    print("exports", rows[-1], flush=True)

    # -- Excel --------------------------------------------------------------------------
    snapshot = load(excel_articles)
    messages = []
    QMessageBox.information = staticmethod(lambda *a, **k: messages.append(a))
    QMessageBox.warning = staticmethod(lambda *a, **k: messages.append(a))
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(tmp / "async.xlsx"), ""))
    t0 = time.perf_counter()
    SnapshotExcelExportService().export(copy.deepcopy(snapshot), str(tmp / "sync.xlsx"))
    sync_s = time.perf_counter() - t0
    returned, worst_gap, total = measure_async(window._on_export_snapshot_excel, lambda: bool(messages))
    rows.append({"export": "Excel", "articles": excel_articles, "sync_gui_blocked_s": round(sync_s, 3),
                 "async_gui_blocked_s": round(returned, 3), "async_worst_event_gap_s": round(worst_gap, 3),
                 "async_total_s": round(total, 3)})
    print("exports", rows[-1], flush=True)
    window.close()
    return rows


def bench_varcond(latency_ms: float):
    """Development VARCOND against a fake PDM with a *simulated* per-query latency (no real PDM is used).

    A: relation export, option-increment queries and wall time with the original per-occurrence lookup
       (emulated with a cache that never stores) vs the memoised lookup.
    B: typing 7 characters into the filter: generations started and time the GUI thread is blocked,
       synchronous per keystroke (the original) vs debounced on a worker."""
    from PySide6.QtCore import QCoreApplication, QSettings, QTimer
    from PySide6.QtWidgets import QApplication
    import repositories.pdm_repository as repo_module
    from services.varcond_service import VarCondService
    from tests import varcond_fakes as fakes
    from tests.test_varcond_background import _reference_relation_objects_for_export
    from ui.dialogs.varcond_generation_dialog import VarCondGenerationPanel

    QApplication.instance() or QApplication([])
    delay = latency_ms / 1000.0

    class SlowRepo(fakes.FakeLiveRepo):
        def _execute(self, *a, **k):
            time.sleep(delay)
            return super()._execute(*a, **k)

        def fetch_item_components(self, *a, **k):
            time.sleep(delay)
            return super().fetch_item_components(*a, **k)

        def fetch_category_master_notes(self, *a, **k):
            time.sleep(delay)
            return super().fetch_category_master_notes(*a, **k)

        def fetch_item_option_increments(self, *a, **k):
            time.sleep(delay)
            return super().fetch_item_option_increments(*a, **k)

    repo_module.PDMRepository = SlowRepo

    class NeverStores(dict):
        def __setitem__(self, key, value):
            pass

    rows = []
    panel = VarCondGenerationPanel(fakes.build_context())
    real_live = VarCondService.generate_live
    entry = {"section": "export", "simulated_latency_ms": latency_ms}
    for label in ("original_lookup", "memoised_lookup"):
        VarCondService.generate_live = (
            (lambda self, *a, **k: real_live(self, *a, increment_cache=NeverStores(), **k))
            if label == "original_lookup" else real_live)
        fakes.FakeLiveRepo.calls = []
        t0 = time.perf_counter()
        if label == "original_lookup":
            _reference_relation_objects_for_export(panel)
        else:
            panel.relation_objects_for_export()
        entry[label] = {"increment_queries": fakes.increment_queries(),
                        "total_queries": len(fakes.FakeLiveRepo.calls),
                        "seconds": round(time.perf_counter() - t0, 3)}
    VarCondService.generate_live = real_live
    rows.append(entry)
    print("varcond", entry, flush=True)

    # B: typing in the filter
    panel = VarCondGenerationPanel(fakes.build_context())
    panel._relations.setCurrentRow(0)
    keys = [text for text in ("G", "GE", "GES", "GESC", "GESCR", "GESCRN", "GESCRNN")]
    started = []
    VarCondService.generate_live = lambda self, *a, **k: (started.append(1), real_live(self, *a, **k))[1]
    t0 = time.perf_counter()
    # original behaviour: every keystroke regenerated the selected relation synchronously on the GUI thread
    for _text in keys:
        panel._relations.setCurrentRow(0)
        real_live(VarCondService(panel._context), ["GESCRNNU.105508F"])
    sync_blocked = time.perf_counter() - t0
    started.clear()
    gaps, last = [], [time.perf_counter()]
    timer = QTimer()
    timer.timeout.connect(lambda: (gaps.append(time.perf_counter() - last[0]), last.__setitem__(0, time.perf_counter())))
    timer.start(10)
    t0 = time.perf_counter()
    for text in keys:
        panel._filter.setText(text)
    typing_s = time.perf_counter() - t0
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline and not (started and panel._live_task is None):
        QCoreApplication.processEvents()
        time.sleep(0.002)
    timer.stop()
    VarCondService.generate_live = real_live
    entry = {"section": "typing", "simulated_latency_ms": latency_ms, "keystrokes": len(keys),
             "original_generations": len(keys), "original_gui_blocked_s": round(sync_blocked, 3),
             "new_generations": len(started), "new_gui_blocked_s": round(typing_s, 3),
             "new_worst_event_gap_s": round(max(gaps) if gaps else 0.0, 3)}
    rows.append(entry)
    print("varcond", entry, flush=True)
    return rows


SECTIONS = ("navigation", "exports", "varcond")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", default=",".join(SECTIONS))
    parser.add_argument("--articles", type=int, default=2000)
    parser.add_argument("--prices", type=int, default=20000)
    parser.add_argument("--xocd-articles", type=int, default=3000)
    parser.add_argument("--excel-articles", type=int, default=300)
    parser.add_argument("--latency-ms", type=float, default=20.0, help="simulated PDM latency per query (varcond)")
    parser.add_argument("--first", default="legacy", choices=("legacy", "new"), help="which variant runs first")
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    result = {"sections": {}}
    runners = {"varcond": lambda: bench_varcond(args.latency_ms),
               "exports": lambda: bench_exports(args.xocd_articles, args.excel_articles),
               "navigation": lambda: bench_navigation(args.articles, args.prices, ("legacy", "new") if args.first == "legacy" else ("new", "legacy"))}
    for name in [s for s in args.only.split(",") if s]:
        if name in runners:
            result["sections"][name] = runners[name]()
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
