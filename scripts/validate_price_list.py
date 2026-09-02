"""Headless validation for named price lists + date roll-over (Slice A).

Verifies the PriceListService chains each currency's validity windows without
gap/overlap, keeps currencies independent, and that price lists round-trip
through snapshot serialization.

Run:  $env:PYTHONPATH="."; python scripts/validate_price_list.py
"""
from __future__ import annotations

import sys

from core.application_context import ApplicationContext
from models.product import Product
from services.snapshot_serialization import snapshot_from_dict, snapshot_to_dict


def main() -> int:
    ctx = ApplicationContext()
    svc = ctx.price_list_service
    snap = ctx.snapshot_manager.create_empty_snapshot(
        Product(id="p1", code="P1", name="Prod", range_name="R")
    )

    # Add two EUR lists out of order + one GBP list.
    svc.add_price_list(snap, "euro_2027", "Euro 2027", "EUR", "20270101")
    svc.add_price_list(snap, "euro_2026", "Euro 2026", "eur", "20260101")
    svc.add_price_list(snap, "gbp_2026", "GBP 2026", "GBP", "20260401")

    lists = {pl.id: pl for pl in svc.price_lists(snap)}
    assert lists["euro_2026"].currency == "EUR", "currency upper-cased"
    # Roll-over within EUR: 2026 closes the day before 2027 starts; 2027 open.
    assert lists["euro_2026"].date_from == "20260101"
    assert lists["euro_2026"].date_to == "20261231", lists["euro_2026"].date_to
    assert lists["euro_2027"].date_to == "99991231", lists["euro_2027"].date_to
    print("OK: EUR chain rolls over (2026 -> 20261231, 2027 open)")

    # GBP is an independent chain: single list stays open.
    assert lists["gbp_2026"].date_to == "99991231", lists["gbp_2026"].date_to
    print("OK: GBP chain independent (single list stays open)")

    # Duplicate id rejected.
    assert svc.add_price_list(snap, "euro_2026", "dup", "EUR", "20280101") is None
    print("OK: duplicate id rejected")

    # Remove re-opens the previous list.
    svc.remove_price_list(snap, "euro_2027")
    lists = {pl.id: pl for pl in svc.price_lists(snap)}
    assert "euro_2027" not in lists
    assert lists["euro_2026"].date_to == "99991231", lists["euro_2026"].date_to
    print("OK: removing the later list re-opens the earlier (20261231 -> 99991231)")

    # Add it back, then edit the start date -> re-chain.
    svc.add_price_list(snap, "euro_2028", "Euro 2028", "EUR", "20280101")
    svc.set_price_list(snap, "euro_2028", date_from="20270601")
    lists = {pl.id: pl for pl in svc.price_lists(snap)}
    assert lists["euro_2026"].date_to == "20270531", lists["euro_2026"].date_to
    print("OK: editing a start date re-chains (2026 -> 20270531)")

    # Serialization round-trip.
    restored = snapshot_from_dict(snapshot_to_dict(snap))
    ids = {pl.id: pl.date_to for pl in restored.price_lists}
    assert ids == {pl.id: pl.date_to for pl in snap.price_lists}, ids
    print("OK: price lists round-trip through serialization")

    # -- Slice B: export wiring (per-list price rows) -------------------
    from models.price_record import PriceRecord

    snap.price_records = [
        PriceRecord(article_code="A1", level="B", value=100.0, currency="EUR"),
        PriceRecord(article_code="A1", variant_condition=" 9502=OK", level="X",
                    value=10.0, currency="EUR"),
        PriceRecord(article_code="A1", level="B", value=90.0, currency="GBP"),
    ]
    snap.price_lists = []
    svc.add_price_list(snap, "euro_2026", "Euro 2026", "EUR", "20260101")
    svc.add_price_list(snap, "gbp_2026", "GBP 2026", "GBP", "20260101")
    xocd = ctx.xocd_export_service
    ctxd = {"program": "PROG", "price_list": "STD"}
    lists = xocd._active_price_lists(snap, ctxd)
    rows = xocd._prices(snap, ctxd, lists)
    euro_rows = [r for r in rows if r[1] == "euro_2026"]
    gbp_rows = [r for r in rows if r[1] == "gbp_2026"]
    assert len(euro_rows) == 2 and all(r[10] == "EUR" for r in euro_rows), euro_rows
    assert len(gbp_rows) == 1 and gbp_rows[0][10] == "GBP", gbp_rows
    assert euro_rows[0][11] == "20260101" and euro_rows[0][12] == "99991231", euro_rows[0]
    print("OK: export emits per-list price rows (EUR->euro_2026, GBP->gbp_2026, list dates)")

    # Fallback: no lists + multiple currencies -> ONE default list PER CURRENCY
    # (OCD requires a price list to be single-currency).
    snap.price_lists = []
    rows = xocd._prices(snap, ctxd, xocd._active_price_lists(snap, ctxd))
    lists = {r[1] for r in rows}
    assert lists == {"STD_EUR", "STD_GBP"}, lists
    assert len(rows) == 3, rows
    assert all(r[10] == "EUR" for r in rows if r[1] == "STD_EUR")
    assert all(r[10] == "GBP" for r in rows if r[1] == "STD_GBP")
    print("OK: no lists + multi-currency -> one STD_<currency> list each (single-currency)")

    # Single-currency fallback stays the plain 'STD' list (backward compatible).
    snap.price_records = [
        PriceRecord(article_code="A1", level="B", value=100.0, currency="GBP"),
    ]
    rows = xocd._prices(snap, ctxd, xocd._active_price_lists(snap, ctxd))
    assert {r[1] for r in rows} == {"STD"} and rows[0][10] == "GBP", rows
    print("OK: no lists + single currency -> plain 'STD' list (unchanged)")

    # -- Slice D: pricing accumulates records by currency ---------------
    from services.pricing_service import PricingService

    existing = [
        PriceRecord(article_code="A1", level="B", value=100.0, currency="EUR"),
        PriceRecord(article_code="A1", level="B", value=90.0, currency="GBP"),
    ]
    merged = PricingService._accumulate_by_currency(
        existing, [PriceRecord(article_code="A1", level="B", value=95.0, currency="GBP")], "GBP"
    )
    eur = [r for r in merged if r.currency == "EUR"]
    gbp = [r for r in merged if r.currency == "GBP"]
    assert len(eur) == 1 and eur[0].value == 100.0, "EUR kept"
    assert len(gbp) == 1 and gbp[0].value == 95.0, "GBP replaced"
    print("OK: pricing accumulates by currency (EUR kept, GBP replaced)")

    # -- Slice E: compute targets every price-list currency -------------
    from services.pricing_service import PriceParams
    from models.price_list import PriceList

    svc_p = PricingService.__new__(PricingService)  # no ctx needed for these
    # Defined EUR + GBP lists -> both currencies computed (order preserved).
    snap.price_lists = [
        PriceList(id="euro_2025", label="EUR 2025", currency="EUR"),
        PriceList(id="gbp_2025", label="GBP 2025", currency="GBP"),
    ]
    assert svc_p.target_currencies(snap, PriceParams(currency="USD")) == ["EUR", "GBP"]
    # No lists -> fall back to the selected combo currency only.
    snap.price_lists = []
    assert svc_p.target_currencies(snap, PriceParams(currency="usd")) == ["USD"]
    # No lists + "All" (empty currency) -> GBP default.
    assert svc_p.target_currencies(snap, PriceParams(currency="")) == ["GBP"]
    print("OK: compute targets price-list currencies (else selected currency)")

    # Multi-currency accumulate replaces ALL computed currencies, keeps others.
    existing = [
        PriceRecord(article_code="A1", level="B", value=100.0, currency="EUR"),
        PriceRecord(article_code="A1", level="B", value=90.0, currency="GBP"),
        PriceRecord(article_code="A1", level="B", value=80.0, currency="USD"),
    ]
    new = [
        PriceRecord(article_code="A1", level="B", value=110.0, currency="EUR"),
        PriceRecord(article_code="A1", level="B", value=95.0, currency="GBP"),
    ]
    merged = PricingService._accumulate_currencies(existing, new, ["EUR", "GBP"])
    by_cur = {r.currency: r.value for r in merged}
    assert by_cur == {"EUR": 110.0, "GBP": 95.0, "USD": 80.0}, merged
    print("OK: multi-currency accumulate replaces EUR+GBP, keeps USD")

    print("\nvalidate_price_list: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
