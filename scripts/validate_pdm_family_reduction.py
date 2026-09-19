"""Read-only live validation of reduction against the legacy PDM boundary.

Three modes:

--snapshot <name.json>
                THE PRODUCTION FLOW. Reads a cached family snapshot from
                ``cache/pdm_snapshots`` to recover WHICH Products that family
                held, then loads those Products from PDM through the real
                production loader (``PDMService.load_family``), lets the
                existing reduction engine derive the candidate families exactly
                as the application does, and proves each derived ArticleSet
                against the real ``dbo.ProductsList``. No mapping is supplied
                from outside - every family under test is one the engine itself
                produced. This is the mode that measures production reduction.

                The cache file is NOT deserialised into a snapshot: it is a
                lossy source-data archive (``PDMService.save_family_snapshot``)
                that stores properties through ``_scalars`` - dropping each
                property's nested values - and omits
                ``product_property_value_ids`` entirely. Restoring it as a
                snapshot leaves the reduction engine with no product-to-value
                link at all, so every article collapses into ONE class with an
                empty property signature and the run measures a grouping the
                application never produces.

                Add ``--complete-ranges`` to bring every ProductRange in the
                session up to its full legacy-eligible population first.
                ``dbo.ProductsList`` filters the whole range, so a candidate
                drawn from a partly loaded range cannot be compared against it
                and is reported ``unresolved``.

--input <csv>   Validate engineering-supplied candidate families. The CSV
                must have a ``base`` column (an opaque label - any proposed
                group of ProductIds that engineering believes share one
                reduced base article) and a ``ProductId`` column. Rows with
                the same ``base`` form one candidate family. Diagnostic only:
                production reduction never takes a grouping from a file.

--discover      No dataset required. Samples real ProductRanges from the
                live PDM database and, within each, clusters ProductIds that
                already share an identical non-order-code (functional)
                ProductAttributeValues signature into candidate families.
                This produces a broad, non-dataset-specific cross-range
                validation run when no engineering-supplied dataset is
                available. Clustering is diagnostic only - it is never used
                as production reduction logic.

The ``--input`` and ``--discover`` modes exist for diagnostics only: neither
is production reduction, and neither grouping rule is ever used by the
application. Every candidate, from any mode, is proven or rejected only
through the real ``dbo.ProductsList`` procedure (see
``PDMFamilyReductionService``). No data is written to PDM.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.application_context import ApplicationContext  # noqa: E402
from models.product import Product  # noqa: E402
from services.engineering.pdm_family_reduction_service import (  # noqa: E402
    FamilyCandidate,
    PDMFamilyReductionService,
)

SNAPSHOT_CACHE = Path(__file__).resolve().parents[1] / "cache" / "pdm_snapshots"


def read_candidates_from_csv(path: Path) -> list[FamilyCandidate]:
    text = path.read_text(encoding="utf-8-sig")
    rows = csv.DictReader(text.splitlines())
    if not rows.fieldnames or "base" not in rows.fieldnames or "ProductId" not in rows.fieldnames:
        raise ValueError(
            f"Expected columns 'base' and 'ProductId'. Found: {rows.fieldnames!r}"
        )
    by_base: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        base = (row.get("base") or "").strip()
        product_id = (row.get("ProductId") or "").strip()
        if not base or not product_id:
            continue
        by_base[base].append(product_id)
    return [
        FamilyCandidate(base=base, product_ids=tuple(dict.fromkeys(ids)))
        for base, ids in by_base.items()
    ]


def discover_candidates(
    service: PDMFamilyReductionService, connection: Any, sample_ranges: int
) -> list[FamilyCandidate]:
    """Build diagnostic candidate families straight from live data.

    Samples up to ``sample_ranges`` ProductRangeIds that have more than one
    Product, then within each range groups Products whose non-order-code
    ProductAttributeValues set is byte-for-byte identical. This is a
    diagnostic seed for exercising the validator broadly; it is not a
    production grouping rule.
    """
    cursor = connection.cursor()
    cursor.execute(
        """
        SELECT TOP (?) pr.ProductRangeId
        FROM ProductRange pr WITH (NOLOCK)
        WHERE EXISTS (
            SELECT 1 FROM Product p WITH (NOLOCK)
            WHERE p.ProductRangeId = pr.ProductRangeId
            GROUP BY p.ProductRangeId
            HAVING COUNT(*) > 1
        )
        ORDER BY pr.ProductRangeId
        """,
        (sample_ranges,),
    )
    range_ids = [row[0] for row in cursor.fetchall()]

    candidates: list[FamilyCandidate] = []
    for range_id in range_ids:
        cursor.execute(
            "SELECT ProductId FROM Product WITH (NOLOCK) WHERE ProductRangeId = ?",
            (range_id,),
        )
        product_ids = [str(row[0]) for row in cursor.fetchall()]
        if len(product_ids) < 2:
            continue
        attribute_rows = service.repository.fetch_products_attributes(
            product_ids, connection=connection
        )
        functional, _configurable = service._split_attributes(product_ids, attribute_rows)
        by_signature: dict[frozenset, list[str]] = defaultdict(list)
        for product_id, values in functional.items():
            if values:
                by_signature[frozenset(values)].append(product_id)
        for signature, members in by_signature.items():
            if len(members) > 1:
                candidates.append(
                    FamilyCandidate(base=f"range{range_id}-seed{members[0]}", product_ids=tuple(members))
                )
    return candidates


def cached_family_product_ids(path: Path) -> list[str]:
    """The ProductIds a cached family snapshot covered.

    Only the article rows are read. The rest of the cache is a lossy archive
    (see the module docstring) and is deliberately not restored.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    return sorted({
        str(article.get("product_id"))
        for article in (data.get("articles") or [])
        if article.get("product_id")
    })


def validate_snapshot(
    ctx: Any, name: str, complete_ranges: bool = False
) -> tuple[list[Any], list[Any]]:
    """Run the PRODUCTION flow on a cached family's Products.

    The family's Products are loaded from PDM through the real production
    loader, the reduction engine derives the candidate families, and this
    script only asks the legacy boundary whether each derived base is
    equivalent. Nothing here supplies or repairs a grouping, and nothing is
    written back to PDM.
    """
    path = SNAPSHOT_CACHE / name if not Path(name).is_file() else Path(name)
    product_ids = cached_family_product_ids(path)
    if not product_ids:
        raise ValueError(f"{path.name} carries no articles with a product_id.")
    print(f"{path.name}: loading {len(product_ids)} product(s) from PDM...")
    # The production loader auto-saves the family cache. This script is a
    # read-only check, so the user's cached family must survive it untouched -
    # otherwise validating a family would silently replace the very file it was
    # asked to measure (and any reduction work saved in it).
    ctx.pdm_service.save_family_snapshot = lambda snapshot, family_name: None
    result = ctx.pdm_service.load_family(
        [Product(id=pid) for pid in product_ids], path.stem
    )
    if not result.ok or result.snapshot is None:
        raise RuntimeError(f"Production load failed: {result.message}")
    snapshot = result.snapshot
    ctx.snapshot_manager.load_snapshot(snapshot)
    if complete_ranges:
        completion = ctx.pdm_service.complete_product_ranges(snapshot)
        print(f"  {completion.message}")
        if completion.snapshot is not None:
            snapshot = completion.snapshot
    for gap in ctx.pdm_service.product_range_gaps(snapshot):
        state = "complete" if gap.is_complete else (
            f"INCOMPLETE - {len(gap.missing_product_ids)} missing"
        )
        print(
            f"  range {gap.range_name or gap.product_range_id}: "
            f"{len(gap.loaded_product_ids)}/{gap.eligible_count} loaded ({state})"
        )
    sets = ctx.engineering_reduction_service.materialize_article_sets(snapshot)
    # Members are what reduction stamps; a cached snapshot carries none yet.
    if not (snapshot.engineering and snapshot.engineering.families):
        ctx.engineering_initialization_service.initialize(snapshot)
    print(
        f"{path.name}: {len(snapshot.articles)} articles, "
        f"{len({a.product_id for a in snapshot.articles})} products, "
        f"{len(sets)} candidate families from the reduction engine"
    )
    # The ENFORCED production step: validate, then collapse only what legacy
    # PDM confirmed. Blocked families are left expanded.
    application = ctx.engineering_reduction_service.apply_validated_reduction(snapshot)
    bases = {
        m.reduced_article
        for f in (snapshot.engineering.families if snapshot.engineering else [])
        for m in f.members
        if m.reduced_article
    }
    print(
        f"  applied to {application.applied_members} members "
        f"({len(bases)} distinct bases), blocked {application.blocked_members} "
        f"members across {len(application.blocked_candidates)} candidate families"
    )
    results = list(application.validations)
    candidates = [
        FamilyCandidate(base=r.base_code, product_ids=r.product_ids) for r in results
    ]
    return candidates, results


def result_row(r: Any) -> dict:
    """One JSON row, tolerating either result shape (set verdict or family)."""
    return {
        "base": getattr(r, "base_code", None) or getattr(r, "base", ""),
        "set_id": getattr(r, "set_id", ""),
        "product_range": getattr(r, "product_range", ""),
        "product_category_id": getattr(r, "product_category_id", None),
        "intended_product_ids": list(
            getattr(r, "product_ids", None) or getattr(r, "intended_product_ids", ())
        ),
        "product_range_id": r.product_range_id,
        "functional_attribute_value_ids": list(r.functional_attribute_value_ids),
        "filtered_product_ids": list(r.filtered_product_ids),
        "status": r.status,
        "reason": r.reason,
        "missing_from_filter": list(r.missing_from_filter),
        "extra_in_filter": list(r.extra_in_filter),
        "extra_outside_snapshot": list(
            getattr(r, "extra_outside_snapshot", None)
            or getattr(r, "extra_outside_known", ())
        ),
        "snapshot_covers_range": getattr(
            r, "snapshot_covers_range", getattr(r, "range_population_complete", None)
        ),
        "unloaded_range_product_count": getattr(r, "unloaded_range_product_count", 0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", help="Cached family snapshot (production flow)")
    parser.add_argument(
        "--complete-ranges",
        action="store_true",
        help="Load every ProductRange in the session up to its full "
             "legacy-eligible population before validating",
    )
    parser.add_argument("--input", type=Path, help="CSV with 'base' and 'ProductId' columns")
    parser.add_argument("--discover", action="store_true", help="Sample live ranges instead of a dataset")
    parser.add_argument("--sample-ranges", type=int, default=25)
    parser.add_argument("--output", type=Path, default=Path(".audit_tmp_family_reduction_report.json"))
    args = parser.parse_args()

    if not args.snapshot and not args.input and not args.discover:
        parser.error("Supply --snapshot <name.json>, --input <csv>, or --discover")

    ctx = ApplicationContext()
    service = PDMFamilyReductionService(ctx)

    if args.snapshot:
        candidates, results = validate_snapshot(
            ctx, args.snapshot, complete_ranges=args.complete_ranges
        )
    elif args.input:
        candidates = read_candidates_from_csv(args.input)
        print(f"Loaded {len(candidates)} candidate families from {args.input}")
        results = service.validate_families(candidates)
    else:
        connection = service.repository.get_connection()
        try:
            candidates = discover_candidates(service, connection, args.sample_ranges)
            print(f"Discovered {len(candidates)} candidate families across up to {args.sample_ranges} ranges")
            results = tuple(
                service.validate_family(candidate, connection=connection) for candidate in candidates
            )
        finally:
            connection.close()

    by_status: dict[str, int] = defaultdict(int)
    for result in results:
        by_status[result.status] += 1

    report = {
        "candidate_count": len(candidates),
        "by_status": dict(by_status),
        "results": [result_row(r) for r in results],
    }
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Report written: {args.output}")
    print(f"By status: {dict(by_status)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
