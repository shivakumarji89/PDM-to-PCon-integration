"""Basket paste contract: the Testsuite-proven envelope around Workbench's condition-engine output.

Reference: the MK OFML Testsuite's ``build_obx`` output (``Docs/Tool generated obx cloud.obx``). Only its
structure is compared; its basketId, session id and article data are never reused.
"""
from __future__ import annotations

import os
import re
import unittest
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

from services.article_obx.basket_contract import (
    BasketPayloadError, basket_problems, prepare_basket_payload,
)
from services.article_obx.ocd_repository_obx import build_rows
from services.article_obx.article_obx_service import ArticleObxService
from services.ocd_engine.generator import GeneratedSku
from services.obx_validation_service import ObxValidationService

TESTSUITE_REFERENCE = (Path(os.environ.get("USERPROFILE", "")) / "Desktop" / "MK_OFML_Testsuite"
                       / "Docs" / "Tool generated obx cloud.obx")


def _sku(index: int, final: str, price: str = "100", currency: str = "EUR") -> GeneratedSku:
    from decimal import Decimal
    return GeneratedSku(
        index=index, base_article="NODLE100", series_id="DALBY", final_article=final, variant_code="",
        ofml_varcode=f"DALBY_OPT.Frame_Finish={final.split()[1]}", configuration_text="", label="Dalby table / 650mm",
        values=(("DALBY_OPT", "Frame_Finish", final.split()[1], final.split()[1]),),
        price=Decimal(price), currency=currency,
    )


def _xml(*finals: str) -> str:
    skus = [_sku(i, f) for i, f in enumerate(finals or ("NODLE100 OAK", "NODLE100 BRC"))]
    return ArticleObxService(None).render(build_rows(skus, "2026-11-04"), manufacturer_id="HM", series_id="DALBY")


class EnvelopeTests(unittest.TestCase):
    def test_every_article_has_a_unique_uuid_basket_id(self):
        root = ET.fromstring(_xml("NODLE100 OAK", "NODLE100 BRC", "NODLE100 WSE"))
        ids = [a.get("basketId") for a in root.findall("./items/bskArticle")]
        self.assertEqual(len(set(ids)), 3)
        for value in ids:
            self.assertEqual(str(uuid.UUID(value)), value)

    def test_ids_are_fresh_on_every_export(self):
        first = {a.get("basketId") for a in ET.fromstring(_xml()).findall("./items/bskArticle")}
        second = {a.get("basketId") for a in ET.fromstring(_xml()).findall("./items/bskArticle")}
        self.assertFalse(first & second)

    def test_calculation_changes_point_at_each_article(self):
        root = ET.fromstring(_xml())
        ids = [a.get("basketId") for a in root.findall("./items/bskArticle")]
        changes = root.find("docCalculationChanges")
        self.assertEqual(changes.get("ppName"), "STDB2B_WBK")
        self.assertEqual([c.get("id") for c in changes.findall("itemCalculationChanges")], ids)

    def test_top_level_order_matches_the_testsuite(self):
        self.assertEqual([c.tag for c in ET.fromstring(_xml())],
                         ["state", "versionInfo", "items", "docCalculationChanges"])
        self.assertTrue(ET.fromstring(_xml()).find("state").get("sessionId"))

    @unittest.skipUnless(TESTSUITE_REFERENCE.is_file(), "Testsuite reference OBX not found")
    def test_structure_matches_the_testsuite_reference_without_reusing_its_ids(self):
        reference = ET.parse(TESTSUITE_REFERENCE).getroot()
        generated = ET.fromstring(_xml())
        self.assertEqual([c.tag for c in generated], [c.tag for c in reference])
        self.assertEqual(generated.find("versionInfo").attrib, reference.find("versionInfo").attrib)
        ref_article = reference.find("./items/bskArticle")
        article = generated.find("./items/bskArticle")
        self.assertEqual(article.get("itemType"), ref_article.get("itemType"))
        self.assertNotEqual(article.get("basketId"), ref_article.get("basketId"))
        self.assertNotEqual(generated.find("state").get("sessionId"), reference.find("state").get("sessionId"))


class PipelineTests(unittest.TestCase):
    """GeneratedSku (condition engine output) -> OBX: SKU, price and currency survive serialization."""

    def test_final_article_holds_only_the_sku(self):
        article = ET.fromstring(_xml("NODLE100 OAK")).find("./items/bskArticle")
        final = article.find("artNr[@type='final']")
        self.assertEqual((final.text, len(final)), ("NODLE100 OAK", 0))
        self.assertNotIn("Dalby", final.text)

    def test_varcode_and_base_come_from_the_generated_sku(self):
        article = ET.fromstring(_xml("NODLE100 OAK")).find("./items/bskArticle")
        self.assertEqual(article.findtext("artNr[@type='base']"), "NODLE100")
        self.assertEqual(article.findtext("artNr[@type='ofmlvarcode']"), "DALBY_OPT.Frame_Finish=OAK")

    def test_price_and_currency_are_serialized_and_read_back_by_the_validator(self):
        rows = build_rows([_sku(0, "NODLE100 OAK", "1243", "GBP")], "2026-11-04")
        xml = ArticleObxService(None).render(rows, manufacturer_id="HM", series_id="DALBY")
        self.assertTrue(all(p.get("currency") == "GBP" and p.get("value") == "1243.00"
                            for p in ET.fromstring(xml).iter("itemPrice")))
        currency, lines = ObxValidationService(None).parse_obx(xml)
        self.assertEqual((currency, [(l.final_article, l.obx_price) for l in lines]), ("GBP", [("NODLE100 OAK", 1243.0)]))

    def test_unpriced_skus_are_not_exported(self):
        unpriced = _sku(0, "NODLE100 OAK")
        object.__setattr__(unpriced, "price", None)
        self.assertEqual(build_rows([unpriced], "2026-11-04"), [])


class PayloadTests(unittest.TestCase):
    def test_a_generated_obx_is_accepted(self):
        payload = prepare_basket_payload(_xml())
        self.assertEqual(payload.article_count, 2)
        self.assertEqual(len(set(payload.basket_ids)), 2)
        self.assertEqual(payload.data, payload.xml.encode("utf-8"))

    def test_missing_basket_id_reproduces_the_basket_error(self):
        broken = re.sub(r' basketId="[^"]+"', "", _xml(), count=1)
        with self.assertRaises(BasketPayloadError) as caught:
            prepare_basket_payload(broken)
        self.assertTrue(any("attribute 'basketId' is missing or empty" in p for p in caught.exception.problems))

    def test_empty_basket_id_is_rejected(self):
        problems = basket_problems(re.sub(r'basketId="[^"]+"', 'basketId=""', _xml(), count=1))
        self.assertTrue(any("missing or empty" in p for p in problems))

    def test_duplicate_basket_ids_are_rejected(self):
        xml = _xml()
        ids = re.findall(r'<bskArticle basketId="([^"]+)"', xml)
        self.assertTrue(any("is used by 2 articles" in p for p in basket_problems(xml.replace(ids[1], ids[0]))))

    def test_calculation_changes_must_match_the_articles(self):
        xml = re.sub(r"<docCalculationChanges.*</docCalculationChanges>", "", _xml(), flags=re.DOTALL)
        self.assertTrue(any("docCalculationChanges" in p for p in basket_problems(xml)))

    def test_malformed_and_empty_files_report_clearly(self):
        self.assertIn("not well-formed", basket_problems("<cutBuffer>")[0])
        self.assertIn("no <bskArticle>", " ".join(basket_problems("<cutBuffer><items/></cutBuffer>")))


if __name__ == "__main__":
    unittest.main()
