"""Product-level fallback rule in the class scope + empty-value handling in the P&V export."""
from __future__ import annotations

import logging
from types import SimpleNamespace

from models.mdb_export_session import MdbExportSession
from models.article import Article
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.class_creation_selection_service import (
    ClassCreationArticleScope, build_class_creation_scope)
from services.properties_values_mdb_export_service import PropertiesValuesMdbExportService

from tests.test_properties_values_mdb_export_service import _ExportFakeMdb


# ------------------------------------------------------- product-level fallback

def _snap() -> Snapshot:
    snap = Snapshot()
    snap.properties = [Property(id="p1", name="Colour", values=[])]
    snap.property_values = [
        PropertyValue(id="c1", property_id="p1", code="A", value="Black"),
        PropertyValue(id="c2", property_id="p1", code="B", value="Blue"),
        PropertyValue(id="c3", property_id="p1", code="C", value="Cyan"),
    ]
    snap.properties[0].values = list(snap.property_values)
    snap.articles = [
        Article(id="x1", product_id="X", code="X1"), Article(id="x2", product_id="X", code="X2"),
        Article(id="y1", product_id="Y", code="Y1"),
        Article(id="z1", product_id="Z", code="Z1"), Article(id="z2", product_id="Z", code="Z2"),
    ]
    snap.product_property_value_ids = {
        "X": ["c1", "c2", "c3"], "Y": ["c1", "c2", "c3"], "Z": ["c1", "c2", "c3"]}
    return snap


def _values(scope, pid="p1"):
    return set(scope.property_value_ids.get(pid, ()))


def test_product_without_any_article_rows_uses_product_fallback(caplog):
    snap = _snap()
    snap.article_property_value_ids = {}
    with caplog.at_level(logging.INFO, logger="services.class_creation_selection_service"):
        scope = build_class_creation_scope(snap, {"x1", "x2"})
    assert _values(scope) == {"c1", "c2", "c3"}
    assert any("product X" in r.getMessage() and "product-level" in r.getMessage()
               for r in caplog.records)
    assert len([r for r in caplog.records if "product X" in r.getMessage()]) == 1   # once


def test_product_with_article_rows_does_not_use_product_fallback(caplog):
    snap = _snap()
    snap.article_property_value_ids = {"x1": ["c1"], "x2": ["c2"]}
    with caplog.at_level(logging.INFO, logger="services.class_creation_selection_service"):
        scope = build_class_creation_scope(snap, {"x1", "x2"})
    assert _values(scope) == {"c1", "c2"}
    assert not caplog.records


def test_article_without_rows_next_to_siblings_with_rows_gets_nothing():
    snap = _snap()
    snap.article_property_value_ids = {"x1": ["c1"]}            # x2 has none
    only_x2 = build_class_creation_scope(snap, {"x2"})
    assert only_x2.property_ids == frozenset() and only_x2.property_value_ids == {}
    both = build_class_creation_scope(snap, {"x1", "x2"})
    assert _values(both) == {"c1"}                              # not the c2/c3 menu


def test_sibling_rows_outside_the_selection_still_block_the_fallback():
    snap = _snap()
    snap.article_property_value_ids = {"x1": ["c1"]}
    scope = build_class_creation_scope(snap, {"x2"})            # x1 not selected
    assert _values(scope) == set()


def test_different_products_keep_independent_fallback():
    snap = _snap()
    snap.article_property_value_ids = {"x1": ["c1"], "z1": ["c3"]}   # Y has no rows anywhere
    scope = build_class_creation_scope(snap, {"x1", "x2", "y1", "z1", "z2"})
    # X, Z use article rows only; Y (no rows in the product) uses its menu.
    assert _values(scope) == {"c1", "c3"} | {"c1", "c2", "c3"}
    assert _values(build_class_creation_scope(snap, {"x2", "z2"})) == set()
    assert _values(build_class_creation_scope(snap, {"y1"})) == {"c1", "c2", "c3"}


# ---------------------------------------------------- empty-value export handling

def _scope(property_ids=(), values=None, option_ids=(), option_values=None):
    return ClassCreationArticleScope(
        property_ids=frozenset(property_ids),
        property_value_ids={k: frozenset(v) for k, v in (values or {}).items()},
        option_ids=frozenset(option_ids),
        option_value_ids={k: frozenset(v) for k, v in (option_values or {}).items()},
    )


def test_allowed_value_ids_rules():
    allowed = PropertiesValuesMdbExportService._allowed_value_ids
    assert allowed(_scope(["p"], {"p": ["v1"]}), "p") == frozenset({"v1"})
    assert allowed(_scope(["p"], {}), "p") == frozenset()                     # no mapping
    assert allowed(_scope(["p"], {"p": []}), "p") == frozenset()              # empty
    assert allowed(_scope([], {}, ["o"], {"o": ["ov"]}), "o") == frozenset({"ov"})
    assert allowed(_scope([], {}, ["o"], {}), "o") == frozenset()
    assert allowed(_scope(["p"]), "visual-def") is None                       # genuinely unscoped


def _run_export(tmp_path, *, assignment_values, article_links, article_sets=()):
    mdb = tmp_path / "p.mdb"
    mdb.touch()
    data = {"package": [{"com_PackageID": 10}],
            "classes": [{"com_ClassID": 20, "com_ClassName": "Desk_Attribute", "com_PackageID": 10}],
            "articles": [{"com_ArticleID": 5, "com_ArticleCode": "BASE", "com_PackageID": 10}],
            "properties": [], "values": [], "texts": [], "relobjs": []}
    db = _ExportFakeMdb(data)
    session = MdbExportSession(
        product_key="id:p1", mdb_path=str(mdb), package_id=10,
        article_map={"BASE": {"mdb_id": 5}},
        prototypes={"tCOMd_Property": {"com_StatusInfoID": 3}, "tCOMd_PropValue": {"com_StatusInfoID": 3}})
    sessions = SimpleNamespace(
        product_key=lambda _s: "id:p1",
        record_workflow=lambda cur, wf, counts: cur.workflow_status.update(
            {wf: {"status": "exported", "counts": dict(counts)}}),
        save=lambda _s: None)
    vals = [SimpleNamespace(id=i, property_id="p1", value=n, code=c)
            for i, n, c in (("pv1", "Red", "R"), ("pv2", "Blue", "B"), ("pv3", "Green", "G"))]
    source = SimpleNamespace(id="p1", name="Colour", code="COL", data_type="C", values=vals)
    assignment = SimpleNamespace(
        property_id="p1", property_name="Colour",
        values=[SimpleNamespace(value_id=i, code=dict(pv1="R", pv2="B", pv3="G")[i], value=i)
                for i in assignment_values],
        text_block="Colour", usage="Configuration", type="C", placement=0, relation_object="")
    classes = [SimpleNamespace(id="c1", name="Desk_Attribute", properties=[assignment])]
    snapshot = SimpleNamespace(
        product=SimpleNamespace(id="p1", category="Desk", range_name="Desk"),
        articles=[SimpleNamespace(id="a1", product_id="prod1")],
        properties=[source], property_values=vals, options=[], option_values=[],
        article_property_value_ids={"a1": list(article_links)},
        product_property_value_ids={}, product_option_value_ids={},
        product_range={}, attribute_range={}, article_sets=list(article_sets),
        split_classes_by_group=False, class_group_basis="range")
    xocd = SimpleNamespace(
        base_code_entries=lambda _s: [("a1", "BASE")],
        _value_code_map=lambda _s: {"pv1": "R", "pv2": "B", "pv3": "G"},
        _value_lengths=lambda _s: {"p1": 1},
        _prop_ident=lambda n: str(n).replace(" ", "_"))
    ctx = SimpleNamespace(
        mdb_export_session_service=sessions, mdb_service=db, xocd_export_service=xocd,
        engineering_class_service=SimpleNamespace(get_classes=lambda _s: classes))
    result = PropertiesValuesMdbExportService(ctx).export_to_session(snapshot, session, {"a1"})
    assert result["ok"], result
    return sorted(r["com_PropValueFrom"] for r in data["values"]), data


def _set_carrying_elsewhere():
    """An article set lists the property for a1's set, but no value is carried by a1."""
    return [SimpleNamespace(
        id="s", base_code="BASE", article_ids=["a1"], options=[],
        properties=[SimpleNamespace(id="p1", values=[
            SimpleNamespace(id="pv1", article_ids=["other"])])])]


def test_export_in_scope_property_with_values_exports_only_scoped_values(tmp_path):
    codes, _ = _run_export(tmp_path, assignment_values=["pv1", "pv2", "pv3"], article_links=["pv1", "pv3"])
    assert codes == ["G", "R"]


def test_export_in_scope_property_with_empty_class_values_is_limited_to_scope(tmp_path):
    codes, _ = _run_export(tmp_path, assignment_values=[], article_links=["pv2"])
    assert codes == ["B"]               # fallback to PDM values is filtered by scope, not all three


def test_export_in_scope_property_with_no_value_mapping_exports_zero_values(tmp_path):
    codes, data = _run_export(tmp_path, assignment_values=[], article_links=[],
                              article_sets=_set_carrying_elsewhere())
    assert codes == []
    assert len(data["properties"]) == 1            # the property row itself is still written


def test_export_no_value_mapping_with_class_values_still_exports_zero_values(tmp_path):
    codes, _ = _run_export(tmp_path, assignment_values=["pv1", "pv2", "pv3"], article_links=[],
                           article_sets=_set_carrying_elsewhere())
    assert codes == []
