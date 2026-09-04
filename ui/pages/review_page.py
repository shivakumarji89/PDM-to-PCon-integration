"""Review workspace for repository ↔ PDM source discovery.

This page is intentionally evidence-only. It helps compare an existing
repository series with PDM candidates before any semantic mapping is
standardized.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.pages.base_page import BasePage


class ReviewPage(BasePage):
    """Source discovery workspace for repository and PDM comparison."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Review",
            description=(
                "Compare repository evidence with PDM candidates before "
                "standardizing source mappings."
            ),
            parent=parent,
            show_placeholder=False,
        )
        self._context = context

        self.add_content(self._build_toolbar())
        self.add_content(self._build_source_comparison_group())
        self.refresh()

    def _build_toolbar(self) -> QWidget:
        box = QGroupBox("Review Actions", self)
        layout = QHBoxLayout(box)
        self._refresh_btn = QPushButton("Refresh", box)
        self._refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(self._refresh_btn)
        layout.addStretch(1)
        return box

    def _build_source_comparison_group(self) -> QWidget:
        """Show evidence without asserting repository/PDM equivalence."""
        box = QGroupBox("Repository ↔ PDM Discovery", self)
        layout = QVBoxLayout(box)

        self._source_status = QLabel(
            "No repository series selected. Open a repository series from Product.",
            box,
        )
        self._source_status.setWordWrap(True)
        layout.addWidget(self._source_status)

        repository_box = QGroupBox("Repository Evidence", box)
        form = QFormLayout(repository_box)
        self._source_rows = {}
        for key, label in (
            ("name", "Name"),
            ("code", "Code"),
            ("category", "Category"),
            ("catalogue", "Catalogue"),
        ):
            value = QLabel("-", repository_box)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self._source_rows[key] = value
            form.addRow(f"{label}:", value)
        layout.addWidget(repository_box)

        candidates_box = QGroupBox(
            "PDM Candidates (discovery only — not standardized mappings)", box
        )
        candidates_layout = QVBoxLayout(candidates_box)
        self._pdm_candidates = QListWidget(candidates_box)
        self._pdm_candidates.setMinimumHeight(180)
        candidates_layout.addWidget(self._pdm_candidates)
        layout.addWidget(candidates_box)

        return box

    def _refresh_source_comparison(self) -> None:
        context = self._context.repository_context_service.active_context
        if context is None:
            self._source_status.setText(
                "No repository series selected. Open a repository series from Product."
            )
            for widget in self._source_rows.values():
                widget.setText("-")
            self._pdm_candidates.clear()
            self._pdm_candidates.addItem("No PDM discovery data available.")
            return

        self._source_status.setText(
            f"Repository: {context.repository_path}\n"
            f"PDM discovery status: {context.pdm_match_status.replace('_', ' ')}"
        )

        for key, widget in self._source_rows.items():
            record = context.records.get(key)
            widget.setText(
                str(record.value if record and record.value not in (None, "") else "-")
            )

        self._pdm_candidates.clear()
        if context.candidate_products:
            for index, product in enumerate(context.candidate_products, start=1):
                self._pdm_candidates.addItem(
                    f"{index}. {product['name'] or '-'}"
                    f" | Code: {product['code'] or '-'}"
                    f" | Category: {product['category'] or '-'}"
                    f" | Catalogue: {product['catalogue'] or '-'}"
                )
        else:
            self._pdm_candidates.addItem("No PDM candidates found.")

    def refresh(self) -> None:
        self._refresh_source_comparison()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self.refresh()

    def is_ready(self) -> bool:
        # Review is investigative; it must not block the workflow.
        return True
