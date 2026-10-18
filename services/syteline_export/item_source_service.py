"""Read-only adapter for the legacy item-selection query."""
from __future__ import annotations

from typing import Any, Callable

from repositories.pdm_repository import PDMRepository
from services.syteline_export.item_selection_query import (
    ItemSelection,
    ItemSelectionQuery,
    build_item_selection_query,
)


class SyteLineItemSourceService:
    """Execute the source-mapped item query and return rows by column name."""

    def __init__(
        self,
        context: Any = None,
        connection_factory: Callable[[], Any] | None = None,
    ) -> None:
        if context is None and connection_factory is None:
            raise ValueError("A PDM context or connection factory is required.")
        self._context = context
        self._connection_factory = connection_factory

    def _connect(self):
        if self._connection_factory is not None:
            return self._connection_factory()
        return PDMRepository(self._context).get_connection()

    @staticmethod
    def build_query(selection: ItemSelection) -> ItemSelectionQuery:
        return build_item_selection_query(selection)

    def fetch_items(self, selection: ItemSelection) -> list[dict[str, Any]]:
        query = build_item_selection_query(selection)
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.timeout = 600
            cursor.execute(query.sql, *query.parameters)
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            connection.close()
