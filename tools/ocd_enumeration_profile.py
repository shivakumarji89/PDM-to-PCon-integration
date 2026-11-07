"""Measure where OCD SKU-generation time goes for one article, on the real repository data.

Nothing in ``services/`` is modified: the engine/generator methods are wrapped from outside, so the
result set is the production code's own. Run it with the same article and options for every
comparison; the SKU digest printed at the end must be identical between runs.

    python -I tools/ocd_enumeration_profile.py bay_work_pod PEP100 --json out.json
    python -I tools/ocd_enumeration_profile.py bay_work_pod PEP100 --plain     # no wrappers (overhead check)
    python -I tools/ocd_enumeration_profile.py bay_work_pod PEP100 --reporter real --max-seconds 120

Phases (inclusive wall time, perf_counter):
  enumerate     time inside ``engine.enumerate()`` next() calls = the depth-first walk
  finalize      ``engine.finalize`` per complete configuration (computed props, verify, varconds)
  encode        ``CodeSchemeEncoder.encode`` (final article number)
  price         ``PriceCalculator.price_resolved`` (cache misses only)
  sku_build     ``OcdArticleGenerator._sku`` + ``ResolvedConfiguration.of`` + dedup bookkeeping (rest)
  progress      ``reporter.note`` calls (the only UI-facing call from the worker)
Walk internals (inside ``enumerate``): ``_is_hidden``, ``_candidates`` (cache hit/miss and the
``_filter_values`` it falls back to), ``_early_constraints_ok``.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from services.ocd_engine import configuration_engine as ce  # noqa: E402
from services.ocd_engine import generator as gen  # noqa: E402
from services.ocd_engine.codescheme_engine import CodeSchemeEncoder  # noqa: E402
from services.ocd_engine.computed_property_engine import ComputedPropertyEngine  # noqa: E402
from services.ocd_engine.varcond_engine import VarcondEngine  # noqa: E402

REAL_OCD_ROOT = "C:/HermanMillerOFMLSVN/Staging/HermanMiller/_repository/hmx"
clock = time.perf_counter


class Phase:
    __slots__ = ("seconds", "calls")

    def __init__(self) -> None:
        self.seconds = 0.0
        self.calls = 0


PHASES: dict[str, Phase] = defaultdict(Phase)
DEPTH_VISITS: Counter = Counter()          # property name -> nodes that evaluated it
DEPTH_BRANCH: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])   # name -> [calls, sum(len), max(len)]
CACHE = Counter()                          # candidate cache hit / miss
SERIES: list[tuple] = []                   # (elapsed, finalize calls, nodes, skus-so-far proxy, bucket finalize s)
LEAVES: list[tuple] = []                   # (finalize seconds, {property: value}) per complete configuration
SERIES_EVERY = 2000


def timed(name: str, fn):
    phase = PHASES[name]

    def wrapper(*args, **kwargs):
        t = clock()
        try:
            return fn(*args, **kwargs)
        finally:
            phase.seconds += clock() - t
            phase.calls += 1
    return wrapper


def timed_iter(name: str, make_iter):
    """Time only the work done inside the generator, not the consumer between ``next`` calls."""
    phase = PHASES[name]

    def wrapper(*args, **kwargs):
        it = make_iter(*args, **kwargs)
        while True:
            t = clock()
            try:
                item = next(it)
            except StopIteration:
                phase.seconds += clock() - t
                return
            phase.seconds += clock() - t
            phase.calls += 1
            yield item
    return wrapper


def instrument(max_seconds: float | None, started: list[float]) -> None:
    Engine = ce.ConfigurationEngine
    orig_enumerate = Engine.enumerate
    Engine.enumerate = lambda self, *a, **k: timed_iter("enumerate", orig_enumerate)(self, *a, **k)
    orig_finalize = Engine.finalize
    bucket = [0.0]

    def finalize(self, assignments, **kwargs):
        t = clock()
        try:
            return orig_finalize(self, assignments, **kwargs)
        finally:
            dt = clock() - t
            phase = PHASES["finalize"]
            phase.seconds += dt
            phase.calls += 1
            bucket[0] += dt
            LEAVES.append((dt, tuple((a.prop.name, a.value.value if a.value is not None else None)
                                     for a in assignments if not a.hidden)))
            if phase.calls % SERIES_EVERY == 0:
                SERIES.append((round(clock() - started[0], 2), phase.calls, self.stats.nodes, round(bucket[0], 3)))
                bucket[0] = 0.0
    Engine.finalize = finalize
    VarcondEngine.run = timed("finalize.varcond", VarcondEngine.run)
    ComputedPropertyEngine.run = timed("finalize.computed", ComputedPropertyEngine.run)
    Engine._verify = timed("finalize.verify", Engine._verify)
    Engine._early_constraints_ok = timed("walk.early_constraints", Engine._early_constraints_ok)
    Engine._filter_values = timed("walk.filter_values", Engine._filter_values)

    orig_hidden = Engine._is_hidden

    def hidden(self, dim, ctx):
        DEPTH_VISITS[dim.name] += 1
        t = clock()
        try:
            return orig_hidden(self, dim, ctx)
        finally:
            PHASES["walk.is_hidden"].seconds += clock() - t
            PHASES["walk.is_hidden"].calls += 1
    Engine._is_hidden = hidden

    orig_candidates = Engine._candidates

    def candidates(self, dim, ctx):
        misses = PHASES["walk.filter_values"].calls
        t = clock()
        try:
            out = orig_candidates(self, dim, ctx)
        finally:
            PHASES["walk.candidates"].seconds += clock() - t
            PHASES["walk.candidates"].calls += 1
        CACHE["miss" if PHASES["walk.filter_values"].calls != misses else "hit"] += 1
        row = DEPTH_BRANCH[dim.name]
        row[0] += 1
        row[1] += len(out)
        row[2] = max(row[2], len(out))
        return out
    Engine._candidates = candidates

    CodeSchemeEncoder.encode = timed("encode", CodeSchemeEncoder.encode)
    gen.PriceCalculator.price_resolved = timed("price", gen.PriceCalculator.price_resolved)
    gen.ResolvedConfiguration.of = staticmethod(timed("sku_build.resolved", gen.ResolvedConfiguration.of))
    gen.OcdArticleGenerator._sku = staticmethod(timed("sku_build.sku", gen.OcdArticleGenerator._sku))
    if max_seconds is not None:
        orig_node = Engine._is_hidden

        def deadline(self, dim, ctx):
            if clock() - started[0] > max_seconds:
                self.stats.truncated, self.stats.reason = True, f"profile deadline {max_seconds}s"
            return orig_node(self, dim, ctx)
        Engine._is_hidden = deadline


class CountingReporter:
    """Plain reporter: counts note() calls and the time spent in them (no Qt)."""

    def __init__(self) -> None:
        self.notes = 0

    def note(self, _text):
        t = clock()
        self.notes += 1
        PHASES["progress"].seconds += clock() - t
        PHASES["progress"].calls += 1

    def advance(self, *_a):
        pass


def make_real_reporter():
    """The production ProgressReporter (signals with no receivers); isolates its own cost from the GUI's."""
    from PySide6.QtCore import QCoreApplication
    from core.progress import ProgressReporter
    QCoreApplication.instance() or QCoreApplication([])
    reporter = ProgressReporter()
    reporter.begin(1, title="profile")
    reporter.note = timed("progress", reporter.note)
    return reporter


def leaf_cost() -> dict:
    """Mean finalize ms per value of each property, to see whether any choice drives the per-leaf cost."""
    if not LEAVES:
        return {}
    times = sorted(t for t, _ in LEAVES)
    n = len(times)
    by_value: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(lambda: [0.0, 0]))
    for t, items in LEAVES:
        for name, value in items:
            cell = by_value[name][str(value)]
            cell[0] += t
            cell[1] += 1
    return {
        "leaves": n,
        "msMin": round(1000 * times[0], 2), "msMedian": round(1000 * times[n // 2], 2),
        "msP95": round(1000 * times[int(n * 0.95)], 2), "msMax": round(1000 * times[-1], 2),
        "meanMsByPropertyValue": {name: {v: round(1000 * c[0] / c[1], 2) for v, c in vals.items()}
                                  for name, vals in by_value.items() if len(vals) > 1},
    }


def full_digest(outcome) -> str:
    """Every field of every SKU, in order: values, variant conditions, pricing factors, price, status, message."""
    h = hashlib.sha256()
    for s in outcome.skus:
        h.update((repr(s) + chr(10)).encode())
    return h.hexdigest()


def peak_memory_mb() -> float | None:
    """Peak working set of this process (Windows ``GetProcessMemoryInfo``); ``None`` elsewhere."""
    try:
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        counters = Counters()
        counters.cb = ctypes.sizeof(Counters)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if not kernel32.K32GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            return None
        return round(counters.PeakWorkingSetSize / 1048576, 1)
    except Exception:
        return None


def digest(outcome) -> str:
    h = hashlib.sha256()
    for s in outcome.skus:       # order-sensitive on purpose: ordering is part of the contract
        h.update(f"{s.final_article}|{s.variant_code}|{s.ofml_varcode}|{s.price}|{s.currency}|{s.status}\n".encode())
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("range")
    ap.add_argument("article")
    ap.add_argument("--root", default=REAL_OCD_ROOT)
    ap.add_argument("--date", default="2026-11-04")
    ap.add_argument("--currency", default="EUR", help="does not affect enumeration")
    ap.add_argument("--plain", action="store_true", help="no wrappers: wall time only, for the overhead check")
    ap.add_argument("--reporter", choices=["count", "real", "none"], default="count")
    ap.add_argument("--no-price-cache", action="store_true", help="evaluate every price relation for every configuration")
    ap.add_argument("--verify-every", type=int, default=0, help="re-evaluate every Nth price-cache hit and raise on a difference")
    ap.add_argument("--max-seconds", type=float, default=None, help="stop the walk early (result is then partial)")
    ap.add_argument("--json", default="")
    args = ap.parse_args()

    db = Path(args.root) / args.range / "ANY" / "1" / "db"
    generator = gen.OcdArticleGenerator(db)
    t0 = clock()
    _ = generator.dataset
    load_s = clock() - t0
    started = [clock()]
    if not args.plain:
        instrument(args.max_seconds, started)
    reporter = {"count": CountingReporter, "real": make_real_reporter, "none": lambda: None}[args.reporter]()

    started[0] = clock()
    options = {}
    if "price_relation_cache" in inspect.signature(generator.generate).parameters:   # absent in the original code
        options = {"price_relation_cache": not args.no_price_cache, "price_cache_verify_every": args.verify_every}
    outcome = generator.generate([args.article], (), currency=args.currency, price_date=args.date,
                                 max_configurations=None, reporter=reporter, **options)
    total = clock() - started[0]

    enum_s = PHASES["enumerate"].seconds
    result = {
        "range": args.range, "article": args.article, "plain": args.plain, "reporter": args.reporter,
        "dataLoadSeconds": round(load_s, 3), "generateSeconds": round(total, 3),
        "skus": len(outcome.skus), "configurations": outcome.configurations, "nodes": outcome.nodes,
        "invalid": outcome.invalid, "duplicates": outcome.duplicates, "pruned": outcome.pruned,
        "priceEvaluations": outcome.price_evaluations, "priceReused": outcome.price_reused,
        "truncated": outcome.truncated, "skuDigest": digest(outcome), "fullSkuDigest": full_digest(outcome),
        "priceRelationCache": bool(options) and not args.no_price_cache, "verifyEvery": args.verify_every,
        "priceRelationStats": getattr(outcome, "price_relation_stats", {}), "peakWorkingSetMB": peak_memory_mb(),
        "sortedSkuDigest": hashlib.sha256("\n".join(sorted(s.final_article for s in outcome.skus)).encode()).hexdigest(),
    }
    if not args.plain:
        top = {k: v for k, v in PHASES.items() if not k.startswith(("walk.", "sku_build."))}
        accounted = sum(p.seconds for p in top.values() if p is not PHASES["progress"])
        result["phases"] = {k: {"seconds": round(v.seconds, 3), "calls": v.calls,
                                "pctOfTotal": round(100 * v.seconds / total, 1) if total else 0,
                                "usPerCall": round(1e6 * v.seconds / v.calls, 1) if v.calls else 0}
                            for k, v in sorted(PHASES.items())}
        result["unaccountedSeconds"] = round(total - accounted - PHASES["sku_build.sku"].seconds
                                             - PHASES["sku_build.resolved"].seconds, 3)
        result["candidateCache"] = dict(CACHE)
        result["enumerateSecondsWalkOnly"] = round(enum_s, 3)
        result["perProperty"] = {
            name: {"visits": DEPTH_VISITS[name], "candidateCalls": row[0],
                   "avgBranch": round(row[1] / row[0], 2) if row[0] else 0, "maxBranch": row[2]}
            for name, (row) in DEPTH_BRANCH.items()
        }
        result["propertyOrderBySeen"] = list(DEPTH_VISITS)
        result["finalizeSeries"] = [{"elapsed": a, "finalizeCalls": b, "nodes": c, "bucketFinalizeSeconds": d,
                                     "msPerLeaf": round(1000 * d / SERIES_EVERY, 2)} for a, b, c, d in SERIES]
        result["leafCost"] = leaf_cost()
    if hasattr(reporter, "notes"):
        result["progressNotes"] = reporter.notes
    text = json.dumps(result, indent=2)
    print(text)
    if args.json:
        Path(args.json).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
