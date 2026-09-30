"""Maintenance-only PDM ↔ released-MDB article alignment."""
from __future__ import annotations

from models.maintenance_snapshot import (
    MaintenanceAlignment,
    MaintenanceArticleRelation,
    MaintenanceBaseRule,
    MaintenanceSnapshot,
)
from services.base_service import BaseService


class MaintenanceAlignmentService(BaseService):
    """Align Maintenance PDM articles against released MDB base articles."""

    def align(self, state: MaintenanceSnapshot) -> MaintenanceAlignment:
        """Align Maintenance PDM articles using PDM's authoritative slice length."""
        pdm = state.pdm_snapshot
        repository = state.repository_snapshot
        if pdm is None:
            state.clear_alignment()
            state.alignment.message = "Maintenance PDM snapshot is not loaded."
            return state.alignment
        if repository is None:
            state.clear_alignment()
            state.alignment.message = "Maintenance MDB repository is not loaded."
            return state.alignment

        rules = self._released_base_rules(repository)
        if not rules:
            state.clear_alignment()
            state.alignment.message = "Released MDB contains no base articles."
            return state.alignment

        mdb_by_code = {
            str(article.code or "").strip().casefold(): article
            for article in repository.articles
            if str(article.code or "").strip()
        }

        relations: list[MaintenanceArticleRelation] = []
        unresolved_ids: list[str] = []
        unresolved_codes: list[str] = []

        for article in pdm.articles:
            code = str(article.code or "").strip()
            article_id = str(article.id or "").strip()
            if not code or not article_id:
                continue

            base_length, method = self._authoritative_base_length(pdm, article)
            if base_length <= 0:
                unresolved_ids.append(article_id)
                unresolved_codes.append(code)
                continue
            if base_length > len(code):
                unresolved_ids.append(article_id)
                unresolved_codes.append(code)
                continue

            base_code = code[:base_length]
            mdb_article = mdb_by_code.get(base_code.casefold())
            if mdb_article is None:
                unresolved_ids.append(article_id)
                unresolved_codes.append(code)
                continue

            relations.append(
                MaintenanceArticleRelation(
                    pdm_article_id=article_id,
                    pdm_article_code=code,
                    mdb_article_id=str(mdb_article.id or ""),
                    mdb_article_code=str(mdb_article.code or ""),
                    base_code=base_code,
                    base_length=base_length,
                    slicing_method=method,
                    reason="Base derived from PDM article prefix length.",
                )
            )

        state.alignment = MaintenanceAlignment(
            status="ALIGNED" if not unresolved_ids else "PARTIAL",
            base_rules=rules,
            relations=relations,
            unresolved_article_ids=unresolved_ids,
            unresolved_article_codes=unresolved_codes,
            message=(
                f"Aligned {len(relations):,} PDM article(s) using PDM slicing rules."
                + (
                    f" {len(unresolved_ids):,} article(s) remain unresolved."
                    if unresolved_ids else ""
                )
            ),
        )
        return state.alignment

    @staticmethod
    def _authoritative_base_length(snapshot, article) -> tuple[int, str]:
        code = str(article.code or "").strip()

        # An explicit Maintenance/base-length registry override is authoritative
        # when present. It is keyed by article CODE, not ItemId.
        overrides = getattr(snapshot, "base_length_overrides", {}) or {}
        override = overrides.get(code)
        if isinstance(override, int) and override > 0:
            return override, "MAINTENANCE_BASE_LENGTH_OVERRIDE"

        # PDMService populates this from Item.Notes, with category-master fallback.
        prefix_by_id = getattr(snapshot, "article_prefix_length", {}) or {}
        prefix = prefix_by_id.get(str(article.id))
        if isinstance(prefix, int) and prefix > 0:
            return prefix, "PDM_ITEM_NOTES_PREFIX_LENGTH"

        # Family loading normally materializes ArticleSets. Use their stored
        # base boundary only as a fallback when PDM did not provide a prefix.
        for article_set in getattr(snapshot, "article_sets", []) or []:
            if str(article.id) in (str(item_id) for item_id in article_set.article_ids):
                length = int(article_set.base_length or 0)
                if length > 0:
                    return length, "PDM_ARTICLE_SET_BASE_LENGTH"

        return 0, "UNRESOLVED"

    @staticmethod
    def _released_base_rules(repository) -> list[MaintenanceBaseRule]:
        rules: list[MaintenanceBaseRule] = []
        seen: set[str] = set()
        for article in repository.articles:
            code = str(article.code or "").strip()
            if not code or code.casefold() in seen:
                continue
            seen.add(code.casefold())
            rules.append(MaintenanceBaseRule(base_code=code, base_length=len(code)))
        return rules

    @staticmethod
    def _match_rule(code: str, rules: list[MaintenanceBaseRule]):
        folded = code.casefold()
        for rule in rules:
            if folded.startswith(rule.base_code.casefold()):
                return rule
        return None
