"""PDM-style VARCOND relation browser and generator.

Legacy PDM builds a list of unique PA_<article-prefix> relations. Every relation is generated from its matching parent articles. Changing the
prefix length regroups the already-loaded source rows and regenerates all output. Relation Prefix Length controls the relation name/grouping; it
does not rewrite component target codes inside the VARCOND rules.
"""
from __future__ import annotations

from typing import Callable
from dataclasses import dataclass, field
import re

from PySide6.QtCore import QThreadPool, QTimer, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton,
    QVBoxLayout, QWidget, QSpinBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
)

from core.progress import ProgressReporter
from services.pricing_relation_service import price_relation_names
from services.varcond_service import VarCondService
from ui.dialogs.progress_dialog import ProgressDialog
from ui.workers.background_task import BackgroundTask


def _article_code_matches_filter(code: str, query: str) -> bool:
    """Match article-code filters; * is many chars, ? and _ are one char.

    Plain text retains the existing starts-with behaviour. Wildcard patterns
    are also anchored at the start so users can filter article-code prefixes.
    """
    pattern = (query or "").strip().casefold()
    candidate = (code or "").casefold()
    if not pattern:
        return True
    if not any(char in pattern for char in "*?_"):
        return candidate.startswith(pattern)
    regex = "".join(
        ".*" if char == "*" else "." if char in "?_" else re.escape(char)
        for char in pattern
    )
    return re.match(regex, candidate, flags=re.DOTALL) is not None


@dataclass
class _RelationExportPlan:
    """Everything ``build_relation_objects`` needs, captured on the GUI thread."""

    groups: list = field(default_factory=list)          # [(relation name, [(code, article id)])]
    maintenance: bool = False
    maintenance_service: object = None
    context: object = None
    snapshot: object = None
    exclusions: str = ""
    substitutions: str = ""
    xocd: object = None
    base_entries: list | None = None


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

    #: Pause (ms) after the last keystroke in the filter before the relations are rebuilt.
    FILTER_DEBOUNCE_MS = 250

    def __init__(
        self, context, parent: QWidget | None = None,
        maintenance_check: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(parent)
        self._context = context
        # Development live generation runs on a worker; the latest request wins.
        self._live_seq = 0
        self._live_task: BackgroundTask | None = None
        self._live_scheduled = False
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
        self._relation_store = None
        self._reload_requested = False
        self.setObjectName("varcondGenerationPanel")

        root = QVBoxLayout(self)

        # Expose these controls so the page can align them with PDM / MDB.
        self.controls_widget = QWidget(self)
        controls = QHBoxLayout(self.controls_widget)
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(8)
        controls.addWidget(QLabel("Filter:", self.controls_widget))
        self._filter = QLineEdit(self.controls_widget)
        self._filter.setPlaceholderText("Article code... (* = any, ? or _ = one)")
        self._filter.setToolTip(
            "Filter article-code prefixes. Use * for any number of characters; "
            "? or _ for exactly one character. Example: RY?XS or RY*XS."
        )
        # Typing rebuilds the relation list (and, in Development, regenerates from PDM): wait for a
        # pause instead of doing it per keystroke.
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(self.FILTER_DEBOUNCE_MS)
        self._filter_timer.timeout.connect(self._refresh_relations)
        self._filter.textChanged.connect(lambda *_: self._filter_timer.start())
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
        self._reload_button = QPushButton("Reload Relations", self.controls_widget)
        self._reload_button.setToolTip(
            "Read this product's relation source data from PDM again and replace the "
            "saved copy. Relations are otherwise loaded from the saved copy."
        )
        self._reload_button.clicked.connect(self._on_reload_relations)
        self._reload_button.setVisible(self._maintenance_check())

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
        # Keep the relation list and VARCOND table aligned at the top;
        # place the status/details line beneath the table.
        right.addWidget(self._summary)
        split.addLayout(right, 4)
        root.addLayout(split, 1)

        self._article_rows: list[tuple[str, str, str]] = []
        self._rules_by_relation: dict[str, list[str]] = {}
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
            self._bind_relation_store(self._maintenance_service)
        self._reload_button.setVisible(self._maintenance_check())
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
        self._filter_timer.stop()          # this rebuild supersedes a pending debounced one
        self._rules_by_relation.clear()    # prefix length / filter changed: cached rules no longer apply
        current = self._relations.currentItem().text() if self._relations.currentItem() else ""
        current_prefix = current[3:] if current.startswith("PA_") else current
        anchor_code = next(
            (code for code, _label, _article_id in self._article_rows
             if current_prefix and code.startswith(current_prefix)),
            "",
        )
        needle = self._filter.text().strip().casefold()
        length = self._relation_length.value()
        relation_names: set[str] = set()
        for code, _label, _article_id in self._article_rows:
            if not _article_code_matches_filter(code, needle):
                continue
            relation_prefix = code[:length] if len(code) > length else code
            relation_names.add("PA_" + relation_prefix)
        self._relations.blockSignals(True)
        self._relations.clear()
        for name in sorted(relation_names, key=str.casefold):
            self._relations.addItem(QListWidgetItem(name))
        target_prefix = anchor_code[:length] if anchor_code and len(anchor_code) > length else anchor_code
        target_name = "PA_" + target_prefix if target_prefix else current
        match = self._relations.findItems(target_name, Qt.MatchFlag.MatchExactly) if target_name else []
        if match:
            self._relations.setCurrentItem(match[0])
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
            self._output.setRowCount(0)
            return
        name = current.text()
        if name not in self._rules_by_relation:
            # Only the selected relation is ever generated, so selecting another one must request
            # its rules (Development: live PDM worker; Maintenance: local, from the cached sources).
            self._display_relation_rules(name)
            self._generate_all()
            return
        self._display_relation_rules(name)

    def _display_relation_rules(self, relation_name: str) -> None:
        """Show only the rules belonging to the currently selected relation."""
        rules = self._rules_by_relation.get(relation_name, [])
        self._output.setUpdatesEnabled(False)
        try:
            self._output.setRowCount(len(rules))
            for row, rule_text in enumerate(rules):
                item = QTableWidgetItem(rule_text)
                item.setData(Qt.ItemDataRole.UserRole, relation_name)
                self._output.setItem(row, 0, item)
        finally:
            self._output.setUpdatesEnabled(True)
        char_count = len("\\r\\n".join(rules))
        self._summary.setText(
            f"{relation_name} · {len(rules):,} VARCOND definition(s) · "
            f"{char_count:,} characters"
            if rules else f"{relation_name} · Waiting for this relation to finish loading"
        )

    def _ensure_maintenance_service(self):
        from services.maintenance_varcond_service import MaintenanceVarCondService

        if self._maintenance_service is None:
            self._maintenance_service = MaintenanceVarCondService(self._context)
            self._maintenance_snapshot = self._snapshot
            self._bind_relation_store(self._maintenance_service)
        return self._maintenance_service

    def _bind_relation_store(self, service) -> None:
        """Back the service with this product's saved relation sources."""
        from services.relation_source_store import RelationSourceStore, relation_scope

        scope = relation_scope(self._snapshot, self._context)
        if self._relation_store is None:
            self._relation_store = RelationSourceStore()
        service.bind_store(self._relation_store, scope)

    def _on_reload_relations(self) -> None:
        """Explicit user action: read the relation sources from PDM again."""
        if not self._maintenance_check() or not self._article_rows:
            return
        self._reload_requested = True
        self._load_maintenance_sources_async(
            [row[0] for row in self._article_rows], refresh=True
        )

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
        self._rules_by_relation.clear()
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
        self._reload_button.setEnabled(False)
        self._substitution_button.setEnabled(False)
        stream_prefix_length = self._relation_length.value()
        stream_filter_text = self._filter.text().strip().casefold()
        stream_exclusions = self._exclusions.text()
        stream_substitutions = self._substitutions.text()

        # Build the relation groups once. A relation is published as soon as
        # every parent belonging to that prefix has completed source loading.
        relation_groups: dict[str, list[str]] = {}
        for code, _label, _article_id in self._article_rows:
            if not _article_code_matches_filter(code, stream_filter_text):
                continue
            prefix = code[:stream_prefix_length] if len(code) > stream_prefix_length else code
            relation_groups.setdefault("PA_" + prefix, []).append(code)

        def load_sources(_progress):
            def report_source_progress(completed, total, parent_code):
                if total <= 0:
                    reporter.begin(1, title="Loading Price Relation", subject="All Price Relations")
                    reporter.advance("No uncached PDM sources to load.")
                    return
                if completed == 0:
                    reporter.begin(total, title="Loading Price Relation", subject="All Price Relations")
                    reporter.note(f"Reading {total:,} uncached parent article(s)...")
                    return
                detail = f"Loaded {completed:,} / {total:,} parent articles"
                if parent_code:
                    detail += f" · {parent_code}"
                reporter.advance(detail)

            completed_parents: set[str] = set()
            published_relations: set[str] = set()

            def publish_completed_relation(source):
                completed_parents.add(source.parent)
                for relation_name, group_codes in relation_groups.items():
                    if relation_name in published_relations:
                        continue
                    if not all(code in completed_parents for code in group_codes):
                        continue
                    result = service.generate(
                        group_codes, prefix="",
                        property_exclusions=stream_exclusions,
                        property_substitutions=stream_substitutions,
                    )
                    published_relations.add(relation_name)
                    _progress({
                        "kind": "relation_rules",
                        "relation": relation_name,
                        "parents": list(group_codes),
                        "rules": [rule.rule for rule in result.rules],
                        "warnings": result.warnings,
                    })

            # Cached sources count as complete immediately; newly loaded
            # sources trigger the same relation-readiness check.
            for code in parent_codes:
                if not refresh and code in service._cache:
                    publish_completed_relation(service._cache[code])

            sources = service.sources_for(
                parent_codes, refresh=refresh,
                progress_callback=report_source_progress,
                source_callback=publish_completed_relation,
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
        self._reload_button.setEnabled(True)
        self._substitution_button.setEnabled(True)

    def _on_maintenance_source_progress(self, payload) -> None:
        """Cache completed relation rules and display only the selected relation."""
        if not isinstance(payload, dict) or payload.get("kind") != "relation_rules":
            return
        relation_name = str(payload.get("relation", ""))
        self._rules_by_relation[relation_name] = [
            str(rule_text) for rule_text in payload.get("rules", [])
        ]
        selected = self._relations.currentItem()
        if selected and selected.text() == relation_name:
            self._display_relation_rules(relation_name)
        if payload.get("warnings"):
            current = self._summary.toolTip()
            new_warnings = "\\n".join(str(value) for value in payload["warnings"])
            self._summary.setToolTip("\\n".join(value for value in (current, new_warnings) if value))

    def _on_maintenance_sources_loaded(self, _sources) -> None:
        loaded_snapshot = self._maintenance_load_snapshot
        self._finish_maintenance_load()
        self._maintenance_load_snapshot = None
        refresh = self._maintenance_pending_refresh
        self._maintenance_pending_refresh = False
        if not refresh:
            self._reload_requested = False
        if loaded_snapshot is not self._snapshot:
            # Snapshot changed while PDM was loading. Never render/cache results
            # from the previous product in the newly selected product's panel.
            if self._maintenance_service is not None:
                self._maintenance_service.clear_cache()
                self._maintenance_snapshot = self._snapshot
                self._bind_relation_store(self._maintenance_service)
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
        selected = self._relations.currentItem()
        selected_name = selected.text() if selected is not None else ""
        selected_rules = self._rules_by_relation.get(selected_name, [])
        char_count = len("\\r\\n".join(selected_rules))
        self._summary.setText(
            f"{self._relations.count():,} relation(s) | "
            f"{self._output.rowCount():,} definitions displayed | "
            f"{char_count:,} characters displayed | "
            "All completed relations are ready"
        )
        self._finish_maintenance_progress(True, "VARCOND source data ready")

    def _on_maintenance_sources_failed(self, message: str) -> None:
        was_reload = self._reload_requested
        self._reload_requested = False
        self._finish_maintenance_load()
        self._maintenance_load_snapshot = None
        self._finish_maintenance_progress(False, "Price relation load failed")
        service = self._maintenance_service
        codes = [row[0] for row in self._article_rows]
        if was_reload and service is not None and codes and service.has_sources(codes):
            # The failed reload left the previous saved relations untouched.
            self._generate_all()
            self._summary.setText(
                f"Reload failed - previous saved relations kept: {message}"
            )
            return
        self._summary.setText(f"Could not load relation data from PDM: {message}")
        self._output.setRowCount(0)

    def _on_maintenance_sources_cancelled(self, message: str) -> None:
        self._finish_maintenance_load()
        self._maintenance_load_snapshot = None
        self._finish_maintenance_progress(False, "Price relation load cancelled")
        self._summary.setText(f"PDM relation loading cancelled: {message}")

    def _generate_all(self) -> None:
        """Generate and display only the currently selected relation."""
        self._live_seq += 1                 # supersedes any Development generation still in flight
        self._current_parent_codes = [row[0] for row in self._article_rows]
        selected = self._relations.currentItem()
        if selected is None:
            self._output.setRowCount(0)
            return
        relation_name = selected.text()
        relation_prefix = relation_name[3:] if relation_name.startswith("PA_") else relation_name
        needle = self._filter.text().strip().casefold()
        parent_codes = [
            code for code, _label, _article_id in self._article_rows
            if code.startswith(relation_prefix)
            and _article_code_matches_filter(code, needle)
        ]
        if not parent_codes:
            self._rules_by_relation[relation_name] = []
            self._display_relation_rules(relation_name)
            return
        if self._maintenance_check():
            service = self._ensure_maintenance_service()
            if not service.has_sources(parent_codes):
                self._summary.setText(f"Loading source data for {relation_name}...")
                self._load_maintenance_sources_async(self._current_parent_codes, refresh=False)
                return
            result = service.generate(
                parent_codes, prefix="",
                property_exclusions=self._exclusions.text(),
                property_substitutions=self._substitutions.text(),
            )
        else:
            self._request_live_generation()
            return
        self._rules_by_relation[relation_name] = [rule.rule for rule in result.rules]
        self._summary.setToolTip("\\n".join(result.warnings))
        self._display_relation_rules(relation_name)

    # -- Development: live PDM generation on a worker ----------------------
    def _request_live_generation(self) -> None:
        """Generate the selected relation from PDM on a worker thread.

        Several requests in the same event-loop turn (the panel asks twice when it is built or
        re-entered) are served by one generation, and a result that is no longer current is dropped.
        """
        if not self._live_scheduled:
            self._live_scheduled = True
            QTimer.singleShot(0, self._start_live_generation)

    def _start_live_generation(self) -> None:
        self._live_scheduled = False
        selected = self._relations.currentItem()
        if selected is None or self._maintenance_check():
            return
        relation_name = selected.text()
        relation_prefix = relation_name[3:] if relation_name.startswith("PA_") else relation_name
        needle = self._filter.text().strip().casefold()
        parent_codes = [
            code for code, _label, _article_id in self._article_rows
            if code.startswith(relation_prefix)
            and _article_code_matches_filter(code, needle)
        ]
        if not parent_codes:
            return
        if self._live_task is not None:
            self._live_task.cancel()        # stops at its next PDM query boundary
        seq = self._live_seq
        exclusions, substitutions = self._exclusions.text(), self._substitutions.text()
        context = self._context
        self._summary.setText(f"{relation_name} · Generating from PDM...")

        def work(_progress):
            return VarCondService(context).generate_live(
                article_codes=parent_codes, prefix="",
                property_exclusions=exclusions,
                property_substitutions=substitutions,
            )

        task = BackgroundTask(work)
        self._live_task = task
        task.signals.finished.connect(
            lambda result, seq=seq, name=relation_name: self._on_live_generated(seq, name, result))
        task.signals.failed.connect(
            lambda message, seq=seq, name=relation_name: self._on_live_failed(seq, name, message))
        QThreadPool.globalInstance().start(task)

    def _on_live_generated(self, seq: int, relation_name: str, result) -> None:
        if seq != self._live_seq:
            return                          # superseded by a newer generation
        self._live_task = None
        self._rules_by_relation[relation_name] = [rule.rule for rule in result.rules]
        self._summary.setToolTip("\\n".join(result.warnings))
        selected = self._relations.currentItem()
        if selected is not None and selected.text() == relation_name:
            self._display_relation_rules(relation_name)     # only the selected relation is shown

    def _on_live_failed(self, seq: int, relation_name: str, message: str) -> None:
        if seq != self._live_seq:
            return
        self._live_task = None
        selected = self._relations.currentItem()
        if selected is not None and selected.text() == relation_name:
            self._output.setRowCount(0)
            self._summary.setText(f"{relation_name} · Could not generate from PDM: {message}")

    # -- export --------------------------------------------------------------
    def relation_objects_for_export(self):
        """Build complete PA_<prefix> price relations from the current VARCOND settings.

        Export deliberately ignores the left-side text filter: a filtered view
        must never produce a partial MDB. The selected prefix length and the
        current exclusions/substitutions are retained.
        """
        return self.build_relation_objects(self.prepare_relation_export())

    def prepare_relation_export(
        self, selected_article_ids: set[str] | None = None,
    ) -> "_RelationExportPlan":
        """GUI thread: validate and collect everything the relation build needs.

        Maintenance incremental exports may pass the Articles-page selection.
        A VARCOND relation is shared by every article in its prefix group, so a
        partial group is rejected rather than replacing a shared relation body
        with rules for only part of its existing article coverage.
        """
        if self._maintenance_load_task is not None:
            raise RuntimeError("Wait for PDM source loading to finish before exporting VARCOND relations.")

        all_rows = list(self._article_rows)
        if not all_rows:
            raise RuntimeError("No parent articles with BOM data are available to export.")
        selected = (
            {str(value) for value in selected_article_ids if str(value)}
            if selected_article_ids is not None else None
        )
        if selected is not None:
            if not selected:
                raise RuntimeError("Select one or more articles in the Articles page Export column first.")
            rows_by_prefix: dict[str, list] = {}
            length = self._relation_length.value()
            for row in all_rows:
                code, _label, article_id = row
                prefix = code[:length] if len(code) > length else code
                rows_by_prefix.setdefault("PA_" + prefix, []).append(row)
            selected_rows = []
            for relation_name, rows in rows_by_prefix.items():
                group_ids = {str(row[2]) for row in rows}
                selected_in_group = group_ids & selected
                if selected_in_group and selected_in_group != group_ids:
                    raise RuntimeError(
                        f"VARCOND relation {relation_name} is shared by {len(group_ids)} articles. "
                        "Select every article in that relation group before exporting it."
                    )
                if selected_in_group:
                    selected_rows.extend(rows)
            article_rows = selected_rows
        else:
            article_rows = all_rows

        parent_codes = [row[0] for row in article_rows]
        if not parent_codes:
            raise RuntimeError("The selected articles do not contain a complete VARCOND relation group.")

        if self._maintenance_check():
            service = self._ensure_maintenance_service()
            if not service.has_sources(parent_codes):
                raise RuntimeError("PDM source data is not fully loaded. Wait for all relations to finish loading.")

        length = self._relation_length.value()
        groups: dict[str, list[tuple[str, str]]] = {}
        for code, _label, article_id in article_rows:
            prefix = code[:length] if len(code) > length else code
            groups.setdefault("PA_" + prefix, []).append((code, article_id))

        xocd = getattr(self._context, "xocd_export_service", None)
        entries = None
        if xocd is not None and hasattr(xocd, "base_code_entries"):
            # Selection-independent part of the base codes, computed once for every relation.
            entries = xocd.base_code_entries(self._snapshot)
        return _RelationExportPlan(
            groups=[(name, groups[name]) for name in sorted(groups, key=str.casefold)],
            maintenance=self._maintenance_check(),
            maintenance_service=self._maintenance_service,
            context=self._context,
            snapshot=self._snapshot,
            exclusions=self._exclusions.text(),
            substitutions=self._substitutions.text(),
            xocd=xocd,
            base_entries=entries,
        )

    @staticmethod
    def build_relation_objects(plan: "_RelationExportPlan", emit: Callable[[str], None] | None = None):
        """Generate every relation of ``plan`` (safe on a worker thread: no widget access)."""
        from models.relation_object import RelationObject

        relations = []
        # Option-increment rows are looked up once per component prefix for the whole export.
        increment_cache: dict = {}
        total = len(plan.groups)
        for order, (relation_name, parent_rows) in enumerate(plan.groups, start=100):
            if emit is not None:
                emit(f"Generating {relation_name} ({order - 99} of {total})...")
            codes = [code for code, _article_id in parent_rows]
            if plan.maintenance:
                result = plan.maintenance_service.generate(
                    codes, prefix="",
                    property_exclusions=plan.exclusions,
                    property_substitutions=plan.substitutions,
                )
            else:
                result = VarCondService(plan.context).generate_live(
                    article_codes=codes, prefix="",
                    property_exclusions=plan.exclusions,
                    property_substitutions=plan.substitutions,
                    increment_cache=increment_cache,
                )
            body = "\r\n".join(rule.rule for rule in result.rules if rule.rule)
            if not body.strip():
                continue
            selected_ids = {article_id for _code, article_id in parent_rows}
            if plan.xocd is None:
                base_codes = list(codes)
            elif plan.base_entries is not None:
                base_codes = plan.xocd.base_codes_from_entries(plan.base_entries, selected_ids)
            else:
                base_codes = plan.xocd._base_codes(plan.snapshot, selected_article_ids=selected_ids)
            # Relation object ``P_<prefix>``; its relation is ``PA_<prefix>`` (the group name).
            object_name, defined_name = price_relation_names(relation_name[len("PA_"):])
            relations.append(RelationObject(
                name=object_name,
                relation_name=defined_name,
                type_code="3",
                domain="P",
                order=order,
                body=body,
                article_codes=base_codes,
            ))

        if not relations:
            raise RuntimeError("No VARCOND rules were generated; nothing was exported.")
        return relations

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
            self._rules_by_relation.clear()
            self._generate_all()

    def _extract_relation_substitution_names(self, parent_codes: list[str]) -> list[str]:
        """Return generated VARCOND property names plus option-increment names."""
        names = set(self._extract_relation_properties(parent_codes))
        snapshot = self._snapshot
        if snapshot is None:
            return sorted(names, key=str.casefold)

        service = VarCondService(self._context)
        id_by_code = {
            str(article.id): (article.code or "")
            for article in snapshot.articles if article.id is not None
        }
        id_for_code = {
            code: article_id for article_id, code in id_by_code.items() if code
        }
        components_by_article = snapshot.article_components or {}
        increments_by_prefix = snapshot.option_increments or {}

        for parent_code in parent_codes:
            article_id = id_for_code.get(parent_code)
            if article_id is None:
                continue
            for component in components_by_article.get(article_id, []) or []:
                sub_item = str(component.get("sub_item", "") or "").strip()
                if not sub_item:
                    continue
                prefix = service._item_prefix(sub_item)
                for increment in increments_by_prefix.get(prefix, []) or []:
                    option_name = str(increment.get("option_name", "") or "").strip()
                    if option_name:
                        normalized = service._pcon_option_name(option_name)
                        if normalized:
                            names.add(normalized)
        return sorted(names, key=str.casefold)

    def _edit_substitutions(self) -> None:
        properties = self._extract_relation_substitution_names(
            [row[0] for row in self._article_rows]
        )
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
            self._rules_by_relation.clear()
            self._generate_all()

