"""Read-only derivation of reduction candidates from legacy PDM filter semantics."""

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
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters="\t,;")
    except csv.Error:
        dialect = csv.excel_tab
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    if not reader.fieldnames or "ProductId" not in reader.fieldnames:
        raise ValueError(f"Input must contain ProductId. Columns: {reader.fieldnames}")
    return sorted({int((r.get("ProductId") or "").strip()) for r in reader if (r.get("ProductId") or "").strip()})


def fetch_products(repo: PDMRepository, product_ids: List[int]) -> Dict[int, dict]:
    found: Dict[int, dict] = {}
    conn = repo.get_connection()
    try:
        for start in range(0, len(product_ids), CHUNK_SIZE):
            chunk = product_ids[start:start + CHUNK_SIZE]
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
            chunk = product_ids[start:start + CHUNK_SIZE]
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
        f'<attribute attributeid="{int(value_info[v]["AttributeId"])}" attributevalueid="{v}" />'
        for v in ids
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


def smallest_filters_per_support(candidates):
    best = {}
    for combo, ids in candidates:
        key = frozenset(ids)
        current = best.get(key)
        if current is None or (len(combo), combo) < (len(current[0]), current[0]):
            best[key] = (combo, ids)
    return list(best.values())


def attribute_level_profile(product_ids: Set[int], by_product: Dict[int, Set[int]], value_info: Dict[int, dict]):
    """Describe which attribute IDs are fixed and which have multiple values inside a group."""
    frequency = defaultdict(int)
    for pid in product_ids:
        for value_id in by_product.get(pid, set()):
            frequency[value_id] += 1

    by_attribute = defaultdict(list)
    for value_id, count in frequency.items():
        info = value_info[value_id]
        by_attribute[info["AttributeId"]].append((value_id, count))

    profile = []
    for attribute_id, values in sorted(by_attribute.items()):
        values.sort(key=lambda item: (-item[1], value_info[item[0]].get("DisplayOrdinal") or 0, item[0]))
        info_rows = []
        for value_id, count in values:
            info = value_info[value_id]
            info_rows.append({
                "AttributeValueId": value_id,
                "ValueName": info["ValueName"],
                "OrderCodeValue": info["OrderCodeValue"],
                "Count": count,
                "Fraction": count / len(product_ids),
            })
        fixed = [row for row in info_rows if row["Count"] == len(product_ids)]
        variable = [row for row in info_rows if row["Count"] < len(product_ids)]
        profile.append({
            "AttributeId": attribute_id,
            "AttributeName": value_info[values[0][0]]["AttributeName"],
            "FixedValues": fixed,
            "VariableValues": variable,
            "ValueCount": len(info_rows),
        })
    return profile


def make_group_candidate(
    product_ids: Set[int],
    by_product: Dict[int, Set[int]],
    value_info: Dict[int, dict],
    product_to_code: Dict[int, str],
    product_to_description: Dict[int, str],
    product_range_id: int,
    filter_ids: Tuple[int, ...],
) -> dict:
    profile = attribute_level_profile(product_ids, by_product, value_info)
    fixed = [value for attr in profile for value in attr["FixedValues"]]
    variable = [value for attr in profile for value in attr["VariableValues"]]
    # A Product group is a candidate reduction group only when it is a proper
    # subset of the range. The filter is the proof of group membership; the
    # reduction engine still needs to decide how article code is synthesized.
    return {
        "ProductRangeId": int(product_range_id),
        "FilterAttributeValueIds": list(filter_ids),
        "FilterValues": [value_info[v] for v in filter_ids],
        "ProductIds": sorted(product_ids),
        "ProductCount": len(product_ids),
        "ProductCodes": sorted(product_to_code[p] for p in product_ids),
        "Descriptions": sorted(set(product_to_description[p] for p in product_ids)),
        "DistinctProductCount": len(product_ids),
        "AttributeProfile": profile,
        "FixedAttributeValues": fixed,
        "VariableAttributeValues": variable,
    }


def compute_reduction_partition(
    groups: List[dict],
    all_product_ids: Set[int],
) -> Tuple[List[dict], Set[int]]:
    """Choose a deterministic non-overlapping partition from validated groups.

    Groups are ordered by descending coverage and then by shortest filter. This
    is an analysis policy only; it is intentionally separate from PDM filter
    semantics, which remain the membership oracle.
    """
    selected: List[dict] = []
    uncovered = set(all_product_ids)
    ordered = sorted(
        groups,
        key=lambda g: (-g["ProductCount"], len(g["FilterAttributeValueIds"]), g["ProductIds"]),
    )
    for group in ordered:
        group_ids = set(group["ProductIds"])
        if not group_ids or not group_ids <= uncovered:
            continue
        selected.append(group)
        uncovered -= group_ids
        if not uncovered:
            break
    return selected, uncovered


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
    for row in pav_rows:
        pid = int(row.ProductId)
        vid = int(row.AttributeValueId)
        by_product[pid].add(vid)
        value_info[vid] = {
            "AttributeId": int(row.AttributeId),
            "AttributeName": str(row.AttributeName),
            "ValueName": str(row.ValueName),
            "OrderCodeValue": row.OrderCodeValue,
            "DisplayOrder": int(row.DisplayOrder) if row.DisplayOrder is not None else None,
            "DisplayOrdinal": int(row.DisplayOrdinal) if row.DisplayOrdinal is not None else None,
        }

    product_to_code = {pid: products[pid]["Product"] for pid in products}
    product_to_description = {pid: str(products[pid]["Product"]) for pid in products}

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
            selected = candidates[:args.limit_per_range]

            print(f"Range {range_id}: {len(range_products)} input products; {len(selected)} support patterns to validate", flush=True)
            for index, (combo, observed) in enumerate(selected, 1):
                returned = products_list(cur, int(range_id), build_xml(value_info, combo))
                intended = set(observed)
                exact = returned == intended
                print(f"  validated {index}/{len(selected)}; support={len(intended)}; legacy={len(returned)}; exact={exact}", flush=True)
                if exact:
                    exact_groups.append(make_group_candidate(
                        intended,
                        by_product,
                        value_info,
                        product_to_code,
                        product_to_description,
                        int(range_id),
                        tuple(combo),
                    ))
    finally:
        conn.close()

    unique_groups = {}
    for group in exact_groups:
        key = frozenset(group["ProductIds"])
        current = unique_groups.get(key)
        if current is None or (len(group["FilterAttributeValueIds"]), group["FilterAttributeValueIds"]) < (
            len(current["FilterAttributeValueIds"]), current["FilterAttributeValueIds"]
        ):
            unique_groups[key] = group

    unique_group_list = list(unique_groups.values())
    selected_groups, uncovered = compute_reduction_partition(unique_group_list, input_set)

    size_distribution = defaultdict(int)
    for group in unique_group_list:
        size_distribution[group["ProductCount"]] += 1
    selected_size_distribution = defaultdict(int)
    for group in selected_groups:
        selected_size_distribution[group["ProductCount"]] += 1

    covered_by_selected = set().union(*(set(g["ProductIds"]) for g in selected_groups)) if selected_groups else set()

    report = {
        "input_product_count": len(input_ids),
        "resolved_product_count": len(products),
        "missing_product_ids": sorted(input_set - set(products)),
        "pav_row_count": len(pav_rows),
        "ranges": {str(r): sum(1 for p in products.values() if p["ProductRangeId"] == r) for r in ranges},
        "max_candidate_filter_size": args.max_values,
        "support_patterns_validated_per_range": args.limit_per_range,
        "exact_filter_groups_found": len(exact_groups),
        "unique_exact_product_groups_found": len(unique_group_list),
        "unique_group_size_distribution": dict(sorted(size_distribution.items())),
        "selected_non_overlapping_group_count": len(selected_groups),
        "selected_non_overlapping_group_size_distribution": dict(sorted(selected_size_distribution.items())),
        "products_covered_by_selected_groups": len(covered_by_selected),
        "products_not_covered_by_selected_groups": len(uncovered),
        "selected_groups": selected_groups,
        "unique_exact_groups": unique_group_list,
        "uncovered_product_ids": sorted(uncovered),
        "note": "ProductsList is used only as the legacy filter truth function. The selected partition is an analysis policy and is not yet the final article reduction algorithm.",
    }
    Path(args.output).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"Input ProductIds: {len(input_ids)}")
    print(f"Resolved Products: {len(products)}")
    print(f"ProductAttributeValues rows: {len(pav_rows)}")
    print(f"Exact filter groups found: {len(exact_groups)}")
    print(f"Unique exact Product groups found: {len(unique_group_list)}")
    print(f"Unique group-size distribution: {dict(sorted(size_distribution.items()))}")
    print(f"Selected non-overlapping groups: {len(selected_groups)}")
    print(f"Products covered by selected groups: {len(covered_by_selected)}")
    print(f"Products not covered by selected groups: {len(uncovered)}")
    print(f"Report written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
