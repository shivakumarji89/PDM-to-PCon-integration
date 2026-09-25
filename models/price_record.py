"""PriceRecord domain model.

One OCD price row, mirroring either ``tCOMd_Price`` (article pricing) or
``tCOMd_GlobalPrice`` (super-product / global pricing). The ``value`` is always
computed by SQL Server via ``fnGetListPriceByItem`` / ``fnGetListPrice`` and only
carried here - never recomputed in Python, so it stays byte-identical to PDM.

Records form the persisted price baseline: the diff key
``(is_global, article_code, variant_condition, level, currency)`` -> ``value``
is what a later price run compares against to emit only the changed cells.
Fields only - no logic.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PriceRecord:
    """One OCD price row (``tCOMd_Price`` or ``tCOMd_GlobalPrice``)."""

    #: False -> ``tCOMd_Price``; True -> ``tCOMd_GlobalPrice`` (super product).
    is_global: bool = False
    #: ``com_ArticleCode`` (base article). Empty for a global record.
    article_code: str = ""
    #: ``com_VariantCondition``: "" base, " 9502=OK" upcharge, full item (global).
    variant_condition: str = ""
    #: ``com_PriceLevelCode``: 'B' base, 'X' upcharge. Ignored for global.
    level: str = "B"
    #: ``com_PriceValue`` - computed by SQL Server, carried verbatim.
    value: float = 0.0
    #: ``sys_ISOCurrencyCode`` (e.g. 'GBP', 'EUR').
    currency: str = ""
    valid_from: str = ""
    valid_to: str = ""

    def key(self) -> tuple[bool, str, str, str, str]:
        """Identity for year-over-year diffing (everything but the value)."""
        return (
            self.is_global,
            self.article_code,
            self.variant_condition,
            self.level,
            self.currency,
        )
