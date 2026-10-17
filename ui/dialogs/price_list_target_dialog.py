"""Review and rename the target price lists before a Pricing export.

One editable name per currency, prefilled from the computation year and the
MDB's existing naming. Every edit is validated live against the MDB's lists and
the computation date; OK is only enabled when every currency resolves to a list
that will be reused or created.
"""
from __future__ import annotations

from typing import Any, Sequence

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from services.price_list_targets import ListTargetPlan, resolve_targets


def describe_plan(plan: ListTargetPlan) -> str:
    """One-line status shown next to a name (also used by tests)."""
    if plan.errors:
        return "BLOCKED: " + " ".join(plan.errors)
    window = f"{_day(plan.date_from)} to {_day(plan.date_to)}"
    if plan.action == "reuse":
        text = f"Reuse existing list id {plan.list_id}, valid {window}"
        text += ", region-linked" if plan.linked else ", NOT region-linked"
    else:
        text = f"Create new {plan.currency} list, valid {window}"
    if plan.warnings:
        text += "\n" + "\n".join(plan.warnings)
    return text


def _day(value: str) -> str:
    return f"{value[:4]}-{value[4:6]}-{value[6:8]}" if len(value) == 8 else value


class PriceListTargetDialog(QDialog):
    """Choose an existing MDB price list or explicitly create a new one per currency."""

    _CREATE_NEW = "＋ Create new price list…"

    def __init__(self, currencies: Sequence[str], names: dict[str, str],
                 existing_lists: Sequence[dict[str, Any]], linked_ids: set[str],
                 comp_date: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Target price lists")
        self.resize(820, 380)
        self._lists, self._linked, self._comp = list(existing_lists), set(linked_ids), comp_date
        self._currencies = list(currencies)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"Prices computed for {_day(comp_date) if comp_date else 'an unknown date'}. "
            "Select one existing list per currency, or choose Create new price list. "
            "New lists are created only after you approve the export preview. Existing lists are never changed or deleted.",
            self))
        grid = QGridLayout()
        layout.addLayout(grid)
        self.selectors: dict[str, QComboBox] = {}
        self.edits: dict[str, QLineEdit] = {}
        self.status: dict[str, QLabel] = {}
        for row, ccy in enumerate(self._currencies):
            grid.addWidget(QLabel(f"{ccy} price list:", self), row, 0)
            selector = QComboBox(self)
            selector.addItem(self._CREATE_NEW, userData=None)
            currency_lists = sorted(
                (item for item in self._lists
                 if str(item.get("sys_ISOCurrencyCode") or "").strip().upper() == ccy),
                key=lambda item: (str(item.get("com_PriceListLabel") or "").casefold(),
                                  str(item.get("com_PriceListID") or "")),
            )
            for item in currency_lists:
                label = str(item.get("com_PriceListLabel") or "").strip()
                pid = item.get("com_PriceListID")
                linked = " · region-linked" if str(pid) in self._linked else ""
                selector.addItem(f"{label} (ID {pid}){linked}", userData=label)
            grid.addWidget(selector, row, 1)
            edit = QLineEdit(names.get(ccy, ""), self)
            edit.setPlaceholderText(f"{'EURO' if ccy == 'EUR' else ccy}_YYYY")
            edit.setVisible(True)
            grid.addWidget(edit, row, 2)
            label = QLabel("", self)
            label.setWordWrap(True)
            grid.addWidget(label, row + len(self._currencies), 0, 1, 3)
            self.selectors[ccy], self.edits[ccy], self.status[ccy] = selector, edit, label

            # Default to an existing list only when the proposed name resolves to it.
            target_key = str(names.get(ccy, "")).strip().casefold()
            match_index = next(
                (i for i in range(1, selector.count())
                 if str(selector.itemData(i) or "").strip().casefold() == target_key),
                0,
            )
            selector.setCurrentIndex(match_index)
            selector.currentIndexChanged.connect(lambda _index, currency=ccy: self._selection_changed(currency))
            edit.textEdited.connect(lambda _text, currency=ccy: self._name_edited(currency))
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self.plans: dict[str, ListTargetPlan] = {}
        for ccy in self._currencies:
            self._selection_changed(ccy)
        self._revalidate()

    def names(self) -> dict[str, str]:
        result: dict[str, str] = {}
        for ccy in self._currencies:
            selector = self.selectors[ccy]
            selected = selector.currentData()
            result[ccy] = str(selected if selected is not None else self.edits[ccy].text()).strip()
        return result

    def _selection_changed(self, ccy: str) -> None:
        creating = self.selectors[ccy].currentData() is None
        self.edits[ccy].setEnabled(creating)
        self.edits[ccy].setVisible(creating)
        self._revalidate()

    def _name_edited(self, ccy: str) -> None:
        # Editing a proposed name is an explicit request to create/reuse by name,
        # not to keep routing to the previously selected list.
        selector = self.selectors[ccy]
        if selector.currentData() is not None:
            selector.setCurrentIndex(0)
        self._revalidate()

    def _revalidate(self) -> None:
        self.plans = resolve_targets(self.names(), self._lists, self._linked, self._comp)
        for ccy, plan in self.plans.items():
            self.status[ccy].setText(describe_plan(plan))
        ok = bool(self.plans) and all(p.ok for p in self.plans.values())
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ok)
