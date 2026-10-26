"""Helpers reproducing the .NET/VB semantics the legacy ExportThread relies on.

The legacy exporter is decompiled C#/VB. Where a decompiled expression has
observable .NET behaviour that Python does not share (``int.Parse``,
``double.Parse``, ``Substring`` bounds, ``DBNull`` to string, ``ArrayList``
lookups), the port calls these helpers so the behaviour is explicit and tested.

Deliberate simplifications (documented deviations):
* ``string.IndexOf(string)`` is culture-sensitive in .NET; ordinal search is used.
* ``double.ToString()`` / ``Parse`` assume the en-US culture used by the legacy host and the
  .NET Framework 15-significant-digit format (the legacy project targets net40).
"""
from __future__ import annotations
from core.cancellation import checkpoint

import math
import re
from decimal import Decimal
from typing import Any, Sequence


class LegacyFormatError(ValueError):
    """Equivalent of System.FormatException raised by int.Parse/double.Parse."""


class LegacyRangeError(IndexError):
    """Equivalent of System.ArgumentOutOfRangeException raised by Substring."""


_INT_RE = re.compile(r"^[ \t\r\n]*[+-]?[0-9]+[ \t\r\n]*$", re.ASCII)
_DOUBLE_RE = re.compile(
    r"^[ \t\r\n]*[+-]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]*)(?:\.[0-9]*)?(?:[eE][+-]?[0-9]+)?[ \t\r\n]*$",
    re.ASCII,
)


def tostr(value: Any) -> str:
    """``obj.ToString()`` for database values: DBNull/None becomes the empty string."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float):
        return double_to_string(value)
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def double_to_string(value: float) -> str:
    """.NET Framework (net40, as in PDMMaintenance.csproj) ``double.ToString()``.

    The "G" default shows at most 15 significant digits and switches to exponent form when the
    decimal exponent is < -4 or >= 15, which is exactly Python's ``.15g`` rule. The exponent is
    written with an upper-case ``E``, an explicit sign and at least two digits (``1E-05``).
    """
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    if value == 0:
        return "-0" if math.copysign(1.0, value) < 0 else "0"
    text = format(value, ".15g")
    if "e" in text:
        mantissa, exponent = text.split("e")
        exp = int(exponent)
        return f"{mantissa}E{'-' if exp < 0 else '+'}{abs(exp):02d}"
    return text


def net_int(value: Any) -> int:
    """``int.Parse(value.ToString())``; raises LegacyFormatError like FormatException."""
    text = tostr(value)
    if not _INT_RE.match(text):
        raise LegacyFormatError(f"Input string was not in a correct format: {text!r}")
    number = int(text.strip())
    if not -2147483648 <= number <= 2147483647:
        raise LegacyFormatError(f"Value was either too large or too small for an Int32: {text!r}")
    return number


def net_double(value: Any) -> float:
    """``double.Parse(value.ToString())`` under en-US number rules."""
    text = tostr(value)
    stripped = text.strip()
    if stripped in {"Infinity", "+Infinity"}:
        return math.inf
    if stripped == "-Infinity":
        return -math.inf
    if stripped == "NaN":
        return math.nan
    if not stripped or not _DOUBLE_RE.match(text) or not re.search(r"[0-9]", stripped):
        raise LegacyFormatError(f"Input string was not in a correct format: {text!r}")
    return float(stripped.replace(",", ""))


def net_bool(value: Any) -> bool:
    """``bool.Parse``: accepts 'True'/'False' case-insensitively with surrounding whitespace."""
    text = tostr(value).strip().lower()
    if text == "true":
        return True
    if text == "false":
        return False
    raise LegacyFormatError(f"String was not recognized as a valid Boolean: {tostr(value)!r}")


def substring(text: str, start: int, length: int | None = None) -> str:
    """C# ``Substring`` with its bounds checks."""
    if start < 0 or start > len(text):
        raise LegacyRangeError(f"startIndex {start} out of range for length {len(text)}")
    if length is None:
        return text[start:]
    if length < 0 or start + length > len(text):
        raise LegacyRangeError(f"length {length} out of range at {start} for length {len(text)}")
    return text[start:start + length]


def index_of(text: str, needle: str) -> int:
    """``string.IndexOf(string)`` (ordinal)."""
    return text.find(needle)


def list_index_of(items: Sequence[Any], value: Any) -> int:
    """``ArrayList.IndexOf``: first equal element or -1 (no bool/int coercion)."""
    value_is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
    for position, item in enumerate(items):
        checkpoint()
        item_is_number = isinstance(item, (int, float)) and not isinstance(item, bool)
        if (item_is_number and value_is_number) or type(item) is type(value):
            if item == value:
                return position
    return -1


def list_contains(items: Sequence[Any], value: Any) -> bool:
    return list_index_of(items, value) > -1


def list_remove(items: list, value: Any) -> None:
    """``ArrayList.Remove``: removes the first equal element if present."""
    position = list_index_of(items, value)
    if position > -1:
        del items[position]


_ALNUM = frozenset("0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")


def remove_non_alphanumeric(data: str) -> str:
    """SytelineExport.removeNonAlphaNumeric (SytelineExport.cs:2284)."""
    return "".join(ch for ch in data if ch in _ALNUM)


_KNOLL_CATALOGUES = frozenset({649, 771, 740, 790, 834, 769})


def is_knoll_catalogue(catalogue_id: int) -> bool:
    """SytelineCSIExport.IsKnollCatalogue (SytelineCSIExport.cs:595)."""
    return catalogue_id in _KNOLL_CATALOGUES


def debug_feature_pos(featpos: str, ref: str) -> str:
    """SytelineExport.debugFeaturePos with every debug flag off (the shipped default)."""
    return featpos


def debug_feature_template(template: str, ref: str) -> str:
    """SytelineExport.debugFeatureTemplate with every debug flag off."""
    return template


def debug_post_processed_feature_pos(featpos: str, ref: str) -> str:
    """SytelineExport.debugPostProcessedFeaturePos with every debug flag off."""
    return featpos
