"""Investigate why identical functional filters map to different pre-dot prefixes.

Read-only diagnostic. It deliberately does not alter production reduction code.
The current 591-row proving dataset is used only as input; the query logic is
parameterized by the ProductIds in that input.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.application_context import ApplicationContext
from repositories.pdm_repository import PDMRepository

CHUNK = 100


def placeholders(n):
    return ",".join("?" for _ in range(n))


def read_input(path):
    text = path.read_text(encoding="utf-8-sig")
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters="\t,;")
    except csv.Error:
        dialect = csv.excel_tab
    rows = {}
    for r in csv.DictReader(text.splitlines(), dialect=dialect):
        if r.get("ProductId") and r.get("Product"):
            rows[int(r["ProductId"])] = r["Product"].strip().split(".", 1)[0]
    return rows


def fetch(repo, ids):
    out = {}
    conn = repo.get_connection()
    try:
        for i in range(0, len(ids), CHUNK):
            chunk = ids[i:i + CHUNK]
            cur = conn.cursor()
            cur.execute(f"""
                SELECT p.ProductId, p.Product, p.ProductRangeId, p.ProductCodeId,
                       p.Status, p.NewProduct, p.IsSuperProduct,
                       pc.Product_Code, pc.BasePriceRef, pc.GroupCode,
                       pr.Name AS ProductRangeName, pr.OrderCodeFormatString AS RangeOCFS,
                       p.OrderCodeFormatString AS ProductOCFS
                FROM Product p WITH (NOLOCK)
                LEFT JOIN Product_Code pc WITH (NOLOCK) ON pc.ProductCodeId=p.ProductCodeId
                LEFT JOIN ProductRange pr WITH (NOLOCK) ON pr.ProductRangeId=p.ProductRangeId
                WHERE p.ProductId IN ({placeholders(len(chunk))})
            """, tuple(chunk))
            cols = [d[0] for d in cur.description]
            for row in cur.fetchall():
                out[int(row.ProductId)] = dict(zip(cols, row))
    finally:
        conn.close()
    return out


def fetch_attributes(repo, ids):
    out = defaultdict(list)
    conn = repo.get_connection()
    try:
        for i in range(0, len(ids), CHUNK):
            chunk = ids[i:i + CHUNK]
            cur = conn.cursor()
            cur.execute(f"""
                SELECT pav.ProductId, pav.AttributeValueId, av.AttributeId,
                       a.Name AS AttributeName, a.AttributeType,
                       a.OrderCodeFormatKey, a.HasDependentOptions,
                       a.DisplayOrder, av.Name AS ValueName,
                       av.OrderCodeValue, av.ParentAttributeValueId,
                       av.ModelSuffix, av.DisplayOrdinal
                FROM ProductAttributeValues pav WITH (NOLOCK)
                INNER JOIN AttributeValue av WITH (NOLOCK) ON av.AttributeValueId=pav.AttributeValueId
                INNER JOIN Attribute a WITH (NOLOCK) ON a.AttributeId=av.AttributeId
                WHERE pav.ProductId IN ({placeholders(len(chunk))}) AND av.Status=1
                ORDER BY pav.ProductId,a.DisplayOrder,av.DisplayOrdinal,av.AttributeValueId
            """, tuple(chunk))
            cols = [d[0] for d in cur.description]
            for row in cur.fetchall():
                d = dict(zip(cols, row))
                d["DimensionClass"] = "order_code" if (d["OrderCodeValue"] or "") != "" else "functional"
                out[int(d["ProductId"])].append(d)
    finally:
        conn.close()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--prefixes", default="RY3XS,RYCX1,RY3XSD,RYCX1S,RY3XSS,RYCX1E,RY3XSDA,RYCX1SA,RY3XSDS,RYCX1SX,RY3XSSA,RYCX1EA,RY3XSSS,RYCX1EX")
    ap.add_argument("--output", default=".audit_tmp_ambiguous_reduction_families.txt")
    args = ap.parse_args()

    codes = read_input(Path(args.input))
    wanted = [x.strip() for x in args.prefixes.split(",") if x.strip()]
    families = {p: sorted(pid for pid, code in codes.items() if code.startswith(p)) for p in wanted}
    ids = sorted({pid for pids in families.values() for pid in pids})
    repo = PDMRepository(ApplicationContext())
    products = fetch(repo, ids)
    attrs = fetch_attributes(repo, ids)

    lines = []
    lines.append("AMBIGUOUS REDUCTION FAMILY ANALYSIS (READ-ONLY)")
    lines.append("=" * 80)
    lines.append("Functional = AttributeValue.OrderCodeValue empty; order-code dimensions are reported but not used as pre-dot evidence.")
    lines.append("")

    for prefix, pids in families.items():
        if not pids:
            continue
        lines.append(f"FAMILY {prefix} ({len(pids)} products)")
        ranges = sorted({products[pid]["ProductRangeId"] for pid in pids})
        codes_here = [codes[pid] for pid in pids]
        lines.append(f"  ProductRanges: {ranges}")
        lines.append(f"  ProductCodes: {sorted({products[pid]['ProductCodeId'] for pid in pids})}")
        lines.append(f"  Product_Code: {sorted({str(products[pid]['Product_Code']) for pid in pids})}")
        lines.append(f"  GroupCode: {sorted({str(products[pid]['GroupCode']) for pid in pids})}")
        lines.append(f"  BasePriceRef: {sorted({str(products[pid]['BasePriceRef']) for pid in pids})}")
        lines.append(f"  IsSuperProduct: {sorted({str(products[pid]['IsSuperProduct']) for pid in pids})}")
        lines.append(f"  ProductRangeName: {sorted({str(products[pid]['ProductRangeName']) for pid in pids})}")
        lines.append(f"  ProductOCFS: {sorted({str(products[pid]['ProductOCFS']) for pid in pids})}")
        lines.append(f"  RangeOCFS: {sorted({str(products[pid]['RangeOCFS']) for pid in pids})}")

        by_attr = defaultdict(lambda: defaultdict(set))
        for pid in pids:
            for a in attrs[pid]:
                if a["DimensionClass"] == "functional":
                    by_attr[(int(a["AttributeId"]), str(a["AttributeName"]))][int(a["AttributeValueId"])].add(pid)
        lines.append("  Functional dimensions present:")
        for (aid, aname), vals in sorted(by_attr.items()):
            value_text = []
            for vid, members in sorted(vals.items()):
                sample = next(a for pid in pids for a in attrs[pid] if int(a["AttributeValueId"]) == vid)
                value_text.append(f"{vid}={sample['ValueName']!s} ({len(members)}/{len(pids)})")
            lines.append(f"    Attribute {aid} {aname}: " + "; ".join(value_text))

        lines.append("  Representative products (first 5):")
        for pid in pids[:5]:
            lines.append(f"    {pid}: {codes[pid]}")
            for a in attrs[pid]:
                if a["DimensionClass"] == "functional":
                    lines.append(f"      F {a['AttributeId']} {a['AttributeName']} = {a['AttributeValueId']} {a['ValueName']}")
        lines.append("")

    # Direct pairwise difference analysis for the ambiguous prefix pairs.
    lines.append("PAIRWISE FUNCTIONAL DIFFERENCES")
    lines.append("=" * 80)
    pairs = list(zip(wanted[0::2], wanted[1::2]))
    for left, right in pairs:
        if left not in families or right not in families or not families[left] or not families[right]:
            continue
        lset, rset = set(families[left]), set(families[right])
        lvals = {v for pid in lset for a in attrs[pid] if a["DimensionClass"] == "functional" for v in [int(a["AttributeValueId"])]}
        rvals = {v for pid in rset for a in attrs[pid] if a["DimensionClass"] == "functional" for v in [int(a["AttributeValueId"])]}
        only_l, only_r = sorted(lvals-rvals), sorted(rvals-lvals)
        lines.append(f"{left} VS {right}")
        lines.append(f"  Functional values only in left: {only_l}")
        lines.append(f"  Functional values only in right: {only_r}")
        lines.append(f"  Same ProductRangeId: {sorted({products[p]['ProductRangeId'] for p in lset}) == sorted({products[p]['ProductRangeId'] for p in rset})}")
        lines.append("")

    Path(args.output).write_text("\n".join(lines), encoding="utf-8")
    print(f"Analyzed {len(ids)} products across {sum(bool(v) for v in families.values())} requested families")
    print(f"Report written: {args.output}")


if __name__ == "__main__":
    main()
