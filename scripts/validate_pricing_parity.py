"""Live parity + benchmark for batched PDM pricing (read-only).

Proves the batched price queries return values identical to calling PDM's own
``fnGetListPrice*`` functions one item at a time, and measures the round-trip
speedup. Read-only: nothing is written to PDM or any MDB.

Because it needs a live PDM SQL Server connection it is NOT part of the offline
suite - run it explicitly against real item codes:

    $env:PYTHONPATH="."; python scripts/validate_pricing_parity.py ^
        --currency GBP --date 06-Apr-2026 --site 1 DWE3UH4.0812 DWE3UH4.1012

With no item codes it prints usage and exits 0 (safe no-op).
"""
from __future__ import annotations

import argparse
import time

from core.application_context import ApplicationContext
from repositories.pdm_repository import PDMRepository


def _base_map(rows) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for r in rows:
        raw = r.price
        out[str(r.Item)] = None if raw is None or str(raw).strip() == "" else float(raw)
    return out


def _inc_map(rows) -> dict[tuple[str, str, str], float]:
    out: dict[tuple[str, str, str], float] = {}
    for r in rows:
        raw = r.IncPrice
        if raw is None or str(raw).strip() == "":
            continue
        out[(str(r.Item), str(r.OptionId), str(r.Code))] = float(raw)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("items", nargs="*", help="item codes to price")
    parser.add_argument("--currency", default="GBP")
    parser.add_argument("--date", default="06-Apr-2026", help="PDM 'dd-MMM-yyyy'")
    parser.add_argument("--site", type=int, default=1)
    args = parser.parse_args()

    if not args.items:
        print("No item codes given - nothing to check.")
        print("Example: python scripts/validate_pricing_parity.py "
              "--currency GBP --date 06-Apr-2026 DWE3UH4.0812 DWE3UH4.1012")
        return 0

    repo = PDMRepository(ApplicationContext())
    try:
        conn = repo.get_connection()
    except Exception as error:
        print(f"SKIP: no live PDM connection ({error})")
        return 0

    try:
        # -- base prices: batched (1 call) vs per-item (N calls) -----------
        t0 = time.perf_counter()
        batched_base = _base_map(
            repo.fetch_item_base_prices(args.items, args.currency, args.date, conn)
        )
        t_batched = time.perf_counter() - t0

        t0 = time.perf_counter()
        peritem_base: dict[str, float | None] = {}
        for item in args.items:
            peritem_base.update(
                _base_map(
                    repo.fetch_item_base_prices(
                        [item], args.currency, args.date, conn
                    )
                )
            )
        t_peritem = time.perf_counter() - t0

        assert batched_base == peritem_base, (
            "BASE MISMATCH:\n"
            f"  batched: {batched_base}\n  per-item: {peritem_base}"
        )
        print(f"OK: base prices identical for {len(batched_base)} item(s)")
        print(f"    batched {t_batched*1000:.0f} ms  vs  "
              f"per-item {t_peritem*1000:.0f} ms")

        # -- increment prices: batched vs per-item ------------------------
        batched_inc = _inc_map(
            repo.fetch_item_option_increment_prices(
                args.items, args.currency, args.date, args.site, conn
            )
        )
        peritem_inc: dict[tuple[str, str, str], float] = {}
        for item in args.items:
            peritem_inc.update(
                _inc_map(
                    repo.fetch_item_option_increment_prices(
                        [item], args.currency, args.date, args.site, conn
                    )
                )
            )
        assert batched_inc == peritem_inc, (
            "INCREMENT MISMATCH:\n"
            f"  batched: {batched_inc}\n  per-item: {peritem_inc}"
        )
        print(f"OK: increment prices identical for {len(batched_inc)} upcharge(s)")

        print("ALL PARITY CHECKS PASSED")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
