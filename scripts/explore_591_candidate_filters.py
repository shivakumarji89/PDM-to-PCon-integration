"""Read-only exploration of candidate Product filters for the 591-product dataset.

This script deliberately does NOT implement Product reduction. It discovers
candidate AttributeValueId filters from the supplied ProductAttributeValues
and validates them using the legacy ProductsList semantics available through
PDMRepository.

Input format: TSV/CSV/text containing at least ProductId. If ProductId is the
only useful identity, the script uses it directly; no Item/article resolution
is performed.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.application_context import ApplicationContext
from repositories.pdm_repository import PDMRepository

CHUNK_SIZE = 100


def placeholders(count: int) -> str:
    return ", ".join("?" for _ in range(count))


def read_product_ids(path: Path) -> List[int]:
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        return []
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters="\t,;")
    except csv.Error:
        dialect = csv.excel_tab
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    if not reader.fieldnames or "ProductId" not in reader.fieldnames:
        raise ValueError(f"Input must contain ProductId. Columns: {reader.fieldnames}")
    ids: Set[int] = set()
    for row in reader:
        value = (row.get("ProductId") or "").strip()
        if value:
            ids.add(int(value))
    return sorted(ids)


def fetch_products(repo: PDMRepository, product_ids: List[int]) -> Dict[int, dict]:
    found: Dict[int, dict] = {}
    conn = repo.get_connection()
    try:
        for start in range(0, len(product_ids), CHUNK_SIZE):
            chunk = product_ids[start : start + CHUNK_SIZE]
            sql = f"""
                SELECT ProductId, Product, ProductRangeId, ProductCodeId,
                       Status, NewProduct, IsSuperProduct
                FROM Product WITH (NOLOCK)
                WHERE ProductId IN ({placeholders(len(chunk))})
            """
            cursor = conn.cursor()
            cursor.execute(sql, tuple(chunk))
            for r in cursor.fetchall():
                found[int(r.ProductId)] = {
                    "Product": str(r.Product),
                    "ProductRangeId": int(r.ProductRangeId) if r.ProductRangeId is not None else None,
                    "ProductCodeId": int(r.ProductCodeId) if r.ProductCodeId is not None else None,
                    "Status": int(r.Status) if r.Status is not None else None,
                    "NewProduct": int(r.NewProduct) if r.NewProduct is not None else 0,
                    "IsSuperProduct": int(r.IsSuperProduct) if r.IsSuperProduct is not None else 0,
                }
    finally:
        conn.close()
    return found


def fetch_pavs(repo: PDMRepository, product_ids: List[int]) -> list:
    rows = []
    conn = repo.get_connection()
    try:
        for start in range(0, len(product_ids), CHUNK_SIZE):
            chunk = product_ids[start : start + CHUNK_SIZE]
            sql = f"""
                SELECT pav.ProductId, pav.AttributeValueId,
                       av.AttributeId, a.Name AS AttributeName,
                       av.Name AS ValueName, av.OrderCodeValue,
                       a.DisplayOrder, av.DisplayOrdinal
                FROM ProductAttributeValues pav WITH (NOLOCK)
                INNER JOIN AttributeValue av WITH (NOLOCK)
                    ON pav.AttributeValueId = av.AttributeValueId
                INNER JOIN Attribute a WITH (NOLOCK)
                    ON av.AttributeId = a.AttributeId
                WHERE pav.ProductId IN ({placeholders(len(chunk))})
                  AND av.Status = 1
                ORDER BY pav.ProductId, a.DisplayOrder, av.DisplayOrdinal
            """
            cursor = conn.cursor()
            cursor.execute(sql, tuple(chunk))
            rows.extend(cursor.fetchall())
    finally:
        conn.close()
    return rows


def products_list(
    repo: PDMRepository,
    product_range_id: int,
    value_info: Dict[int, dict],
    value_ids: Iterable[int],
) -> Set[int]:
    """Call the legacy dbo.ProductsList using ODBC EXEC syntax."""
    values = list(dict.fromkeys(int(v) for v in value_ids))
    if not values:
        return set()

    xml_values = "".join(
        f'<attribute attributeid="{int(value_info[v]["AttributeId"])}" '
        f'attributevalueid="{v}" />'
        for v in values
    )
    xml = f"<attributes>{xml_values}</attributes>"

    conn = repo.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("EXEC dbo.ProductsList ?, ?, ?", (product_range_id, 1, xml))
        columns = [desc[0] for desc in cursor.description or ()]
        product_id_index = next(
            (i for i, name in enumerate(columns) if str(name).lower() == "productid"),
            None,
        )
        if product_id_index is None:
            raise RuntimeError(f"ProductsList did not return ProductId. Columns: {columns!r}")
        return {int(row[product_id_index]) for row in cursor.fetchall()}
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--max-values", type=int, default=3,
                        help="maximum candidate filter size; default 3")
    parser.add_argument("--limit-per-range", type=int, default=500,
                        help="maximum candidate combinations validated per ProductRangeId")
    parser.add_argument("--output", default=".audit_tmp_591_candidate_filters.json")
    args = parser.parse_args()

    input_ids = read_product_ids(Path(args.input))
    repo = PDMRepository(ApplicationContext())
    products = fetch_products(repo, input_ids)
    pav_rows = fetch_pavs(repo, input_ids)

    by_product: Dict[int, Set[int]] = defaultdict(set)
    value_info: Dict[int, dict] = {}
    for r in pav_rows:
        pid = int(r.ProductId)
        vid = int(r.AttributeValueId)
        by_product[pid].add(vid)
        value_info[vid] = {
            "AttributeId": int(r.AttributeId),
            "AttributeName": str(r.AttributeName),
            "ValueName": str(r.ValueName),
            "OrderCodeValue": r.OrderCodeValue,
        }

    results = []
    range_summary = {}

    for range_id in sorted(
        {p["ProductRangeId"] for p in products.values() if p["ProductRangeId"] is not None}
    ):
        range_products = sorted(
            pid for pid, p in products.items() if p["ProductRangeId"] == range_id
        )
        range_summary[str(range_id)] = len(range_products)

        counts: Dict[Tuple[int, ...], Set[int]] = defaultdict(set)
        for pid in range_products:
            vals = sorted(by_product.get(pid, set()))
            for size in range(1, min(args.max_values, len(vals)) + 1):
                for combo in itertools.combinations(vals, size):
                    counts[combo].add(pid)

        candidates = sorted(
            (
                (combo, ids)
                for combo, ids in counts.items()
                if 1 < len(ids) < len(range_products)
            ),
            key=lambda item: (-len(item[1]), len(item[0]), item[0]),
        )

        for combo, observed in candidates[: args.limit_per_range]:
            returned = products_list(repo, int(range_id), value_info, combo)
            intended = set(observed)
            results.append(
                {
                    "ProductRangeId": int(range_id),
                    "AttributeValueIds": list(combo),
                    "Values": [value_info.get(v, {}) for v in combo],
                    "ObservedDatasetSupportCount": len(intended),
                    "ObservedDatasetSupportProductIds": sorted(intended),
                    "LegacyProductsListCount": len(returned),
                    "LegacyProductsListProductIds": sorted(returned),
                    "ExactDatasetGroup": returned == intended,
                    "LegacyOnlyProductIds": sorted(returned - intended),
                    "DatasetOnlyProductIds": sorted(intended - returned),
                    "ExactDatasetGroupWithinInput": returned == intended and returned.issubset(set(input_ids)),
                }
            )

    report = {
        "input_product_count": len(input_ids),
        "resolved_product_count": len(products),
        "missing_product_ids": sorted(set(input_ids) - set(products)),
        "pav_row_count": len(pav_rows),
        "ranges": range_summary,
        "max_candidate_filter_size": args.max_values,
        "candidate_limit_per_range": args.limit_per_range,
        "candidate_count": len(results),
        "exact_candidates": sum(1 for r in results if r["ExactDatasetGroup"]),
        "results": results,
    }
    Path(args.output).write_text(
        json.dumps(report, indent=2, default=str),
        encoding="utf-8",
    )

    print(f"Input ProductIds: {len(input_ids)}")
    print(f"Resolved Products: {len(products)}")
    print(f"ProductAttributeValues rows: {len(pav_rows)}")
    print(f"Candidate filters tested: {len(results)}")
    print(f"Exact dataset groups found: {report['exact_candidates']}")
    print(f"Report written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
