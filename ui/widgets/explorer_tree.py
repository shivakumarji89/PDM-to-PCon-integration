"""Standard tree / explorer framework for the Engineering Workbench.

One reusable behaviour set applied to every explorer tree so navigation feels
consistent everywhere (Solution Explorer / Feature Manager style): expand /
collapse, uniform indentation and row height, a right-click context menu,
copy, keyboard navigation and optional persistence of expanded / selected
state. Presentation only - no engineering logic.

Use :func:`standardize_tree` to upgrade an existing ``QTreeWidget`` in place,
or subclass :class:`ExplorerTree` for new explorers.
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import QMenu, QTreeWidget, QTreeWidgetItem


def standardize_tree(tree: QTreeWidget, *, settings_key: str | None = None) -> None:
    """Apply the standard explorer behaviours to ``tree`` in place."""
    if tree.property("_ews_standardized"):
        return
    tree.setProperty("_ews_standardized", True)

    tree.setUniformRowHeights(True)
    tree.setAnimated(True)
    tree.setExpandsOnDoubleClick(True)
    tree.setIndentation(16)
    tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    tree.customContextMenuRequested.connect(
        lambda pos, t=tree: _show_menu(t, pos)
    )

    shortcut = QShortcut(QKeySequence.StandardKey.Copy, tree)
    shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
    shortcut.activated.connect(lambda t=tree: _copy_current(t))

    if settings_key:
        _bind_persistence(tree, settings_key)


class ExplorerTree(QTreeWidget):
    """A ``QTreeWidget`` with the standard explorer behaviours built in."""

    def __init__(self, parent=None, *, settings_key: str | None = None) -> None:
        super().__init__(parent)
        standardize_tree(self, settings_key=settings_key)

    def filter(self, text: str) -> int:
        """Filter leaves by ``text``; hide empty groups. Returns visible count."""
        return filter_tree(self, text)


def filter_tree(tree: QTreeWidget, text: str) -> int:
    """Hide items whose label (and whose descendants' labels) do not match."""
    low = text.strip().lower()

    def visit(item: QTreeWidgetItem) -> bool:
        child_match = False
        for i in range(item.childCount()):
            child_match = visit(item.child(i)) or child_match
        self_match = not low or low in item.text(0).lower()
        visible = self_match or child_match
        item.setHidden(not visible)
        return visible

    count = 0
    for i in range(tree.topLevelItemCount()):
        if visit(tree.topLevelItem(i)):
            count += 1
    return count


# -- context menu ----------------------------------------------------------
def _show_menu(tree: QTreeWidget, pos: QPoint) -> None:
    menu = QMenu(tree)
    expand = menu.addAction("Expand All")
    collapse = menu.addAction("Collapse All")
    menu.addSeparator()
    item = tree.itemAt(pos)
    copy = menu.addAction("Copy")
    copy.setEnabled(item is not None)

    chosen = menu.exec(tree.viewport().mapToGlobal(pos))
    if chosen is expand:
        tree.expandAll()
    elif chosen is collapse:
        tree.collapseAll()
    elif chosen is copy and item is not None:
        _copy_item(tree, item)


def _copy_current(tree: QTreeWidget) -> None:
    items = tree.selectedItems()
    if items:
        _copy_item(tree, items[0])


def _copy_item(tree: QTreeWidget, item: QTreeWidgetItem) -> None:
    columns = max(1, tree.columnCount())
    text = "\t".join(item.text(c) for c in range(columns)).strip()
    QGuiApplication.clipboard().setText(text)


# -- optional persistence --------------------------------------------------
def _bind_persistence(tree: QTreeWidget, settings_key: str) -> None:
    from PySide6.QtCore import QSettings

    def save() -> None:
        expanded = []
        for i in range(tree.topLevelItemCount()):
            _collect_expanded(tree.topLevelItem(i), (i,), expanded)
        QSettings().setValue(f"trees/{settings_key}/expanded", expanded)

    tree.itemExpanded.connect(lambda *_: save())
    tree.itemCollapsed.connect(lambda *_: save())


def _collect_expanded(item: QTreeWidgetItem, path, out: list) -> None:
    if item.isExpanded():
        out.append(list(path))
    for i in range(item.childCount()):
        _collect_expanded(item.child(i), (*path, i), out)
