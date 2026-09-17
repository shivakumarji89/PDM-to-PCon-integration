"""Read-only PDM article reduction based on legacy ProductsList membership."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from repositories.legacy_pdm_compat_repository import LegacyPDMCompatRepository
from services.base_service import BaseService
from services.engineering.legacy_pdm_reduction_service import (
    LegacyPDMReductionService,
    PDMSelection,
)


@dataclass(frozen=True)
class PDMAttributeValue:
    """One ProductAttributeValues row with enough metadata to classify it."""

    attribute_value_id: str
    attribute_id: str = ""
    attribute_name: str = ""
    value_name: str = ""
    order_code_value: str = ""


@dataclass(frozen=True)
class PDMProductRecord:
    """Minimal Product record consumed by the reduction algorithm."""

    product_id: str
    product: str
    product_range_id: Any
    eligible: bool = True
    attribute_values: tuple[PDMAttributeValue, ...] = ()


@dataclass(frozen=True)
class PDMFilterValidation:
    valid: bool
    returned_product_ids: tuple[str, ...] = ()
    reason: str = ""


@dataclass(frozen=True)
class PDMEquivalentFilter:
    prefix: str
    attribute_value_ids: tuple[str, ...]


@dataclass(frozen=True)
class PDMArticleReductionCandidate:
    product_range_id: Any
    base: str
    product_ids: tuple[str, ...]
    filter_attribute_value_ids: tuple[str, ...]
    filter_attributes: tuple[PDMSelection, ...]
    validation: PDMFilterValidation
    ambiguous_equivalent_filters: tuple[PDMEquivalentFilter, ...] = ()


class PDMArticleReductionService(BaseService):
    """Discover validated pre-dot article groups without mutating engineering data."""

    def __init__(
        self,
        context: Any = None,
        repository: LegacyPDMCompatRepository | None = None,
    ) -> None:
        if context is not None:
            super().__init__(context)
        else:
            self.context = None
        self.repository = repository

    @staticmethod
    def _value(record: Any, name: str, default: Any = None) -> Any:
        if isinstance(record, Mapping):
            return record.get(name, default)
        return getattr(record, name, default)

    @classmethod
    def _attribute_values(cls, record: Any) -> tuple[PDMAttributeValue, ...]:
        rows = cls._value(record, "attribute_values", None)
        if rows is None:
            rows = cls._value(record, "functional_attributes", None)
        if rows is None:
            rows = cls._value(record, "product_attribute_values", None)
        if rows is None:
            rows = cls._value(record, "ProductAttributeValues", None)
        if rows is None:
            ids = cls._value(record, "product_attribute_value_ids", None)
            if ids is None:
                ids = cls._value(record, "ProductAttributeValueIds", ())
            rows = (PDMAttributeValue(str(value)) for value in (ids or ()))
        result: list[PDMAttributeValue] = []
        for row in rows:
            if isinstance(row, PDMAttributeValue):
                result.append(row)
                continue
            value_id = cls._value(row, "attribute_value_id", None)
            if value_id is None:
                value_id = cls._value(row, "AttributeValueId", None)
            if value_id is None:
                value_id = cls._value(row, "id", None)
            if value_id is None:
                continue
            result.append(
                PDMAttributeValue(
                    attribute_value_id=str(value_id),
                    attribute_id=str(cls._value(row, "attribute_id", cls._value(row, "AttributeId", "")) or ""),
                    attribute_name=str(cls._value(row, "attribute_name", cls._value(row, "AttributeName", "")) or ""),
                    value_name=str(cls._value(row, "value_name", cls._value(row, "ValueName", "")) or ""),
                    order_code_value=str(cls._value(row, "order_code_value", cls._value(row, "OrderCodeValue", "")) or ""),
                )
            )
        return tuple(result)

    @classmethod
    def _normalise_product(cls, record: Any) -> PDMProductRecord:
        product_id = cls._value(record, "product_id", cls._value(record, "ProductId"))
        product = cls._value(record, "product", cls._value(record, "Product", ""))
        range_id = cls._value(record, "product_range_id", cls._value(record, "ProductRangeId"))
        eligible = cls._value(record, "eligible", cls._value(record, "Eligibility", True))
        if isinstance(eligible, str):
            eligible = eligible.strip().lower() not in {"", "0", "false", "no", "n"}
        return PDMProductRecord(
            product_id=str(product_id),
            product=str(product or ""),
            product_range_id=range_id,
            eligible=bool(eligible),
            attribute_values=cls._attribute_values(record),
        )

    @staticmethod
    def _prefixes(products: Iterable[PDMProductRecord]) -> dict[str, tuple[PDMProductRecord, ...]]:
        grouped: dict[str, list[PDMProductRecord]] = {}
        for product in products:
            code = product.product.split(".", 1)[0]
            for length in range(1, len(code)):
                grouped.setdefault(code[:length], []).append(product)
        return {prefix: tuple(rows) for prefix, rows in grouped.items()}

    @classmethod
    def _meaningful_prefixes(
        cls, products: Iterable[PDMProductRecord]
    ) -> tuple[tuple[str, tuple[PDMProductRecord, ...]], ...]:
        """Keep the longest strict prefix for each multi-product ID set."""
        by_ids: dict[frozenset[str], tuple[str, tuple[PDMProductRecord, ...]]] = {}
        for prefix, prefix_products in cls._prefixes(products).items():
            product_ids = frozenset(product.product_id for product in prefix_products)
            if len(product_ids) < 2:
                continue
            current = by_ids.get(product_ids)
            if current is None or len(prefix) > len(current[0]):
                by_ids[product_ids] = (prefix, prefix_products)
        return tuple(sorted(by_ids.values(), key=lambda item: item[0]))

    @staticmethod
    def _functional_values(
        products: tuple[PDMProductRecord, ...],
    ) -> tuple[PDMAttributeValue, ...]:
        if not products:
            return ()
        common = {
            value.attribute_value_id
            for value in products[0].attribute_values
            if not value.order_code_value.strip()
        }
        by_id = {value.attribute_value_id: value for value in products[0].attribute_values}
        for product in products[1:]:
            common &= {
                value.attribute_value_id
                for value in product.attribute_values
                if not value.order_code_value.strip()
            }
            for value in product.attribute_values:
                by_id.setdefault(value.attribute_value_id, value)
        return tuple(by_id[value_id] for value_id in sorted(common))

    @staticmethod
    def _selection(value: PDMAttributeValue) -> PDMSelection:
        return PDMSelection(
            attribute_id=value.attribute_id,
            attribute_value_id=value.attribute_value_id,
            attribute_name=value.attribute_name,
            value_name=value.value_name,
            order_code_value=value.order_code_value,
        )

    def _validate(
        self,
        range_id: Any,
        selections: tuple[PDMSelection, ...],
        expected_ids: frozenset[str],
        *,
        language_id: Any,
        us_data: bool,
        product_category_id: Any,
    ) -> PDMFilterValidation:
        if self.repository is None:
            return PDMFilterValidation(False, reason="A legacy repository is required.")
        scope = product_category_id if us_data else range_id
        if us_data and product_category_id is None:
            return PDMFilterValidation(False, reason="USProductsList requires ProductCategoryId.")
        rows = self.repository.fetch_legacy_filtered_products(
            scope,
            language_id,
            LegacyPDMReductionService.build_attribute_xml(selections),
            us_data=us_data,
        )
        returned = tuple(sorted({str(self._value(row, "ProductId")) for row in rows if self._value(row, "ProductId") is not None}))
        valid = frozenset(returned) == expected_ids
        return PDMFilterValidation(
            valid,
            returned,
            "" if valid else "ProductsList ProductId set differs from the prefix set.",
        )

    def _equivalent_single_value_filters(
        self,
        range_id: Any,
        values: tuple[PDMAttributeValue, ...],
        expected_ids: frozenset[str],
        *,
        language_id: Any,
        us_data: bool,
        product_category_id: Any,
    ) -> tuple[PDMEquivalentFilter, ...]:
        """Check only singleton subsets to expose cheap filter ambiguity."""
        if len(values) < 2:
            return ()
        equivalent: list[PDMEquivalentFilter] = []
        for value in values:
            selection = self._selection(value)
            validation = self._validate(
                range_id,
                (selection,),
                expected_ids,
                language_id=language_id,
                us_data=us_data,
                product_category_id=product_category_id,
            )
            if validation.valid:
                equivalent.append(
                    PDMEquivalentFilter(
                        prefix="",
                        attribute_value_ids=(value.attribute_value_id,),
                    )
                )
        return tuple(equivalent)

    def discover(
        self,
        products: Iterable[Any],
        *,
        language_id: Any = 1,
        us_data: bool = False,
        product_category_id: Any = None,
    ) -> tuple[PDMArticleReductionCandidate, ...]:
        """Return only prefixes whose common functional filter exactly validates."""
        records = [self._normalise_product(product) for product in products]
        by_range: dict[Any, list[PDMProductRecord]] = {}
        for product in records:
            if product.product_range_id is not None:
                by_range.setdefault(product.product_range_id, []).append(product)

        candidates: list[PDMArticleReductionCandidate] = []
        for range_id, range_products in by_range.items():
            for prefix, prefix_products in self._meaningful_prefixes(
                product for product in range_products if product.eligible
            ):
                product_ids = frozenset(product.product_id for product in prefix_products)
                values = self._functional_values(prefix_products)
                selections = tuple(self._selection(value) for value in values)
                validation = self._validate(
                    range_id,
                    selections,
                    product_ids,
                    language_id=language_id,
                    us_data=us_data,
                    product_category_id=product_category_id,
                )
                if validation.valid:
                    singleton_equivalents = self._equivalent_single_value_filters(
                        range_id,
                        values,
                        product_ids,
                        language_id=language_id,
                        us_data=us_data,
                        product_category_id=product_category_id,
                    )
                    candidates.append(
                        PDMArticleReductionCandidate(
                            product_range_id=range_id,
                            base=prefix,
                            product_ids=tuple(sorted(product_ids)),
                            filter_attribute_value_ids=tuple(value.attribute_value_id for value in values),
                            filter_attributes=selections,
                            validation=validation,
                            ambiguous_equivalent_filters=singleton_equivalents,
                        )
                    )

        by_ids: dict[tuple[Any, tuple[str, ...]], list[PDMArticleReductionCandidate]] = {}
        for candidate in candidates:
            key = (candidate.product_range_id, candidate.product_ids)
            by_ids.setdefault(key, []).append(candidate)
        enriched: list[PDMArticleReductionCandidate] = []
        for candidate in candidates:
            equivalent = tuple(
                PDMEquivalentFilter(other.base, other.filter_attribute_value_ids)
                for other in by_ids[(candidate.product_range_id, candidate.product_ids)]
                if other.base != candidate.base
                or other.filter_attribute_value_ids != candidate.filter_attribute_value_ids
            )
            enriched.append(
                PDMArticleReductionCandidate(
                    product_range_id=candidate.product_range_id,
                    base=candidate.base,
                    product_ids=candidate.product_ids,
                    filter_attribute_value_ids=candidate.filter_attribute_value_ids,
                    filter_attributes=candidate.filter_attributes,
                    validation=candidate.validation,
                        ambiguous_equivalent_filters=equivalent + candidate.ambiguous_equivalent_filters,
                )
            )
        return tuple(enriched)