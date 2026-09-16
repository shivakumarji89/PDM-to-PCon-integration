"""Read-only combined analysis of article prefixes, PDM attributes, descriptions and legacy filters.

This script does not modify production code and does not perform article reduction.
It tests whether observed article-prefix families can be reproduced by the legacy
ProductsList filter and reports description consistency alongside the PDM data.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.application_context import ApplicationContext
from repositories.pdm_repository import PDMRepository

CHUNK_SIZE = 100


def placeholders(n: int) -> str:
    return ", ".join("?" for _ in range(n))


def read_rows(path: Path):
    text = path.read_text(encoding="utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters="\t,;")
    except csv.Error:
        dialect = csv.excel_tab
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    required = {"ProductId", "Product"}
    if not reader.fieldnames or not required <= set(reader.fieldnames):
        raise ValueError(f"Input must contain ProductId and Product. Columns: {reader.fieldnames}")
    rows = []
    for row in reader:
        raw_id = (row.get("ProductId") or "").strip()
        product = (row.get("Product") or "").strip().split(".", 1)[0]
        if raw_id and product:
            rows.append({
                "ProductId": int(raw_id),
                "Product": product,
                "Description": (row.get("Description") or "").strip(),
                "NewProduct": (row.get("NewProduct") or "").strip(),
            })
    return rows


def fetch_products(repo, ids):
    found = {}
    conn = repo.get_connection()
    try:
        for start in range(0, len(ids), CHUNK_SIZE):
            chunk = ids[start:start + CHUNK_SIZE]
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


def fetch_pavs(repo, ids):
    rows = []
    conn = repo.get_connection()
    try:
        for start in range(0, len(ids), CHUNK_SIZE):
            chunk = ids[start:start + CHUNK_SIZE]
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


def build_xml(value_info, value_ids):
    ids = list(dict.fromkeys(int(v) for v in value_ids))
    return "<attributes>" + "".join(
        f'<attribute attributeid="{int(value_info[v]["AttributeId"])}" attributevalueid="{v}" />'
        for v in ids
    ) + "</attributes>"


def products_list(cur, range_id, xml):
    cur.execute("EXEC dbo.ProductsList ?, ?, ?", (range_id, 1, xml))
    columns = [d[0] for d in cur.description or ()]
    index = next((i for i, name in enumerate(columns) if str(name).lower() == "productid"), None)
    if index is None:
        raise RuntimeError(f"ProductsList did not return ProductId. Columns: {columns!r}")
    return {int(row[index]) for row in cur.fetchall()}


def maximal_prefix_groups(product_to_code, min_group):
    candidates = []
    max_len = max((len(code) for code in product_to_code.values()), default=0)
    for length in range(2, max_len + 1):
        groups = defaultdict(list)
        for pid, code in product_to_code.items():
            if len(code) >= length:
                groups[code[:length]].append(pid)
        for prefix, pids in groups.items():
            if len(pids) >= min_group:
                candidates.append((length, prefix, sorted(pids)))

    by_set = defaultdict(list)
    for length, prefix, pids in candidates:
        by_set[frozenset(pids)].append((length, prefix, pids))
    maximal = []
    for items in by_set.values():
        maximal.append(max(items, key=lambda x: (x[0], x[1])))
    return sorted(maximal, key=lambda x: (-len(x[2]), x[0], x[1]))


def common_values(pids, by_product):
    result = None
    for pid in pids:
        vals = by_product.get(pid, set())
        result = set(vals) if result is None else result & vals
    return result or set()


def exact_filters_for_group(cur, pids, range_id, common, value_info, max_values):
    if not common:
        return []
    ordered = sorted(common)
    exact = []
    for size in range(1, min(max_values, len(ordered)) + 1):
        for combo in itertools.combinations(ordered, size):
            returned = products_list(cur, range_id, build_xml(value_info, combo))
            if returned == set(pids):
                exact.append(tuple(combo))
        if exact:
            break
    return exact


def describe_group(pids, prefix, rows_by_id, products, by_product, value_info, cur, max_values):
    ranges = Counter(products[pid]["ProductRangeId"] for pid in pids if pid in products)
    descriptions = Counter(rows_by_id[pid]["Description"] for pid in pids if rows_by_id[pid]["Description"])
    common = common_values(pids, by_product)
    result = {
        "Prefix": prefix,
        "PrefixLength": len(prefix),
        "ProductCount": len(pids),
        "ProductIds": pids,
        "ProductRanges": dict(ranges),
        "DescriptionCount": len(descriptions),
        "Descriptions": [{"Description": d, "Count": n} for d, n in descriptions.most_common()],
        "CommonAttributeValueIds": sorted(common),
        "CommonValues": [value_info[v] for v in sorted(common)],
        "ExactLegacyFilters": [],
        "ExactLegacyFilterCount": 0,
    }

    if len(ranges) == 1:
        range_id = next(iter(ranges))
        exact = exact_filters_for_group(cur, pids, range_id, common, value_info, max_values)
        result["ExactLegacyFilters"] = [
            {"AttributeValueIds": list(combo), "Values": [value_info[v] for v in combo]}
            for combo in exact
        ]
        result["ExactLegacyFilterCount"] = len(exact)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--min-group", type=int, default=24)
    parser.add_argument("--max-values", type=int, default=3)
    parser.add_argument("--output", default=".audit_tmp_591_prefix_filter_description.json")
    args = parser.parse_args()

    rows = read_rows(Path(args.input))
    rows_by_id = {r["ProductId"]: r for r in rows}
    ids = sorted(rows_by_id)
    repo = PDMRepository(ApplicationContext())
    products = fetch_products(repo, ids)
    pav_rows = fetch_pavs(repo, ids)

    by_product = defaultdict(set)
    value_info = {}
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

    product_to_code = {pid: rows_by_id[pid]["Product"] for pid in ids}
    groups = maximal_prefix_groups(product_to_code, args.min_group)

    conn = repo.get_connection()
    try:
        cur = conn.cursor()
        results = []
        for index, (length, prefix, pids) in enumerate(groups, 1):
            print(f"Analyzing {index}/{len(groups)}: {prefix} ({len(pids)})", flush=True)
            results.append(describe_group(pids, prefix, rows_by_id, products, by_product, value_info, cur, args.max_values))
    finally:
        conn.close()

    exact = [r for r in results if r["ExactLegacyFilterCount"]]
    description_consistent = [r for r in results if r["DescriptionCount"] <= 1]
    report = {
        "input_product_count": len(ids),
        "resolved_product_count": len(products),
        "pav_row_count": len(pav_rows),
        "min_group": args.min_group,
        "max_filter_values_tested": args.max_values,
        "maximal_prefix_group_count": len(results),
        "groups_with_exact_legacy_filter": len(exact),
        "groups_with_single_description_or_empty": len(description_consistent),
        "groups": results,
        "note": "Descriptions are reported as evidence only. Product prefix is an article-number observation. ProductsList remains the authoritative filter-equivalence test. No reduction is performed.",
    }
    Path(args.output).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"Input ProductIds: {len(ids)}")
    print(f"Resolved Products: {len(products)}")
    print(f"ProductAttributeValues rows: {len(pav_rows)}")
    print(f"Maximal prefix groups (>= {args.min_group}): {len(results)}")
    print(f"Groups with exact legacy filter: {len(exact)}")
    print(f"Groups with single description or empty: {len(description_consistent)}")
    print("Exact-filter groups:")
    for group in exact:
        filters = group["ExactLegacyFilters"]
        print(f"  {group['Prefix']} count={group['ProductCount']} descriptions={group['DescriptionCount']} exact_filters={len(filters)}")
        for item in filters[:3]:
            print(f"    filter={item['AttributeValueIds']} values={[v['ValueName'] for v in item['Values']]}")
    print(f"Report written: {args.output}")


if __name__ == "__main__":
    main()
