"""Read-only adapters for legacy SyteLine item and option selection."""
from __future__ import annotations

from typing import Any, Callable

from repositories.pdm_repository import PDMRepository
from services.syteline_export.item_selection_query import (
    ItemSelection,
    ItemSelectionQuery,
    build_item_selection_query,
)
from services.syteline_export.material_conversion import (
    assign_legacy_feature_positions,
    normalize_legacy_option_report_rows,
    order_legacy_option_report_rows,
    reconcile_legacy_option_child_ids,
)


class SyteLineItemSourceService:
    """Execute source-mapped legacy queries and return rows by column name."""

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
        """Run the item-selection query. Downstream legacy transformations are separate."""
        query = build_item_selection_query(selection)
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.timeout = 600
            cursor.execute(query.sql, *query.parameters)
            if cursor.description is None:
                raise RuntimeError(
                    "The item-selection query returned no result set; an empty "
                    "selection is a result set with zero rows, so this is a driver "
                    "or database error."
                )
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            connection.close()

    def fetch_prepared_option_report(
        self,
        long_item: str,
        *,
        flatten_fabrics: bool = False,
    ) -> list[dict[str, Any]]:
        """Fetch and apply source-backed option normalization, ordering and child reconciliation.

        This is a preparation layer for downstream feature/material assembly;
        it does not claim to reproduce the full legacy traversal.
        """
        item = str(long_item).strip()
        rows = self.fetch_option_report(item)
        normalized = normalize_legacy_option_report_rows(
            rows, flatten_fabrics=flatten_fabrics
        )
        ordered = order_legacy_option_report_rows(normalized, item_code=item)
        return reconcile_legacy_option_child_ids(ordered)

    def fetch_staged_option_features(
        self,
        long_item: str,
        *,
        allowed_option_ids: set[int] | list[int] | tuple[int, ...],
        flatten_fabrics: bool = False,
    ) -> list[dict[str, Any]]:
        """Prepare option rows and assign feature positions after an explicit allowlist.

        The legacy exporter applies catalogue/item-specific allowlists before
        assigning feature positions. Requiring the caller to supply the allowed
        option IDs prevents this service from silently treating every procedure
        row as exportable feature data.
        """
        item = str(long_item).strip()
        if not item:
            raise ValueError("A non-empty long item code is required.")
        try:
            allowed = {int(option_id) for option_id in allowed_option_ids}
        except (TypeError, ValueError) as exc:
            raise ValueError("Allowed option IDs must all be integers.") from exc
        if not allowed or any(option_id <= 0 for option_id in allowed):
            raise ValueError("At least one positive allowed option ID is required.")

        rows = self.fetch_prepared_option_report(item, flatten_fabrics=flatten_fabrics)
        eligible = []
        for row in rows:
            try:
                option_id = int(row.get("OptionId"))
            except (TypeError, ValueError):
                continue
            if option_id in allowed:
                eligible.append(row)
        return assign_legacy_feature_positions(eligible)

    def fetch_option_report(self, long_item: str) -> list[dict[str, Any]]:
        """Read the option rows produced by the legacy PDMOptionDataReport procedure.

        ExportThread creates a temporary table by executing this procedure and
        then applies substantial ordering, dependency, fabric and feature
        transformations. This method deliberately returns the raw procedure
        result and does not claim to reproduce those downstream transformations.
        """
        item = str(long_item).strip()
        if not item:
            raise ValueError("A non-empty long item code is required.")
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.timeout = 900
            cursor.execute("EXEC PDMOptionDataReport ?", item)
            if cursor.description is None:
                raise RuntimeError(
                    "PDMOptionDataReport returned no result set; the configured PDM "
                    "database may not expose the legacy procedure as expected."
                )
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            connection.close()


    def fetch_legacy_option_feature_length_rows(
        self,
        option_id: int,
        catalogue_id: int,
    ) -> list[dict[str, Any]]:
        """Read catalogue-scoped feature-length candidates used by legacy stage 20.

        The legacy query prefers a dependent fabric option's SLFeatureLength,
        maximum order-code length and IsFabric flag when that dependent option
        is a fabric option. Selection among candidate rows remains the caller's
        responsibility; this method returns the database's grouped candidates.
        """
        try:
            selected_option_id = int(option_id)
            selected_catalogue_id = int(catalogue_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("Option and catalogue IDs must be integers.") from exc
        if selected_option_id <= 0 or selected_catalogue_id <= 0:
            raise ValueError("Option and catalogue IDs must be positive.")

        sql = """
            SELECT
                CASE WHEN fabric_opt.OptionId IS NULL
                     THEN opt.SLFeatureLength ELSE fabric_opt.SLFeatureLength END
                    AS SLFeatureLength,
                CASE WHEN fabric_opt.OptionId IS NULL
                     THEN MAX(LEN(REPLACE(optval.OrderCodeValue, '#', '')))
                     ELSE MAX(LEN(REPLACE(fabric_optval.OrderCodeValue, '#', ''))) END
                    AS max_length,
                CASE WHEN fabric_opt.OptionId IS NULL
                     THEN opt.IsFabric ELSE fabric_opt.IsFabric END AS IsFabric
            FROM [Option] opt WITH (NOLOCK)
            INNER JOIN OptionValue optval
                ON opt.OptionId = optval.OptionId
            INNER JOIN CatalogueOptionValues cov
                ON optval.OptionValueId = cov.OptionValueId
               AND cov.CatalogueId = ?
            LEFT OUTER JOIN DependentOptionValues dov
                ON optval.OptionValueId = dov.AdditionalOptionValueId
            LEFT OUTER JOIN OptionValue fabric_optval
                ON dov.OptionValueId = fabric_optval.OptionValueId
            LEFT OUTER JOIN [Option] fabric_opt
                ON fabric_optval.OptionId = fabric_opt.OptionId
               AND fabric_opt.IsFabric = 1
            GROUP BY opt.OptionId, opt.SLFeatureLength, opt.IsFabric,
                     fabric_opt.OptionId, fabric_opt.SLFeatureLength,
                     fabric_opt.IsFabric
            HAVING opt.OptionId = ?
        """
        connection = self._connect()
        try:
            cursor = connection.cursor()
            cursor.timeout = 600
            cursor.execute(sql, selected_catalogue_id, selected_option_id)
            if cursor.description is None:
                raise RuntimeError("The feature-length query returned no result set.")
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        finally:
            connection.close()
