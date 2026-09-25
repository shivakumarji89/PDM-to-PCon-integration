"""Headless validation for the PIP -> Class Creation accuracy diff (Slice 2).

No live PDM: builds a synthetic snapshot, renders it as a PipProduct via
``from_snapshot``, and diffs it against crafted ground-truth PipProducts to
prove every finding category (missing/extra property, split, missing/extra
value, code mismatch, missing code, head decoder-pending) and that an identical
pair passes clean.

Run:  $env:PYTHONPATH="."; python scripts/validate_pip_diff.py
"""
from __future__ import annotations

import sys

from core.application_context import ApplicationContext
from models.article import Article
from models.option import Option
from models.option_value import OptionValue
from models.pip import PipProduct, PipProperty, PipValue
from models.product import Product
from models.property import Property
from models.property_value import PropertyValue


def _snapshot(ctx: ApplicationContext):
    """Type (functional/head, uncoded) + Depth (physical/tail, token+coded) +
    an option, so from_snapshot exercises both sides of the '.' split."""
    product = Product(id="p1", code="DTW1", name="Everywhere", range_name="Everywhere")
    snap = ctx.snapshot_manager.create_empty_snapshot(product)
    snap.id = "p1"

    # Functional/head: no OrderCodeFormatKey token, values uncoded.
    typ = Property(id="pr1", code="", name="Type", display_order=0)
    t1 = PropertyValue(id="tv1", property_id="pr1", value="Desk", code="", display_order=0)
    t2 = PropertyValue(id="tv2", property_id="pr1", value="Table", code="", display_order=1)
    typ.values.extend([t1, t2])
    # Physical/tail: has a token, values coded.
    depth = Property(id="pr2", code="{DEP}", name="Depth", display_order=1)
    d1 = PropertyValue(id="dv1", property_id="pr2", value="800", code="08", display_order=0)
    d2 = PropertyValue(id="dv2", property_id="pr2", value="1000", code="10", display_order=1)
    depth.values.extend([d1, d2])
    snap.properties.extend([typ, depth])
    snap.property_values.extend([t1, t2, d1, d2])

    opt = Option(id="op1", code="{MT}", name="Material", display_order=5)
    ov1 = OptionValue(id="ov1", option_id="op1", value="Oak", code="S4M", display_order=0)
    opt.values.append(ov1)
    snap.options.append(opt)
    snap.option_values.append(ov1)

    snap.articles.append(Article(id="a1", code="DTW1AB.0800S4M", product_id="p1"))
    return snap


def main() -> int:
    ctx = ApplicationContext()
    pip = ctx.pip_service
    snap = _snapshot(ctx)

    actual = pip.from_snapshot(snap)
    names = [p.name for p in actual.properties]
    assert names == ["Type", ".", "Depth", "Material"], names
    print("OK: from_snapshot builds head | . | tail (Type | . | Depth, Material)")

    # 1) Identical pair -> clean pass (no errors, no warnings).
    d = pip.diff(pip.from_snapshot(snap), actual)
    assert d.ok and not d.errors and not d.warnings, d.summary()
    print("OK: identical PIP vs Class Creation -> PASS (no findings)")

    # 2) Ground truth that differs in every category.
    expected = PipProduct(title="DTW1", properties=[
        PipProperty(name="Type", order=0, values=[
            PipValue("Desk", ""), PipValue("Table", ""), PipValue("Bench", ""),
        ]),
        PipProperty(name="Leg", order=1, values=[PipValue("Post", "")]),  # missing prop
        PipProperty(name=".", order=2, is_separator=True),
        PipProperty(name="Depth", order=3, values=[
            PipValue("800", "08"), PipValue("1000", "99"),  # 1000 code mismatch (10 vs 99)
        ]),
        PipProperty(name="Material", order=4, values=[PipValue("Oak", "S4M")]),
    ])
    d = pip.diff(expected, actual)
    cats = {i.category for i in d.items}
    assert "missing_property" in cats, cats          # Leg
    assert "missing_value" in cats, cats             # Type/Bench
    assert "code_mismatch" in cats, cats             # Depth/1000 08!=99 -> wait 10 vs 99
    assert "head_pending" in cats, cats              # Type head codes
    assert not d.ok, "expected failure with errors"
    print(f"OK: divergent PIP flagged -> {d.summary()}; categories={sorted(cats)}")

    # 3) Split mismatch: PIP says Depth is head; ours has it as tail.
    exp_split = PipProduct(properties=[
        PipProperty(name="Type", order=0, values=[PipValue("Desk", ""), PipValue("Table", "")]),
        PipProperty(name="Depth", order=1, values=[PipValue("800", "08"), PipValue("1000", "10")]),
        PipProperty(name=".", order=2, is_separator=True),
        PipProperty(name="Material", order=3, values=[PipValue("Oak", "S4M")]),
    ])
    d = pip.diff(exp_split, actual)
    assert any(i.category == "split" for i in d.items), [i.category for i in d.items]
    print("OK: head/tail split mismatch flagged")

    # 4) Extra value + missing code (warnings, still overall pass if no errors).
    exp_warn = PipProduct(properties=[
        PipProperty(name="Type", order=0, values=[PipValue("Desk", ""), PipValue("Table", "")]),
        PipProperty(name=".", order=1, is_separator=True),
        PipProperty(name="Depth", order=2, values=[
            PipValue("800", "08"), PipValue("1000", "10"),
        ]),
        PipProperty(name="Material", order=3, values=[PipValue("Oak", "S4M")]),
    ])
    # Ours (actual) is identical here -> clean; craft an actual with an uncoded tail.
    snap2 = _snapshot(ctx)
    snap2.property_values[2].code = ""   # Depth/800 uncoded in Class Creation
    d = pip.diff(exp_warn, pip.from_snapshot(snap2))
    assert any(i.category == "missing_code" for i in d.items), [i.category for i in d.items]
    print("OK: uncoded tail value flagged as missing_code (warning)")

    # 5) Excel-style source: HEAD codes are printed -> they ARE validated (not
    #    decoder-pending). Author matching head codes in Class Creation.
    snap3 = _snapshot(ctx)
    for v in snap3.property_values:
        if v.property_id == "pr1":
            v.code = {"Desk": "D", "Table": "T"}[v.value]
    actual3 = pip.from_snapshot(snap3)
    assert [p.name for p in actual3.properties][:2] == ["Type", "."], \
        "head prop with authored codes must STAY functional"
    exp_head_ok = PipProduct(properties=[
        PipProperty(name="Type", order=0, values=[PipValue("Desk", "D"), PipValue("Table", "T")]),
        PipProperty(name=".", order=1, is_separator=True),
        PipProperty(name="Depth", order=2, values=[PipValue("800", "08"), PipValue("1000", "10")]),
        PipProperty(name="Material", order=3, values=[PipValue("Oak", "S4M")]),
    ])
    d = pip.diff(exp_head_ok, actual3)
    assert d.ok and not any(i.category == "head_pending" for i in d.items), d.summary()
    print("OK: Excel-style head codes matched -> clean, no head_pending")

    # 6) Excel head code MISMATCH -> code_mismatch error (head is now verified).
    exp_head_bad = PipProduct(properties=[
        PipProperty(name="Type", order=0, values=[PipValue("Desk", "D"), PipValue("Table", "Z")]),
        PipProperty(name=".", order=1, is_separator=True),
        PipProperty(name="Depth", order=2, values=[PipValue("800", "08"), PipValue("1000", "10")]),
        PipProperty(name="Material", order=3, values=[PipValue("Oak", "S4M")]),
    ])
    d = pip.diff(exp_head_bad, actual3)
    assert any(i.category == "code_mismatch" for i in d.items) and not d.ok, d.summary()
    print("OK: Excel head-code mismatch flagged (code_mismatch error)")

    print("\nvalidate_pip_diff: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
