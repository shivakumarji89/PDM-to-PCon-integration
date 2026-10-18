"""Port of ExportThread material bookkeeping and option-value normalization."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Any


@dataclass(frozen=True)
class ConvertedMaterial:
    material: str
    description_key: str
    description: str
    other_description: str
    status: int
    is_fabric: bool
    dependent_option: bool
    has_super_parent: bool
    feature_position: str
    feature_length: int
    child_feature_length: int
    option_id: int


# Exact ParentOptValId special cases from ExportThread's option-report SELECT.
_OPTION_VALUE_PREFIXES = {
    149730: "m", 195468: "m",
    194397: "c", 195469: "c",
    197074: "m", 197077: "m",
    197075: "c", 197076: "c",
    197237: "m", 197329: "m",
    197238: "c", 197240: "c",
}


def normalize_legacy_option_report_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    flatten_fabrics: bool = False,
) -> list[dict[str, Any]]:
    """Apply source-visible option value transformations to raw procedure rows.

    This ports the CASE expression and FSC marker handling visible in
    ExportThread.cs. It is not a replacement for its full dependency traversal,
    feature ordering, or material/BOM assembly.
    """
    normalized_rows: list[dict[str, Any]] = []
    for source in rows:
        row = dict(source)
        order_value = "" if row.get("OrderCodeValue2") is None else str(row["OrderCodeValue2"])
        parent_id = row.get("ParentOptValId")
        try:
            prefix = _OPTION_VALUE_PREFIXES.get(int(parent_id)) if parent_id not in (None, "") else None
        except (TypeError, ValueError):
            prefix = None
        if prefix:
            order_value = prefix + order_value
        if flatten_fabrics and order_value.endswith("#"):
            continue
        row["OrderCodeValue2"] = order_value
        try:
            fsc_compliant = int(row.get("fsccompliant") or 0) == 1
        except (TypeError, ValueError):
            fsc_compliant = str(row.get("fsccompliant", "")).strip().lower() in {"true", "yes"}
        option_name = str(row.get("optval_name") or "").lower()
        row["OptChildCount"] = (
            1 if "customers own" in option_name
            else row.get("OptChildCount")
        )
        row["DisplayName"] = str(row.get("optval_name") or "") + ("#" if fsc_compliant else "")
        normalized_rows.append(row)
    return normalized_rows


class LegacyMaterialConversionRegistry:
    """Keep the parallel conversion metadata required by legacy material expansion."""

    def __init__(
        self,
        *,
        materials_on_item_tab: Iterable[str] = (),
        previously_converted: Iterable[str] = (),
        previous_feature_length: int = 2,
    ) -> None:
        self._materials_on_item_tab = set(materials_on_item_tab)
        self._previously_converted = set(previously_converted)
        self._previous_feature_length = previous_feature_length
        self._records: list[ConvertedMaterial] = []
        self._seen: set[str] = set()

    @property
    def records(self) -> tuple[ConvertedMaterial, ...]:
        return tuple(self._records)

    def add(
        self,
        material: str,
        description: str,
        other_description: str,
        status: int,
        dependent_option: bool,
        is_superproduct: bool,
        feature: str,
        feature_length: int,
        child_option_ids: Iterable[int],
    ) -> ConvertedMaterial | None:
        """Register one converted material; duplicate and already-exported values are ignored."""
        child_ids = tuple(child_option_ids)
        if not child_ids:
            raise ValueError("At least one child option ID is required by the legacy converter.")
        is_fabric = "#" in material
        normalized = material.replace("#", "")
        if (
            normalized in self._materials_on_item_tab
            or normalized in self._previously_converted
            or normalized in self._seen
        ):
            return None

        description_key = normalized.rsplit("-", 1)[-1]
        if normalized.endswith(("5-5", "5-6")):
            description_key = normalized[-3:]
        elif normalized.startswith(("9-FAB-5-5", "9-FAB-5-6")):
            description_key = normalized.replace("9-FAB-", "", 1)
        if normalized.startswith(("MRFN", "9-MRFN")) and "-AJ-" in normalized:
            description_key = "AJ"

        effective_feature_length = (
            self._previous_feature_length if feature_length == -1 else feature_length
        )
        record = ConvertedMaterial(
            material=normalized,
            description_key=description_key,
            description=description,
            other_description=other_description if other_description.strip() else "",
            status=int(status),
            is_fabric=is_fabric,
            dependent_option=bool(dependent_option),
            has_super_parent=bool(is_superproduct),
            feature_position=feature,
            feature_length=effective_feature_length,
            child_feature_length=-1,
            option_id=int(child_ids[0]),
        )
        self._seen.add(normalized)
        self._records.append(record)
        return record
