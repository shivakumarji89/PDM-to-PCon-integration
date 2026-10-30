"""Catalogue and article discovery through the pCon.planner plugin.

Maps to SDK calls executed inside pCon.planner:

* ``Articles.Package.GetAll()`` for manufacturers / programs,
* ``Articles.Catalog.Get(package).GetAllItems()`` filtered to
  ``CatalogItemType.Article`` for base articles,
* ``IArticleManager.InsertArticle`` + ``InstantiateArticle`` +
  ``IPropertyProvider.GetProperties()`` for property discovery.
"""
from __future__ import annotations

from services.pcon_sdk_obx import protocol
from services.pcon_sdk_obx.bridge import PconPluginBridge
from services.pcon_sdk_obx.protocol import (
    ArticleInfo,
    ArticleProperty,
    CatalogArticle,
    CatalogPackage,
    PropertyAssignment,
)


class PconCatalogService:
    """Read-only catalogue access; every call is one plugin round trip."""

    def __init__(self, bridge: PconPluginBridge) -> None:
        self._bridge = bridge

    def list_packages(self) -> list[CatalogPackage]:
        data = self._bridge.send(protocol.KIND_CATALOG)
        packages = [CatalogPackage.from_dict(p) for p in data.get("packages", []) or []]
        packages.sort(key=lambda p: (p.manufacturer_name.lower(), p.manufacturer_id, p.label.lower()))
        return packages

    @staticmethod
    def manufacturers(packages: list[CatalogPackage]) -> list[tuple[str, str]]:
        """Distinct ``(manufacturer_id, manufacturer_name)`` pairs in display order."""
        seen: dict[str, str] = {}
        for package in packages:
            if package.manufacturer_id and package.manufacturer_id not in seen:
                seen[package.manufacturer_id] = package.manufacturer_name or package.manufacturer_id
        return sorted(seen.items(), key=lambda item: item[1].lower())

    @staticmethod
    def programs_for(packages: list[CatalogPackage], manufacturer_id: str) -> list[CatalogPackage]:
        return [p for p in packages if p.manufacturer_id == manufacturer_id and p.has_catalog]

    def list_articles(self, package: CatalogPackage) -> list[CatalogArticle]:
        data = self._bridge.send(protocol.KIND_ARTICLES, {"packageName": package.package_name})
        articles = [CatalogArticle.from_dict(a) for a in data.get("articles", []) or []]
        # Keep one row per (article number, variant code); catalogue trees can
        # reference the same article from several folders.
        unique: dict[tuple[str, str], CatalogArticle] = {}
        for article in articles:
            if not article.article_number:
                continue
            unique.setdefault((article.article_number, article.variant_code), article)
        return sorted(unique.values(), key=lambda a: (a.article_number, a.variant_code))

    def describe_article(self, package: CatalogPackage, article: CatalogArticle,
                         series_id: str = "",
                         assignments: tuple[PropertyAssignment, ...] = ()
                         ) -> tuple[ArticleInfo, list[ArticleProperty]]:
        """Instantiate one article in pCon and return its live property list.

        ``assignments`` are applied in order before the properties are read,
        so callers can inspect how dependent properties react to a selection.
        """
        data = self._bridge.send(protocol.KIND_PROPERTIES, {
            "manufacturerId": package.manufacturer_id,
            "seriesId": series_id,
            "catalogPackage": package.package_name,
            "articlePackage": article.package_name,
            "articleNumber": article.article_number,
            "variantCode": article.variant_code,
            "assignments": [a.to_dict() for a in assignments],
        })
        info = ArticleInfo.from_dict(data.get("article", {}) or {})
        properties = [ArticleProperty.from_dict(p) for p in data.get("properties", []) or []]
        return info, properties


__all__ = ["PconCatalogService"]
