"""Dialog for choosing the owner Metatype when owner resolution is not unique.

Candidates and their evidence are listed; **nothing is pre-selected**, the OK button stays disabled until the user
picks one and the choice validates (``validate_owner_choice``). Cancelling changes nothing: the dialog holds no state
of the articles work table, so pending edits are untouched.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QLabel, QListWidget, QListWidgetItem, QPlainTextEdit, QVBoxLayout, QWidget,
)

from services.metatype.owner_selection import OwnerChoice, OwnerState, validate_owner_choice

_TITLES = {
    OwnerState.UNIQUE: "Unique owner Metatype",
    OwnerState.MULTIPLE: "Several candidate Metatypes - choose one",
    OwnerState.NONE: "No valid candidate Metatype",
}


class OwnerSelectionDialog(QDialog):
    def __init__(self, choice: OwnerChoice, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.choice = choice
        self.setObjectName("metatypeOwnerDialog")
        self.setWindowTitle("Owner Metatype")
        layout = QVBoxLayout(self)
        self.state_label = QLabel(_TITLES[choice.state], self)
        self.state_label.setObjectName("metatypeOwnerState")
        self.reason_label = QLabel(choice.explanation, self)
        self.reason_label.setWordWrap(True)
        self.candidates = QListWidget(self)
        self.candidates.setObjectName("metatypeOwnerCandidates")
        for candidate in choice.candidates:
            item = QListWidgetItem(f"{candidate.metatype_id} - {candidate.evidence()}")
            item.setData(0x0100, candidate.metatype_id)      # Qt.UserRole
            self.candidates.addItem(item)
        self.candidates.setCurrentRow(-1)                    # never pre-select
        self.candidates.clearSelection()
        self.feedback = QPlainTextEdit(self)
        self.feedback.setObjectName("metatypeOwnerFeedback")
        self.feedback.setReadOnly(True)
        self.feedback.setMaximumHeight(90)
        self.buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        for widget in (self.state_label, self.reason_label, self.candidates, self.feedback, self.buttons):
            layout.addWidget(widget)
        self.candidates.itemSelectionChanged.connect(self._changed)
        self._changed()

    @property
    def selected_id(self) -> str | None:
        items = self.candidates.selectedItems()
        return items[0].data(0x0100) if items else None

    def select_candidate(self, metatype_id: str) -> bool:
        for row in range(self.candidates.count()):
            if self.candidates.item(row).data(0x0100) == metatype_id:
                self.candidates.setCurrentRow(row)
                return True
        return False

    def _changed(self) -> None:
        chosen = self.selected_id
        if self.choice.state is OwnerState.NONE:
            self.feedback.setPlainText("No Metatype can be chosen. Add existing articles of the target Metatype "
                                       "to the Step 4 list, or decide the owner outside this tool.")
            ok = False
        elif chosen is None:
            self.feedback.setPlainText("Select the Metatype that should own the property.")
            ok = False
        else:
            issues = validate_owner_choice(self.choice, chosen)
            self.feedback.setPlainText("\n".join(f"{i.severity.upper()} [{i.code}] {i.message}" for i in issues)
                                       or "The selection is valid.")
            ok = not any(i.severity == "error" for i in issues)
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(ok)
