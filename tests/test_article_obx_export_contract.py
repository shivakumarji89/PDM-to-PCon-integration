"""Article OBX export contract: what the Validator and pCon-style parsers read back from the file.

Root causes covered (found by comparing a Workbench export with a pCon export):
* the Validator reads only ``itemPrice type=sale pd=1``; the export used to write one ``purchase`` row,
* the article label sat *inside* ``<artNr type="final">``, corrupting the SKU for parsers that read up to
  the next closing tag.

The Desktop files are comparison evidence only and the tests are skipped when they are absent.
"""
from __future__ import annotations

import os
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from services.article_obx.article_obx_models import (
    ArticleConfigurationValue, ArticleObxRow, ArticlePermutation, ArticlePrice,
)
from services.article_obx.article_obx_service import FINAL_OMIT, ArticleObxService
from services.obx_validation_service import ObxValidationService
from services.sif_validation_service import SifValidationService

DESKTOP = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
REFERENCE = DESKTOP / "1_Dalby_Circular_Table_Euro(4).obx"

FINAL = "NODLE630 NC WSL OAK BRC"
LABEL = "Dalby 6-leg Bar Height Table / 3200mm"


def _row(price: float = 6300.0, label: str = LABEL) -> ArticleObxRow:
    values = tuple(
        ArticleConfigurationValue(kind="property", entity_id=f"DALBY_OPT:{n}", value_id=f"DALBY_OPT:{n}:{c}",
                                  name=n, value=c, code=c, display_order=i)
        for i, (n, c) in enumerate([("Frame_Finish", "OAK"), ("Top_Finish", "BRC")])
    )
    permutation = ArticlePermutation(
        article_id="NODLE630", product_id="", base_code="NODLE630", final_article=FINAL, name=label,
        description=label, properties=values, series_id="DALBY",
        ofml_varcode="DALBY_OPT.Frame_Finish=OAK;DALBY_OPT.Top_Finish=BRC",
    )
    return ArticleObxRow(permutation, ArticlePrice("NODLE630", FINAL, "EUR", "2026-11-04", 1, total_price=price))


def _render(*rows: ArticleObxRow, **kwargs) -> str:
    return ArticleObxService(None).render(rows or (_row(),), manufacturer_id="HM", series_id="DALBY", **kwargs)


def _article(xml: str) -> ET.Element:
    return ET.fromstring(xml).find("./items/bskArticle")


class PriceRowTests(unittest.TestCase):
    def test_price_rows_match_the_pcon_set_with_one_amount(self):
        prices = _article(_render()).findall("itemPrice")
        self.assertEqual([(p.get("type"), p.get("pd")) for p in prices],
                         [("purchase", "1"), ("purchase", None), ("sale", "1"), ("sale", None)])
        self.assertEqual({(p.get("value"), p.get("currency")) for p in prices}, {("6300.00", "EUR")})

    def test_validator_reads_price_currency_and_date(self):
        currency, lines = ObxValidationService(None).parse_obx(_render())
        self.assertEqual(currency, "EUR")
        self.assertEqual([(l.final_article, l.currency, l.obx_price, l.source_date) for l in lines],
                         [(FINAL, "EUR", 6300.0, "2026-11-04")])


class FinalArticleTests(unittest.TestCase):
    def test_final_article_is_plain_text(self):
        final = _article(_render()).find("artNr[@type='final']")
        self.assertEqual((final.text, len(final)), (FINAL, 0))

    def test_label_moves_to_description_elements(self):
        descriptions = _article(_render()).findall("description")
        self.assertEqual([(d.get("type"), d.get("default"), d.findtext("text")) for d in descriptions],
                         [("short", "0", LABEL), ("long", "1", LABEL)])
        self.assertEqual(descriptions[0].find("text").get("lang"), "en")

    def test_no_description_without_a_label(self):
        self.assertEqual(_article(_render(_row(label=""))).findall("description"), [])

    def test_legacy_sif_parser_reads_the_clean_sku(self):
        _, lines = SifValidationService.__new__(SifValidationService).parse_obx(_render())
        self.assertEqual([(l.base, l.pl) for l in lines], [(FINAL, 6300.0)])

    def test_omit_mode_keeps_description_and_drops_final(self):
        article = _article(_render(final_article_mode=FINAL_OMIT))
        self.assertEqual([a.get("type") for a in article.findall("artNr")], ["base", "ofmlvarcode"])
        self.assertEqual(len(article.findall("description")), 2)

    def test_element_order_follows_pcon(self):
        tags = [c.tag for c in _article(_render())]
        self.assertEqual(tags[:2], ["manufacturer", "series"])
        self.assertLess(tags.index("artNr"), tags.index("description"))
        self.assertLess(tags.index("description"), tags.index("itemPrice"))
        self.assertLess(tags.index("itemPrice"), tags.index("priceDate"))


@unittest.skipUnless(REFERENCE.is_file(), f"pCon reference OBX not found: {REFERENCE}")
class PcOnReferenceComparisonTests(unittest.TestCase):
    """Compare structure against the pCon export. Metadata Workbench cannot produce is not asserted."""

    @classmethod
    def setUpClass(cls):
        cls.reference = ET.parse(REFERENCE).getroot().findall("./items/bskArticle")[0]

    def test_price_row_signature_equals_pcon(self):
        def signature(article):
            return [(p.get("type"), p.get("pd")) for p in article.findall("itemPrice")]
        self.assertEqual(signature(_article(_render())), signature(self.reference))

    def test_description_signature_equals_pcon(self):
        def signature(article):
            return [(d.get("type"), d.get("default")) for d in article.findall("description")][:2]
        self.assertEqual(signature(_article(_render())), [s for s in signature(self.reference) if s[0] != "features"])

    def test_pcon_final_article_is_plain_text(self):
        self.assertEqual(len(self.reference.find("artNr[@type='final']")), 0)

    def test_runtime_metadata_is_not_fabricated(self):
        article = _article(_render())
        for tag in ("geometryChecksum", "addStateCode", "appData", "metaType", "catalogInfo", "fields"):
            self.assertIsNone(article.find(tag), tag)
        # basketId is identity Basket requires, not pCon runtime metadata: it is generated, never copied.
        self.assertNotEqual(article.get("basketId"), self.reference.get("basketId"))


if __name__ == "__main__":
    unittest.main()
