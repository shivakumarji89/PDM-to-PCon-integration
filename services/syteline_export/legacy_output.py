"""Legacy SyteLine output path and record-normalization rules.

Ported from PDMMaintenance/ExportThread.cs: allocateFiles, writeData,
writeToStream, and removeNonStandardCharacters. These helpers preserve observed
legacy behavior; they do not implement the SQL-driven item/material transforms.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


# Exact allow-list used by legacy removeNonStandardCharacters, plus the
# explicitly accepted CR/LF/tab characters.
_LEGACY_ALLOWED = frozenset(
    "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-+=_!\"£$%^&*()[]<>,./?#~{}:;@'`|\\ "
)
_LEGACY_MATERIAL_PREFIX = "9-F"
_LEGACY_SUPERPRODUCT_MARKER = "BOCFAB-OF"
_LEGACY_HAR_MARKER = "2-HAR"


@dataclass(frozen=True)
class LegacyOutputPaths:
    item: Path
    material: Path
    superprod: Path | None
    description: Path | None
    planning: Path | None
    priceformula: Path | None
    productcode: Path | None


def allocate_legacy_output_paths(
    export_directory: str | Path,
    export_file_name: str,
    site: str,
    currency: str,
    *,
    miller_cad: bool = False,
    format_csi: bool = False,
) -> LegacyOutputPaths:
    """Reproduce ExportThread.allocateFiles path naming without writing files."""
    root = Path(export_directory).expanduser()
    if miller_cad:
        stem = f"{site.lower()}{currency}"
        item = root / f"b-{stem}.asc"
        material = root / f"o-{stem}.asc"
        default_name = f"b-{stem}"
        if export_file_name != default_name:
            suffix = export_file_name.replace(default_name, "").lstrip("_")
            item = root / f"b-{stem}_{suffix}.asc"
            material = root / f"o-{stem}_{suffix}.asc"
        return LegacyOutputPaths(item, material, None, None, None, None, None)

    suffix = "_csi" if format_csi else ""
    temp = root / "temp"
    return LegacyOutputPaths(
        item=temp / f"{export_file_name}_item_data{suffix}.txt",
        material=temp / f"{export_file_name}_material_data{suffix}.txt",
        superprod=temp / f"{export_file_name}_superprod_data{suffix}.txt",
        description=temp / f"{export_file_name}_description_data{suffix}.txt",
        planning=temp / f"{export_file_name}_planning_data{suffix}.txt",
        priceformula=temp / f"{export_file_name}_priceformula_data{suffix}.txt",
        productcode=temp / f"{export_file_name}_productcode_data{suffix}.txt",
    )


def remove_legacy_nonstandard_characters(data: str) -> str:
    """Keep only characters accepted by the legacy C# writer."""
    return "".join(
        character
        for character in data
        if character in _LEGACY_ALLOWED or character in "\r\n\t"
    ).replace("\r\n\r\n", "\r\n")


def normalize_legacy_record(data: str) -> str:
    """Apply source-defined replacements performed before a legacy record write."""
    if _LEGACY_SUPERPRODUCT_MARKER in data and _LEGACY_HAR_MARKER in data:
        data = data.replace("-BOCFAB-", "-")
    return remove_legacy_nonstandard_characters(data.replace("HAR-F", "H-F"))


class LegacyRecordDeduplicator:
    """Model the two distinct duplicate checks in legacy writeData."""

    def __init__(self) -> None:
        self._item_records: set[str] = set()
        self._materials_on_item_tab: set[str] = set()

    def accept(self, data: str, *, is_item: bool) -> bool:
        if data.startswith(_LEGACY_MATERIAL_PREFIX):
            material = data.split("\t", 1)[0]
            if material in self._materials_on_item_tab:
                return False
            self._materials_on_item_tab.add(material)
        if is_item:
            if data in self._item_records:
                return False
            self._item_records.add(data)
        return True

    def filter_records(self, records: Iterable[str], *, is_item: bool) -> list[str]:
        return [record for record in records if self.accept(record, is_item=is_item)]
