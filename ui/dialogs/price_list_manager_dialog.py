"""Interactive price-list planning dialog.

The dialog separates proposal from application: the service detects the required
price-list change, the user reviews the generated name/date rollover, and only
then are the snapshot lists mutated.
"""
from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QDateEdit,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from services.price_list_service import PriceListProposal


class PriceListManagerDialog(QDialog):
    """Review and apply generated price-list changes."""

    def __init__(
        self,
        context,
        snapshot,
        *,
        mode: str,
        currencies: list[str],
        effective_date: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._context = context
        self._snapshot = snapshot
        self._mode = mode
        self._service = context.price_list_service
        self._proposals: list[PriceListProposal] = []
        self._applied = False

        title = "Create Price Lists" if mode == "new_creation" else "Prepare Price Update"
        self.setWindowTitle(title)
        self.setMinimumSize(760, 460)

        layout = QVBoxLayout(self)
        description = (
            "New creation: prepare the first price list for the selected currency."
            if mode == "new_creation"
            else "Maintenance: prepare the next price list and close the previous open list."
        )
        layout.addWidget(QLabel(description, self))

        date_row = QHBoxLayout()
        date_row.addWidget(QLabel("Effective date:", self))
        self._date = QDateEdit(self)
        self._date.setDisplayFormat("dd-MMM-yyyy")
        self._date.setCalendarPopup(True)
        parsed = QDate.fromString(effective_date[:8], "yyyyMMdd")
        self._date.setDate(parsed if parsed.isValid() else QDate.currentDate())
        self._date.dateChanged.connect(lambda _date: self._refresh_proposals(currencies))
        date_row.addWidget(self._date)
        date_row.addStretch(1)
        layout.addLayout(date_row)

        self._table = QTableWidget(0, 7, self)
        self._table.setHorizontalHeaderLabels([
            "Currency", "Price List", "Valid From", "Valid To",
            "Previous List", "Previous Valid To", "Status",
        ])
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._table, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self._apply_button = buttons.addButton(
            "Apply Changes", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self._apply_button.clicked.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._currencies = list(currencies)
        self._refresh_proposals(self._currencies)

    @property
    def applied(self) -> bool:
        return self._applied

    def _refresh_proposals(self, currencies: list[str]) -> None:
        start = self._date.date().toString("yyyyMMdd")
        self._proposals = self._service.propose(
            self._snapshot,
            currencies,
            start,
            mode=self._mode,
        )
        self._table.setRowCount(0)
        has_conflict = False
        for proposal in self._proposals:
            row = self._table.rowCount()
            self._table.insertRow(row)
            previous_to = proposal.previous_date_to or "-"
            previous_id = proposal.previous_id or "-"
            status = proposal.conflict or "Ready"
            if proposal.conflict:
                has_conflict = True
            values = [
                proposal.currency,
                proposal.list_id,
                proposal.date_from,
                "99991231",
                previous_id,
                previous_to,
                status,
            ]
            for column, value in enumerate(values):
                self._table.setItem(row, column, QTableWidgetItem(value))
        self._apply_button.setEnabled(bool(self._proposals) and not has_conflict)

    def _apply(self) -> None:
        if not self._service.apply_proposals(self._snapshot, self._proposals):
            QMessageBox.warning(
                self,
                "Price Lists",
                "The proposed price-list changes could not be applied. "
                "Review the conflicts and try again.",
            )
            return
        self._context.snapshot_manager.mark_modified()
        self._applied = True
        self.accept()
