"""Distribution-region resolution for OCD/XOCD packages.

The authoritative region set for a product lives in the OCD MDB table
``tCOMd_DistributionRegion`` and is mirrored 1:1 as repository directory levels
(``<program>/<REGION>/1/db``). This service reads both so the exporter and the
MDB->XOCD reconcile use the *real* region list instead of a hardcoded value, and
can diff the two sides for parity.

The master region uses the OFML standard code ``ANY`` (``tCOMd_DistributionRegion``
fixed master, parent ``None``); market regions (``EURO``/``GBP``/``NOPRICE`` ...)
are its children. Nothing here is currency-hardcoded: codes come from the MDB or
the repository, never guessed.
"""
from __future__ import annotations

from pathlib import Path

from models.distribution_region import DistributionRegion
from services.base_service import BaseService

#: OFML standard master-region code (``tCOMd_DistributionRegion`` root, parent
#: NULL). Documented as the fixed master in docs/pcon_reference/dsr-3.7_en.md.
MASTER_CODE = "ANY"


class DistributionRegionService(BaseService):
    """Reads distribution regions from the OCD MDB and the repository."""

    def master_region_code(self) -> str:
        """The master/root region code written into ``ocd_version.csv`` for the
        full master-data package (OFML standard ``ANY``)."""
        return MASTER_CODE

    # -- authoritative: OCD MDB -----------------------------------------

    def regions_from_mdb(self, mdb_path: str | Path) -> list[DistributionRegion]:
        """The full region set from ``tCOMd_DistributionRegion`` (authoritative).

        Ordered master first, then children by id. Returns ``[]`` when the MDB
        bridge is unavailable or the table cannot be read.
        """
        svc = self.context.mdb_service
        if not svc.is_available():
            return []
        rows = svc.read_table(
            mdb_path,
            "SELECT com_DistributionRegionID, reg_DistributionRegionCode, "
            "reg_DistributionRegionLabel, com_ParentDistributionRegionID "
            "FROM tCOMd_DistributionRegion ORDER BY com_DistributionRegionID",
        )
        by_id = {
            r.get("com_DistributionRegionID"): r.get("reg_DistributionRegionCode")
            for r in rows
        }
        regions: list[DistributionRegion] = []
        for r in rows:
            code = (r.get("reg_DistributionRegionCode") or "").strip()
            if not code:
                continue
            parent_id = r.get("com_ParentDistributionRegionID")
            regions.append(DistributionRegion(
                code=code,
                label=(r.get("reg_DistributionRegionLabel") or code).strip(),
                parent_code=(by_id.get(parent_id) or None) if parent_id else None,
            ))
        return regions

    # -- authoritative: repository --------------------------------------

    def regions_from_repository(self, product_root: str | Path) -> list[DistributionRegion]:
        """The region set present in a repository product folder.

        A region is any immediate subdirectory that carries an OCD package at
        ``<name>/1/db/ocd_version.csv``; the region *code* is read from that
        file's 6th field (so the folder name is confirmed, not assumed). The
        sibling OGF geometry folder (``1/``) has no such file and is skipped.
        """
        root = Path(product_root)
        if not root.is_dir():
            return []
        out: list[DistributionRegion] = []
        for child in sorted(p for p in root.iterdir() if p.is_dir()):
            version = child / "1" / "db" / "ocd_version.csv"
            if not version.is_file():
                continue
            code = self._region_from_version(version) or child.name
            out.append(DistributionRegion(
                code=code,
                label=code,
                parent_code=None if code == MASTER_CODE else MASTER_CODE,
            ))
        return out

    @staticmethod
    def _region_from_version(version_csv: Path) -> str | None:
        """Region code = 6th ``;``-delimited field of ``ocd_version.csv``."""
        try:
            line = version_csv.read_text(encoding="latin-1").splitlines()[0]
        except (OSError, IndexError):
            return None
        fields = line.split(";")
        return fields[5].strip() if len(fields) > 5 else None

    # -- parity ----------------------------------------------------------

    def diff_regions(
        self, mdb_path: str | Path, product_root: str | Path
    ) -> dict[str, list[str]]:
        """Compare the MDB region codes with the repository's.

        Returns ``{'mdb': [...], 'repo': [...], 'only_mdb': [...],
        'only_repo': [...]}`` (all sorted). Empty ``only_*`` lists == parity.
        """
        mdb = {r.code for r in self.regions_from_mdb(mdb_path)}
        repo = {r.code for r in self.regions_from_repository(product_root)}
        return {
            "mdb": sorted(mdb),
            "repo": sorted(repo),
            "only_mdb": sorted(mdb - repo),
            "only_repo": sorted(repo - mdb),
        }
