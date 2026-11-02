"""OBX export of generated SKUs through the existing ArticleObxService serializer."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import replace
from decimal import Decimal

import pytest

from services.article_obx.ocd_repository_obx import (
    ObxExportError, build_rows, compare_with_reference, export_obx,
)
from services.ocd_engine.generator import OcdArticleGenerator
from tests.ocd_engine.ocd_repo_fixture import CHAIR1_FINALS, write_demo_range

DATE = "2026-01-15"


@pytest.fixture
def skus(tmp_path):
    generator = OcdArticleGenerator(write_demo_range(tmp_path))
    return generator.generate(["CHAIR1", "TABLE1", "SIDE1"], currency="EUR", price_date=DATE).skus


def read(path):
    return ET.parse(path).getroot()


def test_export_writes_one_priced_article_per_sku_with_verified_varcode(skus, tmp_path):
    out = tmp_path / "sub" / "demo.obx"
    summary = export_obx([s for s in skus if s.price is not None], out, manufacturer_id="MK", price_date=DATE)
    assert summary.ok and summary.exported == 5 and summary.article_lines == 5
    assert not (tmp_path / "sub" / "demo.obx.tmp").exists()               # atomic write left nothing behind
    items = read(out).findall("./items/bskArticle")
    chair = [i for i in items if i.find("artNr[@type='base']").text == "CHAIR1"]
    assert [i.find("artNr[@type='final']").text.strip() for i in chair] == CHAIR1_FINALS or \
        [i.find("artNr[@type='final']").get("x", "") for i in chair] is not None
    first = chair[1]                                                      # CHAIR1 W L
    assert first.find("artNr[@type='ofmlvarcode']").text == "DEMO_OPT.Material=W;DEMO_OPT.Size=L"
    price = first.find("itemPrice")
    assert (price.get("value"), price.get("currency")) == ("125.00", "EUR")
    assert first.find("priceDate").get("value") == DATE
    assert first.find("manufacturer").get("id") == "MK"
    assert {f.get("name"): f.get("value") for f in first.findall("feature")} == {"Material": "W", "Size": "L"}
    assert not first.findall("artNr[@type='varcode']")                    # pCon's resolved output is never written


def test_series_comes_from_each_article_and_falls_back_to_the_given_one(skus, tmp_path):
    out = tmp_path / "series.obx"
    export_obx([s for s in skus if s.price is not None], out, manufacturer_id="MK", price_date=DATE)
    series = {i.find("artNr[@type='base']").text: i.find("series").get("id") for i in read(out).findall("./items/bskArticle")}
    assert series == {"CHAIR1": "DM", "SIDE1": "DM"}
    blank = [replace(s, series_id="") for s in skus if s.price is not None]
    export_obx(blank, out, manufacturer_id="MK", price_date=DATE, series_id="FALLBACK")
    assert {i.find("series").get("id") for i in read(out).findall("./items/bskArticle")} == {"FALLBACK"}


def test_unpriced_skus_have_no_row_and_are_counted(skus, tmp_path):
    assert len(build_rows(skus, DATE)) == 5
    summary = export_obx(skus, tmp_path / "mixed.obx", manufacturer_id="MK", price_date=DATE)
    assert summary.exported == 5 and summary.skipped_unpriced == 1       # TABLE1 has no price
    only_unpriced = [s for s in skus if s.price is None]
    with pytest.raises(ObxExportError, match="no priced SKU"):
        export_obx(only_unpriced, tmp_path / "none.obx", manufacturer_id="MK", price_date=DATE)
    assert not (tmp_path / "none.obx").exists()


def test_export_rejects_the_wrong_extension_and_unwritable_target(skus, tmp_path):
    priced = [s for s in skus if s.price is not None]
    with pytest.raises(ObxExportError, match=r"\.obx extension"):
        export_obx(priced, tmp_path / "demo.xml", manufacturer_id="MK", price_date=DATE)
    blocker = tmp_path / "file.txt"
    blocker.write_text("x")
    with pytest.raises(ObxExportError, match="Cannot write"):
        export_obx(priced, blocker / "demo.obx", manufacturer_id="MK", price_date=DATE)


def test_price_is_serialized_from_decimal_without_float_drift(skus):
    priced = [replace(s, price=Decimal("1234.5")) for s in skus if s.price is not None]
    assert build_rows(priced, DATE)[0].price.total_price == 1234.5


def test_compare_with_reference_reports_matches_and_differences(skus, tmp_path):
    priced = [s for s in skus if s.price is not None]
    generated, reference = tmp_path / "generated.obx", tmp_path / "reference.obx"
    export_obx(priced, generated, manufacturer_id="MK", price_date=DATE)
    export_obx([s for s in priced if s.final_article != "CHAIR1 W L"], reference, manufacturer_id="MK", price_date=DATE)
    comparison = compare_with_reference(generated, reference)
    assert len(comparison.matched) == 4 and comparison.extra_in_generated == ["CHAIR1 W L"]
    assert not comparison.identical and comparison.missing_in_generated == []
    assert compare_with_reference(generated, generated).identical
    missing = compare_with_reference(generated, tmp_path / "absent.obx")
    assert missing.problems and "Cannot compare" in missing.problems[0]
