from models.article import Article
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.engineering.engineering_class_service import EngineeringClassService
import services.engineering.engineering_class_decode_fix as decode_fix


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
        Article(id="2", product_id="P2", code="XN.tail"),
        Article(id="3", product_id="P3", code="YM.tail"),
        Article(id="4", product_id="P4", code="YN.tail"),
    ]
    # A is available at article level, while B exists only in the product rows.
    snapshot.article_property_value_ids = {
        "1": ["A1"],
        "2": ["A1"],
        "3": ["A2"],
        "4": ["A2"],
    }
    snapshot.product_property_value_ids = {
        "P1": ["A2", "B1"],
        "P2": ["A2", "B2"],
        "P3": ["A1", "B1"],
        "P4": ["A1", "B2"],
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

    # Product rows deliberately carry conflicting A values. The article-level
    # A values remain authoritative while B is supplemented from product rows.
    assert result["A"] == {"A1": "X", "A2": "Y"}
    assert result["B"] == {"B1": "M", "B2": "N"}


def test_partial_legacy_decode_does_not_hide_product_level_property(monkeypatch):
    snapshot = make_snapshot()

    # Reproduce the real failure mode: the legacy decoder successfully resolves
    # the article-level property A, but returns no B mapping even after the
    # product-level values have been merged.
    def partial_legacy_decode(_self, _snapshot):
        return {"A": {"A1": "X", "A2": "Y"}}

    monkeypatch.setattr(decode_fix, "_ORIGINAL_DECODE", partial_legacy_decode)

    result = EngineeringClassService(None).decode_config_codes_by_value_id(snapshot)

    assert result["A"] == {"A1": "X", "A2": "Y"}
    assert result["B"] == {"B1": "M", "B2": "N"}
