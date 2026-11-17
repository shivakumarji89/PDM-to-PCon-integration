"""PDM-style VARCOND relation browser and generator.

Legacy PDM builds a list of unique PA_<article-prefix> relations. Every relation is generated from its matching parent articles. Changing the
prefix length regroups the already-loaded source rows and regenerates all output. Relation Prefix Length controls the relation name/grouping; it
does not rewrite component target codes inside the VARCOND rules.
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton,
    QVBoxLayout, QWidget, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
)

from core.progress import ProgressReporter
from services.varcond_service import VarCondService
from ui.dialogs.progress_dialog import ProgressDialog
from ui.workers.background_task import BackgroundTask


class _CopyableVarCondTable(QTableWidget):
    """Read-only result table with spreadsheet-friendly Ctrl+C support."""

    def keyPressEvent(self, event) -> None:
        if event.matches(QKeySequence.StandardKey.Copy):
            ranges = self.selectedRanges()
            if not ranges:
                return
            rows = sorted({r for area in ranges for r in range(area.topRow(), area.bottomRow() + 1)})
            cols = sorted({col for area in ranges for col in range(area.leftColumn(), area.rightColumn() + 1)})
            lines = []
            for row in rows:
                lines.append(chr(9).join(
                    self.item(row, col).text() if self.item(row, col) else ""
                    for col in cols
                ))
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(chr(10).join(lines))
            return
        super().keyPressEvent(event)


class VarCondGenerationPanel(QWidget):
    """PDM relation list on the left and merged relation names on the right."""

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
        self._maintenance_load_snapshot = None
        self._maintenance_reporter = None
        self._maintenance_monitor = None
        self.setObjectName("varcondGenerationPanel")

        root = QVBoxLayout(self)

        # Expose these controls so the page can align them with PDM / MDB.
        self.controls_widget = QWidget(self)
        controls = QHBoxLayout(self.controls_widget)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        controls.addWidget(QLabel("Filter:", self.controls_widget))
        self._filter = QLineEdit(self.controls_widget)
        self._filter.setPlaceholderText("Article code starts with...")
        self._filter.textChanged.connect(self._refresh_relations)
        controls.addWidget(self._filter, 1)
        self._exclusion_button = QPushButton("Exclusion…", self.controls_widget)
        self._exclusion_button.clicked.connect(self._edit_exclusions)
        controls.addWidget(self._exclusion_button)
        self._substitution_button = QPushButton("Substitution…", self.controls_widget)
        self._substitution_button.clicked.connect(self._edit_substitutions)
        controls.addWidget(self._substitution_button)
        self._relation_length = QSpinBox(self.controls_widget)
        self._relation_length.setRange(1, 30)
        self._relation_length.setPrefix("Relation Prefix Length: ")
        self._relation_length.setToolTip(
            "Unique relation names are built from the first N characters of each "
            "parent article. Articles sharing that prefix are generated together."
        )
        self._relation_length.valueChanged.connect(self._refresh_relations)
        controls.addWidget(self._relation_length)

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
        # Hidden fields retain applied dialog values for relation generation.
        self._exclusions = QLineEdit(self)
        self._exclusions.setReadOnly(True)
        self._exclusions.hide()
        self._substitutions = QLineEdit(self)
        self._substitutions.setReadOnly(True)
        self._substitutions.hide()
        self._summary = QLabel("Merged Article VARCOND Relations", self)
        right.addWidget(self._summary)
        self._output = _CopyableVarCondTable(self)
        self._output.setColumnCount(1)
        self._output.setHorizontalHeaderLabels(["VARCOND Rule"])
        self._output.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._output.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self._output.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._output.setAlternatingRowColors(True)
        self._output.verticalHeader().setVisible(False)
        self._output.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        right.addWidget(self._output, 1)
        split.addLayout(right, 4)
        root.addLayout(split, 1)

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
            f"{len(self._article_rows)} parent articles with BOM in the snapshot. "
            "Loading source data for all relations..."
        )
        self._current_parent_codes = [row[0] for row in self._article_rows]
        if self._maintenance_check() and self._current_parent_codes:
            self._load_maintenance_sources_async(self._current_parent_codes, refresh=False)
        else:
            self._generate_all()

    def refresh_from_snapshot(self) -> None:
        """Refresh the article-code scope after a product snapshot is loaded."""
        self._snapshot = self._context.active_snapshot
        if (
            self._maintenance_service is not None
            and self._snapshot is not self._maintenance_snapshot
        ):
            # A different product/snapshot: cached PDM rows no longer apply.
            # If a worker is still loading, its completion handler will discard
            # the result rather than let old-product data repopulate this cache.
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
        self._current_parent_codes = [row[0] for row in self._article_rows]
        self._summary.setText(f"{len(self._article_rows)} parent articles available.")
        if self._maintenance_check() and self._current_parent_codes:
            self._load_maintenance_sources_async(self._current_parent_codes, refresh=False)
        else:
            self._generate_all()

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
        # Do not auto-select the first relation. Opening the workflow should
        # only build the local list; All relation outputs are generated automatically after source loading.
        self._relations.blockSignals(False)
        self._relation_count.setText(f"{self._relations.count()} Price Relation(s)")
        if hasattr(self, "_output") and (
            not self._maintenance_check()
            or (self._maintenance_service is not None and self._maintenance_service.has_sources(
                [row[0] for row in self._article_rows]
            ))
        ):
            self._generate_all()

    def _on_relation_changed(self, current, _previous) -> None:
        if current is None:
            return
        relation = current.text()
        for row in range(self._output.rowCount()):
            item = self._output.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == relation:
                self._output.setCurrentCell(row, 0)
                self._output.scrollToItem(item)
                break

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
        self._maintenance_load_snapshot = self._snapshot
        self._summary.setText(f"Loading source data for {len(parent_codes)} parent articles from PDM...")
        self._output.setRowCount(0)
        reporter = ProgressReporter(self)
        monitor = self._maintenance_progress_monitor()
        monitor.bind(reporter)
        # The service starts the reporter with the exact number of uncached
        # parents, then advances it after each parent has been fully loaded.
        monitor.set_family("Maintenance · PDM source loading")
        monitor.set_step(f"Preparing {len(parent_codes):,} parent article(s)...")
        monitor.show()
        monitor.raise_()
        self._maintenance_reporter = reporter
        self._relations.setEnabled(False)
        self._filter.setEnabled(False)
        self._relation_length.setEnabled(False)
        self._exclusion_button.setEnabled(False)
        self._substitution_button.setEnabled(False)
        stream_prefix_length = self._relation_length.value()
        stream_filter_text = self._filter.text().strip().casefold()
        stream_exclusions = self._exclusions.text()
        stream_substitutions = self._substitutions.text()
        stream_parent_order = {
            row[0]: index for index, row in enumerate(self._article_rows)
        }

        def load_sources(_progress):
            def report_source_progress(completed, total, parent_code):
                if total <= 0:
                    reporter.begin(
                        1, title="Loading Price Relation",
                        subject="All Price Relations",
                    )
                    reporter.advance("No uncached PDM sources to load.")
                    return
                if completed == 0:
                    reporter.begin(
                        total, title="Loading Price Relation",
                        subject="All Price Relations",
                    )
                    reporter.note(f"Reading {total:,} uncached parent article(s)...")
                    return
                detail = f"Loaded {completed:,} / {total:,} parent articles"
                if parent_code:
                    detail += f" · {parent_code}"
                reporter.advance(detail)

            # Stream already-cached parents first (if this is a partial
            # refresh), then stream each newly completed parent from the loader.
            # Rule generation is local because the source cache is populated
            # before source_callback is invoked.
            def publish_parent(source):
                code = source.parent
                if stream_filter_text and not code.casefold().startswith(stream_filter_text):
                    return
                result = service.generate(
                    [code], prefix="",
                    property_exclusions=stream_exclusions,
                    property_substitutions=stream_substitutions,
                )
                relation_name = "PA_" + (code[:stream_prefix_length] if len(code) > stream_prefix_length else code)
                parent_order = stream_parent_order.get(code, len(stream_parent_order))
                _progress({
                    "kind": "rules",
                    "relation": relation_name,
                    "parent": code,
                    "parent_order": parent_order,
                    "rules": [rule.rule for rule in result.rules],
                    "warnings": result.warnings,
                })

            # Publish cached sources not included in the new-load callback.
            cached_codes = [
                code for code in parent_codes
                if not refresh and code in service._cache
            ]
            for code in cached_codes:
                publish_parent(service._cache[code])

            sources = service.sources_for(
                parent_codes, refresh=refresh,
                progress_callback=report_source_progress,
                source_callback=publish_parent,
            )
            return sources

        task = BackgroundTask(
            load_sources, cancellation_token=reporter.cancellation_token
        )
        self._maintenance_load_task = task
        task.signals.progress.connect(self._on_maintenance_source_progress)
        task.signals.finished.connect(self._on_maintenance_sources_loaded)
        task.signals.failed.connect(self._on_maintenance_sources_failed)
        task.signals.cancelled.connect(self._on_maintenance_sources_cancelled)
        from PySide6.QtCore import QThreadPool
        QThreadPool.globalInstance().start(task)

    def _maintenance_progress_monitor(self) -> ProgressDialog:
        monitor = self._maintenance_monitor
        if monitor is None:
            monitor = ProgressDialog(self)
            self._maintenance_monitor = monitor
        return monitor

    def _finish_maintenance_progress(self, success: bool, message: str) -> None:
        reporter = self._maintenance_reporter
        self._maintenance_reporter = None
        if reporter is not None:
            reporter.finish(success, message)
        monitor = self._maintenance_monitor
        if monitor is not None and reporter is not None:
            monitor.unbind_reporter(reporter)

    def _finish_maintenance_load(self) -> None:
        self._maintenance_load_task = None
        self._relations.setEnabled(True)
        self._filter.setEnabled(True)
        self._relation_length.setEnabled(True)
        self._exclusion_button.setEnabled(True)
        self._substitution_button.setEnabled(True)

    def _on_maintenance_source_progress(self, payload) -> None:
        """Append each completed parent's rules on the GUI thread."""
        if not isinstance(payload, dict) or payload.get("kind") != "rules":
            return
        relation_name = str(payload.get("relation", ""))
        parent_code = str(payload.get("parent", ""))
        parent_order = int(payload.get("parent_order", len(self._article_rows)))
        rules = payload.get("rules", [])
        self._output.setUpdatesEnabled(False)
        try:
            for rule_text in rules:
                # Completion is asynchronous, but keep the final table in the
                # original parent-article order rather than worker-finish order.
                row = self._output.rowCount()
                for existing_row in range(self._output.rowCount()):
                    existing = self._output.item(existing_row, 0)
                    existing_order = existing.data(Qt.ItemDataRole.UserRole + 1) if existing else None
                    if existing_order is not None and int(existing_order) > parent_order:
                        row = existing_row
                        break
                self._output.insertRow(row)
                item = QTableWidgetItem(str(rule_text))
                item.setData(Qt.ItemDataRole.UserRole, relation_name)
                item.setData(Qt.ItemDataRole.UserRole + 1, parent_order)
                item.setData(Qt.ItemDataRole.UserRole + 2, parent_code)
                self._output.setItem(row, 0, item)
        finally:
            self._output.setUpdatesEnabled(True)
        if payload.get("warnings"):
            current = self._summary.toolTip()
            new_warnings = "\n".join(str(value) for value in payload["warnings"])
            self._summary.setToolTip("\n".join(value for value in (current, new_warnings) if value))
        self._summary.setText(
            f"Generating VARCOND rules · {self._output.rowCount():,} definitions displayed"
        )

    def _on_maintenance_sources_loaded(self, _sources) -> None:
        loaded_snapshot = self._maintenance_load_snapshot
        self._finish_maintenance_load()
        self._maintenance_load_snapshot = None
        refresh = self._maintenance_pending_refresh
        self._maintenance_pending_refresh = False
        if loaded_snapshot is not self._snapshot:
            # Snapshot changed while PDM was loading. Never render/cache results
            # from the previous product in the newly selected product's panel.
            if self._maintenance_service is not None:
                self._maintenance_service.clear_cache()
            self._maintenance_snapshot = self._snapshot
            self._finish_maintenance_progress(False, "Product changed while loading; stale relation data discarded.")
            self._generate_all()
            return
        # Read the current selection and current transformation controls, not
        # stale values captured when the worker started.
        if refresh:
            self._load_maintenance_sources_async(
                [row[0] for row in self._article_rows], refresh=True
            )
            return
        # Rules were appended as each parent completed. Do not clear and
        # regenerate the entire table at the end.
        self._summary.setText(
            f"{self._relations.count()} relation(s) | "
            f"{self._output.rowCount():,} generated definition(s) | "
            "Select cells and press Ctrl+C to copy"
        )
        self._finish_maintenance_progress(True, "All VARCOND rules ready")

    def _on_maintenance_sources_failed(self, message: str) -> None:
        self._finish_maintenance_load()
        self._maintenance_load_snapshot = None
        self._finish_maintenance_progress(False, "Price relation load failed")
        self._summary.setText(f"Could not load relation data from PDM: {message}")
        self._output.setRowCount(0)

    def _on_maintenance_sources_cancelled(self, message: str) -> None:
        self._finish_maintenance_load()
        self._maintenance_load_snapshot = None
        self._finish_maintenance_progress(False, "Price relation load cancelled")
        self._summary.setText(f"PDM relation loading cancelled: {message}")

    def _generate_all(self) -> None:
        """Generate and display all VARCOND rules for the current relation groups."""
        self._current_parent_codes = [row[0] for row in self._article_rows]
        self._output.setRowCount(0)
        if self._maintenance_check():
            service = self._ensure_maintenance_service()
            if self._current_parent_codes and not service.has_sources(self._current_parent_codes):
                self._load_maintenance_sources_async(self._current_parent_codes, refresh=False)
                return

        total_rules = 0
        warning_messages: list[str] = []
        needle = self._filter.text().strip().casefold()
        rows_to_add: list[tuple[str, str]] = []
        for index in range(self._relations.count()):
            relation_name = self._relations.item(index).text()
            relation_prefix = relation_name[3:] if relation_name.startswith("PA_") else relation_name
            parent_codes = [
                code for code, _label, _article_id in self._article_rows
                if code.startswith(relation_prefix)
                and (not needle or code.casefold().startswith(needle))
            ]
            if not parent_codes:
                continue
            if self._maintenance_check():
                result = service.generate(
                    parent_codes, prefix="",
                    property_exclusions=self._exclusions.text(),
                    property_substitutions=self._substitutions.text(),
                )
            else:
                result = VarCondService(self._context).generate_live(
                    article_codes=parent_codes, prefix="",
                    property_exclusions=self._exclusions.text(),
                    property_substitutions=self._substitutions.text(),
                )
            warning_messages.extend(result.warnings)
            total_rules += len(result.rules)
            rows_to_add.extend(
                (relation_name, rule.rule)
                for rule in result.rules
            )

        self._output.setUpdatesEnabled(False)
        try:
            self._output.setRowCount(len(rows_to_add))
            for row, (relation_name, rule_text) in enumerate(rows_to_add):
                item = QTableWidgetItem(rule_text)
                # Keep relation identity as hidden item metadata for navigation
                # and grouping; the visible working table contains rules only.
                item.setData(Qt.ItemDataRole.UserRole, relation_name)
                self._output.setItem(row, 0, item)
        finally:
            self._output.setUpdatesEnabled(True)

        self._summary.setText(
            f"{self._relations.count()} relation(s) | "
            f"{total_rules:,} generated definition(s)"
            + (f" | {len(warning_messages)} warning(s)" if warning_messages else "")
            + " | Select cells and press Ctrl+C to copy"
        )
        self._summary.setToolTip("\n".join(warning_messages))

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
        properties = self._extract_relation_properties([row[0] for row in self._article_rows])
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
            self._generate_all()

    def _edit_substitutions(self) -> None:
        properties = self._extract_relation_properties([row[0] for row in self._article_rows])
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
            self._generate_all()

