from models.article import Article
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.engineering.engineering_class_service import EngineeringClassService


def make_snapshot():
    prop_a = Property(
        id="A",
        name="Property A",
        attribute_type=0,
        values=[
            PropertyValue(id="A1", property_id="A"),
            PropertyValue(id="A2", property_id="A"),
        ],
    )
    prop_b = Property(
        id="B",
        name="Property B",
        attribute_type=0,
        values=[
            PropertyValue(id="B1", property_id="B"),
            PropertyValue(id="B2", property_id="B"),
        ],
    )
    snapshot = Snapshot()
    snapshot.properties = [prop_a, prop_b]
    snapshot.articles = [
        Article(id="1", product_id="P1", code="XM.tail"),
        Article(id="2", product_id="P2", code="YN.tail"),
    ]
    snapshot.article_property_value_ids = {
        "1": ["A1"],
        "2": ["A2"],
    }
    snapshot.product_property_value_ids = {
        "P1": ["A2", "B1"],
        "P2": ["A1", "B2"],
    }
    return snapshot


def test_product_level_property_is_used_when_article_level_row_is_sparse():
    snapshot = make_snapshot()

    result = EngineeringClassService(None).decode_config_codes_by_value_id(snapshot)

    assert result["A"] == {"A1": "X", "A2": "Y"}
    assert result["B"] == {"B1": "M", "B2": "N"}


def test_article_level_property_wins_over_conflicting_product_value():
    snapshot = make_snapshot()

    result = EngineeringClassService(None).decode_config_codes_by_value_id(snapshot)

    # Product P1 carries A2 and P2 carries A1, but their articles explicitly
    # carry the opposite A values. The article-level value must remain
    # authoritative while B is supplemented from the product row.
    assert result["A"]["A1"] == "X"
    assert result["A"]["A2"] == "Y"
    assert result["B"] == {"B1": "M", "B2": "N"}
