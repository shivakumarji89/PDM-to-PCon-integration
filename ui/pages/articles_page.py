"""Articles workspace page.

A snapshot-driven engineering *reduction* workbench: it separates each article
code into a common **Base Article** (the shared leading characters) and the
variable **Remaining Characters**, with a **Len** column showing each article's
base length. The base length is applied per *subset*: narrow the table with the
search box, set a base length, and click **Apply base length** to stamp it onto
the shown rows. Short/Long text are editable inline. All data comes from the
active snapshot (no database queries); edits update the in-memory members only.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.engines.filtering import text_match
from core.engines.status import warnings_text
from ui import theme
from ui.pages.base_page import BasePage
from ui.widgets.busy_popup import BusyPopup

# Column indices for the articles reduction table.
_COL_SOURCE = 0       # Source Article (full code, read-only)
_COL_LEN = 1          # Base length (narrow, read-only)
_COL_BASE = 2         # Base Article (derived prefix, read-only)
_COL_REMAINING = 3    # Remaining Characters (derived tail, read-only)
_COL_SHORT = 4        # Short Text (editable)
_COL_LONG = 5         # Long Text (editable)
_COL_RELATION = 6     # Relation Object (editable, default P_<base>)
_COL_SCHEME = 7       # Code Scheme (editable)
_COL_ORDER = 8        # Hidden natural-order sort key.


class ArticlesPage(BasePage):
    """Engineering reduction workspace for the active snapshot's articles."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Articles",
            description="Reduce articles: split base and remaining, edit reduced "
            "article and long text.",
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._rows: list[tuple] = []
        self._validation = None
        self._populating = False
        self._families: list = []
        self._active_family_id: str | None = None  # None = all families
        self._active_set_ids: frozenset[str] | None = None  # None = all sets
        self._filtered: list[tuple] = []  # rows currently shown
        self._base_len_by_member: dict[str, int] = {}  # member id -> base length
        self._set_len_by_ids: dict = {}  # set ids -> Class-Creation-derived length
        self._snapshot_key = None  # identity of the loaded snapshot (product change)
        self._auto_reduced_signature: object = object()  # last auto-reduced set lengths
        self._group_by_base = True  # collapse line items to one row per base
        self._syncing = False  # guard while programmatically syncing widgets

        # Debounce search typing: validation is snapshot-scoped
        # (term-independent), so coalesce keystrokes into one filter pass.
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(250)
        self._filter_timer.timeout.connect(self._apply_filter)

        self.add_content(self._build_body())

        self.refresh()

    # -- construction ------------------------------------------------------
    def _build_toolbar(self) -> QWidget:
        box = QGroupBox("Toolbar", self)
        layout = QHBoxLayout(box)

        self._search = QLineEdit(box)
        self._search.setPlaceholderText("Search code or description...")
        self._search.setClearButtonEnabled(True)
        self._search.setMinimumWidth(240)
        self._search.textChanged.connect(self._schedule_filter)
        layout.addWidget(self._search, 1)

        self._copy_long_btn = QPushButton("Copy Text", box)
        self._copy_long_btn.setToolTip(
            "Copy each shown article's Long Text into its Short Text."
        )
        self._copy_long_btn.clicked.connect(self._on_copy_long_to_short)
        layout.addWidget(self._copy_long_btn)

        self._components_btn = QPushButton("Filter Components", box)
        self._components_btn.setToolTip(
            "Exclude component / accessory / hardware ranges from the snapshot "
            "so every workspace shows the main product only."
        )
        self._components_btn.clicked.connect(self._on_filter_components)
        layout.addWidget(self._components_btn)

        self._clear_btn = QPushButton("Clear", box)
        self._clear_btn.setToolTip("Clear a field on the articles currently shown.")
        clear_menu = QMenu(self._clear_btn)
        clear_menu.addAction("Base Length", self._on_clear_length)
        clear_menu.addAction("Long Text", self._on_clear_long)
        clear_menu.addAction("Short Text", self._on_clear_short)
        self._clear_btn.setMenu(clear_menu)
        layout.addWidget(self._clear_btn)

        self._group_check = QCheckBox("Group by Base", box)
        self._group_check.setChecked(self._group_by_base)
        self._group_check.setToolTip(
            "Show one row per Base Article (the reduced prefix) instead of every "
            "line item. Text edits apply to all line items of the base."
        )
        self._group_check.toggled.connect(self._on_group_toggled)
        layout.addWidget(self._group_check)

        return box

    def _build_body(self) -> QWidget:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        top_row = QWidget(container)
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(self._build_family_panel(), 1)
        top_layout.addWidget(self._build_sets_panel(), 1)
        top_layout.addWidget(self._build_status_group(), 1)
        top_layout.addWidget(self._build_details_panel(), 1)

        layout.addWidget(top_row, 0)
        layout.addWidget(self._build_toolbar(), 0)
        layout.addWidget(self._build_table(), 1)
        return container

    def _build_family_panel(self) -> QWidget:
        box = QGroupBox("Families", self)
        layout = QVBoxLayout(box)
        self._family_list = QListWidget(box)
        self._family_list.setMinimumWidth(150)
        self._family_list.currentRowChanged.connect(self._on_family_changed)
        layout.addWidget(self._family_list)
        self._family_box = box
        return box

    def _build_sets_panel(self) -> QWidget:
        box = QGroupBox("Article Sets", self)
        layout = QVBoxLayout(box)
        self._sets_tree = QTreeWidget(box)
        self._sets_tree.setObjectName("articleSetsTree")
        self._sets_tree.setColumnCount(1)
        self._sets_tree.setHeaderLabels(["Article Set"])
        self._sets_tree.setRootIsDecorated(False)  # flat rows, no expand arrows
        self._sets_tree.setUniformRowHeights(True)
        self._sets_tree.setMinimumWidth(340)
        self._sets_tree.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._sets_tree.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self._sets_tree.setToolTip(
            "Distinct article sets by property structure. Select a set to view "
            "its full line items; the base length is driven by Class Creation."
        )
        header = self._sets_tree.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._sets_tree.itemSelectionChanged.connect(self._on_set_changed)
        layout.addWidget(self._sets_tree)
        return box

    def _populate_sets(self) -> None:
        """Fill the Article Sets table: one row per BASE MASTER (articles that
        share a base article number, merged across property structures) once the
        materialised article_sets exist, else the property-structure classes.
        Row 0 is "All sets"/Apply All. A master with an optional property (only
        some variants have it) is tagged in its label and tooltip.
        """
        self._syncing = True
        self._set_len_by_ids = {}
        tree = self._sets_tree
        tree.clear()
        snapshot = self._context.active_snapshot
        select_item = self._add_set_row(None, "All sets")
        for base, article_ids, base_len, prop_count, optional in self._set_rows(snapshot):
            ids = frozenset(str(a) for a in article_ids)
            label = (
                f"{base}: {len(article_ids)} articles \u2013 {prop_count} properties"
                + (f" ({len(optional)} optional)" if optional else "")
            )
            maxlen = self._set_max_code_len(snapshot, article_ids)
            self._set_len_by_ids[ids] = base_len or maxlen
            item = self._add_set_row(ids, label)
            if optional:
                item.setToolTip(
                    0, "Optional (only some variants): " + ", ".join(optional)
                )
            if self._active_set_ids is not None and ids == self._active_set_ids:
                select_item = item
        if select_item is tree.topLevelItem(0):
            self._active_set_ids = None
        tree.setCurrentItem(select_item)
        self._syncing = False

    def _set_rows(self, snapshot):
        """Yield (base, article_ids, base_length, property_count, optional) for
        each Article Sets row: base masters when the materialised article_sets
        exist (merge same-base classes), else the property-structure classes
        (base length falls back to the code length)."""
        if snapshot is None:
            return
        svc = self._context.engineering_reduction_service
        if getattr(snapshot, "article_sets", None):
            for m in svc.merge_sets_by_base(snapshot):
                yield (m.base or "Set", m.article_ids, m.base_length,
                       len(m.property_names), m.optional_property_names)
        else:
            for cls in svc.classify_by_properties(snapshot):
                prefix = self._set_prefix(snapshot, cls.article_ids) or "Set"
                yield (prefix, cls.article_ids, None, len(cls.property_names), ())

    def _add_set_row(self, ids, label: str):
        """Append one Article Sets row (label only). The base length comes from
        Class Creation; selecting the row shows the set's full line items."""
        item = QTreeWidgetItem(self._sets_tree, [label])
        item.setData(0, Qt.ItemDataRole.UserRole, ids)
        return item

    def _on_set_changed(self, *_args) -> None:
        """Select a set to view its FULL line items (ungrouped); 'All sets' shows
        the grouped overview. Base length is driven by Class Creation."""
        if self._syncing:
            return
        item = self._sets_tree.currentItem()
        self._active_set_ids = (
            item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        )
        group = self._active_set_ids is None  # specific set -> full line items
        if group != self._group_by_base:
            self._group_by_base = group
            self._group_check.blockSignals(True)
            self._group_check.setChecked(group)
            self._group_check.blockSignals(False)
        self._apply_filter()

    def _build_table(self) -> QWidget:
        self._table = QTableWidget(0, 9, self)
        self._table.setObjectName("articlesTable")
        self._table.setHorizontalHeaderLabels(
            ["Source Article", "Len", "Base Article", "Remaining",
             "Short Text", "Long Text", "Relation Object", "Code Scheme", ""]
        )
        self._table.setColumnHidden(_COL_ORDER, True)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(28)  # match tree rows app-wide
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self._table.setSortingEnabled(True)
        self._table.setMinimumHeight(280)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(_COL_SOURCE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_BASE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_REMAINING, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_LEN, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(_COL_SHORT, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(_COL_LONG, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(_COL_RELATION, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_SCHEME, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setColumnWidth(_COL_LEN, 48)
        self._table.itemSelectionChanged.connect(self._on_row_selected)
        self._table.itemChanged.connect(self._on_item_changed)
        return self._table

    def _build_details_panel(self) -> QWidget:
        box = QGroupBox("Article Details", self)
        form = QFormLayout(box)
        self._d_code = QLabel("-", box)
        self._d_description = QLabel("-", box)
        self._d_id = QLabel("-", box)
        self._d_status = QLabel("-", box)
        self._d_super = QLabel("-", box)
        self._d_source = QLabel("-", box)
        self._d_validation = QLabel("-", box)
        self._d_description.setWordWrap(True)

        form.addRow("Article Code:", self._d_code)
        form.addRow("Description:", self._d_description)
        form.addRow("Item ID:", self._d_id)
        form.addRow("Status:", self._d_status)
        form.addRow("Super Product:", self._d_super)
        form.addRow("Source:", self._d_source)
        form.addRow("Validation:", self._d_validation)
        self._details_box = box
        return box

    def _build_status_group(self) -> QWidget:
        box = QGroupBox("Workspace Status", self)
        form = QFormLayout(box)
        self._s_loaded = QLabel("0", box)
        self._s_selected = QLabel("0", box)
        self._s_validation = QLabel("-", box)
        self._s_warnings = QLabel("-", box)
        self._s_reduction = QLabel("-", box)
        self._s_readiness = QLabel("-", box)
        self._s_warnings.setWordWrap(True)
        self._s_reduction.setWordWrap(True)
        form.addRow("Loaded Articles:", self._s_loaded)
        form.addRow("Selected Articles:", self._s_selected)
        form.addRow("Validation Summary:", self._s_validation)
        form.addRow("Warnings:", self._s_warnings)
        form.addRow("Reduction:", self._s_reduction)
        form.addRow("Readiness:", self._s_readiness)
        return box

    # -- data / refresh ----------------------------------------------------
    def refresh(self) -> None:
        """Reload engineering members from the active snapshot and rebuild."""
        snapshot = self._context.active_snapshot
        key = snapshot.id if snapshot is not None else None
        if key != self._snapshot_key:
            # A different product is now active: drop the per-article base-length
            # overrides so this product starts from its own common prefix.
            self._snapshot_key = key
            self._base_len_by_member.clear()
            self._active_family_id = None
        self._rows = self._collect_rows()
        self._rebuild_family_list()
        self._populate_sets()
        # Reduce every set at its Class-Creation-derived base length so the
        # grouped list is ready without clicking Apply. Re-run whenever those
        # derived lengths change (e.g. the user toggled an Ignore box in Class
        # Creation) so the Length column tracks the current slicing; skip when
        # unchanged. Gate on the MATERIALISED article_sets (real base lengths).
        set_len_signature = frozenset(self._set_len_by_ids.items())
        if (
            snapshot is not None
            and getattr(snapshot, "article_sets", None)
            and set_len_signature != self._auto_reduced_signature
        ):
            self._auto_reduce_all_sets()
            self._auto_reduced_signature = set_len_signature
        self._apply_filter()

    def _collect_rows(self) -> list[tuple]:
        """Build (family, member, article) rows from the engineering hierarchy.

        The source article is resolved through the member service; when it
        cannot be resolved the article is ``None`` and its columns stay blank.
        """
        snapshot = self._context.active_snapshot
        engineering = snapshot.engineering if snapshot is not None else None
        families = list(engineering.families) if engineering is not None else []
        self._families = families
        member_service = self._context.engineering_member_service
        rows: list[tuple] = []
        for family in families:
            for member in family.members:
                article = member_service.get_article(snapshot, member)
                rows.append((family, member, article))
        return rows

    # -- family focus ------------------------------------------------------
    def _rebuild_family_list(self) -> None:
        """Rebuild the family selector (All Families + one row per family)."""
        self._syncing = True
        self._family_list.clear()
        total_members = sum(len(f.members) for f in self._families)
        all_item = QListWidgetItem(f"All Families ({total_members})")
        all_item.setData(Qt.ItemDataRole.UserRole, None)
        self._family_list.addItem(all_item)
        select_row = 0
        for index, family in enumerate(self._families, start=1):
            item = QListWidgetItem(f"{family.name} ({len(family.members)})")
            item.setData(Qt.ItemDataRole.UserRole, family.id)
            self._family_list.addItem(item)
            if family.id == self._active_family_id:
                select_row = index
        # The previously active family may no longer exist: fall back to All.
        if self._active_family_id is not None and select_row == 0:
            self._active_family_id = None
        # With a single family (the common case) focus it by default so the
        # base-length control is active instead of the disabled "All" state.
        if self._active_family_id is None and len(self._families) == 1:
            self._active_family_id = self._families[0].id
            select_row = 1
        self._family_list.setCurrentRow(select_row)
        # One family is the common case - hide the redundant selector.
        self._family_box.setVisible(len(self._families) > 1)
        self._syncing = False

    def _on_family_changed(self, *_args) -> None:
        if self._syncing:
            return
        item = self._family_list.currentItem()
        self._active_family_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        self._apply_filter()

    # -- base / remaining --------------------------------------------------
    @staticmethod
    def _longest_common_prefix(codes: list[str]) -> str:
        codes = [c for c in codes if c]
        if not codes:
            return ""
        prefix = codes[0]
        for code in codes[1:]:
            limit = min(len(prefix), len(code))
            index = 0
            while index < limit and prefix[index] == code[index]:
                index += 1
            prefix = prefix[:index]
            if not prefix:
                break
        return prefix

    def _all_codes(self) -> list[str]:
        return [
            article.code
            for _family, _member, article in self._rows
            if article is not None and article.code
        ]

    def _default_base_len(self) -> int:
        """Default base length = the full article code length (the longest code).

        Shorter codes are clamped per code, so every article starts fully in the
        base (remaining empty); the user trims the base down per subset.
        """
        codes = self._all_codes()
        return max((len(c) for c in codes), default=0)

    @staticmethod
    def _set_base_length(snapshot, article_ids) -> int | None:
        """A set's auto-derived base length from the materialised article-set
        table (code length minus the sum of its property widths); ``None`` when
        the set is not found."""
        if snapshot is None:
            return None
        target = frozenset(str(a) for a in article_ids)
        for aset in getattr(snapshot, "article_sets", None) or []:
            if frozenset(str(a) for a in aset.article_ids) == target:
                return aset.base_length
        return None

    @staticmethod
    def _set_max_code_len(snapshot, article_ids) -> int:
        """The longest article-code length in the set (spinbox upper bound)."""
        if snapshot is None:
            return 0
        code_of = {str(a.id): (a.code or "") for a in snapshot.articles}
        return max(
            (len(code_of.get(str(a), "")) for a in article_ids), default=0
        )

    @staticmethod
    def _set_prefix(snapshot, article_ids) -> str:
        """The longest article-code prefix common to every article in the set -
        the natural 'shortened article' shown for the set (uncapped)."""
        if snapshot is None:
            return ""
        code_of = {str(a.id): (a.code or "") for a in snapshot.articles}
        codes = [c for c in (code_of.get(str(a), "") for a in article_ids) if c]
        if not codes:
            return ""
        prefix = codes[0]
        for code in codes[1:]:
            limit = min(len(prefix), len(code))
            i = 0
            while i < limit and prefix[i] == code[i]:
                i += 1
            prefix = prefix[:i]
            if not prefix:
                break
        return prefix

    def _applied_length(self, member) -> int | None:
        """A member's applied base length: the in-memory override, else the
        persisted ``reduced_article`` length; ``None`` when not applied."""
        mid = getattr(member, "id", "")
        if mid in self._base_len_by_member:
            return self._base_len_by_member[mid]
        reduced = getattr(member, "reduced_article", "") or ""
        return len(reduced) if reduced else None

    @staticmethod
    def _split_base(code: str, length: int) -> tuple[str, str]:
        length = max(0, min(length, len(code)))
        return code[:length], code[length:]

    def _apply_set(self, article_ids, value: int, refresh: bool = True, busy=None) -> None:
        """Reduce a set: stamp the base length, mark selected and store the
        reduced base for every article in the set (regardless of the current
        filter). ``article_ids=None`` applies to every shown load row.
        """
        id_set = {str(a) for a in article_ids} if article_ids is not None else None
        article_service = self._context.article_service
        member_service = self._context.engineering_member_service
        for _family, member, article in self._rows:
            if article is None:
                continue
            if id_set is not None and str(article.id) not in id_set:
                continue
            mid = getattr(member, "id", "")
            if mid:
                self._base_len_by_member[mid] = value
            article_service.set_selected(article, True)
            # Persist the split so it survives save/reload and feeds Class
            # Creation slicing (reduced_article = base; remaining = the rest).
            base, _remaining = self._split_base(article.code, value)
            member_service.set_reduced_article(member, base)
        if busy is not None:
            busy.update_status("Grouping articles...")
        if refresh:
            self._apply_filter()

    def _auto_reduce_all_sets(self) -> None:
        """Reduce every set at its Class-Creation-derived base length so the
        grouped list is ready the moment the workflow opens."""
        for ids, length in self._set_len_by_ids.items():
            self._apply_set(ids, length, refresh=False)

    def _effective_long_text(self, member, article) -> str:
        """The Long Text shown for a member: override, else the generic
        product-TYPE name (same as Short - the full permutation is too detailed),
        else the article's own name."""
        type_name = (
            self._context.product_type_name(article.product_id)
            if article is not None else ""
        )
        return member.long_description or type_name or (
            article.name if article is not None else ""
        )

    def _on_copy_long_to_short(self) -> None:
        """Copy each shown article's Long Text into its Short Text."""
        service = self._context.engineering_member_service
        for _family, member, article in self._filtered:
            service.set_short_description(
                member, self._effective_long_text(member, article)
            )
        self._apply_filter()

    def _on_filter_components(self) -> None:
        """Tick ProductRanges to exclude (components / accessories / hardware).

        Excluded ranges are held aside, not deleted, so every workspace shows
        the main product only while unticking restores a range with no reload.
        """
        snapshot = self._context.active_snapshot
        if snapshot is None:
            return
        # Work off the full pre-exclusion baseline (if any) so already-excluded
        # ranges still appear - ticked - and can be restored.
        base = getattr(snapshot, "exclusion_baseline", None)
        product_range = (base["product_range"] if base
                         else getattr(snapshot, "product_range", None)) or {}
        articles = base["articles"] if base else snapshot.articles
        if not product_range:
            return
        counts: dict[str, int] = {}
        for article in articles:
            rng = product_range.get(str(getattr(article, "product_id", "") or ""))
            if rng:
                counts[rng] = counts.get(rng, 0) + 1
        ranges = sorted(counts) or sorted(set(product_range.values()))
        if len(ranges) < 2:
            return  # single range: nothing to separate out
        excluded = set(getattr(snapshot, "ignored_ranges", None) or [])

        dialog = QDialog(self)
        dialog.setWindowTitle("Filter Components / Accessories")
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel(
            "Tick the ranges to EXCLUDE (components, accessories, hardware).\n"
            "They are held aside so only the main product remains \u2013 untick "
            "to bring a range back (no reload)."
        ))
        listw = QListWidget(dialog)
        for rng in ranges:
            n = counts.get(rng, 0)
            item = QListWidgetItem(f"{rng}  ({n} articles)" if n else rng)
            item.setData(Qt.ItemDataRole.UserRole, rng)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if rng in excluded
                else Qt.CheckState.Unchecked
            )
            listw.addItem(item)
        layout.addWidget(listw)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        chosen = {
            listw.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(listw.count())
            if listw.item(i).checkState() == Qt.CheckState.Checked
        }
        if chosen == excluded:
            return
        with BusyPopup("Applying exclusions", self):
            self._context.pdm_service.set_excluded_ranges(snapshot, chosen)
        # Force the reduced view to rebuild for the new active set.
        self._auto_reduced_signature = object()
        self.refresh()

    # -- filtering / populate ---------------------------------------------
    def _schedule_filter(self, *_args) -> None:
        """Debounce search typing so the snapshot-scoped validation runs once the
        user pauses, not on every keystroke."""
        self._filter_timer.start()

    def _apply_filter(self, *_args) -> None:
        self._validation = self._context.article_service.validate()
        term = self._search.text().strip().lower()

        filtered: list[tuple] = []
        for family, member, article in self._rows:
            if self._active_family_id is not None and (
                family is None or family.id != self._active_family_id
            ):
                continue
            if self._active_set_ids is not None and (
                article is None or str(article.id) not in self._active_set_ids
            ):
                continue
            code = article.code if article is not None else ""
            description = article.description if article is not None else ""
            if not text_match(term, code, description):
                continue
            filtered.append((family, member, article))

        self._filtered = filtered
        self._populate(filtered)
        self._update_status()

    @staticmethod
    def _set_readonly(item: QTableWidgetItem) -> None:
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

    def _populate(self, rows: list[tuple]) -> None:
        self._populating = True
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        if self._group_by_base:
            self._populate_grouped(rows)
            self._table.setSortingEnabled(True)
            self._table.sortByColumn(_COL_ORDER, Qt.SortOrder.AscendingOrder)
            self._populating = False
            return
        self._table.setHorizontalHeaderLabels(
            ["Source Article", "Len", "Base Article", "Remaining",
             "Short Text", "Long Text", "Relation Object", "Code Scheme", ""]
        )
        self._table.setColumnHidden(_COL_REMAINING, False)
        default_len = self._default_base_len()
        for order, (family, member, article) in enumerate(rows):
            row = self._table.rowCount()
            self._table.insertRow(row)

            code = article.code if article is not None else ""
            applied = self._applied_length(member)
            has_length = applied is not None
            length = applied if applied is not None else default_len
            base, remaining = self._split_base(code, length)

            source_item = QTableWidgetItem(code)
            source_item.setData(Qt.ItemDataRole.UserRole, (family, member, article))
            self._set_readonly(source_item)
            self._table.setItem(row, _COL_SOURCE, source_item)

            base_item = QTableWidgetItem(base)
            self._set_readonly(base_item)
            self._table.setItem(row, _COL_BASE, base_item)

            remaining_item = QTableWidgetItem(remaining)
            self._set_readonly(remaining_item)
            self._table.setItem(row, _COL_REMAINING, remaining_item)

            len_item = QTableWidgetItem()
            # Empty until a base length is actually applied to this member, so an
            # empty Len cell always means "not applied" (including after Clear).
            if has_length:
                len_item.setData(Qt.ItemDataRole.DisplayRole, len(base))
            len_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._set_readonly(len_item)
            self._table.setItem(row, _COL_LEN, len_item)

            # Editable: short text defaults to the generic product-TYPE name
            # (product name up to the first '/', e.g. 'Always Chair') so the
            # shortened article reads generically, not the full permutation; the
            # user's override (member.short_description) wins when present.
            short_default = member.short_description or (
                self._context.product_type_name(article.product_id)
                if article is not None else ""
            ) or (article.description if article is not None else "")
            self._table.setItem(row, _COL_SHORT, QTableWidgetItem(short_default))

            # Editable: long text defaults to the article's product name (from
            # the shared product registry), falling back to the article's own
            # name; the user's override (member.long_description) wins.
            long_default = self._effective_long_text(member, article)
            self._table.setItem(row, _COL_LONG, QTableWidgetItem(long_default))

            # Editable: relation object defaults to P_<base>; the user's
            # override (member.relation_object) wins when present.
            relation_default = member.relation_object or (f"P_{base}" if base else "")
            self._table.setItem(row, _COL_RELATION, QTableWidgetItem(relation_default))

            # Code Scheme defaults to the base article; a saved override wins.
            self._table.setItem(
                row, _COL_SCHEME, QTableWidgetItem(member.code_scheme or base)
            )

            order_item = QTableWidgetItem()
            order_item.setData(Qt.ItemDataRole.DisplayRole, order)
            self._set_readonly(order_item)
            self._table.setItem(row, _COL_ORDER, order_item)
        self._table.setSortingEnabled(True)
        self._table.sortByColumn(_COL_ORDER, Qt.SortOrder.AscendingOrder)
        self._populating = False

    def _populate_grouped(self, rows: list[tuple]) -> None:
        """One row per Base Article (the reduced prefix): line-item count +
        distinct variants, with per-base text/relation applying to all members."""
        self._table.setHorizontalHeaderLabels(
            ["Base Article", "Length", "Variants", "",
             "Short Text", "Long Text", "Relation Object", "Code Scheme", ""]
        )
        # Grouped view has no per-line "Remaining"; hide that column here.
        self._table.setColumnHidden(_COL_REMAINING, True)
        default_len = self._default_base_len()
        groups: dict[str, dict] = {}
        order_keys: list[str] = []
        for family, member, article in rows:
            code = article.code if article is not None else ""
            base, remaining = self._split_base(
                code, self._applied_length(member) or default_len
            )
            group = groups.get(base)
            if group is None:
                group = {"members": [], "remainders": set(),
                         "rep": (family, member, article)}
                groups[base] = group
                order_keys.append(base)
            group["members"].append(member)
            if remaining:
                group["remainders"].add(remaining)
        for order, base in enumerate(order_keys):
            group = groups[base]
            members = group["members"]
            family, rep_member, rep_article = group["rep"]
            row = self._table.rowCount()
            self._table.insertRow(row)

            base_item = QTableWidgetItem(base)
            base_item.setData(
                Qt.ItemDataRole.UserRole,
                ("__base__", base, tuple(members), family),
            )
            self._set_readonly(base_item)
            self._table.setItem(row, _COL_SOURCE, base_item)

            count_item = QTableWidgetItem()
            count_item.setData(Qt.ItemDataRole.DisplayRole, len(base))
            count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._set_readonly(count_item)
            self._table.setItem(row, _COL_LEN, count_item)

            variants_item = QTableWidgetItem()
            variants_item.setData(Qt.ItemDataRole.DisplayRole, len(group["remainders"]))
            variants_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._set_readonly(variants_item)
            self._table.setItem(row, _COL_BASE, variants_item)

            blank = QTableWidgetItem("")
            self._set_readonly(blank)
            self._table.setItem(row, _COL_REMAINING, blank)

            short_default = rep_member.short_description or (
                rep_article.description if rep_article is not None else ""
            )
            self._table.setItem(row, _COL_SHORT, QTableWidgetItem(short_default))
            self._table.setItem(
                row, _COL_LONG,
                QTableWidgetItem(self._effective_long_text(rep_member, rep_article)),
            )
            self._table.setItem(
                row, _COL_RELATION,
                QTableWidgetItem(
                    rep_member.relation_object or (f"P_{base}" if base else "")
                ),
            )
            self._table.setItem(
                row, _COL_SCHEME, QTableWidgetItem(rep_member.code_scheme or base)
            )

            order_item = QTableWidgetItem()
            order_item.setData(Qt.ItemDataRole.DisplayRole, order)
            self._set_readonly(order_item)
            self._table.setItem(row, _COL_ORDER, order_item)

    def _on_group_toggled(self, checked: bool) -> None:
        self._group_by_base = checked
        self._apply_filter()

    def _update_base_details(self, record) -> None:
        _marker, base, members, _family = record
        snapshot = self._context.active_snapshot
        # Map once (avoids an O(n) article scan per member across the base).
        by_id = {a.id: a for a in (snapshot.articles if snapshot else [])}
        articles = [by_id.get(m.article_id) for m in members]
        articles = [a for a in articles if a is not None]
        statuses = {(a.status or "").strip() for a in articles if (a.status or "").strip()}
        product = snapshot.product if snapshot else None
        self._d_code.setText(base or "-")
        self._d_description.setText(f"{len(members)} line item(s) under this base")
        self._d_id.setText("-")
        self._d_status.setText(
            next(iter(statuses)) if len(statuses) == 1
            else ("Mixed" if statuses else "-")
        )
        self._d_super.setText(
            "Yes" if (product and getattr(product, "is_super_product", False)) else "No"
        )
        self._d_source.setText("Base Article")
        self._d_validation.setText("OK")

    # -- editing -----------------------------------------------------------
    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._populating:
            return
        column = item.column()
        if column not in (_COL_SHORT, _COL_LONG, _COL_RELATION, _COL_SCHEME):
            return
        source = self._table.item(item.row(), _COL_SOURCE)
        record = source.data(Qt.ItemDataRole.UserRole) if source else None
        if not record:
            return
        text = item.text()
        service = self._context.engineering_member_service
        # Grouped base row edits apply to every line item under the base.
        members = list(record[2]) if record[0] == "__base__" else [record[1]]
        for member in members:
            if column == _COL_SHORT:
                service.set_short_description(member, text)
            elif column == _COL_LONG:
                service.set_long_description(member, text)
            elif column == _COL_RELATION:
                service.set_relation_object(member, text)
            else:
                service.set_code_scheme(member, text)

    # -- clear (per shown subset) ------------------------------------------
    def _on_clear_length(self) -> None:
        """Remove the base-length override on the shown rows (revert to full)."""
        member_service = self._context.engineering_member_service
        for _family, member, _article in self._filtered:
            self._base_len_by_member.pop(getattr(member, "id", ""), None)
            member_service.set_reduced_article(member, "")
        self._apply_filter()

    def _on_clear_long(self) -> None:
        """Clear the Long Text modification on the shown rows (revert to the
        default product name, not blank)."""
        service = self._context.engineering_member_service
        for _family, member, _article in self._filtered:
            service.set_long_description(member, "")
        self._apply_filter()

    def _on_clear_short(self) -> None:
        """Clear the Short Text override on the shown rows (revert to default)."""
        service = self._context.engineering_member_service
        for _family, member, _article in self._filtered:
            service.set_short_description(member, "")
        self._apply_filter()

    # -- details -----------------------------------------------------------
    def _on_row_selected(self) -> None:
        if self._populating:
            return
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        item = self._table.item(rows[0].row(), _COL_SOURCE)
        record = item.data(Qt.ItemDataRole.UserRole) if item else None
        if not record:
            return
        self._details_box.setVisible(True)
        if record[0] == "__base__":
            self._update_base_details(record)
            return
        family, member, article = record
        self._update_details(family, member, article)

    def _update_details(self, family, member, article) -> None:
        self._d_code.setText((article.code if article else "") or "-")
        self._d_description.setText((article.description if article else "") or "-")
        self._d_id.setText((str(article.id) if article and article.id else "") or "-")
        self._d_status.setText((article.status if article else "") or "-")
        snapshot = self._context.active_snapshot
        product = snapshot.product if snapshot else None
        self._d_super.setText(
            "Yes" if (product and getattr(product, "is_super_product", False)) else "No"
        )
        self._d_source.setText((article.source if article else "") or "-")
        issues = self._validation.issues_for(article) if (self._validation and article) else []
        self._d_validation.setText("; ".join(issues) if issues else "OK")

    # -- status ------------------------------------------------------------
    def _update_status(self) -> None:
        # Reuse the validation _apply_filter just computed (it runs immediately
        # before this) instead of validating the snapshot a second time.
        validation = self._validation
        if validation is None:
            validation = self._context.article_service.validate()
            self._validation = validation
        self._s_loaded.setText(str(validation.total))
        self._s_selected.setText(str(validation.selected))
        if validation.total == 0:
            self._s_validation.setText("No articles to validate.")
            self._s_readiness.setText("Load a product to review articles.")
        else:
            self._s_validation.setText(
                "OK" if validation.ok else f"{len(validation.warnings)} issue group(s)"
            )
            self._s_readiness.setText("Articles reviewed - ready to continue to Properties.")
        text = warnings_text(validation)
        self._s_warnings.setText(text if text and text != "None" else "None")
        self._apply_reduction_status()
        # Article Details is shown only when a row is selected.
        self._details_box.setVisible(False)

    def _reduction_warning(self) -> str:
        """Warn when the shown reduced set won't slice consistently.

        The '.' delimiter check applies in BOTH views (some bases ending at '.'
        while others keep characters after it is a real misalignment). The
        mixed-length / multiple-series checks apply only in line-item view, since
        grouping already separates series into their own base rows."""
        applied = [
            (article.code, self._applied_length(member))
            for _family, member, article in self._filtered
            if article is not None and article.code
            and self._applied_length(member) is not None
        ]
        if len(applied) < 2:
            return ""
        bases = [self._split_base(code, n)[0] for code, n in applied]
        dot = self._dot_boundary_warning(bases)
        if dot:
            return dot
        if self._group_by_base:
            return ""
        lengths = {n for _code, n in applied}
        if len(lengths) > 1:
            shown = ", ".join(str(n) for n in sorted(lengths))
            return (
                f"Mixed base lengths in the shown set ({shown}) - these won't "
                "slice consistently; reduce each series separately."
            )
        length = lengths.pop()
        lcp = len(self._longest_common_prefix([code for code, _n in applied]))
        if length > lcp:
            return (
                f"Base length {length} exceeds the shared prefix ({lcp}) - the "
                "shown set spans multiple series; reduce each series separately."
            )
        return ""

    @staticmethod
    def _dot_boundary_warning(bases: list[str]) -> str:
        """Flag inconsistent reduction at the '.' delimiter: some bases end at
        '.' while others keep characters after it."""
        tails = {b.rsplit(".", 1)[1] for b in bases if "." in b}
        if "" in tails and any(tails):
            return (
                "Inconsistent base at the '.' delimiter: some bases end at '.' "
                "while others keep characters after it - align the base length "
                "to the '.'."
            )
        return ""

    def _apply_reduction_status(self) -> None:
        warning = self._reduction_warning()
        if warning:
            self._s_reduction.setText(f"\u26A0 {warning}")
            self._s_reduction.setStyleSheet(f"color: {theme.COLOR_WARNING};")
        else:
            self._s_reduction.setText("Consistent")
            self._s_reduction.setStyleSheet(f"color: {theme.COLOR_OK};")

    # -- lifecycle ---------------------------------------------------------
    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        self.refresh()

    def is_ready(self) -> bool:
        snapshot = self._context.active_snapshot
        return snapshot is not None and snapshot.product is not None
