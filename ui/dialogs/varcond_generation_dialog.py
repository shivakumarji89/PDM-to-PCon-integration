"""PDM-style VARCOND relation browser and generator.

Legacy PDM builds a list of unique PA_<article-prefix> relations. Selecting a
relation generates one body from every parent article whose code starts with
that prefix. Relation Prefix Length controls the relation name/grouping; it
does not rewrite component target codes inside the VARCOND rules.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QPlainTextEdit, QFileDialog,
    QVBoxLayout, QWidget, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
)

from services.varcond_service import VarCondService
from ui.workers.background_task import BackgroundTask


class VarCondGenerationPanel(QWidget):
    """PDM-style relation list on the left and selected relation body on right."""

    def __init__(
        self, context, parent: QWidget | None = None,
        maintenance_check: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(parent)
        self._context = context
        self._snapshot = context.active_snapshot
        # Maintenance only: generate from the cached legacy-source service.
        # Development (check absent/False) keeps VarCondService.generate_live.
        self._maintenance_check = maintenance_check or (lambda: False)
        self._maintenance_service = None
        self._maintenance_snapshot = None
        self._maintenance_load_task = None
        self._maintenance_pending_refresh = False
        self.setObjectName("varcondGenerationPanel")

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
        self._exclusions.setPlaceholderText("Selected exclusions (managed by button)")
        self._exclusions.setReadOnly(True)
        self._substitutions = QLineEdit(self)
        self._substitutions.setPlaceholderText("Substitutions (managed by button)")
        self._substitutions.setReadOnly(True)
        column = QVBoxLayout()
        column.addWidget(QLabel("Prefix"))
        column.addWidget(self._prefix)
        options.addLayout(column, 1)
        self._exclusion_button = QPushButton("Exclusion…", self)
        self._exclusion_button.clicked.connect(self._edit_exclusions)
        options.addWidget(self._exclusion_button)
        self._substitution_button = QPushButton("Substitution…", self)
        self._substitution_button.clicked.connect(self._edit_substitutions)
        options.addWidget(self._substitution_button)
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
        generate.clicked.connect(self._on_generate_clicked)
        buttons.addWidget(generate)
        copy_btn = QPushButton("Copy", self)
        copy_btn.clicked.connect(self._copy)
        buttons.addWidget(copy_btn)
        save_btn = QPushButton("Save...", self)
        save_btn.clicked.connect(self._save)
        buttons.addWidget(save_btn)
        buttons.addStretch(1)
        root.addLayout(buttons)

        self._article_rows: list[tuple[str, str, str]] = []
        self._selected_exclusions: set[str] = set()
        self._property_substitutions: dict[str, str] = {}
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

    def refresh_from_snapshot(self) -> None:
        """Refresh the article-code scope after a product snapshot is loaded."""
        self._snapshot = self._context.active_snapshot
        if (
            self._maintenance_service is not None
            and self._snapshot is not self._maintenance_snapshot
        ):
            # A different product/snapshot: cached PDM rows no longer apply.
            self._maintenance_service.clear_cache()
            self._maintenance_snapshot = self._snapshot
        self._article_rows = []
        snapshot = self._snapshot
        if snapshot is not None:
            code_by_id = {
                str(article.id): (article.code or "")
                for article in snapshot.articles if article.id is not None
            }
            article_by_id = {
                str(article.id): article for article in snapshot.articles if article.id is not None
            }
            for article_id in (snapshot.article_components or {}):
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
            f"{len(self._article_rows)} parent articles available. "
            "VARCOND rules are fetched from live PDM when generated."
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
            relation_prefix = code[:length] if len(code) > length else code
            relation_names.add("PA_" + relation_prefix)
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

    def _on_generate_clicked(self) -> None:
        """Explicit Generate / Refresh: re-read PDM (Maintenance path only)."""
        self._generate_selected(refresh=True)

    def _ensure_maintenance_service(self):
        from services.maintenance_varcond_service import MaintenanceVarCondService

        if self._maintenance_service is None:
            self._maintenance_service = MaintenanceVarCondService(self._context)
            self._maintenance_snapshot = self._snapshot
        return self._maintenance_service

    def _load_maintenance_sources_async(self, parent_codes: list[str], refresh: bool) -> None:
        """Load missing/refresh PDM source rows off the UI thread.

        The service cache is only touched by this worker while a load is active;
        after completion, generation and all setting changes are local.
        """
        if self._maintenance_load_task is not None:
            self._maintenance_pending_refresh = self._maintenance_pending_refresh or refresh
            return
        service = self._ensure_maintenance_service()
        self._maintenance_pending_refresh = False
        self._summary.setText("Loading relation data from PDM in the background...")
        self._output.setPlainText("Loading relation data from PDM...")
        self._relations.setEnabled(False)
        self._filter.setEnabled(False)
        self._relation_length.setEnabled(False)
        self._prefix.setEnabled(False)
        self._exclusion_button.setEnabled(False)
        self._substitution_button.setEnabled(False)
        task = BackgroundTask(
            lambda _progress: service.sources_for(parent_codes, refresh=refresh)
        )
        self._maintenance_load_task = task
        task.signals.finished.connect(self._on_maintenance_sources_loaded)
        task.signals.failed.connect(self._on_maintenance_sources_failed)
        task.signals.cancelled.connect(self._on_maintenance_sources_cancelled)
        from PySide6.QtCore import QThreadPool
        QThreadPool.globalInstance().start(task)

    def _finish_maintenance_load(self) -> None:
        self._maintenance_load_task = None
        self._relations.setEnabled(True)
        self._filter.setEnabled(True)
        self._relation_length.setEnabled(True)
        self._prefix.setEnabled(True)
        self._exclusion_button.setEnabled(True)
        self._substitution_button.setEnabled(True)

    def _on_maintenance_sources_loaded(self, _sources) -> None:
        self._finish_maintenance_load()
        refresh = self._maintenance_pending_refresh
        self._maintenance_pending_refresh = False
        # Read the current selection and current transformation controls, not
        # stale values captured when the worker started.
        self._generate_selected(refresh=refresh)

    def _on_maintenance_sources_failed(self, message: str) -> None:
        self._finish_maintenance_load()
        self._summary.setText(f"Could not load relation data from PDM: {message}")
        self._output.setPlainText("PDM relation loading failed. Use Generate / Refresh to retry.")

    def _on_maintenance_sources_cancelled(self, message: str) -> None:
        self._finish_maintenance_load()
        self._summary.setText(f"PDM relation loading cancelled: {message}")

    def _generate_selected(self, refresh: bool = False) -> None:
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
        self._current_parent_codes = parent_codes
        if not parent_codes:
            self._output.clear()
            self._summary.setText(f"{relation_name}: no matching parent articles.")
            return

        if self._maintenance_check():
            service = self._ensure_maintenance_service()
            # Avoid blocking the GUI during initial PDM reads or explicit refresh.
            # Once loaded, transformations are generated synchronously from cache.
            if refresh or any(code not in service._cache for code in parent_codes):
                self._load_maintenance_sources_async(parent_codes, refresh)
                return
            result = service.generate(
                parent_codes,
                prefix=self._prefix.text(),
                property_exclusions=self._exclusions.text(),
                property_substitutions=self._substitutions.text(),
            )
        else:
            service = VarCondService(self._context)
            result = service.generate_live(
                article_codes=parent_codes,
                prefix=self._prefix.text(),
                property_exclusions=self._exclusions.text(),
                property_substitutions=self._substitutions.text(),
            )
        self._output.setPlainText(result.text or "(nothing generated)")
        self._summary.setText(
            f"{relation_name} | {len(parent_codes)} parent article(s) | "
            f"{len(result.rules)} definitions | {len(result.text)} characters"
            + (f" | {len(result.warnings)} warning(s)" if result.warnings else "")
        )
        self._summary.setToolTip("\n".join(result.warnings))


    def _extract_relation_properties(self, parent_codes: list[str]) -> list[str]:
        """Single shared extractor for the selected relation's normalized properties."""
        if not self._snapshot:
            return []
        service = VarCondService(self._context)
        id_by_code: dict[str, str] = {}
        for article in self._snapshot.articles:
            if article.id is not None:
                id_by_code.setdefault(article.code or "", str(article.id))
        terms_by_article = self._snapshot.article_varcond_terms or {}
        names: set[str] = set()
        for code in parent_codes:
            article_id = id_by_code.get(code)
            if article_id is None:
                continue
            for term in terms_by_article.get(article_id, []):
                hdo = int(term.get("has_dependent_options", 0) or 0)
                if not str(term.get("order_code", "") or "") and hdo == 0:
                    continue
                name = service._pcon_property_name(str(term.get("name", "") or ""), code)
                if name:
                    names.add(name)
        return sorted(names, key=str.casefold)

    def _edit_exclusions(self) -> None:
        properties = self._extract_relation_properties(getattr(self, "_current_parent_codes", []))
        if not properties:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Exclusions", "No properties were found for this relation.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Properties to Exclude")
        dialog.resize(480, 560)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Select the properties that should be excluded:"))
        search = QLineEdit(dialog)
        search.setPlaceholderText("Search properties")
        layout.addWidget(search)
        listing = QListWidget(dialog)
        layout.addWidget(listing, 1)
        rows: dict[str, QListWidgetItem] = {}
        for name in properties:
            row = QListWidgetItem(name)
            row.setFlags(row.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            row.setCheckState(Qt.CheckState.Checked if name in self._selected_exclusions else Qt.CheckState.Unchecked)
            listing.addItem(row)
            rows[name] = row
        search.textChanged.connect(lambda value: [
            row.setHidden(bool(value.strip()) and value.casefold() not in row.text().casefold())
            for row in rows.values()
        ])
        actions = QHBoxLayout()
        select_all, clear_all = QPushButton("Select visible", dialog), QPushButton("Clear visible", dialog)
        apply_btn, cancel_btn = QPushButton("Apply", dialog), QPushButton("Cancel", dialog)
        actions.addWidget(select_all); actions.addWidget(clear_all); actions.addStretch(1)
        actions.addWidget(apply_btn); actions.addWidget(cancel_btn); layout.addLayout(actions)
        select_all.clicked.connect(lambda: [row.setCheckState(Qt.CheckState.Checked) for row in rows.values() if not row.isHidden()])
        clear_all.clicked.connect(lambda: [row.setCheckState(Qt.CheckState.Unchecked) for row in rows.values() if not row.isHidden()])
        apply_btn.clicked.connect(dialog.accept); cancel_btn.clicked.connect(dialog.reject)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._selected_exclusions = {name for name, row in rows.items() if row.checkState() == Qt.CheckState.Checked}
            self._exclusions.setText(",".join(sorted(self._selected_exclusions, key=str.casefold)))
            self._generate_selected()

    def _edit_substitutions(self) -> None:
        properties = self._extract_relation_properties(getattr(self, "_current_parent_codes", []))
        if not properties:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Substitutions", "No properties were found for this relation.")
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Substitute Property Names")
        dialog.resize(680, 560)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Enter a replacement beside a property. Leave it blank or unchanged to keep the original name."))
        search = QLineEdit(dialog)
        search.setPlaceholderText("Search properties")
        layout.addWidget(search)
        table = QTableWidget(len(properties), 2, dialog)
        table.setHorizontalHeaderLabels(["Existing property", "Replacement property"])
        table.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed | QAbstractItemView.EditTrigger.AnyKeyPressed)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i, name in enumerate(properties):
            original = QTableWidgetItem(name)
            original.setFlags(original.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(i, 0, original)
            table.setItem(i, 1, QTableWidgetItem(self._property_substitutions.get(name, "")))
        layout.addWidget(table, 1)
        search.textChanged.connect(lambda value: [
            table.setRowHidden(i, bool(value.strip()) and value.casefold() not in properties[i].casefold())
            for i in range(len(properties))
        ])
        actions = QHBoxLayout()
        apply_btn, cancel_btn = QPushButton("Apply", dialog), QPushButton("Cancel", dialog)
        actions.addStretch(1); actions.addWidget(apply_btn); actions.addWidget(cancel_btn); layout.addLayout(actions)
        apply_btn.clicked.connect(dialog.accept); cancel_btn.clicked.connect(dialog.reject)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated: dict[str, str] = {}
            for i, name in enumerate(properties):
                item = table.item(i, 1)
                replacement = item.text().strip() if item else ""
                if replacement and replacement != name:
                    updated[name] = replacement
            self._property_substitutions = updated
            self._substitutions.setText(",".join(
                f"{old}={new}" for old, new in sorted(updated.items(), key=lambda pair: pair[0].casefold())
            ))
            self._generate_selected()

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
