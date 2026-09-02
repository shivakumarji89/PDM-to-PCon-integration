"""Headless validation for the Builder snapper (permutation OBX generation).

Checks the pure permutation engine, hierarchy expansion, varcode format, and the
``SnapperService`` OBX output + sentinel clean round-trip. No database access.

Run:  $env:PYTHONPATH="."; python scripts/validate_snapper.py
"""
from __future__ import annotations

from core.application_context import ApplicationContext
from core.engines.permutations import (
    build_varcode,
    build_varcode_multi,
    compute_permutations,
    expand_with_children,
)
from models.article import Article
from models.product import Product
from models.property import Property
from models.property_value import PropertyValue
from services.obx_service import OBX_SENTINEL, OBXService
from services.snapper_service import SnapperService


def _check_permutations() -> None:
    perms = compute_permutations(
        ["FLC142"], {"Arms": ["N", "H"], "Fabric": ["1HA", "2AB"]}
    )
    assert len(perms) == 4, perms
    assert {tuple(sorted(p["properties"].items())) for p in perms} == {
        (("Arms", "N"), ("Fabric", "1HA")),
        (("Arms", "N"), ("Fabric", "2AB")),
        (("Arms", "H"), ("Fabric", "1HA")),
        (("Arms", "H"), ("Fabric", "2AB")),
    }
    # no dimensions -> one per article; no articles -> empty
    assert compute_permutations(["A"], {}) == [{"article": "A", "properties": {}}]
    assert compute_permutations([], {"X": ["1"]}) == []
    print("OK: compute_permutations - cartesian product")


def _check_hierarchy() -> None:
    perms = compute_permutations(["C"], {"Fabric_Type": ["1HA", "2AB"]})
    child = {
        "Fabric_Colour": {
            "parent": "Fabric_Type",
            "map": {"1HA": ["1HA01", "1HA02"], "2AB": ["2AB01"]},
        }
    }
    # first-only: one child per parent, count unchanged
    first = expand_with_children([dict(p, properties=dict(p["properties"])) for p in perms], child)
    assert len(first) == 2, first
    got = {(p["properties"]["Fabric_Type"], p["properties"]["Fabric_Colour"]) for p in first}
    assert got == {("1HA", "1HA01"), ("2AB", "2AB01")}, got
    # distribute: one row per child value
    dist = expand_with_children(
        [dict(p, properties=dict(p["properties"])) for p in perms], child, distribute=True
    )
    assert len(dist) == 3, dist  # 1HA->2 colours + 2AB->1 colour
    print("OK: expand_with_children - first-only + distribute")


def _check_varcode() -> None:
    assert build_varcode("COSM_NORMAL", {"Arms": "N", "Back_Height": "4"}) == \
        "COSM_NORMAL.Arms=N;COSM_NORMAL.Back_Height=4"
    assert build_varcode("X", {}) == ""
    multi = build_varcode_multi(
        {"Type": "10", "Base_Finish": "R00"},
        {"Type": "CLOUD_ATTR", "Base_Finish": "CLOUD_OPT"},
    )
    assert multi == "CLOUD_ATTR.Type=10;CLOUD_OPT.Base_Finish=R00", multi
    print("OK: build_varcode / build_varcode_multi format")


def _snapshot(ctx) -> None:
    snap = ctx.snapshot_manager.create_empty_snapshot(Product(id="p", code="COSM"))
    snap.articles = [Article(id="a1", code="FLC142"), Article(id="a2", code="FLC143")]
    snap.properties = [Property(id="P_ARMS", name="Arms")]
    snap.property_values = [
        PropertyValue(id="v1", property_id="P_ARMS", value="No Arms", code="N"),
        PropertyValue(id="v2", property_id="P_ARMS", value="Height Arms", code="H"),
    ]


def _check_service() -> None:
    ctx = ApplicationContext()
    _snapshot(ctx)
    svc = SnapperService(ctx)

    dims = svc.available_dimensions()
    assert "Arms" in dims and {d["code"] for d in dims["Arms"]} == {"N", "H"}, dims

    res = svc.generate(
        article_codes=["FLC142", "FLC143"], selections={"Arms": ["N", "H"]}
    )
    assert res.count == 4, res.count  # 2 articles x 2 values
    assert "COSM_OPT.Arms=N" in res.xml
    assert OBX_SENTINEL in res.xml  # sentinel written into final
    assert "<cutBuffer>" in res.xml and "ofmlvarcode" in res.xml
    print("OK: SnapperService.generate - permutation OBX with sentinel")

    # Simulate pCon resolving 2 of the 4 (remove the sentinel from two finals).
    resolved = res.xml.replace(f">{OBX_SENTINEL}</artNr>", ">FLC142 RESOLVED</artNr>", 2)
    cleaned, kept, removed = OBXService.clean_obx(resolved)
    assert kept == 2 and removed == 2, (kept, removed)
    assert OBX_SENTINEL not in cleaned
    print("OK: clean_obx - drops unresolved sentinel articles")


def _check_derive_hierarchy() -> None:
    from models.option import Option
    from models.option_value import OptionValue

    ctx = ApplicationContext()
    snap = ctx.snapshot_manager.create_empty_snapshot(Product(id="p", code="ALW"))
    snap.articles = [Article(id="a1", code="NOALE1")]
    snap.options = [
        Option(id="O_TYPE", name="Fabric Type"),
        Option(id="O_COL", name="Fabric Colour"),
    ]
    snap.option_values = [
        OptionValue(id="t1", option_id="O_TYPE", value="1HA", code="1HA"),
        OptionValue(id="t2", option_id="O_TYPE", value="2AB", code="2AB"),
        OptionValue(id="c1", option_id="O_COL", value="Grey", code="1HA01"),
        OptionValue(id="c2", option_id="O_COL", value="Blue", code="1HA02"),
        OptionValue(id="c3", option_id="O_COL", value="Red", code="2AB01"),
    ]
    # Type 1HA enables colours 1HA01/1HA02; Type 2AB enables 2AB01.
    snap.option_option_dependencies = {"t1": ["c1", "c2"], "t2": ["c3"]}

    svc = SnapperService(ctx)
    child_res, child_props = svc.derive_child_resolutions()
    assert child_props == {"Fabric_Colour"}, child_props
    fc = child_res["Fabric_Colour"]
    assert fc["parent"] == "Fabric_Type", fc
    assert fc["map"] == {"1HA": ["1HA01", "1HA02"], "2AB": ["2AB01"]}, fc["map"]
    print("OK: derive_child_resolutions - parent/child from dependency edges")


def _check_sales_product_line() -> None:
    """Project/OBX sales product line = the commercial series (range 'Aeron' ->
    'AERON'), consistent with the XOCD Program_ID - NOT the product code."""
    ctx = ApplicationContext()
    snap = ctx.snapshot_manager.create_empty_snapshot(
        Product(id="p", code="AER1A11AF", range_name="Aeron")
    )
    snap.articles = [Article(id="a1", code="AER1A11AF")]
    ctx.snapshot_manager.load_snapshot(snap)

    obx = OBXService(ctx).generate()
    assert 'series id="AERON"' in obx.xml, obx.xml[:400]
    assert 'seriesId="AERON"' in obx.xml, obx.xml[:400]
    assert 'series id="AER1A11AF"' not in obx.xml, "series is the product code, not the range"

    snapper = SnapperService(ctx).generate(
        article_codes=["AER1A11AF"], selections={}, snapshot=snap
    )
    assert 'series id="AERON"' in snapper.xml, snapper.xml[:400]
    print("OK: sales product line = commercial series 'AERON' (obx + snapper)")


def main() -> int:
    _check_permutations()
    _check_hierarchy()
    _check_varcode()
    _check_service()
    _check_derive_hierarchy()
    _check_sales_product_line()
    print("ALL SNAPPER CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
