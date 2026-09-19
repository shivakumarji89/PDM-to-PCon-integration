"""OFML ProgInfo material-picking rules.

The OFML proginfo table is a three-column ordered control table. In particular,
@PropInfoPicPrefix entries select the prefix used for property value pictures;
the first matching entry wins. This service keeps that rule evaluation separate
from class creation and MDB writing so the same semantics can be reused by
workflow creation and export.
"""
from __future__ import annotations

import re
from typing import Any

from models.snapshot import Snapshot
from services.base_service import BaseService


class MaterialPickingService(BaseService):
    """Evaluate the material-related subset of an OFML ProgInfo table."""

    INFO_TYPE = "@PropInfoPicPrefix"
    DEFAULT_MANUFACTURER = "hmx"
    DEFAULT_PACKAGE = "basics"
    DEFAULT_MAP = "hm"

    def ensure_package_defaults(self, snapshot: Snapshot | None) -> None:
        if snapshot is None:
            return
        if not (snapshot.material_manufacturer_code or "").strip():
            snapshot.material_manufacturer_code = self.DEFAULT_MANUFACTURER
        if not (snapshot.material_package_code or "").strip():
            snapshot.material_package_code = self.DEFAULT_PACKAGE

    def set_prog_info_rows(
        self, snapshot: Snapshot | None, rows: list[dict[str, Any]]
    ) -> None:
        """Persist normalized ProgInfo rows without changing their order."""
        if snapshot is None:
            return
        normalized: list[dict[str, str]] = []
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            normalized.append({
                "type": str(row.get("type") or "").strip(),
                "argument": str(row.get("argument") or "").strip(),
                "value": str(row.get("value") or "").strip(),
            })
        snapshot.prog_info_rows = normalized

    def prop_info_pic_prefix(
        self,
        snapshot: Snapshot | None,
        property_name: str,
        property_key: str = "",
        property_value: str = "",
    ) -> str:
        """Return the first matching @PropInfoPicPrefix value."""
        if snapshot is None:
            return ""
        for row in snapshot.prog_info_rows or []:
            if str(row.get("type") or "").strip() != self.INFO_TYPE:
                continue
            argument = str(row.get("argument") or "").strip()
            if argument and not self._conditions_match(
                argument, property_name, property_key, property_value
            ):
                continue
            return str(row.get("value") or "")
        return ""

    def material_map_name(self, prefix: str) -> str:
        """Extract the material-map token from a ::manufacturer::package::map prefix."""
        parts = [p for p in str(prefix or "").split("::") if p]
        return parts[-1] if parts else self.DEFAULT_MAP

    def mapped_properties(
        self, snapshot: Snapshot | None, properties: list[Any]
    ) -> list[tuple[Any, str, str]]:
        """Return (property, prefix, map-name) for properties with a prefix."""
        out: list[tuple[Any, str, str]] = []
        seen: set[str] = set()
        for prop in properties or []:
            pid = str(getattr(prop, "id", "") or "")
            if not pid or pid in seen:
                continue
            prefix = self.prop_info_pic_prefix(
                snapshot,
                str(getattr(prop, "name", "") or ""),
                str(getattr(prop, "code", "") or ""),
            )
            if not prefix:
                continue
            seen.add(pid)
            out.append((prop, prefix, self.material_map_name(prefix)))
        return out

    @staticmethod
    def _conditions_match(
        argument: str,
        property_name: str,
        property_key: str,
        property_value: str,
    ) -> bool:
        for condition in MaterialPickingService._condition_vectors(argument):
            match = re.match(
                r"^\s*\[\s*(@[A-Za-z0-9_]+)\s*,\s*(.*?)\s*\]\s*$",
                condition,
            )
            if not match:
                return False
            kind = match.group(1)
            values = MaterialPickingService._quoted_values(match.group(2))
            if not values:
                return False

            if kind == "@PropKey":
                ok = any(property_key.startswith(v) for v in values)
            elif kind == "@PropKeyNOT":
                ok = not any(property_key.startswith(v) for v in values)
            elif kind == "@PropName":
                ok = any(property_name.startswith(v) for v in values)
            elif kind == "@PropNameNOT":
                ok = not any(property_name.startswith(v) for v in values)
            elif kind == "@PropValue":
                ok = property_value in values
            else:
                return False
            if not ok:
                return False
        return True

    @staticmethod
    def _condition_vectors(argument: str) -> list[str]:
        text = argument.strip()
        if text.startswith("[") and text.endswith("]"):
            text = text[1:-1]
        vectors: list[str] = []
        start = 0
        depth = 0
        quote = ""
        for i, char in enumerate(text):
            if quote:
                if char == quote and (i == 0 or text[i - 1] != "\\"):
                    quote = ""
                continue
            if char in "\"'":
                quote = char
            elif char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
            elif char == "," and depth == 0:
                chunk = text[start:i].strip()
                if chunk:
                    vectors.append(chunk)
                start = i + 1
        chunk = text[start:].strip()
        if chunk:
            vectors.append(chunk)
        return vectors

    @staticmethod
    def _quoted_values(value_text: str) -> list[str]:
        return [
            a if a != "" else b
            for a, b in re.findall(r'"([^"]*)"|\'([^\']*)\'', value_text)
        ]
