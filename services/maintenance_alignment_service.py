"""Maintenance-only PDM ↔ released-MDB article alignment.

In Maintenance the released MDB is the authority for the Base Article boundary.
Every released MDB article (``tCOMd_Article``) is a base article, so:

    PDM article
        → its released MDB base article (code begins the PDM article number)
        → base length = len(MDB base article code)
        → PDM ``base_length_overrides[article.code]``
          (the same input Development's manual Articles boundary uses)
        → unchanged PDM engine ``materialize_article_sets``

``align()`` uses the same resolver, so for every resolved article
``base_code == pdm_code[:len(mdb_code)]``. Development never calls this service
and keeps PDM's own ``article_prefix_length`` behaviour.
"""
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

    def prepare_pdm_scope(self, pdm_snapshot, mdb_import_snapshot) -> int:
        """Feed released-MDB base lengths into the existing PDM engine.

        Writes the MDB base lengths into ``base_length_overrides`` and re-runs
        the unchanged Development reduction engine (``materialize_article_sets``,
        also run by PDMService during loading) so the Article Sets use them.
        """
        session = self.context.workflow_session("maintenance_base_length_overrides")
        new_scope = (
            session.get("pdm_snapshot") is not pdm_snapshot
            or session.get("mdb_import_snapshot") is not mdb_import_snapshot
        )
        if new_scope:
            self.restore_pdm_scope()
            session = self.context.workflow_session("maintenance_base_length_overrides")
            session["pdm_snapshot"] = pdm_snapshot
            session["mdb_import_snapshot"] = mdb_import_snapshot
            session["original_overrides"] = dict(
                getattr(pdm_snapshot, "base_length_overrides", {}) or {}
            )

        applied = self.apply_released_mdb_base_lengths(pdm_snapshot, mdb_import_snapshot)
        if applied:
            self.context.engineering_reduction_service.materialize_article_sets(pdm_snapshot)
        elif new_scope:
            self.context.clear_workflow_session("maintenance_base_length_overrides")
        return applied

    def restore_pdm_scope(self) -> bool:
        """Restore the shared PDM overrides after Maintenance stops using them."""
        session = self.context.workflow_session("maintenance_base_length_overrides")
        pdm_snapshot = session.get("pdm_snapshot")
        if pdm_snapshot is None:
            return False

        pdm_snapshot.base_length_overrides = dict(session.get("original_overrides", {}))
        self.context.engineering_reduction_service.materialize_article_sets(pdm_snapshot)
        self.context.clear_workflow_session("maintenance_base_length_overrides")
        return True

    @classmethod
    def apply_released_mdb_base_lengths(cls, pdm_snapshot, mdb_import_snapshot) -> int:
        """Set ``base_length_overrides[code] = len(released MDB base code)``.

        The MDB length wins over the PDM ``article_prefix_length`` and over any
        earlier override. Articles without a single released base are left
        unchanged here and reported UNRESOLVED by :meth:`align`.
        """
        if pdm_snapshot is None or mdb_import_snapshot is None:
            return 0

        mdb_by_code = cls._mdb_by_code(mdb_import_snapshot)
        if not mdb_by_code:
            return 0

        overrides = dict(getattr(pdm_snapshot, "base_length_overrides", {}) or {})
        applied = 0
        for article in pdm_snapshot.articles:
            code = str(article.code or "").strip()
            if not code:
                continue
            mdb_article, _reason = cls.resolve_released_base(article, mdb_by_code)
            if mdb_article is None:
                continue
            length = len(str(mdb_article.code).strip())
            if overrides.get(code) != length:
                overrides[code] = length
                applied += 1

        pdm_snapshot.base_length_overrides = overrides
        return applied

    def align(self, state: MaintenanceSnapshot) -> MaintenanceAlignment:
        """Relate each Maintenance PDM article to its released MDB base article."""
        pdm = state.pdm_snapshot
        mdb = state.mdb_import_snapshot
        if pdm is None:
            state.clear_alignment()
            state.alignment.message = "Maintenance PDM snapshot is not loaded."
            return state.alignment
        if mdb is None:
            state.clear_alignment()
            state.alignment.message = "Maintenance MDB Import Snapshot is not loaded."
            return state.alignment

        rules = self._released_base_rules(mdb)
        if not rules:
            state.clear_alignment()
            state.alignment.message = "Released MDB contains no base articles."
            return state.alignment

        mdb_by_code = self._mdb_by_code(mdb)

        relations: list[MaintenanceArticleRelation] = []
        unresolved_ids: list[str] = []
        unresolved_codes: list[str] = []

        for article in pdm.articles:
            code = str(article.code or "").strip()
            article_id = str(article.id or "").strip()
            if not code or not article_id:
                continue

            mdb_article, reason = self.resolve_released_base(article, mdb_by_code)
            if mdb_article is None:
                unresolved_ids.append(article_id)
                unresolved_codes.append(code)
                continue

            base_length = len(str(mdb_article.code).strip())
            relations.append(
                MaintenanceArticleRelation(
                    pdm_article_id=article_id,
                    pdm_article_code=code,
                    mdb_article_id=str(mdb_article.id or ""),
                    mdb_article_code=str(mdb_article.code or ""),
                    base_code=code[:base_length],
                    base_length=base_length,
                    reason=reason,
                )
            )

        state.alignment = MaintenanceAlignment(
            status="ALIGNED" if not unresolved_ids else "PARTIAL",
            base_rules=rules,
            relations=relations,
            unresolved_article_ids=unresolved_ids,
            unresolved_article_codes=unresolved_codes,
            message=(
                f"Aligned {len(relations):,} PDM article(s) to released MDB base articles."
                + (
                    f" {len(unresolved_ids):,} article(s) remain unresolved."
                    if unresolved_ids else ""
                )
            ),
        )
        return state.alignment

    @staticmethod
    def resolve_released_base(article, mdb_by_code) -> tuple[object | None, str]:
        """Return (released MDB base article or None, reason) for a PDM article.

        Candidates are the released base articles whose code begins the PDM
        article number (case-insensitive). One candidate is the base. When
        released bases nest (e.g. ``ABC`` and ``ABC123``), MDB data alone
        cannot say which one is correct, so nothing is guessed: PDM's
        ``article_prefix_length`` and ``base_length_overrides`` never decide
        the Maintenance base, and the article is left unresolved.
        """
        folded = str(article.code or "").strip().casefold()
        candidates = [mdb_by_code[base] for base in mdb_by_code if folded.startswith(base)]
        if not candidates:
            return None, "No released MDB base article begins this article number."
        if len(candidates) == 1:
            return candidates[0], "Released MDB base article."
        return None, "Ambiguous: several released MDB base articles begin this article number."

    @staticmethod
    def _mdb_by_code(mdb_import_snapshot) -> dict:
        return {
            str(article.code or "").strip().casefold(): article
            for article in mdb_import_snapshot.articles
            if str(article.code or "").strip()
        }

    @staticmethod
    def _released_base_rules(mdb_import_snapshot) -> list[MaintenanceBaseRule]:
        rules: list[MaintenanceBaseRule] = []
        seen: set[str] = set()
        for article in mdb_import_snapshot.articles:
            code = str(article.code or "").strip()
            if not code or code.casefold() in seen:
                continue
            seen.add(code.casefold())
            rules.append(MaintenanceBaseRule(base_code=code, base_length=len(code)))
        return rules
