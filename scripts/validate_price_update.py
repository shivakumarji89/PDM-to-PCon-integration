"""Headless validation for the batch price-list roll-over (XOCD).

Builds a small repository of two XOCD packages, each with EUR + GBP open
(9999) price lists, then runs the batch roll-over with an injected price lookup
and checks that, per package and currency:
* the open list is end-dated to the day before the effective date (values kept),
* a new ``<prefix>_<token>`` list is registered and appended with fresh values,
* both currencies and both packages are processed (one keyed token for all),
* an already-ended list is left untouched.

Run:  $env:PYTHONPATH="."; python scripts/validate_price_update.py
"""
from __future__ import annotations

import csv
import shutil
import tempfile
from pathlib import Path

from core.application_context import ApplicationContext

_DELIM = ";"
_ENC = "latin-1"


def _seed(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    rows = [
        # program;list;article;varcond;S;level;;;value;fix;cur;from;to;
        ["always", "EURO_2024", "AER", "", "S", "B", "", "", "90", "1", "EUR", "20240101", "20241231", ""],
        ["always", "EURO_2025", "AER", "", "S", "B", "", "", "100", "1", "EUR", "20250101", "99991231", ""],
        ["always", "EURO_2025", "AER", " 9502=OK", "S", "X", "", "", "5", "0", "EUR", "20250101", "99991231", ""],
        ["always", "GBP_2025", "AER", "", "S", "B", "", "", "80", "1", "GBP", "20250101", "99991231", ""],
        ["always", "EURO_2025", "*", "SUPER1", "S", "", "", "", "50", "0", "EUR", "20250101", "99991231", ""],
    ]
    with (folder / "xocd_price.csv").open("w", encoding=_ENC, newline="") as fh:
        csv.writer(fh, delimiter=_DELIM, lineterminator="\r\n").writerows(rows)
    (folder / "xocd_pricelists.csv").write_text(
        "EURO_2025;EURO 2025\r\nGBP_2025;GBP 2025\r\n", encoding=_ENC)


def _read(path: Path) -> list[list[str]]:
    with path.open("r", encoding=_ENC, newline="") as fh:
        return [r for r in csv.reader(fh, delimiter=_DELIM) if r]


def _price(currency, is_global, article, varcond, level):
    """Fresh prices, keyed the way the lookup is called (base + upcharge)."""
    if "=" in (varcond or ""):                    # option upcharge / increment
        return {"EUR": 6.0, "GBP": 5.0}.get(currency)
    table = {("EUR", "AER"): 110.0, ("EUR", "SUPER1"): 55.0, ("GBP", "AER"): 96.0}
    return table.get((currency, varcond if is_global else article))


def main() -> int:
    root = Path(tempfile.gettempdir()) / "validate_price_update"
    shutil.rmtree(root, ignore_errors=True)
    _seed(root / "seriesA")
    _seed(root / "seriesB")

    ctx = ApplicationContext()
    svc = ctx.price_update_service

    scan = svc.run_batch(root, False, "20260101", "2026", _price, apply=False)
    print(f"scan: ok={scan.ok} packages={len(scan.packages)}")
    for pkg in scan.packages:
        for lr in pkg.lists:
            print(f"  {Path(pkg.package).name} [{lr.currency}] {lr.old_list} -> {lr.new_list}: "
                  f"rows={lr.rows} changed={lr.changed}")

    result = svc.run_batch(root, False, "20260101", "2026", _price, apply=True)
    print(f"\napply: ok={result.ok} packages={len(result.packages)}")

    rows = _read(root / "seriesA" / "xocd_price.csv")
    new = [r for r in rows if r[1] in ("EURO_2026", "GBP_2026")]
    old_open = [r for r in rows if r[1] in ("EURO_2025", "GBP_2025")]
    ended_2024 = [r for r in rows if r[1] == "EURO_2024"]
    lists = {r[0] for r in _read(root / "seriesA" / "xocd_pricelists.csv")}

    checks = {
        "both packages applied": all(p.applied for p in result.packages),
        "old lists end-dated 20251231": all(r[12] == "20251231" for r in old_open),
        "old values untouched (AER=100)": any(r[2] == "AER" and r[8] == "100" for r in old_open),
        "new EURO_2026 AER = 110": any(r[1] == "EURO_2026" and r[2] == "AER" and r[8] == "110" for r in new),
        "new GBP_2026 AER = 96": any(r[1] == "GBP_2026" and r[2] == "AER" and r[8] == "96" for r in new),
        "new global present (55)": any(r[1] == "EURO_2026" and r[2] == "*" and r[8] == "55" for r in new),
        "new upcharge refreshed (6)": any(r[1] == "EURO_2026" and "=" in r[3] and r[8] == "6" for r in new),
        "new rows start 20260101": all(r[11] == "20260101" for r in new),
        "new lists registered": {"EURO_2026", "GBP_2026"} <= lists,
        "already-ended 2024 untouched": bool(ended_2024) and ended_2024[0][12] == "20241231",
    }

    # Resumability 1: a re-run with the same token finds everything done and
    # neither duplicates rows nor rolls the new list onto itself.
    rerun = svc.run_batch(root, False, "20260101", "2026", _price, apply=True)
    a_after = _read(root / "seriesA" / "xocd_price.csv")
    euro2026 = [r for r in a_after if r[1] == "EURO_2026"]
    checks["re-run: all lists done"] = all(
        lr.status == "done" for p in rerun.packages for lr in p.lists)
    checks["re-run: no duplicate EURO_2026 rows"] = len(euro2026) == 3
    checks["re-run: no EURO_2027 created"] = not any(r[1] == "EURO_2027" for r in a_after)

    # Resumability 2: a leftover target row from an interrupted run is detected
    # (partial) on scan and rebuilt cleanly on apply - no stray, no duplicate.
    part = root / "seriesC"
    _seed(part)
    with (part / "xocd_price.csv").open("a", encoding=_ENC, newline="") as fh:
        csv.writer(fh, delimiter=_DELIM, lineterminator="\r\n").writerow(
            ["always", "EURO_2026", "AER", "", "S", "B", "", "", "999", "1", "EUR", "20260101", "99991231", ""])
    scan_c = svc.run_batch(part, False, "20260101", "2026", _price, apply=False)
    statuses = [lr.status for p in scan_c.packages for lr in p.lists if lr.old_list != lr.new_list]
    checks["partial detected on scan"] = "partial" in statuses
    svc.run_batch(part, False, "20260101", "2026", _price, apply=True)
    c_new = [r for r in _read(part / "xocd_price.csv") if r[1] == "EURO_2026"]
    checks["partial healed: stray 999 gone"] = not any(r[8] == "999" for r in c_new)
    checks["partial healed: correct AER=110"] = any(r[2] == "AER" and r[3] == "" and r[8] == "110" for r in c_new)
    checks["partial healed: single base AER row"] = len([r for r in c_new if r[2] == "AER" and r[3] == ""]) == 1

    # _lookup_key: reconstruct the PDM (item, option_id, code) for both buttons.
    key = svc._lookup_key
    checks["key: article base"] = key(False, "NOALE2", "11") == ("NOALE211", "", "")
    checks["key: article upcharge"] = key(False, "NOALE2", "11 9502=OK") == ("NOALE211", "9502", "OK")
    checks["key: upcharge no suffix"] = key(False, "NOALE2", " 9502=OK") == ("NOALE2", "9502", "OK")
    checks["key: global base"] = key(True, "", "DTWB1E3.C") == ("DTWB1E3.C", "", "")
    checks["key: global increment"] = key(True, "", "DTWB1E3.C 3785=CD") == ("DTWB1E3.C", "3785", "CD")

    # MDB date parity: the bridge serialises dates as '/Date(ms)/'; open detection,
    # date-literal writing and the NOPRICE guard all key off decoding that. Dates
    # are decoded timezone-aware (local wall-clock), so a value stored at local
    # midnight reads back as its own calendar day.
    from datetime import datetime, timedelta
    _off = datetime.now().astimezone().utcoffset() or timedelta(0)
    _midnight_ms = int(((datetime(2025, 6, 1) - _off) - datetime(1970, 1, 1)).total_seconds() * 1000)
    checks["bridge decodes local-midnight to its day"] = (
        svc._bridge_ymd(f"/Date({_midnight_ms})/") == "20250601")
    checks["bridge open sentinel -> 9999"] = svc._is_open_ymd("/Date(253402194600000)/")
    checks["bridge yyyymmdd passthrough"] = svc._bridge_ymd("20260101") == "20260101"
    from services.price_update_service import _mdb_date_literal
    checks["date literal midnight"] = _mdb_date_literal("20260101") == "#2026-01-01 00:00:00#"
    checks["date literal 9999"] = _mdb_date_literal("99991231") == "#9999-12-31 00:00:00#"
    checks["dated list has year"] = svc._is_dated_list("EURO_2025")
    checks["NOPRICE not dated (skipped)"] = not svc._is_dated_list("NOPRICE")
    checks["mid-year list dated"] = svc._is_dated_list("EURO_2025_2")

    print("\nchecks:")
    ok = True
    for name, passed in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and bool(passed)
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
