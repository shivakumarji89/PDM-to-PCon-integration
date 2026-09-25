"""Headless validation for the per-article link maps (from PDM).

Verifies the article<->property-value link (PDM ``BaseAttributeValues``) and the
super-product BOM (``ItemComponents``) without a live database:
  * the index helpers map raw rows -> the snapshot link maps
    (``article_property_value_ids`` / ``article_varcond_terms`` /
    ``article_components``);
  * ``PDMService._populate_links`` fills those maps onto a snapshot from stubbed
    repository rows; and
  * the maps survive a snapshot serialization round-trip.

The live fetch SQL is NOT exercised here - verify that against your PDM database.

Run:  $env:QT_QPA_PLATFORM="offscreen"; $env:PYTHONPATH="."; \
      python scripts/validate_article_property_link.py
"""
from __future__ import annotations

from types import SimpleNamespace

from core.application_context import ApplicationContext
from models.article import Article
from models.snapshot import Snapshot
from services.pdm_service import PDMService
from services.snapshot_serialization import snapshot_from_dict, snapshot_to_dict


def _row(item_id, value_id):
    return SimpleNamespace(ItemId=item_id, AttributeValueId=value_id)


def _comp_row(parent, sub, qty, seq):
    return SimpleNamespace(
        ParentItemId=parent, SubItem=sub, Quantity=qty, ComponentSequence=seq
    )


def _term_row(item_id, value_id, name, order, hdo, code):
    return SimpleNamespace(
        ItemId=item_id, AttributeValueId=value_id, AttrName=name,
        DisplayOrder=order, HasDependentOptions=hdo, Code=code,
        ModelSuffix=None, DisplayOrdinal=0,
    )


def _prefix_row(item_id, item, notes, category_id):
    return SimpleNamespace(
        ItemId=item_id, Item=item, Notes=notes, ProductCategoryId=category_id
    )


def _master_row(category_id, notes):
    return SimpleNamespace(ProductCategoryId=category_id, Notes=notes)


def _attr_name_row(item, name):
    return SimpleNamespace(Item=item, AttrName=name)


def _inc_row(item, opt_id, opt_name, val_name, code, inc):
    return SimpleNamespace(
        Item=item, OptionId=opt_id, OptionName=opt_name, ValueName=val_name,
        Code=code, IncrementalPrice=inc,
    )


def check_index() -> None:
    rows = [
        _row("art1", "v1"),
        _row("art1", "v2"),
        _row("art1", "v1"),   # duplicate ignored
        _row("art2", "v3"),
    ]
    index = PDMService._index_item_attribute_values(rows)
    assert index == {"art1": ["v1", "v2"], "art2": ["v3"]}, index
    print("OK: index maps ItemId -> [AttributeValueId] (unique, ordered)")


def check_components_index() -> None:
    rows = [
        _comp_row("sup1", "SUB_A", "1", "1"),
        _comp_row("sup1", "SUB_B", "2", "2"),
        _comp_row("sup2", "SUB_C", None, "1"),
    ]
    index = PDMService._index_item_components(rows)
    assert index == {
        "sup1": [
            {"sub_item": "SUB_A", "quantity": 1, "sequence": "1"},
            {"sub_item": "SUB_B", "quantity": 2, "sequence": "2"},
        ],
        "sup2": [{"sub_item": "SUB_C", "quantity": 1, "sequence": "1"}],
    }, index
    print("OK: ItemComponents index maps parent -> ordered sub-items")


def check_varcond_term_index() -> None:
    rows = [
        _term_row("sup1", "v2", "WorktopWidth", 3, 2, None),
        _term_row("sup1", "v1", "LegStyle", 1, 0, "C"),
        _term_row("sup1", "v1b", "LegStyle", 1, 0, "C"),  # same attr name ignored
    ]
    index = PDMService._index_item_varcond_terms(rows)
    assert index == {
        "sup1": [
            {"name": "LegStyle", "order": 1,
             "has_dependent_options": 0, "order_code": "C"},
            {"name": "WorktopWidth", "order": 3,
             "has_dependent_options": 2, "order_code": ""},
        ],
    }, index
    print("OK: varcond terms indexed (unique by name, sorted by display order)")


def check_populate_links() -> None:
    ctx = ApplicationContext()
    pdm = ctx.pdm_service
    snapshot = Snapshot()
    snapshot.articles = [
        Article(id="I1", product_id="p", code="I1"),
        Article(id="I2", product_id="p", code="I2"),
    ]
    link_rows = [
        _term_row("I1", "v1", "LegStyle", 1, 0, "C"),
        _term_row("I1", "v2", "Colour", 2, 0, "R"),
        _term_row("I2", "v3", "LegStyle", 1, 0, "D"),
    ]
    comp_rows = [_comp_row("I1", "SUB_A", "2", "1")]

    repo = pdm.repository
    repo.get_connection = lambda: SimpleNamespace(close=lambda: None)
    repo.fetch_item_attribute_values = lambda ids, connection=None: link_rows
    repo.fetch_item_components = lambda ids, connection=None: comp_rows
    repo.fetch_article_prefix_lengths = lambda ids, connection=None: [
        _prefix_row("I1", "I1", "6", 42),
        _prefix_row("I2", "I2", "", 42),   # no own Notes -> category fallback
    ]
    repo.fetch_category_master_notes = lambda ids, connection=None: [
        _master_row(42, "5,master"),
    ]
    repo.fetch_item_head_attribute_names = lambda codes, connection=None: [
        _attr_name_row("SUB_A", "LegStyle"),   # the component's own head attr
    ]
    repo.fetch_item_option_increments = lambda prefixes, connection=None: []

    pdm._populate_links(snapshot)
    assert snapshot.article_property_value_ids == {
        "I1": ["v1", "v2"], "I2": ["v3"],
    }, snapshot.article_property_value_ids
    assert snapshot.article_components == {
        "I1": [{"sub_item": "SUB_A", "quantity": 2, "sequence": "1"}],
    }, snapshot.article_components
    assert snapshot.article_varcond_terms["I1"][0]["name"] == "LegStyle"
    # Prefix length: I1 from its own Notes '6'; I2 falls back to the category
    # master item's first Notes token '5'.
    assert snapshot.article_prefix_length == {"I1": 6, "I2": 5}, \
        snapshot.article_prefix_length
    # Per-component controlling head properties (the component's own attrs).
    assert snapshot.component_head_attrs == {"SUB_A": ["LegStyle"]}, \
        snapshot.component_head_attrs
    print("OK: _populate_links fills the article link maps from PDM rows")


def check_component_head_attrs_index() -> None:
    rows = [
        _attr_name_row("FKCKITLEG1", "Base type"),
        _attr_name_row("FKCTOP1580W", "Top material"),
        _attr_name_row("FKCKITLEG1", "Base type"),   # duplicate ignored
        _attr_name_row("FKCTOP1580W", ""),            # blank name ignored
    ]
    out = PDMService._index_component_head_attrs(rows)
    assert out == {
        "FKCKITLEG1": ["Base type"], "FKCTOP1580W": ["Top material"],
    }, out
    print("OK: component head-attr index maps component code -> its own attrs")


def check_option_increments_index() -> None:
    rows = [
        _inc_row("NOALE211", 6530, "Base Finish", "Chrome", "CHR", 12.0),
        _inc_row("NOALE211", 6530, "Base Finish", "Graphite", "R00", 0.0),
        _inc_row("DWE3UH4.0812", 9502, "Worktop Finish", "Oak", "OK", 25.0),
    ]
    out = PDMService._index_option_increments(rows)
    # Keyed by item prefix (up to and including the first '.').
    assert set(out) == {"NOALE211", "DWE3UH4."}, out
    assert len(out["NOALE211"]) == 2, out
    assert out["NOALE211"][0]["option_id"] == 6530
    assert out["DWE3UH4."][0]["increment"] == 25.0
    print("OK: option-increment index maps item prefix -> increment rows")


def check_prefix_length_index() -> None:
    prefix_rows = [
        _prefix_row("a", "a", "6", 1),          # own Notes '6'
        _prefix_row("b", "b", "5,extra", 1),     # first token '5'
        _prefix_row("c", "c", "", 1),            # empty -> category fallback
        _prefix_row("d", "d", "abc", 2),         # 3-char token ignored -> fallback
    ]
    master_rows = [
        _master_row(1, "7,master"),   # category 1 master default -> 7
        _master_row(2, ""),           # category 2 has no usable default -> 0
    ]
    out = PDMService._index_article_prefix_lengths(prefix_rows, master_rows)
    assert out == {"a": 6, "b": 5, "c": 7, "d": 0}, out
    print("OK: prefix length = own Notes token, else category master default")


def check_varcond_value_picking() -> None:
    # End-to-end: the prefix length the loader derives must let the VARCOND pick
    # the CORRECT value (code) for each applicable property, and drop a property
    # whose code is not present in the article number.
    from services.varcond_service import VarCondService
    snap = Snapshot()
    snap.articles = [Article(id="s1", product_id="p", code="DWE362S4C.0812")]
    snap.article_prefix_length = {"s1": 5}   # base 'DWE36'
    snap.article_varcond_terms = {
        "s1": [
            {"name": "WorktopWidth", "order": 1, "has_dependent_options": 2,
             "order_code": ""},   # chars 6-7 -> '2S'
            {"name": "WorktopDepth", "order": 2, "has_dependent_options": 1,
             "order_code": ""},   # char 8    -> '4'
            {"name": "LegStyle", "order": 3, "has_dependent_options": 0,
             "order_code": "C"},  # fixed code 'C'
        ],
    }
    snap.article_components = {"s1": [{"sub_item": "SUB.", "quantity": 1}]}
    rule = VarCondService.__new__(VarCondService).generate(snapshot=snap).rules[0].rule
    # Each applicable property is ADDED and picks the CORRECT value.
    assert "WorktopWidth = '2S'" in rule, rule
    assert "WorktopDepth = '4'" in rule, rule
    assert "LegStyle = 'C'" in rule, rule
    print("OK: applicable properties added, each picks the correct sliced value")


def check_serialization_roundtrip() -> None:
    snapshot = Snapshot()
    snapshot.article_property_value_ids = {"art1": ["v1", "v2"], "art2": ["v3"]}
    snapshot.article_components = {
        "art1": [{"sub_item": "SUB1", "quantity": 2, "sequence": "1"}],
    }
    snapshot.article_varcond_terms = {
        "art1": [{"name": "LegStyle", "order": 1,
                  "has_dependent_options": 0, "order_code": "C"}],
    }
    restored = snapshot_from_dict(snapshot_to_dict(snapshot))
    assert restored.article_property_value_ids == {
        "art1": ["v1", "v2"], "art2": ["v3"],
    }, restored.article_property_value_ids
    assert restored.article_components == {
        "art1": [{"sub_item": "SUB1", "quantity": 2, "sequence": "1"}],
    }, restored.article_components
    assert restored.article_varcond_terms == snapshot.article_varcond_terms, (
        restored.article_varcond_terms
    )
    print("OK: link + components + varcond terms round-trip")


def main() -> int:
    check_index()
    check_components_index()
    check_varcond_term_index()
    check_prefix_length_index()
    check_component_head_attrs_index()
    check_option_increments_index()
    check_populate_links()
    check_varcond_value_picking()
    check_serialization_roundtrip()
    print("ALL ARTICLE-PROPERTY LINK CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
