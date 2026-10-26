"""Bulk product-version updater for published OCD + ODB packages.

The export version of a series is stored as ``Major.Minor.Build`` in BOTH the
commercial and geometry databases of its package folder:

* OCD - ``pcr_data_com_ocd.mdb`` -> ``tCOMd_Package.reg_Version{Major,Minor,Build}``
* ODB - ``pcr_data_geo_odb.mdb`` -> ``tGEOd_Package.reg_Version{Major,Minor,Build}``

This service discovers the series under a repository (reusing the price-update
package discovery, so the same non-product-folder guard and multi-root support
apply), reads each one's current OCD/ODB version, and writes a user-keyed version
into the selected series' both files. Optionally stamps the release date.
"""
from __future__ import annotations

import re
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from core.cancellation import OperationCancelled, checkpoint
from services.base_service import BaseService
from services.price_update_service import (
    _execute_batch, _mdb_date_literal, _publish_staged, _read_table, _staged_file,
)

_ODB_FILE = "pcr_data_geo_odb.mdb"
#: The package table that carries the version, per database.
_PACKAGE_TABLE = {"ocd": "tCOMd_Package", "odb": "tGEOd_Package"}


@dataclass
class SeriesVersion:
    """One series' folder + its current OCD/ODB export versions."""

    folder: str
    program: str = ""
    ocd_path: str = ""
    odb_path: str = ""
    ocd_version: str = ""   # "M.m.b" or "" when absent/unreadable
    odb_version: str = ""


@dataclass
class VersionUpdateResult:
    """Outcome of writing the version into one series' two databases."""

    series: str = ""
    ocd_updated: bool = False
    odb_updated: bool = False
    error: str | None = None


class VersionUpdateService(BaseService):
    """Read + bulk-write the export version across OCD and ODB packages."""

    @staticmethod
    def parse_version(text: str) -> tuple[int, int, int] | None:
        """``"1.34.0"`` -> ``(1, 34, 0)``. Needs three numeric parts."""
        parts = re.findall(r"\d+", text or "")
        if len(parts) < 3:
            return None
        return int(parts[0]), int(parts[1]), int(parts[2])

    def series_folders(self, repository: str | Path) -> list[Path]:
        """The product folders under the repository (fast - just the OCD-file
        glob, with the shared non-product-folder guard)."""
        return [ocd.parent for ocd in
                self.context.price_update_service._discover_packages(repository, is_mdb=True)]

    def read_series(self, folders, progress=None) -> list[SeriesVersion]:
        """Read each folder's current OCD + ODB versions. ``progress(done, total,
        text)`` is called per series for a progress bar."""
        folders = list(folders)
        out: list[SeriesVersion] = []
        for i, folder in enumerate(folders, 1):
            checkpoint()
            folder = Path(folder)
            if progress:
                progress(i, len(folders), folder.name)
            ocd = folder / "pcr_data_com_ocd.mdb"
            odb = folder / _ODB_FILE
            sv = SeriesVersion(folder=str(folder),
                               ocd_path=str(ocd) if ocd.is_file() else "",
                               odb_path=str(odb) if odb.is_file() else "")
            if sv.ocd_path:
                sv.program, sv.ocd_version = self._read_version(sv.ocd_path, "ocd")
            if sv.odb_path:
                prog, sv.odb_version = self._read_version(sv.odb_path, "odb")
                sv.program = sv.program or prog
            sv.program = sv.program or folder.name
            out.append(sv)
        checkpoint()
        return out

    def _read_version(self, mdb: str, db: str) -> tuple[str, str]:
        """``(program, "M.m.b")`` from a package table; ``("", "")`` if unreadable."""
        table = _PACKAGE_TABLE[db]
        try:
            rows = _read_table(self.context.mdb_service,
                mdb, f"SELECT reg_ProgramCode, reg_VersionMajor, reg_VersionMinor, "
                     f"reg_VersionBuild FROM [{table}]")
        except OSError:
            return "", ""
        if not rows:
            return "", ""
        r = rows[0]
        version = (f"{r.get('reg_VersionMajor')}.{r.get('reg_VersionMinor')}."
                   f"{r.get('reg_VersionBuild')}")
        return str(r.get("reg_ProgramCode") or ""), version

    def update(
        self, series, major: int, minor: int, build: int, progress=None,
    ) -> list[VersionUpdateResult]:
        """Write ``major.minor.build`` into every selected series' OCD + ODB
        package rows and stamp today's release date.

        Cancellation discards both staged databases for the current series.
        Completed series remain published. The two replacements form a single
        cancellation boundary, but are not atomic against process/power loss.
        """
        series = list(series)
        results: list[VersionUpdateResult] = []
        try:
            for i, sv in enumerate(series, 1):
                checkpoint()
                results.append(self._update_one(sv, major, minor, build))
                if progress:
                    progress(i, len(series), sv.program or Path(sv.folder).name)
            checkpoint()
        except OperationCancelled as exc:
            completed = sum(r.error is None for r in results)
            raise OperationCancelled(
                f"Cancelled. {completed} series committed; "
                f"{len(results)} series completed.") from exc
        return results

    def _update_one(
        self, sv: SeriesVersion, major: int, minor: int, build: int
    ) -> VersionUpdateResult:
        result = VersionUpdateResult(series=sv.program or Path(sv.folder).name)
        version_fields: dict[str, Any] = {
            "reg_VersionMajor": major, "reg_VersionMinor": minor, "reg_VersionBuild": build,
        }
        release = {"reg_ReleaseDate": _mdb_date_literal(datetime.now().strftime("%Y%m%d"))}
        svc = self.context.mdb_service
        # Both databases are staged before publishing either. Separate update
        # ops avoid ADODB's mixed int/datetime recordset cast failure, while one
        # transaction per staged MDB keeps the version and date together.
        with ExitStack() as stack:
            staged = {}
            updated = []
            for db, path in (("ocd", sv.ocd_path), ("odb", sv.odb_path)):
                checkpoint()
                if not path:
                    continue
                path = Path(path)
                target = stack.enter_context(_staged_file(path))
                table = _PACKAGE_TABLE[db]
                batch = _execute_batch(svc, target, [
                    {"op": "update", "table": table, "set": version_fields},
                    {"op": "update", "table": table, "set": release},
                ], transaction=True)
                if not batch.ok:
                    result.error = batch.first_error() or "Version update failed."
                    return result
                staged[path] = target
                updated.append(db)
            _publish_staged(staged)
            result.ocd_updated = "ocd" in updated
            result.odb_updated = "odb" in updated
        return result
