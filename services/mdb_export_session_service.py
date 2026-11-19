"""Shared MDB export session: one product -> one MDB, updated incrementally.

The first workflow export (Articles) *initializes* the product's MDB exactly
once by copying the category template; every later workflow reuses that file
through the session recorded here.  All database I/O goes through
:class:`~services.mdb_service.MDBService` - this module adds no second access
path.

Persistence: one small JSON file per product under
``%LOCALAPPDATA%\\MK Product Workbench\\export_sessions`` (override with
``store_dir``). It holds only the MDB path, package/ComGroup/manufacturer ids,
template boilerplate rows and the source->MDB id maps. Nothing sensitive.
Recovery validates that the MDB still exists and still carries the same
package id; a stale session is reported, never silently replaced.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from models.mdb_export_session import MdbExportSession
from models.snapshot import Snapshot
from services import ocd_export_service as _ocd
from services.base_service import BaseService
from services.xocd_export_service import XocdExportService

DEFAULT_MDB_NAME = "pcr_data_com_ocd.mdb"


class ExportSessionError(RuntimeError):
    """The export session cannot be created or is no longer valid."""


class MdbExportSessionService(BaseService):
    """Create, persist, recover and update per-product MDB export sessions."""

    #: Test/override hook; ``None`` uses the per-user application data folder.
    store_dir: Path | None = None

    # -- Identity & persistence ----------------------------------------

    @staticmethod
    def product_key(snapshot: Snapshot) -> str:
        """Stable product identity: PDM product id, falling back to its code."""
        product = snapshot.product if snapshot is not None else None
        if product is None:
            raise ExportSessionError("No product loaded.")
        ident = str(getattr(product, "id", "") or "").strip()
        code = str(getattr(product, "code", "") or "").strip()
        key = ident or code or str(getattr(product, "name", "") or "").strip()
        if not key:
            raise ExportSessionError("The loaded product has no identity to key an MDB session on.")
        return f"id:{key}" if ident else f"code:{key}"

    def _store(self) -> Path:
        if self.store_dir is not None:
            return Path(self.store_dir)
        base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
        return Path(base) / "MK Product Workbench" / "export_sessions"

    def _file(self, key: str) -> Path:
        return self._store() / (hashlib.sha1(key.encode("utf-8")).hexdigest()[:20] + ".json")

    def save(self, session: MdbExportSession) -> None:
        """Atomically persist ``session`` (temp file + replace)."""
        path = self._file(session.product_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(session.to_dict(), indent=1), encoding="utf-8")
        os.replace(tmp, path)

    def load(self, snapshot: Snapshot) -> MdbExportSession | None:
        """The stored session for the loaded product (no validation)."""
        key = self.product_key(snapshot)
        path = self._file(key)
        if not path.is_file():
            return None
        try:
            session = MdbExportSession.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError) as exc:
            raise ExportSessionError(f"Export session file is unreadable ({path.name}): {exc}") from exc
        if session.product_key != key:  # hash collision / manual edit: never cross products
            raise ExportSessionError("Export session belongs to a different product.")
        return session

    def attach_existing(
        self, snapshot: Snapshot, mdb_path: str | Path, template_kind: str = "",
    ) -> MdbExportSession:
        """Attach an existing series repository MDB without copying or clearing it.

        This path is used only when the user opens a normal series repository.
        The MDB remains at its original repository location and all existing
        rows and identifiers are preserved.
        """
        key = self.product_key(snapshot)
        if self.load(snapshot) is not None:
            raise ExportSessionError("This product already has an MDB export session.")
        mdb = Path(mdb_path).resolve()
        if not mdb.is_file():
            raise ExportSessionError(f"Selected repository MDB does not exist: {mdb}")
        mdb_svc = self.context.mdb_service
        if not mdb_svc.is_available():
            raise ExportSessionError("32-bit PowerShell / ACE OLEDB bridge unavailable.")

        queries = {
            "package": "SELECT * FROM tCOMd_Package",
            **{f"proto:{table}": f"SELECT TOP 1 * FROM [{table}]"
               for table in _ocd._PRODUCT_TABLES},
        }
        try:
            data = mdb_svc.read_tables(mdb, queries)
        except RuntimeError as exc:
            raise ExportSessionError(f"Selected repository MDB schema is not usable: {exc}") from exc
        if not data["package"]:
            raise ExportSessionError("Selected repository MDB has no tCOMd_Package row.")
        package = data["package"][0]
        package_id = package.get("com_PackageID")
        if package_id is None:
            raise ExportSessionError("Selected repository MDB package has no ID.")

        comgroup_id = package.get("com_ComGroupID")
        manufacturer_id = _ocd._MATERIAL_MANUFACTURER
        if package.get("com_ManufacturerID") is not None:
            rows = mdb_svc.read_table(
                mdb,
                "SELECT TOP 1 reg_ManufacturerCode FROM tCOMd_Manufacturer "
                f"WHERE com_ManufacturerID = {int(package['com_ManufacturerID'])}",
            )
            if rows and rows[0].get("reg_ManufacturerCode"):
                manufacturer_id = str(rows[0]["reg_ManufacturerCode"])

        prototypes = {}
        for table in _ocd._PRODUCT_TABLES:
            rows = data[f"proto:{table}"]
            if not rows:
                continue
            proto = dict(rows[0])
            proto.pop(_ocd._PK.get(table, ""), None)
            for column in [name for name in proto if str(name).startswith("sys_tmp")]:
                proto.pop(column, None)
            prototypes[table] = proto

        product = snapshot.product
        program_code = str(package.get("reg_ProgramCode") or
                           snapshot.generation_program or XocdExportService.program_key(product)).strip()
        series_id = str(package.get("com_ComGroupCode") or
                        snapshot.generation_series or XocdExportService.series_id(product)).strip()
        session = MdbExportSession(
            product_key=key,
            mdb_path=str(mdb),
            product_code=str(getattr(product, "code", "") or ""),
            product_name=str(getattr(product, "name", "") or ""),
            template_kind=template_kind,
            manufacturer_id=manufacturer_id,
            package_id=package_id,
            comgroup_id=comgroup_id,
            program_code=program_code,
            series_id=series_id,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            prototypes=prototypes,
            attached_existing=True,
        )
        try:
            self.save(session)
        except OSError as exc:
            raise ExportSessionError(f"Could not save the export session: {exc}") from exc
        return session

    def get_active(self, snapshot: Snapshot) -> MdbExportSession | None:
        """The loaded product's session, or ``None`` when no MDB exists yet.

        Raises :class:`ExportSessionError` when a session exists but its MDB
        file is gone, so a missing file is never mistaken for "first export".
        """
        session = self.load(snapshot)
        if session is None:
            return None
        if not Path(session.mdb_path).is_file():
            raise ExportSessionError(
                f"The MDB for this product no longer exists:\n{session.mdb_path}\n"
                "Restore the file, or discard the session to create a new MDB."
            )
        return session

    def discard(self, snapshot: Snapshot) -> None:
        """Forget the product's session (the MDB file itself is never deleted)."""
        path = self._file(self.product_key(snapshot))
        if path.is_file():
            path.unlink()

    def session_for_mdb_path(self, mdb_path: str | Path) -> MdbExportSession | None:
        """The session that owns ``mdb_path``, if any (guards legacy overwrite)."""
        wanted = os.path.normcase(os.path.abspath(str(mdb_path)))
        store = self._store()
        if not store.is_dir():
            return None
        for file in store.glob("*.json"):
            try:
                session = MdbExportSession.from_dict(json.loads(file.read_text(encoding="utf-8")))
            except (OSError, ValueError, TypeError):
                continue
            if os.path.normcase(os.path.abspath(session.mdb_path)) == wanted:
                return session
        return None

    # -- Workflow status -------------------------------------------------

    def record_workflow(
        self, session: MdbExportSession, workflow: str, counts: dict[str, Any] | None = None,
        status: str = "exported",
    ) -> None:
        session.workflow_status[workflow] = {
            "status": status,
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "counts": dict(counts or {}),
        }

    # -- Initialization ---------------------------------------------------

    def initialize(
        self, snapshot: Snapshot, dest: str | Path, template_kind: str | None = None,
        template_path: str | Path | None = None,
    ) -> MdbExportSession:
        """Create the product's MDB from its category template - exactly once.

        The template is copied to a staging file beside the destination, the
        template's example-product rows are removed and the package/ComGroup
        are renamed in ONE transaction, and only then is the staging file moved
        into place. A failure at any step leaves nothing at ``dest``. An
        existing file at ``dest`` is never overwritten.
        """
        key = self.product_key(snapshot)
        if self.load(snapshot) is not None:
            raise ExportSessionError("This product already has an MDB export session.")
        mdb_svc = self.context.mdb_service
        if not mdb_svc.is_available():
            raise ExportSessionError("32-bit PowerShell / ACE OLEDB bridge unavailable.")

        product = snapshot.product
        kind = (template_kind or snapshot.generation_template
                or _ocd.OcdExportService._infer_template(product)).strip().lower()
        kind = _ocd._TEMPLATE_ALIASES.get(kind, kind)
        # A template selected from Open Repository takes precedence over the
        # legacy bundled-template resolver. The selected source is copied into
        # the product output; the shared SVN template is never modified.
        template = Path(template_path) if template_path else _ocd._template_for_kind(kind)
        if template is None or not Path(template).is_file():
            source = str(template) if template_path else str(_ocd._TEMPLATE_ROOT)
            raise ExportSessionError(
                f"Selected '{kind}' MDB template is missing: {source}."
            )

        mdb = Path(dest)
        if mdb.suffix.lower() != ".mdb":
            mdb = mdb / DEFAULT_MDB_NAME
        if mdb.exists():
            raise ExportSessionError(
                f"{mdb} already exists and is not this product's export MDB. "
                "Choose another folder; an existing file is never overwritten."
            )

        staging = mdb.with_name(mdb.name + ".init")
        try:
            try:
                mdb_svc.copy_template(template, staging)
            except OSError as exc:
                raise ExportSessionError(f"Copy template failed: {exc}") from exc

            queries = {
                "package": "SELECT * FROM tCOMd_Package",
                "group": "SELECT * FROM tCOMd_ComGroup",
                **{f"proto:{t}": f"SELECT TOP 1 * FROM [{t}]" for t in _ocd._PRODUCT_TABLES},
            }
            try:
                data = mdb_svc.read_tables(staging, queries)
            except RuntimeError as exc:
                raise ExportSessionError(f"Template schema is not usable: {exc}") from exc
            if not data["package"]:
                raise ExportSessionError("Template tCOMd_Package is empty.")
            package = data["package"][0]
            package_id = package["com_PackageID"]
            comgroup_id = package.get("com_ComGroupID")

            manufacturer_id = _ocd._MATERIAL_MANUFACTURER
            if package.get("com_ManufacturerID") is not None:
                rows = mdb_svc.read_table(
                    staging,
                    "SELECT TOP 1 reg_ManufacturerCode FROM tCOMd_Manufacturer "
                    f"WHERE com_ManufacturerID = {int(package['com_ManufacturerID'])}",
                )
                if rows and rows[0].get("reg_ManufacturerCode"):
                    manufacturer_id = str(rows[0]["reg_ManufacturerCode"])

            prototypes = {}
            for table in _ocd._PRODUCT_TABLES:
                rows = data[f"proto:{table}"]
                if not rows:
                    continue
                proto = dict(rows[0])
                proto.pop(_ocd._PK.get(table, ""), None)
                for col in [c for c in proto if str(c).startswith("sys_tmp")]:
                    proto.pop(col, None)
                prototypes[table] = proto

            picking = getattr(self.context, "material_picking_service", None)
            if picking is not None:
                picking.ensure_package_defaults(snapshot)
            program_code = (snapshot.generation_program or XocdExportService.program_key(product)).strip()
            series_id = (snapshot.generation_series or XocdExportService.series_id(product)).strip()
            label = product.range_name or product.name or program_code
            package_set = {
                "reg_ProgramCode": program_code,
                "reg_ProgramLabel": label,
                "com_MaterialMF": snapshot.material_manufacturer_code or _ocd._MATERIAL_MANUFACTURER,
                "com_MaterialPK": snapshot.material_package_code or _ocd._MATERIAL_PACKAGE,
            }

            # Only the template's *example product* rows are removed - at this
            # point nothing of ours exists in the file. Done once, here.
            ops: list[dict[str, Any]] = [{"op": "delete", "table": t} for t in _ocd._PRODUCT_TABLES]
            ops.append({"op": "update", "table": "tCOMd_Package", "set": package_set,
                        "where": {"com_PackageID": package_id}})
            if comgroup_id is not None:
                ops.append({"op": "update", "table": "tCOMd_ComGroup",
                            "set": {"com_ComGroupCode": series_id, "com_ComGroupLabel": label},
                            "where": {"com_ComGroupID": comgroup_id}})
            batch = mdb_svc.execute_batch(staging, ops, transaction=True)
            if not batch.ok:
                raise ExportSessionError(f"MDB initialization failed: {batch.first_error()}")

            # Re-check: the move below must not race a file created meanwhile.
            if mdb.exists():
                raise ExportSessionError(f"{mdb} appeared during initialization; not overwritten.")
            os.replace(staging, mdb)
        finally:
            try:
                if staging.exists():
                    staging.unlink()
            except OSError:
                pass

        session = MdbExportSession(
            product_key=key,
            mdb_path=str(mdb),
            product_code=str(getattr(product, "code", "") or ""),
            product_name=str(getattr(product, "name", "") or ""),
            template_kind=kind,
            manufacturer_id=manufacturer_id,
            package_id=package_id,
            comgroup_id=comgroup_id,
            program_code=program_code,
            series_id=series_id,
            created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            prototypes=prototypes,
        )
        try:
            self.save(session)
        except OSError as exc:
            # Do not leave an MDB that no session knows about.
            try:
                mdb.unlink()
            except OSError:
                pass
            raise ExportSessionError(f"Could not save the export session: {exc}") from exc
        return session
