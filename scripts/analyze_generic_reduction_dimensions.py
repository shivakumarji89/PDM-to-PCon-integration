"""Read-only generic analysis of functional vs order-code PDM dimensions.

This intentionally does not implement reduction. It is designed to test the
same discovery logic against any supplied ProductId dataset, without knowing
series, catalogue, category, article prefixes, or business-specific names.

A PDM attribute/value is classified as order-code when OrderCodeValue is
non-empty. Such dimensions are reported separately because they belong to the
existing after-dot article generation. Functional dimensions are analyzed for
pre-dot family discovery and validated with the legacy ProductsList procedure.
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

CHUNK = 100


def ph(n):
    return ", ".join("?" for _ in range(n))


def read_input(path):
    text = path.read_text(encoding="utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters="\t,;")
    except csv.Error:
        dialect = csv.excel_tab
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    if not reader.fieldnames or "ProductId" not in reader.fieldnames or "Product" not in reader.fieldnames:
        raise ValueError(f"Input must contain ProductId and Product. Columns: {reader.fieldnames}")
    rows = {}
    for r in reader:
        raw = (r.get("ProductId") or "").strip()
        code = (r.get("Product") or "").strip().split(".", 1)[0]
        if raw and code:
            rows[int(raw)] = {"Product": code, "Description": (r.get("Description") or "").strip()}
    return rows


def fetch_products(repo, ids):
    found = {}
    conn = repo.get_connection()
    try:
        for i in range(0, len(ids), CHUNK):
            chunk = ids[i:i + CHUNK]
            cur = conn.cursor()
            cur.execute(
                f"SELECT ProductId, Product, ProductRangeId, ProductCodeId, Status, NewProduct, IsSuperProduct "
                f"FROM Product WITH (NOLOCK) WHERE ProductId IN ({ph(len(chunk))})", tuple(chunk))
            for r in cur.fetchall():
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


def fetch_pavs(repo, ids):
    rows = []
    conn = repo.get_connection()
    try:
        for i in range(0, len(ids), CHUNK):
            chunk = ids[i:i + CHUNK]
            cur = conn.cursor()
            cur.execute(
                f"""SELECT pav.ProductId, pav.AttributeValueId,
                           av.AttributeId, a.Name AS AttributeName,
                           av.Name AS ValueName, av.OrderCodeValue,
                           a.DisplayOrder, av.DisplayOrdinal
                    FROM ProductAttributeValues pav WITH (NOLOCK)
                    INNER JOIN AttributeValue av WITH (NOLOCK) ON pav.AttributeValueId = av.AttributeValueId
                    INNER JOIN Attribute a WITH (NOLOCK) ON av.AttributeId = a.AttributeId
                    WHERE pav.ProductId IN ({ph(len(chunk))}) AND av.Status = 1
                    ORDER BY pav.ProductId, a.DisplayOrder, av.DisplayOrdinal""", tuple(chunk))
            rows.extend(cur.fetchall())
    finally:
        conn.close()
    return rows


def products_list(cur, range_id, value_info, value_ids):
    xml = "<attributes>" + "".join(
        f'<attribute attributeid="{value_info[v]["AttributeId"]}" attributevalueid="{v}" />'
        for v in value_ids
    ) + "</attributes>"
    cur.execute("EXEC dbo.ProductsList ?, ?, ?", (range_id, 1, xml))
    cols = [d[0] for d in cur.description or ()]
    idx = next((i for i, n in enumerate(cols) if str(n).lower() == "productid"), None)
    if idx is None:
        raise RuntimeError(f"ProductsList did not return ProductId: {cols!r}")
    return {int(r[idx]) for r in cur.fetchall()}


def prefix_groups(codes, min_group):
    candidates = []
    max_len = max((len(c) for c in codes.values()), default=0)
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
    return sorted((max(items, key=lambda x: (x[0], x[1])) for items in by_set.values()), key=lambda x: (-len(x[2]), x[0], x[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--min-group", type=int, default=24)
    ap.add_argument("--max-filter-values", type=int, default=4)
    ap.add_argument("--output", default=".audit_tmp_generic_reduction_dimensions.json")
    args = ap.parse_args()

    rows = read_input(Path(args.input))
    ids = sorted(rows)
    repo = PDMRepository(ApplicationContext())
    products = fetch_products(repo, ids)
    pavs = fetch_pavs(repo, ids)

    by_product = defaultdict(set)
    value_info = {}
    classification = {}
    for r in pavs:
        pid, vid = int(r.ProductId), int(r.AttributeValueId)
        by_product[pid].add(vid)
        oc = "" if r.OrderCodeValue is None else str(r.OrderCodeValue)
        classification[vid] = "order_code" if oc != "" else "functional"
        value_info[vid] = {
            "AttributeId": int(r.AttributeId), "AttributeName": str(r.AttributeName),
            "ValueName": str(r.ValueName), "OrderCodeValue": r.OrderCodeValue,
            "DisplayOrder": int(r.DisplayOrder) if r.DisplayOrder is not None else None,
            "DisplayOrdinal": int(r.DisplayOrdinal) if r.DisplayOrdinal is not None else None,
            "DimensionClass": classification[vid],
        }

    functional = {pid: {v for v in vals if classification.get(v) == "functional"} for pid, vals in by_product.items()}
    order_code = {pid: {v for v in vals if classification.get(v) == "order_code"} for pid, vals in by_product.items()}
    codes = {pid: rows[pid]["Product"] for pid in ids}
    groups = prefix_groups(codes, args.min_group)

    conn = repo.get_connection()
    results = []
    try:
        cur = conn.cursor()
        for n, (_, prefix, pids) in enumerate(groups, 1):
            ranges = Counter(products[pid]["ProductRangeId"] for pid in pids if pid in products)
            common = None
            for pid in pids:
                vals = functional.get(pid, set())
                common = set(vals) if common is None else common & vals
            common = common or set()
            exact = []
            if len(ranges) == 1 and common:
                range_id = next(iter(ranges))
                ordered = sorted(common)
                for size in range(1, min(args.max_filter_values, len(ordered)) + 1):
                    for combo in itertools.combinations(ordered, size):
                        returned = products_list(cur, range_id, value_info, combo)
                        if returned == set(pids):
                            exact.append(combo)
                    if exact:
                        break
            varying_functional = set().union(*(functional.get(pid, set()) for pid in pids)) - common if pids else set()
            results.append({
                "Prefix": prefix,
                "PrefixLength": len(prefix),
                "ProductCount": len(pids),
                "ProductIds": pids,
                "ProductRanges": dict(ranges),
                "CommonFunctionalValues": [value_info[v] for v in sorted(common)],
                "VariableFunctionalValues": [value_info[v] for v in sorted(varying_functional)],
                "OrderCodeValuesPresent": sorted({v for pid in pids for v in order_code.get(pid, set())}),
                "ExactLegacyFunctionalFilters": [list(c) for c in exact],
            })
            print(f"Analyzed {n}/{len(groups)}: {prefix} ({len(pids)}) exact_functional_filters={len(exact)}", flush=True)
    finally:
        conn.close()

    exact = [r for r in results if r["ExactLegacyFunctionalFilters"]]
    report = {
        "input_product_count": len(ids),
        "resolved_product_count": len(products),
        "pav_row_count": len(pavs),
        "functional_pav_rows": sum(1 for r in pavs if classification[int(r.AttributeValueId)] == "functional"),
        "order_code_pav_rows": sum(1 for r in pavs if classification[int(r.AttributeValueId)] == "order_code"),
        "maximal_prefix_groups": len(results),
        "groups_with_exact_legacy_functional_filter": len(exact),
        "groups": results,
        "note": "Generic discovery only. Prefix is an observed candidate family boundary; OrderCodeValue classification is used to exclude after-dot dimensions; ProductsList is the legacy membership validator. No production reduction is performed.",
    }
    Path(args.output).write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(f"Input ProductIds: {len(ids)}")
    print(f"Resolved Products: {len(products)}")
    print(f"PAV rows: {len(pavs)}; functional={report['functional_pav_rows']}; order_code={report['order_code_pav_rows']}")
    print(f"Maximal prefix groups: {len(results)}")
    print(f"Groups with exact legacy functional filter: {len(exact)}")
    print(f"Report written: {args.output}")


if __name__ == "__main__":
    main()
