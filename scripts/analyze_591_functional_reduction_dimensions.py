"""Read-only analysis separating functional/pre-dot PDM attributes from order-code attributes.

The after-dot/order-code side is intentionally not redesigned here. This script
uses ProductAttributeValues.OrderCodeValue as the legacy signal: non-empty
OrderCodeValue values are reported as order-code dimensions, while empty values
are reported as functional dimensions to investigate for pre-dot reduction.

No reduction is performed and no production code is modified.
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
    return sorted(
        (max(items, key=lambda x: (x[0], x[1])) for items in by_set.values()),
        key=lambda x: (-len(x[2]), x[0], x[1]),
    )


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


def partition_values(pids, by_product, value_info):
    all_values = defaultdict(Counter)
    for pid in pids:
        for vid in by_product.get(pid, set()):
            info = value_info[vid]
            kind = "order_code" if (info["OrderCodeValue"] or "").strip() else "functional"
            all_values[kind][vid] += 1

    result = {}
    total = len(pids)
    for kind, counter in all_values.items():
        by_attr = defaultdict(list)
        for vid, count in counter.items():
            by_attr[value_info[vid]["AttributeId"]].append((vid, count))
        attrs = []
        for aid, values in sorted(by_attr.items()):
            values.sort(key=lambda x: (-x[1], value_info[x[0]]["DisplayOrdinal"] or 0, x[0]))
            rows = []
            for vid, count in values:
                info = value_info[vid]
                rows.append({
                    "AttributeValueId": vid,
                    "AttributeId": info["AttributeId"],
                    "AttributeName": info["AttributeName"],
                    "ValueName": info["ValueName"],
                    "OrderCodeValue": info["OrderCodeValue"],
                    "Count": count,
                    "Fraction": count / total,
                    "FixedForGroup": count == total,
                })
            attrs.append({
                "AttributeId": aid,
                "AttributeName": value_info[values[0][0]]["AttributeName"],
                "Values": rows,
            })
        result[kind] = attrs
    return result


def common_kind_values(pids, by_product, value_info, kind):
    result = None
    for pid in pids:
        vals = {
            vid for vid in by_product.get(pid, set())
            if ((value_info[vid]["OrderCodeValue"] or "").strip() != "") == (kind == "order_code")
        }
        result = vals if result is None else result & vals
    return result or set()


def exact_functional_filters(cur, pids, range_id, common_ids, value_info, max_values):
    if not common_ids:
        return []
    ordered = sorted(common_ids)
    target = set(pids)
    exact = []
    for size in range(1, min(max_values, len(ordered)) + 1):
        for combo in itertools.combinations(ordered, size):
            returned = products_list(cur, range_id, build_xml(value_info, combo))
            if returned == target:
                exact.append(tuple(combo))
        if exact:
            break
    return exact


def article_variation(pids, prefix, rows_by_id):
    codes = [rows_by_id[pid]["Product"] for pid in pids]
    max_len = max((len(c) for c in codes), default=len(prefix))
    positions = []
    for pos in range(len(prefix), max_len):
        chars = Counter(c[pos] if pos < len(c) else "<END>" for c in codes)
        if len(chars) > 1:
            positions.append({"Position": pos + 1, "Values": dict(chars)})
    return positions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--min-group", type=int, default=24)
    parser.add_argument("--max-values", type=int, default=3)
    parser.add_argument("--output", default=".audit_tmp_591_functional_reduction_dimensions.json")
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

    groups = maximal_prefix_groups({pid: rows_by_id[pid]["Product"] for pid in ids}, args.min_group)
    conn = repo.get_connection()
    try:
        cur = conn.cursor()
        results = []
        for index, (_, prefix, pids) in enumerate(groups, 1):
            print(f"Analyzing {index}/{len(groups)}: {prefix} ({len(pids)})", flush=True)
            ranges = Counter(products[pid]["ProductRangeId"] for pid in pids if pid in products)
            common_functional = common_kind_values(pids, by_product, value_info, "functional")
            common_order = common_kind_values(pids, by_product, value_info, "order_code")
            exact = []
            if len(ranges) == 1:
                range_id = next(iter(ranges))
                exact = exact_functional_filters(cur, pids, range_id, common_functional, value_info, args.max_values)

            descriptions = Counter(rows_by_id[pid]["Description"] for pid in pids if rows_by_id[pid]["Description"])
            results.append({
                "Prefix": prefix,
                "PrefixLength": len(prefix),
                "ProductCount": len(pids),
                "ProductIds": pids,
                "ProductRanges": dict(ranges),
                "DescriptionCount": len(descriptions),
                "Descriptions": [{"Description": d, "Count": n} for d, n in descriptions.most_common()],
                "FunctionalCommonValues": [value_info[v] for v in sorted(common_functional)],
                "OrderCodeCommonValues": [value_info[v] for v in sorted(common_order)],
                "AttributePartition": partition_values(pids, by_product, value_info),
                "ExactLegacyFiltersUsingFunctionalCommonValues": [
                    {"AttributeValueIds": list(combo), "Values": [value_info[v] for v in combo]}
                    for combo in exact
                ],
                "ArticlePositionsThatVaryAfterPrefix": article_variation(pids, prefix, rows_by_id),
            })
    finally:
        conn.close()

    exact_groups = [r for r in results if r["ExactLegacyFiltersUsingFunctionalCommonValues"]]
    report = {
        "input_product_count": len(ids),
        "resolved_product_count": len(products),
        "pav_row_count": len(pav_rows),
        "min_group": args.min_group,
        "max_functional_filter_values_tested": args.max_values,
        "maximal_prefix_group_count": len(results),
        "groups_with_exact_legacy_filter_using_only_functional_common_values": len(exact_groups),
        "groups": results,
        "classification_rule": "OrderCodeValue non-empty => order-code/after-dot dimension; empty => functional/pre-dot dimension, matching the legacy code's physical-vs-functional distinction.",
        "note": "This is investigation only. The after-dot article logic is not changed and no reduction is performed.",
    }
    Path(args.output).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"Input ProductIds: {len(ids)}")
    print(f"Resolved Products: {len(products)}")
    print(f"ProductAttributeValues rows: {len(pav_rows)}")
    print(f"Maximal prefix groups (>= {args.min_group}): {len(results)}")
    print(f"Groups with exact legacy filter using only functional common values: {len(exact_groups)}")
    print("Exact functional-filter groups:")
    for group in exact_groups:
        print(f"  {group['Prefix']} count={group['ProductCount']} filters={len(group['ExactLegacyFiltersUsingFunctionalCommonValues'])}")
        for item in group["ExactLegacyFiltersUsingFunctionalCommonValues"][:3]:
            print(f"    filter={item['AttributeValueIds']} values={[v['ValueName'] for v in item['Values']]}")
    print(f"Report written: {args.output}")


if __name__ == "__main__":
    main()
