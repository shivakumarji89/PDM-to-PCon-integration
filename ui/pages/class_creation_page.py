"""Class Creation workspace page.

The OCD *property-class* creation surface, unifying what used to be four
separate workspaces into three stacked cards:

* **Attributes** - PDM-fetched properties and their values. Assign each value's
  order-code letter (``code``) and select the values.
* **Options** - PDM-fetched options listed by NAME only (option-level select);
  the list is large and option order codes are standard, not edited here.
* **Visual / Misc** - engineered property definitions the user creates by simply
  typing a name into the trailing add-row (no buttons); rename inline, remove
  with Delete.

Each module is its own titled card (matching the app's card design), so the
three are clearly separated.

Data stays SEPARATE underneath: Attributes/Options read PDM source (only the
value ``code``/selection, which already live on the values, are edited), while
Visual/Misc writes ONLY the engineering vocabulary
(``snapshot.engineering.properties``) via ``engineering_property_service``. This
preserves the Builder Table's distinct inputs and downstream OCD parity.

The page is additive: the legacy pages are untouched, so it can be tested
alongside them before they are retired. It reads/writes only the active
snapshot (no database access).
"""
from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QSplitter,
    QStackedWidget,
    QWidget,
)

from core.engines.filtering import text_match
from core.modules import WorkbenchModule
from services.engineering.engineering_reduction_service import (
    collapse_duplicate_values,
)
from ui import theme
from ui.pages.base_page import BasePage
from ui.widgets.data_table import standardize_table

# Tree columns.
_COL_NAME = 0       # property/option/definition name, or value text
_COL_CODE = 1       # code / key / type
_COL_SELECTED = 2   # selection checkbox
_COL_SLICED = 3     # Sliced status indicator
_COL_TYPE = 4       # Type dropdown (property rows only: C/L/N/T)
_COL_USAGE = 5      # Usage dropdown (Configuration | Graphic)
_COL_TEXTBLOCK = 6  # Text-block (display key)
_COL_RELATION = 7   # Relation Object name
_COL_IGNORE = 8     # Ignore checkbox (keep property in the base, don't slice)

# Node kinds (stored in UserRole) so edits route to the right service.
_KIND_GROUP = "group"                 # functional-group header (ProductCategory)
_KIND_PROP_VALUE = "property_value"   # attribute value row (name + editable code)
_KIND_PROP = "property"               # attribute property node (editable slice width)
_KIND_OPTION = "option"               # option row (name only, option-level select)
_KIND_DEFINITION = "definition"       # engineered PropertyDefinition row
_KIND_ADD = "add"                     # the trailing "type to add" row
_KIND_CLASS_PROP = "class_property"   # a property assigned to a class (editable width)
_KIND_CLASS_VALUE = "class_value"     # a code->value row under a class property
_KIND_CLASS_VALUE_ADD = "class_value_add"  # trailing "type a code to add value" row

_ADD_VALUE_HINT = "+ add value (code)"

_ADD_HINT = "Type to add a property..."

# Type dropdown options for properties: (code, description)
_TYPE_OPTIONS = [
    ("", ""),
    ("C", "Character"),
    ("L", "Length"),
    ("N", "Number"),
    ("T", "Text"),
]

# Usage dropdown options for properties (MDB Usage column).
_USAGE_OPTIONS = ["", "Configuration", "Graphic"]


def _by_display_order(values):
    """Values ordered by ``display_order``; unordered ones keep insertion order."""
    return sorted(values, key=lambda v: (
        getattr(v, "display_order", None) is None,
        getattr(v, "display_order", 0) or 0,
    ))


class _NameOrCodeDelegate(QStyledItemDelegate):
    """Restrict in-place editing to the columns each row allows.

    A row declares which columns it allows via a set stored in
    ``Qt.UserRole + 1`` (value rows allow only Code; definition/add rows allow
    only Name). Value rows that have discovered codes use an embedded combo box
    instead (see the page), so they are not editor-driven here.
    """

    def createEditor(self, parent, option, index):  # noqa: N802 (Qt override)
        editable = index.data(Qt.ItemDataRole.UserRole + 1)
        if not editable or index.column() not in editable:
            return None
        return super().createEditor(parent, option, index)

    def sizeHint(self, option, index):  # noqa: N802 (Qt override)
        # Consistent row height across all three trees (fits the 26px combos).
        size = super().sizeHint(option, index)
        size.setHeight(max(size.height(), 28))
        return size


class _DeletableTree(QTreeWidget):
    """Tree that removes the current row on Delete via an injected callback."""

    def __init__(self, on_delete, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._on_delete = on_delete

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            item = self.currentItem()
            if item is not None and self._on_delete(item):
                return
        super().keyPressEvent(event)


class _CollapsibleCard(QGroupBox):
    """A standard group-box card that collapses to just its title bar.

    Keeps the app's card look (titled, bordered) but is checkable: unchecking
    the title hides the content so tall, few-column tables can reclaim vertical
    space. The inherited :attr:`toggled` signal lets the page redistribute
    layout stretch.
    """

    def __init__(self, title: str, content: QWidget, parent: QWidget | None = None):
        super().__init__(title, parent)
        self.setObjectName("classCreationCard")
        self.setCheckable(False)
        self.setFont(theme.font("card_title"))
        # Give Attribute / Options / Visual a distinct card surface instead of
        # making the class name look like a raw tree heading.
        self.setStyleSheet(
            f"""
            QGroupBox#classCreationCard {{
                border: 1px solid {theme.LINE};
                border-radius: {theme.RADIUS_LG}px;
                margin-top: 14px;
                background: {theme.SURFACE};
            }}
            QGroupBox#classCreationCard::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 7px;
                color: {theme.INK};
                font-weight: 600;
            }}
            QGroupBox#classCreationCard::title {{
                color: {theme.INK};
            }}
            """
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(theme.GROUP_PADDING, theme.GROUP_PADDING,
                                  theme.GROUP_PADDING, theme.GROUP_PADDING)
        self._content = content
        layout.addWidget(content, 1)
        # Hide/show the content when the title is toggled (collapse / expand).
        self.toggled.connect(self._content.setVisible)

    def is_expanded(self) -> bool:
        return self.isChecked()

    def set_expanded(self, expanded: bool) -> None:
        self.setChecked(expanded)



class ClassCreationPage(BasePage):
    """Unified Attributes + Options + Visual/Misc class-creation workspace."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Class Creation",
            description=(
                "Assign order-code letters, select property & option values, "
                "and create visual/misc properties."
            ),
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._populating = False
        self._active_class_id: str | None = None
        self._cards: list[_CollapsibleCard] = []
        # Active class group whose cards are shown (empty = the flat category).
        self._active_group_name: str = ""
        # Properties whose value codes the user has hand-edited: their cells stay
        # editable so a second edit is never locked out (reset per snapshot).
        self._user_edited_props: set[str] = set()
        self._edited_snap_id: int | None = None
        self._selected_attr_prop = None
        self._selected_attr_value = None

        self.add_content(self._build_toolbar())
        self.add_content(self._build_body())
        self.refresh()

    # -- construction ------------------------------------------------------
    def _build_toolbar(self) -> QWidget:
        box = QGroupBox("Toolbar", self)
        layout = QHBoxLayout(box)

        self._search = QLineEdit(box)
        self._search.setPlaceholderText("Search attributes, options or values...")
        self._search.setClearButtonEnabled(True)
        self._search.setMaximumWidth(320)
        self._search.textChanged.connect(self._apply_filter)
        layout.addWidget(self._search)

        # Split the classes into one group per product range (desk / screen /
        # wire management). Off = the historical flat <Category>_* classes.
        self._split_cb = QCheckBox("Split by group", box)
        self._split_cb.setToolTip(
            "Create a separate class set per product range instead of one flat "
            "set - scopes each group to the properties and values it carries."
        )
        self._split_cb.toggled.connect(self._on_split_toggled)
        layout.addWidget(self._split_cb)

        # How the split groups are formed: by PDM product range, or by article
        # set (base article). Visible only when the split is on.
        self._basis_combo = QComboBox(box)
        self._basis_combo.addItem("by Product range", "range")
        self._basis_combo.addItem("by Article set", "article_set")
        self._basis_combo.setToolTip(
            "Group basis: one class set per PDM product range, or one per "
            "article set (base article)."
        )
        self._basis_combo.currentIndexChanged.connect(self._on_basis_changed)
        self._basis_combo.setVisible(False)
        layout.addWidget(self._basis_combo)

        # Active group whose classes the cards below show (only when split on).
        self._group_combo = QComboBox(box)
        self._group_combo.setMinimumWidth(160)
        self._group_combo.setToolTip("The class group shown in the cards below.")
        self._group_combo.currentIndexChanged.connect(self._on_group_changed)
        self._group_combo.setVisible(False)
        layout.addWidget(self._group_combo)

        # Development Class Creation controls. These are deliberately visible
        # instead of being available only through a context menu so the
        # authoritative property/value editing workflow is discoverable.
        self._move_up_btn = QPushButton("Move Up", box)
        self._move_up_btn.clicked.connect(lambda: self._move_selected_attr_property(-1))
        self._move_up_btn.setEnabled(False)
        layout.addWidget(self._move_up_btn)

        self._move_down_btn = QPushButton("Move Down", box)
        self._move_down_btn.clicked.connect(lambda: self._move_selected_attr_property(1))
        self._move_down_btn.setEnabled(False)
        layout.addWidget(self._move_down_btn)

        self._remove_value_btn = QPushButton("Remove Value", box)
        self._remove_value_btn.clicked.connect(self._remove_selected_attr_value)
        self._remove_value_btn.setEnabled(False)
        layout.addWidget(self._remove_value_btn)

        # Amber hint shown when configuration codes were inferred (read-only
        # guesses the user must confirm before generation).
        self._inferred_hint = QLabel("", box)
        self._inferred_hint.setObjectName("inferredHint")
        self._inferred_hint.setStyleSheet("color: #b8860b; font-weight: 600;")
        self._inferred_hint.setVisible(False)
        layout.addWidget(self._inferred_hint)

        layout.addStretch(1)

        self._auto_btn = QPushButton("Resolve remaining", box)
        self._auto_btn.setToolTip(
            "Jump to the next configuration attribute the automation could not "
            "code and start editing it; assign a code and the automation "
            "continues until none remain."
        )
        self._auto_btn.clicked.connect(self._on_resolve_remaining)
        layout.addWidget(self._auto_btn)

        separator = QFrame(box)
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        self._expand_btn = QPushButton("Expand All", box)
        self._expand_btn.clicked.connect(self._expand_all)
        layout.addWidget(self._expand_btn)

        self._collapse_btn = QPushButton("Collapse All", box)
        self._collapse_btn.clicked.connect(self._collapse_all)
        layout.addWidget(self._collapse_btn)

        return box

    def _build_body(self) -> QWidget:
        container = QWidget(self)
        self._body_layout = QVBoxLayout(container)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(theme.SECTION_SPACING)

        # Class Creation has three functional workspaces. Keep them as explicit
        # cards, but show one workspace at a time so the user gets the full area
        # for the task instead of three compressed tables stacked vertically.
        self._workspace_nav = QHBoxLayout()
        self._workspace_nav.setSpacing(theme.CONTROL_SPACING)
        self._workspace_buttons = []
        for index, (label, subtitle) in enumerate((
            ("ATTRIBUTE", "Properties & values"),
            ("OPTIONS", "Class options"),
            ("VISUAL", "Engineering properties"),
        )):
            button = QPushButton(label)
            button.setToolTip(subtitle)
            button.setCheckable(True)
            button.setMinimumHeight(42)
            button.setObjectName("classCreationWorkspaceButton")
            button.setStyleSheet(
                f"""
                QPushButton#classCreationWorkspaceButton {{
                    border: 1px solid {theme.LINE};
                    border-radius: {theme.RADIUS_MD}px;
                    background: {theme.SURFACE};
                    color: {theme.INK_SOFT};
                    font-weight: 600;
                    padding: 8px 12px;
                    text-align: center;
                }}
                QPushButton#classCreationWorkspaceButton:hover {{
                    border-color: {theme.LINE_STRONG};
                    background: {theme.SURFACE_ALT};
                }}
                QPushButton#classCreationWorkspaceButton:checked {{
                    border: 2px solid {theme.ACCENT};
                    background: {theme.ACCENT_SOFT};
                    color: {theme.ACCENT_DARK};
                }}
                """
            )
            button.clicked.connect(lambda checked, i=index: self._select_workspace(i))
            self._workspace_buttons.append(button)
            self._workspace_nav.addWidget(button, 1)
        self._body_layout.addLayout(self._workspace_nav)

        self._workspace_stack = QStackedWidget(self)
        self._workspace_stack.setObjectName("classCreationWorkspaceStack")
        cards = (
            self._build_attributes_card(),
            self._build_options_card(),
            self._build_visual_card(),
        )
        for card in cards:
            self._cards.append(card)
            # The card itself is the visible workspace surface. Its checkable
            # title is disabled because workspace selection is handled above.
            card.setCheckable(False)
            self._workspace_stack.addWidget(card)
        self._body_layout.addWidget(self._workspace_stack, 1)
        self._select_workspace(0)
        return container

    def _select_workspace(self, index: int) -> None:
        if not self._workspace_buttons or not self._workspace_stack:
            return
        index = max(0, min(index, len(self._workspace_buttons) - 1))
        self._workspace_stack.setCurrentIndex(index)
        for i, button in enumerate(self._workspace_buttons):
            button.setChecked(i == index)
            button.setProperty("active", i == index)
            button.style().unpolish(button)
            button.style().polish(button)
        # Keep the toolbar relevant to the Attribute workspace. Options and
        # Visual retain their own direct editing/context actions.
        attribute = index == 0
        for widget in (
            self._move_up_btn, self._move_down_btn, self._remove_value_btn,
            self._auto_btn,
        ):
            widget.setVisible(attribute)
        self._inferred_hint.setVisible(attribute and self._inferred_hint.text() != "")

    def _rebalance_cards(self, *_args) -> None:
        # Retained as a compatibility hook for existing callers; the workspace
        # stack now gives the selected card all available vertical space.
        if hasattr(self, "_workspace_stack"):
            self._workspace_stack.updateGeometry()

    def _expand_all(self) -> None:
        for tree in (self._attr_tree, self._opt_tree, self._misc_tree):
            tree.expandAll()

    def _collapse_all(self) -> None:
        for tree in (self._attr_tree, self._opt_tree, self._misc_tree):
            tree.collapseAll()

    def _configure_tree(self, tree: QTreeWidget, headers: list[str]) -> None:
        tree.setColumnCount(3)
        tree.setHeaderLabels(headers)
        tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        tree.setUniformRowHeights(True)
        tree.setItemDelegate(_NameOrCodeDelegate(tree))
        tree.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        header = tree.header()
        header.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(_COL_CODE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(_COL_SELECTED, QHeaderView.ResizeMode.ResizeToContents)
        tree.itemChanged.connect(self._on_item_changed)

    def _apply_column_layout(self, tree: QTreeWidget) -> None:
        """Shared 8-column layout so the three cards line up: name stretches,
        the rest keep matching fixed widths (Interactive = still user-draggable).
        """
        widths = {
            _COL_CODE: 48,
            _COL_SELECTED: 58,   # Width column (constant name is legacy)
            _COL_SLICED: 110,
            _COL_TYPE: 85,
            _COL_USAGE: 85,
            _COL_TEXTBLOCK: 140,
            _COL_RELATION: 150,
            _COL_IGNORE: 60,
        }
        header = tree.header()
        header.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeMode.Stretch)
        for col, width in widths.items():
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(col, width)
        header.setStretchLastSection(False)

    def _build_attributes_card(self) -> "_CollapsibleCard":
        """Build the Attribute master/detail workspace.

        The legacy tree remains as an invisible backing model because the
        existing Class Creation actions (grouping, inferred-code resolution,
        add/remove value and reduction synchronisation) already operate on it.
        The visible surface is now a compact Property -> Value master/detail
        editor.
        """
        self._attr_tree = QTreeWidget(self)
        self._attr_tree.setObjectName("classAttributesBackingTree")
        self._attr_tree.setColumnCount(9)
        self._attr_tree.setHeaderLabels(
            ["Property / Value", "Code", "Width", "Sliced", "Type",
             "Usage", "Text-block", "Relation Object", "Ignore"]
        )
        self._attr_tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._attr_tree.setUniformRowHeights(True)
        self._attr_tree.setItemDelegate(_NameOrCodeDelegate(self._attr_tree))
        self._attr_tree.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self._apply_column_layout(self._attr_tree)
        self._attr_tree.itemChanged.connect(self._on_attr_item_changed)
        self._attr_tree.itemClicked.connect(self._on_attr_item_clicked)
        self._attr_tree.itemSelectionChanged.connect(self._on_attr_selection_changed)
        self._attr_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._attr_tree.customContextMenuRequested.connect(self._on_attr_context_menu)
        self._attr_tree.setProperty("_ews_standardized", True)
        self._attr_tree.setExpandsOnDoubleClick(False)
        self._attr_tree.setVisible(False)

        self._attr_master = QTableWidget(self)
        self._attr_master.setObjectName("classAttributePropertiesTable")
        self._attr_master.setColumnCount(6)
        self._attr_master.setHorizontalHeaderLabels(
            ["Property", "Width", "Ignore", "Type", "Usage", "Relation Object"]
        )
        self._attr_master.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._attr_master.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._attr_master.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self._attr_master.setAlternatingRowColors(True)
        self._attr_master.itemSelectionChanged.connect(self._on_attribute_master_selected)
        self._attr_master.itemChanged.connect(self._on_attribute_master_changed)

        self._attr_values = QTableWidget(self)
        self._attr_values.setObjectName("classAttributeValuesTable")
        self._attr_values.setColumnCount(5)
        self._attr_values.setHorizontalHeaderLabels(
            ["Value", "Code", "Sliced", "Relation Object", "Status"]
        )
        self._attr_values.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._attr_values.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._attr_values.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self._attr_values.setAlternatingRowColors(True)
        self._attr_values.itemChanged.connect(self._on_attribute_value_changed)
        self._attr_values.itemSelectionChanged.connect(self._on_attribute_value_selected)

        for table in (self._attr_master, self._attr_values):
            table.verticalHeader().setVisible(False)
            table.horizontalHeader().setStretchLastSection(False)
            table.setWordWrap(False)

        mh = self._attr_master.horizontalHeader()
        mh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col, width in ((1, 65), (2, 65), (3, 105), (4, 110), (5, 160)):
            mh.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            mh.resizeSection(col, width)

        vh = self._attr_values.horizontalHeader()
        vh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col, width in ((1, 90), (2, 100), (3, 170), (4, 110)):
            vh.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            vh.resizeSection(col, width)

        value_toolbar = QWidget(self)
        value_layout = QHBoxLayout(value_toolbar)
        value_layout.setContentsMargins(0, 0, 0, 4)
        value_layout.addWidget(QLabel("Values", value_toolbar))
        value_layout.addStretch(1)
        self._add_value_btn = QPushButton("Add Value", value_toolbar)
        self._add_value_btn.clicked.connect(self._add_selected_attr_value)
        self._add_value_btn.setEnabled(False)
        value_layout.addWidget(self._add_value_btn)
        self._remove_value_btn.setEnabled(False)
        # The existing toolbar Remove Value button is kept as the single remove action.
        
        values_panel = QWidget(self)
        values_layout = QVBoxLayout(values_panel)
        values_layout.setContentsMargins(0, 0, 0, 0)
        values_layout.setSpacing(4)
        values_layout.addWidget(value_toolbar)
        values_layout.addWidget(self._attr_values, 1)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.setObjectName("classAttributeMasterDetail")
        splitter.addWidget(self._attr_master)
        splitter.addWidget(values_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 5)
        splitter.setChildrenCollapsible(False)
        splitter.setSizes([420, 680])

        self._attr_box = _CollapsibleCard("Attribute", splitter, self)
        self._attr_box.setToolTip(
            "Attribute: configure class properties and their PDM values. "
            "Sliced is the Development reduction code."
        )
        return self._attr_box

    def _populate_attribute_tables(self) -> None:
        """Render the visible Property and Value tables from the backing tree."""
        self._populating = True
        self._attr_master.clearContents()
        self._attr_master.setRowCount(0)
        self._attr_values.clearContents()
        self._attr_values.setRowCount(0)
        self._visible_attr_records = []

        def walk(parent, group_name=None):
            for i in range(parent.childCount()):
                item = parent.child(i)
                data = item.data(_COL_NAME, Qt.ItemDataRole.UserRole)
                current_group = group_name
                if data and data[0] == _KIND_GROUP:
                    current_group = str(data[1])
                elif data and data[0] == _KIND_PROP:
                    prop = data[1]
                    self._visible_attr_records.append((prop, current_group, item))
                if item.childCount():
                    walk(item, current_group)

        for i in range(self._attr_tree.topLevelItemCount()):
            item = self._attr_tree.topLevelItem(i)
            data = item.data(_COL_NAME, Qt.ItemDataRole.UserRole)
            group = str(data[1]) if data and data[0] == _KIND_GROUP else None
            if data and data[0] == _KIND_PROP:
                self._visible_attr_records.append((data[1], group, item))
            if item.childCount():
                walk(item, group)

        for prop, group_name, backing in self._visible_attr_records:
            cls = self._attribute_class_for_group(group_name)
            cls_prop = next(
                (a for a in (cls.properties if cls else [])
                 if str(a.property_id) == str(prop.id)), None
            )
            row = self._attr_master.rowCount()
            self._attr_master.insertRow(row)
            label = prop.name or "-"
            if group_name and getattr(self._context.active_snapshot, "split_classes_by_group", False):
                label = f"{label}  [{group_name}]"
            name_item = QTableWidgetItem(label)
            name_item.setData(Qt.ItemDataRole.UserRole, (prop, group_name, backing))
            name_item.setToolTip(
                "Select this property to edit its values."
                + (f"\nGroup: {group_name}" if group_name else "")
            )
            self._attr_master.setItem(row, 0, name_item)

            width = int(getattr(cls_prop, "width", 0) or 0)
            width_item = QTableWidgetItem(str(width))
            width_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            width_item.setData(Qt.ItemDataRole.UserRole, (prop, group_name, backing))
            self._attr_master.setItem(row, 1, width_item)

            ignore = self._ignore_state_for_property(prop.id)
            ignore_cb = QCheckBox()
            ignore_cb.setChecked(ignore)
            ignore_cb.setToolTip("Keep this property in the base and do not slice it.")
            ignore_cb.toggled.connect(
                lambda checked, p=prop, g=group_name, b=backing:
                self._on_visible_attr_ignore(p, g, b, checked)
            )
            ignore_host = QWidget(self._attr_master)
            il = QHBoxLayout(ignore_host)
            il.setContentsMargins(0, 0, 0, 0)
            il.setAlignment(Qt.AlignmentFlag.AlignCenter)
            il.addWidget(ignore_cb)
            self._attr_master.setCellWidget(row, 2, ignore_host)

            type_combo = QComboBox(self._attr_master)
            for code, desc in _TYPE_OPTIONS:
                type_combo.addItem(f"{code} - {desc}" if code and desc else "", code)
            if cls_prop and cls_prop.type:
                idx = type_combo.findData(cls_prop.type)
                type_combo.setCurrentIndex(max(0, idx))
            type_combo.currentIndexChanged.connect(
                lambda _idx, p=prop, g=group_name, b=backing, c=type_combo:
                self._on_visible_attr_type(p, g, b, c.currentData())
            )
            self._attr_master.setCellWidget(row, 3, type_combo)

            usage_combo = QComboBox(self._attr_master)
            for usage in _USAGE_OPTIONS:
                usage_combo.addItem(usage)
            if cls_prop and cls_prop.usage:
                idx = usage_combo.findText(cls_prop.usage)
                usage_combo.setCurrentIndex(max(0, idx))
            usage_combo.currentTextChanged.connect(
                lambda text, p=prop, g=group_name, b=backing:
                self._on_visible_attr_usage(p, g, b, text)
            )
            self._attr_master.setCellWidget(row, 4, usage_combo)

            relation = self._prop_relation_object(prop)
            self._attr_master.setItem(row, 5, QTableWidgetItem(relation))

        self._attr_master.resizeRowsToContents()
        self._attr_values.setRowCount(0)
        if self._attr_master.rowCount():
            self._attr_master.selectRow(0)
        else:
            self._selected_attr_prop = None
            self._selected_attr_value = None
        self._populating = False
        self._on_attribute_master_selected()

    def _ignore_state_for_property(self, prop_id: str) -> bool:
        overrides = getattr(self._context.active_snapshot, "config_ignore_overrides", None) or {}
        if str(prop_id) in overrides:
            return bool(overrides[str(prop_id)])
        hint = getattr(self, "_slice_hints", {}).get(str(prop_id))
        return bool(hint.get("ignored")) if hint else False

    def _on_attribute_master_selected(self) -> None:
        if self._populating:
            return
        rows = self._attr_master.selectionModel().selectedRows()
        if not rows:
            self._selected_attr_prop = None
            self._selected_attr_value = None
            self._attr_values.setRowCount(0)
            self._add_value_btn.setEnabled(False)
            self._remove_value_btn.setEnabled(False)
            return
        row = rows[0].row()
        meta = self._attr_master.item(row, 0).data(Qt.ItemDataRole.UserRole)
        if not meta:
            return
        prop, group_name, backing = meta
        self._active_group_name = group_name or self._active_group_name
        self._selected_attr_prop = prop
        self._selected_attr_value = None
        self._populate_visible_values(prop, group_name, backing)
        development = getattr(self.window(), "_active_module", None) == WorkbenchModule.DEVELOPMENT
        self._add_value_btn.setEnabled(development)
        self._remove_value_btn.setEnabled(False)

    def _populate_visible_values(self, prop, group_name, backing) -> None:
        self._populating = True
        self._attr_values.clearContents()
        self._attr_values.setRowCount(0)
        cls = self._attribute_class_for_group(group_name)
        cls_prop = next(
            (a for a in (cls.properties if cls else [])
             if str(a.property_id) == str(prop.id)), None
        )
        class_values = {
            str(getattr(v, "value_id", "")): v
            for v in (getattr(cls_prop, "values", []) if cls_prop else [])
            if getattr(v, "value_id", "")
        }
        decoded = (getattr(self, "_config_layout", {}) and
                   self._context.engineering_class_service.resolve_config_codes(
                       self._context.active_snapshot
                   ).get(str(prop.id), {})) or {}
        allowed_ids = None
        if backing is not None:
            ids = set()
            for i in range(backing.childCount()):
                child_data = backing.child(i).data(_COL_NAME, Qt.ItemDataRole.UserRole)
                if child_data and child_data[0] == _KIND_PROP_VALUE:
                    ids.add(str(getattr(child_data[1], "id", "")))
            if ids:
                allowed_ids = ids
        displayed = [
            v for v in (getattr(prop, "values", []) or [])
            if allowed_ids is None or str(getattr(v, "id", "")) in allowed_ids
        ]
        for value in _by_display_order(displayed):
            cv = class_values.get(str(getattr(value, "id", "")))
            pdm_code = (getattr(value, "code", "") or "").strip()
            sliced = (
                (getattr(cv, "code", "") if cv is not None else "").strip()
                or decoded.get(str(getattr(value, "id", "")), "")
            )
            row = self._attr_values.rowCount()
            self._attr_values.insertRow(row)
            value_item = QTableWidgetItem(value.value or "-")
            value_item.setData(Qt.ItemDataRole.UserRole, (prop, value, cv, group_name))
            self._attr_values.setItem(row, 0, value_item)

            code_item = QTableWidgetItem(pdm_code)
            code_item.setToolTip("PDM value code (source value).")
            code_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._attr_values.setItem(row, 1, code_item)

            sliced_item = QTableWidgetItem(sliced)
            sliced_item.setData(Qt.ItemDataRole.UserRole, (prop, value, cv, group_name))
            if getattr(self.window(), "_active_module", None) == WorkbenchModule.DEVELOPMENT:
                sliced_item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsEditable
                )
            else:
                sliced_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            sliced_item.setToolTip(
                "Development Class Creation reduction code. Edit this value to "
                "change the pre-dot slice vocabulary."
            )
            self._attr_values.setItem(row, 2, sliced_item)

            self._attr_values.setItem(
                row, 3, QTableWidgetItem(self._value_relation_object(prop, value))
            )
            status = "PDM"
            if cv is not None and getattr(cv, "source", "pdm") != "pdm":
                status = "Added"
            elif not sliced:
                status = "Needs Sliced code"
            elif sliced_item.text() != pdm_code:
                status = "Corrected"
            status_item = QTableWidgetItem(status)
            status_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self._attr_values.setItem(row, 4, status_item)
        self._attr_values.resizeRowsToContents()
        self._populating = False

    def _on_attribute_value_selected(self) -> None:
        if self._populating:
            return
        rows = self._attr_values.selectionModel().selectedRows()
        if not rows:
            self._selected_attr_value = None
            self._remove_value_btn.setEnabled(False)
            return
        meta = self._attr_values.item(rows[0].row(), 0).data(Qt.ItemDataRole.UserRole)
        if not meta:
            self._selected_attr_value = None
            self._remove_value_btn.setEnabled(False)
            return
        prop, value, _cv, group_name = meta
        self._selected_attr_prop = prop
        self._selected_attr_value = value
        self._active_group_name = group_name or self._active_group_name
        self._remove_value_btn.setEnabled(
            getattr(self.window(), "_active_module", None) == WorkbenchModule.DEVELOPMENT
        )

    def _on_attribute_value_changed(self, item: QTableWidgetItem) -> None:
        if self._populating or item.column() != 2:
            return
        meta = item.data(Qt.ItemDataRole.UserRole)
        if not meta:
            return
        prop, value, cv, group_name = meta
        self._set_active_group_from_attr_item(None)
        self._active_group_name = group_name or self._active_group_name
        new_code = item.text().strip()
        if cv is None:
            self._commit_property_inferred(value, group_name)
            cv = self._class_value_for(str(prop.id), str(value.id), group_name)
        if cv is not None:
            cv.code = new_code
        else:
            # No class value exists yet; keep the PDM source untouched and stop
            # rather than silently changing source data.
            self._populate_visible_values(prop, group_name, None)
            return
        self._user_edited_props.add(str(prop.id))
        self._sync_development_article_sets()
        self._context.snapshot_manager.mark_modified()
        self._populate_visible_values(prop, group_name, None)

    def _on_visible_attr_ignore(self, prop, group_name, backing, checked) -> None:
        if self._populating:
            return
        self._active_group_name = group_name or self._active_group_name
        self._on_ignore_toggled(prop.id, checked, backing)

    def _on_visible_attr_type(self, prop, group_name, backing, code) -> None:
        if self._populating:
            return
        self._active_group_name = group_name or self._active_group_name
        self._on_type_selected(str(prop.id), code, backing)

    def _on_visible_attr_usage(self, prop, group_name, backing, usage) -> None:
        if self._populating:
            return
        self._active_group_name = group_name or self._active_group_name
        self._on_usage_selected(str(prop.id), usage, backing)

    def _on_attribute_master_changed(self, item: QTableWidgetItem) -> None:
        if self._populating or item.column() != 1:
            return
        meta = item.data(Qt.ItemDataRole.UserRole)
        if not meta:
            return
        prop, group_name, backing = meta
        text = item.text().strip()
        width = int(text) if text.isdigit() else 0
        self._active_group_name = group_name or self._active_group_name
        cls = self._attribute_class_for_group(group_name)
        if cls is not None:
            self._context.engineering_class_service.set_width(
                self._context.active_snapshot, cls.id, str(prop.id), width
            )
            self._sync_development_article_sets()
            self._context.snapshot_manager.mark_modified()
            self.refresh()

    def _build_options_card(self) -> "_CollapsibleCard":
        self._opt_tree = QTreeWidget(self)
        self._opt_tree.setObjectName("classOptionsTree")
        # Match the frozen Attributes card: same column set, checkbox next to
        # the name (col 0). Options are always fully-coded, so Width/Sliced are
        # derived from the value codes (no article slicing).
        self._opt_tree.setColumnCount(9)
        self._opt_tree.setHeaderLabels(
            ["Option / Value", "Code", "Width", "", "Type",
             "Usage", "", "Relation Object", ""]
        )
        self._opt_tree.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._opt_tree.setUniformRowHeights(True)
        self._opt_tree.setItemDelegate(_NameOrCodeDelegate(self._opt_tree))
        self._opt_tree.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self._apply_column_layout(self._opt_tree)
        # Keep the legacy backing columns hidden; the visible Options workspace
        # is intentionally compact: Option/Value, Code, Width, Type, Usage,
        # Relation Object.
        for col in (3, 6, 8):
            self._opt_tree.hideColumn(col)
        self._opt_tree.itemChanged.connect(self._on_item_changed)
        # Expandable (option -> its values); single click expands, matching the
        # Attributes card. Opt out of the global standardisation so a
        # double-click never swallows the option-level selection toggle.
        self._opt_tree.setProperty("_ews_standardized", True)
        self._opt_tree.setExpandsOnDoubleClick(False)
        self._opt_tree.itemClicked.connect(self._on_opt_item_clicked)
        self._opt_box = _CollapsibleCard("Options", self._opt_tree, self)
        self._opt_box.setToolTip(
            "Options: select and configure the options that belong to this class."
        )
        return self._opt_box

    def _build_visual_card(self) -> "_CollapsibleCard":
        self._misc_tree = _DeletableTree(self._delete_definition, self)
        self._misc_tree.setObjectName("classVisualTree")
        # Match the Attributes/Options cards: same 8-column set. Visual rows are
        # engineered definitions (no PDM values), so Code/Width/Sliced stay blank.
        self._misc_tree.setColumnCount(9)
        self._misc_tree.setHeaderLabels(
            ["Property / Value", "Code", "", "", "Type",
             "Usage", "", "Relation Object", ""]
        )
        self._misc_tree.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._misc_tree.setUniformRowHeights(True)
        self._misc_tree.setItemDelegate(_NameOrCodeDelegate(self._misc_tree))
        self._misc_tree.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self._apply_column_layout(self._misc_tree)
        # Visual/Misc needs only Property/Value, Code, Type, Usage and Relation
        # Object. Width/Sliced/Text-block are implementation details here.
        for col in (2, 3, 6, 8):
            self._misc_tree.hideColumn(col)
        self._misc_tree.itemChanged.connect(self._on_item_changed)
        self._misc_tree.setRootIsDecorated(True)
        # Opt out of the global standardisation (own context menu + editing) so
        # the Add/Remove value menu and inline editing are not swallowed.
        self._misc_tree.setProperty("_ews_standardized", True)
        self._misc_tree.setExpandsOnDoubleClick(False)
        self._misc_tree.setContextMenuPolicy(
            Qt.ContextMenuPolicy.CustomContextMenu
        )
        self._misc_tree.customContextMenuRequested.connect(
            self._on_visual_context_menu
        )
        self._misc_box = _CollapsibleCard("Visual / Misc", self._misc_tree, self)
        self._misc_box.setToolTip(
            "Visual / Misc: create engineering properties that are not sourced from PDM."
        )
        return self._misc_box

    # -- data --------------------------------------------------------------
    def refresh(self) -> None:
        """Rebuild the cards from the active snapshot.

        The cards ARE the classes. When "Split by group" is off there is one flat
        ``<Category>_*`` set (historical). When on, the group combo selects which
        group's ``<Group>_*`` classes the cards show; the backend classes for
        every group are kept in sync (auto-created + auto-grouped).
        """
        self._populating = True
        category = self._category_label()
        snap = self._context.active_snapshot
        # A new snapshot clears the remembered user-edited properties.
        if id(snap) != self._edited_snap_id:
            self._user_edited_props.clear()
            self._edited_snap_id = id(snap)
        service = self._context.engineering_class_service
        service.ensure_standard_classes(snap, category)
        self._sync_development_article_sets()

        groups = service.resolve_class_groups(snap, category) if snap else []
        split_on = bool(getattr(snap, "split_classes_by_group", False)) and len(groups) > 1
        self._split_cb.blockSignals(True)
        self._split_cb.setChecked(bool(getattr(snap, "split_classes_by_group", False)))
        self._split_cb.blockSignals(False)

        names = [g.name for g in groups]
        self._group_combo.blockSignals(True)
        self._group_combo.clear()
        self._group_combo.addItems(names)
        if self._active_group_name in names:
            self._group_combo.setCurrentText(self._active_group_name)
        elif names:
            self._active_group_name = names[0]
        self._group_combo.blockSignals(False)
        # Split results are rendered together in the Attribute tree. The selector
        # is retained for compatibility but is not used as a separate result table.
        self._group_combo.setVisible(False)

        # The basis selector shows whenever the split is on (even for a single
        # group), so the user can switch between range and article-set grouping.
        split_checked = bool(getattr(snap, "split_classes_by_group", False))
        self._basis_combo.blockSignals(True)
        basis_idx = self._basis_combo.findData(
            str(getattr(snap, "class_group_basis", "") or "range")
        )
        self._basis_combo.setCurrentIndex(basis_idx if basis_idx >= 0 else 0)
        self._basis_combo.blockSignals(False)
        self._basis_combo.setVisible(split_checked)

        token = self._active_token()
        # Keep the functional workspace names visible as the card titles.
        # The active class token is shown alongside the card name so users can
        # distinguish Attribute / Options / Visual without losing the class
        # context (for example: "Attribute — Bolster").
        self._attr_box.setTitle(f"Attribute — {token}")
        self._opt_box.setTitle(f"Options — {token}")
        self._misc_box.setTitle(f"Visual / Misc — {token}")
        self._populate_attributes()
        self._populate_attribute_tables()
        self._populate_options()
        self._on_attr_selection_changed()
        self._populate_visual()
        self._populating = False
        self._last_render_sig = self._render_signature()

    def _on_split_toggled(self, checked: bool) -> None:
        """Persist the split opt-in and rebuild."""
        snap = self._context.active_snapshot
        if snap is None or self._populating:
            return
        snap.split_classes_by_group = bool(checked)
        self.refresh()

    def _on_basis_changed(self, _index: int) -> None:
        """Persist the group basis (range / article set) and rebuild."""
        snap = self._context.active_snapshot
        if snap is None or self._populating:
            return
        snap.class_group_basis = self._basis_combo.currentData() or "range"
        self._active_group_name = ""  # let the new grouping select its first group
        self._context.snapshot_manager.mark_modified()
        self.refresh()

    def _on_group_changed(self, _index: int) -> None:
        """Switch the active group shown in the cards."""
        if self._populating:
            return
        self._active_group_name = self._group_combo.currentText()
        self.refresh()

    def _rename_group_inline(self, key: str, new_text: str) -> None:
        """Rename a group directly from its tree header. Mapping another group's
        name onto this one MERGES them (same as the old Rename dialog)."""
        snap = self._context.active_snapshot
        new_name = (new_text or "").strip()
        if snap is None or not new_name or key == "__none__" or new_name == key:
            self.refresh()  # revert the edited header text
            return
        self._context.engineering_class_service.set_group_name(snap, [key], new_name)
        if self._active_group_name == key:
            self._active_group_name = new_name
        self._context.snapshot_manager.mark_modified()
        self.refresh()

    def _active_groups(self) -> list:
        """The resolved class groups for the active snapshot."""
        snap = self._context.active_snapshot
        if snap is None:
            return []
        return self._context.engineering_class_service.resolve_class_groups(
            snap, self._category_label()
        )

    def _active_group(self):
        """The group currently shown in the cards (the selected one, or the
        sole/first group)."""
        groups = self._active_groups()
        for g in groups:
            if g.name == self._active_group_name:
                return g
        return groups[0] if groups else None

    def _active_token(self) -> str:
        """Class-name prefix for the active group (the flat category when the
        group is the whole load)."""
        group = self._active_group()
        service = self._context.engineering_class_service
        if group is None:
            return self._category_label()
        return service._group_token(group.name)


    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        # The Articles reduction mutates the snapshot IN PLACE (same object), so
        # id() can't detect it - re-render when the grouping inputs (article_sets)
        # or overrides have changed since the last populate, and not otherwise.
        if self._render_signature() != getattr(self, "_last_render_sig", None):
            self.refresh()

    def _render_signature(self):
        """Cheap fingerprint of the inputs this page renders (grouping + codes)."""
        snapshot = self._context.active_snapshot
        if snapshot is None:
            return None
        sets = tuple(
            (
                s.base_length,
                len(s.article_ids),
                tuple(sorted(str(a) for a in s.article_ids)),
            )
            for s in (getattr(snapshot, "article_sets", None) or [])
        )
        # Article workflow reductions are persisted on engineering members
        # (reduced_article), not on ArticleSet itself. Include those values so
        # returning to Class Creation detects an Article-page reduction even
        # when the ArticleSet membership/counts did not change.
        reduced = tuple(
            sorted(
                (
                    str(member.id),
                    str(getattr(member, "reduced_article", "") or ""),
                )
                for family in (getattr(snapshot.engineering, "families", []) or [])
                for member in (getattr(family, "members", []) or [])
            )
        )
        overrides = getattr(snapshot, "config_code_overrides", None) or {}
        return (
            id(snapshot),
            len(snapshot.properties),
            len(snapshot.articles),
            sets,
            reduced,
            sum(len(m) for m in overrides.values()),
            tuple(sorted(getattr(snapshot, "ignored_ranges", None) or [])),
        )

    def _category_label(self) -> str:
        """The <Category> used in the class/card names (product category)."""
        snapshot = self._context.active_snapshot
        product = snapshot.product if snapshot is not None else None
        if product is not None:
            label = (
                product.category or product.range_name or ""
            ).strip()
            if label:
                return label
        if snapshot is not None and snapshot.metadata is not None:
            return (snapshot.metadata.product_code or "").strip() or "Class"
        return "Class"

    def _attribute_class(self):
        """The active group's ``<Group>_Attribute`` class, or None."""
        service = self._context.engineering_class_service
        name = f"{self._active_token()}_Attribute"
        for cls in service.get_classes(self._context.active_snapshot):
            if cls.name == name:
                return cls
        return None

    def _attribute_class_for_group(self, group_name: str | None):
        """Return the Attribute class belonging to a displayed split group."""
        if not group_name:
            return self._attribute_class()
        service = self._context.engineering_class_service
        token = service._group_token(group_name)
        name = f"{token}_Attribute"
        for cls in service.get_classes(self._context.active_snapshot):
            if cls.name == name:
                return cls
        return None

    def _group_name_for_attr_item(self, item) -> str | None:
        """Find the split-group owner of an Attribute property/value row."""
        if item is None:
            return None
        node = item
        while node is not None:
            data = node.data(_COL_NAME, Qt.ItemDataRole.UserRole)
            if data and data[0] == _KIND_GROUP:
                return str(data[1])
            node = node.parent()
        return None

    def _set_active_group_from_attr_item(self, item) -> None:
        group = self._group_name_for_attr_item(item)
        if group and getattr(self._context.active_snapshot, "split_classes_by_group", False):
            self._active_group_name = group

    def _options_class(self):
        """The active group's ``<Group>_Options`` class, or None."""
        service = self._context.engineering_class_service
        name = f"{self._active_token()}_Options"
        for cls in service.get_classes(self._context.active_snapshot):
            if cls.name == name:
                return cls
        return None

    def _visual_class(self):
        """The active group's ``<Group>_Visual`` class, or None."""
        service = self._context.engineering_class_service
        name = f"{self._active_token()}_Visual"
        for cls in service.get_classes(self._context.active_snapshot):
            if cls.name == name:
                return cls
        return None

    def _split_members(self) -> list[tuple[str, str]]:
        """(article code, remaining) for every member with a persisted split."""
        snapshot = self._context.active_snapshot
        if snapshot is None or snapshot.engineering is None:
            return []
        member_service = self._context.engineering_member_service
        rows: list[tuple[str, str]] = []
        for family in snapshot.engineering.families:
            for member in family.members:
                base = member.reduced_article or ""
                if not base:
                    continue
                article = member_service.get_article(snapshot, member)
                code = article.code if article is not None else ""
                rows.append((code or base, code[len(base):]))
        return rows

    def _update_inferred_hint(self, count: int, unresolved: int = 0, issues: int = 0) -> None:
        """Show the config-code status: unresolved (blocks Generate) takes
        priority over the inferred verify-before-Generate hint."""
        if unresolved > 0:
            self._inferred_hint.setText(
                f"\u26a0 {unresolved} config code(s) unresolved \u2013 click "
                "Resolve remaining (blocks Generate)"
            )
            self._inferred_hint.setStyleSheet("color: #b22222; font-weight: 600;")
            self._inferred_hint.setVisible(True)
        elif issues > 0:
            self._inferred_hint.setText(
                f"\u26a0 {issues} config propert{'y' if issues == 1 else 'ies'} "
                "flagged \u2013 hover the highlighted rows for the suggested fix"
            )
            self._inferred_hint.setStyleSheet("color: #b8860b; font-weight: 600;")
            self._inferred_hint.setVisible(True)
        elif count > 0:
            self._inferred_hint.setText(
                f"\u26a0 {count} inferred config code(s) \u2013 verify before Generate"
            )
            self._inferred_hint.setStyleSheet("color: #b8860b; font-weight: 600;")
            self._inferred_hint.setVisible(True)
        else:
            self._inferred_hint.setVisible(False)

    def _on_resolve_remaining(self) -> None:
        """Open one bulk editor for unresolved codes and missing PDM values."""
        snap = self._context.active_snapshot
        svc = self._context.engineering_class_service
        unresolved = svc.unresolved_config_codes(snap)
        resolved = svc.resolve_config_codes(snap)
        rows = []

        for prop in unresolved:
            rmap = resolved.get(str(prop.id), {})
            for value in prop.values:
                if str(value.id) not in rmap:
                    rows.append(("config", prop, value, ""))

        cls = self._attribute_class()
        if cls is not None:
            for prop in self._context.property_service.get_properties():
                for value in self._missing_pdm_values(prop):
                    rows.append((
                        "missing",
                        prop,
                        value,
                        (getattr(value, "code", "") or "").strip(),
                    ))

        if not rows:
            return
        self._open_clarification_dialog(rows)

    def _open_clarification_dialog(self, rows) -> None:
        """Bulk repair unresolved codes and missing PDM class values."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Resolve remaining Class Creation values")
        dialog.resize(760, 460)
        layout = QVBoxLayout(dialog)
        info = QLabel(
            "Review unresolved configuration codes and PDM values missing from "
            "Class Creation. Edit the Code column and click Apply All.",
            dialog,
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        table = QTableWidget(len(rows), 5, dialog)
        table.setHorizontalHeaderLabels(
            ["Type", "Property", "Value", "Suggested Code", "Code"]
        )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.EditTrigger.AllEditTriggers)
        standardize_table(table)

        for r, (kind, prop, value, hint) in enumerate(rows):
            cells = [
                QTableWidgetItem(
                    "Missing PDM value" if kind == "missing" else "Config code"
                ),
                QTableWidgetItem(prop.name or ""),
                QTableWidgetItem(value.value or ""),
                QTableWidgetItem(hint),
                QTableWidgetItem(hint),
            ]
            for col, cell in enumerate(cells):
                table.setItem(r, col, cell)
                if col < 4:
                    cell.setFlags(
                        Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                    )

        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            dialog,
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Apply All")
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        snap = self._context.active_snapshot
        cls = self._attribute_class()
        if snap is None or cls is None:
            return
        service = self._context.engineering_class_service
        changed = False

        for r, (kind, prop, value, _hint) in enumerate(rows):
            code = table.item(r, 4).text().strip()
            if not code:
                continue
            if kind == "config":
                snap.config_code_overrides.setdefault(
                    str(prop.id), {}
                )[str(value.id)] = code
                changed = True
            else:
                added = service.add_value(
                    snap,
                    cls.id,
                    str(prop.id),
                    code,
                    (value.value or "").strip(),
                    source="pdm",
                )
                if added is not None:
                    added.value_id = str(getattr(value, "id", "") or "")
                    changed = True

        if changed:
            self._context.snapshot_manager.mark_modified()
            self._sync_development_article_sets()
            self.refresh()

    def _populate_attributes(self) -> None:
        # Preserve which group headers are collapsed and which property rows are
        # expanded, so an edit (which rebuilds the tree) keeps the current view.
        expanded_props: set = set()
        collapsed_groups: set = set()
        for i in range(self._attr_tree.topLevelItemCount()):
            node = self._attr_tree.topLevelItem(i)
            ndata = node.data(_COL_NAME, Qt.ItemDataRole.UserRole)
            if ndata and ndata[0] == _KIND_GROUP:
                if not node.isExpanded():
                    collapsed_groups.add(ndata[1])
                for j in range(node.childCount()):
                    child = node.child(j)
                    cdata = child.data(_COL_NAME, Qt.ItemDataRole.UserRole)
                    if cdata and cdata[0] == _KIND_PROP and child.isExpanded():
                        expanded_props.add(cdata[1].id)
            elif ndata and ndata[0] == _KIND_PROP and node.isExpanded():
                expanded_props.add(ndata[1].id)
        self._attr_tree.clear()
        cls = self._attribute_class()
        service = self._context.engineering_class_service
        remainings = [r for _code, r in self._split_members()]
        # Authoritative config decode: value_id -> letter for uncoded
        # (configuration) attributes, merging correlation with the per-article
        # slice (+ user overrides). Never written back to value.code (that would
        # flip them to variant props).
        config_codes = service.resolve_config_codes(self._context.active_snapshot)
        self._config_layout = service.config_code_layout(self._context.active_snapshot)
        self._slice_hints = service.config_slice_hints(self._context.active_snapshot)
        unresolved = service.unresolved_config_codes(self._context.active_snapshot)
        findings = service.analyze_config_codes(self._context.active_snapshot)
        self._prop_findings = {}
        for finding in findings:
            self._prop_findings.setdefault(finding.property_id, []).append(finding)
        self._update_inferred_hint(
            len(config_codes), len(unresolved), len(self._prop_findings)
        )
        widths = {}
        if cls is not None:
            widths = {a.property_id: a.width for a in cls.properties}

        props = list(self._context.property_service.get_properties())
        development = (
            getattr(self.window(), "_active_module", None)
            == WorkbenchModule.DEVELOPMENT
        )
        missing_value_count = (
            sum(len(self._missing_pdm_values(prop)) for prop in props)
            if development and cls is not None
            else 0
        )
        self._auto_btn.setEnabled(
            development and (bool(unresolved) or missing_value_count > 0)
        )
        if development and (unresolved or missing_value_count):
            self._auto_btn.setToolTip(
                f"Resolve {len(unresolved)} unresolved code(s) and "
                f"{missing_value_count} missing PDM value(s) in one pass."
            )

        snapshot = self._context.active_snapshot
        # Value ids that will actually get a relation (subset-confined); generic
        # values get a blank Relation cell so the relation table stays clean.
        self._related_values = (
            self._context.engineering_relation_service.related_value_ids(snapshot)
        )
        # Properties stay in PDM DisplayOrder (property_service already sorts by
        # it) - the order every PDM window and the native OCD export use.
        # Property-level "dependent on the article" (per-article variance OR PDM
        # HasDependentOptions); drives the dependency marker, HDO stays per-value.
        self._article_dependent_ids = service.article_dependent_property_ids(snapshot)
        # Properties are a UNIQUE list (each once). When a load SPANS several
        # PDM ProductRanges (Nevi Desks / Screen Components / Wire Management),
        # group them under a header per range; a single-range load stays flat.
        # A property carried by several ranges lists under each of them. Ranges
        # the user ignored on the Articles page (components / accessories /
        # hardware) are dropped so only the main product's classes remain.
        ctx = (cls, service, remainings, config_codes, widths, expanded_props)
        ranges = getattr(snapshot, "attribute_range", None) or {}
        value_range = getattr(snapshot, "value_range", None) or {}
        ignored = set(getattr(snapshot, "ignored_ranges", None) or [])

        def _prop_kept(pid, source_props):
            rs = ranges.get(str(pid))
            return (not rs) or any(r not in ignored for r in rs)

        def _render_group(group, group_cls, group_node=None):
            """Render one split group's properties into the SAME Attribute tree."""
            group_props = [p for p in props if str(p.id) in group.prop_ids and _prop_kept(p.id, props)]
            group_widths = {a.property_id: a.width for a in group_cls.properties} if group_cls else {}
            group_ctx = (group_cls, service, remainings, config_codes, group_widths, expanded_props)
            # The split group itself is the grouping row. Keep all of that
            # group's properties directly inside the same Attribute table rather
            # than introducing another nested result table/group selector.
            parent = group_node if group_node is not None else self._attr_tree
            for prop in group_props:
                vids = None
                if ignored:
                    vids = {
                        str(v.id) for v in prop.values
                        if _prop_kept(v.id, props)
                    }
                self._add_attr_property_node(
                    parent, prop, *group_ctx, value_ids=vids or None,
                    group_name=group.name,
                )

        props = [p for p in props if _prop_kept(p.id, props)]
        split_checked = bool(getattr(snapshot, "split_classes_by_group", False))
        groups = service.resolve_class_groups(snapshot, self._category_label()) if split_checked else []
        if split_checked and len(groups) > 1:
            # One Attribute table, with each split class represented by a group header.
            collapsed_groups = set()
            for i in range(self._attr_tree.topLevelItemCount()):
                n = self._attr_tree.topLevelItem(i)
                d = n.data(_COL_NAME, Qt.ItemDataRole.UserRole)
                if d and d[0] == _KIND_GROUP and not n.isExpanded():
                    collapsed_groups.add(d[1])
            for group in groups:
                group_cls = self._attribute_class_for_group(group.name)
                if group_cls is None:
                    continue
                header = self._make_group_node(
                    self._attr_tree, group.name, group.name, collapsed_groups
                )
                _render_group(group, group_cls, header)
        else:
            all_ranges = {
                r for p in props for r in ranges.get(str(p.id), []) if r not in ignored
            }
            if len(all_ranges) > 1:
                def _group_rank(gname: str) -> int:
                    for i, p in enumerate(props):
                        if gname in ranges.get(str(p.id), []):
                            return i
                    return 10_000
                for gname in sorted(all_ranges, key=_group_rank):
                    gnode = self._make_group_node(
                        self._attr_tree, gname, gname, collapsed_groups
                    )
                    for prop in props:
                        if gname in ranges.get(str(prop.id), []):
                            vids = {str(v.id) for v in prop.values if gname in value_range.get(str(v.id), [])}
                            self._add_attr_property_node(
                                gnode, prop, *ctx, value_ids=vids or None
                            )
                orphans = [p for p in props if not ranges.get(str(p.id))]
                if orphans:
                    gnode = self._make_group_node(
                        self._attr_tree, "General", "__none__", collapsed_groups
                    )
                    for prop in orphans:
                        self._add_attr_property_node(gnode, prop, *ctx)
            else:
                for prop in props:
                    vids = None
                    if ignored:
                        vids = {str(v.id) for v in prop.values if _prop_kept(v.id, props)}
                    self._add_attr_property_node(self._attr_tree, prop, *ctx, value_ids=vids or None)

    def _make_group_node(self, tree, label, key, collapsed_groups):
        """Bold header for one functional group (ProductRange). Editable so the
        group can be renamed/merged directly in the table (except 'General')."""
        node = QTreeWidgetItem(
            tree, [label, "", "", "", "", "", "", "", ""]
        )
        node.setData(_COL_NAME, Qt.ItemDataRole.UserRole, (_KIND_GROUP, key))
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if key != "__none__":
            flags |= Qt.ItemFlag.ItemIsEditable
            node.setToolTip(_COL_NAME, "Double-click to rename this group "
                            "(type another group's name to merge).")
        node.setFlags(flags)
        font = node.font(_COL_NAME)
        font.setBold(True)
        node.setFont(_COL_NAME, font)
        node.setExpanded(key not in collapsed_groups)
        return node

    def _add_attr_property_node(
        self, parent, prop, cls, service, remainings, config_codes, widths,
        expanded_props, value_ids=None, group_name: str | None = None,
    ) -> None:
            # Values shown under a functional-range group are limited to the ones
            # that group's products carry; unfiltered (value_ids None) elsewhere.
            prop_values = [
                v for v in prop.values
                if value_ids is None or str(v.id) in value_ids
            ]
            # Resolve the persisted class assignment and inferred codes before
            # calculating the effective value codes. These must be available
            # below because Class Creation values can come from either source.
            cls_prop = next(
                (a for a in cls.properties if a.property_id == prop.id), None
            ) if cls else None
            decoded = config_codes.get(prop.id) or {}

            # Discovered distinct codes at this property's slice, across ALL
            # split articles, with an "unassigned" count for the ones not yet
            # mapped to a value.
            # When every value already carries a (standard) code the alignment
            # is done: show those codes directly, independent of article slicing.
            class_values_by_id = {
                str(getattr(v, "value_id", "")): v
                for v in (getattr(cls_prop, "values", []) or [])
                if getattr(v, "value_id", "")
            } if cls_prop is not None else {}
            value_codes: list[str] = []
            for v in prop_values:
                cv = class_values_by_id.get(str(v.id))
                c = ((getattr(cv, "code", "") if cv is not None else "") or
                     (v.code or "").strip() or
                     decoded.get(str(v.id), "")).strip()
                if c and c not in value_codes:
                    value_codes.append(c)
            fully_coded = bool(prop_values) and all(
                ((getattr(class_values_by_id.get(str(v.id)), "code", "") if class_values_by_id.get(str(v.id)) else "")
                 or (v.code or "").strip()
                 or decoded.get(str(v.id), "")).strip()
                for v in prop_values
            )
            # A configuration property stays user-editable even once every value
            # is coded. Keyed off the PERSISTED config relation
            # (snapshot.config_value_codes) plus any property the user has
            # hand-edited, so cells never re-lock after the first edit commits
            # the values (the live decode drops coded properties).
            _cfg_codes = getattr(
                self._context.active_snapshot, "config_value_codes", None
            ) or {}
            is_config = (
                str(prop.id) in {str(k) for k in _cfg_codes}
                or str(prop.id) in self._user_edited_props
            )
            # Drop redundant same-name value rows (PDM lists a value once per
            # product sub-series); keep the coded twin, preserve distinct codes.
            display_values = collapse_duplicate_values(
                _by_display_order(prop_values),
                lambda v: (v.code or decoded.get(str(v.id), "")),
            )
            if fully_coded:
                distinct = []
                width = max(len(c) for c in value_codes)
            else:
                distinct = (
                    service.distinct_slice_codes(cls, prop.id, remainings)
                    if cls is not None
                    else []
                )
                if value_codes:
                    # A property with any PDM value code takes its width from
                    # those codes (each value carries its own code width).
                    width = widths.get(prop.id, 0) or max(
                        len(c) for c in value_codes
                    )
                else:
                    # Pure configuration property (no PDM codes): Width = the
                    # decoder's owned-position count (evidence-based true width);
                    # PDM HasDependentOptions is only a last-resort hint.
                    width = (
                        widths.get(prop.id, 0)
                        or getattr(self, "_config_layout", {}).get(
                            prop.id, {}).get("width", 0)
                        or max(int(getattr(prop, "code_width", 0) or 0), 0)
                    )
            dependent = str(prop.id) in getattr(self, "_article_dependent_ids", set())
            cls_prop = next(
                (a for a in cls.properties if a.property_id == prop.id), None
            ) if cls else None
            text_block = (
                cls_prop.text_block if (cls_prop and cls_prop.text_block)
                else self._text_block(prop.name)
            )
            node = QTreeWidgetItem(
                parent,
                [
                    f"{prop.name or '-'} ({len(display_values)})",
                    "",
                    str(width),
                    "",  # Sliced
                    "",  # Type (combo)
                    "",  # Usage (combo)
                    text_block,
                    self._prop_relation_object(prop),
                ],
            )
            # Dependency marker: green ticked box when the property is dependent
            # on the article (per-article variance or PDM HasDependentOptions),
            # red crossed box for identity/metatype props - so the article-
            # defining attributes stand out at a glance.
            node.setIcon(_COL_NAME, self._dependency_icon(dependent))
            # Config-code diagnostics: tint + explain any property the decoder
            # flagged (unresolved / mixed-width), with the suggested fix on hover.
            prop_findings = getattr(self, "_prop_findings", {}).get(str(prop.id), [])
            if prop_findings:
                node.setToolTip(_COL_NAME, "\n".join(
                    f"\u26a0 {f.message}\n   \u2192 {f.suggestion}" for f in prop_findings
                ))
                node.setForeground(_COL_NAME, QBrush(QColor(theme.COLOR_WARNING)))
            # Fully-coded rows show their own codes; otherwise the discovered
            # article codes + how many values still need a code.
            if fully_coded:
                node.setText(_COL_SLICED, ", ".join(value_codes))
                node.setToolTip(_COL_SLICED, ", ".join(value_codes))
                node.setForeground(_COL_SLICED, QBrush(QColor(theme.COLOR_OK)))
            elif decoded:
                # Inferred configuration codes (read-only), shown like coded rows
                # but tagged so they are visibly derived, not stored.
                ordered = [
                    decoded[str(v.id)] for v in prop_values if str(v.id) in decoded
                ]
                node.setText(_COL_SLICED, ", ".join(ordered) + "  (inferred)")
                node.setToolTip(
                    _COL_SLICED,
                    "Configuration codes inferred from the product code "
                    "(not stored in PDM).",
                )
                node.setForeground(_COL_SLICED, QBrush(QColor(theme.COLOR_OK)))
            else:
                self._apply_sliced(node, prop, distinct, width)
            node.setToolTip(
                _COL_NAME,
                "Dependent on the article (item-chosen or drives dependent options)"
                if dependent
                else "Not article-dependent (identity / metatype)",
            )
            node.setData(_COL_NAME, Qt.ItemDataRole.UserRole, (_KIND_PROP, prop))
            if group_name:
                node.setData(_COL_NAME, Qt.ItemDataRole.UserRole + 2, group_name)
            node.setData(2, Qt.ItemDataRole.UserRole + 1, {2})  # Width editable
            node.setData(  # Text-block editable
                _COL_TEXTBLOCK, Qt.ItemDataRole.UserRole + 1, {_COL_TEXTBLOCK}
            )
            node.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEditable
                | Qt.ItemFlag.ItemIsUserCheckable
            )
            # Scope checkbox (was the retired Properties page): feeds the Builder.
            node.setCheckState(
                _COL_NAME,
                Qt.CheckState.Checked
                if getattr(prop, "selected", False)
                else Qt.CheckState.Unchecked,
            )
            # Type dropdown (C/L/N/T) for property classification
            type_combo = QComboBox()
            # Populate with code + description display (store only code)
            for code, desc in _TYPE_OPTIONS:
                display = f"{code} - {desc}" if code and desc else ""
                type_combo.addItem(display, code)  # userData stores just the code
            # Find the class property assignment to get current type value
            if cls_prop and cls_prop.type:
                # Find index by userData (code)
                idx = next(
                    (i for i in range(type_combo.count())
                     if type_combo.itemData(i) == cls_prop.type),
                    0
                )
                type_combo.setCurrentIndex(idx)
            type_combo.setMinimumHeight(26)
            type_combo.currentIndexChanged.connect(
                lambda idx, p_id=prop.id, combo=type_combo, n=node: (
                    self._on_type_selected(p_id, combo.itemData(idx), n)
                    if idx >= 0 else None
                )
            )
            self._attr_tree.setItemWidget(node, _COL_TYPE, type_combo)
            node.setSizeHint(_COL_TYPE, type_combo.sizeHint())
            # Usage dropdown (Configuration | Graphic)
            usage_combo = QComboBox()
            for usage in _USAGE_OPTIONS:
                usage_combo.addItem(usage)
            if cls_prop and cls_prop.usage:
                pos = usage_combo.findText(cls_prop.usage)
                usage_combo.setCurrentIndex(pos if pos >= 0 else 0)
            usage_combo.setMinimumHeight(26)
            usage_combo.currentTextChanged.connect(
                lambda text, p_id=prop.id, n=node: self._on_usage_selected(p_id, text, n)
            )
            self._attr_tree.setItemWidget(node, _COL_USAGE, usage_combo)
            node.setSizeHint(_COL_USAGE, usage_combo.sizeHint())
            # Ignore toggle: every property row gets an Ignore checkbox.
            # For properties recognised by the head decoder, use its suggestion
            # unless the user has an explicit override. Properties without a
            # decoded head span still expose the same row-level control so the
            # table is consistent across all properties.
            hint = getattr(self, "_slice_hints", {}).get(str(prop.id))
            overrides = getattr(
                self._context.active_snapshot, "config_ignore_overrides", None
            ) or {}
            prop_id = str(prop.id)
            ignore_cb = QCheckBox()
            if prop_id in overrides:
                ignore_cb.setChecked(bool(overrides[prop_id]))
            else:
                ignore_cb.setChecked(bool(hint.get("ignored")) if hint else False)

            overlaps = hint.get("overlaps") if hint else ""
            ignore_cb.setToolTip(
                f"Looks like a duplicate of '{overlaps}' - suggested to keep "
                "in the base. Untick to slice it."
                if overlaps else
                "Tick to keep this property in the base (do not slice it)."
            )
            ignore_cb.toggled.connect(
                lambda checked, p_id=prop.id, n=node:
                self._on_ignore_toggled(p_id, checked, n)
            )
            self._attr_tree.setItemWidget(node, _COL_IGNORE, ignore_cb)
            for value in display_values:
                # Value text-block key matches the Text workflow / PDM:
                # <Property>_<code> (e.g. Type_1), using the stored or decoded code.
                class_value = class_values_by_id.get(str(value.id))
                value_code = (
                    (getattr(class_value, "code", "") if class_value is not None else "")
                    or (value.code or "").strip()
                    or decoded.get(str(value.id), "")
                ).replace("#", "")
                value_tb = (
                    f"{self._text_block(prop.name)}_{value_code}"
                    if value_code else self._text_block(value.value)
                )
                item = QTreeWidgetItem(
                    node,
                    [
                        value.value or "-",
                        "" if distinct else (value.code or ""),
                        "",  # No width for values
                        "",  # Sliced (empty for values)
                        "",  # No Type for values
                        "",  # No Usage for values
                        value_tb,
                        self._value_relation_object(prop, value),
                    ],
                )
                item.setData(
                    _COL_NAME, Qt.ItemDataRole.UserRole, (_KIND_PROP_VALUE, value)
                )
                inferred = decoded.get(str(value.id), "")
                flags = (
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                )
                if inferred:
                    # Inferred config code: shown green and editable so the user
                    # can accept it (re-enter) or correct it; editing stores it.
                    item.setText(_COL_CODE, inferred)
                    item.setForeground(_COL_CODE, QBrush(QColor(theme.COLOR_OK)))
                development = (
                    getattr(self.window(), "_active_module", None)
                    == WorkbenchModule.DEVELOPMENT
                )
                if development or inferred or is_config or (not distinct and not fully_coded):
                    # Development Class Creation owns the pre-dot reduction
                    # vocabulary, so every value code is correctable there.
                    item.setData(1, Qt.ItemDataRole.UserRole + 1, {1})
                    flags |= Qt.ItemFlag.ItemIsEditable
                item.setFlags(flags)
                if distinct:
                    # Embedded pull-down: always shows it IS a dropdown and
                    # opens on a single click.
                    combo = QComboBox()
                    combo.addItem("")
                    combo.addItems([str(c) for c in distinct])
                    effective_code = (
                        (getattr(class_value, "code", "") if class_value is not None else "")
                        or (value.code or "").strip()
                    )
                    if effective_code and combo.findText(effective_code) < 0:
                        combo.addItem(effective_code)
                    # Development Class Creation permits correction of every
                    # value code, not only inferred/configuration codes.
                    if getattr(self.window(), "_active_module", None) == WorkbenchModule.DEVELOPMENT:
                        combo.setEditable(True)
                    pos = combo.findText(effective_code)
                    combo.setCurrentIndex(pos if pos >= 0 else 0)
                    combo.setMinimumHeight(26)
                    combo.currentTextChanged.connect(
                        lambda text, v=value, n=node, p=prop, it=item: (
                            self._on_code_selected(v, text, n, p, it)
                        )
                    )
                    self._attr_tree.setItemWidget(item, _COL_CODE, combo)
                    # Grow the row so the combo (and its selected code) is fully
                    # visible instead of being vertically clipped.
                    item.setSizeHint(_COL_CODE, combo.sizeHint())
            # Preserve only the expansion state chosen by the user.
            # Refreshes (for example after changing Ignore) must never expand
            # every property automatically.
            if prop.id in expanded_props:
                node.setExpanded(True)

    def _class_value_for(self, prop_id: str, value_id: str, group_name: str | None = None):
        if getattr(self.window(), "_active_module", None) != WorkbenchModule.DEVELOPMENT:
            return None
        cls = self._attribute_class_for_group(group_name)
        if cls is None:
            return None
        assignment = next(
            (a for a in cls.properties if str(a.property_id) == str(prop_id)),
            None,
        )
        if assignment is None:
            return None
        return next(
            (v for v in assignment.values if str(getattr(v, "value_id", "")) == str(value_id)),
            None,
        )

    def _sync_development_article_sets(self) -> None:
        snapshot = self._context.active_snapshot
        window = self.window()
        if snapshot is None or getattr(window, "_active_module", None) != WorkbenchModule.DEVELOPMENT:
            return
        self._context.engineering_reduction_service.materialize_class_creation_article_sets(snapshot)

    def _on_code_selected(
        self, value, text: str, prop_node, prop, value_item=None
    ) -> None:
        """A value's Code pull-down changed: write the code + refresh the
        property row's discovered/unassigned summary (no full rebuild)."""
        if self._populating:
            return
        new_code = (text or "").strip()
        group_name = self._group_name_for_attr_item(prop_node)
        self._set_active_group_from_attr_item(prop_node)
        class_value = self._class_value_for(
            str(prop.id), str(getattr(value, "id", "")), group_name
        )
        if class_value is not None:
            class_value.code = new_code
        else:
            value.code = new_code
        self._sync_development_article_sets()
        self._context.snapshot_manager.mark_modified()
        self._update_sliced(prop_node, prop)
        if value_item is not None:
            value_item.setText(_COL_RELATION, self._value_relation_object(prop, value))

    def _on_type_selected(
        self, prop_id: str, code: str, prop_node
    ) -> None:
        """A property's Type dropdown changed: write the type code to the class assignment."""
        if self._populating:
            return
        group_name = self._group_name_for_attr_item(prop_node)
        cls = self._attribute_class_for_group(group_name)
        if cls is None:
            return
        # Find the class property assignment
        cls_prop = next(
            (a for a in cls.properties if a.property_id == prop_id),
            None
        )
        if cls_prop:
            cls_prop.type = (code or "").strip()
            self._context.snapshot_manager.mark_modified()

    def _on_usage_selected(self, prop_id: str, usage: str, prop_node) -> None:
        """A property's Usage dropdown changed: write it to the class assignment."""
        if self._populating:
            return
        group_name = self._group_name_for_attr_item(prop_node)
        cls = self._attribute_class_for_group(group_name)
        if cls is None:
            return
        cls_prop = next(
            (a for a in cls.properties if a.property_id == prop_id), None
        )
        if cls_prop:
            cls_prop.usage = (usage or "").strip()
            self._context.snapshot_manager.mark_modified()

    def _on_ignore_toggled(self, prop_id, checked: bool, prop_node=None) -> None:
        """User chose to keep a head property in the base (checked) or slice it
        (unchecked). Re-slices and re-materialises the base masters so both this
        page and the Article Master reflect the choice."""
        if self._populating:
            return
        snapshot = self._context.active_snapshot
        if snapshot is None:
            return
        self._set_active_group_from_attr_item(prop_node)
        self._context.engineering_class_service.set_config_ignore(
            snapshot, str(prop_id), bool(checked)
        )
        self._sync_development_article_sets()
        self._context.snapshot_manager.mark_modified()
        self.refresh()

    def _on_opt_type_selected(self, option_id: str, code: str) -> None:
        """An option's Type dropdown changed: write it to the _Options assignment."""
        if self._populating:
            return
        cls = self._options_class()
        cls_prop = next(
            (a for a in cls.properties if a.property_id == option_id), None
        ) if cls else None
        if cls_prop:
            cls_prop.type = (code or "").strip()
            self._context.snapshot_manager.mark_modified()

    def _on_opt_usage_selected(self, option_id: str, usage: str) -> None:
        """An option's Usage dropdown changed: write it to the _Options assignment."""
        if self._populating:
            return
        cls = self._options_class()
        cls_prop = next(
            (a for a in cls.properties if a.property_id == option_id), None
        ) if cls else None
        if cls_prop:
            cls_prop.usage = (usage or "").strip()
            self._context.snapshot_manager.mark_modified()

    def _on_visual_type_selected(self, def_id: str, code: str) -> None:
        """A definition's Type dropdown changed: write it to the _Visual assignment."""
        if self._populating:
            return
        cls = self._visual_class()
        cls_prop = next(
            (a for a in cls.properties if a.property_id == def_id), None
        ) if cls else None
        if cls_prop:
            cls_prop.type = (code or "").strip()
            self._context.snapshot_manager.mark_modified()

    def _on_visual_usage_selected(self, def_id: str, usage: str) -> None:
        """A definition's Usage dropdown changed: write it to the _Visual assignment."""
        if self._populating:
            return
        cls = self._visual_class()
        cls_prop = next(
            (a for a in cls.properties if a.property_id == def_id), None
        ) if cls else None
        if cls_prop:
            cls_prop.usage = (usage or "").strip()
            self._context.snapshot_manager.mark_modified()

    def _on_attr_selection_changed(self) -> None:
        """Track the selected Attribute property/value for visible edit controls."""
        item = self._attr_tree.currentItem()
        self._set_active_group_from_attr_item(item)
        self._selected_attr_prop = None
        self._selected_attr_value = None
        if item is not None:
            data = item.data(_COL_NAME, Qt.ItemDataRole.UserRole)
            if data:
                kind, obj = data
                if kind == _KIND_PROP:
                    self._selected_attr_prop = obj
                elif kind == _KIND_PROP_VALUE:
                    self._selected_attr_value = obj
                    parent = item.parent()
                    pdata = (
                        parent.data(_COL_NAME, Qt.ItemDataRole.UserRole)
                        if parent is not None else None
                    )
                    if pdata and pdata[0] == _KIND_PROP:
                        self._selected_attr_prop = pdata[1]
        development = (
            getattr(self.window(), "_active_module", None)
            == WorkbenchModule.DEVELOPMENT
        )
        has_prop = self._selected_attr_prop is not None
        self._move_up_btn.setEnabled(development and has_prop)
        self._move_down_btn.setEnabled(development and has_prop)
        self._remove_value_btn.setEnabled(
            development and self._selected_attr_value is not None
        )

    def _move_selected_attr_property(self, direction: int) -> None:
        prop = self._selected_attr_prop
        if prop is not None:
            self._move_attr_property(prop, direction)

    def _add_selected_attr_value(self) -> None:
        prop = self._selected_attr_prop
        if prop is not None:
            self._add_attr_value(prop)

    def _remove_selected_attr_value(self) -> None:
        prop = self._selected_attr_prop
        value = self._selected_attr_value
        if prop is not None and value is not None:
            self._remove_attr_value(prop, value)

    def _on_attr_context_menu(self, pos) -> None:
        if getattr(self.window(), "_active_module", None) != WorkbenchModule.DEVELOPMENT:
            return
        item = self._attr_tree.itemAt(pos)
        if item is None:
            return
        self._set_active_group_from_attr_item(item)
        data = item.data(_COL_NAME, Qt.ItemDataRole.UserRole)
        if not data:
            return
        menu = QMenu(self._attr_tree)
        if data[0] == _KIND_PROP:
            prop = data[1]
            menu.addAction("Move up", lambda p=prop: self._move_attr_property(p, -1))
            menu.addAction("Move down", lambda p=prop: self._move_attr_property(p, 1))
            menu.addSeparator()
            missing = self._missing_pdm_values(prop)
            add_menu = menu.addMenu("Add missing value")
            coded_missing = [
                v for v in missing if (getattr(v, "code", "") or "").strip()
            ]
            for pdm_value in coded_missing:
                code = (getattr(pdm_value, "code", "") or "").strip()
                label = f"{pdm_value.value or '(unnamed)'}  [{code}]"
                add_menu.addAction(
                    label,
                    lambda p=prop, v=pdm_value: self._add_pdm_value(p, v),
                )
            if len(coded_missing) > 1:
                add_menu.addSeparator()
                add_menu.addAction(
                    f"Add all {len(coded_missing)} coded missing values",
                    lambda p=prop, vals=coded_missing: self._add_pdm_values(p, vals),
                )
            if not coded_missing:
                add_menu.addAction("No coded missing values", lambda: None).setEnabled(False)
            menu.addAction("Add custom value...", lambda p=prop: self._add_attr_value(p))
        elif data[0] == _KIND_PROP_VALUE:
            parent = item.parent()
            pdata = parent.data(_COL_NAME, Qt.ItemDataRole.UserRole) if parent else None
            if pdata and pdata[0] == _KIND_PROP:
                menu.addAction(
                    "Remove value",
                    lambda p=pdata[1], v=data[1]: self._remove_attr_value(p, v),
                )
        menu.exec(self._attr_tree.viewport().mapToGlobal(pos))

    def _move_attr_property(self, prop, direction: int) -> None:
        cls = self._attribute_class()
        snapshot = self._context.active_snapshot
        if cls is None or snapshot is None:
            return
        service = self._context.engineering_class_service
        if service.move_property(snapshot, cls.id, str(prop.id), direction):
            self._context.snapshot_manager.mark_modified()
            self._sync_development_article_sets()
            self.refresh()

    def _missing_pdm_values(self, prop) -> list:
        """PDM values that are not yet represented by this Class Creation property."""
        cls = self._attribute_class()
        if cls is None:
            return []
        assignment = next(
            (a for a in cls.properties if str(a.property_id) == str(prop.id)), None
        )
        if assignment is None:
            return list(getattr(prop, "values", []) or [])
        existing_ids = {
            str(getattr(v, "value_id", ""))
            for v in assignment.values
            if getattr(v, "value_id", "")
        }
        existing_pairs = {
            ((getattr(v, "code", "") or "").strip(), (getattr(v, "value", "") or "").strip())
            for v in assignment.values
        }
        return [
            value for value in (getattr(prop, "values", []) or [])
            if str(getattr(value, "id", "") or "") not in existing_ids
            and (
                (getattr(value, "code", "") or "").strip(),
                (getattr(value, "value", "") or "").strip(),
            ) not in existing_pairs
        ]

    def _add_pdm_value(self, prop, pdm_value) -> None:
        cls = self._attribute_class()
        snapshot = self._context.active_snapshot
        if cls is None or snapshot is None:
            return
        code = (getattr(pdm_value, "code", "") or "").strip()
        if not code:
            return
        added = self._context.engineering_class_service.add_value(
            snapshot, cls.id, str(prop.id), code,
            (getattr(pdm_value, "value", "") or "").strip(), source="pdm"
        )
        if added is None:
            return
        added.value_id = str(getattr(pdm_value, "id", "") or "")
        self._context.snapshot_manager.mark_modified()
        self._sync_development_article_sets()
        self.refresh()

    def _add_pdm_values(self, prop, values) -> None:
        cls = self._attribute_class()
        snapshot = self._context.active_snapshot
        if cls is None or snapshot is None:
            return
        service = self._context.engineering_class_service
        for pdm_value in values:
            code = (getattr(pdm_value, "code", "") or "").strip()
            if not code:
                continue
            added = service.add_value(
                snapshot, cls.id, str(prop.id), code,
                (getattr(pdm_value, "value", "") or "").strip(), source="pdm"
            )
            if added is not None:
                added.value_id = str(getattr(pdm_value, "id", "") or "")
        self._context.snapshot_manager.mark_modified()
        self._sync_development_article_sets()
        self.refresh()

    def _add_attr_value(self, prop) -> None:
        """Start an inline missing-value entry directly under this property."""
        cls = self._attribute_class()
        snapshot = self._context.active_snapshot
        if cls is None or snapshot is None:
            return
        assignment = next(
            (a for a in cls.properties if str(a.property_id) == str(prop.id)), None
        )
        if assignment is None:
            return

        # The add row is already rendered under the property. Select it and
        # start editing the value name immediately; the user then enters the
        # pre-dot code in the adjacent Code cell.
        self._populating = True
        self._populate_attributes()
        self._populating = False

        for i in range(self._attr_tree.topLevelItemCount()):
            top = self._attr_tree.topLevelItem(i)
            found = self._find_property_item(top, str(prop.id))
            if found is not None:
                for j in range(found.childCount()):
                    child = found.child(j)
                    data = child.data(_COL_NAME, Qt.ItemDataRole.UserRole)
                    if data and data[0] == _KIND_CLASS_VALUE_ADD:
                        self._attr_tree.setCurrentItem(child, _COL_NAME)
                        self._attr_tree.editItem(child, _COL_NAME)
                        return

    def _find_property_item(self, item, property_id: str):
        data = item.data(_COL_NAME, Qt.ItemDataRole.UserRole)
        if data and data[0] == _KIND_PROP and str(getattr(data[1], "id", "")) == property_id:
            return item
        for i in range(item.childCount()):
            found = self._find_property_item(item.child(i), property_id)
            if found is not None:
                return found
        return None

    def _remove_attr_value(self, prop, value) -> None:
        cls = self._attribute_class()
        snapshot = self._context.active_snapshot
        if cls is None or snapshot is None:
            return
        code = (getattr(value, "code", "") or "").strip()
        if not code:
            return
        self._context.engineering_class_service.remove_value(
            snapshot, cls.id, str(prop.id), code
        )
        self._sync_development_article_sets()
        self._context.snapshot_manager.mark_modified()
        self.refresh()

    def _on_visual_context_menu(self, pos) -> None:
        """Right-click: add a value to a definition, or remove a value row."""
        item = self._misc_tree.itemAt(pos)
        if item is None:
            return
        data = item.data(_COL_NAME, Qt.ItemDataRole.UserRole)
        if not data:
            return
        kind = data[0]
        menu = QMenu(self._misc_tree)
        if kind == _KIND_DEFINITION:
            menu.addAction(
                "Add value", lambda d=data[1]: self._add_visual_value(d)
            )
        elif kind == _KIND_CLASS_VALUE:
            parent = item.parent()
            pdata = (
                parent.data(_COL_NAME, Qt.ItemDataRole.UserRole)
                if parent is not None else None
            )
            if pdata:
                menu.addAction(
                    "Remove value",
                    lambda d=pdata[1], v=data[1]: self._remove_visual_value(d, v),
                )
        if menu.isEmpty():
            return
        menu.exec(self._misc_tree.viewport().mapToGlobal(pos))

    @staticmethod
    def _next_code(cls_prop) -> str:
        """Next unused single-letter code (A..Z, then 1..) for a class property."""
        used = {(v.code or "").strip() for v in cls_prop.values}
        for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if c not in used:
                return c
        i = 1
        while str(i) in used:
            i += 1
        return str(i)

    def _add_visual_value(self, definition) -> None:
        cls = self._visual_class()
        if cls is None:
            return
        cls_prop = next(
            (a for a in cls.properties if a.property_id == definition.id), None
        )
        if cls_prop is None:
            return
        self._context.engineering_class_service.add_value(
            self._context.active_snapshot, cls.id, definition.id,
            self._next_code(cls_prop), ""
        )
        self._context.snapshot_manager.mark_modified()
        self.refresh()

    def _remove_visual_value(self, definition, value) -> None:
        cls = self._visual_class()
        if cls is None:
            return
        self._context.engineering_class_service.remove_value(
            self._context.active_snapshot, cls.id, definition.id, value.code
        )
        self._context.snapshot_manager.mark_modified()
        self.refresh()

    @staticmethod
    def _text_block(name: str) -> str:
        """MDB Text-block from a property name: drop a trailing (variant) and
        join capitalised words with '_' (e.g. 'Desk type (A)' -> 'Desk_Type')."""
        base = (name or "").strip()
        if base.endswith(")") and "(" in base:
            base = base[:base.rfind("(")].strip()
        words = base.replace("-", " ").replace("_", " ").split()
        return "_".join(w[:1].upper() + w[1:] for w in words if w)

    def _update_sliced(self, prop_node, prop) -> None:
        cls = self._attribute_class_for_group(self._group_name_for_attr_item(prop_node))
        if cls is None:
            return
        remainings = [r for _code, r in self._split_members()]
        distinct = self._context.engineering_class_service.distinct_slice_codes(
            cls, prop.id, remainings
        )
        width = next(
            (a.width for a in cls.properties if a.property_id == prop.id), 0
        )
        self._apply_sliced(prop_node, prop, distinct, width)

    def _apply_sliced(self, node, prop, distinct, width: int) -> None:
        """Fill the property row's 'Sliced' cell: the discovered order-codes
        plus a value-assignment status that stays visible when the row is
        collapsed. A value is 'unassigned' when it has no code; only an encoded
        property (width > 0) expects codes."""
        text = ", ".join(distinct)
        missing = (
            sum(1 for v in prop.values if not (v.code or "").strip())
            if width
            else 0
        )
        if width and missing:
            text = "\u26A0   " + text
        node.setText(3, text)
        node.setToolTip(
            3,
            f"{missing} of {len(prop.values)} values unassigned"
            if (width and missing)
            else "",
        )
        if width and missing:
            node.setForeground(3, QBrush(QColor(theme.COLOR_WARNING)))
        elif width:
            node.setForeground(3, QBrush(QColor(theme.COLOR_OK)))
        else:
            node.setForeground(3, QBrush())

    def _dependency_icon(self, dependent: bool) -> QIcon:
        """A small coloured box icon: green ticked = drives dependent options,
        red crossed = independent. Built once per state and cached."""
        cache = getattr(self, "_dep_icon_cache", None)
        if cache is None:
            cache = self._dep_icon_cache = {}
        if dependent not in cache:
            glyph = "\u2611" if dependent else "\u2612"  # ☑ / ☒
            color = theme.COLOR_OK if dependent else theme.COLOR_ERROR
            pix = QPixmap(18, 18)
            pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setPen(QColor(color))
            font = painter.font()
            font.setPointSize(12)
            painter.setFont(font)
            painter.drawText(
                pix.rect(), Qt.AlignmentFlag.AlignCenter, glyph
            )
            painter.end()
            cache[dependent] = QIcon(pix)
        return cache[dependent]

    @staticmethod
    def _relation_object(name: str) -> str:
        """Relation-object name for a property: 'B_' + the property name in
        PascalCase - multiple words are joined without spaces, each word's
        first letter capitalised. e.g. 'Number of Fabrics' -> 'B_NumberOfFabrics'.
        """
        if not name:
            return ""
        pascal = "".join(w[:1].upper() + w[1:] for w in name.split())
        return f"B_{pascal}"

    def _prop_relation_object(self, prop) -> str:
        """Property/option relation object name, blank when the attribute is
        generic (none of its values gets a relation)."""
        related = getattr(self, "_related_values", None) or set()
        if any(
            str(getattr(v, "id", "")) in related
            for v in getattr(prop, "values", [])
        ):
            return self._relation_object(getattr(prop, "name", ""))
        return ""

    def _value_relation_object(self, prop, value) -> str:
        """Relation object for a value: the property's relation object plus the
        value's code, e.g. 'B_Colour_R'. Blank for a generic value (no relation)
        or until the value has a code."""
        related = getattr(self, "_related_values", None) or set()
        if str(getattr(value, "id", "")) not in related:
            return ""
        code = (getattr(value, "code", "") or "").strip()
        base = self._relation_object(getattr(prop, "name", ""))
        return f"{base}_{code}" if (base and code) else ""

    def _on_attr_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._populating:
            return
        data = item.data(_COL_NAME, Qt.ItemDataRole.UserRole)
        if not data:
            return
        kind, obj = data
        if kind == _KIND_GROUP and column == _COL_NAME:
            self._rename_group_inline(obj, item.text(_COL_NAME))
            return
        if kind == _KIND_PROP and column == _COL_NAME:
            # Selecting a property selects its whole value-list (MDB semantics).
            selected = item.checkState(_COL_NAME) == Qt.CheckState.Checked
            self._context.property_service.set_selected(obj, selected)
            for value in obj.values:
                self._context.property_value_service.set_selected(value, selected)
            self._context.snapshot_manager.mark_modified()
            return
        if kind == _KIND_PROP and column == 2:
            text = item.text(2).strip()
            width = int(text) if text.isdigit() else 0
            cls = self._attribute_class_for_group(self._group_name_for_attr_item(item))
            if cls is not None:
                self._context.engineering_class_service.set_width(
                    self._context.active_snapshot, cls.id, obj.id, width
                )
                self._sync_development_article_sets()
                self._context.snapshot_manager.mark_modified()
            self._populating = True
            self._populate_attributes()
            self._populating = False
        elif kind == _KIND_PROP and column == _COL_TEXTBLOCK:
            cls = self._attribute_class_for_group(self._group_name_for_attr_item(item))
            cls_prop = next(
                (a for a in cls.properties if a.property_id == obj.id), None
            ) if cls is not None else None
            if cls_prop is not None:
                cls_prop.text_block = item.text(_COL_TEXTBLOCK).strip()
                self._context.snapshot_manager.mark_modified()
        elif kind == _KIND_PROP_VALUE and column == 1:
            # Accepting/correcting one config value also commits the rest of its
            # property's inferred codes, so it becomes cleanly, fully coded.
            new_code = item.text(1).strip()
            group_name = self._group_name_for_attr_item(item)
            self._set_active_group_from_attr_item(item)
            self._commit_property_inferred(obj, group_name)
            class_value = self._class_value_for(
                str(getattr(next(
                    (p for p in self._context.active_snapshot.properties
                     if any(v is obj for v in p.values)), None
                ), "id", "")),
                str(getattr(obj, "id", "")),
                group_name,
            )
            if class_value is not None:
                class_value.code = new_code
            else:
                obj.code = new_code
            self._sync_development_article_sets()
            # Remember the owning property so its cells stay editable next time.
            snapshot = self._context.active_snapshot
            prop = next(
                (p for p in (snapshot.properties if snapshot else [])
                 if any(v is obj for v in p.values)), None
            )
            if prop is not None:
                self._user_edited_props.add(str(prop.id))
            self._context.snapshot_manager.mark_modified()
            self._populating = True
            self._populate_attributes()
            self._populating = False

    def _commit_property_inferred(self, value, group_name: str | None = None) -> None:
        """Persist inferred configuration codes into the engineering class,
        never into the PDM source value objects."""
        snapshot = self._context.active_snapshot
        if snapshot is None:
            return
        prop = next(
            (p for p in snapshot.properties if any(v is value for v in p.values)),
            None,
        )
        if prop is None:
            return
        mapping = self._context.engineering_class_service.resolve_config_codes(
            snapshot
        ).get(str(prop.id)) or {}
        cls = self._attribute_class_for_group(group_name)
        if cls is None:
            return
        assignment = next(
            (a for a in cls.properties if str(a.property_id) == str(prop.id)),
            None,
        )
        if assignment is None:
            return
        for class_value in getattr(assignment, "values", []) or []:
            code = mapping.get(str(getattr(class_value, "value_id", "")))
            if code and not (getattr(class_value, "code", "") or "").strip():
                class_value.code = code

    def _on_attr_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Expand properties, or start the direct inline missing-value entry."""
        if item is None:
            return
        self._set_active_group_from_attr_item(item)
        data = item.data(_COL_NAME, Qt.ItemDataRole.UserRole)
        if data and data[0] == _KIND_CLASS_VALUE_ADD:
            self._attr_tree.setCurrentItem(item, _COL_NAME)
            self._attr_tree.editItem(item, _COL_NAME)
            return
        if item.childCount() == 0:
            return
        item.setExpanded(not item.isExpanded())

    def _on_opt_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        """Clicking an option (top-level) row toggles its value rows open."""
        if item is None or item.childCount() == 0:
            return
        item.setExpanded(not item.isExpanded())

    def _populate_options(self) -> None:
        # Preserve which range group headers are collapsed across a rebuild.
        collapsed_groups: set = set()
        for i in range(self._opt_tree.topLevelItemCount()):
            node = self._opt_tree.topLevelItem(i)
            ndata = node.data(_COL_NAME, Qt.ItemDataRole.UserRole)
            if ndata and ndata[0] == _KIND_GROUP and not node.isExpanded():
                collapsed_groups.add(ndata[1])
        self._opt_tree.clear()
        cls = self._options_class()
        options = list(self._context.option_service.get_options())

        # Same functional grouping as Attributes, computed from the product
        # option links: option value -> ProductRange(s), option -> their union.
        # When the load spans ranges (desk / screen / wire management) group the
        # options under a header per range and show only that range's values;
        # a single-range load stays flat.
        snapshot = self._context.active_snapshot
        self._related_values = (
            self._context.engineering_relation_service.related_value_ids(snapshot)
        )
        product_range = getattr(snapshot, "product_range", None) or {}
        product_opt_vals = getattr(snapshot, "product_option_value_ids", None) or {}
        ignored = set(getattr(snapshot, "ignored_ranges", None) or [])
        optval_ranges: dict[str, set] = {}
        for pid, vids in product_opt_vals.items():
            rng = product_range.get(str(pid))
            if not rng:
                continue
            for vid in vids:
                optval_ranges.setdefault(str(vid), set()).add(rng)
        opt_ranges: dict[str, set] = {}
        for option in options:
            rs: set = set()
            for v in getattr(option, "values", []):
                rs |= optval_ranges.get(str(v.id), set())
            opt_ranges[str(option.id)] = rs

        # When the split is on, show only the active group's options.
        group = self._active_group() if getattr(
            snapshot, "split_classes_by_group", False
        ) else None
        if group is not None:
            gids = set(group.option_ids)
            options = [o for o in options if str(o.id) in gids]

        all_ranges = {
            r for rs in opt_ranges.values() for r in rs if r not in ignored
        }
        if len(all_ranges) > 1:
            def _group_rank(gname: str) -> int:
                for i, o in enumerate(options):
                    if gname in opt_ranges.get(str(o.id), set()):
                        return i
                return 10_000
            for gname in sorted(all_ranges, key=_group_rank):
                gnode = self._make_group_node(
                    self._opt_tree, gname, gname, collapsed_groups
                )
                for option in options:
                    if gname in opt_ranges.get(str(option.id), set()):
                        vids = {
                            str(v.id) for v in getattr(option, "values", [])
                            if gname in optval_ranges.get(str(v.id), set())
                        }
                        self._add_option_node(
                            gnode, option, cls, value_ids=vids or None
                        )
            orphans = [o for o in options if not opt_ranges.get(str(o.id))]
            if orphans:
                gnode = self._make_group_node(
                    self._opt_tree, "General", "__none_opt__", collapsed_groups
                )
                for option in orphans:
                    self._add_option_node(gnode, option, cls)
        else:
            for option in options:
                self._add_option_node(self._opt_tree, option, cls)

    def _add_option_node(self, parent, option, cls, value_ids=None) -> None:
        # Values shown under a range group are limited to the ones that range's
        # products carry; unfiltered (value_ids None) elsewhere.
        values = [
            v for v in getattr(option, "values", [])
            if value_ids is None or str(v.id) in value_ids
        ]
        # Options carry standard codes -> fully-coded independent display:
        # Width = code length, Sliced = the value codes (no article slicing).
        value_codes: list[str] = []
        for v in values:
            c = (getattr(v, "code", "") or "").strip()
            if c and c not in value_codes:
                value_codes.append(c)
        width = max((len(c) for c in value_codes), default=0)
        cls_prop = next(
            (a for a in cls.properties if a.property_id == option.id), None
        ) if cls else None
        text_block = (
            cls_prop.text_block if (cls_prop and cls_prop.text_block)
            else self._text_block(option.name)
        )
        item = QTreeWidgetItem(
            parent,
            [
                f"{option.name or '-'} ({len(values)})",
                option.code or "-",
                str(width),
                "",  # legacy Sliced column (hidden)
                "",  # Type (combo)
                "",  # Usage (combo)
                "",  # legacy Text-block column (hidden)
                self._prop_relation_object(option),
                "",
            ],
        )
        item.setData(_COL_NAME, Qt.ItemDataRole.UserRole, (_KIND_OPTION, option))
        item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
            | Qt.ItemFlag.ItemIsUserCheckable
        )
        item.setCheckState(
            _COL_NAME,
            Qt.CheckState.Checked
            if getattr(option, "selected", False)
            else Qt.CheckState.Unchecked,
        )
        item.setToolTip(_COL_SLICED, ", ".join(value_codes))
        if value_codes:
            item.setForeground(_COL_SLICED, QBrush(QColor(theme.COLOR_OK)))
        # Type dropdown (C/L/N/T) - stored on the _Options class assignment.
        type_combo = QComboBox()
        for code, desc in _TYPE_OPTIONS:
            display = f"{code} - {desc}" if code and desc else ""
            type_combo.addItem(display, code)
        if cls_prop and cls_prop.type:
            idx = next(
                (i for i in range(type_combo.count())
                 if type_combo.itemData(i) == cls_prop.type),
                0
            )
            type_combo.setCurrentIndex(idx)
        type_combo.setMinimumHeight(26)
        type_combo.currentIndexChanged.connect(
            lambda idx, o_id=option.id, combo=type_combo: (
                self._on_opt_type_selected(o_id, combo.itemData(idx))
                if idx >= 0 else None
            )
        )
        self._opt_tree.setItemWidget(item, _COL_TYPE, type_combo)
        item.setSizeHint(_COL_TYPE, type_combo.sizeHint())
        # Usage dropdown (Configuration | Graphic).
        usage_combo = QComboBox()
        for usage in _USAGE_OPTIONS:
            usage_combo.addItem(usage)
        if cls_prop and cls_prop.usage:
            pos = usage_combo.findText(cls_prop.usage)
            usage_combo.setCurrentIndex(pos if pos >= 0 else 0)
        usage_combo.setMinimumHeight(26)
        usage_combo.currentTextChanged.connect(
            lambda text, o_id=option.id: self._on_opt_usage_selected(o_id, text)
        )
        self._opt_tree.setItemWidget(item, _COL_USAGE, usage_combo)
        item.setSizeHint(_COL_USAGE, usage_combo.sizeHint())
        # Value rows (expand to view the option's values + order codes).
        for value in _by_display_order(values):
            opt_code = (value.code or "").strip().replace("#", "")
            opt_tb = (
                f"{self._text_block(option.name)}_{opt_code}" if opt_code else ""
            )
            child = QTreeWidgetItem(
                item,
                [
                    value.value or "-",
                    value.code or "",
                    "", "", "", "",
                    opt_tb,
                    self._value_relation_object(option, value),
                ],
            )
            child.setFlags(
                Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            )

    def _populate_visual(self) -> None:
        # Rebuilding the tree destroys its existing QTreeWidgetItems. Block
        # itemChanged while clearing/recreating them so a queued edit signal
        # cannot re-enter refresh() and delete the item currently being built.
        blocker = QSignalBlocker(self._misc_tree)
        self._misc_tree.clear()
        cls = self._visual_class()
        snapshot = self._context.active_snapshot
        if snapshot is not None and snapshot.engineering is not None:
            group = self._active_group() if getattr(
                snapshot, "split_classes_by_group", False
            ) else None
            gids = set(group.visual_ids) if group is not None else None
            for definition in sorted(
                snapshot.engineering.properties, key=lambda d: d.order
            ):
                if gids is not None and str(definition.id) not in gids:
                    continue
                cls_prop = next(
                    (a for a in cls.properties if a.property_id == definition.id), None
                ) if cls else None
                text_block = (
                    cls_prop.text_block if (cls_prop and cls_prop.text_block)
                    else self._text_block(definition.name)
                )
                item = QTreeWidgetItem(
                    self._misc_tree,
                    [
                        definition.name or "-",
                        "",  # Code (definitions have no order code)
                        "",  # legacy Width (hidden)
                        "",  # legacy Sliced (hidden)
                        "",  # Type (combo)
                        "",  # Usage (combo)
                        "",  # legacy Text-block (hidden)
                        self._relation_object(definition.name),
                        "",
                    ],
                )
                item.setData(
                    _COL_NAME, Qt.ItemDataRole.UserRole, (_KIND_DEFINITION, definition)
                )
                item.setData(_COL_NAME, Qt.ItemDataRole.UserRole + 1, {_COL_NAME})
                item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsEditable
                )
                # Type dropdown (C/L/N/T) - stored on the _Visual assignment.
                type_combo = QComboBox()
                for code, desc in _TYPE_OPTIONS:
                    display = f"{code} - {desc}" if code and desc else ""
                    type_combo.addItem(display, code)
                if cls_prop and cls_prop.type:
                    idx = next(
                        (i for i in range(type_combo.count())
                         if type_combo.itemData(i) == cls_prop.type),
                        0
                    )
                    type_combo.setCurrentIndex(idx)
                type_combo.setMinimumHeight(26)
                type_combo.currentIndexChanged.connect(
                    lambda idx, d_id=definition.id, combo=type_combo: (
                        self._on_visual_type_selected(d_id, combo.itemData(idx))
                        if idx >= 0 else None
                    )
                )
                self._misc_tree.setItemWidget(item, _COL_TYPE, type_combo)
                item.setSizeHint(_COL_TYPE, type_combo.sizeHint())
                # Usage dropdown (Configuration | Graphic).
                usage_combo = QComboBox()
                for usage in _USAGE_OPTIONS:
                    usage_combo.addItem(usage)
                if cls_prop and cls_prop.usage:
                    pos = usage_combo.findText(cls_prop.usage)
                    usage_combo.setCurrentIndex(pos if pos >= 0 else 0)
                usage_combo.setMinimumHeight(26)
                usage_combo.currentTextChanged.connect(
                    lambda text, d_id=definition.id: self._on_visual_usage_selected(d_id, text)
                )
                self._misc_tree.setItemWidget(item, _COL_USAGE, usage_combo)
                item.setSizeHint(_COL_USAGE, usage_combo.sizeHint())
                # Manually-added value rows (Value + Code, both editable).
                for cv in (cls_prop.values if cls_prop else []):
                    child = QTreeWidgetItem(
                        item,
                        [cv.value or "", cv.code or "", "", "", "", "", "", ""],
                    )
                    child.setData(
                        _COL_NAME, Qt.ItemDataRole.UserRole, (_KIND_CLASS_VALUE, cv)
                    )
                    child.setData(_COL_NAME, Qt.ItemDataRole.UserRole + 1, {_COL_NAME})
                    child.setData(_COL_CODE, Qt.ItemDataRole.UserRole + 1, {_COL_CODE})
                    child.setFlags(
                        Qt.ItemFlag.ItemIsEnabled
                        | Qt.ItemFlag.ItemIsSelectable
                        | Qt.ItemFlag.ItemIsEditable
                    )
                if cls_prop and cls_prop.values:
                    item.setExpanded(True)
        # Trailing "type to add" row (no buttons).
        add_item = QTreeWidgetItem(
            self._misc_tree, [_ADD_HINT, "", "", "", "", "", "", ""]
        )
        add_item.setData(_COL_NAME, Qt.ItemDataRole.UserRole, (_KIND_ADD, None))
        add_item.setData(_COL_NAME, Qt.ItemDataRole.UserRole + 1, {_COL_NAME})
        add_item.setFlags(
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
        )
        add_item.setForeground(_COL_NAME, Qt.GlobalColor.gray)
        del blocker

    # -- interaction -------------------------------------------------------
    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._populating:
            return
        data = item.data(_COL_NAME, Qt.ItemDataRole.UserRole)
        if not data:
            return
        kind, obj = data

        if kind == _KIND_GROUP and column == _COL_NAME:
            self._rename_group_inline(obj, item.text(_COL_NAME))
            return

        if kind == _KIND_PROP_VALUE:
            if column == _COL_SELECTED:
                selected = item.checkState(_COL_SELECTED) == Qt.CheckState.Checked
                self._context.property_value_service.set_selected(obj, selected)
            elif column == _COL_CODE:
                obj.code = item.text(_COL_CODE).strip()
            return

        if kind == _KIND_CLASS_VALUE_ADD:
            _cls_prop, prop = obj
            value = item.text(_COL_NAME).strip()
            code = item.text(_COL_CODE).strip()
            if value == _ADD_VALUE_HINT:
                value = ""
            # Do not interrupt typing. The row becomes a value only when both
            # Name and Code are present.
            if not value or not code:
                return
            cls = self._attribute_class()
            snapshot = self._context.active_snapshot
            if cls is None or snapshot is None:
                return
            cv = self._context.engineering_class_service.add_value(
                snapshot,
                cls.id,
                str(prop.id),
                code,
                value,
                source="manual",
            )
            if cv is None:
                return
            self._context.snapshot_manager.mark_modified()
            self._sync_development_article_sets()
            self._populating = True
            self._populate_attributes()
            self._populating = False
            return

        if kind == _KIND_OPTION:
            if column == _COL_NAME:
                # Selecting an option selects its whole value-list (MDB semantics).
                selected = item.checkState(_COL_NAME) == Qt.CheckState.Checked
                self._context.option_service.set_selected(obj, selected)
                for value in getattr(obj, "values", []):
                    self._context.option_value_service.set_selected(value, selected)
                self._context.snapshot_manager.mark_modified()
            elif column == _COL_TEXTBLOCK:
                cls = self._options_class()
                cls_prop = next(
                    (a for a in cls.properties if a.property_id == obj.id), None
                ) if cls else None
                if cls_prop is not None:
                    cls_prop.text_block = item.text(_COL_TEXTBLOCK).strip()
                    self._context.snapshot_manager.mark_modified()
            return

        if kind == _KIND_CLASS_VALUE:
            cls = self._visual_class()
            parent = item.parent()
            pdata = (
                parent.data(_COL_NAME, Qt.ItemDataRole.UserRole)
                if parent is not None else None
            )
            if cls is None or not pdata:
                return
            definition = pdata[1]
            if column == _COL_NAME:
                self._context.engineering_class_service.set_value_name(
                    self._context.active_snapshot, cls.id, definition.id,
                    obj.code, item.text(_COL_NAME).strip()
                )
                self._context.snapshot_manager.mark_modified()
            elif column == _COL_CODE:
                self._context.engineering_class_service.set_value_code(
                    self._context.active_snapshot, cls.id, definition.id,
                    obj.code, item.text(_COL_CODE).strip()
                )
                self._context.snapshot_manager.mark_modified()
                self._populating = True
                self._populate_visual()
                self._populating = False
            return

        if kind == _KIND_DEFINITION:
            if column == _COL_NAME:
                new_name = item.text(_COL_NAME).strip()
                if new_name:
                    self._context.engineering_property_service.rename_property(
                        self._context.active_snapshot, obj.id, new_name
                    )
                self.refresh()
            elif column == _COL_TEXTBLOCK:
                cls = self._visual_class()
                cls_prop = next(
                    (a for a in cls.properties if a.property_id == obj.id), None
                ) if cls else None
                if cls_prop is not None:
                    cls_prop.text_block = item.text(_COL_TEXTBLOCK).strip()
                    self._context.snapshot_manager.mark_modified()
            return

        if kind == _KIND_ADD and column == _COL_NAME:
            name = item.text(_COL_NAME).strip()
            if name and name != _ADD_HINT:
                self._context.engineering_property_service.create_property(
                    self._context.active_snapshot, name
                )
            self.refresh()
            return

    def _delete_definition(self, item: QTreeWidgetItem) -> bool:
        """Remove the engineered property (or a value row) under ``item``."""
        data = item.data(_COL_NAME, Qt.ItemDataRole.UserRole)
        if data and data[0] == _KIND_DEFINITION:
            self._context.engineering_property_service.delete_property(
                self._context.active_snapshot, data[1].id
            )
            self.refresh()
            return True
        if data and data[0] == _KIND_CLASS_VALUE:
            parent = item.parent()
            pdata = (
                parent.data(_COL_NAME, Qt.ItemDataRole.UserRole)
                if parent is not None else None
            )
            if pdata:
                self._remove_visual_value(pdata[1], data[1])
                return True
        return False

    # -- filtering ---------------------------------------------------------
    def _apply_filter(self, *_args) -> None:
        term = self._search.text().strip()
        self._filter_nested(self._attr_tree, term)
        self._filter_flat(self._opt_tree, term)
        self._filter_flat(self._misc_tree, term, keep_add=True)

    def _filter_flat(self, tree: QTreeWidget, term: str, keep_add: bool = False) -> None:
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            data = item.data(_COL_NAME, Qt.ItemDataRole.UserRole)
            if keep_add and data and data[0] == _KIND_ADD:
                item.setHidden(False)
                continue
            match = not term or text_match(
                term, item.text(_COL_NAME), item.text(_COL_CODE)
            )
            item.setHidden(bool(term) and not match)

    def _filter_nested(self, tree: QTreeWidget, term: str) -> None:
        for i in range(tree.topLevelItemCount()):
            self._filter_item(tree.topLevelItem(i), term)

    def _filter_item(self, item: QTreeWidgetItem, term: str,
                     parent_match: bool = False) -> bool:
        """Hide/reveal an item and its descendants for the search term.

        A match on an ancestor reveals the whole branch; any descendant match
        reveals its ancestors. Handles arbitrary depth (Set -> property ->
        value)."""
        self_match = parent_match or not term or text_match(
            term, item.text(_COL_NAME), item.text(_COL_CODE)
        )
        child_visible = False
        for c in range(item.childCount()):
            if self._filter_item(item.child(c), term, self_match):
                child_visible = True
        visible = self_match or child_visible
        item.setHidden(bool(term) and not visible)
        if term and visible and item.childCount():
            item.setExpanded(True)  # reveal matches
        return visible