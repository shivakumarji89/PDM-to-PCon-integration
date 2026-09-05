"""Workspace article loading service.

Loads existing-series article data directly from the repository OCD into the
working Snapshot. This path is deliberately independent from PDM.
"""
from __future__ import annotations

from pathlib import Path

from models.article import Article
from models.product import Product
from models.snapshot import Snapshot
from services.base_service import BaseService


class WorkspaceArticleService(BaseService):
    """Create an Article workflow snapshot from an existing repository OCD."""

    _OCD_FILE = "pcr_data_com_ocd.mdb"

    def load_active_repository(self) -> Snapshot | None:
        active = self.context.repository_context_service.active_context
        if active is None:
            return None
        return self.load_repository(
            active.repository_path, active.series_name, active.category
        )

    def load_repository(
        self,
        repository_path: str | Path,
        series_name: str = "",
        category: str = "",
    ) -> Snapshot | None:
        folder = Path(repository_path)
        mdb_path = folder / self._OCD_FILE
        if not mdb_path.is_file():
            return None

        rows = self.context.mdb_service.read_table(
            mdb_path,
            "SELECT com_ArticleID, com_ArticleCode FROM tCOMd_Article "
            "WHERE com_ArticleCode IS NOT NULL",
        )

        seen: set[str] = set()
        articles: list[Article] = []
        for row in rows:
            code = str(row.get("com_ArticleCode") or "").strip()
            if not code or code in seen:
                continue
            seen.add(code)
            article_id = str(row.get("com_ArticleID") or code)
            articles.append(
                Article(
                    id=article_id,
                    product_id=str(folder),
                    code=code,
                    source="repository_ocd",
                    selected=True,
                )
            )

        product = Product(
            id=str(folder),
            code=series_name or folder.name,
            name=series_name or folder.name,
            category=category,
            articles=articles,
        )
        snapshot = self.context.snapshot_service.create_snapshot(product)
        # Replaces whatever repository/series was previously active: create_snapshot
        # always installs a brand new Snapshot on the shared SnapshotManager. `id`
        # must be set (mirrors the PDM path, e.g. services/pdm_service.py) so
        # snapshot-keyed UI caches (e.g. ArticlesPage._snapshot_key) detect the
        # change and drop stale per-snapshot state instead of leaking it across
        # repositories.
        snapshot.id = product.id
        snapshot.articles = articles
        snapshot.metadata.source = "repository_ocd"
        snapshot.metadata.product_code = product.code
        snapshot.metadata.notes = f"Loaded directly from {mdb_path}"

        # Same central pipeline PDM loading uses for base article / base length /
        # article-set grouping (services/engineering/engineering_reduction_service.py)
        # and for engineering initialization - no repository-specific duplicate.
        self.context.engineering_reduction_service.materialize_article_sets(snapshot)
        self.context.engineering_initialization_service.initialize(snapshot)
        return snapshot
