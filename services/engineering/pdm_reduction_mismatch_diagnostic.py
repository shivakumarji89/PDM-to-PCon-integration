"""Diagnostics for rejected legacy-PDM reduction candidates.

This module does not change reduction decisions. It explains exact ProductIds
that ProductsList returned outside an engineering candidate by comparing their
functional attribute/value coverage with the candidate population.

The diagnostic is advisory: ProductsList equality remains authoritative.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from services.engineering.pdm_family_reduction_service import (
    FamilyCandidate,
    FamilyValidation,
    PDMFamilyReductionService,
)


@dataclass(frozen=True)
class FunctionalGap:
    """One functional attribute/value pattern absent from an extra Product."""

    product_id: str
    attribute_id: str
    attribute_value_id: str
    supporting_product_count: int
    candidate_product_count: int
    attribute_name: str = ""

    @property
    def support_ratio(self) -> float:
        return (
            self.supporting_product_count / self.candidate_product_count
            if self.candidate_product_count else 0.0
        )


class PDMReductionMismatchDiagnostic:
    """Explain ProductsList extras without changing validation semantics."""

    def __init__(self, validator: PDMFamilyReductionService) -> None:
        self.validator = validator

    def diagnose(
        self,
        candidate: FamilyCandidate,
        validation: FamilyValidation,
        *,
        connection: Any = None,
        min_support_ratio: float = 0.90,
    ) -> tuple[FunctionalGap, ...]:
        """Find dominant functional values missing from each extra Product."""
        if validation.status != "rejected" or not validation.extra_in_filter:
            return ()
        if not 0.0 < min_support_ratio <= 1.0:
            raise ValueError("min_support_ratio must be in (0, 1]")

        product_ids = tuple(
            sorted({str(pid) for pid in validation.intended_product_ids})
        )
        extras = tuple(sorted({str(pid) for pid in validation.extra_in_filter}))
        if not product_ids or not extras:
            return ()

        rows = self.validator.repository.fetch_products_filter_attributes(
            product_ids + extras, connection=connection
        )
        functional = [
            row for row in rows
            if PDMFamilyReductionService.is_functional(row)
        ]
        by_product: dict[str, list[Any]] = {pid: [] for pid in product_ids + extras}
        for row in functional:
            pid = str(getattr(row, "ProductId", ""))
            if pid in by_product:
                by_product[pid].append(row)

        candidate_count = len(product_ids)
        support: dict[tuple[str, str], set[str]] = {}
        for pid in product_ids:
            for row in by_product[pid]:
                key = (
                    str(getattr(row, "AttributeId", "")),
                    str(getattr(row, "AttributeValueId", "")),
                )
                support.setdefault(key, set()).add(pid)

        gaps: list[FunctionalGap] = []
        for extra in extras:
            extra_values = {
                (
                    str(getattr(row, "AttributeId", "")),
                    str(getattr(row, "AttributeValueId", "")),
                )
                for row in by_product[extra]
            }
            for (attribute_id, value_id), supporting in support.items():
                ratio = len(supporting) / candidate_count
                if ratio < min_support_ratio:
                    continue
                if (attribute_id, value_id) in extra_values:
                    continue
                name = next(
                    (
                        str(getattr(row, "AttributeName", "") or "")
                        for row in rows
                        if str(getattr(row, "AttributeId", "")) == attribute_id
                        and str(getattr(row, "AttributeValueId", "")) == value_id
                    ),
                    "",
                )
                gaps.append(
                    FunctionalGap(
                        product_id=extra,
                        attribute_id=attribute_id,
                        attribute_value_id=value_id,
                        supporting_product_count=len(supporting),
                        candidate_product_count=candidate_count,
                        attribute_name=name,
                    )
                )

        return tuple(sorted(
            gaps,
            key=lambda gap: (
                gap.product_id,
                -gap.support_ratio,
                gap.attribute_id,
                gap.attribute_value_id,
            ),
        ))
