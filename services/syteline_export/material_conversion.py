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

        # ExportThread stages one child ID per option row. A missing child is
        # represented by the sentinel -2, except customer-owned options, which
        # point to the legacy customer-owned material option 8512. Later rows
        # for the same staged option can replace -2 with a real child ID; that
        # grouping/reconciliation is handled by the traversal layer.
        child_id = row.get("OptChildId")
        if child_id is not None and str(child_id).strip():
            try:
                resolved_child_ids = (int(child_id),)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid OptChildId in legacy option report: {child_id!r}") from exc
        elif "customers own" in option_name:
            resolved_child_ids = (8512,)
        else:
            resolved_child_ids = (-2,)
        row["ResolvedChildOptionIds"] = resolved_child_ids

        row["DisplayName"] = str(row.get("optval_name") or "") + ("#" if fsc_compliant else "")
        normalized_rows.append(row)
    return normalized_rows


def order_legacy_option_report_rows(
    rows: Iterable[Mapping[str, Any]],
    *,
    item_code: str = "",
) -> list[dict[str, Any]]:
    """Apply ExportThread's option-report ORDER BY to already-fetched rows.

    The legacy query orders by Range2, Product2, DisplayOrder, descending
    OrderCodeValue2 length, then DisplayOrdinal. For OF-prefixed items it
    measures length after replacing each '9B' with '9B__', preserving the
    legacy tie-breaking behavior. This orders rows only; it does not perform
    dependency traversal or feature grouping.
    """
    def nullable_text(value: Any) -> tuple[int, str]:
        # SQL Server ASC sorts NULL before non-NULL; preserve that ordering.
        return (0, "") if value is None else (1, str(value))

    def number(value: Any, *, default: float = 0) -> float:
        if value is None or str(value).strip() == "":
            return default
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid numeric option-report sort value: {value!r}") from exc

    is_of_item = str(item_code).startswith("OF")

    def sort_key(source: Mapping[str, Any]) -> tuple[Any, ...]:
        order_value = "" if source.get("OrderCodeValue2") is None else str(source["OrderCodeValue2"])
        measured = order_value.replace("9B", "9B__") if is_of_item else order_value
        return (
            nullable_text(source.get("Range2")),
            nullable_text(source.get("Product2")),
            number(source.get("DisplayOrder")),
            -len(measured),
            number(source.get("DisplayOrdinal")),
        )

    return [dict(row) for row in sorted(rows, key=sort_key)]


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


def reconcile_legacy_option_child_ids(rows):
    """Merge child IDs for duplicate legacy option identities, preserving order."""
    result = []
    groups = {}
    identity_fields = (
        "OptionValueId", "OptionId", "IsFabric", "OptDescId",
        "optvalDescId", "OrderCodeValue2", "ParentOptValId", "OptChildCount",
    )
    for source in rows:
        row = dict(source)
        key = tuple(row.get(name) for name in identity_fields)
        name = str(row.get("optval_name") or "").lower()
        child = row.get("OptChildId")
        if child is not None and str(child).strip():
            try:
                child_ids = [int(child)]
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid OptChildId in legacy option report: {child!r}") from exc
        elif "customers own" in name:
            child_ids = [8512]
        else:
            child_ids = [-2]
        if key not in groups:
            row["ResolvedChildOptionIds"] = tuple(child_ids)
            groups[key] = row
            result.append(row)
            continue
        merged = list(groups[key]["ResolvedChildOptionIds"])
        for child_id in child_ids:
            if child_id != -2 and -2 in merged:
                merged.remove(-2)
            if child_id not in merged:
                merged.append(child_id)
        groups[key]["ResolvedChildOptionIds"] = tuple(merged)
    return result


_PARENT_SUBSTITUTION_OPTION_IDS = {9275, 9313, 9279, 9325, 9283, 9327, 9287, 9329}


def resolve_legacy_parent_material(
    current_material: str,
    option_id: int,
    parent_option_value_id: int | str | None,
    parent_options: Iterable[Mapping[str, Any]],
) -> tuple[str, bool]:
    """Apply ExportThread stage-16 parent-material substitution.

    parent_options must follow the legacy parallel-array order and expose
    OptionValueId and Material. The boolean reports whether the parent ID was
    found. This helper does not implement later dependency/BOM assembly.
    """
    try:
        wanted_parent_id = int(parent_option_value_id) if parent_option_value_id not in (None, "") else None
        wanted_option_id = int(option_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("Legacy parent and option IDs must be numeric when provided.") from exc

    material = str(current_material or "")
    for parent in parent_options:
        raw_id = parent.get("OptionValueId")
        if raw_id in (None, ""):
            continue
        try:
            candidate_id = int(raw_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid parent OptionValueId: {raw_id!r}") from exc
        if candidate_id != wanted_parent_id:
            continue

        parent_material = str(parent.get("Material") or "")
        special_option = wanted_option_id in _PARENT_SUBSTITUTION_OPTION_IDS
        legacy_garment_case = (
            (material.startswith("GHS") or material.startswith("GHG"))
            and wanted_option_id in {8, 9487}
        )
        if (material and material in parent_material) or special_option or legacy_garment_case:
            material = parent_material
        return material, True
    return material, False


_MRFN_PARENT_SUFFIX_OPTION_VALUE_IDS = {300464, 300563, 300564, 300565, 300566, 300567}


def build_legacy_dependency_material(
    *,
    item_code: str,
    parent_material: str,
    feature_position: str,
    option_position: int,
    option_value_id: int,
    parent_option_code: str = "",
    is_fabric: bool = False,
    ignore_option_dependencies: bool = False,
    child_option_count: int | str = 0,
    is_superproduct: bool = False,
    use_resolved_superproduct_parent: bool = False,
) -> str | None:
    """Build the dependency material code using ExportThread stage 16.6–16.7.

    Returns None when the source conditions do not create a dependency. This
    is only the code-construction step; sequencing, increments, and BOM output
    remain separate legacy stages.
    """
    parent = str(parent_material or "")
    feature = str(feature_position or "")
    try:
        value_id = int(option_value_id)
        position = int(option_position)
        child_count = int(child_option_count or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError("Option value, feature position, and child count must be valid numeric values.") from exc

    if is_fabric or ignore_option_dependencies or child_count <= 0:
        return None
    parent_for_code = (
        str(item_code or "")
        if is_superproduct and not use_resolved_superproduct_parent
        else parent
    )

    if not feature or "|" not in feature:
        raise ValueError("feature_position must contain the legacy 'featureIndex|orderCode' format.")
    feature_index, order_code = feature.split("|", 1)
    if not feature_index:
        raise ValueError("feature_position must include a feature index.")
    code = f"9-{parent_for_code}-[opt{position}]-{order_code.replace(' ', '_')}"
    if parent.startswith(("MRFN", "9-MRFN")) and value_id in _MRFN_PARENT_SUFFIX_OPTION_VALUE_IDS:
        code += "-" + str(parent_option_code or "")
    return code



def assign_legacy_feature_positions(rows):
    """Deduplicate sorted option rows and assign stage-10 feature positions.

    Apply catalogue/item-specific legacy allowlists before calling this helper.
    """
    output = []
    seen = set()
    last_option_id = None
    feature_index = 0
    identity_fields = ("OptionValueId", "OptionId", "IsFabric", "OptDescId", "optvalDescId", "OrderCodeValue2", "ParentOptValId", "OptChildCount")
    for source in rows:
        row = dict(source)
        try:
            value_id = int(row["OptionValueId"])
            option_id = int(row["OptionId"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Feature rows require numeric OptionValueId and OptionId.") from exc
        if value_id in {292, 299, 300}:
            continue
        identity = tuple(row.get(field) for field in identity_fields)
        if identity in seen:
            continue
        seen.add(identity)
        if last_option_id is None or option_id != last_option_id:
            feature_index += 1
            last_option_id = option_id
        code = str(row.get("OrderCodeValue2") or "").replace("#", "")
        row["FeatureIndex"] = feature_index
        row["FeaturePosition"] = f"{feature_index}|{code}"
        output.append(row)
    return output


def resolve_legacy_feature_length(
    *,
    configured_length: int | str,
    maximum_order_code_length: int | str,
    is_fabric: bool,
    length5_features: bool = False,
) -> int:
    """Apply ExportThread stage-20 feature-length rules to resolved SQL values.

    The caller must resolve the selected option (including dependent fabric
    option selection) and provide its SLFeatureLength and maximum order-code
    length from the catalogue-scoped query. This function ports only the
    source-visible post-query rules and performs no database access.
    """
    try:
        feature_length = int(configured_length)
        maximum_length = int(maximum_order_code_length)
    except (TypeError, ValueError) as exc:
        raise ValueError("Configured and maximum feature lengths must be integers.") from exc
    if feature_length < 0 or maximum_length < 0:
        raise ValueError("Feature lengths cannot be negative.")
    if maximum_length > feature_length and feature_length == 2:
        feature_length = maximum_length
    if not is_fabric and feature_length > 2 and length5_features:
        feature_length = 5
    return feature_length



def sum_legacy_increment_entries(
    increment_entries: Iterable[str],
    parent_item_short: str,
) -> float:
    """Sum stage-16 increment rows matching the normalized parent token.

    ExportThread searches each increment string for parent_item_short plus a
    pipe, then adds the numeric remainder after replacing that token. The
    caller must perform legacy parent-token normalization first.
    """
    token = str(parent_item_short or "")
    if not token:
        raise ValueError("A non-empty legacy parent-item token is required.")
    total = 0.0
    marker = token + "|"
    for entry in increment_entries:
        value = str(entry)
        if marker not in value:
            continue
        remainder = value.replace(marker, "")
        try:
            total += float(remainder)
        except ValueError as exc:
            raise ValueError(
                f"Invalid legacy increment amount for parent {token!r}: {remainder!r}"
            ) from exc
    return total
