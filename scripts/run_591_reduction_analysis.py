"""Read-only live PDM analysis for an article list.

This script does not write to PDM. It first verifies the input against the
same Item-search semantics already used by PDMRepository, then resolves each
input article to Product ids, loads ProductAttributeValues, and runs the
current reduction engine.
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


def read_article_numbers(path: Path, column: str) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return []
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel_tab
    rows = csv.DictReader(text.splitlines(), dialect=dialect)
    if not rows.fieldnames or column not in rows.fieldnames:
        raise ValueError(f"Input column {column!r} not found. Columns: {rows.fieldnames!r}")
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


def fetch_article_rows(conn: Any, articles: list[str]) -> dict[str, list[Any]]:
    """Resolve supplied values using the same SQL article-search shape as PDMRepository.

    A value containing '.' is matched as an exact Item. A pre-dot value is
    matched as Item LIKE '<value>.%'. This remains read-only.
    """
    found: dict[str, list[Any]] = {article: [] for article in articles}
    for start in range(0, len(articles), CHUNK_SIZE):
        chunk = articles[start : start + CHUNK_SIZE]
        conditions: list[str] = []
        params: list[str] = []
        for article in chunk:
            if "." in article:
                conditions.append("i.Item = ?")
                params.append(article)
            else:
                conditions.append("i.Item LIKE ?")
                params.append(article + ".%")

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
            WHERE {' OR '.join(f'({condition})' for condition in conditions)}
            ORDER BY i.Item
        """
        cursor = conn.cursor()
        cursor.execute(sql, tuple(params))
        returned = cursor.fetchall()

        for row in returned:
            item = str(getattr(row, "Item"))
            for article in chunk:
                if "." in article:
                    if item == article:
                        found[article].append(row)
                elif item.startswith(article + "."):
                    found[article].append(row)

    return found


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


def products_list_filter(conn: Any, product_range_id: int, attribute_value_ids: list[int]) -> set[int]:
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
        raise RuntimeError(f"ProductsList did not return ProductId. Columns: {columns!r}")
    return {int(row[product_id_index]) for row in cursor.fetchall()}


def row_value(row: Any, name: str) -> Any:
    return getattr(row, name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="CSV/TSV article list")
    parser.add_argument("--article-column", default="Product", help="Input column containing article numbers")
    parser.add_argument("--output", type=Path, default=Path(".audit_tmp_591_reduction_report.json"))
    parser.add_argument("--skip-legacy-proc-validation", action="store_true")
    args = parser.parse_args()

    articles = read_article_numbers(args.input, args.article_column)
    print(f"Input unique articles: {len(articles)}")

    ctx = ApplicationContext()
    repo = PDMRepository(ctx)
    conn = repo.get_connection()
    try:
        by_article = fetch_article_rows(conn, articles)

        exact_match_articles = [
            article for article in articles if "." in article and by_article.get(article)
        ]
        prefix_match_articles = [
            article for article in articles if "." not in article and by_article.get(article)
        ]
        missing = [article for article in articles if not by_article.get(article)]

        product_candidates: dict[str, set[int]] = {
            article: {int(row_value(row, "ProductId")) for row in rows}
            for article, rows in by_article.items()
        }
        ambiguous = {
            article: len(product_ids)
            for article, product_ids in product_candidates.items()
            if len(product_ids) > 1
        }

        resolved = []
        for article in articles:
            rows = by_article.get(article, [])
            product_ids = product_candidates.get(article, set())
            if len(product_ids) == 1:
                product_id = next(iter(product_ids))
                resolved.append(next(row for row in rows if int(row_value(row, "ProductId")) == product_id))

        product_ids = sorted({int(row_value(row, "ProductId")) for row in resolved})
        print(f"Resolved unique article rows: {len(resolved)}")
        print(f"Exact full-article matches: {len(exact_match_articles)}")
        print(f"Pre-dot prefix matches: {len(prefix_match_articles)}")
        print(f"Missing articles: {len(missing)}")
        print(f"Ambiguous article numbers: {len(ambiguous)}")
        print(f"Unique Products represented: {len(product_ids)}")

        if not articles:
            print("No article values were read from the input file.")
            return 1

        if not resolved:
            print("No Products resolved. Writing diagnostic samples to the report.")
            report = {
                "input": str(args.input),
                "input_unique_articles": len(articles),
                "sample_input_articles": articles[:20],
                "missing_articles": missing,
                "ambiguous_articles": ambiguous,
                "resolved_unique_article_rows": 0,
                "unique_products": 0,
                "pav_rows": 0,
                "engine_products": 0,
                "selected_groups": [],
                "uncovered_product_ids": [],
                "legacy_products_list_validation": [],
            }
            args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
            print(f"Report written: {args.output}")
            return 0

        pav_rows = fetch_pav_rows(conn, product_ids)
        pav_by_product: dict[int, list[Any]] = {}
        for row in pav_rows:
            pav_by_product.setdefault(int(row_value(row, "ProductId")), []).append(row)

        engine_rows: list[dict[str, object]] = []
        for product_id in product_ids:
            article_row = next(r for r in resolved if int(row_value(r, "ProductId")) == product_id)
            eligible = bool(
                row_value(article_row, "ItemStatus") == 1
                or row_value(article_row, "NewProduct") == 1
            )
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
            "sample_input_articles": articles[:20],
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
