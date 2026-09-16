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
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

from context import ApplicationContext
from repositories.pdm_repository import PDMRepository


def read_product_ids(path: Path) -> List[int]:
    rows = []
    text = path.read_text(encoding="utf-8-sig")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters="\t,;")
    except csv.Error:
        dialect = csv.excel_tab
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    if not reader.fieldnames or "ProductId" not in reader.fieldnames:
        raise ValueError(f"Input must contain ProductId. Columns: {reader.fieldnames}")
    for row in reader:
        value = (row.get("ProductId") or "").strip()
        if value:
            rows.append(int(value))
    return sorted(set(rows))


def fetch_products(repo: PDMRepository, product_ids: List[int]):
    conn = repo.get_connection()
    placeholders = ",".join("?" for _ in product_ids)
    sql = f"""
        SELECT ProductId, Product, ProductRangeId, ProductCodeId,
               Status, NewProduct, IsSuperProduct
        FROM Product
        WHERE ProductId IN ({placeholders})
    """
    rows = conn.execute(sql, product_ids).fetchall()
    return {
        int(r.ProductId): {
            "Product": r.Product,
            "ProductRangeId": int(r.ProductRangeId) if r.ProductRangeId is not None else None,
            "ProductCodeId": int(r.ProductCodeId) if r.ProductCodeId is not None else None,
            "Status": int(r.Status) if r.Status is not None else None,
            "NewProduct": int(r.NewProduct) if r.NewProduct is not None else 0,
            "IsSuperProduct": int(r.IsSuperProduct) if r.IsSuperProduct is not None else 0,
        }
        for r in rows
    }


def fetch_pavs(repo: PDMRepository, product_ids: List[int]):
    conn = repo.get_connection()
    placeholders = ",".join("?" for _ in product_ids)
    sql = f"""
        SELECT pav.ProductId, pav.AttributeValueId,
               av.AttributeId, a.Name AS AttributeName,
               av.Name AS ValueName, av.OrderCodeValue,
               a.DisplayOrder, av.DisplayOrdinal
        FROM ProductAttributeValues pav
        INNER JOIN AttributeValue av ON pav.AttributeValueId = av.AttributeValueId
        INNER JOIN Attribute a ON av.AttributeId = a.AttributeId
        WHERE pav.ProductId IN ({placeholders})
          AND av.Status = 1
        ORDER BY pav.ProductId, a.DisplayOrder, av.DisplayOrdinal
    """
    return conn.execute(sql, product_ids).fetchall()


def products_list(repo: PDMRepository, product_range_id: int, value_ids: Iterable[int]) -> Set[int]:
    """Call the real legacy dbo.ProductsList through the repository connection."""
    import xml.etree.ElementTree as ET

    root = ET.Element("attributes")
    for value_id in value_ids:
        node = ET.SubElement(root, "attribute")
        node.set("attributeid", "0")
        node.set("attributevalueid", str(value_id))
    xml = ET.tostring(root, encoding="unicode")
    conn = repo.get_connection()
    rows = conn.execute(
        "EXEC dbo.ProductsList ?, ?, ?",
        product_range_id,
        1,
        xml,
    ).fetchall()
    return {int(r.ProductId) for r in rows}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--max-values", type=int, default=3,
                        help="maximum candidate filter size; default 3")
    parser.add_argument("--output", default=".audit_tmp_591_candidate_filters.json")
    args = parser.parse_args()

    input_ids = read_product_ids(Path(args.input))
    repo = PDMRepository(ApplicationContext())
    products = fetch_products(repo, input_ids)
    pav_rows = fetch_pavs(repo, input_ids)

    by_product: Dict[int, Set[int]] = defaultdict(set)
    value_info = {}
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

    # Candidate filters are built from values actually present in the dataset.
    # We intentionally test only combinations up to --max-values and only
    # within each ProductRangeId. The result is diagnostic, not a reducer.
    results = []
    import itertools

    for range_id in sorted({p["ProductRangeId"] for p in products.values() if p["ProductRangeId"] is not None}):
        range_products = sorted(pid for pid, p in products.items() if p["ProductRangeId"] == range_id)
        counts: Dict[Tuple[int, ...], Set[int]] = defaultdict(set)
        for pid in range_products:
            vals = sorted(by_product.get(pid, set()))
            for size in range(1, min(args.max_values, len(vals)) + 1):
                for combo in itertools.combinations(vals, size):
                    counts[combo].add(pid)

        # A candidate is interesting only if its observed support is neither
        # the whole range nor a singleton. Validate the exact legacy filter.
        candidates = sorted(
            ((combo, ids) for combo, ids in counts.items() if 1 < len(ids) < len(range_products)),
            key=lambda x: (-len(x[1]), len(x[0]), x[0]),
        )

        for combo, observed in candidates[:500]:
            returned = products_list(repo, range_id, combo)
            intended = observed
            results.append({
                "ProductRangeId": range_id,
                "AttributeValueIds": list(combo),
                "Values": [value_info.get(v, {}) for v in combo],
                "ObservedDatasetSupportCount": len(observed),
                "ObservedDatasetSupportProductIds": sorted(observed),
                "LegacyProductsListCount": len(returned),
                "LegacyProductsListProductIds": sorted(returned),
                "ExactDatasetGroup": returned == intended,
                "ExactDatasetGroupWithinInput": returned == intended and returned.issubset(set(input_ids)),
            })

    report = {
        "input_product_count": len(input_ids),
        "resolved_product_count": len(products),
        "pav_row_count": len(pav_rows),
        "ranges": {str(r): sum(1 for p in products.values() if p["ProductRangeId"] == r)
                   for r in sorted({p["ProductRangeId"] for p in products.values() if p["ProductRangeId"] is not None})},
        "max_candidate_filter_size": args.max_values,
        "candidate_count": len(results),
        "exact_candidates": sum(1 for r in results if r["ExactDatasetGroup"]),
        "results": results,
    }
    Path(args.output).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Input ProductIds: {len(input_ids)}")
    print(f"Resolved Products: {len(products)}")
    print(f"ProductAttributeValues rows: {len(pav_rows)}")
    print(f"Candidate filters tested: {len(results)}")
    print(f"Exact dataset groups found: {report['exact_candidates']}")
    print(f"Report written: {args.output}")


if __name__ == "__main__":
    main()
