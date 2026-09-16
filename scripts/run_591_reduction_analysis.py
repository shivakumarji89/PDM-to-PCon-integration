"""Read-only live PDM analysis for an article list.

This script does not write to PDM. It resolves the supplied article numbers to
Products, loads their ProductAttributeValues, runs the current reduction
engine, and optionally validates every proposed group through dbo.ProductsList.

Example (PowerShell):
    python scripts/run_591_reduction_analysis.py --input "C:\\path\\articles.tsv"

The input may be CSV/TSV. By default the article column is named ``Product``
(the column used by the 591-row investigation dataset). Use ``--article-column``
to override it.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.application_context import ApplicationContext  # noqa: E402
from repositories.pdm_repository import PDMRepository  # noqa: E402
from services.engineering.legacy_pdm_reduction_engine import (  # noqa: E402
    LegacyPDMReductionEngine,
    products_from_pdm_rows,
)


CHUNK_SIZE = 400


def read_article_numbers(path: Path, column: str) -> list[str]:
    """Read article numbers from CSV/TSV without changing the source file."""
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return []

    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel_tab

    rows = csv.DictReader(text.splitlines(), dialect=dialect)
    if not rows.fieldnames or column not in rows.fieldnames:
        raise ValueError(
            f"Input column {column!r} not found. Columns: {rows.fieldnames!r}"
        )

    result: list[str] = []
    seen: set[str] = set()
    for row in rows:
        value = (row.get(column) or "").strip()
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


def placeholders(count: int) -> str:
    return ", ".join("?" for _ in range(count))


def fetch_article_rows(conn: Any, articles: list[str]) -> list[Any]:
    """Resolve exact Item numbers to their Product and ProductRange context."""
    rows: list[Any] = []
    for start in range(0, len(articles), CHUNK_SIZE):
        chunk = articles[start : start + CHUNK_SIZE]
        sql = f"""
            SELECT
                i.ItemId,
                i.Item,
                i.Status AS ItemStatus,
                i.ProductId,
                p.Product AS ProductCode,
                p.Name AS ProductName,
                p.ProductRangeId,
                p.Status AS ProductStatus,
                p.NewProduct
            FROM Item i WITH (NOLOCK)
            INNER JOIN Product p WITH (NOLOCK)
                ON p.ProductId = i.ProductId
            WHERE i.Item IN ({placeholders(len(chunk))})
            ORDER BY i.Item
        """
        cursor = conn.cursor()
        cursor.execute(sql, tuple(chunk))
        rows.extend(cursor.fetchall())
    return rows


def fetch_pav_rows(conn: Any, product_ids: list[int]) -> list[Any]:
    """Load all ProductAttributeValues for the resolved Products."""
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


def products_list_filter(conn: Any, product_range_id: int, attribute_value_ids: list[int]) -> set[int]:
    """Execute the real legacy ProductsList stored procedure for validation."""
    xml_values = "".join(
        f'<attribute attributeid="0" attributevalueid="{int(value)}" />'
        for value in attribute_value_ids
    )
    xml = f"<attributes>{xml_values}</attributes>"
    cursor = conn.cursor()
    cursor.execute(
        "{{CALL dbo.ProductsList(?, ?, ?)}}",
        (product_range_id, 1, xml),
    )
    columns = [desc[0] for desc in cursor.description or ()]
    product_id_index = next(
        (i for i, name in enumerate(columns) if name.lower() == "productid"),
        None,
    )
    if product_id_index is None:
        raise RuntimeError(f"ProductsList did not return ProductId. Columns: {columns!r}")
    return {int(row[product_id_index]) for row in cursor.fetchall()}


def row_value(row: Any, name: str) -> Any:
    """Read pyodbc Row values by column name."""
    return getattr(row, name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="CSV/TSV article list")
    parser.add_argument("--article-column", default="Product", help="Input column containing full article numbers")
    parser.add_argument("--output", type=Path, default=Path(".audit_tmp_591_reduction_report.json"))
    parser.add_argument(
        "--skip-legacy-proc-validation",
        action="store_true",
        help="Do not call dbo.ProductsList for proposed groups",
    )
    args = parser.parse_args()

    articles = read_article_numbers(args.input, args.article_column)
    print(f"Input unique articles: {len(articles)}")

    ctx = ApplicationContext()
    repo = PDMRepository(ctx)
    conn = repo.get_connection()
    try:
        article_rows = fetch_article_rows(conn, articles)
        by_article: dict[str, list[Any]] = {}
        for row in article_rows:
            by_article.setdefault(str(row_value(row, "Item")), []).append(row)

        missing = [article for article in articles if article not in by_article]
        ambiguous = {
            article: len(rows)
            for article, rows in by_article.items()
            if len(rows) > 1
        }

        resolved = [rows[0] for article in articles if len(by_article.get(article, [])) == 1]
        product_ids = sorted({int(row_value(row, "ProductId")) for row in resolved})
        print(f"Resolved unique article rows: {len(resolved)}")
        print(f"Missing articles: {len(missing)}")
        print(f"Ambiguous article numbers: {len(ambiguous)}")
        print(f"Unique Products represented: {len(product_ids)}")

        pav_rows = fetch_pav_rows(conn, product_ids)
        pav_by_product: dict[int, list[Any]] = {}
        for row in pav_rows:
            pav_by_product.setdefault(int(row_value(row, "ProductId")), []).append(row)

        engine_rows: list[dict[str, object]] = []
        for product_id in product_ids:
            article_row = next(r for r in resolved if int(row_value(r, "ProductId")) == product_id)
            eligible = bool(row_value(article_row, "ItemStatus") == 1 or row_value(article_row, "NewProduct") == 1)
            for pav in pav_by_product.get(product_id, []):
                engine_rows.append(
                    {
                        "ProductId": product_id,
                        "Product": str(row_value(article_row, "ProductCode")),
                        "ProductRangeId": int(row_value(article_row, "ProductRangeId")),
                        "AttributeValueId": int(row_value(pav, "AttributeValueId")),
                        "Eligible": eligible,
                    }
                )

        products = products_from_pdm_rows(engine_rows)
        analysis = LegacyPDMReductionEngine().analyze(products)
        print(f"Products loaded into engine: {len(products)}")
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
            "input_unique_articles": len(articles),
            "missing_articles": missing,
            "ambiguous_articles": ambiguous,
            "resolved_unique_article_rows": len(resolved),
            "unique_products": len(product_ids),
            "pav_rows": len(pav_rows),
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
        }

        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Report written: {args.output}")

        if legacy_validation:
            passed = sum(1 for item in legacy_validation if item["products_list_match"])
            print(f"Legacy ProductsList validation: {passed}/{len(legacy_validation)} groups matched")
            if passed != len(legacy_validation):
                print("WARNING: one or more proposed groups differ from the real ProductsList result.")
                return 2

        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
