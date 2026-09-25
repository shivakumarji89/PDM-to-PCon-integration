"""Generic, PDM-provable base/series reduction.

Legacy PDM stores no Product-to-series/base-family relationship. There is no
authoritative column or table that groups several ``Product`` rows into one
base/series article (``ProductCode``/``ProductCodeId`` is a per-site
order-code/pricing entity, ``IsSuperProduct``/``IsSuperItem`` mark BOM
component assemblies, and ``Item.Notes`` prefix hints feed only pCon VARCOND
relation generation - none of these define a series identity; see
``docs/legacy-pdm-reduction-engine.md`` and the extracted
``docs/Legacy_PDM_Business_Logic`` handbook for the evidence trail).

The only thing legacy PDM can prove is whether a given set of
AttributeValueIds selects *exactly* a given set of ProductIds within one
ProductRange, through the real ``dbo.ProductsList`` boundary. Its body
(recovered via ``sp_helptext``) is:

    SELECT p.ProductId FROM Product p
    INNER JOIN ProductAttributeValues pav ON pav.ProductId = p.ProductId
    WHERE p.ProductRangeId = @ProductRangeId
      AND pav.AttributeValueId IN (<selected AttributeValueIds>)
    GROUP BY p.ProductId
    HAVING COUNT(*) = <selected count>
    -- restricted to Products with >=1 released Item, or NewProduct = 1

This is a containment (AND) filter, not a set-equality filter: a Product
matches when its ProductAttributeValues is a *superset* of the selection.
Choosing the full common intersection of an intended family's non-order-code
AttributeValueIds as the selection is therefore the tightest (least likely
to over-match) input this boundary accepts.

Because the procedure filters the COMPLETE eligible population of the range,
the comparison only means something once the caller HOLDS that population. A
candidate drawn from a partly loaded range is reported ``unresolved``: the
Products nobody loaded come back as over-matches whatever the grouping is, so
treating them as a rejection would blame the grouping for a coverage gap.
``PDMService.complete_product_ranges`` closes that gap; the equality test
itself is never weakened.

So this service takes an engineering-supplied candidate grouping - which
ProductIds are proposed to share one reduced base article - and PROVES or
REJECTS it against that real boundary. It never invents a grouping and never
derives a base identity from article characters, lengths, or prefixes.
US ranges (``ProductCategory.USCategory = 1``) cannot be proven here at all,
and are reported ``unresolved`` rather than approximated - see
:meth:`PDMFamilyReductionService.validate_family` for the recovered
``USProductsList`` body and why its result is not comparable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from repositories.legacy_pdm_compat_repository import LegacyPDMCompatRepository
from services.base_service import BaseService
from services.engineering.legacy_pdm_reduction_service import (
    LegacyPDMReductionService,
    PDMSelection,
)


@dataclass(frozen=True)
class FamilyCandidate:
    """An engineering-declared proposal: these ProductIds should share one
    reduced base article. ``base`` is an opaque caller label - this service
    never derives, inspects, or validates its characters."""

    base: str
    product_ids: tuple[str, ...]


@dataclass(frozen=True)
class FamilyValidation:
    """Outcome of proving (or rejecting) one :class:`FamilyCandidate`."""

    base: str
    intended_product_ids: tuple[str, ...] = ()
    product_range_id: Any = None
    #: The range's ``ProductCategoryId`` - the key ``USProductsList`` uses.
    product_category_id: Any = None
    functional_attribute_value_ids: tuple[str, ...] = ()
    configurable_attribute_ids: tuple[str, ...] = ()
    filtered_product_ids: tuple[str, ...] = ()
    #: "validated" | "rejected" | "unresolved" | "error". ``unresolved`` also
    #: covers a ProductRange the caller loaded only part of: ``ProductsList``
    #: filters the complete range, so the comparison is not available yet.
    status: str = "unresolved"
    reason: str = ""
    #: Size of the complete legacy-eligible population of ``product_range_id``
    #: (0 when it was not looked up, i.e. no ``known_product_ids`` was given).
    range_product_count: int = 0
    #: How many of those eligible Products the caller had NOT loaded.
    unloaded_range_product_count: int = 0
    #: ``True``/``False`` once the population was looked up, ``None`` when the
    #: caller supplied no loaded set - never assume completeness.
    range_population_complete: bool | None = None
    #: Over-matched Products that the caller never loaded. A non-empty value
    #: means the proposed base over-selects *outside* the loaded scope, which a
    #: purely local (snapshot-only) check could not have detected.
    extra_outside_known: tuple[str, ...] = ()

    @property
    def missing_from_filter(self) -> tuple[str, ...]:
        intended = set(self.intended_product_ids)
        return tuple(sorted(intended - set(self.filtered_product_ids)))

    @property
    def extra_in_filter(self) -> tuple[str, ...]:
        intended = set(self.intended_product_ids)
        return tuple(sorted(set(self.filtered_product_ids) - intended))


class PDMFamilyReductionService(BaseService):
    """Validate engineering-proposed Product groupings against the real
    legacy ``ProductsList`` filter boundary. Read-only; never writes to PDM
    and never mutates Engineering/Snapshot state."""

    #: ``dbo.ProductsList`` declares ``@SelAttribValuesXml VARCHAR(4000)``.
    MAX_SELECTOR_XML = 4000

    def __init__(self, context) -> None:
        super().__init__(context)
        self.repository = LegacyPDMCompatRepository(context)

    def validate_family(
        self,
        candidate: FamilyCandidate,
        language_id: Any = 1,
        connection: Any = None,
        known_product_ids: Sequence[Any] | None = None,
    ) -> FamilyValidation:
        """Prove or reject one candidate through the real ``ProductsList``.

        ``known_product_ids`` is the caller's LOADED Product population (e.g.
        the products a Snapshot actually holds). When supplied, the complete
        legacy-eligible population of the resolved ProductRange is read back so
        the result can state whether that loaded set covers the range, and
        which over-matched Products fall outside it. Without it the
        completeness fields stay ``None``/empty - the result never claims
        coverage it did not check.
        """
        product_ids = tuple(sorted({str(pid) for pid in candidate.product_ids}))

        if len(product_ids) < 2:
            return FamilyValidation(
                base=candidate.base,
                intended_product_ids=product_ids,
                status="unresolved",
                reason="A family needs at least two ProductIds to reduce.",
            )

        range_rows = self.repository.fetch_products_range_info(
            product_ids, connection=connection
        )
        range_by_product = {str(r.ProductId): r for r in range_rows}
        missing = [pid for pid in product_ids if pid not in range_by_product]
        if missing:
            return FamilyValidation(
                base=candidate.base,
                intended_product_ids=product_ids,
                status="unresolved",
                reason=f"ProductId(s) not found in PDM: {missing}",
            )

        range_ids = {str(row.ProductRangeId) for row in range_by_product.values()}
        if len(range_ids) != 1:
            return FamilyValidation(
                base=candidate.base,
                intended_product_ids=product_ids,
                status="unresolved",
                reason=(
                    "Family spans multiple ProductRangeIds "
                    f"{sorted(range_ids)}; ProductsList can only be proven "
                    "within one ProductRange."
                ),
            )
        product_range_id = range_by_product[product_ids[0]].ProductRangeId

        product_category_id, is_us = self.repository.range_scope(
            product_range_id, connection=connection
        )
        if is_us:
            # ProductSelector.LoadProducts routes a USCategory range to
            # USProductsList, whose recovered body selects
            #   USItem JOIN USItemAttributeValues itav
            #     ON itav.USAttributeValueId = x.AttributeValueId
            #   WHERE USItem.ProductCategoryId = @productCategoryId
            #   GROUP BY USItem.USItemId HAVING COUNT(*) = @AttribCount
            # and returns USItem.USItemId aliased as "ProductId".
            # Two disjoint key spaces make the comparison impossible, not
            # merely unimplemented: the result is USItemIds (USItem carries no
            # ProductId/ProductRangeId column at all), and the selector matches
            # USAttributeValueIds, for which no AttributeValue-level mapping
            # exists - USAttribute links only whole attributes. Running the
            # non-US ProductsList here instead would be an approximation with
            # no legacy basis, so the candidate stays unproven.
            return FamilyValidation(
                base=candidate.base,
                intended_product_ids=product_ids,
                product_range_id=product_range_id,
                product_category_id=product_category_id,
                status="unresolved",
                reason=(
                    f"ProductRangeId {product_range_id} belongs to US "
                    f"ProductCategoryId {product_category_id} "
                    "(ProductCategory.USCategory = 1). The legacy selector for "
                    "a US category is USProductsList, which returns USItemIds "
                    "from USItem/USItemAttributeValues and matches "
                    "USAttributeValueIds - both disjoint from the "
                    "Product.ProductId / AttributeValue.AttributeValueId space "
                    "this candidate is expressed in, with no value-level "
                    "mapping between them. No exact ProductId-set comparison "
                    "is possible, so the family is left unproven rather than "
                    "approximated through the non-US ProductsList."
                ),
            )

        known = (
            None if known_product_ids is None
            else {str(pid) for pid in known_product_ids}
        )
        range_count = 0
        unloaded_count = 0
        population_complete: bool | None = None
        if known is not None:
            range_population = {
                str(row.ProductId)
                for row in self.repository.fetch_range_product_ids(
                    product_range_id, connection=connection
                )
            }
            range_count = len(range_population)
            unloaded_count = len(range_population - known)
            population_complete = not (range_population - known)

        attribute_rows = self.repository.fetch_products_filter_attributes(
            product_ids, connection=connection
        )
        functional_by_product, configurable_by_product = self._split_attributes(
            product_ids, attribute_rows
        )

        common_functional = self._common_functional_values(functional_by_product)
        if not common_functional:
            return FamilyValidation(
                base=candidate.base,
                intended_product_ids=product_ids,
                product_range_id=product_range_id,
                product_category_id=product_category_id,
                status="unresolved",
                reason=(
                    "No shared non-order-code (functional) AttributeValueId "
                    "across the proposed family; PDM provides no basis to "
                    "filter this grouping."
                ),
                range_product_count=range_count,
                unloaded_range_product_count=unloaded_count,
                range_population_complete=population_complete,
            )

        configurable_attribute_ids = tuple(
            sorted(set().union(*configurable_by_product.values()))
        )

        # The selector carries each value's REAL owning AttributeId so the XML
        # is byte-shaped exactly like TemplateContainer.AttributeXml. The
        # procedure matches on AttributeValueId, but emitting a placeholder id
        # would make the payload unfaithful to the legacy boundary.
        attribute_of_value = self._attribute_ids_by_value(attribute_rows)
        xml = LegacyPDMReductionService.build_attribute_xml(
            PDMSelection(
                attribute_id=attribute_of_value.get(value_id, ""),
                attribute_value_id=value_id,
            )
            for value_id in sorted(common_functional)
        )
        # ProductsList branches on LEN(@SelAttribValuesXml) = 0, so an empty
        # selector means "return the whole range" - never "return nothing".
        # An <attributes></attributes> payload is NOT empty by that test: it
        # takes the filter branch with @AttribCount = 0, whose inner join
        # yields no rows at all. Guard it rather than emit a silent no-match.
        if not common_functional:  # pragma: no cover - unreachable, kept as a guard
            raise AssertionError("refusing to send an empty ProductsList selector")
        if len(xml) > self.MAX_SELECTOR_XML:
            return FamilyValidation(
                base=candidate.base,
                intended_product_ids=product_ids,
                product_range_id=product_range_id,
                product_category_id=product_category_id,
                functional_attribute_value_ids=tuple(sorted(common_functional)),
                configurable_attribute_ids=configurable_attribute_ids,
                status="unresolved",
                reason=(
                    f"Selector XML is {len(xml)} characters; "
                    f"ProductsList declares @SelAttribValuesXml as "
                    f"VARCHAR({self.MAX_SELECTOR_XML}) and would silently "
                    "truncate it into malformed XML. The family is left "
                    "unproven rather than validated against a truncated filter."
                ),
                range_product_count=range_count,
                unloaded_range_product_count=unloaded_count,
                range_population_complete=population_complete,
            )

        filtered_rows = self.repository.fetch_legacy_filtered_products(
            product_range_id, language_id, xml, connection=connection
        )
        filtered_ids = tuple(
            sorted(
                {
                    str(getattr(row, "ProductId"))
                    for row in filtered_rows
                    if getattr(row, "ProductId", None) is not None
                }
            )
        )

        intended = set(product_ids)
        returned = set(filtered_ids)
        extra_outside_known = (
            () if known is None
            else tuple(sorted((returned - intended) - known))
        )
        # ProductsList answers over the COMPLETE eligible population of the
        # range. A candidate drawn from a partially loaded range is therefore
        # not comparable against it at all: the Products nobody loaded come back
        # as over-matches whatever the grouping is. That is an incomplete
        # question, not a wrong answer, so it is UNRESOLVED - never a pass, and
        # never a rejection that blames the grouping. The in-scope comparison is
        # still reported, because the disagreement that remains once the range
        # is completed is visible in it already.
        if population_complete is False:
            in_scope_extra = sorted((returned - intended) & (known or set()))
            detail = (
                f" Inside the loaded scope ProductsList also returned "
                f"{len(in_scope_extra)} Product(s) the candidate excludes "
                f"({', '.join(in_scope_extra[:10])}"
                f"{', ...' if len(in_scope_extra) > 10 else ''}), which will "
                f"still have to be explained once the range is complete."
                if in_scope_extra else
                " Inside the loaded scope ProductsList returned exactly the "
                "candidate."
            )
            status = "unresolved"
            reason = (
                f"ProductRangeId {product_range_id} is only partly loaded: "
                f"{unloaded_count} of its {range_count} legacy-eligible "
                f"Products are missing from the caller's population. "
                f"ProductsList filters the whole range, so no exact comparison "
                f"is possible until the range is complete." + detail
            )
        else:
            status = "validated" if returned == intended else "rejected"
            reason = (
                ""
                if status == "validated"
                else (
                    "ProductsList did not return exactly the intended "
                    f"ProductId set: {len(intended - returned)} missing, "
                    f"{len(returned - intended)} extra."
                )
            )
        return FamilyValidation(
            base=candidate.base,
            intended_product_ids=product_ids,
            product_range_id=product_range_id,
            product_category_id=product_category_id,
            functional_attribute_value_ids=tuple(sorted(common_functional)),
            configurable_attribute_ids=configurable_attribute_ids,
            filtered_product_ids=filtered_ids,
            status=status,
            reason=reason,
            range_product_count=range_count,
            unloaded_range_product_count=unloaded_count,
            range_population_complete=population_complete,
            extra_outside_known=extra_outside_known,
        )

    def validate_families(
        self,
        candidates: Iterable[FamilyCandidate],
        language_id: Any = 1,
        known_product_ids: Sequence[Any] | None = None,
    ) -> tuple[FamilyValidation, ...]:
        """Validate many candidates over one shared connection.

        A failure on one candidate is recorded as an ``"error"`` result
        carrying the exception text and does NOT stop the run or quietly pass
        the candidate off as valid. When the connection itself cannot be
        obtained EVERY candidate comes back as ``"error"`` for the same
        reason: a candidate that could not be checked is never treated as
        checked.
        """
        candidates = list(candidates)
        try:
            connection = self.repository.get_connection()
        except Exception as error:
            return tuple(
                self._error(candidate, error) for candidate in candidates
            )
        try:
            results: list[FamilyValidation] = []
            for candidate in candidates:
                try:
                    results.append(
                        self.validate_family(
                            candidate,
                            language_id,
                            connection=connection,
                            known_product_ids=known_product_ids,
                        )
                    )
                except Exception as error:  # surfaced, never swallowed
                    results.append(self._error(candidate, error))
            return tuple(results)
        finally:
            connection.close()

    @staticmethod
    def _error(candidate: FamilyCandidate, error: Exception) -> FamilyValidation:
        """An explicit un-checked verdict - never a pass."""
        return FamilyValidation(
            base=candidate.base,
            intended_product_ids=tuple(
                sorted({str(pid) for pid in candidate.product_ids})
            ),
            status="error",
            reason=f"{type(error).__name__}: {error}",
        )

    @staticmethod
    def is_functional(row: Any) -> bool:
        """Whether one ProductAttributeValues row is a FUNCTIONAL value.

        Legacy PDM does not state this once - it states it four times, and the
        four tests do not fully agree (146 of 7,730 Attributes differ in live
        data). Rather than pick one, this requires ALL of them, because the
        only dangerous error here is admitting an order-code-bearing value into
        the family selector: that could make a filter match a family for the
        wrong reason and validate a base that legacy would not support. Being
        too strict merely leaves a family unproven.

        =====================================  =====================================
        Legacy test                            Source
        =====================================  =====================================
        ``Attribute.AttributeType = 0``        ``AttributeValidator.isFunctionalAttributeValue``
                                               (``AttributeValidator.cs``), and the
                                               functional/physical split in
                                               ``TemplateContainer.cs``
        ``AttributeValue.ModelSuffix IS NULL`` ``UIGroupMaintenance.getUIGroupIdForProduct``
                                               - the legacy "which Products belong
                                               to one group" query
        ``Attribute.OrderCodeFormatKey IS      ``ProductIntroduction.loadExistingProducts``
        NULL`` (and ``AttributeType <> 2``,
        implied by ``= 0``)
        ``AttributeValue.OrderCodeValue``      ``PermutateThread.cs`` -
        empty                                  Physical vs Functional
                                               AttributeValueIds
        =====================================  =====================================
        """
        def blank(name: str) -> bool:
            return not str(getattr(row, name, "") or "").strip()

        return (
            int(getattr(row, "AttributeType", 0) or 0) == 0
            and blank("OrderCodeFormatKey")
            and blank("OrderCodeValue")
            and blank("ModelSuffix")
        )

    @classmethod
    def _split_attributes(
        cls, product_ids: Sequence[str], attribute_rows: Iterable[Any]
    ) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
        """Partition each Product's rows into functional AttributeValueIds and
        configurable AttributeIds (see :meth:`is_functional`).

        Configurable/order-code-bearing attributes drive the after-dot article
        suffix and must never be treated as shared family identity, even when
        their value happens to be identical across every member of the
        candidate set.
        """
        functional: dict[str, set[str]] = {pid: set() for pid in product_ids}
        configurable: dict[str, set[str]] = {pid: set() for pid in product_ids}
        for row in attribute_rows:
            product_id = str(getattr(row, "ProductId"))
            if product_id not in functional:
                continue
            if cls.is_functional(row):
                functional[product_id].add(str(getattr(row, "AttributeValueId")))
            else:
                configurable[product_id].add(str(getattr(row, "AttributeId")))
        return functional, configurable

    @staticmethod
    def _attribute_ids_by_value(attribute_rows: Iterable[Any]) -> dict[str, str]:
        """AttributeValueId -> its owning AttributeId (for the selector XML)."""
        return {
            str(getattr(row, "AttributeValueId")): str(getattr(row, "AttributeId"))
            for row in attribute_rows
        }

    @staticmethod
    def _common_functional_values(
        functional_by_product: dict[str, set[str]]
    ) -> set[str]:
        value_sets = list(functional_by_product.values())
        if not value_sets or any(not values for values in value_sets):
            return set()
        return set.intersection(*value_sets)
