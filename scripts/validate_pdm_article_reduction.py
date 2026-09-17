"""Read-only validation of PDM article reduction against ProductsList.

Example:
    python scripts/validate_pdm_article_reduction.py --input dataset.csv
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.application_context import ApplicationContext  # noqa: E402
from repositories.legacy_pdm_compat_repository import LegacyPDMCompatRepository  # noqa: E402
from services.engineering.pdm_article_reduction_service import (  # noqa: E402
    PDMArticleReductionService,
    PDMAttributeValue,
)
from scripts.run_591_reduction_analysis import (  # noqa: E402
    fetch_active_item_counts,
    fetch_pav_rows,
    fetch_product_rows,
    read_dataset,
)


def fetch_range_product_rows(connection, range_ids):
    """Load the complete Product population for the selected ranges."""
    if not range_ids:
        return {}
    placeholders = ", ".join("?" for _ in range_ids)
    cursor = connection.cursor()
    cursor.execute(
        f"""
        SELECT p.ProductId, p.Product, p.ProductRangeId, p.NewProduct
        FROM Product p WITH (NOLOCK)
        WHERE p.ProductRangeId IN ({placeholders})
        """,
        tuple(range_ids),
    )
    return {int(row.ProductId): row for row in cursor.fetchall()}


class DiagnosticLegacyRepository:
    """Delegate PDM access while reporting legacy filter-call progress."""

    def __init__(self, repository):
        self.repository = repository
        self.validation_count = 0
        self.started_at = time.perf_counter()
        self.current_prefix = "?"

    def fetch_legacy_filtered_products(
        self, product_range_id, language_id, attribute_xml, *, us_data=False
    ):
        rows = self.repository.fetch_legacy_filtered_products(
            product_range_id,
            language_id,
            attribute_xml,
            us_data=us_data,
        )
        self.validation_count += 1
        if self.validation_count % 10 == 0:
            elapsed = time.perf_counter() - self.started_at
            print(
                "Legacy ProductsList validations: "
                f"{self.validation_count}; elapsed seconds: {elapsed:.2f}; "
                f"candidate prefix: {self.current_prefix}",
                flush=True,
            )
        return rows

    def __getattr__(self, name):
        return getattr(self.repository, name)


class DiagnosticPDMArticleReductionService(PDMArticleReductionService):
    """Add prefix labels to diagnostics without changing reduction behavior."""

    def __init__(self, context, repository, prefix_by_product_ids):
        super().__init__(context, repository)
        self.prefix_by_product_ids = prefix_by_product_ids

    def _validate(
        self,
        range_id,
        selections,
        expected_ids,
        *,
        language_id,
        us_data,
        product_category_id,
    ):
        self.repository.current_prefix = self.prefix_by_product_ids.get(
            (range_id, expected_ids), "?"
        )
        return super()._validate(
            range_id,
            selections,
            expected_ids,
            language_id=language_id,
            us_data=us_data,
            product_category_id=product_category_id,
        )


def announce(stage, started_at):
    elapsed = time.perf_counter() - started_at
    print(f"{stage}: complete; elapsed seconds: {elapsed:.2f}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    stage_started = time.perf_counter()
    print("1. Loading the selected 591 ProductIds...", flush=True)
    source_rows = read_dataset(args.input)
    product_ids = sorted({int(row["ProductId"]) for row in source_rows if row.get("ProductId")})
    if not product_ids:
        raise SystemExit("No ProductId values found.")
    announce(f"1. Loading the selected 591 ProductIds ({len(product_ids)} IDs)", stage_started)

    context = ApplicationContext()
    pdm = context.pdm_service.repository
    connection = pdm.get_connection()
    try:
        stage_started = time.perf_counter()
        print("2. Discovering ProductRangeIds...", flush=True)
        selected_rows = fetch_product_rows(connection, product_ids)
        range_ids = sorted(
            {int(row.ProductRangeId) for row in selected_rows.values() if row.ProductRangeId is not None}
        )
        announce(f"2. Discovering ProductRangeIds ({len(range_ids)} ranges)", stage_started)

        stage_started = time.perf_counter()
        print("3. Loading the complete Product population for those ranges...", flush=True)
        product_rows = fetch_range_product_rows(connection, range_ids)
        announce(f"3. Loading the complete Product population ({len(product_rows)} products)", stage_started)

        stage_started = time.perf_counter()
        print("4. Applying legacy eligibility...", flush=True)
        active_item_counts = fetch_active_item_counts(connection, sorted(product_rows))
        eligible_ids = sorted(
            product_id
            for product_id, row in product_rows.items()
            if active_item_counts.get(product_id, 0) > 0 or int(row.NewProduct or 0) == 1
        )
        product_rows = {product_id: product_rows[product_id] for product_id in eligible_ids}
        announce(f"4. Applying legacy eligibility ({len(eligible_ids)} eligible products)", stage_started)

        stage_started = time.perf_counter()
        print("5. Loading ProductAttributeValues...", flush=True)
        pav_rows = fetch_pav_rows(connection, eligible_ids)
        announce(f"5. Loading ProductAttributeValues ({len(pav_rows)} rows)", stage_started)
    finally:
        connection.close()

    stage_started = time.perf_counter()
    print("6. Creating PDMProductRecord inputs...", flush=True)
    values_by_product = {}
    for row in pav_rows:
        values_by_product.setdefault(int(row.ProductId), []).append(
            PDMAttributeValue(
                str(row.AttributeValueId),
                str(row.AttributeId),
                str(row.AttributeName or ""),
                str(row.AttributeValueName or ""),
                str(row.OrderCodeValue or ""),
            )
        )
    products = [
        SimpleNamespace(
            ProductId=product_id,
            Product=product_row.Product,
            ProductRangeId=product_row.ProductRangeId,
            eligible=True,
            attribute_values=tuple(values_by_product.get(product_id, ())),
        )
        for product_id, product_row in product_rows.items()
    ]
    announce(f"6. Creating PDMProductRecord inputs ({len(products)} records)", stage_started)

    prefix_by_product_ids = {}
    range_products = {}
    for product in products:
        range_products.setdefault(product.ProductRangeId, []).append(
            service_product := PDMArticleReductionService._normalise_product(product)
        )
    for range_id, range_rows in range_products.items():
        for prefix, prefix_rows in PDMArticleReductionService._meaningful_prefixes(range_rows):
            prefix_by_product_ids[(range_id, frozenset(row.product_id for row in prefix_rows))] = prefix

    diagnostic_repository = DiagnosticLegacyRepository(
        LegacyPDMCompatRepository(context)
    )
    service = DiagnosticPDMArticleReductionService(
        context,
        diagnostic_repository,
        prefix_by_product_ids,
    )
    stage_started = time.perf_counter()
    print("7. Starting PDMArticleReductionService.discover()...", flush=True)
    candidates = service.discover(products)
    announce(
        "7. PDMArticleReductionService.discover() "
        f"({diagnostic_repository.validation_count} validations)",
        stage_started,
    )
    ambiguous = [candidate for candidate in candidates if candidate.ambiguous_equivalent_filters]
    covered = {product_id for candidate in candidates for product_id in candidate.product_ids}
    uncovered = sorted(str(product_id) for product_id in product_ids if str(product_id) not in covered)
    print(f"Candidate groups: {len(candidates)}")
    print(f"Validated groups: {sum(candidate.validation.valid for candidate in candidates)}")
    print(f"Uncovered ProductIds: {len(uncovered)}")
    print(f"Ambiguous groups: {len(ambiguous)}")
    for candidate in candidates:
        print(f"{candidate.product_range_id} {candidate.base}: {candidate.product_ids} filter={candidate.filter_attribute_value_ids}")
    if uncovered:
        print("Uncovered:", ", ".join(uncovered))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())