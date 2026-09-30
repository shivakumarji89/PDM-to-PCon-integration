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

from dataclasses import dataclass

from models.price_list import PriceList
from models.snapshot import Snapshot
from services.base_service import BaseService

_DATE_MAX = "99991231"


@dataclass(frozen=True)
class PriceListProposal:
    """A reviewed price-list change that has not been applied yet."""

    mode: str = ""
    currency: str = ""
    list_id: str = ""
    label: str = ""
    date_from: str = ""
    previous_id: str = ""
    previous_date_to: str = ""
    conflict: str = ""


class PriceListService(BaseService):
    """Create, edit and roll over the snapshot's named price lists."""

    def price_lists(self, snapshot: Snapshot | None) -> list[PriceList]:
        """The snapshot's price lists (empty when none/no snapshot)."""
        return list(snapshot.price_lists) if snapshot is not None else []

    @staticmethod
    def generated_name(currency: str, year: str) -> str:
        """Return the canonical generated price-list name for a currency/year."""
        token = "EURO" if (currency or "").strip().upper() == "EUR" else (currency or "").strip().upper()
        return f"{token}_{str(year).strip()}"

    def propose(
        self, snapshot: Snapshot | None, currencies: list[str],
        date_from: str, *, mode: str,
    ) -> list[PriceListProposal]:
        """Prepare price-list changes for explicit user review."""
        if snapshot is None:
            return []
        start = self._norm_date(date_from)
        year = start[:4] if len(start) == 8 else ""
        if not year:
            return []
        normalized: list[str] = []
        for currency in currencies:
            ccy = (currency or "").strip().upper()
            if ccy and ccy not in normalized:
                normalized.append(ccy)
        existing = list(snapshot.price_lists)
        proposals: list[PriceListProposal] = []
        for currency in normalized:
            list_id = self.generated_name(currency, year)
            label = list_id.replace("_", " ")
            conflict = ""
            previous_id = ""
            previous_date_to = ""
            same_start = next((
                (p for p in existing
                 if p.currency.upper() == currency and p.date_from == start),
                None,
            )
            if same_start is not None:
                conflict = f"A {currency} price list already starts on {start}."
            elif any(p.id.upper() == list_id.upper() for p in existing):
                conflict = f"Price list {list_id} already exists."
            if mode == "maintenance":
                prior = [
                    p for p in existing
                    if p.currency.upper() == currency
                    and p.date_from
                    and p.date_from < start
                ]
                if prior:
                    prior = sorted(prior, key=lambda p: p.date_from)
                    previous_id = prior[-1].id
                    previous_date_to = self._day_before(start)
                elif not same_start:
                    conflict = conflict or f"No existing {currency} price list precedes {start}."
            proposals.append(PriceListProposal(
                mode=mode, currency=currency, list_id=list_id, label=label,
                date_from=start, previous_id=previous_id,
                previous_date_to=previous_date_to, conflict=conflict,
            ))
        return proposals

    def apply_proposals(
        self, snapshot: Snapshot | None, proposals: list[PriceListProposal]
    ) -> bool:
        """Apply a reviewed proposal set."""
        if snapshot is None or not proposals or any(p.conflict for p in proposals):
            return False
        for proposal in proposals:
            if self.add_price_list(
                snapshot, proposal.list_id, proposal.label,
                proposal.currency, proposal.date_from,
            ) is None:
                return False
        return True
    def add_price_list(
        self, snapshot: Snapshot | None, list_id: str, label: str,
        currency: str, date_from: str,
    ) -> PriceList | None:
        """Add a list and re-chain validity. Returns it, or None if the id is
        blank or already used."""
        if snapshot is None:
            return None
        pid = (list_id or "").strip().upper()
        if not pid or any(pl.id.upper() == pid for pl in snapshot.price_lists):
            return None
        price_list = PriceList(
            id=pid,
            label=(label or pid).strip().upper() or pid,
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
