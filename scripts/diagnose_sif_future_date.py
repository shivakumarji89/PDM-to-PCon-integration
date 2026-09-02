"""Read-only diagnostic for CET SIF site calibration across pricing dates.

Run:
    $env:PYTHONPATH = "."
    python scripts/diagnose_sif_future_date.py

The script uses the same SIF parser, PDM connection, and
``fnGetListPriceByItem`` repository path as CET SIF Validation.  It does not
write to PDM or to the filesystem.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from core.application_context import ApplicationContext
from repositories.pdm_repository import PDMRepository
from services.sif_validation_service import SifLine, SifValidationService


DEFAULT_SIF = Path(r"C:\Users\siaoca\Downloads\SIF\ASIA_Atlas_Typical-1_CNY_29032026.sif")
DATES = ("24-Aug-2026", "07-Sep-2026")

# These are printed with --show-sql.  All statements are SELECT-only.
SQL_CNY_SITES = """
SELECT SiteId, Site, DomCurrCode
FROM Site
WHERE UPPER(DomCurrCode) = UPPER(?)
ORDER BY SiteId
"""
SQL_ALL_SITES = """
SELECT SiteId, Site, DomCurrCode
FROM Site
ORDER BY SiteId
"""
SQL_FORMULAS = """
SELECT DISTINCT
    i.Item,
    s.SiteId,
    s.Site,
    s.DomCurrCode AS SiteDomCurrCode,
    pc.PriceCode AS ItemPriceCode,
    pm.CustPriceCode,
    pm.PriceFormula,
    pf.PriceFormulaId,
    pf.DomCurrCode AS FormulaCurrency,
    pf.EffectiveDate,
    pf.FirstPrice,
    pf.FirstBase
FROM Item i
INNER JOIN Product p ON p.ProductId = i.ProductId
INNER JOIN Product_Code pc ON pc.ProductCodeId = p.ProductCodeId
    AND pc.SiteId = ?
INNER JOIN PriceMatrix pm ON pm.ItemPriceCode = pc.PriceCode
INNER JOIN Currency c ON c.PriceCode = pm.CustPriceCode
    AND c.Currency = ?
INNER JOIN PriceFormula pf ON pf.PriceFormula = pm.PriceFormula
    AND pf.SiteId = ?
    AND pf.DomCurrCode = ?
INNER JOIN Site s ON s.SiteId = pf.SiteId
WHERE i.Item IN ({placeholders})
  AND pf.EffectiveDate <= CONVERT(smalldatetime, ?, 106)
ORDER BY i.Item, pf.EffectiveDate, pm.PriceFormula
"""
SQL_EFFECTIVE_CHANGES = """
SELECT pf.PriceFormulaId, pf.SiteId, s.Site, s.DomCurrCode AS SiteDomCurrCode,
       pf.DomCurrCode AS FormulaCurrency, pf.EffectiveDate, pf.PriceFormula,
       pf.FirstPrice, pf.FirstBase
FROM PriceFormula pf
INNER JOIN Site s ON s.SiteId = pf.SiteId
WHERE pf.SiteId = ?
  AND pf.DomCurrCode = ?
  AND pf.EffectiveDate BETWEEN CONVERT(smalldatetime, ?, 106)
      AND CONVERT(smalldatetime, ?, 106)
ORDER BY pf.EffectiveDate, pf.PriceFormula
"""


def _value(row: Any, name: str) -> Any:
    return getattr(row, name, None)


def _price(value: Any) -> str:
    return "NULL" if value is None else f"{float(value):.2f}"


def _sample(lines: list[SifLine], limit: int) -> list[SifLine]:
    """Mirror resolve_site's calibration sample selection exactly."""
    sample = [line for line in lines if line.base and not any(opt.ol for opt in line.options)][:limit]
    return sample or [line for line in lines if line.base][:limit]


def _price_map(rows: list[Any]) -> dict[int, dict[str, float | None]]:
    out: dict[int, dict[str, float | None]] = defaultdict(dict)
    for row in rows:
        raw = _value(row, "price")
        out[int(row.SiteId)][str(row.Item)] = None if raw is None else float(raw)
    return out


def _calibration_summary(
    sample: list[SifLine], site_rows: list[Any], prices: dict[int, dict[str, float | None]]
) -> tuple[dict[int, tuple[int, int]], int | None]:
    wanted = {line.base: line.pl for line in sample}
    summary: dict[int, tuple[int, int]] = {}
    best_site, best_hits = None, 0
    for site_row in site_rows:
        site_id = int(site_row.SiteId)
        site_prices = prices.get(site_id, {})
        available = sum(1 for item in wanted if site_prices.get(item) is not None)
        hits = sum(
            1
            for item, sif_price in wanted.items()
            if site_prices.get(item) is not None
            and abs(float(site_prices[item]) - sif_price) < 0.005
        )
        summary[site_id] = (hits, available)
        if hits > best_hits:
            best_hits, best_site = hits, site_id
    return summary, best_site


def _print_rows(title: str, columns: list[str], rows: list[Any]) -> None:
    print(f"\n{title}")
    print(" | ".join(columns))
    print("-|-".join("-" * len(column) for column in columns))
    if not rows:
        print("(none)")
        return
    for row in rows:
        print(" | ".join("" if _value(row, column) is None else str(_value(row, column)) for column in columns))


def _formula_rows(
    repo: PDMRepository,
    conn: Any,
    items: list[str],
    site_id: int,
    currency: str,
    as_of: str,
) -> list[Any]:
    if not items:
        return []
    placeholders = repo._placeholders(len(items))
    query = SQL_FORMULAS.format(placeholders=placeholders)
    return repo._execute(query, (site_id, currency, site_id, currency, *items, as_of), conn)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sif", type=Path, default=DEFAULT_SIF, help="SIF file to parse")
    parser.add_argument("--sample-size", type=int, default=10, help="Maximum calibration lines (default: 10)")
    parser.add_argument("--show-sql", action="store_true", help="Print the SELECT statements used")
    args = parser.parse_args()

    if not args.sif.is_file():
        print(f"ERROR: SIF not accessible: {args.sif}")
        print("Pass --sif <path>; no SKU data will be invented.")
        return 2

    service = SifValidationService(ApplicationContext())
    text = args.sif.read_text(encoding="utf-8", errors="ignore")
    currency, lines = service.parse_sif(text)
    lines = [line for line in lines if (line.currency or currency).upper() == "CNY"]
    if not lines:
        print("ERROR: no CNY lines were parsed from the SIF.")
        return 2
    sample = _sample(lines, args.sample_size)
    items = list(dict.fromkeys(line.base for line in sample if line.base))

    print(f"SIF: {args.sif}")
    print(f"Parsed CNY lines: {len(lines)}; calibration sample: {len(sample)}")
    print("Calibration sample (SKU | SIF base price):")
    for line in sample:
        print(f"  {line.base} | {line.pl:.2f}")

    if args.show_sql:
        print("\nSELECT-only SQL used by this script:")
        for name, query in {
            "CNY sites": SQL_CNY_SITES,
            "All sites": SQL_ALL_SITES,
            "Relevant item price formulas": SQL_FORMULAS,
            "Effective changes between dates": SQL_EFFECTIVE_CHANGES,
        }.items():
            print(f"\n-- {name}\n{query.strip()}")
        print("\nRepository UDF query: dbo.fnGetListPriceByItem(i.Item, ?, ?, s.SiteId, NULL)")

    repo = PDMRepository(ApplicationContext())
    conn = repo.get_connection()
    try:
        cny_sites = repo._execute(SQL_CNY_SITES, (currency,), conn)
        all_sites = repo._execute(SQL_ALL_SITES, (), conn)
        _print_rows("CNY-domestic Site records", ["SiteId", "Site", "DomCurrCode"], cny_sites)
        _print_rows("All calibration Site records", ["SiteId", "Site", "DomCurrCode"], all_sites)

        site_ids = [int(row.SiteId) for row in all_sites]
        site_by_id = {int(row.SiteId): row for row in all_sites}
        by_date: dict[str, dict[int, dict[str, float | None]]] = {}

        for as_of in DATES:
            rows = repo.fetch_item_base_prices_all_sites(items, currency, as_of, site_ids, conn)
            prices = _price_map(rows)
            by_date[as_of] = prices
            summary, selected = _calibration_summary(sample, all_sites, prices)

            print(f"\n=== {as_of}: fnGetListPriceByItem calibration ===")
            print("SiteId | Site | DomCurrCode | Exact SIF hits | Available sample items")
            for site_id in site_ids:
                row = site_by_id[site_id]
                hits, available = summary[site_id]
                marker = "  <-- resolve_site selection" if site_id == selected else ""
                print(f"{site_id} | {row.Site} | {row.DomCurrCode} | {hits} | {available}{marker}")
            print(f"resolve_site result: {selected}")
            availability_fallback = max(
                site_ids,
                key=lambda site_id: summary[site_id][1],
            )
            print(
                "Availability-only fallback (diagnostic only; rejected): "
                f"{availability_fallback} ({site_by_id[availability_fallback].Site}), "
                f"{summary[availability_fallback][1]} available sample items"
            )

            for site in cny_sites:
                site_id = int(site.SiteId)
                print(f"\nCNY-site price detail: date={as_of}, SiteId={site_id}, Site={site.Site}")
                print("SKU | SIF base | PDM price | State")
                for line in sample:
                    value = prices.get(site_id, {}).get(line.base)
                    state = "AVAILABLE" if value is not None else "NULL"
                    match = " exact" if value is not None and abs(value - line.pl) < 0.005 else ""
                    print(f"{line.base} | {line.pl:.2f} | {_price(value)} | {state}{match}")

        if 9 in site_by_id:
            site = site_by_id[9]
            print(f"\n=== Site 9 comparison ({site.Site}, DomCurrCode={site.DomCurrCode}) ===")
            print("SKU | SIF base | 24-Aug PDM | 07-Sep PDM")
            for line in sample:
                print(
                    f"{line.base} | {line.pl:.2f} | "
                    f"{_price(by_date[DATES[0]].get(9, {}).get(line.base))} | "
                    f"{_price(by_date[DATES[1]].get(9, {}).get(line.base))}"
                )

        for site in cny_sites:
            site_id = int(site.SiteId)
            print(f"\n=== Relevant PriceFormula rows: SiteId={site_id}, CNY ===")
            for as_of in DATES:
                rows = _formula_rows(repo, conn, items, site_id, currency, as_of)
                _print_rows(
                    f"Formula context on or before {as_of}",
                    ["Item", "ItemPriceCode", "PriceFormulaId", "EffectiveDate", "PriceFormula", "FirstPrice", "FirstBase"],
                    rows,
                )
            changes = repo._execute(SQL_EFFECTIVE_CHANGES, (site_id, currency, *DATES), conn)
            _print_rows(
                f"Formula changes between {DATES[0]} and {DATES[1]}",
                ["PriceFormulaId", "SiteId", "Site", "FormulaCurrency", "EffectiveDate", "PriceFormula", "FirstPrice", "FirstBase"],
                changes,
            )

        print("\nDIAGNOSTIC COMPLETE")
        print("Interpretation: resolve_site selects only the site with the highest non-zero exact SIF base-price hit count.")
        print("All reported prices come from PDM dbo.fnGetListPriceByItem through PDMRepository.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())