"""Validate the bulk family load path (``PDMService.load_family``).

PDM-free: stubs the repository so the four bulk ``IN()`` queries plus the two
per-article link queries return canned rows, then asserts ``load_family`` builds
a SINGLE snapshot holding the UNION of every product's data with the per-article
link maps populated (the behaviour that replaced the old per-product
``merge_into_snapshot`` path).

Run:  $env:QT_QPA_PLATFORM="offscreen"; $env:PYTHONPATH="."; \
      python scripts/validate_family_load.py
"""
from __future__ import annotations

from types import SimpleNamespace as NS

from core.application_context import ApplicationContext
from models.product import Product


def _attr(pid, aid, name, vid, code):
    return NS(ProductId=pid, AttributeId=aid, Property=name, PropertyKey=None,
              DisplayOrder=1, AttributeType=1, HasDependentOptions=0,
              Value=name + "V", AttributeValueId=vid, Code=code, ModelSuffix=None)


def _opt(pid, oid, name, vid, code):
    return NS(ProductId=pid, OptionId=oid, Property=name, OptionKey=None,
              IsFabric=0, Value=name + "V", Code=code, SupplierCode=None,
              OptionValueId=vid, OptionDisplayOrder=1, OptionValueDisplayOrdinal=1)


def _item(pid, iid, code, sup=0):
    return NS(ProductId=pid, ItemId=iid, Item=code, Status=1, IsSuperItem=sup,
              Notes=None, WeightKilos=None, VolumeLitres=None, Height=None,
              Width=None, Depth=None, Description=code)


def _info(pid, code, rng, sup=0):
    return NS(ProductId=pid, ProductName="P" + pid, ProductCode=code, Status=1,
              NewProduct=0, IsSuperProduct=sup, RangeName=rng)


def _link(iid, vid, name):
    return NS(ItemId=iid, AttributeValueId=vid, AttrName=name, DisplayOrder=1,
              HasDependentOptions=0, Code="X", ModelSuffix=None, DisplayOrdinal=0)


def _comp(parent, sub):
    return NS(ParentItemId=parent, SubItem=sub, Quantity="1", ComponentSequence="1")


def main() -> int:
    ctx = ApplicationContext()
    pdm = ctx.pdm_service

    products = [
        Product(id="P1", code="AAA", name="Prod1", catalogue_id="C1"),
        Product(id="P2", code="BBB", name="Prod2", catalogue_id="C1"),
    ]
    attr_rows = [_attr("P1", "A1", "Colour", "V1", "R"),
                 _attr("P2", "A2", "Size", "V2", "B")]
    opt_rows = [_opt("P1", "O1", "Fabric", "OV1", "W")]
    item_rows = [_item("P1", "I1", "AAA01"),
                 _item("P2", "I2", "BBB01", 1),
                 _item("P2", "I3", "BBB02", 1)]
    info_rows = [_info("P1", "AAA", "RangeX"), _info("P2", "BBB", "RangeY", 1)]
    link_rows = [_link("I1", "V1", "Colour"),
                 _link("I2", "V2", "Size"),
                 _link("I3", "V2", "Size")]
    comp_rows = [_comp("I2", "SUB_A"), _comp("I3", "SUB_B")]

    repo = pdm.repository
    repo.get_connection = lambda: NS(close=lambda: None)
    repo.fetch_products_attributes = lambda ids, connection=None: attr_rows
    repo.fetch_products_options = (
        lambda ids, catalogue_by_product=None, connection=None: opt_rows
    )
    repo.fetch_products_items = lambda ids, connection=None: item_rows
    repo.fetch_products_info = lambda ids, connection=None: info_rows
    repo.fetch_item_attribute_values = lambda ids, connection=None: link_rows
    repo.fetch_item_components = lambda ids, connection=None: comp_rows
    repo.fetch_article_prefix_lengths = lambda ids, connection=None: []
    repo.fetch_category_master_notes = lambda ids, connection=None: []
    repo.fetch_item_head_attribute_names = lambda codes, connection=None: []
    repo.fetch_item_option_increments = lambda prefixes, connection=None: []
    repo.fetch_products_option_dependencies = lambda ids, connection=None: []
    pdm.save_family_snapshot = lambda snap, name: None

    res = pdm.load_family(products, family_name="Fam")
    assert res.ok, res.message
    snap = res.snapshot

    # One snapshot with the union of every product's data.
    assert len(snap.articles) == 3, snap.articles
    assert {a.code for a in snap.articles} == {"AAA01", "BBB01", "BBB02"}
    assert len(snap.properties) == 2 and len(snap.property_values) == 2
    assert len(snap.options) == 1 and len(snap.option_values) == 1

    # Per-product wiring (P2 is a super product in RangeY).
    assert products[1].is_super_product is True, products[1].is_super_product
    assert products[1].range_name == "RangeY", products[1].range_name
    p2 = [a for a in snap.articles if a.product_id == "P2"]
    assert {a.code for a in p2} == {"BBB01", "BBB02"}, p2

    # Per-article link maps populated on a fresh load.
    assert snap.article_property_value_ids == {
        "I1": ["V1"], "I2": ["V2"], "I3": ["V2"],
    }, snap.article_property_value_ids
    assert set(snap.article_components) == {"I2", "I3"}, snap.article_components
    assert snap.article_varcond_terms["I1"][0]["name"] == "Colour"

    print("ALL FAMILY LOAD CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
