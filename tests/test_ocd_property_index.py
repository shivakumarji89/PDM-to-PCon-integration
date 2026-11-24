"""Exported property rows are per class: one source property in N classes -> N property rows."""
from __future__ import annotations

from types import SimpleNamespace

from services.ocd_export_service import OcdExportService


def _service():
    picking = SimpleNamespace(prop_info_pic_prefix=lambda *a, **k: "")
    return OcdExportService(SimpleNamespace(material_picking_service=picking))


def _assign(pid, name):
    return SimpleNamespace(property_id=pid, property_name=name, type="C", usage="", text_block="")


def _snapshot():
    return SimpleNamespace(
        properties=[SimpleNamespace(id="p1", code=""), SimpleNamespace(id="p2", code="")],
        property_values=[
            SimpleNamespace(id="v1", property_id="p1", code="R", value="Red"),
            SimpleNamespace(id="v2", property_id="p1", code="B", value="Blue"),
            SimpleNamespace(id="v3", property_id="p2", code="S", value="Small"),
        ],
        option_values=[],
    )


CODES = {"v1": "R", "v2": "B", "v3": "S"}


def _build(classes):
    svc, snap = _service(), _snapshot()
    class_index = {str(c.id): 100 + i for i, c in enumerate(classes)}
    prop_rows, index = svc._properties(snap, classes, class_index, {}, {}, {}, {})
    val_rows = svc._property_values(snap, classes, index, {}, {}, CODES, {})
    return prop_rows, index, val_rows, class_index


def _two_classes():
    return [
        SimpleNamespace(id="cA", name="AAA_ATTRIBUTE", properties=[_assign("p1", "Colour"), _assign("p2", "Size")]),
        SimpleNamespace(id="cB", name="BBB_ATTRIBUTE", properties=[_assign("p1", "Colour"), _assign("p2", "Size")]),
    ]


def test_same_source_property_in_two_classes_gets_two_distinct_property_ids():
    prop_rows, index, _vals, class_index = _build(_two_classes())
    assert index[("cA", "p1")] != index[("cB", "p1")]
    assert len(prop_rows) == 4 and len({r["com_PropertyID"] for r in prop_rows}) == 4
    owner = {r["com_PropertyID"]: r["com_ClassID"] for r in prop_rows}
    assert owner[index[("cA", "p1")]] == class_index["cA"]
    assert owner[index[("cB", "p1")]] == class_index["cB"]


def test_each_class_values_reference_its_own_property_id():
    prop_rows, index, vals, class_index = _build(_two_classes())
    owner = {r["com_PropertyID"]: r["com_ClassID"] for r in prop_rows}
    by_prop: dict[int, set[str]] = {}
    for v in vals:
        by_prop.setdefault(v["com_PropertyID"], set()).add(v["com_PropValueFrom"])
    for cls in ("cA", "cB"):
        assert by_prop[index[(cls, "p1")]] == {"R", "B"}
        assert by_prop[index[(cls, "p2")]] == {"S"}
        assert owner[index[(cls, "p1")]] == class_index[cls]
    assert len(vals) == 6                       # 3 values x 2 classes, none lost or doubled


def test_multiple_properties_in_one_class_stay_mapped():
    prop_rows, index, vals, _ = _build(_two_classes()[:1])
    p1, p2 = index[("cA", "p1")], index[("cA", "p2")]
    assert p1 != p2
    got = {(v["com_PropertyID"], v["com_PropValueFrom"]) for v in vals}
    assert got == {(p1, "R"), (p1, "B"), (p2, "S")}


def test_property_in_only_one_class_keeps_existing_behaviour():
    classes = [
        SimpleNamespace(id="cA", name="AAA_ATTRIBUTE", properties=[_assign("p1", "Colour")]),
        SimpleNamespace(id="cB", name="BBB_ATTRIBUTE", properties=[_assign("p2", "Size")]),
    ]
    prop_rows, index, vals, _ = _build(classes)
    assert [r["com_PropertyID"] for r in prop_rows] == [1, 2]       # sequential ids as before
    assert {(v["com_PropertyID"], v["com_PropValueFrom"]) for v in vals} == {
        (1, "R"), (1, "B"), (2, "S")}


def test_no_duplicate_value_primary_keys_or_property_value_pairs():
    classes = _two_classes() + [
        SimpleNamespace(id="cC", name="CCC_ATTRIBUTE", properties=[_assign("p1", "Colour")])]
    _prop_rows, _index, vals, _ = _build(classes)
    ids = [v["com_ValueID"] for v in vals]
    assert len(ids) == len(set(ids))
    pairs = [(v["com_PropertyID"], v["com_PropValueFrom"]) for v in vals]
    assert len(pairs) == len(set(pairs))       # the (property, value) unique index of tCOMd_PropValue
