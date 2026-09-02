"""Headless validation for distribution regions (OCD/XOCD).

Checks:
  * master region code = OFML standard ``ANY``;
  * ``xocd_version.csv`` is written with the master region (not the PDM Site scope);
  * ``_region_from_version`` reads the 6th field;
  * when reachable, the Aeron OCD MDB and repository expose the SAME region set
    (ANY/EURO/GBP/NOPRICE) - the parity the user asked to verify.

Run:  $env:PYTHONPATH="."; python scripts/validate_distribution_region.py
"""
from __future__ import annotations

import csv
import tempfile
from pathlib import Path

from core.application_context import ApplicationContext
from services.distribution_region_service import MASTER_CODE
from services.xocd_export_service import XocdExportService

AERON_MDB = r"C:\HermanMillerOFMLSVN\Staging\HermanMiller\WS\Seating\Seating\Aeron\pcr_data_com_ocd.mdb"
AERON_REPO = r"C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx\aeron"
EXPECTED = {"ANY", "EURO", "GBP", "NOPRICE"}


def main() -> int:
    ctx = ApplicationContext()
    svc = ctx.distribution_region_service

    assert MASTER_CODE == "ANY", MASTER_CODE
    assert svc.master_region_code() == "ANY"
    print("OK: master region code = ANY (OFML standard)")

    # xocd_version.csv carries the master region, NOT config.catalogue_region.
    ctx.config.catalogue_region = "UK"  # the PDM Site scope must NOT leak here
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        from services.xocd_export_service import XocdExportResult
        XocdExportService(ctx)._write_version(out, XocdExportResult())
        row = next(csv.reader(
            (out / "xocd_version.csv").open("r", encoding="latin-1", newline=""),
            delimiter=";",
        ))
        assert row[5] == "ANY", row
    print("OK: xocd_version.csv region = ANY (not the 'UK' Site scope)")

    # _region_from_version reads field 6.
    with tempfile.TemporaryDirectory() as tmp:
        vf = Path(tmp) / "ocd_version.csv"
        vf.write_text("4.2;OCD_4;1.34.9;20171229;99991231;EURO;;0;tables;\r\n",
                      encoding="latin-1")
        assert svc._region_from_version(vf) == "EURO"
    print("OK: _region_from_version reads the 6th field")

    # Authoritative sides (skip gracefully when unreachable).
    mdb = svc.regions_from_mdb(AERON_MDB) if ctx.mdb_service.is_available() else []
    repo = svc.regions_from_repository(AERON_REPO)

    if mdb:
        codes = {r.code for r in mdb}
        assert codes == EXPECTED, codes
        master = [r for r in mdb if r.is_master]
        assert [r.code for r in master] == ["ANY"], master
        assert all(r.parent_code == "ANY" for r in mdb if not r.is_master)
        print(f"OK: MDB regions = {sorted(codes)} (ANY master, rest children)")
    else:
        print("SKIP: OCD MDB unreachable (32-bit bridge or file) - MDB check skipped")

    if repo:
        codes = {r.code for r in repo}
        assert codes == EXPECTED, codes
        print(f"OK: repository regions = {sorted(codes)}")
    else:
        print("SKIP: Aeron repository not present - repo check skipped")

    if mdb and repo:
        diff = svc.diff_regions(AERON_MDB, AERON_REPO)
        assert not diff["only_mdb"] and not diff["only_repo"], diff
        print(f"OK: MDB <-> repository region parity ({diff['mdb']})")

    print("\nvalidate_distribution_region: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
