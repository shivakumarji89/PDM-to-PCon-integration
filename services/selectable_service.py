"""Selection engine.

A reusable base service for workspaces that operate on a selectable collection
held in the active snapshot. It standardises selection behaviour (select,
deselect, select all, clear, selected list/count) so every workspace service
shares one implementation instead of duplicating it.

Selection is stored on each item's ``selected`` attribute and therefore lives
entirely in the in-memory snapshot - no database writes.
"""
from __future__ import annotations

from typing import Any

from services.base_service import BaseService


class SelectableSnapshotService(BaseService):
    """Base for services exposing a selectable snapshot collection."""

    def items(self) -> list[Any]:
        """Return the managed collection from the active snapshot.

        Subclasses override this to return the relevant snapshot list (e.g.
        ``snapshot.articles``). Returns an empty list when nothing is loaded.
        """
        return []

    # -- selection ---------------------------------------------------------
    def selected(self) -> list[Any]:
        return [item for item in self.items() if getattr(item, "selected", False)]

    def selected_count(self) -> int:
        return sum(1 for item in self.items() if getattr(item, "selected", False))

    def set_selected(self, item: Any, selected: bool) -> None:
        item.selected = bool(selected)

    def select_all(self) -> None:
        for item in self.items():
            item.selected = True

    def clear_selection(self) -> None:
        for item in self.items():
            item.selected = False
