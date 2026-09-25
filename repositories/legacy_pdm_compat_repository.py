"""Read-only legacy-PDM compatibility queries.

This module is deliberately isolated from the production reduction engine. It
contains only the PDM reads needed to reconstruct an existing Item and invoke
the legacy ProductSelector filter contract.
"""
from __future__ import annotations

from typing import Any, Sequence

from repositories.pdm_repository import PDMRepository


class LegacyPDMCompatRepository(PDMRepository):
    """Additional read-only queries required for legacy compatibility checks."""

    ITEM_OPTIONS_QUERY = """
        SELECT iov.ItemId, o.OptionId, o.Name AS OptionName,
               o.OrderCodeFormatKey, o.DisplayOrder,
               ov.OptionValueId, ov.Name AS ValueName,
               ov.OrderCodeValue, ov.DisplayOrdinal
        FROM ItemOptionValues iov WITH (NOLOCK)
        INNER JOIN OptionValue ov ON iov.OptionValueId = ov.OptionValueId
        INNER JOIN [Option] o ON ov.OptionId = o.OptionId
        WHERE iov.ItemId = ? AND ov.Status = 1
        ORDER BY o.DisplayOrder, ov.DisplayOrdinal
    """

    PRODUCT_OCFS_QUERY = """
        SELECT TOP 1 p.ProductId, p.Product,
               p.OrderCodeFormatString AS ProductOrderCodeFormatString,
               pr.ProductRangeId, pr.Name AS RangeName,
               pr.OrderCodeFormatString AS RangeOrderCodeFormatString
        FROM Product p WITH (NOLOCK)
        INNER JOIN ProductRange pr ON p.ProductRangeId = pr.ProductRangeId
        WHERE p.ProductId = ?
    """

    #: Mirrors ``ProductSelector.isUSRange`` exactly (``ProductSelector.cs``):
    #: a ProductRange is a US range iff its category's ``USCategory`` flag is 1.
    #: US ranges go to ``USProductsList``, which filters an entirely separate
    #: entity (see :meth:`fetch_legacy_filtered_us_items`).
    RANGE_CATEGORY_QUERY = """
        SELECT pc.USCategory, pc.ProductCategoryId
        FROM ProductCategory pc WITH (NOLOCK)
        INNER JOIN ProductRange pr WITH (NOLOCK) ON pc.ProductCategoryId = pr.ProductCategoryId
        WHERE pr.ProductRangeId = ?
    """

    #: The attribute rows the legacy filter itself sees. ``dbo.ProductsList``
    #: joins ``ProductAttributeValues`` with NO ``AttributeValue.Status``
    #: predicate, so a validation read must not apply one either - dropping a
    #: non-released value would silently weaken the selector and over-match.
    #: (Contrast ``PDMRepository.fetch_products_attributes``, which filters
    #: ``av.Status = 1`` because it feeds the editable snapshot, not the filter.)
    PRODUCT_FILTER_ATTRIBUTES_SQL = (
        "SELECT pav.ProductId, a.AttributeId, av.AttributeValueId, "
        "a.AttributeType, a.OrderCodeFormatKey, av.OrderCodeValue, av.ModelSuffix "
        "FROM ProductAttributeValues pav WITH (NOLOCK) "
        "INNER JOIN AttributeValue av WITH (NOLOCK) "
        "ON pav.AttributeValueId = av.AttributeValueId "
        "INNER JOIN Attribute a WITH (NOLOCK) ON av.AttributeId = a.AttributeId "
    )

    #: Mirrors the eligibility clause inside ``ProductsList``: a Product is
    #: offered by the selector when it is flagged ``NewProduct`` or owns at
    #: least one released (``Status = 1``) Item. Used to establish the COMPLETE
    #: eligible population of a ProductRange so a locally loaded product set can
    #: be REPORTED as complete or partial instead of being assumed complete.
    RANGE_POPULATION_QUERY = """
        SELECT p.ProductId
        FROM Product p WITH (NOLOCK)
        WHERE p.ProductRangeId = ?
          AND (
                p.NewProduct = 1
                OR EXISTS (
                    SELECT 1 FROM Item i WITH (NOLOCK)
                    WHERE i.ProductId = p.ProductId AND i.Status = 1
                )
          )
    """

    #: The same eligibility clause, resolved for every ProductRange a set of
    #: Products belongs to, in one read. Used to answer "is this ProductRange
    #: fully loaded?" before a family is sent to ``ProductsList`` - which always
    #: answers over the COMPLETE range, never over a locally loaded subset.
    RANGE_POPULATION_FOR_PRODUCTS_SQL = (
        "SELECT p.ProductId, p.ProductRangeId, pr.Name AS RangeName, p.Product "
        "FROM Product p WITH (NOLOCK) "
        "INNER JOIN ProductRange pr WITH (NOLOCK) "
        "ON pr.ProductRangeId = p.ProductRangeId "
        "WHERE p.ProductRangeId IN ("
        "    SELECT seed.ProductRangeId FROM Product seed WITH (NOLOCK) "
        "    WHERE seed.ProductId IN ({placeholders})"
        ") AND ("
        "    p.NewProduct = 1"
        "    OR EXISTS ("
        "        SELECT 1 FROM Item i WITH (NOLOCK) "
        "        WHERE i.ProductId = p.ProductId AND i.Status = 1"
        "    )"
        ")"
    )

    def fetch_item_options(self, item_id: Any, connection: Any = None) -> list[Any]:
        return self._execute(self.ITEM_OPTIONS_QUERY, (item_id,), connection=connection)

    def fetch_product_ocfs(self, product_id: Any, connection: Any = None) -> list[Any]:
        return self._execute(self.PRODUCT_OCFS_QUERY, (product_id,), connection=connection)

    def fetch_range_category(self, product_range_id: Any, connection: Any = None) -> list[Any]:
        return self._execute(self.RANGE_CATEGORY_QUERY, (product_range_id,), connection=connection)

    def is_us_range(self, product_range_id: Any, connection: Any = None) -> bool:
        rows = self.fetch_range_category(product_range_id, connection=connection)
        return bool(rows) and int(getattr(rows[0], "USCategory", 0) or 0) == 1

    def range_scope(
        self, product_range_id: Any, connection: Any = None
    ) -> tuple[Any, bool]:
        """``(ProductCategoryId, is_us_range)`` for one range, in one read.

        ``ProductCategoryId`` is what ``USProductsList`` is keyed by, so it is
        needed to describe (or perform) the US path accurately.
        """
        rows = self.fetch_range_category(product_range_id, connection=connection)
        if not rows:
            return None, False
        row = rows[0]
        return (
            getattr(row, "ProductCategoryId", None),
            int(getattr(row, "USCategory", 0) or 0) == 1,
        )

    def fetch_products_filter_attributes(
        self, product_ids: Sequence[Any], connection: Any = None
    ) -> list[Any]:
        """ProductAttributeValues as the legacy filter sees them (no Status
        filter), with the columns every legacy functional test needs."""
        ids = [pid for pid in product_ids if pid is not None]
        rows: list[Any] = []
        for chunk in self._chunked(ids, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = self.PRODUCT_FILTER_ATTRIBUTES_SQL + f"WHERE pav.ProductId IN ({ph})"
            rows.extend(self._execute(query, tuple(chunk), connection=connection))
        return rows

    def fetch_range_product_ids(
        self, product_range_id: Any, connection: Any = None
    ) -> list[Any]:
        """The complete legacy-eligible ProductId population of one range."""
        return self._execute(
            self.RANGE_POPULATION_QUERY, (product_range_id,), connection=connection
        )

    def fetch_range_population_for_products(
        self, product_ids: Sequence[Any], connection: Any = None
    ) -> list[Any]:
        """The COMPLETE legacy-eligible population of every ProductRange the
        given Products belong to.

        Rows carry ``ProductId``, ``ProductRangeId``, ``RangeName`` and the
        product code ``Product``. The eligibility clause is the one inside
        ``ProductsList`` itself, so the result is exactly the population that
        procedure would consider - the population a candidate family has to
        cover before an exact comparison against it can mean anything, and the
        population a candidate strategy may draw members from.
        """
        ids = [pid for pid in product_ids if pid is not None]
        rows: list[Any] = []
        seen: set = set()
        for chunk in self._chunked(ids, self._IN_CHUNK):
            query = self.RANGE_POPULATION_FOR_PRODUCTS_SQL.format(
                placeholders=self._placeholders(len(chunk))
            )
            for row in self._execute(query, tuple(chunk), connection=connection):
                key = str(getattr(row, "ProductId", ""))
                if key not in seen:
                    seen.add(key)
                    rows.append(row)
        return rows

    #: ``HandbookProducts`` is the pricebook definition the Handbook Designer
    #: writes (``docs/Legacy_PDM_Business_Logic/23_Generation.md``). It is the
    #: one place legacy PDM records "these Products are published together",
    #: and ``ProductListEntry`` is the base article its maintainers wrote for
    #: that group, masked with ``_`` where the members differ.
    #:
    #: It is CURATED, not derived: see ``docs/pdm-family-boundary.md`` 1.3 for
    #: the measured inconsistency (581 distinct masks inside one range, ~47%
    #: product coverage, mask/prefix agreement 72.2%). It is therefore only ever
    #: a source of candidate groupings to be PROVEN against ``ProductsList`` -
    #: never an authority on its own.
    HANDBOOK_GROUPS_SQL = (
        "SELECT hp.HandbookId, hp.ProductGroupId, hp.GroupName, "
        "hp.ProductListEntry, hp.ProductId, p.ProductRangeId "
        "FROM HandbookProducts hp WITH (NOLOCK) "
        "INNER JOIN Product p WITH (NOLOCK) ON p.ProductId = hp.ProductId "
        "WHERE hp.ProductId IN ({placeholders})"
    )

    def fetch_handbook_groups(
        self, product_ids: Sequence[Any], connection: Any = None
    ) -> list[Any]:
        """The handbook group rows covering the given Products.

        One row per (Handbook, ProductGroup, Product). Products with no
        handbook row simply do not appear - roughly half of active Products,
        which is why anything built on this has to be a fallback rather than
        the primary rule.
        """
        ids = [pid for pid in product_ids if pid is not None]
        rows: list[Any] = []
        for chunk in self._chunked(ids, self._IN_CHUNK):
            query = self.HANDBOOK_GROUPS_SQL.format(
                placeholders=self._placeholders(len(chunk))
            )
            rows.extend(self._execute(query, tuple(chunk), connection=connection))
        return rows

    def fetch_products_range_info(
        self, product_ids: Sequence[Any], connection: Any = None
    ) -> list[Any]:
        """Bulk ProductId -> ProductRangeId/Product/Status/NewProduct."""
        ids = [pid for pid in product_ids if pid is not None]
        rows: list[Any] = []
        for chunk in self._chunked(ids, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = (
                "SELECT p.ProductId, p.Product, p.ProductRangeId, p.Status, p.NewProduct "
                "FROM Product p WITH (NOLOCK) "
                f"WHERE p.ProductId IN ({ph})"
            )
            rows.extend(self._execute(query, tuple(chunk), connection=connection))
        return rows

    def fetch_items_for_products(self, product_ids: Sequence[Any], connection: Any = None) -> list[Any]:
        ids = [pid for pid in product_ids if pid is not None]
        rows: list[Any] = []
        for chunk in self._chunked(ids, self._IN_CHUNK):
            ph = self._placeholders(len(chunk))
            query = (
                "SELECT i.ProductId, i.ItemId, i.Item, i.Status, i.IsSuperItem "
                "FROM Item i WITH (NOLOCK) "
                f"WHERE i.ProductId IN ({ph}) ORDER BY i.ProductId, i.Item"
            )
            rows.extend(self._execute(query, tuple(chunk), connection=connection))
        return rows

    def fetch_product_attribute_values_full(self, product_id: Any, connection: Any = None) -> list[Any]:
        query = """
            SELECT pav.ProductId, a.AttributeId, a.Name AS AttributeName,
                   a.AttributeType, a.OrderCodeFormatKey, a.DisplayOrder,
                   a.HasDependentOptions, av.AttributeValueId, av.Name AS ValueName,
                   av.OrderCodeValue, av.DisplayOrdinal
            FROM ProductAttributeValues pav WITH (NOLOCK)
            INNER JOIN AttributeValue av ON pav.AttributeValueId = av.AttributeValueId
            INNER JOIN Attribute a ON av.AttributeId = a.AttributeId
            WHERE pav.ProductId = ? AND av.Status = 1
            ORDER BY a.DisplayOrder, av.DisplayOrdinal
        """
        return self._execute(query, (product_id,), connection=connection)

    def fetch_item_attribute_values_full(self, item_id: Any, connection: Any = None) -> list[Any]:
        query = """
            SELECT bav.ItemId, a.AttributeId, a.Name AS AttributeName,
                   a.AttributeType, a.OrderCodeFormatKey, a.DisplayOrder,
                   a.HasDependentOptions, av.AttributeValueId, av.Name AS ValueName,
                   av.OrderCodeValue, av.DisplayOrdinal
            FROM BaseAttributeValues bav WITH (NOLOCK)
            INNER JOIN AttributeValue av ON bav.AttributeValueId = av.AttributeValueId
            INNER JOIN Attribute a ON av.AttributeId = a.AttributeId
            WHERE bav.ItemId = ? AND av.Status = 1
            ORDER BY a.DisplayOrder, av.DisplayOrdinal
        """
        return self._execute(query, (item_id,), connection=connection)

    def fetch_legacy_filtered_products(
        self, product_range_id: Any, language_id: Any, attribute_xml: str,
        connection: Any = None,
    ) -> list[Any]:
        """Invoke the real ``dbo.ProductsList(@ProductRangeId, @LanguageId,
        @SelAttribValuesXml)`` - the non-US selector path.

        The stored procedure remains the authority for filter equivalence; this
        method deliberately does not reproduce its WHERE/JOIN logic. It is NOT
        valid for a US range: ``ProductSelector.LoadProducts`` routes those to
        :meth:`fetch_legacy_filtered_us_items`, which takes a different key and
        queries a different entity. The two are kept as separate methods so a
        US range can never be filtered through the non-US procedure by
        accident.

        Returns rows with ``ProductId`` (a real ``Product.ProductId``).
        """
        return self._execute(
            "EXEC ProductsList ?, ?, ?",
            (product_range_id, language_id, attribute_xml),
            connection=connection,
        )

    def fetch_legacy_filtered_us_items(
        self, product_category_id: Any, language_id: Any, attribute_xml: str,
        connection: Any = None,
    ) -> list[Any]:
        """Invoke the real ``dbo.USProductsList(@productCategoryId,
        @LanguageId, @selAttribValuesXml)``.

        **This does not return Products.** The procedure selects from
        ``USItem`` joined to ``USItemAttributeValues``, scoped by
        ``USItem.ProductCategoryId``, and aliases ``USItem.USItemId`` as
        ``ProductId`` (with ``ProductRangeId`` hardcoded to ``-1``). Its
        ``attributevalueid`` inputs are matched against
        ``USItemAttributeValues.USAttributeValueId`` - the ``USAttributeValue``
        vocabulary, not ``AttributeValue``. It applies no Item/NewProduct
        eligibility clause (that predicate is commented out in the procedure).

        Provided for completeness and for US-native callers. A Product-based
        reduction candidate cannot be compared against its result, because
        ``USItemId`` and ``Product.ProductId`` are disjoint key spaces - see
        ``PDMFamilyReductionService.validate_family``.
        """
        return self._execute(
            "EXEC USProductsList ?, ?, ?",
            (product_category_id, language_id, attribute_xml),
            connection=connection,
        )

    @staticmethod
    def effective_ocfs(row: Any) -> str:
        """Apply the legacy Product -> ProductRange OCFS fallback."""
        product = (getattr(row, "ProductOrderCodeFormatString", None) or "").strip()
        return product or (getattr(row, "RangeOrderCodeFormatString", None) or "").strip()
