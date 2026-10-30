"""Resolve Article OBX prices from repository Snapshot data for an explicit date.

The arithmetic (row selection, base + conditional increments, percentages,
rounding) lives in ``services.ocd_engine.pricing``; this service adapts
Snapshot price records and generated permutations to it. One price is
resolved *per permutation*, in the same order as the permutations given.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from services.base_service import BaseService
from services.article_obx.article_obx_models import ArticlePermutation, ArticlePrice
from services.ocd_engine.pricing import PriceCalculator, PriceRow, ymd


@dataclass(frozen=True)
class ArticlePriceRequest:
    """Repository pricing inputs for an Article OBX run."""

    currency: str
    effective_date: str
    site_id: int = 1


class ArticlePriceService(BaseService):
    """Resolve prices exclusively from the active repository Snapshot.

    The generator must not query PDM during OBX generation. Repository import
    is responsible for materialising Snapshot.price_records.
    """

    #: Legacy helper kept for callers that normalise dates.
    _ymd = staticmethod(ymd)

    @staticmethod
    def _rows(price_records) -> list[PriceRow]:
        rows = []
        for record in price_records:
            code = str(getattr(record, "article_code", "") or "")
            if not code or getattr(record, "is_global", False):
                continue                   # global rows carry full-item conditions, not OCD keys
            level = str(getattr(record, "level", "") or "B").upper()
            rows.append(PriceRow(
                article=code,
                var_cond=str(getattr(record, "variant_condition", "") or "").strip().upper(),
                level=level, value=Decimal(str(getattr(record, "value", 0) or 0)), is_fix=True,
                currency=str(getattr(record, "currency", "") or "").upper(),
                date_from=ymd(getattr(record, "valid_from", "")) or "00000000",
                date_to=ymd(getattr(record, "valid_to", "")) or "99991231",
            ))
        return rows

    @staticmethod
    def _keys(permutation: ArticlePermutation) -> tuple[str, ...]:
        if permutation.variant_conditions:
            return permutation.variant_conditions
        return tuple(part for part in str(permutation.variant_condition or "").split() if part)

    def resolve(
        self,
        permutations: list[ArticlePermutation],
        request: ArticlePriceRequest,
    ) -> list[ArticlePrice]:
        if not request.currency.strip():
            raise ValueError("currency is required")
        if not request.effective_date.strip():
            raise ValueError("effective_date is required")

        currency = request.currency.upper()

        def unresolved(permutation, reason):
            return ArticlePrice(
                article_id=permutation.article_id,
                article_code=permutation.final_article,
                currency=currency,
                effective_date=request.effective_date,
                site_id=request.site_id,
                unresolved_reason=reason,
            )

        snapshot = self.context.qa_snapshot
        if snapshot is None:
            return [unresolved(p, "No repository snapshot is loaded") for p in permutations]

        rows = self._rows(snapshot.price_records)
        calculator = PriceCalculator(rows)
        date = ymd(request.effective_date)
        has_rows: set[str] = {
            r.article for r in rows if r.currency == currency and r.date_from <= date <= r.date_to
        }

        results: list[ArticlePrice] = []
        for permutation in permutations:
            if permutation.base_code not in has_rows:
                results.append(unresolved(
                    permutation, "Repository price could not be resolved for article/date/currency"))
                continue
            factors = dict(getattr(permutation, "pricing_factors", ()) or ())
            priced = calculator.price(
                permutation.base_code, self._keys(permutation),
                price_date=request.effective_date, currency=currency, factors=factors,
            )
            if priced.total is None:
                results.append(unresolved(permutation, "Repository base price could not be resolved"))
                continue
            increments = tuple(
                (c.key, float(c.amount)) for c in priced.components if c.level != "B"
            )
            results.append(ArticlePrice(
                article_id=permutation.article_id,
                article_code=permutation.final_article,
                currency=currency,
                effective_date=request.effective_date,
                site_id=request.site_id,
                base_price=float(priced.base),
                option_increments=increments,
                total_price=float(priced.total),
            ))
        return results
