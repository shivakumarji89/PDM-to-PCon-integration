"""Headless validation for the offline option-increment pricing report.

Builds a synthetic super product (BOM + option increment prices) and checks
``PricingService`` reports the ItemOptionValues increments per super product and
sub-item. No database access.

Run:  $env:QT_QPA_PLATFORM="offscreen"; $env:PYTHONPATH="."; \
      python scripts/validate_pricing.py
"""
from __future__ import annotations

from models.article import Article
from models.product import Product
from models.snapshot import Snapshot
from services.pricing_service import PriceParams, PricingService


def _snapshot() -> Snapshot:
    snap = Snapshot()
    snap.articles = [Article(id="sup1", code="DWE362S4C.0812")]
    snap.article_components = {
        "sup1": [{"sub_item": "DWE3UH4.", "quantity": 1, "sequence": "1"}],
    }
    snap.option_increments = {
        "DWE3UH4.": [
            {"item": "DWE3UH4.", "option_id": 9502, "option_name": "Worktop Finish",
             "value_name": "Oak", "code": "OK", "increment": 25.0},
            {"item": "DWE3UH4.", "option_id": 9502, "option_name": "Worktop Finish",
             "value_name": "Walnut", "code": "WN", "increment": 40.0},
        ],
    }
    return snap


def main() -> int:
    svc = PricingService.__new__(PricingService)  # no context for generate(snapshot)

    res = svc.generate(snapshot=_snapshot())

    # 1) Every increment row is reported (per option value, not deduped).
    assert len(res.lines) == 2, res.lines
    assert {ln.value_name for ln in res.lines} == {"Oak", "Walnut"}
    assert {ln.increment for ln in res.lines} == {25.0, 40.0}
    print("OK: option-value increments reported per sub-item")

    # 2) Report text groups by super product then sub-item.
    assert "# DWE362S4C.0812" in res.text
    assert "  DWE3UH4." in res.text
    assert "[9502] Worktop Finish / Oak (OK) = 25" in res.text
    print("OK: report text grouped by super product / sub-item")

    # 3) Empty snapshot -> no lines + warnings.
    empty = svc.generate(snapshot=Snapshot())
    assert empty.lines == []
    assert any("ItemComponents" in w for w in empty.warnings)
    print("OK: no BOM -> no pricing (warns)")

    _check_build_records()
    _check_article_set_slicing()
    _check_super_global()
    _check_classification()
    _check_super_plan()
    _check_diff()

    print("ALL PRICING CHECKS PASSED")
    return 0


class _Row:
    """Minimal stand-in for a pyodbc row (attribute access by column name)."""

    def __init__(self, **cols: object) -> None:
        self.__dict__.update(cols)


def _check_build_records() -> None:
    params = PriceParams(currency="GBP", mydate="06-Apr-2026",
                         valid_from="2026-04-06", valid_to="2027-04-05")
    base_rows = [
        _Row(Item="DWE3UH4.0812", price=250.0),   # plain article -> B
        _Row(Item="DWESUPER.01", price=999.0),     # super -> global
        _Row(Item="DWE3UH4.9999", price=None),     # unresolved
    ]
    inc_rows = [
        _Row(Item="DWE3UH4.0812", OptionId=9502, Code="OK", IncPrice=25.0),
        _Row(Item="DWE3UH4.0812", OptionId=9502, Code="WN#", IncPrice=40.0),
        _Row(Item="DWESUPER.01", OptionId=1, Code="X", IncPrice=5.0),  # super -> skip
    ]
    super_codes = {"DWESUPER.01"}
    prefix_by_item = {"DWE3UH4.0812": "DWE3UH4.", "DWESUPER.01": "DWESUPER."}

    records, unresolved = PricingService.build_records(
        base_rows, inc_rows, super_codes, prefix_by_item, params
    )

    assert unresolved == ["DWE3UH4.9999"], unresolved

    base = [r for r in records if r.level == "B"]
    # Base article is sliced at the prefix: base code + dimension chars in varcond.
    assert len(base) == 1 and base[0].article_code == "DWE3UH4.", base
    assert base[0].variant_condition == "0812", base[0].variant_condition
    assert base[0].value == 250.0 and base[0].currency == "GBP"

    glob = [r for r in records if r.is_global]
    # Super base (full code) + super increment (code + option), both global.
    glob_base = [r for r in glob if " " not in r.variant_condition]
    assert len(glob_base) == 1 and glob_base[0].variant_condition == "DWESUPER.01", glob
    assert glob_base[0].value == 999.0 and glob_base[0].article_code == ""
    glob_inc = [r for r in glob if " " in r.variant_condition]
    assert len(glob_inc) == 1 and glob_inc[0].variant_condition == "DWESUPER.01 1=X", glob_inc

    ups = [r for r in records if r.level == "X"]
    assert len(ups) == 2, ups  # only the non-super article upcharges are level X
    assert {u.variant_condition for u in ups} == {
        "0812 9502=OK", "0812 9502=WN"  # '#' stripped, PDM ' {opt}={code}' format
    }, {u.variant_condition for u in ups}
    assert all(u.article_code == "DWE3UH4." for u in ups)
    print("OK: build_records - base/global/upcharge shapes match PDM")


def _check_article_set_slicing() -> None:
    from models.article_set import ArticleSet

    svc = PricingService.__new__(PricingService)
    snap = Snapshot()
    snap.articles = [
        Article(id="a1", code="NOALE211"),
        Article(id="a2", code="NOALE251"),
    ]
    # Article set base length 6 -> base "NOALE2", dims "11"/"51" (PDM parity).
    snap.article_sets = [
        ArticleSet(id="s1", base_length=6, base_code="NOALE2",
                   article_ids=["a1", "a2"])
    ]
    prefix_by_item = svc._prefix_by_item(snap)
    assert prefix_by_item == {"NOALE211": "NOALE2", "NOALE251": "NOALE2"}, prefix_by_item

    params = PriceParams(currency="GBP")
    base_rows = [_Row(Item="NOALE211", price=1770.0), _Row(Item="NOALE251", price=1920.0)]
    inc_rows = [_Row(Item="NOALE211", OptionId=3344, Code="1HA", IncPrice=31.0)]
    records, _ = PricingService.build_records(
        base_rows, inc_rows, set(), prefix_by_item, params
    )
    base = {(r.article_code, r.variant_condition) for r in records if r.level == "B"}
    assert base == {("NOALE2", "11"), ("NOALE2", "51")}, base
    ups = [r for r in records if r.level == "X"]
    assert ups[0].article_code == "NOALE2", ups[0]
    assert ups[0].variant_condition == "11 3344=1HA", ups[0].variant_condition
    print("OK: article-set base_length slices base code + dims into varcond")


def _check_super_global() -> None:
    # Super product: base + incremental go to GLOBAL, full code, no slicing.
    params = PriceParams(currency="GBP")
    super_codes = {"DTWB1E3.C"}
    base_rows = [_Row(Item="DTWB1E3.C", price=540.0)]
    inc_rows = [_Row(Item="DTWB1E3.C", OptionId=3785, Code="CD", IncPrice=60.0)]
    records, _ = PricingService.build_records(
        base_rows, inc_rows, super_codes, {}, params
    )
    assert all(r.is_global for r in records), records
    base = [r for r in records if r.variant_condition == "DTWB1E3.C"]
    assert len(base) == 1 and base[0].value == 540.0, base
    inc = [r for r in records if r.variant_condition == "DTWB1E3.C 3785=CD"]
    assert len(inc) == 1 and inc[0].value == 60.0, inc
    assert all(r.article_code == "" for r in records)  # global, no base article
    print("OK: super product -> global base + incremental (full code, no slice)")


def _check_classification() -> None:
    svc = PricingService.__new__(PricingService)
    # Super pricing is decided by the PRODUCT, not the per-item flag or BOM.
    snap = Snapshot()
    snap.product = Product(id="P1", is_super_product=True)
    snap.articles = [
        Article(id="a1", code="ONE.01", product_id="P1"),
        Article(id="a2", code="TWO.01", product_id="P1"),
    ]
    codes = svc._super_item_codes(snap)
    assert codes == {"ONE.01", "TWO.01"}, codes
    # A non-super product prices every article as a plain (sliced) article,
    # even if it carries a BOM or a per-item super flag.
    snap2 = Snapshot()
    snap2.product = Product(id="P2", is_super_product=False)
    snap2.articles = [Article(id="a1", code="PLAIN.01", product_id="P2",
                              is_super_item=True)]
    snap2.article_components = {"a1": [{"sub_item": "X.", "quantity": 1}]}
    assert svc._super_item_codes(snap2) == set(), svc._super_item_codes(snap2)
    print("OK: classification - super PRODUCT => global (not per-item / BOM)")


def _check_super_plan() -> None:
    svc = PricingService.__new__(PricingService)
    # A super product prices its COMPONENT article numbers globally (each
    # component code is a variant condition), NOT its own super item.
    snap = Snapshot()
    snap.product = Product(id="P1", is_super_product=True)
    snap.articles = [Article(id="sup1", code="DWESUPER.01", product_id="P1")]
    snap.article_components = {"sup1": [
        {"sub_item": "COMPA.01", "quantity": 1, "sequence": "1"},
        {"sub_item": "COMPB.02", "quantity": 1, "sequence": "2"},
    ]}
    items, super_codes = svc._price_plan(snap)
    assert set(items) == {"COMPA.01", "COMPB.02"}, items
    assert super_codes == {"COMPA.01", "COMPB.02"}, super_codes
    assert "DWESUPER.01" not in items, items  # super item itself is not priced
    # A non-super product prices its own articles as sliced (never global).
    snap2 = Snapshot()
    snap2.product = Product(id="P2", is_super_product=False)
    snap2.articles = [Article(id="a", code="PLAIN.01", product_id="P2")]
    items2, super2 = svc._price_plan(snap2)
    assert items2 == ["PLAIN.01"] and super2 == set(), (items2, super2)
    # Even without the product flag, a BOM parent is a super item: only its
    # components are priced (never the parent as a base), and a component that
    # also appears in the loaded articles is not double-priced.
    snap3 = Snapshot()
    snap3.product = Product(id="P3", is_super_product=False)
    snap3.articles = [
        Article(id="sp", code="SPITEM.01", product_id="P3"),
        Article(id="c1", code="COMPX.01", product_id="P3"),
    ]
    snap3.article_components = {"sp": [{"sub_item": "COMPX.01", "quantity": 1}]}
    items3, super3 = svc._price_plan(snap3)
    assert items3 == ["COMPX.01"], items3
    assert super3 == {"COMPX.01"}, super3
    print("OK: super plan - component article numbers priced globally")


def _check_diff() -> None:
    params = PriceParams(currency="GBP")
    y1 = [
        _Row(Item="A.01", price=100.0),
        _Row(Item="B.01", price=200.0),
        _Row(Item="C.01", price=300.0),
    ]
    y2 = [
        _Row(Item="A.01", price=100.0),   # unchanged
        _Row(Item="B.01", price=210.0),   # changed
        _Row(Item="D.01", price=400.0),   # added (C removed)
    ]
    base, _ = PricingService.build_records(y1, [], set(), {}, params)
    curr, _ = PricingService.build_records(y2, [], set(), {}, params)

    d = PricingService.diff(base, curr)
    assert d.unchanged == 1, d.unchanged
    assert len(d.changed) == 1 and d.changed[0][0].value == 200.0, d.changed
    assert d.changed[0][1].value == 210.0
    assert {r.article_code for r in d.added} == {"D.01"}, d.added
    assert {r.article_code for r in d.removed} == {"C.01"}, d.removed
    assert d.has_changes
    print("OK: diff - year-over-year add/change/remove/unchanged")


if __name__ == "__main__":
    raise SystemExit(main())
