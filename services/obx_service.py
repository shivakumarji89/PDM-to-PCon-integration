"""OBX basket generator.

Produces pCon-compatible ``.obx`` XML ``<cutBuffer>`` documents from the active
snapshot.  One ``<bskArticle>`` is emitted per article; features are the
property values that article carries (from ``article_property_value_ids``);
prices come from ``snapshot.price_records`` (level 'B'); the OFML variant code
is ``<SERIES>_OPT.<PConProp>=<code>;…``.

The format is reverse-engineered from PDM ``CADMaintenance.ConvertOBXToSIF``
and the observed ``Tool generated obx cloud.obx`` sample (EAI-Server
``bskXmlVersion='1.8.10'``).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from services.base_service import BaseService
from services.xocd_export_service import XocdExportService

if TYPE_CHECKING:
    from models.snapshot import Snapshot


#: Marker written into ``<artNr type='final'>`` for snapper-generated articles.
#: pCon overwrites ``final`` with the resolved number on Update, so a surviving
#: sentinel identifies an unresolved (invalid) configuration for ``clean_obx``.
OBX_SENTINEL = "__SNAPPER_RAW__"


# Features suppressed from OBX output (structural/parametric, not config options).
# Mirrors ``GetOBXFeatureExclusions`` default branch in CADMaintenance.cs.
_DEFAULT_EXCLUSIONS: set[str] = {
    "Type", "Chair_Type", "Stool_Type", "Sideboard_Size",
    "Work_Top_Shape", "Work_Top_Size",
    "LEADTIME", "ARTICLECODE",
}


@dataclass
class OBXFeature:
    name: str           # pCon property id (e.g. 'Base_Finish')
    value: str          # value code (e.g. 'R00')
    flags: str = "1"    # '1' = include in description; '0' = hidden
    descr_field0: str = ""   # property display name
    descr_field1: str = ""   # value display name


@dataclass
class OBXArticle:
    base_code: str              # artNr type='base'
    final_code: str             # artNr type='final'
    ofml_varcode: str           # artNr type='ofmlvarcode'
    manufacturer_id: str = "HM"
    series_id: str = ""
    description: str = ""
    quantity: int = 1
    price: float = 0.0
    currency: str = "EUR"
    features: list[OBXFeature] = field(default_factory=list)


@dataclass
class OBXResult:
    articles: list[OBXArticle] = field(default_factory=list)
    xml: str = ""
    warnings: list[str] = field(default_factory=list)


class OBXService(BaseService):
    """Generate OBX basket XML from the active snapshot."""

    # pCon property-name normalisation: spaces → underscores, strip qualifier.
    @staticmethod
    def _pcon_name(prop_name: str) -> str:
        name = prop_name
        paren = name.find(" (")
        if paren > -1:
            name = name[:paren]
        return name.replace(" ", "_")

    def generate(
        self,
        manufacturer_id: str = "HM",
        series_id: str | None = None,
        ofml_class_suffix: str = "_OPT",
        exclude_features: set[str] | None = None,
    ) -> OBXResult:
        """Build one OBXArticle per snapshot article and render to XML."""
        result = OBXResult()
        snapshot: Snapshot | None = self.context.active_snapshot
        if snapshot is None or snapshot.product is None:
            result.warnings.append("No active snapshot.")
            return result

        product = snapshot.product
        # Sales product line = the commercial series (e.g. 'AERON'), same source as
        # the XOCD Program_ID - NOT the specific product code.
        sid = series_id or XocdExportService.series_id(product)
        ofml_class = sid + ofml_class_suffix
        exclusions = exclude_features if exclude_features is not None else _DEFAULT_EXCLUSIONS

        # Index property values by id for fast lookup.
        pv_by_id: dict[str, object] = {}
        for pv in snapshot.property_values:
            if pv.id:
                pv_by_id[pv.id] = pv

        # Index properties by id.
        prop_by_id: dict[str, object] = {}
        for p in snapshot.properties:
            if p.id:
                prop_by_id[p.id] = p

        # Index level-B prices by article base code.
        price_by_code: dict[str, float] = {}
        currency = "EUR"
        for pr in snapshot.price_records:
            if pr.level == "B" and pr.article_code:
                price_by_code[pr.article_code] = pr.value
                if pr.currency:
                    currency = pr.currency

        for article in snapshot.articles:
            pv_ids = snapshot.article_property_value_ids.get(article.id or "", [])
            if not pv_ids and article.id:
                # fall back to the product-level value set
                pv_ids = snapshot.product_property_value_ids.get(article.id, [])

            features: list[OBXFeature] = []
            varcode_parts: list[str] = []

            for vid in pv_ids:
                pv = pv_by_id.get(vid)
                if pv is None:
                    continue
                prop = prop_by_id.get(pv.property_id or "")
                if prop is None:
                    continue

                pcon_name = self._pcon_name(prop.name)
                if pcon_name in exclusions:
                    continue

                code = pv.code or pv.value
                features.append(OBXFeature(
                    name=pcon_name,
                    value=code,
                    flags="1",
                    descr_field0=prop.name,
                    descr_field1=pv.value,
                ))
                varcode_parts.append(f"{ofml_class}.{pcon_name}={code}")

            ofml_varcode = ";".join(varcode_parts)
            # Final article code = base + variant code (PDM convention: space-separated).
            final_code = (article.code + " " + ofml_varcode).strip() if ofml_varcode else article.code

            obx_article = OBXArticle(
                base_code=article.code,
                final_code=final_code,
                ofml_varcode=ofml_varcode,
                manufacturer_id=manufacturer_id,
                series_id=sid,
                description=article.name,
                quantity=1,
                price=price_by_code.get(article.code, 0.0),
                currency=currency,
                features=features,
            )
            result.articles.append(obx_article)

        if not result.articles:
            result.warnings.append("No articles found in snapshot.")

        result.xml = self._render_xml(result.articles)
        return result

    # ------------------------------------------------------------------
    def _render_xml(self, articles: list[OBXArticle]) -> str:
        root = ET.Element("cutBuffer")

        vi = ET.SubElement(root, "versionInfo")
        vi.set("vendorKey", "EasternGraphics")
        vi.set("appKey", "EAI-Server")
        vi.set("appVersion", "4.18.3")
        vi.set("bskXmlVersion", "1.8.10")

        items = ET.SubElement(root, "items")

        for art in articles:
            bsk = ET.SubElement(items, "bskArticle")
            bsk.set("itemType", "BasketAggregate")
            bsk.set("updateState", "Migratable")

            mfr = ET.SubElement(bsk, "manufacturer")
            mfr.set("id", art.manufacturer_id)

            series = ET.SubElement(bsk, "series")
            series.set("id", art.series_id)

            an_base = ET.SubElement(bsk, "artNr")
            an_base.set("type", "base")
            an_base.text = art.base_code

            an_final = ET.SubElement(bsk, "artNr")
            an_final.set("type", "final")
            an_final.text = art.final_code
            if art.description:
                txt = ET.SubElement(an_final, "text")
                txt.set("lang", "en")
                txt.text = art.description

            an_varcode = ET.SubElement(bsk, "artNr")
            an_varcode.set("type", "ofmlvarcode")
            an_varcode.text = art.ofml_varcode

            if art.price:
                ip = ET.SubElement(bsk, "itemPrice")
                ip.set("type", "purchase")
                ip.set("value", str(art.price))

            qty = ET.SubElement(bsk, "quantity")
            qty.set("count", str(art.quantity))

            for feat in art.features:
                f = ET.SubElement(bsk, "feature")
                f.set("name", feat.name)
                f.set("value", feat.value)
                f.set("flags", feat.flags)
                if feat.descr_field0:
                    d0 = ET.SubElement(f, "descrField0")
                    d0.text = feat.descr_field0
                if feat.descr_field1:
                    d1 = ET.SubElement(f, "descrField1")
                    d1.text = feat.descr_field1

            ET.SubElement(bsk, "itemPriceComponents").set("type", "purchase")
            ET.SubElement(bsk, "itemPriceComponents").set("type", "sale")

            pdi = ET.SubElement(bsk, "pdInfo")
            pdi.set("pdbType", "undef")
            pdi.set("pkgName", "")
            pdi.set("manufacturerId", art.manufacturer_id)
            pdi.set("seriesId", art.series_id)
            pdi.set("progId", "")

        ET.indent(root, space="  ")
        return '<?xml version=\'1.0\' encoding=\'utf-8\'?>\n' + ET.tostring(root, encoding="unicode")

    def write(self, path: str, **generate_kwargs) -> OBXResult:
        """Generate and write the OBX file to *path*. Returns the result."""
        result = self.generate(**generate_kwargs)
        if result.xml:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(result.xml)
        return result

    # ------------------------------------------------------------------
    @staticmethod
    def clean_obx(xml: str) -> tuple[str, int, int]:
        """Drop unresolved (sentinel-bearing) articles from a pCon-updated OBX.

        After importing a snapper OBX and running pCon's *Update*, valid articles
        have their ``final`` number filled in; invalid ones still carry
        :data:`OBX_SENTINEL`. Returns ``(cleaned_xml, kept, removed)``.
        """
        root = ET.fromstring(xml)
        items = root.find("items")
        if items is None:
            return xml, 0, 0
        kept = removed = 0
        for bsk in list(items.findall("bskArticle")):
            final = next(
                (a for a in bsk.findall("artNr") if a.get("type") == "final"), None
            )
            text = (final.text or "") if final is not None else ""
            if OBX_SENTINEL in text:
                items.remove(bsk)
                removed += 1
            else:
                kept += 1
        ET.indent(root, space="  ")
        cleaned = "<?xml version='1.0' encoding='utf-8'?>\n" + ET.tostring(
            root, encoding="unicode"
        )
        return cleaned, kept, removed
