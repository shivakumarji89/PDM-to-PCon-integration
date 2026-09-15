"""Read-only legacy-PDM compatibility queries.

This module is deliberately isolated from the production reduction engine.  It
contains only the PDM reads needed to reconstruct an existing Item using the
same metadata used by the legacy DPS/PDM workflow.

No reduction decision is made here and no database write is performed.
"""
from __future__ import annotations

from typing import Any, Sequence

from repositories.pdm_repository import PDMRepository


class LegacyPDMCompatRepository(PDMRepository):
    """Additional read-only queries required for legacy compatibility checks."""

    ITEM_OPTIONS_QUERY = """
        SELECT
            iov.ItemId,
            o.OptionId,
            o.Name AS OptionName,
            o.OrderCodeFormatKey,
            o.DisplayOrder,
            ov.OptionValueId,
            ov.Name AS ValueName,
            ov.OrderCodeValue,
            ov.DisplayOrdinal
        FROM ItemOptionValues iov WITH (NOLOCK)
        INNER JOIN OptionValue ov
            ON iov.OptionValueId = ov.OptionValueId
        INNER JOIN [Option] o
            ON ov.OptionId = o.OptionId
        WHERE iov.ItemId = ?
          AND ov.Status = 1
        ORDER BY o.DisplayOrder, ov.DisplayOrdinal
    """

    PRODUCT_OCFS_QUERY = """
        SELECT TOP 1
            p.ProductId,
            p.Product,
            p.OrderCodeFormatString AS ProductOrderCodeFormatString,
            pr.ProductRangeId,
            pr.Name AS RangeName,
            pr.OrderCodeFormatString AS RangeOrderCodeFormatString
        FROM Product p WITH (NOLOCK)
        INNER JOIN ProductRange pr
            ON p.ProductRangeId = pr.ProductRangeId
        WHERE p.ProductId = ?
    """

    def fetch_item_options(self, item_id: Any, connection: Any = None) -> list[Any]:
        """Return the actual option values carried by one Item."""
        return self._execute(self.ITEM_OPTIONS_QUERY, (item_id,), connection=connection)

    def fetch_product_ocfs(self, product_id: Any, connection: Any = None) -> list[Any]:
        """Return Product OCFS plus ProductRange fallback OCFS.

        Legacy validation uses Product.OrderCodeFormatString when present and
        otherwise ProductRange.OrderCodeFormatString.
        """
        return self._execute(self.PRODUCT_OCFS_QUERY, (product_id,), connection=connection)

    def fetch_items_for_products(
        self, product_ids: Sequence[Any], connection: Any = None
    ) -> list[Any]:
        """Return ItemId/ProductId/Item for a product set."""
        ids = [pid for pid in product_ids if pid is not None]
        rows: list[Any] = []
        for chunk in self._chunked(ids, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = (
                "SELECT i.ProductId, i.ItemId, i.Item, i.Status, i.IsSuperItem "
                "FROM Item i WITH (NOLOCK) "
                f"WHERE i.ProductId IN ({ph}) "
                "ORDER BY i.ProductId, i.Item"
            )
            rows.extend(self._execute(query, tuple(chunk), connection=connection))
        return rows

    def fetch_product_attribute_values_full(
        self, product_id: Any, connection: Any = None
    ) -> list[Any]:
        """Return the complete ProductAttributeValues metadata needed by the
        compatibility layer, including AttributeId/ValueId, key, type, display
        order and the stored OrderCodeValue.
        """
        query = """
            SELECT
                pav.ProductId,
                a.AttributeId,
                a.Name AS AttributeName,
                a.AttributeType,
                a.OrderCodeFormatKey,
                a.DisplayOrder,
                a.HasDependentOptions,
                av.AttributeValueId,
                av.Name AS ValueName,
                av.OrderCodeValue,
                av.DisplayOrdinal
            FROM ProductAttributeValues pav WITH (NOLOCK)
            INNER JOIN AttributeValue av
                ON pav.AttributeValueId = av.AttributeValueId
            INNER JOIN Attribute a
                ON av.AttributeId = a.AttributeId
            WHERE pav.ProductId = ?
              AND av.Status = 1
            ORDER BY a.DisplayOrder, av.DisplayOrdinal
        """
        return self._execute(query, (product_id,), connection=connection)

    def fetch_item_attribute_values_full(
        self, item_id: Any, connection: Any = None
    ) -> list[Any]:
        """Return the complete BaseAttributeValues metadata for one Item."""
        query = """
            SELECT
                bav.ItemId,
                a.AttributeId,
                a.Name AS AttributeName,
                a.AttributeType,
                a.OrderCodeFormatKey,
                a.DisplayOrder,
                a.HasDependentOptions,
                av.AttributeValueId,
                av.Name AS ValueName,
                av.OrderCodeValue,
                av.DisplayOrdinal
            FROM BaseAttributeValues bav WITH (NOLOCK)
            INNER JOIN AttributeValue av
                ON bav.AttributeValueId = av.AttributeValueId
            INNER JOIN Attribute a
                ON av.AttributeId = a.AttributeId
            WHERE bav.ItemId = ?
              AND av.Status = 1
            ORDER BY a.DisplayOrder, av.DisplayOrdinal
        """
        return self._execute(query, (item_id,), connection=connection)

    @staticmethod
    def effective_ocfs(row: Any) -> str:
        """Apply the legacy Product -> ProductRange OCFS fallback."""
        product = (getattr(row, "ProductOrderCodeFormatString", None) or "").strip()
        if product:
            return product
        return (getattr(row, "RangeOrderCodeFormatString", None) or "").strip()
