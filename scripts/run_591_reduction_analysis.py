"""Read-only live PDM analysis for the 591-product reduction dataset.

The input dataset is Product-level data: it contains ProductId, Product,
Description and NewProduct. ProductId is therefore the authoritative key and
is used directly; the Product column is a product code, not an Item article.

This script does not write to PDM. It loads ProductRange/ProductAttributeValues
for the supplied ProductIds, runs the experimental reduction engine, and
validates every proposed group against the real legacy dbo.ProductsList
procedure.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.application_context import ApplicationContext  # noqa: E402
from repositories.pdm_repository import PDMRepository  # noqa: E402
from services.engineering.legacy_pdm_reduction_engine import (  # noqa: E402
    LegacyPDMReductionEngine,
    products_from_pdm_rows,
)

CHUNK_SIZE = 100


def read_dataset(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return []
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel_tab
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("Input file has no header row")
    required = {"ProductId", "Product"}
    missing = required - set(reader.fieldnames)
    if missing:
        raise ValueError(
            f"Input file must contain {sorted(required)}; missing {sorted(missing)}. "
            f"Columns: {reader.fieldnames!r}"
        )
    return [
        {key: (value or "").strip() for key, value in row.items()}
        for row in reader
    ]


def placeholders(count: int) -> str:
    return ", ".join("?" for _ in range(count))


def fetch_product_rows(conn: Any, product_ids: list[int]) -> dict[int, Any]:
    """Fetch one authoritative Product row for each supplied ProductId."""
    found: dict[int, Any] = {}
    for start in range(0, len(product_ids), CHUNK_SIZE):
        chunk = product_ids[start : start + CHUNK_SIZE]
        sql = f"""
            SELECT
                p.ProductId,
                p.Product,
                p.Name AS ProductName,
                p.ProductRangeId,
                p.Status AS ProductStatus,
                p.NewProduct,
                pr.Name AS ProductRangeName
            FROM Product p WITH (NOLOCK)
            LEFT OUTER JOIN ProductRange pr WITH (NOLOCK)
                ON pr.ProductRangeId = p.ProductRangeId
            WHERE p.ProductId IN ({placeholders(len(chunk))})
        """
        cursor = conn.cursor()
        cursor.execute(sql, tuple(chunk))
        for row in cursor.fetchall():
            found[int(row.ProductId)] = row
    return found


def fetch_active_item_counts(conn: Any, product_ids: list[int]) -> dict[int, int]:
    """Count active Items per ProductId for legacy ProductsList eligibility."""
    counts: dict[int, int] = {product_id: 0 for product_id in product_ids}
    for start in range(0, len(product_ids), CHUNK_SIZE):
        chunk = product_ids[start : start + CHUNK_SIZE]
        sql = f"""
            SELECT i.ProductId, COUNT(*) AS ActiveItemCount
            FROM Item i WITH (NOLOCK)
            WHERE i.ProductId IN ({placeholders(len(chunk))})
              AND i.Status = 1
            GROUP BY i.ProductId
        """
        cursor = conn.cursor()
        cursor.execute(sql, tuple(chunk))
        for row in cursor.fetchall():
            counts[int(row.ProductId)] = int(row.ActiveItemCount)
    return counts


def fetch_pav_rows(conn: Any, product_ids: list[int]) -> list[Any]:
    rows: list[Any] = []
    for start in range(0, len(product_ids), CHUNK_SIZE):
        chunk = product_ids[start : start + CHUNK_SIZE]
        sql = f"""
            SELECT
                pav.ProductId,
                p.Product,
                p.ProductRangeId,
                pav.AttributeValueId,
                a.AttributeId,
                a.Name AS AttributeName,
                av.Name AS AttributeValueName,
                av.OrderCodeValue
            FROM ProductAttributeValues pav WITH (NOLOCK)
            INNER JOIN Product p WITH (NOLOCK)
                ON p.ProductId = pav.ProductId
            INNER JOIN AttributeValue av WITH (NOLOCK)
                ON av.AttributeValueId = pav.AttributeValueId
            INNER JOIN Attribute a WITH (NOLOCK)
                ON a.AttributeId = av.AttributeId
            WHERE pav.ProductId IN ({placeholders(len(chunk))})
              AND av.Status = 1
            ORDER BY pav.ProductId, a.DisplayOrder, av.DisplayOrdinal
        """
        cursor = conn.cursor()
        cursor.execute(sql, tuple(chunk))
        rows.extend(cursor.fetchall())
    return rows


def products_list_filter(
    conn: Any,
    product_range_id: int,
    attribute_value_ids: list[int],
) -> set[int]:
    """Execute the real legacy ProductsList procedure for validation."""
    xml_values = "".join(
        f'<attribute attributeid="0" attributevalueid="{int(value)}" />'
        for value in attribute_value_ids
    )
    xml = f"<attributes>{xml_values}</attributes>"
    cursor = conn.cursor()
    cursor.execute("{CALL dbo.ProductsList(?, ?, ?)}", (product_range_id, 1, xml))
    columns = [desc[0] for desc in cursor.description or ()]
    product_id_index = next(
        (i for i, name in enumerate(columns) if name.lower() == "productid"), None
    )
    if product_id_index is None:
        raise RuntimeError(
            f"ProductsList did not return ProductId. Columns: {columns!r}"
        )
    return {int(row[product_id_index]) for row in cursor.fetchall()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="CSV/TSV Product dataset")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".audit_tmp_591_reduction_report.json"),
    )
    parser.add_argument("--skip-legacy-proc-validation", action="store_true")
    args = parser.parse_args()

    rows = read_dataset(args.input)
    input_by_product_id: dict[int, dict[str, str]] = {}
    for row in rows:
        product_id_text = row.get("ProductId", "")
        if not product_id_text:
            continue
        product_id = int(product_id_text)
        input_by_product_id[product_id] = row

    product_ids = sorted(input_by_product_id)
    print(f"Input rows: {len(rows)}")
    print(f"Input unique ProductIds: {len(product_ids)}")

    if not product_ids:
        raise SystemExit("No ProductId values were read from the input file.")

    ctx = ApplicationContext()
    repo = PDMRepository(ctx)
    conn = repo.get_connection()
    try:
        product_rows = fetch_product_rows(conn, product_ids)
        resolved_product_ids = sorted(set(product_ids) & set(product_rows))
        missing_product_ids = sorted(set(product_ids) - set(product_rows))
        print(f"Resolved ProductIds from PDM: {len(resolved_product_ids)}")
        print(f"Missing ProductIds from PDM: {len(missing_product_ids)}")

        active_item_counts = fetch_active_item_counts(conn, resolved_product_ids)
        pav_rows = fetch_pav_rows(conn, resolved_product_ids)
        print(f"ProductAttributeValues rows: {len(pav_rows)}")

        pav_by_product: dict[int, list[Any]] = {}
        for pav in pav_rows:
            pav_by_product.setdefault(int(pav.ProductId), []).append(pav)

        engine_rows: list[dict[str, object]] = []
        product_summary: list[dict[str, object]] = []
        for product_id in resolved_product_ids:
            product_row = product_rows[product_id]
            input_row = input_by_product_id[product_id]
            new_product = int(product_row.NewProduct or 0)
            active_item_count = active_item_counts.get(product_id, 0)
            eligible = active_item_count > 0 or new_product == 1
            values = pav_by_product.get(product_id, [])
            for pav in values:
                engine_rows.append(
                    {
                        "ProductId": product_id,
                        "Product": str(product_row.Product),
                        "ProductRangeId": int(product_row.ProductRangeId),
                        "AttributeValueId": int(pav.AttributeValueId),
                        "Eligible": eligible,
                    }
                )
            product_summary.append(
                {
                    "ProductId": product_id,
                    "InputProduct": input_row.get("Product", ""),
                    "PDMProduct": str(product_row.Product),
                    "Description": input_row.get("Description", ""),
                    "ProductRangeId": int(product_row.ProductRangeId),
                    "ProductRangeName": str(product_row.ProductRangeName or ""),
                    "ActiveItemCount": active_item_count,
                    "NewProduct": new_product,
                    "Eligible": eligible,
                    "AttributeValueCount": len(values),
                }
            )

        products = products_from_pdm_rows(engine_rows)
        analysis = LegacyPDMReductionEngine().analyze(products)
        print(f"Products loaded into engine: {len(products)}")
        print(f"Selected non-overlapping groups: {len(analysis.groups)}")
        print(f"Uncovered Products: {len(analysis.uncovered_product_ids)}")

        legacy_validation: list[dict[str, object]] = []
        if not args.skip_legacy_proc_validation:
            by_product = {product.product_id: product for product in products}
            for group in analysis.groups:
                seed_id = group.product_ids[0]
                seed = by_product[seed_id]
                actual = products_list_filter(
                    conn,
                    seed.product_range_id,
                    sorted(seed.attribute_value_ids),
                )
                expected = set(group.product_ids)
                legacy_validation.append(
                    {
                        "product_ids": list(group.product_ids),
                        "seed_product_id": seed_id,
                        "product_range_id": seed.product_range_id,
                        "seed_attribute_value_count": len(seed.attribute_value_ids),
                        "products_list_match": actual == expected,
                        "products_list_count": len(actual),
                        "engine_group_count": len(expected),
                        "products_list_only": sorted(actual - expected),
                        "engine_only": sorted(expected - actual),
                    }
                )

        report = {
            "input": str(args.input),
            "input_rows": len(rows),
            "input_unique_product_ids": len(product_ids),
            "resolved_product_ids": len(resolved_product_ids),
            "missing_product_ids": missing_product_ids,
            "product_attribute_value_rows": len(pav_rows),
            "engine_products": len(products),
            "selected_groups": [
                {
                    "product_ids": list(group.product_ids),
                    "product_range_id": group.product_range_id,
                    "common_attribute_value_ids": list(group.common_attribute_value_ids),
                }
                for group in analysis.groups
            ],
            "uncovered_product_ids": list(analysis.uncovered_product_ids),
            "legacy_products_list_validation": legacy_validation,
            "product_summary": product_summary,
        }
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Report written: {args.output}")

        if legacy_validation:
            passed = sum(1 for item in legacy_validation if item["products_list_match"])
            print(
                f"Legacy ProductsList validation: {passed}/{len(legacy_validation)} groups matched"
            )
            if passed != len(legacy_validation):
                print(
                    "WARNING: one or more proposed groups differ from the real ProductsList result."
                )
                return 2
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
