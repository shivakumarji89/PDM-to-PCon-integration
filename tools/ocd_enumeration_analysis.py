"""Two read-only analyses that back ``docs/04_Reference/pCon/Enumeration_Performance_PEP100.md``.

    python -I tools/ocd_enumeration_analysis.py price-inputs bay_work_pod PEP100
        How many distinct input tuples the price-domain relations read across all configurations
        (an upper bound on the work a per-input cache would still have to do). Walk only, ~2 s.

    python -I tools/ocd_enumeration_analysis.py slices bay_work_pod PEP100 --buckets 2 6 14 21 22
        Times ``finalize`` on fixed slices of the configuration list, interleaved and repeated in one
        process, to separate per-configuration cost from machine noise.

Neither changes any engine code or output.
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from services.ocd_engine import configuration_engine as ce  # noqa: E402
from services.ocd_engine import generator as gen  # noqa: E402
from services.ocd_engine import model as m  # noqa: E402
from services.ocd_engine import relation_parser as rp  # noqa: E402

REAL_OCD_ROOT = "C:/HermanMillerOFMLSVN/Staging/HermanMiller/_repository/hmx"


def load(args):
    generator = gen.OcdArticleGenerator(Path(args.root) / args.range / "ANY" / "1" / "db")
    model = generator._build_model(args.article)
    return model, ce.ConfigurationEngine(model)


def price_inputs(args) -> None:
    model, engine = load(args)
    relations = [r for r in model.article_relations if r.rel_type == m.ACTION and r.domain.upper() == "P"]
    props = {p.name_upper for p in model.properties}
    reads = []
    for relation in relations:
        compiled = rp.compile_relation(relation.rel_type, relation.text)
        reads.append(sorted({ref.rsplit(".", 1)[-1].upper() for ref in compiled.refs} & props))
    union = sorted(set().union(*reads)) if reads else []
    seen_union, seen_each = set(), [set() for _ in reads]
    leaves = 0
    for config in engine.enumerate():
        leaves += 1
        values = {a.prop.name_upper: (a.value.value if a.value is not None and not a.hidden else None)
                  for a in config.assignments}
        seen_union.add(tuple(values.get(k) for k in union))
        for seen, keys in zip(seen_each, reads):
            seen.add(tuple(values.get(k) for k in keys))
    sizes = [len(s) for s in seen_each]
    print(f"article-level price relations: {len(relations)}")
    print(f"properties they read ({len(union)} of {len(props)}): {', '.join(union)}")
    print(f"unread by any price relation: {', '.join(sorted(props - set(union)))}")
    print(f"configurations: {leaves:,}; distinct union-input tuples: {len(seen_union):,} "
          f"({leaves / max(1, len(seen_union)):.1f}x redundancy)")
    print(f"per-relation distinct inputs: min {min(sizes):,} median {statistics.median(sizes):,.0f} max {max(sizes):,}")


def slices(args) -> None:
    _, engine = load(args)
    leaves = [c.assignments for c in engine.enumerate()]
    size, rounds = args.slice, args.rounds
    for assignments in leaves[:20]:       # warm the relation compile cache so round 1 is not inflated
        engine.finalize(assignments)
    results = {b: [] for b in args.buckets}
    for _ in range(rounds):
        for bucket in args.buckets:
            start = bucket * args.bucket_size + args.bucket_size // 2
            began = time.perf_counter()
            for assignments in leaves[start:start + size]:
                engine.finalize(assignments)
            results[bucket].append(1000 * (time.perf_counter() - began) / size)
    print(f"{len(leaves):,} configurations; {size} per slice, {rounds} interleaved rounds")
    for bucket, values in results.items():
        print(f"bucket {bucket:>3}: " + " ".join(f"{v:5.1f}" for v in values) +
              f"  median {statistics.median(values):5.1f} ms/configuration")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["price-inputs", "slices"])
    ap.add_argument("range")
    ap.add_argument("article")
    ap.add_argument("--root", default=REAL_OCD_ROOT)
    ap.add_argument("--buckets", type=int, nargs="*", default=[2, 6, 14, 21, 22])
    ap.add_argument("--bucket-size", type=int, default=2000)
    ap.add_argument("--slice", type=int, default=250)
    ap.add_argument("--rounds", type=int, default=3)
    args = ap.parse_args()
    {"price-inputs": price_inputs, "slices": slices}[args.mode](args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
