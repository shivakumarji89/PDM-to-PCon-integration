"""Article-filtered VARCOND generation dialog.

This first-pass UI mirrors the basic legacy PDM workflow: filter the available
super-product articles, select one or more parents, and generate their relation
text in the selected order. Advanced legacy export controls can be added later.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QPlainTextEdit,
    QFileDialog, QVBoxLayout, QWidget, QSpinBox,
)

from services.varcond_service import VarCondService


class VarCondGenerationDialog(QDialog):
    """Filter/select parent articles and generate legacy-shaped VARCOND text."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._context = context
        self._snapshot = context.active_snapshot
        self.setWindowTitle("Generate VARCOND")
        self.resize(1180, 760)

        root = QVBoxLayout(self)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Article filter:"))
        self._filter = QLineEdit(self)
        self._filter.setPlaceholderText("Type part of an article code or name")
        self._filter.textChanged.connect(self._apply_filter)
        filter_row.addWidget(self._filter, 1)
        self._relation_length = QSpinBox(self)
        self._relation_length.setRange(1, 30)
        self._relation_length.setValue(9)
        self._relation_length.setPrefix("Relation prefix length: ")
        self._relation_length.setToolTip(
            "Group selected parent articles by this many leading characters."
        )
        self._relation_length.valueChanged.connect(self._on_selection_changed)
        filter_row.addWidget(self._relation_length)
        root.addLayout(filter_row)

        split = QHBoxLayout()
        self._articles = QListWidget(self)
        self._articles.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self._articles.setMinimumWidth(300)
        self._articles.itemSelectionChanged.connect(self._on_selection_changed)
        split.addWidget(self._articles, 1)

        right = QVBoxLayout()
        options = QHBoxLayout()
        self._prefix = QLineEdit(self)
        self._prefix.setPlaceholderText("Optional property-class prefix")
        self._exclusions = QLineEdit(self)
        self._exclusions.setPlaceholderText("Property exclusions (comma/text)")
        self._substitutions = QLineEdit(self)
        self._substitutions.setPlaceholderText("Old=New substitutions")
        for label, widget in (
            ("Prefix", self._prefix),
            ("Exclusions", self._exclusions),
            ("Substitutions", self._substitutions),
        ):
            column = QVBoxLayout()
            column.addWidget(QLabel(label))
            column.addWidget(widget)
            options.addLayout(column, 1)
        right.addLayout(options)

        self._summary = QLabel("Select articles and click Generate.", self)
        right.addWidget(self._summary)
        self._output = QPlainTextEdit(self)
        self._output.setReadOnly(True)
        self._output.setPlaceholderText("Generated VARCOND relations appear here.")
        right.addWidget(self._output, 1)
        split.addLayout(right, 4)
        root.addLayout(split, 1)

        buttons = QHBoxLayout()
        generate = QPushButton("Generate", self)
        generate.clicked.connect(self._generate)
        buttons.addWidget(generate)
        copy_btn = QPushButton("Copy", self)
        copy_btn.clicked.connect(self._copy)
        buttons.addWidget(copy_btn)
        save_btn = QPushButton("Save...", self)
        save_btn.clicked.connect(self._save)
        buttons.addWidget(save_btn)
        buttons.addStretch(1)
        close_btn = QPushButton("Close", self)
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        root.addLayout(buttons)

        self._article_rows: list[tuple[str, str, str]] = []
        code_by_id = {
            str(article.id): article.code
            for article in (self._snapshot.articles if self._snapshot else [])
            if article.id is not None
        }
        # Only parent articles with a BOM can produce component VARCOND rules.
        for article_id, components in (self._snapshot.article_components or {}).items():
            code = code_by_id.get(str(article_id), "")
            article = next(
                (a for a in self._snapshot.articles
                 if a.id is not None and str(a.id) == str(article_id)),
                None,
            )
            if not code:
                continue
            label = code + (f" — {article.name}" if article and article.name else "")
            self._article_rows.append((code, label, str(article_id)))
        self._article_rows.sort(key=lambda row: row[0].casefold())
        for code, label, _article_id in self._article_rows:
            item = QListWidgetItem(label)
            item.setData(256, code)
            self._articles.addItem(item)
        self._summary.setText(
            f"{len(self._article_rows)} parent articles with BOM loaded. "
            "Filter, select one or more, then Generate."
        )

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().casefold()
        for index in range(self._articles.count()):
            item = self._articles.item(index)
            item.setHidden(needle not in item.text().casefold())

    def _on_selection_changed(self) -> None:
        """Refresh the relation preview as the article selection changes."""
        if any(
            self._articles.item(index).isSelected()
            for index in range(self._articles.count())
        ):
            self._generate()
        else:
            self._output.clear()
            self._summary.setText("Select an article to preview its relations.")

    def _generate(self) -> None:
        selected_codes = [
            self._articles.item(index).data(256)
            for index in range(self._articles.count())
            if self._articles.item(index).isSelected()
        ]
        if not selected_codes:
            QMessageBox.information(
                self, "Generate VARCOND", "Select at least one article from the list."
            )
            return
        length = self._relation_length.value()
        groups: dict[str, list[str]] = {}
        for code in selected_codes:
            group_key = code[:length] if len(code) >= length else code
            groups.setdefault(group_key, []).append(code)

        service = VarCondService(self._context)
        blocks: list[str] = []
        warnings: list[str] = []
        definition_count = 0
        for group_key, codes in groups.items():
            result = service.generate(
                prefix=self._prefix.text(),
                property_exclusions=self._exclusions.text(),
                property_substitutions=self._substitutions.text(),
                legacy_exact=True,
                article_codes=codes,
            )
            definition_count += len(result.rules)
            warnings.extend(result.warnings)
            blocks.append(
                f"* Relation group {group_key} ({len(codes)} article(s))\\r\\n"
                + result.text.rstrip("\\r\\n")
            )
        output = "\\r\\n\\r\\n".join(blocks)
        self._output.setPlainText(output or "(nothing generated)")
        self._summary.setText(
            f"{len(selected_codes)} selected article(s) | {len(groups)} relation group(s) | "
            f"{definition_count} definitions | {len(output)} characters"
            + (f" | {len(warnings)} warning(s)" if warnings else "")
        )
        if warnings:
            self._summary.setToolTip("\\n".join(warnings))

    def _copy(self) -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._output.toPlainText())

    def _save(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save VARCOND output", "varcond.txt", "Text files (*.txt)"
        )
        if path:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(self._output.toPlainText())
