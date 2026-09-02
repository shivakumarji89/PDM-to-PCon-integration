"""TextBlock domain model.

An OCD ``tCOMd_Text`` row: a named text block (the ``com_TextName`` key) with
its per-language strings, categorised by ``type_code`` (``com_TextTypeCode``).
Fields only - no logic.
"""
from __future__ import annotations

from dataclasses import dataclass

#: Known OCD text-type codes (``tCOMd_Text.com_TextTypeCode``), in display order.
TEXT_TYPE_CODES: tuple[str, ...] = (
    "artshort",
    "artlong",
    "property",
    "propvalue",
    "option",
    "optionvalue",
    "propclass",
    "prophint",
    "price",
)


@dataclass
class TextBlock:
    """One localized text block. Mirrors an OCD ``tCOMd_Text`` row."""

    name: str = ""
    type_code: str = ""
    de: str = ""
    en: str = ""
    fr: str = ""
    nl: str = ""
