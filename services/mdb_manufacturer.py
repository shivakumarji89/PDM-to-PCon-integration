"""Manufacturer lookup for an OCD ``pcr_data_com_ocd.mdb`` package, for both real schema layouts.

Layout A  ``tCOMd_Package.com_ManufacturerID`` holds the manufacturer (older / fixture schema).
Layout B  ``tCOMd_Package`` has only ``com_ComGroupID``; the manufacturer is
          ``tCOMd_ComGroup.com_ManufacturerID`` (every real Seating / Tables / Knoll template).

The layout is detected from the columns the rows actually carry - never assumed - and a SQL
failure is reported as such instead of looking like an empty table (``MDBService.read_table``
returns ``[]`` for a failed query; ``read_tables`` raises).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

LAYOUT_PACKAGE = "A"
LAYOUT_COMGROUP = "B"


class ManufacturerLookupError(RuntimeError):
    """The package's manufacturer cannot be resolved from the template."""


@dataclass(frozen=True)
class PackageManufacturer:
    package: dict[str, Any]
    comgroup_id: Any
    manufacturer_db_id: Any        # com_ManufacturerID, None when the template leaves it NULL (layout A)
    manufacturer_code: str | None  # reg_ManufacturerCode, None -> caller applies its default
    layout: str


def read_package_manufacturer(mdb_svc, mdb: str | Path) -> PackageManufacturer:
    """Read ``tCOMd_Package`` / ``tCOMd_ComGroup`` from ``mdb`` and resolve the first package's manufacturer."""
    try:
        data = mdb_svc.read_tables(mdb, {
            "package": "SELECT * FROM tCOMd_Package",
            "group": "SELECT * FROM tCOMd_ComGroup",
        })
    except RuntimeError as exc:
        raise ManufacturerLookupError(f"Template schema is not usable: {exc}") from exc
    return resolve_package_manufacturer(mdb_svc, mdb, data["package"], data["group"])


def resolve_package_manufacturer(
    mdb_svc, mdb: str | Path, packages: list[dict[str, Any]], groups: list[dict[str, Any]],
) -> PackageManufacturer:
    """Resolve the manufacturer of ``packages[0]`` from already-read Package / ComGroup rows."""
    if not packages:
        raise ManufacturerLookupError("Template tCOMd_Package is empty.")
    package = dict(packages[0])
    if package.get("com_PackageID") is None:
        raise ManufacturerLookupError("Template package has no com_PackageID.")
    comgroup_id = package.get("com_ComGroupID")

    manufacturer_id: Any = None
    layout = LAYOUT_PACKAGE
    if "com_ManufacturerID" in package:
        manufacturer_id = package["com_ManufacturerID"]
    if manufacturer_id is None:
        group_has_column = any("com_ManufacturerID" in g for g in groups)
        if "com_ManufacturerID" not in package and not group_has_column:
            raise ManufacturerLookupError(
                "Template has no com_ManufacturerID in tCOMd_Package or tCOMd_ComGroup; "
                "the package's manufacturer cannot be determined."
            )
        if group_has_column:
            if comgroup_id is None:
                if "com_ManufacturerID" in package:
                    return PackageManufacturer(package, None, None, None, LAYOUT_PACKAGE)
                raise ManufacturerLookupError(
                    "Template package has no com_ComGroupID, so its ComGroup manufacturer cannot be found."
                )
            matches = [g for g in groups if g.get("com_ComGroupID") == comgroup_id]
            if not matches:
                raise ManufacturerLookupError(
                    f"Template package references ComGroup {comgroup_id}, which is not in tCOMd_ComGroup."
                )
            if len(matches) > 1:
                raise ManufacturerLookupError(
                    f"Template tCOMd_ComGroup has {len(matches)} rows for ComGroup {comgroup_id}; "
                    "the manufacturer is ambiguous."
                )
            manufacturer_id = matches[0].get("com_ManufacturerID")
            if "com_ManufacturerID" not in package:
                layout = LAYOUT_COMGROUP
                if manufacturer_id is None:
                    raise ManufacturerLookupError(
                        f"Template ComGroup {comgroup_id} has no com_ManufacturerID value."
                    )
    if manufacturer_id is None:
        return PackageManufacturer(package, comgroup_id, None, None, layout)

    try:
        rows = mdb_svc.read_tables(mdb, {
            "manufacturer": "SELECT reg_ManufacturerCode FROM tCOMd_Manufacturer "
                            f"WHERE com_ManufacturerID = {int(manufacturer_id)}",
        })["manufacturer"]
    except (RuntimeError, TypeError, ValueError) as exc:
        raise ManufacturerLookupError(f"Manufacturer {manufacturer_id!r} cannot be read: {exc}") from exc
    if len(rows) != 1 or not rows[0].get("reg_ManufacturerCode"):
        raise ManufacturerLookupError(
            f"Template manufacturer {manufacturer_id} is "
            f"{'missing from' if not rows else 'ambiguous in'} tCOMd_Manufacturer."
        )
    return PackageManufacturer(
        package, comgroup_id, manufacturer_id, str(rows[0]["reg_ManufacturerCode"]), layout)
