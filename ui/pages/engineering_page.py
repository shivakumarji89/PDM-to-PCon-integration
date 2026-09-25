"""Engineering workspace page (read-only).

Visualizes the engineering hierarchy already built in the active snapshot:

    Engineering
      Default Family
        Member 1
        Member 2

It is strictly read-only - it renders the snapshot's engineering families and
members and never creates, edits, moves, or deletes them, and never touches the
engineering models or the initialization service.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QInputDialog,
    QMenu,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from ui.pages.base_page import BasePage


class EngineeringPage(BasePage):
    """Read-only view of the snapshot's engineering families and members.

    Family management (create / rename / delete) is available from a right-click
    context menu; members themselves are not edited here.
    """

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Engineering",
            description="Engineering families and members. Right-click to manage families.",
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context

        self._tree = QTreeWidget(self)
        self._tree.setObjectName("engineeringTree")
        self._tree.setHeaderLabel("Engineering")
        self._tree.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        # This workspace provides its own family context menu, so it opts out of
        # the generic shared tree menu (Expand/Collapse/Copy).
        self._tree.setProperty("_ews_standardized", True)
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_menu)
        self.add_content(self._tree)

        self.refresh()

    def refresh(self) -> None:
        """Rebuild the tree from the active snapshot's engineering hierarchy.

        Read-only rendering: it reads ``snapshot.engineering`` and stores each
        family on its node so the context menu can act on it. It never mutates
        an engineering object.
        """
        self._tree.clear()
        snapshot = self._context.active_snapshot
        engineering = snapshot.engineering if snapshot is not None else None
        families = list(engineering.families) if engineering is not None else []

        root = QTreeWidgetItem(self._tree, ["Engineering"])
        for family in families:
            family_node = QTreeWidgetItem(
                root, [f"{family.name} ({len(family.members)})"]
            )
            family_node.setData(0, Qt.ItemDataRole.UserRole, family)
            for index, member in enumerate(family.members, start=1):
                member_node = QTreeWidgetItem(
                    family_node, [f"Member {index}: {member.id}"]
                )
                member_node.setData(0, Qt.ItemDataRole.UserRole, member)
        self._tree.expandAll()

    # -- family management (context menu) ---------------------------------
    def _show_menu(self, pos) -> None:
        item = self._tree.itemAt(pos)
        data = item.data(0, Qt.ItemDataRole.UserRole) if item is not None else None
        snapshot = self._context.active_snapshot

        # Member node -> member management (Move To).
        if isinstance(data, MemberArticle):
            self._show_member_menu(pos, data, snapshot)
            return

        # Family / root node -> family management.
        service = self._context.engineering_family_service
        menu = QMenu(self._tree)
        create = menu.addAction("Create Family")

        rename = None
        delete = None
        if isinstance(data, EngineeringFamily):
            is_default = service.is_default(data)
            rename = menu.addAction("Rename Family")
            rename.setEnabled(not is_default)
            delete = menu.addAction("Delete Family")
            # Deletable only when it is not the Default Family and is empty.
            delete.setEnabled(not is_default and not data.members)

        chosen = menu.exec(self._tree.viewport().mapToGlobal(pos))
        if chosen is None:
            return

        if chosen is create:
            service.create_family(snapshot)
            self.refresh()
        elif rename is not None and chosen is rename:
            new_name, ok = QInputDialog.getText(
                self, "Rename Family", "Family name:", text=data.name
            )
            if ok and new_name.strip():
                service.rename_family(snapshot, data, new_name)
                self.refresh()
        elif delete is not None and chosen is delete:
            service.delete_family(snapshot, data)
            self.refresh()

    # -- member management (context menu) ---------------------------------
    def _show_member_menu(self, pos, member, snapshot) -> None:
        service = self._context.engineering_member_service
        source = service.get_member_family(snapshot, member)
        families = (
            list(snapshot.engineering.families)
            if snapshot is not None and snapshot.engineering is not None
            else []
        )

        menu = QMenu(self._tree)
        move_to = menu.addMenu("Move To")
        destinations = {}
        for family in families:
            if family is source:
                continue
            action = move_to.addAction(family.name)
            destinations[action] = family
        # No other family to move into -> nothing selectable.
        move_to.setEnabled(bool(destinations))

        chosen = menu.exec(self._tree.viewport().mapToGlobal(pos))
        if chosen in destinations:
            service.move_member(snapshot, member, destinations[chosen])
            self.refresh()

