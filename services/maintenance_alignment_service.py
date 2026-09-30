"""Apply released-MDB base-article rules to a Maintenance PDM snapshot.

The released MDB is authoritative. This service never invents a base boundary from
PDM and never writes to the MDB. It copies the MDB article-code/base definitions
into the Maintenance snapshot and records explicit PDM -> MDB relationships.
"""
from __future__ import annotations

from models.maintenance_alignment import (
    MaintenanceAlignmentResult,
    MaintenanceArticleRelation,
    MaintenanceBaseRule,
)
from models.snapshot import Snapshot
from services.base_service import BaseService


class MaintenanceAlignmentService(BaseService):
    """Align a PDM snapshot using the base articles already released in MDB."""

    def align(
        self,
        pdm_snapshot: Snapshot | None,
        repository_snapshot: Snapshot | None,
    ) -> MaintenanceAlignmentResult:
        if pdm_snapshot is None:
            return MaintenanceAlignmentResult(
                status="UNRESOLVED",
                message="PDM snapshot is not loaded.",
            )
        if repository_snapshot is None:
            return MaintenanceAlignmentResult(
                status="UNRESOLVED",
                message="Released MDB snapshot is not loaded.",
            )

        rules = self._released_base_rules(repository_snapshot)
        if not rules:
            self._clear_alignment(pdm_snapshot)
            return MaintenanceAlignmentResult(
                status="UNRESOLVED",
                message="Released MDB contains no base articles.",
            )

        # Longest base first is important when a released MDB contains base
        # codes where one is a prefix of another. The MDB definitions remain
        # authoritative; this only selects the most specific applicable rule.
        ordered_rules = sorted(
            rules,
            key=lambda rule: (-len(rule.base_code), rule.base_code.casefold()),
        )

        relations: list[MaintenanceArticleRelation] = []
        unresolved_ids: list[str] = []
        unresolved_codes: list[str] = []

        pdm_snapshot.maintenance_base_rules = {
            rule.base_code: {
                "base_length": rule.base_length,
                "slicing_method": rule.slicing_method,
                "source": rule.source,
            }
            for rule in rules
        }
        pdm_snapshot.maintenance_article_relations = {}
        pdm_snapshot.maintenance_unresolved_article_ids = []
        pdm_snapshot.maintenance_alignment_status = "UNRESOLVED"

        # These are existing Snapshot fields used by downstream slicing/reduction.
        # In Maintenance they are populated from the released MDB, not inferred
        # independently from the PDM.
        pdm_snapshot.base_length_overrides = {}
        pdm_snapshot.article_prefix_length = {}

        mdb_by_code = {
            str(article.code or "").strip().casefold(): article
            for article in repository_snapshot.articles
            if str(article.code or "").strip()
        }

        for article in pdm_snapshot.articles:
            pdm_code = str(article.code or "").strip()
            article_id = str(article.id or "").strip()
            if not pdm_code or not article_id:
                continue

            rule = self._match_rule(pdm_code, ordered_rules)
            if rule is None:
                unresolved_ids.append(article_id)
                unresolved_codes.append(pdm_code)
                continue

            mdb_article = mdb_by_code.get(rule.base_code.casefold())
            if mdb_article is None:
                unresolved_ids.append(article_id)
                unresolved_codes.append(pdm_code)
                continue

            relation = MaintenanceArticleRelation(
                pdm_article_id=article_id,
                pdm_article_code=pdm_code,
                mdb_article_id=str(mdb_article.id or ""),
                mdb_article_code=str(mdb_article.code or ""),
                base_code=rule.base_code,
                base_length=rule.base_length,
                slicing_method=rule.slicing_method,
                reason="Applied released MDB base-article rule.",
            )
            relations.append(relation)
            pdm_snapshot.maintenance_article_relations[article_id] = {
                "pdm_article_code": relation.pdm_article_code,
                "mdb_article_id": relation.mdb_article_id,
                "mdb_article_code": relation.mdb_article_code,
                "base_code": relation.base_code,
                "base_length": relation.base_length,
                "slicing_method": relation.slicing_method,
                "status": relation.status,
                "reason": relation.reason,
            }
            pdm_snapshot.base_length_overrides[pdm_code] = rule.base_length
            pdm_snapshot.article_prefix_length[article_id] = rule.base_length

        pdm_snapshot.maintenance_unresolved_article_ids = unresolved_ids
        pdm_snapshot.maintenance_alignment_status = (
            "ALIGNED" if not unresolved_ids else "PARTIAL"
        )

        status = pdm_snapshot.maintenance_alignment_status
        message = (
            f"Applied {len(rules)} released MDB base rule(s) to "
            f"{len(relations):,} PDM article(s)."
        )
        if unresolved_ids:
            message += f" {len(unresolved_ids):,} PDM article(s) could not be aligned."

        return MaintenanceAlignmentResult(
            status=status,
            base_rules=rules,
            relations=relations,
            unresolved_article_ids=unresolved_ids,
            unresolved_article_codes=unresolved_codes,
            message=message,
        )

    @staticmethod
    def _released_base_rules(repository_snapshot: Snapshot) -> list[MaintenanceBaseRule]:
        """Read the released MDB's base articles as the authoritative rules."""
        rules: list[MaintenanceBaseRule] = []
        seen: set[str] = set()
        for article in repository_snapshot.articles:
            code = str(article.code or "").strip()
            if not code:
                continue
            key = code.casefold()
            if key in seen:
                continue
            seen.add(key)
            rules.append(
                MaintenanceBaseRule(
                    base_code=code,
                    # The released MDB Article code is itself the base boundary.
                    # Therefore its persisted base length is the length of that
                    # released base code, not a PDM-derived guess.
                    base_length=len(code),
                )
            )
        return rules

    @staticmethod
    def _match_rule(
        pdm_code: str, rules: list[MaintenanceBaseRule]
    ) -> MaintenanceBaseRule | None:
        folded = pdm_code.casefold()
        for rule in rules:
            if folded.startswith(rule.base_code.casefold()):
                return rule
        return None

    @staticmethod
    def _clear_alignment(snapshot: Snapshot) -> None:
        snapshot.maintenance_base_rules = {}
        snapshot.maintenance_article_relations = {}
        snapshot.maintenance_unresolved_article_ids = []
        snapshot.maintenance_alignment_status = "UNRESOLVED"
