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

        ordered = sorted(
            rules,
            key=lambda rule: (-len(rule.base_code), rule.base_code.casefold()),
        )
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

            rule = self._match_rule(code, ordered)
            if rule is None:
                unresolved_ids.append(article_id)
                unresolved_codes.append(code)
                continue

            mdb_article = mdb_by_code.get(rule.base_code.casefold())
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
                    base_code=rule.base_code,
                    base_length=rule.base_length,
                    slicing_method=rule.slicing_method,
                    reason="Applied released MDB base-article rule.",
                )
            )

        state.alignment = MaintenanceAlignment(
            status="ALIGNED" if not unresolved_ids else "PARTIAL",
            base_rules=rules,
            relations=relations,
            unresolved_article_ids=unresolved_ids,
            unresolved_article_codes=unresolved_codes,
            message=(
                f"Applied {len(rules)} released MDB base rule(s) to "
                f"{len(relations):,} PDM article(s)."
                + (
                    f" {len(unresolved_ids):,} PDM article(s) could not be aligned."
                    if unresolved_ids else ""
                )
            ),
        )
        return state.alignment

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
