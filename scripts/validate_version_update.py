"""Headless validation for the bulk export-version updater.

Copies a real product's OCD + ODB MDBs into a temp repository, reads their
current versions, writes a new keyed version into the selected series, and reads
both files back. Never touches the SVN originals.

Run:  $env:PYTHONPATH="."; python scripts/validate_version_update.py
"""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from core.application_context import ApplicationContext

_SRC = Path(r"C:\HermanMillerOFMLSVN\Staging\HermanMiller_old\WS\Seating\Seating\Aeron")


def main() -> int:
    ctx = ApplicationContext()
    if not ctx.mdb_service.is_available():
        print("SKIP: 32-bit PowerShell / ACE bridge unavailable on this host.")
        return 0
    ocd_src = _SRC / "pcr_data_com_ocd.mdb"
    odb_src = _SRC / "pcr_data_geo_odb.mdb"
    if not (ocd_src.is_file() and odb_src.is_file()):
        print(f"SKIP: source MDBs not found under {_SRC}")
        return 0

    repo = Path(tempfile.gettempdir()) / "validate_version" / "TestSeries"
    if repo.exists():
        shutil.rmtree(repo.parent)
    repo.mkdir(parents=True)
    shutil.copy2(ocd_src, repo / "pcr_data_com_ocd.mdb")
    shutil.copy2(odb_src, repo / "pcr_data_geo_odb.mdb")

    svc = ctx.version_update_service

    checks: dict[str, bool] = {}

    # 1. parse.
    checks["parse 1.34.0"] = svc.parse_version("1.34.0") == (1, 34, 0)
    checks["parse loose 'v2.5.7 build'"] = svc.parse_version("v2.5.7 build") == (2, 5, 7)
    checks["parse too few -> None"] = svc.parse_version("1.2") is None

    # 2. discover + read current versions.
    folders = svc.series_folders(str(repo.parent))
    series = svc.read_series(folders)
    print("discovered:", [(s.program, s.ocd_version, s.odb_version) for s in series])
    checks["one series discovered"] = len(series) == 1
    sv = series[0]
    checks["series has both OCD + ODB"] = bool(sv.ocd_path and sv.odb_path)
    checks["current OCD version read"] = sv.ocd_version not in ("", "None.None.None")
    checks["current ODB version read"] = sv.odb_version not in ("", "None.None.None")

    # 3. update both files to a new version.
    results = svc.update(series, 3, 41, 7)
    checks["update ok (no error)"] = all(r.error is None for r in results)
    checks["OCD updated flag"] = all(r.ocd_updated for r in results)
    checks["ODB updated flag"] = all(r.odb_updated for r in results)

    # 4. read back - both databases now carry the new version.
    after = svc.read_series(folders)[0]
    print("after update:", after.ocd_version, "/", after.odb_version)
    checks["OCD version now 3.41.7"] = after.ocd_version == "3.41.7"
    checks["ODB version now 3.41.7"] = after.odb_version == "3.41.7"

    # 5. release date stamped to today in both databases.
    m = ctx.mdb_service
    ymd = ctx.price_update_service._bridge_ymd
    ocd_date = ymd(m.read_table(str(repo / "pcr_data_com_ocd.mdb"),
                                "SELECT reg_ReleaseDate FROM tCOMd_Package")[0]["reg_ReleaseDate"])
    odb_date = ymd(m.read_table(str(repo / "pcr_data_geo_odb.mdb"),
                                "SELECT reg_ReleaseDate FROM tGEOd_Package")[0]["reg_ReleaseDate"])
    from datetime import datetime
    today = datetime.now().strftime("%Y%m%d")
    print("release dates:", ocd_date, "/", odb_date, "(today", today + ")")
    checks["OCD release date = today"] = ocd_date == today
    checks["ODB release date = today"] = odb_date == today

    print("\nchecks:")
    ok = True
    for name, passed in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and bool(passed)
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
