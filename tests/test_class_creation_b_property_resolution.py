"""Regression tests for B-property (product-level only) config-code resolution.

Covers the mixed BaseAttributeValues (article-level, "A") / ProductAttributeValues
(product-level only, "B") scenario in Class Creation: B must resolve exactly like
A when the article heads carry deterministic evidence, and must remain
unresolved (never guessed) when the evidence is genuinely ambiguous. Ignoring a
property must remove it from both the unresolved count and the warning
findings. A manually assigned slice Width must never be mistaken for a decode.
"""
from __future__ import annotations

from models.article import Article
from models.engineering import Engineering
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.engineering.engineering_class_service import EngineeringClassService


def _prop(pid, values):
    return Property(
        id=pid, name=f"Property {pid}", attribute_type=0,
        has_dependent_options=True,
        values=[PropertyValue(id=v, property_id=pid, value=v) for v in values],
    )


def make_deterministic_snapshot() -> Snapshot:
    """A resolves at article level; B is product-only but fully deterministic
    (each B value maps to a stable, contiguous head position across many
    products, matching the shape of real PDM ProductAttributeValues data)."""
    snapshot = Snapshot()
    snapshot.properties = [_prop("A", ["A1", "A2"]), _prop("B", ["B1", "B2", "B3"])]
    snapshot.articles = [
        Article(id="1", product_id="P1", code="XM1.tail"),
        Article(id="2", product_id="P2", code="XN1.tail"),
        Article(id="3", product_id="P3", code="YM1.tail"),
        Article(id="4", product_id="P4", code="YN1.tail"),
        Article(id="5", product_id="P5", code="XM2.tail"),
        Article(id="6", product_id="P6", code="YM2.tail"),
    ]
    # Article-level: only A is materialised (BaseAttributeValues).
    snapshot.article_property_value_ids = {
        "1": ["A1"], "2": ["A1"], "3": ["A2"], "4": ["A2"],
        "5": ["A1"], "6": ["A2"],
    }
    # Product-level: B exists only here (ProductAttributeValues), consistently
    # keyed by the trailing head character across every product that carries it.
    snapshot.product_property_value_ids = {
        "P1": ["A2", "B1"], "P2": ["A2", "B2"],
        "P3": ["A1", "B1"], "P4": ["A1", "B2"],
        "P5": ["A2", "B3"], "P6": ["A1", "B3"],
    }
    return snapshot


def make_ambiguous_snapshot() -> Snapshot:
    """B is product-only (no BaseAttributeValues at all) and each value's
    carrying products disagree with each other in every head position, so no
    stable contiguous run exists - it must stay unresolved rather than
    receive a guessed code."""
    snapshot = Snapshot()
    snapshot.properties = [_prop("B", ["B1", "B2"])]
    snapshot.articles = [
        Article(id="1", product_id="P1", code="XM.tail"),
        Article(id="2", product_id="P2", code="YN.tail"),
        Article(id="3", product_id="P3", code="XN.tail"),
        Article(id="4", product_id="P4", code="YM.tail"),
    ]
    snapshot.article_property_value_ids = {}
    # B1 carries both XM and YN (no shared position); B2 carries XN and YM.
    snapshot.product_property_value_ids = {
        "P1": ["B1"], "P2": ["B1"], "P3": ["B2"], "P4": ["B2"],
    }
    return snapshot


def test_deterministic_b_property_resolves_from_article_evidence():
    snapshot = make_deterministic_snapshot()
    service = EngineeringClassService(None)
    result = service.decode_config_codes_by_value_id(snapshot)
    assert result["A"] == {"A1": "X", "A2": "Y"}
    assert result["B"] == {"B1": "M1", "B2": "N1", "B3": "M2"}
    resolved = service.resolve_config_codes(snapshot)
    prop_b = next(p for p in snapshot.properties if p.id == "B")
    assert all(str(v.id) in resolved.get("B", {}) for v in prop_b.values)
    assert service.unresolved_config_codes(snapshot) == []


def test_mixed_article_and_product_values_preserve_a_and_recover_b():
    snapshot = make_deterministic_snapshot()
    # A stays article-level authoritative even though a conflicting value is
    # also present on the owning product.
    assert snapshot.article_property_value_ids["1"] == ["A1"]
    assert snapshot.product_property_value_ids["P1"] == ["A2", "B1"]
    service = EngineeringClassService(None)
    result = service.decode_config_codes_by_value_id(snapshot)
    assert result["A"]["A1"] == "X"
    assert "B" in result and result["B"]


def test_b_property_remains_unresolved_when_genuinely_ambiguous():
    snapshot = make_ambiguous_snapshot()
    service = EngineeringClassService(None)
    resolved = service.resolve_config_codes(snapshot)
    assert resolved.get("B", {}) == {}
    unresolved_ids = {p.id for p in service.unresolved_config_codes(snapshot)}
    assert "B" in unresolved_ids


def test_ignore_removes_property_from_unresolved_count_and_findings():
    snapshot = make_ambiguous_snapshot()
    service = EngineeringClassService(None)
    assert "B" in {p.id for p in service.unresolved_config_codes(snapshot)}
    assert any(f.property_id == "B" for f in service.analyze_config_codes(snapshot))

    service.set_config_ignore(snapshot, "B", True)

    assert "B" not in {p.id for p in service.unresolved_config_codes(snapshot)}
    assert not any(f.property_id == "B" for f in service.analyze_config_codes(snapshot))


def test_manual_width_does_not_create_a_false_decoded_mapping():
    snapshot = make_ambiguous_snapshot()
    snapshot.engineering = Engineering()
    service = EngineeringClassService(None)
    cls = service.create_class(snapshot, "Test_Attribute")
    service.assign_property(snapshot, cls.id, "B", property_name="Property B", width=0)
    service.set_width(snapshot, cls.id, "B", 1)

    assert next(a for a in cls.properties if a.property_id == "B").width == 1
    assert service.resolve_config_codes(snapshot).get("B", {}) == {}
    assert "B" in {p.id for p in service.unresolved_config_codes(snapshot)}


def test_after_dot_article_code_is_never_modified():
    snapshot = make_deterministic_snapshot()
    before = {a.id: a.code for a in snapshot.articles}
    service = EngineeringClassService(None)
    service.decode_config_codes_by_value_id(snapshot)
    service.resolve_config_codes(snapshot)
    service.set_config_ignore(snapshot, "B", True)
    service.resolve_config_codes(snapshot)
    after = {a.id: a.code for a in snapshot.articles}
    assert before == after
    for article in snapshot.articles:
        assert article.code.endswith(".tail")
