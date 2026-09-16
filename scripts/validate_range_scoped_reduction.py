"""Validate ProductRange-scoped reduction discovery without repeated ProductsList calls.

Read-only diagnostic. It reproduces the legacy ProductsList membership rule
in memory after loading Product/PAV data once:
- candidates must belong to the same ProductRange;
- every selected AttributeValueId must be present on the Product;
- eligible Products are represented by the supplied dataset.

This deliberately excludes values with OrderCodeValue because those dimensions
belong to the post-dot/order-code side of the article.
"""
from __future__ import annotations

import argparse
import csv
import itertools
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.application_context import ApplicationContext
from repositories.pdm_repository import PDMRepository

CHUNK = 100


def ph(n: int) -> str:
    return ",".join("?" for _ in range(n))


def read_input(path: Path):
    text = path.read_text(encoding="utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters="\t,;")
    except csv.Error:
        dialect = csv.excel_tab
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    if not reader.fieldnames or "ProductId" not in reader.fieldnames or "Product" not in reader.fieldnames:
        raise ValueError(f"Input must contain ProductId and Product. Columns: {reader.fieldnames}")
    rows = {}
    for row in reader:
        raw_id = (row.get("ProductId") or "").strip()
        raw_code = (row.get("Product") or "").strip()
        if raw_id and raw_code:
            rows[int(raw_id)] = raw_code.split(".", 1)[0]
    return rows


def fetch(repo: PDMRepository, ids: list[int]):
    products = {}
    by_product = defaultdict(set)
    value_info = {}
    conn = repo.get_connection()
    try:
        for start in range(0, len(ids), CHUNK):
            chunk = ids[start:start + CHUNK]
            cur = conn.cursor()
            cur.execute(
                f"SELECT ProductId, Product, ProductRangeId, Status, NewProduct "
                f"FROM Product WITH (NOLOCK) WHERE ProductId IN ({ph(len(chunk))})",
                tuple(chunk),
            )
            for r in cur.fetchall():
                products[int(r.ProductId)] = {
                    "code": str(r.Product),
                    "range": int(r.ProductRangeId),
                    "status": int(r.Status) if r.Status is not None else None,
                    "new_product": int(r.NewProduct) if r.NewProduct is not None else 0,
                }

            cur.execute(
                f"""SELECT pav.ProductId, pav.AttributeValueId, av.AttributeId,
                           a.Name AS AttributeName, av.Name AS ValueName,
                           av.OrderCodeValue
                    FROM ProductAttributeValues pav WITH (NOLOCK)
                    INNER JOIN AttributeValue av WITH (NOLOCK)
                      ON pav.AttributeValueId = av.AttributeValueId
                    INNER JOIN Attribute a WITH (NOLOCK)
                      ON av.AttributeId = a.AttributeId
                    WHERE pav.ProductId IN ({ph(len(chunk))})
                      AND av.Status = 1""",
                tuple(chunk),
            )
            for r in cur.fetchall():
                pid = int(r.ProductId)
                vid = int(r.AttributeValueId)
                by_product[pid].add(vid)
                value_info[vid] = {
                    "AttributeId": int(r.AttributeId),
                    "AttributeName": str(r.AttributeName),
                    "ValueName": str(r.ValueName),
                    "OrderCodeValue": r.OrderCodeValue,
                }
    finally:
        conn.close()
    return products, by_product, value_info


def maximal_prefix_groups(codes: dict[int, str], min_group: int):
    candidates = []
    max_len = max((len(code) for code in codes.values()), default=0)
    for length in range(2, max_len + 1):
        groups = defaultdict(list)
        for pid, code in codes.items():
            if len(code) >= length:
                groups[code[:length]].append(pid)
        for prefix, pids in groups.items():
            if len(pids) >= min_group:
                candidates.append((length, prefix, sorted(pids)))

    by_set = defaultdict(list)
    for item in candidates:
        by_set[frozenset(item[2])].append(item)
    return sorted(
        (max(items, key=lambda item: (item[0], item[1])) for items in by_set.values()),
        key=lambda item: (-len(item[2]), item[0], item[1]),
    )


def eligible_product_ids(products, dataset_ids, range_id):
    # ProductsList's range/eligibility rule, restricted to the supplied dataset.
    return {
        pid for pid in dataset_ids
        if pid in products
        and products[pid]["range"] == range_id
        and (products[pid]["new_product"] == 1 or any(True for _ in [pid]))
    }


def legacy_in_memory(products, pavs, dataset_ids, range_id, values):
    """Return the supplied-dataset equivalent of dbo.ProductsList for values.

    The legacy procedure requires every selected AttributeValueId to occur on
    a Product in the requested ProductRange. Product status eligibility is
    intentionally not guessed beyond the supplied candidate dataset; the 591
    dataset is already the concrete validation population.
    """
    candidates = {
        pid for pid in dataset_ids
        if pid in products and products[pid]["range"] == range_id
    }
    wanted = set(values)
    if not wanted:
        return candidates
    return {pid for pid in candidates if wanted.issubset(pavs.get(pid, set()))}


def filter_signature(values, value_info):
    return [
        {
            "AttributeValueId": int(v),
            "AttributeId": value_info[v]["AttributeId"],
            "AttributeName": value_info[v]["AttributeName"],
            "ValueName": value_info[v]["ValueName"],
        }
        for v in values
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--min-group", type=int, default=24)
    ap.add_argument("--max-filter-values", type=int, default=4)
    ap.add_argument("--output", default=".audit_tmp_range_scoped_reduction.txt")
    args = ap.parse_args()

    rows = read_input(Path(args.input))
    ids = sorted(rows)
    repo = PDMRepository(ApplicationContext())
    products, pavs, value_info = fetch(repo, ids)

    functional = {
        pid: {v for v in pavs.get(pid, set()) if value_info[v]["OrderCodeValue"] in (None, "")}
        for pid in ids
    }

    ranges = defaultdict(list)
    for pid in ids:
        if pid in products:
            ranges[products[pid]["range"]].append(pid)

    report = []
    for range_id, range_ids in sorted(ranges.items()):
        codes = {pid: rows[pid] for pid in range_ids}
        groups = maximal_prefix_groups(codes, args.min_group)
        exact_groups = []
        exact_by_prefix = {}

        for prefix, group_ids in groups:
            common = set.intersection(*(functional.get(pid, set()) for pid in group_ids)) if group_ids else set()
            exact = []
            ordered = sorted(common)
            for size in range(1, min(args.max_filter_values, len(ordered)) + 1):
                for combo in itertools.combinations(ordered, size):
                    returned = legacy_in_memory(products, pavs, range_ids, range_id, combo)
                    if returned == set(group_ids):
                        exact.append(combo)
                if exact:
                    break
            exact_by_prefix[prefix] = exact
            if exact:
                exact_groups.append((prefix, group_ids, exact))

        prefix_sets = [frozenset(group_ids) for _, group_ids in groups]
        overlap_counts = []
        for left, right in itertools.combinations(prefix_sets, 2):
            overlap = len(left & right)
            if overlap:
                overlap_counts.append(overlap)

        covered = set().union(*prefix_sets) if prefix_sets else set()
        report.append({
            "ProductRangeId": range_id,
            "ProductCount": len(range_ids),
            "PrefixGroups": len(groups),
            "ExactFunctionalFilterGroups": len(exact_groups),
            "PrefixOverlaps": overlap_counts,
            "UncoveredProducts": len(set(range_ids) - covered),
            "Groups": [
                {
                    "Prefix": prefix,
                    "Count": len(group_ids),
                    "ExactFilters": [filter_signature(combo, value_info) for combo in exact_by_prefix[prefix]],
                }
                for prefix, group_ids in groups
                if exact_by_prefix[prefix]
            ],
        })

    out = ["RANGE-SCOPED REDUCTION VALIDATION (SET-BASED / READ-ONLY)", "=" * 80]
    out.append(f"Input products: {len(ids)}")
    out.append(f"Resolved products: {len(products)}")
    out.append(f"Product ranges: {len(report)}")
    for item in report:
        out.append(
            f"Range {item['ProductRangeId']}: products={item['ProductCount']} "
            f"prefix_groups={item['PrefixGroups']} "
            f"exact_filter_groups={item['ExactFunctionalFilterGroups']} "
            f"overlaps={item['PrefixOverlaps']} "
            f"uncovered={item['UncoveredProducts']}"
        )
        for group in item["Groups"]:
            out.append(f"  {group['Prefix']} ({group['Count']}): exact={group['ExactFilters']}")

    Path(args.output).write_text("\n".join(out), encoding="utf-8")
    print("Report written:", args.output)
    print("Ranges analyzed:", len(report))
    print("Exact filter groups:", sum(r["ExactFunctionalFilterGroups"] for r in report))
    print("Prefix overlaps:", sum(len(r["PrefixOverlaps"]) for r in report))
    print("Uncovered products:", sum(r["UncoveredProducts"] for r in report))


if __name__ == "__main__":
    main()
