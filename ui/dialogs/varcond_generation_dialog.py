"""PDM-style VARCOND relation browser and generator.

Legacy PDM builds a list of unique PA_<article-prefix> relations. Selecting a
relation generates one body from every parent article whose code starts with
that prefix. Relation Prefix Length controls the relation name/grouping; it
does not rewrite component target codes inside the VARCOND rules.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, Qt,
    QListWidgetItem, QMessageBox, QPushButton, QPlainTextEdit,
    QFileDialog, QVBoxLayout, QWidget, QSpinBox,
)

from services.varcond_service import VarCondService


class VarCondGenerationDialog(QDialog):
    """PDM-style relation list on the left and selected relation body on right."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._context = context
        self._snapshot = context.active_snapshot
        self.setWindowTitle("Generate VARCOND Relations")
        self.resize(1180, 760)

        root = QVBoxLayout(self)
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Relation / Article Filter:"))
        self._filter = QLineEdit(self)
        self._filter.setPlaceholderText("Filter article codes (starts with)")
        self._filter.textChanged.connect(self._refresh_relations)
        filter_row.addWidget(self._filter, 1)
        self._relation_length = QSpinBox(self)
        self._relation_length.setRange(1, 30)
        self._relation_length.setPrefix("Relation Prefix Length: ")
        self._relation_length.setToolTip(
            "Unique relation names are built from the first N characters of each "
            "parent article. Articles sharing that prefix are generated together."
        )
        self._relation_length.valueChanged.connect(self._refresh_relations)
        filter_row.addWidget(self._relation_length)
        root.addLayout(filter_row)

        split = QHBoxLayout()
        left = QVBoxLayout()
        self._relations = QListWidget(self)
        self._relations.setMinimumWidth(300)
        self._relations.currentItemChanged.connect(self._on_relation_changed)
        left.addWidget(self._relations, 1)
        self._relation_count = QLabel("", self)
        left.addWidget(self._relation_count)
        split.addLayout(left, 1)

        right = QVBoxLayout()
        options = QHBoxLayout()
        self._prefix = QLineEdit(self)
        self._prefix.setPlaceholderText("Optional property-class prefix")
        self._exclusions = QLineEdit(self)
        self._exclusions.setPlaceholderText("Property exclusions")
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
        self._summary = QLabel("Select a relation to preview its generated body.", self)
        right.addWidget(self._summary)
        self._output = QPlainTextEdit(self)
        self._output.setReadOnly(True)
        self._output.setPlaceholderText("Selected PA_<prefix> relation body.")
        right.addWidget(self._output, 1)
        split.addLayout(right, 4)
        root.addLayout(split, 1)

        buttons = QHBoxLayout()
        generate = QPushButton("Generate / Refresh", self)
        generate.clicked.connect(self._generate_selected)
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
        articles = self._snapshot.articles if self._snapshot else []
        code_by_id = {
            str(article.id): (article.code or "")
            for article in articles if article.id is not None
        }
        article_by_id = {
            str(article.id): article for article in articles if article.id is not None
        }
        for article_id in (self._snapshot.article_components or {} if self._snapshot else {}):
            code = code_by_id.get(str(article_id), "")
            if not code:
                continue
            article = article_by_id.get(str(article_id))
            label = code + (f" — {article.name}" if article and article.name else "")
            self._article_rows.append((code, label, str(article_id)))
        self._article_rows.sort(key=lambda row: row[0].casefold())

        max_length = max((len(row[0]) for row in self._article_rows), default=1)
        self._relation_length.setRange(1, max_length)
        self._relation_length.setValue(max_length)
        self._refresh_relations()
        self._summary.setText(
            f"{len(self._article_rows)} parent articles with BOM loaded. "
            "Select a PA_<prefix> relation to preview its rules."
        )

    def _refresh_relations(self, *_args) -> None:
        """Mirror PDM updateItemList: unique PA_<prefix> entries from filtered items."""
        current = self._relations.currentItem().text() if self._relations.currentItem() else ""
        needle = self._filter.text().strip().casefold()
        length = self._relation_length.value()
        relation_names: set[str] = set()
        for code, _label, _article_id in self._article_rows:
            if needle and not code.casefold().startswith(needle):
                continue
            relation_names.add("PA_" + (code[:length] if len(code) > length else code)

            )
        self._relations.blockSignals(True)
        self._relations.clear()
        for name in sorted(relation_names, key=str.casefold):
            self._relations.addItem(QListWidgetItem(name))
        match = self._relations.findItems(current, Qt.MatchFlag.MatchExactly) if current else []
        if match:
            self._relations.setCurrentItem(match[0])
        elif self._relations.count():
            self._relations.setCurrentRow(0)
        self._relations.blockSignals(False)
        self._relation_count.setText(f"{self._relations.count()} Price Relation(s)")
        self._generate_selected()

    def _on_relation_changed(self, current, _previous) -> None:
        if current is not None:
            self._generate_selected()
        else:
            self._output.clear()
            self._summary.setText("No relation selected.")

    def _generate_selected(self) -> None:
        item = self._relations.currentItem()
        if item is None:
            self._output.clear()
            self._summary.setText("No matching relations.")
            return
        relation_name = item.text()
        relation_prefix = relation_name[3:] if relation_name.startswith("PA_") else relation_name
        parent_codes = [
            code for code, _label, _article_id in self._article_rows
            if code.startswith(relation_prefix)
        ]
        if not parent_codes:
            self._output.clear()
            self._summary.setText(f"{relation_name}: no matching parent articles.")
            return

        service = VarCondService(self._context)
        result = service.generate(
            prefix=self._prefix.text(),
            property_exclusions=self._exclusions.text(),
            property_substitutions=self._substitutions.text(),
            legacy_exact=True,
            article_codes=parent_codes,
        )
        self._output.setPlainText(result.text or "(nothing generated)")
        self._summary.setText(
            f"{relation_name} | {len(parent_codes)} parent article(s) | "
            f"{len(result.rules)} definitions | {len(result.text)} characters"
            + (f" | {len(result.warnings)} warning(s)" if result.warnings else "")
        )
        self._summary.setToolTip("\n".join(result.warnings))

    def _copy(self) -> None:
        from PySide6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._output.toPlainText())

    def _save(self) -> None:
        item = self._relations.currentItem()
        default_name = (item.text() if item else "varcond") + ".txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save VARCOND relation", default_name, "Text files (*.txt)"
        )
        if path:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(self._output.toPlainText())
