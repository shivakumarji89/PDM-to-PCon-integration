"""PriceList domain model.

One named OCD price list (``tCOMd_PriceList``): an id, a display label, a
currency, and a validity window (``YYYYMMDD``). Multiple lists chain by date so
adding a new list closes the previous one's window (roll-over). Fields only - no
logic.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PriceList:
    """One named price list with its currency and validity window."""

    #: xocd ``PriceList`` id, e.g. ``euro_2026``.
    id: str = ""
    #: Display label (defaults to the id).
    label: str = ""
    #: ISO currency code, e.g. ``EUR`` / ``GBP``.
    currency: str = ""
    #: Start of validity (``YYYYMMDD``).
    date_from: str = ""
    #: End of validity (``YYYYMMDD``); set by roll-over, latest list = ``99991231``.
    date_to: str = ""
