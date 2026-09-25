"""Generic legacy-PDM reduction compatibility engine.

This service is intentionally isolated from EngineeringReductionService. It
uses PDM IDs and the legacy ProductsList/USProductsList filter boundary rather
than article-character positions. It is read-only and is suitable for proving
the reduction model before wiring it into production reduction.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
from xml.sax.saxutils import quoteattr

from repositories.legacy_pdm_compat_repository import LegacyPDMCompatRepository
from services.base_service import BaseService


@dataclass(frozen=True)
class PDMSelection:
    attribute_id: str
    attribute_value_id: str
    attribute_name: str = ""
    value_name: str = ""
    order_code_value: str = ""
    order_code_format_key: str = ""


@dataclass(frozen=True)
class PDMOptionSelection:
    option_id: str
    option_value_id: str
    option_name: str = ""
    value_name: str = ""
    order_code_value: str = ""
    order_code_format_key: str = ""


@dataclass(frozen=True)
class PDMArticleConfiguration:
    item_id: Any
    product_id: Any
    item: str
    product: str
    product_range_id: Any
    range_name: str
    ocfs: str
    attributes: tuple[PDMSelection, ...] = ()
    options: tuple[PDMOptionSelection, ...] = ()
    reconstructed_item: str = ""
    reconstruction_ok: bool = False
    unresolved_tokens: tuple[str, ...] = ()
    duplicate_tokens: tuple[str, ...] = ()


@dataclass(frozen=True)
class LegacyFilterResult:
    product_ids: tuple[str, ...] = ()
    products: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReductionCandidate:
    """A PDM identity plus the attribute selections that distinguish it."""

    product_id: str
    product: str
    product_range_id: Any
    item_ids: tuple[str, ...] = ()
    item_codes: tuple[str, ...] = ()
    configurable_attribute_ids: tuple[str, ...] = ()
    configurable_attribute_value_ids: tuple[str, ...] = ()
    filter_product_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ReductionReport:
    configurations: tuple[PDMArticleConfiguration, ...] = ()
    candidates: tuple[ReductionCandidate, ...] = ()
    reconstruction_failures: tuple[str, ...] = ()


class LegacyPDMReductionService(BaseService):
    """Read-only PDM truth/reconstruction and legacy-filter verification."""

    def __init__(self, context) -> None:
        super().__init__(context)
        self.repository = LegacyPDMCompatRepository(context)

    @staticmethod
    def _row_value(row: Any, name: str, default: Any = None) -> Any:
        return getattr(row, name, default)

    @staticmethod
    def build_attribute_xml(selections: Iterable[PDMSelection]) -> str:
        """Build the selector XML in the shape ``TemplateContainer.AttributeXml``
        emits and ``ProductsList`` parses.

        ``AttributeXml`` additionally separates elements with CR/LF and
        emits ``<DISABLED_attribute .../>`` placeholders for unselected
        selectors; both are invisible to the procedure, which reads the
        document through ``OPENXML(@hDoc, '/attributes/attribute', 1)``. It
        also returns ``string.Empty`` when nothing is selected - callers must
        reproduce that by sending no XML at all, never an empty
        ``<attributes></attributes>`` document (see
        ``PDMFamilyReductionService``).
        """
        parts = ["<attributes>"]
        for selection in selections:
            parts.append(
                "<attribute attributeid="
                + quoteattr(str(selection.attribute_id))
                + " attributevalueid="
                + quoteattr(str(selection.attribute_value_id))
                + "/>"
            )
        parts.append("</attributes>")
        return "".join(parts)

    @staticmethod
    def _index_rows(rows: Iterable[Any], key_name: str) -> dict[str, list[Any]]:
        result: dict[str, list[Any]] = {}
        for row in rows:
            key = str(getattr(row, key_name))
            result.setdefault(key, []).append(row)
        return result

    @staticmethod
    def _selected_attributes(product_rows: list[Any], item_rows: list[Any]) -> tuple[PDMSelection, ...]:
        """Use item BaseAttributeValues as the authoritative selected state.

        ProductAttributeValues is the fallback for attributes not materialised on
        an Item. Multiple values for one AttributeId are preserved rather than
        guessed away; the legacy filter can then be compared with the exact IDs.
        """
        chosen: dict[str, list[Any]] = {}
        for row in product_rows:
            chosen.setdefault(str(row.AttributeId), []).append(row)
        for row in item_rows:
            chosen.setdefault(str(row.AttributeId), []).append(row)
            # An Item value is the concrete value for that attribute.
            chosen[str(row.AttributeId)] = [row]

        selections: list[PDMSelection] = []
        for rows in chosen.values():
            for row in rows:
                selections.append(
                    PDMSelection(
                        attribute_id=str(row.AttributeId),
                        attribute_value_id=str(row.AttributeValueId),
                        attribute_name=str(getattr(row, "AttributeName", "") or ""),
                        value_name=str(getattr(row, "ValueName", "") or ""),
                        order_code_value=str(getattr(row, "OrderCodeValue", "") or ""),
                        order_code_format_key=str(getattr(row, "OrderCodeFormatKey", "") or ""),
                    )
                )
        return tuple(selections)

    @staticmethod
    def _selected_options(rows: list[Any]) -> tuple[PDMOptionSelection, ...]:
        return tuple(
            PDMOptionSelection(
                option_id=str(row.OptionId),
                option_value_id=str(row.OptionValueId),
                option_name=str(getattr(row, "OptionName", "") or ""),
                value_name=str(getattr(row, "ValueName", "") or ""),
                order_code_value=str(getattr(row, "OrderCodeValue", "") or ""),
                order_code_format_key=str(getattr(row, "OrderCodeFormatKey", "") or ""),
            )
            for row in rows
        )

    @staticmethod
    def _expand_ocfs(product: str, ocfs: str, attributes: tuple[PDMSelection, ...], options: tuple[PDMOptionSelection, ...]) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
        """Replace OCFS tokens with PDM OrderCodeValue values.

        Replacement follows the token sequence already stored in OCFS. It does
        not use Attribute.DisplayOrder, fixed widths, or article positions.
        """
        attr_by_key: dict[str, list[str]] = {}
        for value in attributes:
            key = value.order_code_format_key.strip()
            code = value.order_code_value.strip()
            if key and code:
                attr_by_key.setdefault(key, []).append(code)

        opt_by_key: dict[str, list[str]] = {}
        for value in options:
            key = value.order_code_format_key.strip()
            code = value.order_code_value.strip()
            if key and code:
                opt_by_key.setdefault(key, []).append(code)

        import re
        token_pattern = re.compile(r"\{([^{}]+)\}")
        unresolved: list[str] = []
        duplicates: list[str] = []

        def replace(match):
            token = match.group(1).strip()
            values = attr_by_key.get(token) or opt_by_key.get(token) or []
            if not values:
                unresolved.append(token)
                return match.group(0)
            if len(values) > 1:
                duplicates.append(token)
            return values[0]

        return product + token_pattern.sub(replace, ocfs), tuple(unresolved), tuple(duplicates)

    def reconstruct_item(self, item_id: Any, product_id: Any) -> PDMArticleConfiguration:
        """Reconstruct one existing Item from PDM configuration and OCFS."""
        items = self.repository.fetch_items_for_products([product_id])
        item = next((r for r in items if str(r.ItemId) == str(item_id)), None)
        if item is None:
            raise ValueError(f"PDM ItemId {item_id} was not found for ProductId {product_id}.")

        header_rows = self.repository.fetch_product_ocfs(product_id)
        if not header_rows:
            raise ValueError(f"PDM ProductId {product_id} has no Product/ProductRange OCFS metadata.")
        header = header_rows[0]
        ocfs = self.repository.effective_ocfs(header)
        product_rows = self.repository.fetch_product_attribute_values_full(product_id)
        item_rows = self.repository.fetch_item_attribute_values_full(item_id)
        option_rows = self.repository.fetch_item_options(item_id)
        attributes = self._selected_attributes(product_rows, item_rows)
        options = self._selected_options(option_rows)
        reconstructed, unresolved, duplicates = self._expand_ocfs(
            str(header.Product or ""), ocfs, attributes, options
        )
        actual = str(item.Item or "")
        return PDMArticleConfiguration(
            item_id=item_id,
            product_id=product_id,
            item=actual,
            product=str(header.Product or ""),
            product_range_id=header.ProductRangeId,
            range_name=str(header.RangeName or ""),
            ocfs=ocfs,
            attributes=attributes,
            options=options,
            reconstructed_item=reconstructed,
            reconstruction_ok=(reconstructed == actual and not unresolved and not duplicates),
            unresolved_tokens=unresolved,
            duplicate_tokens=duplicates,
        )

    def verify_legacy_filter(
        self, configuration: PDMArticleConfiguration, language_id: Any = 1
    ) -> LegacyFilterResult:
        """Send the selected AttributeId/AttributeValueId XML to PDM's actual
        legacy ``ProductsList`` procedure and return its ProductId set.

        Non-US ranges only. ``USProductsList`` takes a ProductCategoryId and
        returns USItemIds from a separate entity, so a Product-keyed
        configuration cannot be verified through it - see
        :meth:`LegacyPDMCompatRepository.fetch_legacy_filtered_us_items`.
        """
        xml = self.build_attribute_xml(configuration.attributes)
        rows = self.repository.fetch_legacy_filtered_products(
            configuration.product_range_id, language_id, xml
        )
        ids = tuple(sorted({str(getattr(r, "ProductId")) for r in rows if getattr(r, "ProductId", None) is not None}))
        products = tuple(sorted({str(getattr(r, "Product", getattr(r, "OrderCode", ""))) for r in rows}))
        return LegacyFilterResult(product_ids=ids, products=products)

    def analyze_items(self, product_ids: Iterable[Any], language_id: Any = 1) -> ReductionReport:
        """Analyze a product set in one pass and report reconstruction/filter data.

        This method deliberately does not alter Snapshot or Engineering data.
        It is the acceptance-test engine used before replacing the existing
        prefix/length reducer.
        """
        configurations: list[PDMArticleConfiguration] = []
        failures: list[str] = []
        candidates: list[ReductionCandidate] = []

        for product_id in product_ids:
            items = self.repository.fetch_items_for_products([product_id])
            for item in items:
                try:
                    configuration = self.reconstruct_item(item.ItemId, product_id)
                except Exception as exc:
                    failures.append(f"{item.ItemId}: {exc}")
                    continue
                configurations.append(configuration)
                if not configuration.reconstruction_ok:
                    failures.append(
                        f"{item.ItemId}: expected {configuration.item!r}, "
                        f"reconstructed {configuration.reconstructed_item!r}; "
                        f"unresolved={configuration.unresolved_tokens}; "
                        f"duplicates={configuration.duplicate_tokens}"
                    )
                    continue
                try:
                    filtered = self.verify_legacy_filter(configuration, language_id)
                except Exception as exc:
                    failures.append(f"{item.ItemId}: legacy filter failed: {exc}")
                    continue
                candidates.append(
                    ReductionCandidate(
                        product_id=str(configuration.product_id),
                        product=configuration.product,
                        product_range_id=configuration.product_range_id,
                        item_ids=(str(configuration.item_id),),
                        item_codes=(configuration.item,),
                        configurable_attribute_ids=tuple(sorted({a.attribute_id for a in configuration.attributes if a.order_code_format_key})),
                        configurable_attribute_value_ids=tuple(sorted({a.attribute_value_id for a in configuration.attributes if a.order_code_format_key})),
                        filter_product_ids=filtered.product_ids,
                    )
                )

        return ReductionReport(
            configurations=tuple(configurations),
            candidates=tuple(candidates),
            reconstruction_failures=tuple(failures),
        )
