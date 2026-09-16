"""Validate whether ProductRange is the required scope for generic reduction discovery.

Read-only diagnostic. It does not change production reduction behavior.

For each ProductRange represented in the supplied dataset, this script groups
products by observed pre-dot prefix and tests whether a functional PDM filter
uniquely identifies that prefix *inside the same ProductRange*. It also checks
whether the maximal prefix families partition the products without overlap.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
from collections import defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.application_context import ApplicationContext
from repositories.pdm_repository import PDMRepository


def read_input(path):
    text = path.read_text(encoding="utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters="\t,;")
    except csv.Error:
        dialect = csv.excel_tab
    rows = csv.DictReader(text.splitlines(), dialect=dialect)
    return {int(r["ProductId"]): (r["Product"] or "").strip().split(".", 1)[0] for r in rows if (r.get("ProductId") or "").strip() and (r.get("Product") or "").strip()}


def fetch(repo, ids):
    conn = repo.get_connection()
    try:
        cur = conn.cursor()
        q = ",".join("?" for _ in ids)
        cur.execute(f"SELECT ProductId, Product, ProductRangeId FROM Product WITH (NOLOCK) WHERE ProductId IN ({q})", tuple(ids))
        products = {int(r.ProductId): {"code": str(r.Product), "range": int(r.ProductRangeId)} for r in cur.fetchall()}
        cur.execute(f"""SELECT pav.ProductId, pav.AttributeValueId, av.AttributeId,
                              a.Name AS AttributeName, av.Name AS ValueName,
                              av.OrderCodeValue
                       FROM ProductAttributeValues pav WITH (NOLOCK)
                       JOIN AttributeValue av WITH (NOLOCK) ON pav.AttributeValueId=av.AttributeValueId
                       JOIN Attribute a WITH (NOLOCK) ON av.AttributeId=a.AttributeId
                       WHERE pav.ProductId IN ({q}) AND av.Status=1""", tuple(ids))
        pavs = cur.fetchall()
    finally:
        conn.close()
    by = defaultdict(set)
    info = {}
    for r in pavs:
        v = int(r.AttributeValueId)
        by[int(r.ProductId)].add(v)
        info[v] = {"AttributeId": int(r.AttributeId), "AttributeName": str(r.AttributeName), "ValueName": str(r.ValueName), "OrderCodeValue": r.OrderCodeValue}
    return products, by, info


def legacy(cur, range_id, info, values):
    xml = "<attributes>" + "".join(f'<attribute attributeid="{info[v]["AttributeId"]}" attributevalueid="{v}" />' for v in values) + "</attributes>"
    cur.execute("EXEC dbo.ProductsList ?, ?, ?", (range_id, 1, xml))
    cols = [d[0] for d in cur.description or ()]
    idx = next(i for i, c in enumerate(cols) if str(c).lower() == "productid")
    return {int(r[idx]) for r in cur.fetchall()}


def maximal_prefix_groups(codes, min_group):
    groups = []
    max_len = max(map(len, codes.values()))
    for n in range(2, max_len + 1):
        g = defaultdict(list)
        for pid, code in codes.items():
            if len(code) >= n:
                g[code[:n]].append(pid)
        groups.extend((p, pids) for p, pids in g.items() if len(pids) >= min_group)
    byset = defaultdict(list)
    for p, ids in groups:
        byset[frozenset(ids)].append(p)
    return [(max(ps, key=len), sorted(ids)) for ids, ps in byset.items()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--min-group", type=int, default=2)
    ap.add_argument("--max-filter-values", type=int, default=4)
    ap.add_argument("--output", default=".audit_tmp_range_scoped_reduction.txt")
    args = ap.parse_args()

    rows = read_input(Path(args.input))
    ids = sorted(rows)
    repo = PDMRepository(ApplicationContext())
    products, pavs, info = fetch(repo, ids)
    functional = {pid: {v for v in vals if info[v]["OrderCodeValue"] in (None, "")} for pid, vals in pavs.items()}

    ranges = defaultdict(list)
    for pid in ids:
        if pid in products:
            ranges[products[pid]["range"]].append(pid)

    conn = repo.get_connection()
    report = []
    try:
        cur = conn.cursor()
        for rid, rids in sorted(ranges.items()):
            codes = {pid: rows[pid] for pid in rids}
            groups = maximal_prefix_groups(codes, args.min_group)
            exact_by_prefix = {}
            for prefix, gpids in groups:
                common = set.intersection(*(functional.get(pid, set()) for pid in gpids)) if gpids else set()
                exact = []
                for n in range(1, min(args.max_filter_values, len(common)) + 1):
                    for combo in itertools.combinations(sorted(common), n):
                        if legacy(cur, rid, info, combo) == set(gpids):
                            exact.append(combo)
                    if exact:
                        break
                exact_by_prefix[prefix] = exact
            exact_count = sum(bool(v) for v in exact_by_prefix.values())
            prefix_sets = [frozenset(gpids) for _, gpids in groups]
            overlap = []
            for a, b in itertools.combinations(prefix_sets, 2):
                if a & b:
                    overlap.append(len(a & b))
            report.append({"ProductRangeId": rid, "ProductCount": len(rids), "MaximalPrefixGroups": len(groups), "ExactFunctionalFilterGroups": exact_count, "PrefixOverlaps": overlap, "UncoveredProducts": len(set(rids) - set().union(*prefix_sets)) if prefix_sets else len(rids), "Groups": [{"Prefix": p, "Count": len(g), "ExactFilters": exact_by_prefix[p]} for p, g in groups]})
    finally:
        conn.close()

    out = ["RANGE-SCOPED REDUCTION VALIDATION (READ-ONLY)", "=" * 80]
    out.append(f"Input products: {len(ids)}")
    out.append(f"Product ranges: {len(report)}")
    for r in report:
        out.append(f"Range {r['ProductRangeId']}: products={r['ProductCount']} prefix_groups={r['MaximalPrefixGroups']} exact_filter_groups={r['ExactFunctionalFilterGroups']} overlaps={r['PrefixOverlaps']} uncovered={r['UncoveredProducts']}")
        for g in r["Groups"]:
            if g["ExactFilters"]:
                out.append(f"  {g['Prefix']} ({g['Count']}): exact={g['ExactFilters']}")
    Path(args.output).write_text("\n".join(out), encoding="utf-8")
    print("Report written:", args.output)
    print("Ranges analyzed:", len(report))
    print("Exact filter groups:", sum(r["ExactFunctionalFilterGroups"] for r in report))
    print("Prefix overlaps:", sum(len(r["PrefixOverlaps"]) for r in report))
    print("Uncovered products:", sum(r["UncoveredProducts"] for r in report))


if __name__ == "__main__":
    main()
