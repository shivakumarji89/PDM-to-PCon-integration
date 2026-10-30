"""Orchestrate repository article permutation, pricing, and OBX generation."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from services.base_service import BaseService
from services.ocd_engine import diagnostics as dg
from services.article_obx.article_obx_models import ArticleObxResult, ArticleObxRow
from services.article_obx.article_permutation_service import ArticlePermutationService
from services.article_obx.article_price_service import ArticlePriceRequest, ArticlePriceService
from services.obx_service import _DEFAULT_EXCLUSIONS, OBX_SENTINEL
from services.xocd_export_service import XocdExportService


#: How ``<artNr type="final">`` is written (see ``generate``).
FINAL_PREDICTED = "predicted"
FINAL_OMIT = "omit"
FINAL_SENTINEL = "sentinel"


class ArticleObxService(BaseService):
    """Generate an OBX from repository Snapshot articles at a specified price date.

    ``final_article_mode`` controls ``artNr type="final"``:

    * ``predicted`` (default, unchanged behaviour): the final number computed by
      the CodeScheme engine. pCon resolves the real number itself on *Update*.
    * ``omit``: input style - only ``base`` and ``ofmlvarcode``, as the pCon
      input OBX files observed in evidence carry.
    * ``sentinel``: the Snapper marker, so ``OBXService.clean_obx`` can drop
      configurations pCon could not resolve.

    ``artNr type="varcode"`` is never written: it is pCon's resolved output.
    """

    def generate(self, currency: str, effective_date: str, site_id: int = 1,
                 manufacturer_id: str = "HM", series_id: str | None = None,
                 ofml_class_suffix: str = "_OPT",
                 exclude_features: set[str] | None = None,
                 final_article_mode: str = FINAL_PREDICTED) -> ArticleObxResult:
        if final_article_mode not in {FINAL_PREDICTED, FINAL_OMIT, FINAL_SENTINEL}:
            raise ValueError(f"unknown final_article_mode {final_article_mode!r}")
        # Article OBX is repository-driven. Never fall back to a PDM snapshot.
        snapshot = self.context.qa_snapshot
        result = ArticleObxResult()
        if snapshot is None or snapshot.product is None:
            result.warnings.append("No active snapshot.")
            return result

        permutation_service = ArticlePermutationService(self.context)
        permutations = permutation_service.build(snapshot)
        for diagnostic in (permutation_service.last_diagnostics or ()):
            if diagnostic.severity is not dg.Severity.INFO:
                result.warnings.append(str(diagnostic))
        prices = ArticlePriceService(self.context).resolve(
            permutations,
            ArticlePriceRequest(currency=currency, effective_date=effective_date, site_id=site_id),
        )

        # Prices are resolved per permutation and returned in the same order. (They
        # were once keyed by article_id, which gave every configuration of an
        # article the price of its last one.)
        for permutation, price in zip(permutations, prices):
            if price is None or price.total_price is None:
                result.warnings.append(
                    f"{permutation.final_article}: "
                    f"{price.unresolved_reason if price else 'price not resolved'}"
                )
                continue
            result.rows.append(ArticleObxRow(permutation=permutation, price=price))

        exclusions = set(exclude_features) if exclude_features is not None else set(_DEFAULT_EXCLUSIONS)
        sid = series_id or XocdExportService.series_id(snapshot.product)
        result.xml = self._render_xml(
            result.rows, manufacturer_id=manufacturer_id, series_id=sid,
            ofml_class_suffix=ofml_class_suffix, exclusions=exclusions,
            final_mode=final_article_mode,
        )
        return result

    @staticmethod
    def _pcon_name(name: str) -> str:
        qualifier = name.find(" (")
        if qualifier > -1:
            name = name[:qualifier]
        return name.replace(" ", "_")

    def _render_xml(self, rows, *, manufacturer_id, series_id, ofml_class_suffix, exclusions,
                    final_mode: str = FINAL_PREDICTED) -> str:
        root = ET.Element("cutBuffer")
        version = ET.SubElement(root, "versionInfo")
        version.attrib.update({
            "vendorKey": "EasternGraphics", "appKey": "EAI-Server",
            "appVersion": "4.18.3", "bskXmlVersion": "1.8.10",
        })
        items = ET.SubElement(root, "items")

        for row in rows:
            p = row.permutation
            price = row.price
            bsk = ET.SubElement(items, "bskArticle", {"itemType": "BasketAggregate", "updateState": "Migratable"})
            ET.SubElement(bsk, "manufacturer", {"id": manufacturer_id})
            ET.SubElement(bsk, "series", {"id": series_id})

            base = ET.SubElement(bsk, "artNr", {"type": "base"})
            base.text = p.base_code
            if final_mode != FINAL_OMIT:
                final = ET.SubElement(bsk, "artNr", {"type": "final"})
                final.text = OBX_SENTINEL if final_mode == FINAL_SENTINEL else p.final_article
                if p.description or p.name:
                    txt = ET.SubElement(final, "text", {"lang": "en"})
                    txt.text = p.description or p.name

            varcode = ET.SubElement(bsk, "artNr", {"type": "ofmlvarcode"})
            varcode.text = self._varcode(p, series_id, ofml_class_suffix, exclusions)

            ET.SubElement(bsk, "itemPrice", {
                "type": "purchase", "value": f"{price.total_price:.2f}", "currency": price.currency,
            })
            ET.SubElement(bsk, "priceDate", {"value": price.effective_date})
            ET.SubElement(bsk, "quantity", {"count": str(p.quantity)})

            for value in p.all_values:
                feature_name = self._pcon_name(value.name)
                if feature_name in exclusions:
                    continue
                feature = ET.SubElement(bsk, "feature", {
                    "name": feature_name, "value": value.code or value.value, "flags": "1",
                })
                ET.SubElement(feature, "descrField0").text = value.name
                ET.SubElement(feature, "descrField1").text = value.value

            ET.SubElement(bsk, "itemPriceComponents", {"type": "purchase"})
            ET.SubElement(bsk, "itemPriceComponents", {"type": "sale"})
            ET.SubElement(bsk, "pdInfo", {
                "pdbType": "undef", "pkgName": "", "manufacturerId": manufacturer_id,
                "seriesId": series_id, "progId": "",
            })

        ET.indent(root, space="  ")
        return "<?xml version='1.0' encoding='utf-8'?>\n" + ET.tostring(root, encoding="unicode")

    def _varcode(self, permutation, series_id, suffix, exclusions):
        parts = []
        ofml_class = series_id + suffix
        for value in permutation.all_values:
            name = self._pcon_name(value.name)
            if name in exclusions:
                continue
            code = value.code or value.value
            if code:
                parts.append(f"{ofml_class}.{name}={code}")
        return ";".join(parts)

    @staticmethod
    def write(path: str, result: ArticleObxResult) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(result.xml)
