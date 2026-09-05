"""Product workspace page.

Connects the product-selection UI to the read-only PDM pipeline. The user
searches PDM on demand (never loading the full catalogue), selects a result,
and loads it into the active snapshot. The page contains no SQL - all data
access goes through the service/repository layers.
"""
from __future__ import annotations

import re
import time

from PySide6.QtCore import Qt, QObject, QRunnable, QThreadPool, QTimer, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.errors import PDMError
from core.progress import ProgressReporter
from core.activity import ActivityType, LogLevel
from models.product import Product
from ui.dialogs.progress_dialog import ProgressDialog
from ui.pages.base_page import BasePage


class _SearchSignals(QObject):
    """Signals emitted from a background search worker."""

    finished = Signal(int, list)  # (token, list[Product])
    failed = Signal(int, str)     # (token, message)


class _SearchWorker(QRunnable):
    """Runs a product search off the UI thread so the UI never freezes."""

    def __init__(self, pdm_service, text: str, limit: int, token: int,
                 signals: _SearchSignals) -> None:
        super().__init__()
        self._pdm_service = pdm_service
        self._text = text
        self._limit = limit
        self._token = token
        self._signals = signals

    def run(self) -> None:
        try:
            results = self._pdm_service.search_products(self._text, self._limit)
            # Also resolve a (full or partial) ARTICLE number to its product and
            # merge it in, deduped by product id. Guarded by length so short,
            # broad queries don't scan the Item table.
            if len(self._text.strip()) >= 3 and len(results) < self._limit:
                seen = {p.id for p in results}
                for product in self._pdm_service.search_products_by_article(
                    self._text, self._limit
                ):
                    if product.id not in seen:
                        seen.add(product.id)
                        results.append(product)
                results = results[: self._limit]
        except PDMError as error:
            self._signals.failed.emit(self._token, str(error))
        except Exception as error:  # defensive: never crash the worker thread
            self._signals.failed.emit(self._token, f"Unexpected error: {error}")
        else:
            self._signals.finished.emit(self._token, results)


class _LoadSignals(QObject):
    """Signals emitted from a background product-load worker."""

    finished = Signal(int, object)  # (token, (product, result, duration))
    failed = Signal(int, str)       # (token, message)


class _LoadWorker(QRunnable):
    """Loads a product into the snapshot off the UI thread."""

    def __init__(self, pdm_service, product, token: int,
                 signals: _LoadSignals) -> None:
        super().__init__()
        self._pdm_service = pdm_service
        self._product = product
        self._token = token
        self._signals = signals

    def run(self) -> None:
        started = time.perf_counter()
        try:
            result = self._pdm_service.load_product(self._product)
        except Exception as error:  # defensive: never crash the worker thread
            self._signals.failed.emit(self._token, f"Unexpected error: {error}")
        else:
            duration = time.perf_counter() - started
            self._signals.finished.emit(
                self._token, (self._product, result, duration)
            )

class _FamilyLoadSignals(QObject):
    """Signals emitted from the background family-load worker."""

    finished = Signal(object)  # ProductLoadResult
    failed = Signal(str)       # message


class _FamilyLoadWorker(QRunnable):
    """Loads a whole family (articles + details) into one snapshot off the UI
    thread, in a single pass.

    The worker only runs the service; all progress/activity reporting is emitted
    by the service through the injected :class:`~core.progress.ProgressReporter`.
    """

    def __init__(self, pdm_service, products, family_name, reporter, signals):
        super().__init__()
        self._pdm_service = pdm_service
        self._products = products
        self._family_name = family_name
        self._reporter = reporter
        self._signals = signals

    def run(self) -> None:
        try:
            result = self._pdm_service.load_family(
                self._products, self._family_name, reporter=self._reporter
            )
        except Exception as error:  # defensive: never crash the worker thread
            self._signals.failed.emit(f"Unexpected error: {error}")
        else:
            self._signals.finished.emit(result)


class _AddFamilyWorker(QRunnable):
    """Merges a family into the CURRENT session's snapshot off the UI thread."""

    def __init__(self, pdm_service, products, family_name, reporter, signals):
        super().__init__()
        self._pdm_service = pdm_service
        self._products = products
        self._family_name = family_name
        self._reporter = reporter
        self._signals = signals

    def run(self) -> None:
        try:
            result = self._pdm_service.add_family_to_session(
                self._products, self._family_name, reporter=self._reporter
            )
        except Exception as error:  # defensive: never crash the worker thread
            self._signals.failed.emit(f"Unexpected error: {error}")
        else:
            self._signals.finished.emit(result)


class _EngineeringInitSignals(QObject):
    """Signals emitted from the background Engineering Initialization worker."""

    finished = Signal()     # engineering initialized successfully
    failed = Signal(str)    # message


class _EngineeringInitWorker(QRunnable):
    """Runs EngineeringInitializationService.initialize() off the UI thread.

    Only the existing initialization service is invoked - no loading, snapshot
    creation or SQL is performed here - so business logic is unchanged; it just
    moves the existing call onto a worker thread using the existing QRunnable
    framework.
    """

    def __init__(self, init_service, snapshot, signals) -> None:
        super().__init__()
        self._service = init_service
        self._snapshot = snapshot
        self._signals = signals

    def run(self) -> None:
        try:
            self._service.initialize(self._snapshot)
        except Exception as error:  # defensive: never crash the worker thread
            self._signals.failed.emit(f"Unexpected error: {error}")
        else:
            self._signals.finished.emit()


# Map the ProgressReporter log kinds to Activity log levels.
_LOG_LEVEL_FOR = {
    "info": LogLevel.INFO,
    "success": LogLevel.SUCCESS,
    "warning": LogLevel.WARNING,
    "error": LogLevel.ERROR,
}


class _ActivityProgressBridge:
    """Translate ProgressReporter signals into Activity updates.

    UI-layer adapter that lets the existing Load Family progress reporter also
    drive an Activity, adding Activity reporting *without changing* any loading,
    repository, engineering or snapshot logic. It forwards the current step,
    current product, item counts and log lines, and maps a few known worker
    steps to coarse stages.
    """

    _STEP_STAGES = (
        ("Connecting", 2, "Repository Retrieval"),
        ("Loading", 2, "Repository Retrieval"),
        ("Merging", 4, "Snapshot Creation"),
    )

    def __init__(self, reporter, activity) -> None:
        self._reporter = reporter
        self._activity = activity
        reporter.step_changed.connect(self._on_step)
        reporter.product_changed.connect(self._on_product)
        reporter.counts_changed.connect(self._on_counts)
        reporter.activity.connect(self._on_log)

    def disconnect(self) -> None:
        """Detach from the reporter so neither object keeps the other alive."""
        reporter = self._reporter
        if reporter is None:
            return
        try:
            reporter.step_changed.disconnect(self._on_step)
            reporter.product_changed.disconnect(self._on_product)
            reporter.counts_changed.disconnect(self._on_counts)
            reporter.activity.disconnect(self._on_log)
        except (RuntimeError, TypeError):
            # Already disconnected or the reporter was deleted - nothing to do.
            pass
        self._reporter = None
        self._activity = None

    def _on_step(self, text: str) -> None:
        stage = self._stage_for(text)
        if stage is not None:
            index, name = stage
            self._activity.update_step(
                text, stage_name=name, stage_index=index, total_stages=6
            )
        else:
            self._activity.update_step(text)

    def _on_product(self, name: str) -> None:
        self._activity.update_step(item=name)

    def _on_counts(self, products: int, total_products: int, *_rest: int) -> None:
        self._activity.update_items(processed=products, total=total_products)

    def _on_log(self, kind: str, message: str) -> None:
        self._activity.add_log(message, _LOG_LEVEL_FOR.get(kind, LogLevel.INFO))

    def _stage_for(self, text: str):
        for prefix, index, name in self._STEP_STAGES:
            if prefix in text:
                return index, name
        return None

class _NavigatorSignals(QObject):
    """Signals emitted from the background navigator (hierarchy) loader."""

    finished = Signal(int, list, object)  # (token, list[Product], grouped)
    failed = Signal(int, str)     # (token, message)


def _group_products(results: list) -> dict:
    """Group products into ``catalogue -> category -> sorted products``.

    Pure CPU work (no Qt), run off the UI thread by the navigator worker so the
    main thread only builds tree nodes from the prepared result.
    """
    catalogues: dict[str, dict] = {}
    for product in results:
        catalogue = product.description or "(no catalogue)"
        category = product.category or "(no category)"
        catalogues.setdefault(catalogue, {}).setdefault(category, []).append(product)
    for categories in catalogues.values():
        for products in categories.values():
            products.sort(key=lambda p: f"{p.code} - {p.name}".casefold())
    return catalogues


class _NavigatorWorker(QRunnable):
    """Loads the browsable product hierarchy off the UI thread.

    Uses the existing ``PdmService.get_products()`` (identity-only catalogue
    listing); it performs no engineering logic and mutates nothing.
    """

    def __init__(self, pdm_service, token: int,
                 signals: _NavigatorSignals, force_refresh: bool = False) -> None:
        super().__init__()
        self._pdm_service = pdm_service
        self._token = token
        self._signals = signals
        self._force_refresh = force_refresh

    def run(self) -> None:
        try:
            products = self._pdm_service.get_cached_products(
                force_refresh=self._force_refresh
            )
            # Group/sort here (off the UI thread) so the main thread only builds
            # the tree nodes from the prepared hierarchy.
            grouped = _group_products(products)
        except Exception as error:  # defensive: never crash the worker thread
            self._signals.failed.emit(self._token, str(error))
        else:
            self._signals.finished.emit(self._token, products, grouped)


class ProductPage(BasePage):
    """Product engineering dashboard: search, load and review a product."""

    #: Emitted with a short status label when the active product changes.
    product_loaded = Signal(str)
    #: Emitted after the active snapshot changes (load or clear).
    snapshot_changed = Signal()
    #: Emitted when the snapshot is published but Engineering Initialization has
    #: not yet run (family load Stage A): refresh only snapshot-dependent pages.
    snapshot_published = Signal()
    #: Emitted after background Engineering Initialization completes.
    engineering_ready = Signal()
    #: Emitted once when a load is fully complete (all phases done): triggers a
    #: single final refresh of the Articles and Class Creation workspaces.
    load_complete = Signal()
    #: Requests the Review workspace for repository ↔ PDM comparison.
    repository_review_requested = Signal()

    #: Max results requested per search.
    SEARCH_LIMIT = 50
    #: Live-search debounce interval in milliseconds.
    DEBOUNCE_MS = 350

    # Snapshot status rows: (label, snapshot collection attribute or None).
    _STATUS_ROWS = (
        ("Product", None),
        ("Articles", "articles"),
        ("Properties", "properties"),
        ("Property Values", "property_values"),
        ("Options", "options"),
        ("Option Values", "option_values"),
        ("Metadata", None),
    )

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Product",
            description="Open and engineer a product from the PDM hierarchy.",
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._results: list[Product] = []
        self._loaded_product: Product | None = None
        # Active engineering node highlighting (Solution-Explorer style).
        self._leaf_by_key: dict[tuple[str, str, str], QTreeWidgetItem] = {}
        self._active_key: tuple[str, str, str] | None = None
        # Lazy navigator: category node -> its products (leaves built on expand).
        self._category_products: dict[QTreeWidgetItem, list[Product]] = {}
        self._materialized: set[QTreeWidgetItem] = set()

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(self.DEBOUNCE_MS)
        self._debounce.timeout.connect(self._apply_search)

        # Background search execution keeps the UI responsive during queries.
        self._pool = QThreadPool.globalInstance()
        self._search_token = 0
        self._search_signals = _SearchSignals()
        self._search_signals.finished.connect(self._on_search_finished)
        self._search_signals.failed.connect(self._on_search_failed)

        # Background product loading (loads can take several seconds).
        self._load_token = 0
        self._load_signals = _LoadSignals()
        self._load_signals.finished.connect(self._on_load_finished)
        self._load_signals.failed.connect(self._on_load_failed)

        # Background navigator load: the default browsable Catalogue -> Category
        # -> Product hierarchy shown before any search. Reuses the tree and the
        # existing result-population logic; the search path stays untouched.
        self._navigator_products: list[Product] = []
        self._navigator_grouped: dict | None = None
        self._navigator_token = 0
        self._navigator_loading = False
        self._navigator_signals = _NavigatorSignals()
        self._navigator_signals.finished.connect(self._on_navigator_finished)
        self._navigator_signals.failed.connect(self._on_navigator_failed)

        self.add_content(self._build_top_section())

        self._reset_display()
        self._update_explorer_view()
        # Populate the default navigator hierarchy on open.
        self._load_navigator()

    # -- UI construction ---------------------------------------------------
    def _build_top_section(self) -> QWidget:
        """Working area: Product Explorer (left) + Repository Workspace (right)."""
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setObjectName("productTopSplitter")
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_explorer())
        splitter.addWidget(self._build_context())
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([700, 340])
        return splitter

    def _build_explorer(self) -> QWidget:
        box = QGroupBox("Product Explorer", self)
        outer = QVBoxLayout(box)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)

        search_row = QHBoxLayout()
        self._search_input = QLineEdit(box)
        self._search_input.setPlaceholderText("Filter the product hierarchy...")
        self._search_input.setClearButtonEnabled(True)
        self._search_input.textChanged.connect(self._on_search_text_changed)
        search_row.addWidget(self._search_input, 1)

        # The cached hierarchy is the primary navigation source; this button
        # re-syncs it from PDM through the existing loader. Live filtering of
        # the cache is handled entirely by the search box above.
        self._refresh_hierarchy_btn = QPushButton("Refresh Hierarchy", box)
        self._refresh_hierarchy_btn.setToolTip(
            "Re-sync the Catalogue \u2192 Category \u2192 Product hierarchy from PDM "
            "and update the local cache"
        )
        self._refresh_hierarchy_btn.clicked.connect(self._on_refresh_hierarchy)
        search_row.addWidget(self._refresh_hierarchy_btn)
        outer.addLayout(search_row)

        self._tree = QTreeWidget(box)
        self._tree.setObjectName("productResults")
        self._tree.setHeaderLabel("Catalogue / Category / Product")
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tree.setMinimumHeight(220)
        self._tree.setUniformRowHeights(True)
        self._tree.itemSelectionChanged.connect(self._on_selection_changed)
        self._tree.itemDoubleClicked.connect(self._on_tree_double_clicked)
        self._tree.itemExpanded.connect(self._on_item_expanded)
        # This explorer provides its own engineering context menu, so it opts
        # out of the generic shared tree menu (Expand/Collapse/Copy).
        self._tree.setProperty("_ews_standardized", True)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_explorer_menu)
        outer.addWidget(self._tree, 1)

        # Meaningful empty state so the explorer never appears as a blank pane.
        self._explorer_placeholder = QLabel(
            "No engineering session loaded.\n\n"
            "Search PDM above to browse the Catalogue \u2192 Category \u2192 Product "
            "hierarchy, then select a Category or Product and choose Load to begin.",
            box,
        )
        self._explorer_placeholder.setObjectName("pagePlaceholder")
        self._explorer_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._explorer_placeholder.setWordWrap(True)
        outer.addWidget(self._explorer_placeholder, 1)

        self._search_status = QLabel("", box)
        self._search_status.setObjectName("pageSubtitle")
        self._search_status.setWordWrap(True)
        outer.addWidget(self._search_status)

        return box

    def _build_context(self) -> QWidget:
        """Centralized product workspace for repository and data-source controls."""
        box = QGroupBox("Repository Workspace", self)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        product_section = QGroupBox("Current Product", box)
        product_form = QFormLayout(product_section)
        product_form.setContentsMargins(8, 6, 8, 8)
        product_form.setSpacing(4)

        self._info_name = QLabel("-", product_section)
        self._info_code = QLabel("-", product_section)
        self._info_category = QLabel("-", product_section)
        self._info_catalogue = QLabel("-", product_section)
        for widget in (
            self._info_name,
            self._info_code,
            self._info_category,
            self._info_catalogue,
        ):
            widget.setWordWrap(True)

        product_form.addRow("Name:", self._info_name)
        product_form.addRow("Code:", self._info_code)
        product_form.addRow("Category:", self._info_category)
        product_form.addRow("Catalogue:", self._info_catalogue)
        layout.addWidget(product_section)

        repository_section = QGroupBox("Repository", box)
        repository_layout = QVBoxLayout(repository_section)
        repository_layout.setContentsMargins(8, 6, 8, 8)
        repository_layout.setSpacing(6)

        self._repository_path = QLabel("Not connected", repository_section)
        self._repository_path.setObjectName("pageSubtitle")
        self._repository_path.setWordWrap(True)
        repository_layout.addWidget(self._repository_path)

        self._repository_status = QLabel(
            "Select a repository workspace to begin existing-series discovery.",
            repository_section,
        )
        self._repository_status.setObjectName("pageSubtitle")
        self._repository_status.setWordWrap(True)
        repository_layout.addWidget(self._repository_status)

        buttons = QHBoxLayout()
        self._open_repository_btn = QPushButton("Open Repository", repository_section)
        self._open_repository_btn.clicked.connect(self._on_open_repository)
        buttons.addWidget(self._open_repository_btn)

        self._clear_repository_btn = QPushButton("Clear", repository_section)
        self._clear_repository_btn.clicked.connect(self._on_clear_repository)
        self._clear_repository_btn.setEnabled(False)
        buttons.addWidget(self._clear_repository_btn)
        repository_layout.addLayout(buttons)
        layout.addWidget(repository_section)

        sources_section = QGroupBox("Data Sources", box)
        sources_layout = QVBoxLayout(sources_section)
        sources_layout.setContentsMargins(8, 6, 8, 8)
        sources_layout.setSpacing(6)

        note = QLabel(
            "Repository provides the existing engineered baseline. PDM remains "
            "available for targeted live updates such as fabric, finish or pricing.",
            sources_section,
        )
        note.setObjectName("pageSubtitle")
        note.setWordWrap(True)
        sources_layout.addWidget(note)

        self._check_pdm_btn = QPushButton("Check PDM Changes", sources_section)
        self._check_pdm_btn.setToolTip(
            "Open Review to compare the selected repository series with discovered "
            "PDM candidates. Candidates are evidence only and are not auto-mapped."
        )
        self._check_pdm_btn.clicked.connect(self._on_check_repository_pdm)
        self._check_pdm_btn.setEnabled(False)
        sources_layout.addWidget(self._check_pdm_btn)
        layout.addWidget(sources_section)

        layout.addStretch(1)
        return box

    def _on_open_repository(self) -> None:
        """Discover existing series from the standard Seating + Tables roots."""
        from PySide6.QtWidgets import QInputDialog, QMessageBox

        roots = [
            r"C:\\HermanMillerOFMLSVN\\Staging\\HermanMiller\\WS\\Seating\\Seating",
            r"C:\\HermanMillerOFMLSVN\\Staging\\HermanMiller\\WS\\Tables\\Tables",
        ]
        repository = ";".join(roots)

        try:
            folders = self._context.version_update_service.series_folders(repository)
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Open Repository",
                f"Could not scan the standard repository locations:\\n{exc}",
            )
            return

        if not folders:
            QMessageBox.information(
                self,
                "Open Repository",
                "No series were found in the Seating or Tables repository locations.",
            )
            return

        items = []
        paths = {}
        for folder in folders:
            label = folder.name
            # Keep the UI label unambiguous when the same series name exists
            # under more than one workspace root.
            if label in paths:
                label = f"{folder.name} ({folder.parent.name})"
            paths[label] = str(folder)
            items.append(label)

        items.sort(key=str.lower)
        selected, accepted = QInputDialog.getItem(
            self,
            "Open Existing Series",
            f"Select a series ({len(items)} found):",
            items,
            0,
            False,
        )
        if not accepted or not selected:
            return

        directory = paths[selected]
        try:
            data_context = self._context.repository_context_service.open_series(
                directory
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Open Repository",
                f"Series was selected but its data context could not be read:\n{exc}",
            )
            return

        self._repository_path.setText(directory)
        self._info_name.setText(str(data_context.records["name"].value or "-"))
        self._info_code.setText(str(data_context.records["code"].value or "-"))
        self._info_category.setText(str(data_context.records["category"].value or "-"))
        self._info_catalogue.setText(
            str(data_context.records["catalogue"].value or "-")
        )

        pdm_status = {
            "exact_match": "PDM exact match",
            "candidates_found": f"PDM candidates: {data_context.pdm_match_count}",
            "not_found": "No PDM match found",
            "unavailable": "PDM cross-check unavailable",
        }.get(data_context.pdm_match_status, "PDM not checked")
        self._repository_status.setText(
            f"Existing series selected: {data_context.series_name} · {pdm_status}"
        )
        self._clear_repository_btn.setEnabled(True)
        self._check_pdm_btn.setEnabled(True)

    def _on_check_repository_pdm(self) -> None:
        """Send repository/PDM evidence to the existing Review workflow."""
        if self._context.repository_context_service.active_context is None:
            return
        self.repository_review_requested.emit()

    def _on_clear_repository(self) -> None:
        self._repository_path.setText("Not connected")
        self._repository_status.setText(
            "Select a repository workspace to begin existing-series discovery."
        )
        self._clear_repository_btn.setEnabled(False)
        self._check_pdm_btn.setEnabled(False)
        self._context.repository_context_service.clear()
        for label in (
            self._info_name,
            self._info_code,
            self._info_category,
            self._info_catalogue,
        ):
            label.setText("-")

    # -- search ------------------------------------------------------------
    def _on_search_text_changed(self, text: str) -> None:
        if not text.strip():
            # Cleared: restore the default navigator hierarchy in place.
            self._debounce.stop()
            self._show_navigator()
            return
        # Debounce BOTH the live filter and the PDM search - filtering the full
        # hierarchy is expensive, so it must not run on every keystroke.
        self._debounce.start()

    def _apply_search(self) -> None:
        """Debounced dispatch: filter the loaded hierarchy in place, or search
        PDM when the hierarchy is not loaded yet."""
        text_s = self._search_input.text().strip()
        if not text_s:
            self._show_navigator()
            return
        if self._tree.topLevelItemCount() == 0:
            self._run_search()
            return
        matches = self._filter_tree(text_s)
        if matches:
            self._search_status.setText(
                f"{matches} product(s) match '{text_s}'."
            )
        elif any(
            not self._tree.topLevelItem(i).isHidden()
            for i in range(self._tree.topLevelItemCount())
        ):
            self._search_status.setText(
                f"Catalogue/category matches for '{text_s}' - expand to browse."
            )
        else:
            self._search_status.setText(f"No matches for '{text_s}'.")

    def _filter_tree(self, text: str) -> int:
        """Filter the loaded hierarchy in place across ALL levels, in priority
        order: catalogue name, then category name, then product/article.

        - A CATALOGUE name match reveals the catalogue and its category nodes
          (collapsed, drill-in) without building every leaf.
        - A CATEGORY name match reveals the category with all its products.
        - A PRODUCT/article match (code or name) reveals the matching leaves.
        Only categories with a match are materialized, so it stays cheap.
        Returns the count of visible product leaves."""
        low = text.lower()
        visible = 0
        self._tree.setUpdatesEnabled(False)
        try:
            for i in range(self._tree.topLevelItemCount()):
                catalogue = self._tree.topLevelItem(i)
                catalogue_match = low in catalogue.text(0).lower()
                catalogue_visible = False
                for j in range(catalogue.childCount()):
                    category = catalogue.child(j)
                    category_match = low in category.text(0).lower()
                    products = self._category_products.get(category, [])
                    product_match = any(
                        low in f"{p.code} - {p.name}".lower() for p in products
                    )
                    if category_match or product_match:
                        # Materialize and reveal: all products for a category-name
                        # match, only the matching ones for a product/article hit.
                        self._materialize_category(category)
                        for k in range(category.childCount()):
                            leaf = category.child(k)
                            match = category_match or low in leaf.text(0).lower()
                            leaf.setHidden(not match)
                            if match:
                                visible += 1
                        category.setHidden(False)
                        category.setExpanded(True)
                        catalogue_visible = True
                    elif catalogue_match:
                        # Catalogue name matched: show the category node to drill
                        # into, but don't build all its leaves (keeps it cheap).
                        category.setHidden(False)
                        category.setExpanded(False)
                        catalogue_visible = True
                    else:
                        category.setHidden(True)
                catalogue.setHidden(not catalogue_visible)
                catalogue.setExpanded(catalogue_visible)
        finally:
            self._tree.setUpdatesEnabled(True)
        return visible

    def _update_explorer_view(self) -> None:
        """Toggle between the hierarchy tree and its empty-state guidance."""
        has_items = self._tree.topLevelItemCount() > 0
        self._tree.setVisible(has_items)
        self._explorer_placeholder.setVisible(not has_items)

    # -- navigator (default hierarchy) ------------------------------------
    def _load_navigator(self, force_refresh: bool = False) -> None:
        """Load the default Catalogue -> Category -> Product hierarchy in the
        background so the explorer is browsable before any search. Uses the
        on-disk registry cache unless ``force_refresh`` re-syncs from PDM."""
        if self._navigator_loading:
            return
        self._navigator_loading = True
        self._navigator_token += 1
        token = self._navigator_token
        if not self._search_input.text().strip():
            self._search_status.setText(
                "Refreshing product hierarchy..."
                if force_refresh
                else "Loading product hierarchy..."
            )
        worker = _NavigatorWorker(
            self._context.pdm_service, token, self._navigator_signals, force_refresh
        )
        self._pool.start(worker)

    def _on_refresh_hierarchy(self) -> None:
        # The button always re-syncs from PDM and rewrites the local cache.
        self._load_navigator(force_refresh=True)

    def reload_products(self) -> None:
        """Re-sync the product hierarchy from the currently selected PDM
        database (used after switching databases)."""
        self._load_navigator(force_refresh=True)

    def reset_for_database_switch(self) -> None:
        """Drop the loaded product/snapshot and re-sync the hierarchy from the
        newly selected PDM database, so no query result or workspace keeps data
        from the previous database."""
        self._on_clear_snapshot()  # clears snapshot + display, refreshes all pages
        self.reload_products()

    def _on_navigator_finished(self, token: int, products: list, grouped=None) -> None:
        if token != self._navigator_token:
            return
        self._navigator_loading = False
        self._navigator_products = products
        self._navigator_grouped = grouped
        # Share id -> name so pages resolve product NAMES (e.g. Long Text).
        self._context.set_product_registry(products)
        # Only take over the explorer when the user is not mid-search.
        if not self._search_input.text().strip():
            self._show_navigator()

    def _on_navigator_failed(self, token: int, message: str) -> None:
        if token != self._navigator_token:
            return
        self._navigator_loading = False
        if not self._search_input.text().strip():
            self._search_status.setText(
                f"Product hierarchy unavailable: {message}"
            )

    def _show_navigator(self) -> None:
        """Show the default navigator hierarchy, reusing the existing tree and
        the existing result-population logic. Loads it first if needed.

        The navigator opens collapsed to its top-level catalogues; categories
        and products expand on user interaction."""
        if self._navigator_products:
            self._populate_results(
                self._navigator_products, expand=False, lazy=True,
                grouped=self._navigator_grouped,
            )
            self._search_status.setText(
                f"Browsing {len(self._navigator_products)} products. "
                "Type to filter the hierarchy."
            )
        elif not self._navigator_loading:
            self._load_navigator()

    def _run_search(self) -> None:
        self._debounce.stop()
        text = self._search_input.text().strip()
        if not text:
            self._populate_results([])
            return
        self._search_token += 1
        token = self._search_token
        self._search_status.setText(f"Searching for '{text}'...")
        worker = _SearchWorker(
            self._context.pdm_service, text, self.SEARCH_LIMIT, token,
            self._search_signals,
        )
        self._pool.start(worker)

    def _on_search_finished(self, token: int, results: list) -> None:
        if token != self._search_token:
            return
        self._populate_results(results)
        if results:
            capped = (
                f" (showing first {self.SEARCH_LIMIT})"
                if len(results) >= self.SEARCH_LIMIT
                else ""
            )
            self._search_status.setText(
                f"Found {len(results)} matching products{capped}."
            )
        else:
            text = self._search_input.text().strip()
            self._search_status.setText(f"No products match '{text}'.")

    def _on_search_failed(self, token: int, message: str) -> None:
        if token != self._search_token:
            return
        self._populate_results([])
        self._search_status.setText(f"PDM error: {message}")
        QMessageBox.warning(self, "PDM", message)

    def _populate_results(
        self, results: list[Product], expand: bool = True, lazy: bool = False,
        grouped: dict | None = None,
    ) -> None:
        self._results = results
        self._tree.clear()
        self._leaf_by_key = {}
        self._category_products = {}
        self._materialized = set()

        # Group into catalogue -> category -> products. Reuse the worker's
        # prepared grouping when given (navigator); search results group here.
        catalogues = grouped if grouped is not None else _group_products(results)

        # Catalogues ordered by lead time (the number in the catalogue name),
        # highest first. Categories and products below are alphabetical. When
        # ``lazy`` (the full browse hierarchy, up to ~120k products), only the
        # catalogue/category nodes are built now; each category's product leaves
        # are materialized on first expand so the tree never freezes the UI.
        self._tree.setUpdatesEnabled(False)
        try:
            for catalogue in sorted(catalogues, key=self._catalogue_sort_key):
                categories = catalogues[catalogue]
                cat_node = QTreeWidgetItem(self._tree, [catalogue])
                for category in sorted(categories, key=str.casefold):
                    category_node = QTreeWidgetItem(cat_node, [category])
                    products = categories[category]  # already sorted
                    self._category_products[category_node] = products
                    if lazy:
                        # Show the expand affordance without building leaves yet.
                        category_node.setChildIndicatorPolicy(
                            QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator
                        )
                    else:
                        self._materialize_category(category_node)
        finally:
            self._tree.setUpdatesEnabled(True)

        # Search results stay expanded (every branch is a match); the default
        # navigator is left collapsed to its top-level catalogues.
        if expand:
            self._tree.expandAll()
        # Keep the active engineering node highlighted across searches so the
        # explorer never switches into an unrelated "results only" mode.
        self._reapply_active_highlight()
        self._update_explorer_view()
        self._on_selection_changed()

    def _materialize_category(self, category_node: QTreeWidgetItem) -> None:
        """Build a category's product leaves on demand (idempotent)."""
        if category_node in self._materialized:
            return
        self._materialized.add(category_node)
        leaves: list[QTreeWidgetItem] = []
        active_leaf = None
        for product in self._category_products.get(category_node, []):
            leaf = QTreeWidgetItem([f"{product.code} - {product.name}"])
            leaf.setData(0, Qt.ItemDataRole.UserRole, product)
            key = self._product_tree_key(product)
            self._leaf_by_key[key] = leaf
            if self._active_key and key == self._active_key:
                active_leaf = leaf
            leaves.append(leaf)
        if leaves:
            category_node.addChildren(leaves)  # one batch insert (fast)
            # Style only the active leaf just added - a full re-highlight here
            # is O(all leaves) and made broad filters quadratic.
            if active_leaf is not None:
                self._apply_active_style(active_leaf)

    def _on_item_expanded(self, item: QTreeWidgetItem) -> None:
        """Materialize a category's leaves the first time it is expanded."""
        if item in self._category_products:
            self._materialize_category(item)

    @staticmethod
    def _catalogue_sort_key(name: str) -> tuple:
        """Order catalogues by lead time (highest first). The lead time is the
        first number in the catalogue name, e.g. '120 Day Leadtime'. Names with
        no number fall back to alphabetical, after the numbered ones."""
        match = re.search(r"\d+", name or "")
        if match:
            return (0, -int(match.group()), name.casefold())
        return (1, 0, name.casefold())

    @staticmethod
    def _product_tree_key(product: Product) -> tuple[str, str, str]:
        """Return a stable explorer key that preserves catalogue context."""
        return (
            str(product.id or ""),
            str(product.catalogue_id or ""),
            (product.code or "").strip().casefold(),
        )

    # -- explorer selection / scope ---------------------------------------
    def _current_item(self) -> QTreeWidgetItem | None:
        items = self._tree.selectedItems()
        return items[0] if items else None

    def _node_scope(self, item: QTreeWidgetItem | None) -> str | None:
        """Return the engineering scope of a tree node.

        Scopes:
          * ``product``  - a leaf that stores a Product in UserRole
          * ``family``   - a grouping node whose direct children are products
          * ``category`` - other non-product grouping nodes below catalogue
          * ``catalogue``- top-level grouping node
        """
        if item is None:
            return None
        if isinstance(item.data(0, Qt.ItemDataRole.UserRole), Product):
            return "product"
        # A category (family) node groups products - even before its leaves are
        # lazily materialized, so recognise it via the deferred product list.
        if item in self._category_products:
            return "family"
        if any(
            isinstance(item.child(i).data(0, Qt.ItemDataRole.UserRole), Product)
            for i in range(item.childCount())
        ):
            return "family"
        return "catalogue" if item.parent() is None else "category"

    def _on_selection_changed(self) -> None:
        # Selection state is used by explorer interactions (double-click and
        # context menu). No bottom action buttons are present on this page.
        _ = self._node_scope(self._current_item())

    def _selected_product(self) -> Product | None:
        item = self._current_item()
        product = item.data(0, Qt.ItemDataRole.UserRole) if item else None
        return product if isinstance(product, Product) else None

    def _collect_products(self, item: QTreeWidgetItem) -> list[Product]:
        """All products under a node (product leaf, category, or catalogue)."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, Product):
            return [data]
        direct = self._category_products.get(item)
        if direct:
            return list(direct)
        out: list[Product] = []
        for i in range(item.childCount()):
            out.extend(self._collect_products(item.child(i)))
        return out

    def _selected_family_products(self) -> tuple[list[Product], str]:
        """Union of products across every selected node, plus a display name.

        Lets the user multi-select any mix of products, categories and
        catalogues; all their products load together via the existing family
        load. Deduplicates by product id, preserving order.
        """
        items = list(self._tree.selectedItems())
        current = self._current_item()
        if current is not None and current not in items:
            items.append(current)
        seen: set[str] = set()
        products: list[Product] = []
        for item in items:
            for product in self._collect_products(item):
                pid = str(getattr(product, "id", "") or "")
                if pid and pid not in seen:
                    seen.add(pid)
                    products.append(product)
        names = [item.text(0) for item in items]
        if len(names) == 1:
            name = names[0]
        elif len(names) > 1:
            name = f"{len(names)} selections"
        else:
            name = ""
        return products, name

    def _on_tree_double_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        # Double-clicking a product opens it; group nodes keep Qt's natural
        # expand/collapse behaviour (drill into the hierarchy).
        if isinstance(item.data(0, Qt.ItemDataRole.UserRole), Product):
            self._on_load_product()

    def _show_explorer_menu(self, pos) -> None:
        """Right-click engineering actions for the explorer, adapted to the
        node under the cursor. Wired to the existing handlers - no new
        engineering behaviour."""
        item = self._tree.itemAt(pos)
        # Preserve an existing multi-selection when right-clicking within it;
        # otherwise select the clicked node.
        if item is not None and item not in self._tree.selectedItems():
            self._tree.setCurrentItem(item)
        selected = self._tree.selectedItems()
        multi = len(selected) > 1
        scope = self._node_scope(self._current_item())
        is_group = scope in ("family", "category", "catalogue")
        has_snapshot = self._context.snapshot_manager.has_snapshot()

        menu = QMenu(self._tree)

        if multi or is_group:
            if multi:
                label = f"Load Selected ({len(selected)})"
            else:
                label = {
                    "family": "Load Family",
                    "category": "Load Category",
                    "catalogue": "Load Catalogue",
                }.get(scope, "Load")
            # No session -> fresh load; existing session -> add to it.
            if has_snapshot:
                load = None
                add_to_session = menu.addAction(label + " to Session")
            else:
                load = menu.addAction(label)
                add_to_session = None
            clear_action = menu.addAction("Clear Snapshot")
            clear_action.setEnabled(has_snapshot)
            menu.addSeparator()
            refresh_hierarchy = menu.addAction("Refresh Hierarchy")
            chosen = menu.exec(self._tree.viewport().mapToGlobal(pos))
            if chosen is None:
                return
            if load is not None and chosen is load:
                self._on_load_family()
            elif add_to_session is not None and chosen is add_to_session:
                self._on_add_family_to_session()
            elif chosen is clear_action:
                self._on_clear_snapshot()
            elif chosen is refresh_hierarchy:
                self._on_refresh_hierarchy()
            return

        # Single product selection.
        load = menu.addAction("Load Product")
        load.setEnabled(scope == "product")
        clear_action = menu.addAction("Clear Snapshot")
        clear_action.setEnabled(has_snapshot)
        menu.addSeparator()
        refresh_hierarchy = menu.addAction("Refresh Hierarchy")
        chosen = menu.exec(self._tree.viewport().mapToGlobal(pos))
        if chosen is None:
            return
        if chosen is load:
            self._on_load_product()
        elif chosen is clear_action:
            self._on_clear_snapshot()
        elif chosen is refresh_hierarchy:
            self._on_refresh_hierarchy()

    def _on_load_family(self) -> None:
        """Load the family represented by the current Product selection."""
        products, family_name = self._selected_family_products()
        self.load_family_products(products, family_name)

    def load_family_products(self, products, family_name: str) -> bool:
        """Start the established family loader for an externally resolved product set.

        Review uses this entry point after the user confirms a catalogue. The
        exact same worker, reusable ProgressDialog, ProgressReporter, Activity
        bridge and completion signals are used as a normal Product-page family
        load; Review only supplies the already-resolved product boundary.
        """
        if not products:
            self._search_status.setText("No PDM products were supplied for loading.")
            return False

        # One reusable reporter drives both the progress dialog and the Activity
        # panel; business logic in the service only calls the reporter methods.
        reporter = ProgressReporter(self)
        dialog = self._progress_monitor()
        dialog.bind(reporter)

        main = self.window()
        if hasattr(main, "log_activity"):
            reporter.activity.connect(main.log_activity)

        # Advance plan (single-pass load). The popup stays open showing live
        # progress until the whole load finishes, then auto-closes. Steps:
        #   connect(1) + articles(1) + info(1)   [articles]
        #   + properties(1) + options(1) + links(1) + merge(1) + sets(1) + save(1)
        #   [details] + initialize(1) + finalize(1)  [engineering + workspaces]
        total_steps = 12
        reporter.begin(total_steps, title="Loading Family", subject=family_name)
        reporter.log("info", "Started Load Family")

        # Activity Framework reporting (additive; business logic unchanged). The
        # activity is driven by the same reporter via a UI-layer bridge, plus the
        # UI-controlled stages set in the finished handler.
        activity = self._context.activity_service.start_activity(
            f"Loading Family: {family_name}" if family_name else "Loading Family",
            ActivityType.LOAD,
            total_items=len(products),
            context={"Family": family_name, "Products": len(products)},
        )
        activity.update_step(
            "Resolving Product IDs",
            stage_name="Resolving Product IDs",
            stage_index=1,
            total_stages=6,
        )
        activity.add_log(
            f"Loading family '{family_name}' ({len(products)} product(s))"
        )
        self._family_activity = activity
        self._family_activity_bridge = _ActivityProgressBridge(reporter, activity)

        # Keep references alive for the duration of the async load.
        self._family_reporter = reporter
        self._family_dialog = dialog
        self._family_products = products
        self._family_name = family_name

        signals = _FamilyLoadSignals()
        signals.finished.connect(self._on_family_finished)
        signals.failed.connect(self._on_family_load_failed)
        self._family_signals = signals

        worker = _FamilyLoadWorker(
            self._context.pdm_service, products, family_name, reporter, signals
        )
        dialog.show()
        dialog.raise_()
        self._pool.start(worker)
        return True

    def _on_add_family_to_session(self) -> None:
        """Merge the selected family into the CURRENT session (accumulate).

        Unlike Load Family (which starts a fresh session), this unions the
        family's articles/properties/options into the active snapshot and
        re-groups the article sets, reduction and Class Creation across every
        family now in the session. Falls back to a fresh load when there is no
        active session yet.
        """
        # Products come from every selected node (products / categories /
        # catalogues), so multi-selection adds them all to the session.
        products, family_name = self._selected_family_products()
        if not products:
            self._search_status.setText("Select product(s) or categories to load.")
            return

        reporter = ProgressReporter(self)
        dialog = self._progress_monitor()
        dialog.bind(reporter)
        main = self.window()
        if hasattr(main, "log_activity"):
            reporter.activity.connect(main.log_activity)
        # connect+articles+info+props+options+links+merge+sets+save(9) + refresh(1)
        reporter.begin(10, title="Add Family to Session", subject=family_name)
        reporter.log("info", "Adding family to session")
        activity = self._context.activity_service.start_activity(
            f"Adding Family: {family_name}" if family_name else "Adding Family",
            ActivityType.LOAD,
            total_items=len(products),
            context={"Family": family_name, "Products": len(products)},
        )
        activity.add_log(
            f"Adding family '{family_name}' ({len(products)} product(s)) to session"
        )
        self._family_activity = activity
        self._family_activity_bridge = _ActivityProgressBridge(reporter, activity)
        self._family_reporter = reporter
        self._family_dialog = dialog
        self._family_products = products
        self._family_name = family_name

        signals = _FamilyLoadSignals()
        signals.finished.connect(self._on_add_family_finished)
        signals.failed.connect(self._on_family_load_failed)
        self._family_signals = signals
        worker = _AddFamilyWorker(
            self._context.pdm_service, products, family_name, reporter, signals
        )
        dialog.show()
        dialog.raise_()
        self._pool.start(worker)

    def _on_add_family_finished(self, result) -> None:
        """A family was merged into the session: sync engineering additively and
        re-group (article sets, Class Creation, reduction) across all families."""
        reporter = self._family_reporter
        activity = getattr(self, "_family_activity", None)
        if not result.ok:
            reporter.log("error", result.message)
            reporter.finish(False, result.message)
            if activity is not None:
                activity.fail(result.message)
            QMessageBox.warning(self, "Load Family to Session", result.message)
            self._finalize_load()
            return

        snapshot = self._context.active_snapshot
        self._loaded_product = snapshot.product if snapshot is not None else None
        # Additive engineering sync: add members for the new articles without
        # discarding existing families / reduction work.
        reporter.advance("Refreshing Workspaces")
        try:
            self._context.engineering_initialization_service.sync(snapshot)
        except Exception as error:  # never let sync break the add
            reporter.log("error", f"Engineering sync: {error}")
        # Re-group everything across the combined session.
        self.product_loaded.emit(
            f"Session: {len(snapshot.articles)} articles"
            if snapshot is not None else "Session"
        )
        self.snapshot_published.emit()
        self.engineering_ready.emit()
        reporter.log("success", "Family added to session")
        reporter.finish(True, "Family added to session")
        if activity is not None:
            activity.complete("Family added to session")
        # One final refresh of Articles + Class Creation now everything is in.
        self.load_complete.emit()
        self._finalize_load()

    def _progress_monitor(self) -> ProgressDialog:
        """Return the single reusable progress monitor, creating it once.

        The dialog is a non-modal live monitor that persists across loads; it is
        never recreated, so it can be reopened while a load is still running.
        """
        dialog = getattr(self, "_progress_dialog", None)
        if dialog is None:
            dialog = ProgressDialog(self)
            self._progress_dialog = dialog
        return dialog

    def progress_monitor(self) -> ProgressDialog:
        """Public accessor for the reusable progress monitor.

        Lets the window (e.g. the status-bar background indicator) reopen the
        same monitor instance without touching the loading workflow.
        """
        return self._progress_monitor()

    def _on_family_finished(self, result) -> None:
        """The whole family (articles + details) is loaded in one pass:
        initialize engineering, publish to every workspace, then finish - the
        popup shows live progress throughout and auto-closes at the end."""
        reporter = self._family_reporter
        products = self._family_products
        family_name = self._family_name
        activity = getattr(self, "_family_activity", None)

        if not result.ok:
            reporter.log("error", result.message)
            reporter.finish(False, result.message)
            if activity is not None:
                activity.fail(result.message)
            QMessageBox.warning(self, "Load Family", result.message)
            self._finalize_load()
            return

        self._loaded_product = products[0]

        # Engineering Initialization (in-memory, one member per article).
        reporter.advance("Initializing Engineering")
        try:
            self._context.engineering_initialization_service.initialize(
                self._context.active_snapshot
            )
        except Exception as error:  # never let init break the load
            reporter.log("error", f"Engineering init: {error}")

        # Publish the COMPLETE snapshot + engineering to every workspace at once.
        reporter.advance("Finalizing Workspaces")
        self._refresh_display(products[0], 0.0, result.warnings)
        self.product_loaded.emit(f"Family: {family_name}")
        self.snapshot_published.emit()
        self.engineering_ready.emit()

        reporter.log("success", "Family loaded successfully")
        reporter.finish(True, "Family loaded successfully")
        if activity is not None:
            activity.update_items(processed=len(products), total=len(products))
            activity.complete("Family loaded successfully")
        self.load_complete.emit()
        self._finalize_load()

    def _on_family_load_failed(self, message: str) -> None:
        reporter = self._family_reporter
        reporter.log("error", message)
        reporter.finish(False, message)
        activity = getattr(self, "_family_activity", None)
        if activity is not None:
            activity.add_log(message, LogLevel.ERROR)
            activity.fail(message)
        QMessageBox.warning(self, "Load Family", message)
        self._finalize_load()

    def _finalize_load(self) -> None:
        """Release the run's ProgressReporter and its Activity bridge.

        Called at every terminal point of a load (Stage A failure, worker
        failure, Engineering Initialization success or failure). It disconnects
        the reporter's temporary consumers (the Activity bridge and the progress
        monitor) and schedules the reporter for deletion, so no reporter or
        bridge survives past its own operation. The Activity itself is retained
        by the ActivityService (intentional history) and is left untouched.
        """
        bridge = getattr(self, "_family_activity_bridge", None)
        if bridge is not None:
            bridge.disconnect()
        reporter = getattr(self, "_family_reporter", None)
        dialog = getattr(self, "_progress_dialog", None)
        if dialog is not None and reporter is not None:
            dialog.unbind_reporter(reporter)
        if reporter is not None:
            reporter.deleteLater()
        self._family_reporter = None
        self._family_activity = None
        self._family_activity_bridge = None
        self._engineering_reporter = None
        self._engineering_activity = None
        self._family_signals = None
        self._engineering_signals = None

    # -- active node highlighting -----------------------------------------
    def _highlight_active_node(self, product: Product) -> None:
        self._active_key = self._product_tree_key(product)
        self._reapply_active_highlight()

    def _reapply_active_highlight(self) -> None:
        from PySide6.QtGui import QBrush, QColor, QFont

        accent = QBrush(QColor("#2f6fed"))
        default = QBrush()
        for key, leaf in self._leaf_by_key.items():
            font = QFont(leaf.font(0))
            is_active = key == self._active_key
            font.setBold(is_active)
            leaf.setFont(0, font)
            leaf.setForeground(0, accent if is_active else default)
        active_leaf = (
            self._leaf_by_key.get(self._active_key) if self._active_key else None
        )
        if active_leaf is not None:
            parent = active_leaf.parent()
            while parent is not None:
                parent.setExpanded(True)
                parent = parent.parent()
            self._tree.scrollToItem(active_leaf)

    def _apply_active_style(self, leaf: QTreeWidgetItem) -> None:
        """Bold + accent a single leaf (the active one) - cheap, O(1)."""
        from PySide6.QtGui import QBrush, QColor, QFont

        font = QFont(leaf.font(0))
        font.setBold(True)
        leaf.setFont(0, font)
        leaf.setForeground(0, QBrush(QColor("#2f6fed")))

    def _clear_active_highlight(self) -> None:
        self._active_key = None
        self._reapply_active_highlight()

    # -- load / reload / clear --------------------------------------------
    def _on_load_product(self) -> None:
        product = self._selected_product()
        if product is None:
            self._search_status.setText("Select a product from the results first.")
            return
        self._do_load(product)

    def _on_reload_product(self) -> None:
        if self._loaded_product is not None:
            self._do_load(self._loaded_product)

    def _do_load(self, product: Product) -> None:
        # Load on a worker thread; a token ignores superseded loads.
        self._load_token += 1
        token = self._load_token
        self._pending_product = product
        self._set_actions_enabled(False)
        worker = _LoadWorker(
            self._context.pdm_service, product, token, self._load_signals
        )
        self._pool.start(worker)

    def _on_load_finished(self, token: int, payload) -> None:
        if token != self._load_token:
            return
        product, result, duration = payload
        self._set_actions_enabled(True)
        if not result.ok:
            QMessageBox.warning(self, "Load Product", result.message)
            return

        self._loaded_product = product
        # Initialize the Engineering model from the fully-loaded snapshot before
        # any workspace reacts to snapshot_changed. Created only via the context.
        self._context.engineering_initialization_service.initialize(
            self._context.active_snapshot
        )
        self._refresh_display(product, duration, result.warnings)
        self._highlight_active_node(product)
        self.product_loaded.emit(f"Product: {product.code} - {product.name}")
        self.snapshot_changed.emit()

    def _on_load_failed(self, token: int, message: str) -> None:
        if token != self._load_token:
            return
        self._set_actions_enabled(True)
        QMessageBox.warning(self, "Load Product", message)

    def _set_actions_enabled(self, enabled: bool) -> None:
        self._refresh_hierarchy_btn.setEnabled(enabled)

    def _on_clear_snapshot(self) -> None:
        self._context.snapshot_manager.clear_snapshot()
        self._loaded_product = None
        self._clear_active_highlight()
        self._reset_display()
        self.product_loaded.emit("No Product Selected")
        self.snapshot_changed.emit()

    # -- display -----------------------------------------------------------
    def _refresh_display(self, product, duration, warnings) -> None:
        self._info_name.setText(product.name or "-")
        self._info_code.setText(product.code or "-")
        self._info_category.setText(product.category or "-")
        self._info_catalogue.setText(product.description or "-")

    def _compute_readiness(self, snapshot) -> tuple[bool, str]:
        if snapshot is None or snapshot.product is None:
            return False, "No product loaded."
        if not snapshot.properties and not snapshot.options:
            return False, "No engineering data (properties or options) loaded."
        return True, "Required engineering data is present."

    def _reset_display(self) -> None:
        for label in (
            self._info_name,
            self._info_code,
            self._info_category,
            self._info_catalogue,
        ):
            label.setText("-")

    # -- readiness (for navigation checks) --------------------------------
    def is_snapshot_ready(self) -> bool:
        """Whether the active snapshot has the required engineering data."""
        ready, _reason = self._compute_readiness(self._context.active_snapshot)
        return ready

    def is_ready(self) -> bool:
        return self.is_snapshot_ready()