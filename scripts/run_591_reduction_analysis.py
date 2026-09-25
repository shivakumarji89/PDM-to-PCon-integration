"""Read-only live PDM analysis for a ProductId list.

The supplied 591-row validation dataset already contains ProductId. This
script therefore resolves the dataset directly through ProductId rather than
trying to interpret the Product column as an Item/article number.

No PDM data is written. The reduction candidates are additionally validated
against the real legacy dbo.ProductsList stored procedure.
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


def read_product_ids(path: Path, column: str) -> list[int]:
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return []
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel_tab
    rows = csv.DictReader(text.splitlines(), dialect=dialect)
    if not rows.fieldnames or column not in rows.fieldnames:
        raise ValueError(
            f"Input column {column!r} not found. Columns: {rows.fieldnames!r}"
        )

    result: list[int] = []
    seen: set[int] = set()
    for row in rows:
        raw = (row.get(column) or "").strip()
        if not raw:
            continue
        try:
            product_id = int(raw)
        except ValueError as exc:
            raise ValueError(
                f"Invalid ProductId value {raw!r} in column {column!r}"
            ) from exc
        if product_id not in seen:
            result.append(product_id)
            seen.add(product_id)
    return result


def placeholders(count: int) -> str:
    return ", ".join("?" for _ in range(count))


def fetch_product_rows(conn: Any, product_ids: list[int]) -> list[Any]:
    """Load supplied Products and mirror legacy ProductsList eligibility."""
    rows: list[Any] = []
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
                CASE
                    WHEN p.NewProduct = 1
                      OR EXISTS (
                            SELECT 1
                            FROM Item i WITH (NOLOCK)
                            WHERE i.ProductId = p.ProductId
                              AND i.Status = 1
                        )
                    THEN 1 ELSE 0
                END AS Eligible
            FROM Product p WITH (NOLOCK)
            WHERE p.ProductId IN ({placeholders(len(chunk))})
            ORDER BY p.ProductId
        """
        cursor = conn.cursor()
        cursor.execute(sql, tuple(chunk))
        rows.extend(cursor.fetchall())
    return rows


def fetch_pav_rows(conn: Any, product_ids: list[int]) -> list[Any]:
    """Load all ProductAttributeValues for supplied Products.

    No AttributeValue status filter is imposed here; the real ProductsList
    procedure remains the authority for filter validation.
    """
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
            ORDER BY pav.ProductId, a.DisplayOrder, av.DisplayOrdinal
        """
        cursor = conn.cursor()
        cursor.execute(sql, tuple(chunk))
        rows.extend(cursor.fetchall())
    return rows


def products_list_filter(
    conn: Any, product_range_id: int, attribute_value_ids: list[int]
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


def row_value(row: Any, name: str) -> Any:
    return getattr(row, name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="CSV/TSV ProductId list")
    parser.add_argument(
        "--product-id-column",
        default="ProductId",
        help="Input column containing PDM ProductIds",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".audit_tmp_591_reduction_report.json"),
    )
    parser.add_argument("--skip-legacy-proc-validation", action="store_true")
    args = parser.parse_args()

    product_ids = read_product_ids(args.input, args.product_id_column)
    print(f"Input unique ProductIds: {len(product_ids)}")

    if not product_ids:
        print("No ProductIds were read from the input file.")
        return 1

    ctx = ApplicationContext()
    repo = PDMRepository(ctx)
    conn = repo.get_connection()
    try:
        product_rows = fetch_product_rows(conn, product_ids)
        found_ids = {int(row_value(row, "ProductId")) for row in product_rows}
        missing_product_ids = [pid for pid in product_ids if pid not in found_ids]

        print(f"Resolved ProductIds: {len(found_ids)}")
        print(f"Missing ProductIds: {len(missing_product_ids)}")

        pav_rows = fetch_pav_rows(conn, sorted(found_ids))
        pav_by_product: dict[int, list[Any]] = {}
        for row in pav_rows:
            pav_by_product.setdefault(int(row_value(row, "ProductId")), []).append(row)

        product_by_id = {
            int(row_value(row, "ProductId")): row for row in product_rows
        }

        engine_rows: list[dict[str, object]] = []
        products_without_pav: list[int] = []
        for product_id in sorted(found_ids):
            product_row = product_by_id[product_id]
            product_pav = pav_by_product.get(product_id, [])
            if not product_pav:
                products_without_pav.append(product_id)
                continue
            for pav in product_pav:
                engine_rows.append(
                    {
                        "ProductId": product_id,
                        "Product": str(row_value(product_row, "Product")),
                        "ProductRangeId": int(row_value(product_row, "ProductRangeId")),
                        "AttributeValueId": int(row_value(pav, "AttributeValueId")),
                        "Eligible": bool(row_value(product_row, "Eligible")),
                    }
                )

        products = products_from_pdm_rows(engine_rows)
        print(f"PAV rows loaded: {len(pav_rows)}")
        print(f"Products loaded into reduction engine: {len(products)}")
        print(f"Products without PAV rows: {len(products_without_pav)}")

        engine = LegacyPDMReductionEngine()
        candidate_groups = engine.discover_exact_groups(products)
        analysis = engine.analyze(products)
        print(f"Candidate groups before non-overlap selection: {len(candidate_groups)}")
        print(f"Selected non-overlapping groups: {len(analysis.groups)}")
        print(f"Uncovered Products: {len(analysis.uncovered_product_ids)}")

        legacy_validation: list[dict[str, object]] = []
        if not args.skip_legacy_proc_validation:
            by_product = {p.product_id: p for p in products}
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
            "input_unique_product_ids": len(product_ids),
            "resolved_product_ids": len(found_ids),
            "missing_product_ids": missing_product_ids,
            "pav_rows": len(pav_rows),
            "products_without_pav": products_without_pav,
            "engine_products": len(products),
            "candidate_group_count": len(candidate_groups),
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
        }

        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Report written: {args.output}")

        if legacy_validation:
            passed = sum(
                1 for item in legacy_validation if item["products_list_match"]
            )
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
