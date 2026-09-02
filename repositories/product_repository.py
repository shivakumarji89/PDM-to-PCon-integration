"""Product repository (placeholder - no data access in Phase 2)."""
from __future__ import annotations

from repositories.base_repository import BaseRepository


class ProductRepository(BaseRepository):
    """Data access for :class:`~models.product.Product` records."""

    def get_all(self) -> list:
        raise NotImplementedError

    def get_by_id(self, product_id: str):
        raise NotImplementedError

    def search(self, term: str) -> list:
        raise NotImplementedError
