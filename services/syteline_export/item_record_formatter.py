"""Source-mapped standard SyteLine item-row formatting.

This ports the ordinary (non-CSI, non-MillerCAD) item-row assembly from
ExportThread.cs. It intentionally accepts already-resolved descriptions,
feature codes, and source values; resolving options/BOM data is a separate
part of the legacy algorithm.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Sequence


@dataclass(frozen=True)
class SyteLineItemRecord:
    long_item: str
    is_superproduct: bool
    description: str
    status: int
    base_price: object = None
    list_price: object = None
    export_base_prices: bool = True
    product_code: str = ""
    price_code: str = ""
    component_cost: object = 0
    volume_litres: object = None
    weight_kilos: object = None
    commodity_code: str = ""
    notes: str = ""
    legacy_item: str = ""
    feature_codes: Sequence[str] = ()
    feature_prefix: str = "BOCFAB"
    height: object = None
    width: object = None
    depth: object = None


def _decimal(value: object) -> Decimal:
    if value is None or str(value).strip() == "":
        return Decimal("0")
    try:
        return Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid numeric value for SyteLine item record: {value!r}") from exc


def _source_number(value: object) -> str:
    """Match the legacy VB Conversions.ToString(double) style for numeric fields."""
    number = float(_decimal(value))
    if number.is_integer():
        return str(int(number))
    return format(number, ".15g")


def format_syteline_item_record(record: SyteLineItemRecord) -> str:
    """Build one standard SyteLine item line, including CRLF, per legacy field order."""
    marker = record.notes if "X" in record.notes else (
        record.legacy_item if "X" in record.legacy_item else ""
    )
    if marker.endswith("-"):
        marker = marker[:-1]
    if marker:
        item_type, brand = "M", "BOC"
    else:
        item_type, brand, marker = "P", "", ""

    if record.status == 1:
        status_code, status_description = "A", ""
    else:
        status_code = "O"
        status_description = {0: "URL", 2: "OBS", 3: "ON HOLD"}.get(record.status, "")

    price = _decimal(record.base_price if record.export_base_prices else record.list_price)
    if price < 0:
        price = Decimal("0")
    # Legacy row uses a separate numeric field before Product_Code.
    fields = [
        record.long_item,
        "yes" if record.is_superproduct else "no",
        record.description.replace(">", " "),
        status_code,
        status_description,
        _source_number(price),
        _source_number(record.component_cost),
        "",
        "",
        record.product_code,
        _source_number(record.volume_litres),
        _source_number(record.weight_kilos),
        "no",
        "35",
        "0",
        "0",
        "",
        "",
        "",
        "",
        "SUP" if record.is_superproduct else "",
        "1",
        "0",
        "EA",
        record.commodity_code,
        item_type,
        "",
        "no",
        marker,
        "",
        "",
        "",
        brand,
        "0",
        "0",
        "",
    ]
    features: list[str] = []
    for raw_feature in record.feature_codes[:20]:
        feature = str(raw_feature).replace(record.feature_prefix + "-", "")
        if "bocfab" not in feature.lower():
            if "-HAR-" in feature:
                feature = feature.split("-HAR-", 1)[1]
            features.append(feature)
        else:
            features.append("")
    fields.extend(features)
    fields.extend([""] * (20 - len(features)))
    fields.extend([str(record.height or ""), str(record.width or ""), str(record.depth or ""), ""])
    return "\t".join(fields) + "\r\n"
