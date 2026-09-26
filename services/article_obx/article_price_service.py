"""Resolve Article OBX prices from repository Snapshot data for an explicit date."""
from __future__ import annotations

import re
from dataclasses import dataclass

from services.base_service import BaseService
from services.article_obx.article_obx_models import ArticlePermutation, ArticlePrice


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

    @staticmethod
    def _ymd(value: str) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())[:8]

    @classmethod
    def _valid_on(cls, record, effective_date: str) -> bool:
        date = cls._ymd(effective_date)
        start = cls._ymd(getattr(record, "valid_from", "")) or "00000000"
        end = cls._ymd(getattr(record, "valid_to", "")) or "99991231"
        return start <= date <= end

    @staticmethod
    def _condition_tokens(condition: str) -> list[tuple[str, str]]:
        """Extract simple VARCOND name=value terms from a repository row."""
        return [
            (match.group(1).strip().upper(), match.group(2).strip().upper())
            for match in re.finditer(r"([A-Za-z0-9_.-]+)\s*=\s*([^\s;]+)", condition or "")
        ]

    @classmethod
    def _condition_matches(cls, condition: str, codes: set[str]) -> bool:
        if not condition.strip():
            return True
        tokens = cls._condition_tokens(condition)
        if not tokens:
            return False
        return all(
            key in codes or value in codes or f"{key}={value}" in codes
            for key, value in tokens
        )

    @classmethod
    def _select_rows(cls, records, article_code: str, currency: str, effective_date: str):
        currency = currency.upper()
        rows = [
            record for record in records
            if str(getattr(record, "article_code", "") or "") == article_code
            and str(getattr(record, "currency", "") or "").upper() == currency
            and cls._valid_on(record, effective_date)
        ]
        return sorted(
            rows,
            key=lambda record: cls._ymd(getattr(record, "valid_from", "")),
            reverse=True,
        )

    def resolve(
        self,
        permutations: list[ArticlePermutation],
        request: ArticlePriceRequest,
    ) -> list[ArticlePrice]:
        if not request.currency.strip():
            raise ValueError("currency is required")
        if not request.effective_date.strip():
            raise ValueError("effective_date is required")

        snapshot = self.context.repository_snapshot or self.context.active_snapshot
        if snapshot is None:
            return [
                ArticlePrice(
                    article_id=p.article_id,
                    article_code=p.final_article,
                    currency=request.currency.upper(),
                    effective_date=request.effective_date,
                    site_id=request.site_id,
                    unresolved_reason="No repository snapshot is loaded",
                )
                for p in permutations
            ]

        results: list[ArticlePrice] = []
        for permutation in permutations:
            rows = self._select_rows(
                snapshot.price_records,
                permutation.final_article,
                request.currency,
                request.effective_date,
            )

            if not rows:
                results.append(ArticlePrice(
                    article_id=permutation.article_id,
                    article_code=permutation.final_article,
                    currency=request.currency.upper(),
                    effective_date=request.effective_date,
                    site_id=request.site_id,
                    unresolved_reason="Repository price could not be resolved for article/date/currency",
                ))
                continue

            codes = {
                str(value.code or value.value or "").strip().upper()
                for value in permutation.all_values
                if str(value.code or value.value or "").strip()
            }

            base_rows = [
                row for row in rows
                if str(getattr(row, "level", "") or "B").upper() == "B"
                and self._condition_matches(
                    str(getattr(row, "variant_condition", "") or ""), codes
                )
            ]
            if not base_rows:
                results.append(ArticlePrice(
                    article_id=permutation.article_id,
                    article_code=permutation.final_article,
                    currency=request.currency.upper(),
                    effective_date=request.effective_date,
                    site_id=request.site_id,
                    unresolved_reason="Repository base price could not be resolved",
                ))
                continue

            base = float(base_rows[0].value)
            increment_rows = [
                row for row in rows
                if str(getattr(row, "level", "") or "").upper() != "B"
                and self._condition_matches(
                    str(getattr(row, "variant_condition", "") or ""), codes
                )
            ]

            increments = tuple(
                (
                    str(getattr(row, "variant_condition", "") or ""),
                    float(row.value),
                )
                for row in increment_rows
            )
            total = round(base + sum(value for _, value in increments), 2)

            results.append(ArticlePrice(
                article_id=permutation.article_id,
                article_code=permutation.final_article,
                currency=request.currency.upper(),
                effective_date=request.effective_date,
                site_id=request.site_id,
                base_price=base,
                option_increments=increments,
                total_price=total,
            ))

        return results
