"""Read-only evidence-B pricing comparison; never opens an MDB.

Run from the repository root with ``python -B -m scripts.pdm_differential.fetch_parity``.
The independent SQL oracle transcribes PriceMaintenance.cs's per-item worker
path, not the tool's repository SQL builder. No capture files are written.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from decimal import Decimal
import json
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

from core.config import AppConfig
from repositories.pdm_repository import PDMRepository
from services.pricing_service import PriceParams, PricingService

if TYPE_CHECKING:
    from core.application_context import ApplicationContext


GLOBAL_CASES = [
    (item, program, catalogue, 1)
    for item, program, catalogues in [
        ("GEMAP.12S1M", "layout_studio", [394, 414, 660]),
        ("GEBH.10", "layout_studio", [414, 521, 660, 662]),
        ("DTW2B1T2.C", "layout_studio", [521, 662]),
        ("GETH.1022FS4W", "layout_studio", [660, 662]),
        ("MRFN121HWAP", "lf", [4, 652]),
        ("AS7EA52AA", "av", [4, 683]),
        ("AS2EA32AA", "av", [4, 683]),
        ("WE5110L", "caper", [4, 652]),
        ("RY3VFTB.105512F", "revive", [658]),
        ("RYMPSH.12SW", "revive", [658]),
        ("RYTRFA.0812SW", "revive", [658]),
        ("894-176092", "", [301]),
        ("PDRSDNBFG.1114", "ratio", [755]),
    ]
    for catalogue in catalogues
] + [
    ("1205S1BQ", "", 649, 1),
    ("CN132AWAA", "embody", 4, 9),
    ("CD63NC0600", "", 172, 9),
    ("RZTA.", "ratio", 405, 1),
]
ARTICLE_CASES = [
    (item, "layout_studio")
    for item in [
        "GESG.", "GEWC.10", "GEWDP.L", "GEWDP.S", "GEWQ.",
        "GEPBPANNF.0608S4M", "GEMAP.12S1M", "GEBH.10",
        "DTW2B1T2.C", "GETH.1022FS4W",
    ]
] + [
    ("MRF752AWAF", "lf"), ("MRF752AWAF", ""), ("MRFN121HWAP", "lf"),
    ("AS7EA52AA", "av"), ("AS7EA52AA", ""), ("AS2EA32AA", "av"),
    ("WE5110L", "caper"), ("RY3VFTB.105512F", "revive"),
    ("RYMPSH.12SW", "revive"), ("RYTRFA.0812SW", "revive"),
    ("894-176092", ""), ("OAW102", "swoop"),
    ("PDRSDNBFG.1114", "ratio"), ("2003", ""),
]
NONVARIABLE = {
    "aeron", "verus", "lino", "embody", "cosm", "mirra2", "sayl", "setu",
    "celle", "keyn", "caper", "mirra", "em", "lf", "av", "ce", "cp",
}
SELECTED = """CASE pc.BasePriceRef WHEN 1 THEN v.IncrementalPrice
    WHEN 2 THEN v.IncrementalPrice2 WHEN 3 THEN v.IncrementalPrice3 END"""
JOINS = """
    FROM ItemOptionValues v
    JOIN OptionValue ov ON ov.OptionValueId=v.OptionValueId
    JOIN Item i ON i.ItemId=v.ItemId
    {scope}
    JOIN Product p ON p.ProductId=i.ProductId
    JOIN Product_Code pc ON pc.ProductCodeId=COALESCE(i.ProductCodeIdOverride,p.ProductCodeId)
        AND pc.SiteId=?
    JOIN PriceMatrix pm ON pm.ItemPriceCode=pc.PriceCode
    JOIN Currency cu ON cu.PriceCode=pm.CustPriceCode AND cu.Currency=?
    JOIN ProductRange pr ON pr.ProductRangeId=p.ProductRangeId
    LEFT JOIN FabricBands fb ON fb.OptionValueId=v.OptionValueId AND fb.Application=1
"""
SCOPES = (
    "JOIN CatalogueItems ci ON ci.ItemId=i.ItemId AND ci.CatalogueId=?",
    """JOIN ItemComponents co ON co.SubItemId=i.ItemId
       JOIN Item parent ON parent.ItemId=co.ItemId
       JOIN CatalogueItems ci ON ci.ItemId=parent.ItemId AND ci.CatalogueId=?""",
)


def source_query(conn, item, program, catalogue, site, currency, date, secondary=None):
    """Exact DISTINCT projection and UNION, including source-projected ordering."""
    if item.startswith("WE51"):
        code = "i.Item+' '+CONVERT(varchar,ov.OptionId)+'='+ov.OrderCodeValue"
    elif program.lower().replace("_", "").replace(" ", "") in NONVARIABLE:
        code = "ov.OrderCodeValue"
    elif program == "memo":
        code = "i.Item+ov.OrderCodeValue"
    else:
        code = "i.Item+'_'+ov.OrderCodeValue"
    fields = (
        f"i.Item,ov.OptionValueId,ov.OptionId,{code} Code,{SELECTED} RawIncrement,fb.PriceBand"
        if secondary is None else
        f"""i.Item,ov.OptionValueId,ov.OrderCodeValue,
        dbo.fnGetListPrice(?,{SELECTED},pc.PriceCode,?,'DMY',pm.Rounding,?,NULL) NewPrice,
        fb.PriceBand"""
    )
    predicates = {
        "lf": " AND p.Product NOT LIKE 'MRF7%'",
        "av": " AND p.Product NOT LIKE 'AS7%'",
        "swoop": " AND (p.Product LIKE 'OAW1%' OR p.Product LIKE 'OAW2%')",
    }
    args = []
    branches = []
    for scope in SCOPES:
        where = "ov.Status=1" if secondary is None else "ov.OptionValueId=? AND v.IncrementalPrice=?"
        branches.append(
            "SELECT DISTINCT " + fields + JOINS.format(scope=scope)
            + " WHERE " + where + predicates.get(program, "") + " AND i.Item LIKE ?"
        )
        if secondary is not None:
            args.extend((currency, date, site))
        args.extend((catalogue, site, currency))
        if secondary is not None:
            args.extend(secondary)
        args.append("%" + item + "%")
    query = " UNION ".join(branches) + (" ORDER BY Code" if secondary is None else "")
    return list(conn.cursor().execute(query, args).fetchall())


def source_processed(conn, item, program, catalogue, site, currency, date):
    initial = source_query(conn, item, program, catalogue, site, currency, date)
    cache = []
    output = []
    for row in initial:
        if row.RawIncrement is None:
            continue
        source_code = str(row.Code or "")
        item_index = next((i for i, value in enumerate(cache) if value[0] == row.Item), -1)
        raw_index = next((i for i, value in enumerate(cache) if value[1] == row.RawIncrement), -1)
        price = -1
        if item_index >= 0 and item_index == raw_index:
            price = cache[raw_index][2]
        else:
            calculated = source_query(
                conn, item, program, catalogue, site, currency, date,
                (row.OptionValueId, row.RawIncrement),
            )
            for value in calculated:
                if value.NewPrice is not None:
                    price = value.NewPrice
                    cache.append((value.Item, row.RawIncrement, price))
        if item.startswith("WE51"):
            prefix = f"{row.Item} {row.OptionId}="
        elif program.lower().replace("_", "").replace(" ", "") in NONVARIABLE:
            prefix = ""
        else:
            prefix = row.Item + ("" if program == "memo" else "_")
        raw_code = source_code[len(prefix):] if prefix else source_code
        lookup = (
            f"{row.OptionId}={source_code}"
            if program == "revive" and row.Item.startswith(("RYM", "RYT"))
            else source_code.replace("_", f" {row.OptionId}=")
        )
        output.append(SimpleNamespace(
            Item=row.Item, OptionValueId=row.OptionValueId, OptionId=row.OptionId,
            Code=raw_code, PriceBand=row.PriceBand, IncPrice=price,
            RawIncrement=row.RawIncrement, LookupCode=lookup, SourceCode=source_code,
        ))
    return initial, output


def normalize(value):
    return None if value is None else str(Decimal(str(value)).normalize())


def identity(row):
    return (
        str(row.Item), row.OptionValueId, row.OptionId,
        getattr(row, "Code", getattr(row, "OrderCodeValue2", "")),
        normalize(row.IncPrice), row.PriceBand,
    )


def compare(expected, actual):
    left, right = Counter(expected), Counter(actual)
    exact = sum((left & right).values())
    a, b = Counter(), Counter()
    for row, count in (left - right).items():
        a[row[:2]] += count
    for row, count in (right - left).items():
        b[row[:2]] += count
    fields = sum((a & b).values())
    missing = sum((a - b).values())
    extra = sum((b - a).values())
    return {
        "pdm": len(expected), "tool": len(actual), "exact": exact,
        "fields": fields, "missing": missing, "extra": extra,
        "denominator": exact + fields + missing + extra,
        "pdm_duplicates": len(expected) - len(left),
        "tool_duplicates": len(actual) - len(right),
        "order_match": expected == actual,
        "pdm_only": list((left - right).elements())[:3],
        "tool_only": list((right - left).elements())[:3],
    }


def target_lookup(value, program):
    """PDM parsePConOrderCode for the worker's removeitemprefix=False path."""
    text = value.upper().replace("_", "~", 1)
    text = text.replace(program.upper() + "_", "").replace("_", "")
    for token in (
        "BACK", "FINISH", "BASE", "FRAME", "WHITE", "CASTORS", "GLIDES",
        "FABRIC", "TYPE", "SUPPORT", "LINKAGE", "SEAT", "CELLULAR", "COLOUR",
        "ARM", "GLIDE", "SUSPENSION", "CHASIS",
    ):
        text = text.replace(token, "")
    if program == "aeron":
        text = text.replace("LE21", "21")
    return text.replace("~", "_").strip()


def baseline_class(ref):
    # Load the committed producer in memory; never checkout or create a worktree.
    text = subprocess.check_output(
        ["git", "show", f"{ref}:repositories/pdm_repository.py"], text=True
    )
    module = ModuleType("_pricing_baseline")
    sys.modules[module.__name__] = module
    exec(compile(text, f"{ref}:repositories/pdm_repository.py", "exec"), module.__dict__)
    return module.PDMRepository


def article_source(conn, item, program, site, currency, date):
    predicate = {
        "lf": " AND p.Product NOT LIKE 'MRF7%'",
        "av": " AND p.Product NOT LIKE 'AS7%'",
    }.get(program, "")
    sql = f"""SELECT DISTINCT i.Item,ov.OptionValueId,ov.OptionId,
        ov.OrderCodeValue Code,
        dbo.fnGetListPrice(?,{SELECTED},pc.PriceCode,?,'DMY',pm.Rounding,?,NULL) IncPrice,
        fb.PriceBand """ + JOINS.format(scope="") + " WHERE ov.Status=1 AND i.Item=?" + predicate
    return list(conn.cursor().execute(
        sql, currency, date, site, site, currency, item
    ).fetchall())


def run(args):
    # The repository needs config only; do not initialize the Qt application.
    context = cast("ApplicationContext", SimpleNamespace(config=AppConfig(
        pdm_server="DBCHIP11V", pdm_database="PDMTEST"
    )))
    repo = PDMRepository(context)
    producer = baseline_class(args.baseline_ref)(context) if args.baseline_ref else repo
    conn = repo.get_connection()
    conn.autocommit = False
    totals: dict[str, list[dict[str, Any]]] = defaultdict(list)
    try:
        database = conn.cursor().execute("SELECT DB_NAME()").fetchone()
        if database is None or database[0] != "PDMTEST":
            raise RuntimeError("Only PDMTEST is allowed")
        print(json.dumps({
            "evidence": "B", "database": "DBCHIP11V.PDMTEST",
            "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "baseline": args.baseline_ref, "dates": args.dates,
            "currencies": args.currencies, "global_cases": GLOBAL_CASES,
            "article_cases": ARTICLE_CASES if args.article else [],
        }), flush=True)
        for item, program, catalogue, site in GLOBAL_CASES:
            if args.item and item not in args.item:
                continue
            for date in args.dates:
                for currency in args.currencies:
                    initial, expected = source_processed(
                        conn, item, program, catalogue, site, currency, date
                    )
                    actual = producer.fetch_global_option_increment_prices(
                        [item], currency, date, site, conn,
                        **({} if args.baseline_ref else {
                            "catalogue_id": catalogue, "program_code": program,
                        }),
                    )
                    left, right = [identity(r) for r in expected], [identity(r) for r in actual]
                    m = compare(left, right)
                    totals["global_processed_fetch"].append(m)
                    records, _ = PricingService.build_records(
                        [], actual, {r.Item for r in actual}, {},
                        PriceParams(currency=currency, program_code=program),
                    )
                    # Compare source lookup metadata, not an assumed physical
                    # target condition. Older producers had no such metadata.
                    right_lookup = [
                        r + (record.pdm_lookup_code or target_lookup(
                            record.variant_condition, program
                        ),)
                        for r, record in zip(right, records, strict=True)
                    ]
                    lp = compare(
                        [r + (s.LookupCode,) for r, s in zip(left, expected, strict=True)],
                        right_lookup,
                    )
                    totals["global_source_lookup_preparation"].append(lp)
                    # This measures compatibility with the update worker's
                    # parser/key, not AddMissingGlobalPricingRecords output.
                    worker_match = compare(
                        [r + (s.LookupCode.replace("#", ""),)
                         for r, s in zip(left, expected, strict=True)],
                        [r + (target_lookup(record.variant_condition, program),)
                         for r, record in zip(right, records, strict=True)],
                    )
                    totals["global_worker_target_matching"].append(worker_match)
                    if not args.baseline_ref:
                        projection = compare(
                            [(s.Item, s.OptionValueId, s.OptionId, s.Code,
                              normalize(s.RawIncrement), s.SourceCode, s.PriceBand)
                             for s in expected],
                            [(s.Item, s.OptionValueId, s.OptionId, s.Code,
                              normalize(s.RawIncrement), s.SourceCode, s.PriceBand)
                             for s in actual],
                        )
                        totals["global_source_projection"].append(projection)
                    print(json.dumps({
                        "input": [item, program, catalogue, site, date, currency],
                        "initial_rows": len(initial),
                        "source_null_raw": sum(r.RawIncrement is None for r in initial),
                        "fetch": m, "source_lookup_preparation": lp,
                        "worker_target_matching": worker_match,
                    }, default=str), flush=True)
        if args.article:
            for item, program in ARTICLE_CASES:
                for date in args.dates:
                    for currency in args.currencies:
                        expected = article_source(conn, item, program, 1, currency, date)
                        actual = producer.fetch_article_option_increment_prices(
                            [item], currency, date, 1, conn, program_code=program
                        )
                        base_row = conn.cursor().execute(
                            "SELECT dbo.fnGetListPriceByItem(?,?,?,1,NULL)",
                            item, currency, date,
                        ).fetchone()
                        if base_row is None:
                            raise RuntimeError(f"Base-price query returned no result for {item}")
                        base = base_row[0]
                        tool_base = producer.fetch_item_base_prices(
                            [item], currency, date, conn, site_id=1
                        )
                        m = compare(
                            [identity(r) for r in expected] + [(item, None, normalize(base))],
                            [identity(r) for r in actual] + [
                                (str(r.Item), None, normalize(r.price)) for r in tool_base
                            ],
                        )
                        totals["article_fetch"].append(m)
        for name, results in totals.items():
            fields = [
                "pdm", "tool", "exact", "fields", "missing", "extra",
                "denominator", "pdm_duplicates", "tool_duplicates",
            ]
            aggregate = {field: sum(r[field] for r in results) for field in fields}
            aggregate.update(
                scenarios=len(results),
                multiset_pass=sum(r["exact"] == r["denominator"] for r in results),
                order_pass=sum(r["order_match"] for r in results),
                empty=sum(r["pdm"] == r["tool"] == 0 for r in results),
            )
            print("SUMMARY", name, json.dumps(aggregate), flush=True)
        return int(any(r["exact"] != r["denominator"] for rows in totals.values() for r in rows))
    finally:
        conn.rollback()
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref")
    parser.add_argument("--dates", nargs="+", default=["15-Oct-2026", "16-Oct-2026"])
    parser.add_argument("--currencies", nargs="+", default=["GBP", "EUR"])
    parser.add_argument("--item", action="append")
    parser.add_argument("--article", action="store_true")
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
