"""Read-only analysis of the 591-product dataset using legacy PDM filter semantics."""

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
    dialect = csv.excel_tab
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters="\t,;")
    except csv.Error:
        pass
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    if not reader.fieldnames or "ProductId" not in reader.fieldnames:
        raise ValueError(f"Input must contain ProductId. Columns: {reader.fieldnames}")
    return sorted({int((r.get("ProductId") or "").strip()) for r in reader if (r.get("ProductId") or "").strip()})


def fetch_products(repo: PDMRepository, product_ids: List[int]) -> Dict[int, dict]:
    found: Dict[int, dict] = {}
    conn = repo.get_connection()
    try:
        for start in range(0, len(product_ids), CHUNK_SIZE):
            chunk = product_ids[start : start + CHUNK_SIZE]
            cur = conn.cursor()
            cur.execute(
                f"SELECT ProductId, Product, ProductRangeId, ProductCodeId, Status, NewProduct, IsSuperProduct "
                f"FROM Product WITH (NOLOCK) WHERE ProductId IN ({placeholders(len(chunk))})",
                tuple(chunk),
            )
            for row in cur.fetchall():
                found[int(row.ProductId)] = {
                    "Product": str(row.Product),
                    "ProductRangeId": int(row.ProductRangeId) if row.ProductRangeId is not None else None,
                    "ProductCodeId": int(row.ProductCodeId) if row.ProductCodeId is not None else None,
                    "Status": int(row.Status) if row.Status is not None else None,
                    "NewProduct": int(row.NewProduct) if row.NewProduct is not None else 0,
                    "IsSuperProduct": int(row.IsSuperProduct) if row.IsSuperProduct is not None else 0,
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
            cur = conn.cursor()
            cur.execute(
                f"""
                SELECT pav.ProductId, pav.AttributeValueId,
                       av.AttributeId, a.Name AS AttributeName,
                       av.Name AS ValueName, av.OrderCodeValue,
                       a.DisplayOrder, av.DisplayOrdinal
                FROM ProductAttributeValues pav WITH (NOLOCK)
                INNER JOIN AttributeValue av WITH (NOLOCK) ON pav.AttributeValueId = av.AttributeValueId
                INNER JOIN Attribute a WITH (NOLOCK) ON av.AttributeId = a.AttributeId
                WHERE pav.ProductId IN ({placeholders(len(chunk))}) AND av.Status = 1
                ORDER BY pav.ProductId, a.DisplayOrder, av.DisplayOrdinal
                """,
                tuple(chunk),
            )
            rows.extend(cur.fetchall())
    finally:
        conn.close()
    return rows


def build_xml(value_info: Dict[int, dict], value_ids: Iterable[int]) -> str:
    ids = list(dict.fromkeys(int(v) for v in value_ids))
    return "<attributes>" + "".join(
        f'<attribute attributeid="{int(value_info[v]["AttributeId"])}" attributevalueid="{v}" />' for v in ids
    ) + "</attributes>"


def products_list(cur, product_range_id: int, xml: str) -> Set[int]:
    cur.execute("EXEC dbo.ProductsList ?, ?, ?", (product_range_id, 1, xml))
    columns = [d[0] for d in cur.description or ()]
    index = next((i for i, name in enumerate(columns) if str(name).lower() == "productid"), None)
    if index is None:
        raise RuntimeError(f"ProductsList did not return ProductId. Columns: {columns!r}")
    return {int(row[index]) for row in cur.fetchall()}


def build_candidate_combinations(range_products: List[int], by_product: Dict[int, Set[int]], max_values: int):
    counts: Dict[Tuple[int, ...], Set[int]] = defaultdict(set)
    for pid in range_products:
        vals = sorted(by_product.get(pid, set()))
        for size in range(1, min(max_values, len(vals)) + 1):
            for combo in itertools.combinations(vals, size):
                counts[combo].add(pid)
    return counts


def smallest_filters_per_support(
    candidates: Iterable[Tuple[Tuple[int, ...], Set[int]]]
) -> List[Tuple[Tuple[int, ...], Set[int]]]:
    """Keep the shortest filters for each identical observed support set."""
    best: Dict[frozenset, Tuple[Tuple[int, ...], Set[int]]] = {}
    for combo, ids in candidates:
        key = frozenset(ids)
        current = best.get(key)
        if current is None or (len(combo), combo) < (len(current[0]), current[0]):
            best[key] = (combo, ids)
    return list(best.values())


def support_key(ids: Iterable[int]) -> frozenset:
    return frozenset(ids)


def filter_minus_common(
    product_ids: Set[int],
    by_product: Dict[int, Set[int]],
) -> Tuple[Set[int], Dict[int, int]]:
    """Return attribute-value IDs common to every Product and their frequencies."""
    common: Set[int] | None = None
    frequencies: Dict[int, int] = defaultdict(int)
    for pid in product_ids:
        values = by_product.get(pid, set())
        for value in values:
            frequencies[value] += 1
        common = set(values) if common is None else common & values
    return common or set(), dict(frequencies)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--max-values", type=int, default=3)
    parser.add_argument("--limit-per-range", type=int, default=30)
    parser.add_argument("--output", default=".audit_tmp_591_candidate_filters.json")
    args = parser.parse_args()

    input_ids = read_product_ids(Path(args.input))
    input_set = set(input_ids)
    repo = PDMRepository(ApplicationContext())
    products = fetch_products(repo, input_ids)
    pav_rows = fetch_pavs(repo, input_ids)

    by_product: Dict[int, Set[int]] = defaultdict(set)
    value_info: Dict[int, dict] = {}
    value_to_products: Dict[int, Set[int]] = defaultdict(set)
    for row in pav_rows:
        pid = int(row.ProductId)
        vid = int(row.AttributeValueId)
        by_product[pid].add(vid)
        value_to_products[vid].add(pid)
        value_info[vid] = {
            "AttributeId": int(row.AttributeId),
            "AttributeName": str(row.AttributeName),
            "ValueName": str(row.ValueName),
            "OrderCodeValue": row.OrderCodeValue,
            "DisplayOrder": int(row.DisplayOrder) if row.DisplayOrder is not None else None,
            "DisplayOrdinal": int(row.DisplayOrdinal) if row.DisplayOrdinal is not None else None,
        }

    report_results = []
    exact_groups = []
    ranges = sorted({p["ProductRangeId"] for p in products.values() if p["ProductRangeId"] is not None})
    conn = repo.get_connection()
    try:
        cur = conn.cursor()
        for range_id in ranges:
            range_products = sorted(pid for pid, p in products.items() if p["ProductRangeId"] == range_id)
            counts = build_candidate_combinations(range_products, by_product, args.max_values)
            candidates = [(combo, ids) for combo, ids in counts.items() if 1 < len(ids) < len(range_products)]
            candidates = smallest_filters_per_support(candidates)
            candidates.sort(key=lambda item: (-len(item[1]), len(item[0]), item[0]))
            selected = candidates[: args.limit_per_range]

            print(f"Range {range_id}: {len(range_products)} input products; {len(selected)} support patterns to validate", flush=True)

            for index, (combo, observed) in enumerate(selected, 1):
                returned = products_list(cur, int(range_id), build_xml(value_info, combo))
                intended = set(observed)
                exact = returned == intended
                item = {
                    "ProductRangeId": int(range_id),
                    "AttributeValueIds": list(combo),
                    "Values": [value_info[v] for v in combo],
                    "ObservedDatasetSupportCount": len(intended),
                    "ObservedDatasetSupportProductIds": sorted(intended),
                    "LegacyProductsListCount": len(returned),
                    "LegacyProductsListProductIds": sorted(returned),
                    "ExactDatasetGroup": exact,
                    "LegacyOnlyProductIds": sorted(returned - intended),
                    "DatasetOnlyProductIds": sorted(intended - returned),
                    "ExactDatasetGroupWithinInput": exact and returned.issubset(input_set),
                }
                if exact:
                    common, frequencies = filter_minus_common(intended, by_product)
                    variable = sorted(v for v, frequency in frequencies.items() if frequency < len(intended))
                    item["CommonAttributeValueIds"] = sorted(common)
                    item["CommonValues"] = [value_info[v] for v in sorted(common)]
                    item["VariableAttributeValueIds"] = variable
                    item["VariableValues"] = [value_info[v] for v in variable]
                    item["VariableValueCounts"] = {str(v): frequencies[v] for v in variable}
                    exact_groups.append(item)
                report_results.append(item)
                print(f"  validated {index}/{len(selected)}; support={len(intended)}; legacy={len(returned)}; exact={exact}", flush=True)
    finally:
        conn.close()

    support_counts = defaultdict(int)
    for result in exact_groups:
        support_counts[result["ObservedDatasetSupportCount"]] += 1

    # De-duplicate exact groups by Product support. This is the actual set of
    # groups that the validation discovered, independent of how many filters
    # happen to reproduce each group.
    unique_groups: Dict[frozenset, dict] = {}
    for result in exact_groups:
        key = support_key(result["ObservedDatasetSupportProductIds"])
        current = unique_groups.get(key)
        if current is None or (len(result["AttributeValueIds"]), result["AttributeValueIds"]) < (
            len(current["AttributeValueIds"]), current["AttributeValueIds"]
        ):
            unique_groups[key] = result

    unique_support_counts = defaultdict(int)
    for result in unique_groups.values():
        unique_support_counts[result["ObservedDatasetSupportCount"]] += 1

    report = {
        "input_product_count": len(input_ids),
        "resolved_product_count": len(products),
        "missing_product_ids": sorted(input_set - set(products)),
        "pav_row_count": len(pav_rows),
        "ranges": {str(r): sum(1 for p in products.values() if p["ProductRangeId"] == r) for r in ranges},
        "max_candidate_filter_size": args.max_values,
        "support_patterns_validated_per_range": args.limit_per_range,
        "candidate_support_patterns_validated": len(report_results),
        "exact_filter_groups_found": len(exact_groups),
        "unique_exact_product_groups_found": len(unique_groups),
        "exact_filter_group_size_distribution": dict(sorted(support_counts.items())),
        "unique_exact_product_group_size_distribution": dict(sorted(unique_support_counts.items())),
        "unique_exact_groups": list(unique_groups.values()),
        "exact_groups": exact_groups,
        "results": report_results,
        "note": "ProductsList is used only as the legacy filter truth function. This report does not implement article reduction.",
    }
    Path(args.output).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"Input ProductIds: {len(input_ids)}")
    print(f"Resolved Products: {len(products)}")
    print(f"ProductAttributeValues rows: {len(pav_rows)}")
    print(f"Support patterns validated: {len(report_results)}")
    print(f"Exact filter groups found: {len(exact_groups)}")
    print(f"Unique exact Product groups found: {len(unique_groups)}")
    print(f"Unique group-size distribution: {dict(sorted(unique_support_counts.items()))}")
    print(f"Report written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
