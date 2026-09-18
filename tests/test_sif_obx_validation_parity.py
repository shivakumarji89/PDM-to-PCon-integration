from services.obx_validation_service import ObxValidationService
from services.sif_validation_service import SifValidationService


def test_obx_uses_sale_price_with_pd_1():
    service = ObxValidationService(None)
    xml = """
    <root>
      <bskArticle basketId="1" itemType="BasketArticle">
        <artNr type="base">ABC</artNr>
        <artNr type="final">ABC RED</artNr>
        <itemPrice type="purchase" currency="EUR" value="80"/>
        <itemPrice type="sale" pd="0" currency="EUR" value="90"/>
        <itemPrice type="sale" pd="1" currency="EUR" value="100"/>
      </bskArticle>
    </root>
    """
    currency, lines = service.parse_obx(xml)

    assert currency == "EUR"
    assert len(lines) == 1
    assert lines[0].obx_price == 100.0
    assert lines[0].currency == "EUR"


def test_obx_ignores_partial_planning_articles():
    service = ObxValidationService(None)
    xml = """
    <root>
      <bskArticle basketId="partial" itemType="BasketPartialPlanning">
        <artNr type="base">PARTIAL</artNr>
        <artNr type="final">PARTIAL RED</artNr>
        <itemPrice type="sale" pd="1" currency="EUR" value="999"/>
      </bskArticle>
      <bskArticle basketId="main" itemType="BasketArticle">
        <artNr type="base">MAIN</artNr>
        <artNr type="final">MAIN BLUE</artNr>
        <itemPrice type="sale" pd="1" currency="EUR" value="100"/>
      </bskArticle>
    </root>
    """
    currency, lines = service.parse_obx(xml)

    assert currency == "EUR"
    assert len(lines) == 1
    assert lines[0].base == "MAIN"
    assert lines[0].obx_price == 100.0
    assert lines[0].seq == 1


def test_obx_parent_does_not_inherit_child_price():
    service = ObxValidationService(None)
    xml = """
    <root>
      <bskArticle basketId="parent" itemType="BasketAggregate">
        <artNr type="base">PARENT</artNr>
        <artNr type="final">PARENT BASE</artNr>
        <itemPrice type="sale" pd="1" currency="EUR" value="100"/>
        <bskArticle basketId="child" itemType="BasketArticle">
          <artNr type="base">CHILD</artNr>
          <artNr type="final">CHILD RED</artNr>
          <itemPrice type="sale" pd="1" currency="EUR" value="25"/>
        </bskArticle>
      </bskArticle>
    </root>
    """
    currency, lines = service.parse_obx(xml)

    assert currency == "EUR"
    assert [line.base for line in lines] == ["PARENT", "CHILD"]
    assert [line.obx_price for line in lines] == [100.0, 25.0]


def test_sif_prefers_specific_prefix_band():
    inc = {
        "1H#": (10.0, 1, 1),
        "1HA#": (25.0, 1, 1),
    }

    assert SifValidationService._match_inc(inc, "1HA01") == 25.0


def test_sif_uses_two_character_prefix_when_no_three_character_band():
    inc = {
        "1H#": (10.0, 1, 1),
    }

    assert SifValidationService._match_inc(inc, "1HA01") == 10.0


def test_obx_does_not_fallback_to_purchase_or_pd0_when_sale_pd1_is_missing():
    service = ObxValidationService(None)
    xml = """
    <root>
      <bskArticle itemType="BasketArticle">
        <artNr type="base">ABC</artNr>
        <artNr type="final">ABC RED</artNr>
        <itemPrice type="purchase" currency="EUR" value="80"/>
        <itemPrice type="sale" pd="0" currency="EUR" value="90"/>
      </bskArticle>
    </root>
    """
    currency, lines = service.parse_obx(xml)

    assert currency == ""
    assert len(lines) == 1
    assert lines[0].currency == ""
    assert lines[0].obx_price == 0.0


def test_obx_non_finite_sale_price_is_not_accepted():
    service = ObxValidationService(None)
    xml = """
    <root>
      <bskArticle itemType="BasketArticle">
        <artNr type="base">ABC</artNr>
        <artNr type="final">ABC RED</artNr>
        <itemPrice type="sale" pd="1" currency="EUR" value="NaN"/>
      </bskArticle>
    </root>
    """
    currency, lines = service.parse_obx(xml)

    assert currency == "EUR"
    assert len(lines) == 1
    assert lines[0].obx_price == 0.0


def test_sif_price_is_base_plus_explicit_option_line_amounts():
    service = SifValidationService(None)
    sif = """
    PZ=EUR
    PN=ABC
    PL=100.00
    SP=999.00
    ON=RED
    OL=12.50
    ON=BLUE
    OL=7.50
    SL=END OF FILE
    """
    currency, lines = service.parse_sif(sif)

    assert currency == "EUR"
    assert len(lines) == 1
    assert lines[0].sif_price == 120.0


def test_obx_selected_options_are_represented_as_priced_codes():
    service = ObxValidationService(None)
    xml = """
    <root>
      <bskArticle itemType="BasketArticle">
        <artNr type="base">NODLE140</artNr>
        <artNr type="final">NODLE140 OAK WSE 1HA01</artNr>
        <feature name="PLC" value="DESK"/>
        <feature name="DERIVED" value="NOT_A_PRICED_OPTION"/>
        <itemPrice type="sale" pd="1" currency="EUR" value="250"/>
      </bskArticle>
    </root>
    """
    currency, lines = service.parse_obx(xml)

    assert currency == "EUR"
    assert len(lines) == 1
    assert lines[0].base == "NODLE140"
    assert [option.code for option in lines[0].options] == ["OAK", "WSE", "1HA01"]
    assert lines[0].plc == "DESK"
    assert "DERIVED" in lines[0].features


def test_obx_option_group_matching_consumes_each_pdm_group_once():
    groups = {
        "10": {"RED": 20.0},
        "20": {"RED": 35.0},
    }

    assert SifValidationService._match_inc_groups(groups, ["RED", "RED"]) == 55.0
\n
def test_obx_recovers_completed_articles_from_truncated_export():
    service = ObxValidationService(None)
    xml = """
    <root>
      <bskArticle itemType="BasketArticle">
        <artNr type="base">ABC</artNr>
        <artNr type="final">ABC RED</artNr>
        <itemPrice type="sale" pd="1" currency="GBP" value="100"/>
      </bskArticle>
      <bskArticle itemType="BasketArticle">
        <artNr type="base">DEF</artNr>
        <artNr type="final">DEF BLUE</artNr>
        <itemPrice type="sale" pd="1" currency="GBP" value="200"/>
      </bskArticle>
      <bskArticle itemType="BasketArticle">
        <artNr type="base">INCOMPLETE</artNr>
    