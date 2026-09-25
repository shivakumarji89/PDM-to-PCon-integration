"""Named price lists with date roll-over.

Manages the snapshot's price lists (id, label, currency, validity). Adding,
editing or removing a list re-chains each currency's validity windows so they
never gap or overlap: within a currency the lists sort by start date and each
list's end date becomes the day before the next list's start; the latest list
stays open (``99991231``). Currencies are independent chains (euro_2026 rolls
into euro_2027, not into a GBP list).
"""
from __future__ import annotations

from datetime import datetime, timedelta

from models.price_list import PriceList
from models.snapshot import Snapshot
from services.base_service import BaseService

_DATE_MAX = "99991231"


class PriceListService(BaseService):
    """Create, edit and roll over the snapshot's named price lists."""

    def price_lists(self, snapshot: Snapshot | None) -> list[PriceList]:
        """The snapshot's price lists (empty when none/no snapshot)."""
        return list(snapshot.price_lists) if snapshot is not None else []

    def add_price_list(
        self, snapshot: Snapshot | None, list_id: str, label: str,
        currency: str, date_from: str,
    ) -> PriceList | None:
        """Add a list and re-chain validity. Returns it, or None if the id is
        blank or already used."""
        if snapshot is None:
            return None
        pid = (list_id or "").strip()
        if not pid or any(pl.id == pid for pl in snapshot.price_lists):
            return None
        price_list = PriceList(
            id=pid,
            label=(label or pid).strip() or pid,
            currency=(currency or "").strip().upper(),
            date_from=self._norm_date(date_from),
        )
        snapshot.price_lists.append(price_list)
        self.roll_over(snapshot)
        return price_list

    def remove_price_list(self, snapshot: Snapshot | None, list_id: str) -> bool:
        """Remove a list by id and re-chain validity."""
        if snapshot is None:
            return False
        before = len(snapshot.price_lists)
        snapshot.price_lists = [
            pl for pl in snapshot.price_lists if pl.id != list_id
        ]
        if len(snapshot.price_lists) == before:
            return False
        self.roll_over(snapshot)
        return True

    def set_price_list(
        self, snapshot: Snapshot | None, list_id: str, *,
        label: str | None = None, currency: str | None = None,
        date_from: str | None = None,
    ) -> bool:
        """Edit a list's label/currency/start date and re-chain validity."""
        price_list = next(
            (p for p in (snapshot.price_lists if snapshot else []) if p.id == list_id),
            None,
        )
        if price_list is None:
            return False
        if label is not None:
            price_list.label = label.strip() or price_list.id
        if currency is not None:
            price_list.currency = currency.strip().upper()
        if date_from is not None:
            price_list.date_from = self._norm_date(date_from)
        self.roll_over(snapshot)
        return True

    def roll_over(self, snapshot: Snapshot | None) -> None:
        """Chain each currency's validity windows so they neither gap nor overlap:
        within a currency, sort by start date and set each list's end to the day
        before the next list's start; the latest list stays open (99991231)."""
        if snapshot is None:
            return
        by_currency: dict[str, list[PriceList]] = {}
        for price_list in snapshot.price_lists:
            by_currency.setdefault(price_list.currency, []).append(price_list)
        for lists in by_currency.values():
            ordered = sorted(lists, key=lambda p: p.date_from or "")
            for index, price_list in enumerate(ordered):
                nxt = ordered[index + 1] if index + 1 < len(ordered) else None
                if nxt is not None and nxt.date_from:
                    price_list.date_to = self._day_before(nxt.date_from)
                else:
                    price_list.date_to = _DATE_MAX

    @staticmethod
    def _norm_date(value: str) -> str:
        """Keep the first 8 digits of a date (``YYYYMMDD``)."""
        digits = "".join(ch for ch in str(value or "") if ch.isdigit())
        return digits[:8]

    @staticmethod
    def _day_before(date_yyyymmdd: str) -> str:
        """The day before a ``YYYYMMDD`` date (unchanged if it can't be parsed)."""
        try:
            day = datetime.strptime(date_yyyymmdd[:8], "%Y%m%d") - timedelta(days=1)
            return day.strftime("%Y%m%d")
        except (ValueError, TypeError):
            return date_yyyymmdd
