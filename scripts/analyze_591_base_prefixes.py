"""Read-only analysis of base article prefixes in the 591-product dataset.

This script does not reduce articles. It treats the Product value in the input
(before any dot) as the article/base-code domain and reports prefix groups at
each possible prefix length. It then correlates each prefix group with the
resolved ProductIds and ProductAttributeValues so we can determine which
prefixes are meaningful candidates for reduction before using ProductsList.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.application_context import ApplicationContext
from repositories.pdm_repository import PDMRepository

CHUNK_SIZE = 100


def placeholders(count: int) -> str:
    return ", ".join("?" for _ in range(count))


def read_rows(path: Path):
    text = path.read_text(encoding="utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters="\t,;")
    except csv.Error:
        dialect = csv.excel_tab
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    if not reader.fieldnames or "ProductId" not in reader.fieldnames or "Product" not in reader.fieldnames:
        raise ValueError(f"Input must contain ProductId and Product. Columns: {reader.fieldnames}")
    rows = []
    for row in reader:
        pid = (row.get("ProductId") or "").strip()
        product = (row.get("Product") or "").strip()
        if pid and product:
            rows.append({
                "ProductId": int(pid),
                "Product": product.split(".", 1)[0],
                "Description": (row.get("Description") or "").strip(),
                "NewProduct": (row.get("NewProduct") or "").strip(),
            })
    return rows


def fetch_products(repo: PDMRepository, product_ids):
    found = {}
    conn = repo.get_connection()
    try:
        for start in range(0, len(product_ids), CHUNK_SIZE):
            chunk = product_ids[start:start + CHUNK_SIZE]
            cur = conn.cursor()
            cur.execute(
                f"SELECT ProductId, Product, ProductRangeId FROM Product WITH (NOLOCK) "
                f"WHERE ProductId IN ({placeholders(len(chunk))})",
                tuple(chunk),
            )
            for row in cur.fetchall():
                found[int(row.ProductId)] = {
                    "Product": str(row.Product),
                    "ProductRangeId": int(row.ProductRangeId) if row.ProductRangeId is not None else None,
                }
    finally:
        conn.close()
    return found


def fetch_pavs(repo: PDMRepository, product_ids):
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
                       av.Name AS ValueName, av.OrderCodeValue
                FROM ProductAttributeValues pav WITH (NOLOCK)
                INNER JOIN AttributeValue av WITH (NOLOCK) ON pav.AttributeValueId = av.AttributeValueId
                INNER JOIN Attribute a WITH (NOLOCK) ON av.AttributeId = a.AttributeId
                WHERE pav.ProductId IN ({placeholders(len(chunk))}) AND av.Status = 1
                """,
                tuple(chunk),
            )
            rows.extend(cur.fetchall())
    finally:
        conn.close()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--min-prefix", type=int, default=2)
    parser.add_argument("--max-prefix", type=int, default=None)
    parser.add_argument("--min-group", type=int, default=2)
    parser.add_argument("--output", default=".audit_tmp_591_base_prefixes.json")
    args = parser.parse_args()

    rows = read_rows(Path(args.input))
    input_ids = sorted({r["ProductId"] for r in rows})
    product_by_id = {r["ProductId"]: r["Product"] for r in rows}
    repo = PDMRepository(ApplicationContext())
    products = fetch_products(repo, input_ids)
    pav_rows = fetch_pavs(repo, input_ids)

    pav_by_product = defaultdict(set)
    value_info = {}
    for r in pav_rows:
        pid = int(r.ProductId)
        vid = int(r.AttributeValueId)
        pav_by_product[pid].add(vid)
        value_info[vid] = {
            "AttributeId": int(r.AttributeId),
            "AttributeName": str(r.AttributeName),
            "ValueName": str(r.ValueName),
            "OrderCodeValue": r.OrderCodeValue,
        }

    max_len = args.max_prefix or max((len(p) for p in product_by_id.values()), default=0)
    prefixes = []
    for length in range(args.min_prefix, max_len + 1):
        groups = defaultdict(list)
        for pid, product in product_by_id.items():
            if len(product) >= length:
                groups[product[:length]].append(pid)
        for prefix, pids in groups.items():
            if len(pids) >= args.min_group:
                ranges = Counter(products[pid]["ProductRangeId"] for pid in pids if pid in products)
                common = None
                for pid in pids:
                    vals = pav_by_product.get(pid, set())
                    common = set(vals) if common is None else common & vals
                variable_attrs = defaultdict(set)
                for pid in pids:
                    for vid in pav_by_product.get(pid, set()):
                        info = value_info[vid]
                        variable_attrs[info["AttributeId"]].add(vid)
                prefixes.append({
                    "PrefixLength": length,
                    "Prefix": prefix,
                    "ProductCount": len(pids),
                    "ProductIds": sorted(pids),
                    "ProductRanges": dict(ranges),
                    "CommonAttributeValueIds": sorted(common or set()),
                    "CommonValues": [value_info[v] for v in sorted(common or set())],
                    "VariableAttributeIds": sorted(variable_attrs),
                    "VariableAttributeValueIds": sorted({v for vals in variable_attrs.values() for v in vals}),
                })

    # Keep only maximal prefixes for each set of ProductIds. A shorter prefix
    # that has exactly the same Products is just a less-specific spelling of
    # the same candidate base group.
    by_product_set = defaultdict(list)
    for item in prefixes:
        by_product_set[frozenset(item["ProductIds"])].append(item)
    maximal = []
    for items in by_product_set.values():
        items.sort(key=lambda x: (-x["PrefixLength"], x["Prefix"]))
        maximal.append(items[0])
    maximal.sort(key=lambda x: (-x["ProductCount"], x["PrefixLength"], x["Prefix"]))

    report = {
        "input_product_count": len(input_ids),
        "resolved_product_count": len(products),
        "pav_row_count": len(pav_rows),
        "prefix_candidate_count": len(prefixes),
        "maximal_prefix_group_count": len(maximal),
        "maximal_prefix_groups": maximal,
        "note": "Prefix groups are article-number observations only. No prefix is declared a valid reduction until its Product set is validated with the legacy ProductsList filter logic.",
    }
    Path(args.output).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    print(f"Input ProductIds: {len(input_ids)}")
    print(f"Resolved Products: {len(products)}")
    print(f"ProductAttributeValues rows: {len(pav_rows)}")
    print(f"Prefix candidates: {len(prefixes)}")
    print(f"Maximal prefix groups: {len(maximal)}")
    print("Top prefix groups:")
    for item in maximal[:30]:
        print(
            f"  {item['Prefix']}  count={item['ProductCount']} "
            f"range={item['ProductRanges']} "
            f"common_pav={len(item['CommonAttributeValueIds'])}"
        )
    print(f"Report written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
