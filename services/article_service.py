"""Article service.

Snapshot-based article operations for the Articles workspace: reading the
active snapshot's articles, managing their selection (via the shared selection
engine), and validating them. Contains no SQL and never touches the database.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.engines import statistics
from core.engines.validation import BaseValidation
from models.article import Article
from services.selectable_service import SelectableSnapshotService


@dataclass
class ArticleValidation(BaseValidation):
    """Result of validating the active snapshot's articles."""

    duplicate_codes: list[str] = field(default_factory=list)
    missing_descriptions: int = 0


class ArticleService(SelectableSnapshotService):
    """Reads and validates articles from the active snapshot."""

    def items(self) -> list[Article]:
        snapshot = self.context.active_snapshot
        if snapshot is None or not snapshot.articles:
            return []
        return list(snapshot.articles)

    def get_articles(self) -> list[Article]:
        """Return the active snapshot's articles (empty if none loaded)."""
        return self.items()

    def selected_articles(self) -> list[Article]:
        return self.selected()

    def validate(self) -> ArticleValidation:
        """Validate the active snapshot's articles (in-memory checks only)."""
        articles = self.get_articles()
        result = ArticleValidation(total=len(articles))

        if not articles:
            result.warnings.append("No articles loaded.")
            return result

        result.duplicate_codes = statistics.duplicate_keys(articles, lambda a: a.code)

        for article in articles:
            issues: list[str] = []
            if article.code in result.duplicate_codes:
                issues.append("Duplicate code")
            if not (article.description or "").strip():
                # Informational only: a missing PDM description is normal and
                # must not mark the article (or its selection) as an issue.
                result.missing_descriptions += 1
            if issues:
                result.issues_by_id[str(article.id)] = issues

        result.selected = sum(1 for a in articles if a.selected)
        result.invalid_selections = sum(
            1 for a in articles if a.selected and str(a.id) in result.issues_by_id
        )

        if result.duplicate_codes:
            result.warnings.append(
                f"{len(result.duplicate_codes)} duplicate article code(s)."
            )
        if result.invalid_selections:
            result.warnings.append(
                f"{result.invalid_selections} selected article(s) have issues."
            )
        return result
