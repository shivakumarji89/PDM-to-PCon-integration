"""Validate the production Snapshot reduction against legacy ProductsList.

Example:
    python scripts/validate_pdm_article_reduction.py --input dataset.csv

This script is read-only. It loads the complete eligible Product population for
all ProductRanges referenced by the input, builds the same Snapshot indexes used
by the production reduction service, and independently checks every discovered
reduction group with legacy ProductsList.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.application_context import ApplicationContext  # noqa: E402
from models.article import Article  # noqa: E402
from models.property import Property  # noqa: E402
from models.property_value import PropertyValue  # noqa: E402
from models.snapshot import Snapshot  # noqa: E402
from repositories.legacy_pdm_compat_repository import LegacyPDMCompatRepository  # noqa: E402
from services.engineering.pdm_article_reduction_service import PDMArticleReductionService  # noqa: E402
from scripts.run_591_reduction_analysis import (  # noqa: E402
    fetch_active_item_counts,
    fetch_pav_rows,
    fetch_product_rows,
    read_dataset,
)


def fetch_range_product_rows(connection, range_ids):
    if not range_ids:
        return {}
    placeholders = ", ".join("?" for _ in range_ids)
    cursor = connection.cursor()
    cursor.execute(
        f"""SELECT p.ProductId, p.Product, p.ProductRangeId, p.NewProduct
            FROM Product p WITH (NOLOCK)
            WHERE p.ProductRangeId IN ({placeholders})""",
        tuple(range_ids),
    )
    return {int(row.ProductId): row for row in cursor.fetchall()}


def build_snapshot(product_rows, pav_rows):
    snapshot = Snapshot()
    values_by_product = {}
    functional_properties = {}

    for row in pav_rows:
        pid = int(row.ProductId)
        values_by_product.setdefault(pid, []).append(str(row.AttributeValueId))
        if int(row.AttributeType or 0) == 0 and not str(row.OrderCodeValue or "").strip():
            aid = str(row.AttributeId)
            value_id = str(row.AttributeValueId)
            value = PropertyValue(
                id=value_id,
                property_id=aid,
                code="",
                name=str(row.AttributeValueName or ""),
            )
            functional_properties.setdefault(aid, {})[value_id] = value

    snapshot.properties = [
        Property(
            id=aid,
            name=str(aid),
            attribute_type=0,
            values=list(values.values()),
        )
        for aid, values in functional_properties.items()
    ]
    snapshot.product_property_value_ids = values_by_product
    snapshot.product_range = {
        str(pid): str(row.ProductRangeId or "")
        for pid, row in product_rows.items()
    }
    snapshot.articles = [
        Article(
            id=str(pid),
            product_id=str(pid),
            code=str(row.Product or "").strip().rstrip("."),
        )
        for pid, row in product_rows.items()
    ]
    return snapshot


def products_list_ids(repository, range_id, value_ids, language_id=1):
    if not value_ids:
        xml = None
    else:
        body = "".join(
            f'<attribute attributeid="0" attributevalueid="{value_id}" />'
            for value_id in sorted(value_ids)
        )
        xml = f"<attributes>{body}</attributes>"
    rows = repository.fetch_legacy_filtered_products(
        range_id,
        language_id,
        xml,
        us_data=False,
    )
    return {str(getattr(row, "ProductId", row[0] if not hasattr(row, "ProductId") else row.ProductId)) for row in rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()

    source_rows = read_dataset(args.input)
    selected_ids = {int(row["ProductId"]) for row in source_rows if row.get("ProductId")}
    if not selected_ids:
        raise SystemExit("No ProductId values found.")

    context = ApplicationContext()
    repository = context.pdm_service.repository
    connection = repository.get_connection()
    try:
        selected_rows = fetch_product_rows(connection, sorted(selected_ids))
        range_ids = sorted({int(r.ProductRangeId) for r in selected_rows.values() if r.ProductRangeId is not None})
        all_rows = fetch_range_product_rows(connection, range_ids)
        active_counts = fetch_active_item_counts(connection, sorted(all_rows))
        eligible_rows = {
            pid: row for pid, row in all_rows.items()
            if active_counts.get(pid, 0) > 0 or int(row.NewProduct or 0) == 1
        }
        pav_rows = fetch_pav_rows(connection, sorted(eligible_rows))
    finally:
        connection.close()

    snapshot = build_snapshot(eligible_rows, pav_rows)
    service = PDMArticleReductionService(context)
    result = service.discover(snapshot)

    legacy = LegacyPDMCompatRepository(context)
    mismatches = []
    validated = 0
    for group in result.groups:
        expected = {str(pid) for pid in group.product_ids}
        actual = products_list_ids(legacy, group.product_range, group.filter_attribute_value_ids)
        if actual == expected:
            validated += 1
        else:
            mismatches.append((group.base_article, expected, actual))

    selected_covered = {
        str(pid) for group in result.groups for pid in group.product_ids
    }
    input_covered = selected_ids & {int(pid) for pid in selected_covered}
    print(f"Input ProductIds: {len(selected_ids)}")
    print(f"Complete eligible range population: {len(eligible_rows)}")
    print(f"Production reduction groups: {len(result.groups)}")
    print(f"Legacy ProductsList validations passed: {validated}")
    print(f"Legacy mismatches: {len(mismatches)}")
    print(f"Input ProductIds covered by reductions: {len(input_covered)}")
    print(f"Input ProductIds not covered: {len(selected_ids - input_covered)}")
    if mismatches:
        for base, expected, actual in mismatches[:20]:
            print(f"MISMATCH {base}: expected={len(expected)} actual={len(actual)}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
