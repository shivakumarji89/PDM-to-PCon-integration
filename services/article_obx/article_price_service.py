"""Resolve Article OBX prices from PDM for an explicit effective date."""
from __future__ import annotations

from dataclasses import dataclass

from repositories.pdm_repository import PDMRepository
from services.base_service import BaseService
from services.sif_validation_service import SifValidationService
from services.article_obx.article_obx_models import ArticlePermutation, ArticlePrice


@dataclass(frozen=True)
class ArticlePriceRequest:
    """PDM pricing inputs for an Article OBX run."""

    currency: str
    effective_date: str
    site_id: int = 1


class ArticlePriceService(BaseService):
    """Resolve prices without changing the Snapshot price baseline."""

    def resolve(
        self,
        permutations: list[ArticlePermutation],
        request: ArticlePriceRequest,
    ) -> list[ArticlePrice]:
        if not request.currency.strip():
            raise ValueError("currency is required")
        if not request.effective_date.strip():
            raise ValueError("effective_date is required")

        # PDM exposes list pricing for Items, including super-items. The
        # existing SIF/OBX pricing path resolves the concrete Item code directly;
        # do not invent component-price aggregation here.
        direct = [p for p in permutations if p.final_article]
        results_by_id: dict[str, ArticlePrice] = {}

        if direct:
            repo = PDMRepository(self.context)
            conn = repo.get_connection()
            try:
                items = [p.final_article for p in direct if p.final_article]
                base_rows = repo.fetch_item_base_prices(
                    items,
                    request.currency.upper(),
                    request.effective_date,
                    connection=conn,
                    site_id=request.site_id,
                )
                base_by_item = {
                    str(row.Item): (
                        None if row.price is None else float(row.price)
                    )
                    for row in base_rows
                }

                option_items = sorted({
                    p.final_article for p in direct if p.options and p.final_article
                })
                inc_rows = (
                    repo.fetch_item_option_increment_prices(
                        option_items,
                        request.currency.upper(),
                        request.effective_date,
                        request.site_id,
                        conn,
                    )
                    if option_items
                    else []
                )
                inc_by_item: dict[str, dict[str, dict[str, float]]] = {}
                fabric_by_item: dict[str, dict[str, dict[str, float]]] = {}
                fabric_targets_by_item: dict[str, dict[str, list[str]]] = {}

                for row in inc_rows:
                    item = str(row.Item)
                    group = str(getattr(row, "OptionId", "") or "")
                    code = str(getattr(row, "OrderCodeValue2", "") or "").strip().upper()
                    if not code:
                        continue
                    value = getattr(row, "IncPrice", None)
                    price = 0.0 if value is None else float(value)
                    inc_by_item.setdefault(item, {}).setdefault(group, {})[code] = price

                    is_fabric = int(getattr(row, "IsFabric", 0) or 0)
                    if is_fabric == 1 and code.endswith("#") and value is not None:
                        fabric_by_item.setdefault(item, {}).setdefault(group, {})[code] = price
                    elif is_fabric == 2:
                        parent_group = str(getattr(row, "ParentOptId", "") or "")
                        if parent_group:
                            fabric_targets_by_item.setdefault(item, {}).setdefault(
                                code, []
                            ).append(parent_group)

                for permutation in direct:
                    item = permutation.final_article
                    base = base_by_item.get(item)
                    if base is None:
                        results_by_id[permutation.article_id] = ArticlePrice(
                            article_id=permutation.article_id,
                            article_code=item,
                            currency=request.currency.upper(),
                            effective_date=request.effective_date,
                            site_id=request.site_id,
                            unresolved_reason="PDM base price could not be resolved",
                        )
                        continue

                    codes = [value.code for value in permutation.options if value.code]
                    upcharge = SifValidationService._match_inc_groups(
                        inc_by_item.get(item, {}),
                        codes,
                        fabric_by_item.get(item, {}),
                        fabric_targets_by_item.get(item, {}),
                    )

                    results_by_id[permutation.article_id] = ArticlePrice(
                        article_id=permutation.article_id,
                        article_code=item,
                        currency=request.currency.upper(),
                        effective_date=request.effective_date,
                        site_id=request.site_id,
                        base_price=base,
                        option_increments=tuple(),
                        total_price=round(base + upcharge, 2),
                    )
            finally:
                conn.close()

        for permutation in permutations:
            if permutation.article_id in results_by_id:
                continue
            results_by_id[permutation.article_id] = ArticlePrice(
                article_id=permutation.article_id,
                article_code=permutation.final_article,
                currency=request.currency.upper(),
                effective_date=request.effective_date,
                site_id=request.site_id,
                unresolved_reason="Article has no direct price",
            )

        return [results_by_id[p.article_id] for p in permutations if p.article_id in results_by_id]
