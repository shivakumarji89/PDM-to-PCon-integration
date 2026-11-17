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


SECTIONS = ("navigation", "exports", "varcond")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", default=",".join(SECTIONS))
    parser.add_argument("--articles", type=int, default=2000)
    parser.add_argument("--prices", type=int, default=20000)
    parser.add_argument("--first", default="legacy", choices=("legacy", "new"), help="which variant runs first")
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    result = {"sections": {}}
    runners = {"navigation": lambda: bench_navigation(args.articles, args.prices, ("legacy", "new") if args.first == "legacy" else ("new", "legacy"))}
    for name in [s for s in args.only.split(",") if s]:
        if name in runners:
            result["sections"][name] = runners[name]()
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
