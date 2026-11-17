"""Reproducible micro-benchmarks for the Phase 1 performance work.

Everything here is offline and non-destructive: synthetic snapshots, an offscreen Qt
application, in-memory fake databases, and a scratch MDB created in a temporary folder.
No PDM connection is opened and no real MDB is touched.

Usage (repo root)::

    python tools/perf_phase1_baseline.py --out before.json
    python tools/perf_phase1_baseline.py --only materialize,articles --sizes 1000,3000
    python tools/perf_phase1_baseline.py --only bridge --bridge-rows 5000,20000,50000

Sections: ``materialize``, ``articles``, ``classcreation``, ``syteline``, ``json``, ``bridge``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from tests.perf_synthetic import (  # noqa: E402
    build_class_creation_snapshot,
    canonical_article_sets,
    digest,
    reduction_service,
)


def _timed(fn, repeat: int = 1):
    best = None
    result = None
    for _ in range(repeat):
        started = time.perf_counter()
        result = fn()
        elapsed = time.perf_counter() - started
        best = elapsed if best is None else min(best, elapsed)
    return best, result


def _peak_mb(fn) -> float:
    tracemalloc.start()
    try:
        fn()
        return tracemalloc.get_traced_memory()[1] / 1e6
    finally:
        tracemalloc.stop()


# -- materialize_class_creation_article_sets ---------------------------------
def bench_materialize(sizes, structures=1):
    rows = []
    for n in sizes:
        snapshot = build_class_creation_snapshot(n, structures=structures)
        service = reduction_service()
        seconds, sets = _timed(lambda: service.materialize_class_creation_article_sets(snapshot))
        rows.append({
            "articles": n, "structures": structures, "seconds": round(seconds, 3),
            "sets": len(sets), "digest": digest(canonical_article_sets(snapshot, sets))[:16],
        })
        print("materialize", rows[-1], flush=True)
    small = build_class_creation_snapshot(min(sizes), structures=structures)
    svc = reduction_service()
    rows.append({"peak_mb_tracemalloc": round(_peak_mb(
        lambda: svc.materialize_class_creation_article_sets(small)), 2), "articles": min(sizes)})
    return rows


# -- Qt pages -----------------------------------------------------------------
def _app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _page_context(n, **kw):
    from core.application_context import ApplicationContext
    ctx = ApplicationContext()
    snapshot = build_class_creation_snapshot(n, **kw)
    ctx.register_pdm_snapshot(snapshot)
    ctx.activate_snapshot_source("pdm")
    ctx.engineering_reduction_service.materialize_class_creation_article_sets(snapshot)
    return ctx, snapshot


def bench_articles(sizes, structures=3):
    from core.modules import WorkbenchModule
    from ui.pages.articles_page import ArticlesPage
    _app()
    rows = []
    for n in sizes:
        ctx, snapshot = _page_context(n, structures=structures)
        page = ArticlesPage(ctx)
        page._active_module = WorkbenchModule.DEVELOPMENT
        page._validate_articles = lambda: ctx.article_service.validate()
        t_collect, page_rows = _timed(page._collect_rows)
        page._rows = page_rows
        t_sets, _ = _timed(page._populate_sets)
        page._group_by_base = True
        t_group, _ = _timed(page._apply_filter)
        page._group_by_base = False
        t_lines, _ = _timed(page._apply_filter)
        page._group_by_base = True
        t_refresh, _ = _timed(page.refresh)
        rows.append({
            "articles": n, "structures": structures,
            "collect_rows_s": round(t_collect, 3), "populate_sets_s": round(t_sets, 3),
            "apply_filter_grouped_s": round(t_group, 3), "apply_filter_lines_s": round(t_lines, 3),
            "refresh_total_s": round(t_refresh, 3), "table_rows_grouped": page._table.rowCount(),
        })
        print("articles", rows[-1], flush=True)
    return rows


def bench_classcreation(sizes, width_values=90):
    from core.modules import WorkbenchModule
    from ui.pages.class_creation_page import ClassCreationPage
    _app()
    rows = []
    for n in sizes:
        ctx, snapshot = _page_context(n, structures=3, width_values=width_values)
        page = ClassCreationPage(ctx)
        page._active_module = WorkbenchModule.DEVELOPMENT
        t_refresh, _ = _timed(page.refresh)
        # Select the Width property (the master table lists one row per property).
        target = None
        for r in range(page._attr_master.rowCount()):
            item = page._attr_master.item(r, 0)
            meta = item.data(0x0100) if item is not None else None
            if meta and getattr(meta[0], "name", "") == "Width":
                target = r
                break
        t_select = None
        if target is not None:
            page._attr_master.clearSelection()
            t_select, _ = _timed(lambda: page._attr_master.selectRow(target))
        rows.append({
            "articles": n, "width_values": width_values,
            "refresh_s": round(t_refresh, 3),
            "select_width_property_s": None if t_select is None else round(t_select, 3),
            "value_rows": page._attr_values.rowCount(),
        })
        print("classcreation", rows[-1], flush=True)
    return rows


# -- SyteLine -------------------------------------------------------------------
def bench_syteline(list_sizes=(20_000, 100_000), calls=100, items=5000):
    from services.syteline_export.pipeline.netsem import list_contains
    rows = []
    for size in list_sizes:
        ints = list(range(size))
        strs = [f"{i}~{i}" for i in range(size)]
        seconds_i, _ = _timed(lambda: [list_contains(ints, -1 - k) for k in range(calls)])
        seconds_s, _ = _timed(lambda: [list_contains(strs, f"x{k}") for k in range(calls)])
        rows.append({"list_size": size, "miss_lookups": calls,
                     "int_list_s": round(seconds_i, 3), "str_list_s": round(seconds_s, 3)})
        print("syteline list", rows[-1], flush=True)
    from tests.test_syteline_pipeline_stage_p00 import ITEM_Q, make, sql_calls
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        h = make(Path(tmp), items=[{"LongItem": f"ITEM{i:06d}"} for i in range(items)])
        seconds, _ = _timed(h.p00_setup)
        rows.append({"p00_items": items, "p00_seconds": round(seconds, 4),
                     "item_query_executions": len(sql_calls(h, ITEM_Q)),
                     "arrayList23_len": len(h.v.arrayList23), "item_rows": len(h.v.item_rows)})
        for name in list(vars(h.v)):
            writer = getattr(h.v, name)
            if name.startswith("streamWriter") and hasattr(writer, "close"):
                writer.close()
        print("syteline p00", rows[-1], flush=True)
    return rows


# -- JSON cache writers --------------------------------------------------------
def bench_json(sizes):
    from services.pdm_service import PDMService
    rows = []
    for n in sizes:
        snapshot = build_class_creation_snapshot(n, structures=3, members_per_family=200)
        for family in snapshot.engineering.families:
            for member in family.members:
                member.reduced_article = "DSK"
        context = SimpleNamespace(config=SimpleNamespace(pdm_server="bench", pdm_database="bench"))
        service = PDMService(context)
        with tempfile.TemporaryDirectory() as tmp:
            service._SNAPSHOT_CACHE_DIR = Path(tmp)
            seconds, path = _timed(lambda: service.save_family_snapshot(snapshot, "bench"), repeat=3)
            size = path.stat().st_size if path else None
            parsed = json.loads(path.read_text(encoding="utf-8")) if path else {}
        rows.append({"articles": n, "save_family_snapshot_s": round(seconds, 4),
                     "file_bytes": size, "articles_in_file": len(parsed.get("articles", []))})
        print("json", rows[-1], flush=True)
    return rows


# -- MDB bridge (scratch MDB only) --------------------------------------------
_SEED_PS = r'''
param([string]$Path, [int]$Rows)
$ErrorActionPreference = "Stop"
$cat = New-Object -ComObject ADOX.Catalog
$cat.Create("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$Path;") | Out-Null
$conn = New-Object -ComObject ADODB.Connection
$conn.Open("Provider=Microsoft.ACE.OLEDB.16.0;Data Source=$Path;")
$conn.Execute("CREATE TABLE tDigit (n LONG)") | Out-Null
foreach ($i in 0..9) { $conn.Execute("INSERT INTO tDigit (n) VALUES ($i)") | Out-Null }
$conn.Execute("CREATE TABLE tBench (id LONG, code TEXT(24), descr TEXT(60), val DOUBLE, flag YESNO)") | Out-Null
$expr = "a.n + 10*b.n + 100*c.n + 1000*d.n + 10000*e.n"
$conn.Execute("INSERT INTO tBench (id, code, descr, val, flag) SELECT $expr, 'ART' & CStr($expr), 'Synthetic row ' & CStr($expr), ($expr) * 1.25, True FROM tDigit AS a, tDigit AS b, tDigit AS c, tDigit AS d, tDigit AS e WHERE ($expr) < $Rows") | Out-Null
$conn.Close()
'''


def bench_bridge(row_counts, op_counts=(50, 200, 400)):
    from services.mdb_service import MDBService
    service = MDBService.__new__(MDBService)
    if not service.is_available():
        return [{"skipped": "32-bit PowerShell / ACE bridge unavailable"}]
    import services.mdb_service as module
    rows = []
    with tempfile.TemporaryDirectory(prefix="perf_bridge_") as tmp:
        seed = Path(tmp) / "seed.ps1"
        seed.write_text(_SEED_PS, encoding="utf-8")
        mdb = Path(tmp) / "scratch.mdb"
        import subprocess
        subprocess.run([module._PS32, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(seed),
                        "-Path", str(mdb), "-Rows", str(max(row_counts))], check=True,
                       capture_output=True, text=True)
        for n in row_counts:
            sql = f"SELECT TOP {n} * FROM tBench ORDER BY id"
            seconds, data = _timed(lambda: service.read_table(mdb, sql))
            rows.append({"read_rows": n, "returned": len(data), "seconds": round(seconds, 3),
                         "first": data[0] if data else None, "last": data[-1] if data else None})
            print("bridge read", {k: v for k, v in rows[-1].items() if k not in ("first", "last")}, flush=True)
        for k in op_counts:
            ops = [{"op": "query", "sql": f"SELECT TOP 1 * FROM tBench WHERE id = {i}"} for i in range(k)]
            seconds, batch = _timed(lambda: service.execute_batch(mdb, ops))
            rows.append({"ops_in_batch": k, "ok": batch.ok, "results": len(batch.results),
                         "seconds": round(seconds, 3)})
            print("bridge ops", rows[-1], flush=True)
        # Shape probes: 0, 1 and 2 rows must come back as lists of dicts.
        for n in (0, 1, 2):
            data = service.read_table(mdb, f"SELECT TOP {n} * FROM tBench WHERE id >= 0 ORDER BY id") if n else \
                service.read_table(mdb, "SELECT * FROM tBench WHERE id < 0")
            rows.append({"shape_probe_rows": n, "returned": len(data), "type": type(data).__name__})
    return rows


SECTIONS = ("materialize", "articles", "classcreation", "syteline", "json", "bridge")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", default=",".join(SECTIONS))
    parser.add_argument("--sizes", default="1000,3000", help="article counts for the page/materialize sections")
    parser.add_argument("--bridge-rows", default="5000,20000,50000")
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    sizes = [int(v) for v in args.sizes.split(",") if v]
    wanted = [s for s in args.only.split(",") if s]
    result = {"python": sys.version.split()[0], "sections": {}}
    runners = {
        "materialize": lambda: bench_materialize(sizes, structures=1),
        "articles": lambda: bench_articles(sizes),
        "classcreation": lambda: bench_classcreation(sizes),
        "syteline": lambda: bench_syteline(),
        "json": lambda: bench_json(sizes),
        "bridge": lambda: bench_bridge([int(v) for v in args.bridge_rows.split(",") if v]),
    }
    for name in wanted:
        result["sections"][name] = runners[name]()
    text = json.dumps(result, indent=2, default=str)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
