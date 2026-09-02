"""Validate the value combination table generator (OCD 4.3 section 2.21).

A synthetic 3-article snapshot with two configurable properties -> assert the
distinct-combination table lines, the ``<name>_tbl.csv`` rows, the ``TABLE()``
constraint body, exclusion of a non-uniform property, and determinism.
"""
from __future__ import annotations

from core.application_context import ApplicationContext
from models.article import Article
from models.article_set import ArticleSet, SetAttribute, SetValue
from models.engineering import Engineering
from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.option import Option
from models.option_value import OptionValue
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.snapshot_serialization import snapshot_from_dict, snapshot_to_dict


def _make_snapshot() -> Snapshot:
    # 3 articles = 3 valid combinations. Back Material (F/P) x Arms (A/H); the
    # combos that exist: (F,A), (F,H), (P,A). "Width" is all-numeric ->
    # parametric -> excluded. Two bases (B1: a1,a2 / B2: a3) -> COL_BAN scope.
    a1 = Article(id="a1", code="CH-F-A", product_id="P1")
    a2 = Article(id="a2", code="CH-F-H", product_id="P1")
    a3 = Article(id="a3", code="CH-P-A", product_id="P1")
    back = Property(id="BM", name="Back Material", display_order=1, values=[
        PropertyValue(id="f", property_id="BM", value="Butterfly", code="F"),
        PropertyValue(id="p", property_id="BM", value="TriFlex", code="P"),
    ])
    arms = Property(id="AR", name="Arms", display_order=2, values=[
        PropertyValue(id="fx", property_id="AR", value="Fixed", code="A"),
        PropertyValue(id="hi", property_id="AR", value="Adjustable", code="H"),
    ])
    width = Property(id="WD", name="Width", display_order=3, values=[
        PropertyValue(id="w6", property_id="WD", value="600", code="06"),
        PropertyValue(id="w8", property_id="WD", value="800", code="08"),
    ])
    fam = EngineeringFamily(id="F1", members=[
        MemberArticle(id="m1", article_id="a1", family_id="F1", reduced_article="B1"),
        MemberArticle(id="m2", article_id="a2", family_id="F1", reduced_article="B1"),
        MemberArticle(id="m3", article_id="a3", family_id="F1", reduced_article="B2"),
    ])
    aset = ArticleSet(id="S1", article_ids=["a1", "a2", "a3"], properties=[
        SetAttribute(id="BM", name="Back Material", values=[
            SetValue(id="f", value="Butterfly", code="F", article_ids=["a1", "a2"]),
            SetValue(id="p", value="TriFlex", code="P", article_ids=["a3"]),
        ]),
        SetAttribute(id="AR", name="Arms", values=[
            SetValue(id="fx", value="Fixed", code="A", article_ids=["a1", "a3"]),
            SetValue(id="hi", value="Adjustable", code="H", article_ids=["a2"]),
        ]),
        SetAttribute(id="WD", name="Width", values=[
            SetValue(id="w6", value="600", code="06", article_ids=["a1", "a2"]),
            SetValue(id="w8", value="800", code="08", article_ids=["a3"]),
        ]),
    ])
    return Snapshot(id="S1", articles=[a1, a2, a3],
                    properties=[back, arms, width],
                    engineering=Engineering(families=[fam]), article_sets=[aset])


def main() -> None:
    ctx = ApplicationContext()
    svc = ctx.engineering_value_table_service
    snap = _make_snapshot()

    table = svc.build_property_table(snap, name="config")
    assert table is not None, "no table built"

    # Columns: base scope first, then discrete props in display order; the
    # all-numeric "Width" (parametric) is excluded.
    assert table.property_names == ["COL_BAN", "COL_BACK_MATERIAL", "COL_ARMS"], \
        table.property_names
    assert table.access == {
        "COL_BAN": "$BAN",
        "COL_BACK_MATERIAL": "x.Back_Material",
        "COL_ARMS": "x.Arms",
    }, table.access

    # Distinct combinations, deterministically ordered (by tuple).
    assert table.lines == [
        {"COL_BAN": "B1", "COL_BACK_MATERIAL": "F", "COL_ARMS": "A"},
        {"COL_BAN": "B1", "COL_BACK_MATERIAL": "F", "COL_ARMS": "H"},
        {"COL_BAN": "B2", "COL_BACK_MATERIAL": "P", "COL_ARMS": "A"},
    ], table.lines

    # OCD _tbl.csv rows.
    assert svc.to_csv_rows(table) == [
        "1;COL_BAN;B1",
        "1;COL_BACK_MATERIAL;F",
        "1;COL_ARMS;A",
        "2;COL_BAN;B1",
        "2;COL_BACK_MATERIAL;F",
        "2;COL_ARMS;H",
        "3;COL_BAN;B2",
        "3;COL_BACK_MATERIAL;P",
        "3;COL_ARMS;A",
    ], svc.to_csv_rows(table)

    # Constraint body: proper OCD form, base via $BAN, class IS_A.
    assert svc.constraint_body(table) == (
        "Objects:\r\n  x IS_A Class_Attribute.\r\n"
        "Restrictions:\r\n  TABLE CONFIG ( COL_BAN = $BAN, "
        "COL_BACK_MATERIAL = x.Back_Material, COL_ARMS = x.Arms )."
    ), svc.constraint_body(table)

    # Deterministic.
    again = svc.build_property_table(snap, name="config")
    assert again.lines == table.lines, "non-deterministic"
    assert again.property_names == table.property_names

    _check_dependency_tables()
    _check_dependency_base()
    _check_persistence()
    _check_partial_coverage()

    print("validate_value_table: PASS")


def _check_partial_coverage() -> None:
    # A property present on only SOME articles is still a column; the row that
    # lacks it simply omits it (correlation preserved, no over-permit).
    a1 = Article(id="a1", code="C1", product_id="P1")
    a2 = Article(id="a2", code="C2", product_id="P1")
    arms = Property(id="AR", name="Arms", display_order=1, values=[
        PropertyValue(id="fx", property_id="AR", value="Fixed", code="A"),
        PropertyValue(id="hi", property_id="AR", value="Adjustable", code="H"),
    ])
    lumbar = Property(id="LU", name="Lumbar", display_order=2, values=[
        PropertyValue(id="y", property_id="LU", value="Yes", code="Y"),
    ])
    fam = EngineeringFamily(id="F1", members=[
        MemberArticle(id="m1", article_id="a1", family_id="F1", reduced_article="B1"),
        MemberArticle(id="m2", article_id="a2", family_id="F1", reduced_article="B1"),
    ])
    aset = ArticleSet(id="S1", article_ids=["a1", "a2"], properties=[
        SetAttribute(id="AR", name="Arms", values=[
            SetValue(id="fx", value="Fixed", code="A", article_ids=["a1"]),
            SetValue(id="hi", value="Adjustable", code="H", article_ids=["a2"]),
        ]),
        SetAttribute(id="LU", name="Lumbar", values=[
            SetValue(id="y", value="Yes", code="Y", article_ids=["a1"]),  # a1 only
        ]),
    ])
    snap = Snapshot(id="S1", articles=[a1, a2], properties=[arms, lumbar],
                    engineering=Engineering(families=[fam]), article_sets=[aset])
    svc = ApplicationContext().engineering_value_table_service
    table = svc.build_property_table(snap, name="config")
    # Lumbar (partial) is still a column; a2's row omits it.
    assert table.property_names == ["COL_BAN", "COL_ARMS", "COL_LUMBAR"], \
        table.property_names
    assert table.lines == [
        {"COL_BAN": "B1", "COL_ARMS": "A", "COL_LUMBAR": "Y"},
        {"COL_BAN": "B1", "COL_ARMS": "H"},
    ], table.lines


def _make_dep_snapshot() -> Snapshot:
    # Frame finish (parent) -> Armpad finish + Base finish (children), via the
    # DependentOptionValues graph. G1 -> Armpad BK, Base {G1,L7P};
    # ZM -> Armpad ZM, Base {L7P,ZM}.
    frame = Option(id="FF", name="Frame finish", values=[
        OptionValue(id="ff_g1", option_id="FF", value="Graphite", code="G1"),
        OptionValue(id="ff_zm", option_id="FF", value="Alpine", code="ZM"),
    ])
    armpad = Option(id="AF", name="Armpad finish", values=[
        OptionValue(id="af_bk", option_id="AF", value="Black", code="BK"),
        OptionValue(id="af_zm", option_id="AF", value="Alpine", code="ZM"),
    ])
    base = Option(id="BF", name="Base finish", values=[
        OptionValue(id="bf_g1", option_id="BF", value="Graphite", code="G1"),
        OptionValue(id="bf_l7", option_id="BF", value="Silver", code="L7P"),
        OptionValue(id="bf_zm", option_id="BF", value="Alpine", code="ZM"),
    ])
    snap = Snapshot(id="D1", options=[frame, armpad, base])
    snap.option_option_dependencies = {
        "ff_g1": ["af_bk", "bf_g1", "bf_l7"],
        "ff_zm": ["af_zm", "bf_l7", "bf_zm"],
    }
    return snap


def _check_dependency_tables() -> None:
    ctx = ApplicationContext()
    svc = ctx.engineering_value_table_service
    tables = svc.build_dependency_tables(_make_dep_snapshot())
    assert len(tables) == 1, [t.name for t in tables]
    t = tables[0]
    assert t.name == "frame_finish", t.name
    assert t.property_names == [
        "COL_FRAME_FINISH", "COL_ARMPAD_FINISH", "COL_BASE_FINISH"
    ], t.property_names
    assert t.access == {
        "COL_FRAME_FINISH": "x.Frame_Finish",
        "COL_ARMPAD_FINISH": "x.Armpad_Finish",
        "COL_BASE_FINISH": "x.Base_Finish",
    }, t.access
    # One logical row per parent value; Base finish carries a value SET.
    assert t.lines == [
        {"COL_FRAME_FINISH": "G1", "COL_ARMPAD_FINISH": "BK",
         "COL_BASE_FINISH": ["G1", "L7P"]},
        {"COL_FRAME_FINISH": "ZM", "COL_ARMPAD_FINISH": "ZM",
         "COL_BASE_FINISH": ["L7P", "ZM"]},
    ], t.lines
    # CSV emits one row per value in a set.
    assert svc.to_csv_rows(t) == [
        "1;COL_FRAME_FINISH;G1",
        "1;COL_ARMPAD_FINISH;BK",
        "1;COL_BASE_FINISH;G1",
        "1;COL_BASE_FINISH;L7P",
        "2;COL_FRAME_FINISH;ZM",
        "2;COL_ARMPAD_FINISH;ZM",
        "2;COL_BASE_FINISH;L7P",
        "2;COL_BASE_FINISH;ZM",
    ], svc.to_csv_rows(t)
    assert svc.constraint_body(t) == (
        "Objects:\r\n  x IS_A Class_Attribute.\r\n"
        "Restrictions:\r\n  TABLE FRAME_FINISH ( COL_FRAME_FINISH = x.Frame_Finish, "
        "COL_ARMPAD_FINISH = x.Armpad_Finish, COL_BASE_FINISH = x.Base_Finish )."
    ), svc.constraint_body(t)


def _check_dependency_base() -> None:
    # Two bases offer different finishes -> the fabric table is base-scoped
    # (COL_BAN). B1 offers Frame G1 -> Base {G1,L7P}; B2 offers Frame ZM -> Base L7P.
    frame = Option(id="FF", name="Frame finish", values=[
        OptionValue(id="ff_g1", option_id="FF", value="Graphite", code="G1"),
        OptionValue(id="ff_zm", option_id="FF", value="Alpine", code="ZM"),
    ])
    base = Option(id="BF", name="Base finish", values=[
        OptionValue(id="bf_g1", option_id="BF", value="Graphite", code="G1"),
        OptionValue(id="bf_l7", option_id="BF", value="Silver", code="L7P"),
    ])
    a1 = Article(id="a1", code="X1", product_id="P1")
    a2 = Article(id="a2", code="X2", product_id="P2")
    fam = EngineeringFamily(id="F1", members=[
        MemberArticle(id="m1", article_id="a1", family_id="F1", reduced_article="B1"),
        MemberArticle(id="m2", article_id="a2", family_id="F1", reduced_article="B2"),
    ])
    snap = Snapshot(id="D2", articles=[a1, a2], options=[frame, base],
                    engineering=Engineering(families=[fam]))
    snap.option_option_dependencies = {
        "ff_g1": ["bf_g1", "bf_l7"],
        "ff_zm": ["bf_l7"],
    }
    snap.product_option_value_ids = {
        "P1": ["ff_g1", "bf_g1", "bf_l7"],
        "P2": ["ff_zm", "bf_l7"],
    }
    svc = ApplicationContext().engineering_value_table_service
    tables = svc.build_dependency_tables(snap)
    assert len(tables) == 1, [t.name for t in tables]
    t = tables[0]
    assert t.property_names == [
        "COL_BAN", "COL_FRAME_FINISH", "COL_BASE_FINISH"
    ], t.property_names
    assert t.access["COL_BAN"] == "$BAN", t.access
    assert t.lines == [
        {"COL_BAN": "B1", "COL_FRAME_FINISH": "G1", "COL_BASE_FINISH": ["G1", "L7P"]},
        {"COL_BAN": "B2", "COL_FRAME_FINISH": "ZM", "COL_BASE_FINISH": "L7P"},
    ], t.lines


def _check_persistence() -> None:
    ctx = ApplicationContext()
    svc = ctx.engineering_value_table_service
    snap = _make_dep_snapshot()

    # ensure_value_tables stores the tables AND emits a Type-4 constraint.
    tables = svc.ensure_value_tables(snap)
    assert len(tables) == 1 and snap.value_tables == tables, "not stored"
    constraint = {r.name: r for r in snap.relation_objects}.get("C_FRAME_FINISH")
    assert constraint is not None, [r.name for r in snap.relation_objects]
    assert constraint.type_code == "4" and constraint.domain == "C"
    assert constraint.body.startswith("Objects:"), constraint.body
    # Idempotent: a second ensure does not duplicate the constraint.
    svc.ensure_value_tables(snap)
    assert sum(1 for r in snap.relation_objects if r.name == "C_FRAME_FINISH") == 1

    # JSON round-trip preserves the tables, including the Base finish value set.
    restored = snapshot_from_dict(snapshot_to_dict(snap))
    assert len(restored.value_tables) == 1, restored.value_tables
    rt = restored.value_tables[0]
    assert rt.name == "frame_finish"
    assert rt.property_names == [
        "COL_FRAME_FINISH", "COL_ARMPAD_FINISH", "COL_BASE_FINISH"
    ]
    assert rt.lines[0]["COL_BASE_FINISH"] == ["G1", "L7P"], rt.lines[0]
    assert {r.name for r in restored.relation_objects} >= {"C_FRAME_FINISH"}




if __name__ == "__main__":
    main()
