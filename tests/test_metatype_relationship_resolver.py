"""Metatype relationship resolver: real-format families loaded through the table loader."""
import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

import services.metatype.metatype_relationship_resolver as resolver_module
from core.application_context import ApplicationContext
from core.config import AppConfig
from models.metatype_relationships import DuplicateStatus, RelationshipStatus, ReportStatus
from models.metatype_tables import LoadStatus, MetatypeFamilyTables, TableLoadState
from services.metatype.metatype_relationship_resolver import MetatypeRelationshipResolver
from services.metatype.metatype_table_loader import MetatypeTableLoader
from services.metatype.relationship_specs import DUPLICATES, RELATIONSHIPS

# Column names exactly as mt.inp_descr declares them (go_children shortened to the columns used).
COLUMNS = {
    "go_types": "id name format default mode filter",
    "go_articles": "id manufacturer program article_nr prm_key chprm_key",
    "go_properties": "id key name value variant_code variant_value",
    "go_noproperties": "key name",
    "go_childprops": "key name value child_key",
    "go_children": "child_key manufacturer program article_nr variant condition",
    "go_actions": "id own_key foreign_key direction condition action param_1 param_2 text",
    "go_propvalues": "id name value condition",
    "go_propclasses": "id prop_name prop_class",
    "go_setup": "id key value",
    "go_classes": "id class",
    "go_attpt": "id key direction condition",
}


def schema(tables=COLUMNS) -> str:
    text = "# GO III (MT) Input Description, Version 1.16\nname    go_tables\n\n"
    for table, columns in tables.items():
        names = columns.split()
        text += f"table   {table}\t{table}.csv\t\tcsv\nfields  {len(names)}\n"
        text += "".join(f"field   {i}  {n}\t\tvstring\t\tdelim ; trim\n" for i, n in enumerate(names, 1))
        text += "\n"
    return text


# A small but complete consistent family (same shapes as Verus/Atlas data).
GOOD = {
    "go_types": (
        "MT_X ;GX_Type   ;ch ;@A ;131 ;\r\n"
        "MT_X ;GX_Head   ;ch ;@N ;11  ;\r\n"
        "MT_X ;GWidth    ;na ;800 ;2049;GX_Head,CHILD_PROP\r\n"       # na: filter may name child props
        "MT_X ;GHeight   ;i  ;700 ;1   ;GX_Type\r\n"
        "MT_Y ;GY_Type   ;ch ;@A ;131 ;\r\n"
    ),
    "go_articles": (
        "# articles\r\n"
        "MT_X ;hmx ;x ;PIA1Z ;SET_1 ;CHP_X\r\n"
        "MT_X ;hmx ;x ;PIA2Z ;SET_2 ;CHP_X, CHP_Z\r\n"
        "MT_Y ;hmx ;x ;PIA3Z ;SET_3 ;\r\n"
        "_native_ ;hmx ;x ;NAT ;SET_1 ;\r\n"
    ),
    "go_properties": "MT_X;SET_1;GX_Type;A;;\r\nMT_X;SET_2;GX_Type;B;;\r\nMT_Y;SET_3;GY_Type;A;;\r\n",
    "go_childprops": "CHP_X;GX_Head;YES;CH_A\r\nCHP_X;GX_Head;NO;\r\nCHP_Z;GX_Head;YES;CH_A,CH_B\r\n",
    "go_children": "CH_A;hmx;x;PIA5Y;;GX_Type==@A\r\nCH_A;hmx;x;PIA5Y;;GX_Type==@B\r\nCH_B;hmx;x;PIA6Y;;\r\n",
    "go_actions": (
        "MT_X;GX_Type;;CON;GX_Type==@B;CON_PROP;GX_Head;0;\r\n"
        "MT_X;GX_Type;CH_A,CH_B;CON;;SET_PROP;GX_Head;@N;\r\n"
        "MT_X;GX_Head;CH_A;CON;;CON_CH_PROP;GCHILD_Only;2;\r\n"       # child property: not checked
        "MT_X;;;CH_ADD;;CH_PROP;GCHILD_Other;1;\r\n"
        "MT_X;;;CREATE;;ADD_CHILD;LINK1;CH_A;\r\n"
    ),
    "go_propvalues": "MT_X;GX_Type;A;GX_Head==@N\r\n",
    "go_propclasses": "MT_X;GX_Type;PC_X\r\n;GWidth;PC_ANY\r\nMT_Y;GY_Type;PC_X\r\n",
    "go_setup": "MT_X;NoMTOrderRep;1\r\n",
    "go_classes": "*;::hmx::x::Base\r\nMT_X;::hmx::x::Special\r\n",
    "go_attpt": "MT_X;AP_L;L;\r\n",
    "go_noproperties": "",
}


def build(root: Path, name="fam", files=None, tables=COLUMNS, loader=None) -> MetatypeFamilyTables:
    data = root / name / "1"
    data.mkdir(parents=True, exist_ok=True)
    (data / "mt.inp_descr").write_text(schema(tables), encoding="utf-8")
    content = dict(GOOD)
    content.update(files or {})
    for table in tables:
        value = content.get(table, "")
        if value is None:
            continue
        (data / f"{table}.csv").write_bytes(value if isinstance(value, bytes) else value.encode("utf-8"))
    return (loader or MetatypeTableLoader()).load_family(root, name)


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "hmx"
    path.mkdir()
    return path


def resolve(tables):
    return MetatypeRelationshipResolver().resolve(tables)


def finding(report, rule):
    items = report.findings_for(rule)
    assert items, f"no finding for {rule}"
    return items


# valid family ------------------------------------------------------------------------------
def test_consistent_family_resolves_every_reference(root):
    tables = build(root)
    assert tables.status is LoadStatus.OK
    report = resolve(tables)

    assert report.status is ReportStatus.OK and report.findings == []
    expected = {
        "articles.id->types.id": 3,                 # '_native_' is ignored
        "articles.prm_key->properties.key": 4,
        "articles.chprm_key->childprops.key": 3,    # CHP_X, CHP_X, "CHP_Z" after trimming the list
        "childprops.child_key->children.child_key": 3,
        "childprops.name->types.name": 3,
        "properties.id->types.id": 3,
        "properties.name->types.name": 3,
        "propvalues.id->types.id": 1, "propvalues.name->types.name": 1,
        "propclasses.id->types.id": 2,              # the blank id is "all metatypes", not a reference
        "propclasses.prop_name->types.name": 3,     # blank id: name must exist for some metatype
        "setup.id->types.id": 1,
        "classes.id->types.id": 1,                  # '*' is the default class
        "attpt.id->types.id": 1,
        "actions.id->types.id": 5,
        "actions.own_key->types.name": 3,
        "actions.foreign_key->children.child_key": 3,
        "actions.param_1->types.name": 2,           # CON_CH_PROP / CH_PROP address the child
        "actions.param_2->children.child_key": 1,
    }
    for rule, count in expected.items():
        result = report.relationship(rule)
        assert (result.status, result.reference_count, result.resolved_count) == (
            RelationshipStatus.RESOLVED, count, count), rule
    assert report.relationship("noproperties.key->articles.prm_key").status is RelationshipStatus.NO_REFERENCES
    assert report.relationship("articles.id->types.id").skipped_count == 1
    assert all(d.status is DuplicateStatus.UNIQUE for d in report.duplicate_checks)
    assert report.summary.unresolved == 0 and report.summary.not_checkable == 0
    assert report.table_states["go_types"] == "valid"


def test_children_child_key_may_repeat_and_is_not_a_duplicate(root):
    report = resolve(build(root))     # CH_A appears twice (conditional alternatives)
    assert report.duplicate_check("types(id,name)").status is DuplicateStatus.UNIQUE
    assert not any(d.table == "go_children" for d in report.duplicate_checks)


# broken references ------------------------------------------------------------------------------
def test_unresolved_references_are_reported_with_exact_location(root):
    files = {
        "go_articles": (
            "MT_X ;hmx ;x ;PIA1Z ;SET_1 ;CHP_X\r\n"
            "MT_NOPE ;hmx ;x ;PIA9Z ;SET_9 ;CHP_X, CHP_MISSING\r\n"        # line 2: id, prm_key, one list item
        ),
        "go_childprops": "CHP_X;GX_Head;YES;CH_A,CH_GONE\r\nCHP_X;GNoSuch;YES;\r\n",
        "go_actions": (
            "MT_X;GX_Typo;CH_NOPE;CON;;SET_PROP;GX_Nope;@N;\r\n"
            "MT_X;;;CREATE;;ADD_CHILD;L;CH_NOPE;\r\n"
        ),
        "go_propclasses": "MT_X;GX_Type;PC\r\nMT_X;GBad;PC\r\n;GNowhere;PC\r\n",
        "go_setup": "MT_UNDEFINED;NoMTOrderRep;1\r\n",
        "go_properties": "MT_X;SET_1;GX_Type;A;;\r\nMT_X;SET_1;GNotDefined;A;;\r\n",
    }
    report = resolve(build(root, files=files))
    assert report.status is ReportStatus.ISSUES

    (f,) = finding(report, "articles.id->types.id")
    assert (f.code, f.severity, f.table, f.file, f.line, f.columns, f.values) == (
        "UNRESOLVED_REFERENCE", "error", "go_articles", "go_articles.csv", 2, ("id",), ("MT_NOPE ",))
    assert not f.uncertain and "line 2" in f.message
    assert [x.values for x in finding(report, "articles.prm_key->properties.key")] == [("SET_9 ",)]
    assert finding(report, "articles.prm_key->properties.key")[0].severity == "warning"   # observed rule
    (chp,) = finding(report, "articles.chprm_key->childprops.key")
    assert chp.values == ("CHP_X, CHP_MISSING",) and chp.reference == ("CHP_MISSING",) and chp.line == 2
    assert [x.line for x in finding(report, "childprops.child_key->children.child_key")] == [1]
    assert [x.values for x in finding(report, "childprops.name->types.name")] == [("CHP_X", "GNoSuch")]
    assert [x.values for x in finding(report, "actions.own_key->types.name")] == [("MT_X", "GX_Typo")]
    (fk,) = finding(report, "actions.foreign_key->children.child_key")
    assert fk.values == ("CH_NOPE",) and fk.reference == ("CH_NOPE",)
    assert [x.values for x in finding(report, "actions.param_1->types.name")] == [("MT_X", "GX_Nope")]
    assert [x.values for x in finding(report, "actions.param_2->children.child_key")] == [("CH_NOPE",)]
    assert [x.values for x in finding(report, "propclasses.prop_name->types.name")] == [
        ("MT_X", "GBad"), ("", "GNowhere")]
    assert [x.values for x in finding(report, "setup.id->types.id")] == [("MT_UNDEFINED",)]
    assert [x.line for x in finding(report, "properties.name->types.name")] == [2]
    result = report.relationship("articles.chprm_key->childprops.key")
    assert (result.status, result.reference_count, result.resolved_count, result.unresolved_count) == (
        RelationshipStatus.UNRESOLVED, 3, 2, 1)
    assert report.summary.unresolved_references == sum(r.unresolved_count for r in report.relationships)


def test_filter_on_non_na_property_must_name_own_properties(root):
    files = {"go_types": "MT_X;GA;ch;@A;1;GB,GMissing\r\nMT_X;GB;ch;@A;1;\r\nMT_X;GN;na;1;1;ChildOnly\r\n"}
    report = resolve(build(root, files=files))
    (f,) = finding(report, "types.filter->types.name")
    assert f.values == ("MT_X", "GB,GMissing") and f.reference == ("MT_X", "GMissing") and f.severity == "warning"
    assert report.relationship("types.filter->types.name").reference_count == 2     # na row excluded


def test_childprops_property_is_scoped_to_the_owning_metatype(root):
    files = {
        "go_types": "MT_X;GX;ch;@A;1;\r\nMT_Y;GY;ch;@A;1;\r\n",
        "go_articles": "MT_X;h;x;A1;S1;CP_X\r\nMT_Y;h;x;A2;S2;CP_Y\r\n",
        "go_childprops": "CP_X;GX;1;\r\nCP_X;GY;1;\r\nCP_UNUSED;GZ;1;\r\nCP_Y;GY;1;\r\n",
    }
    report = resolve(build(root, files=files))
    result = report.relationship("childprops.name->types.name")
    assert (result.reference_count, result.resolved_count, result.unresolved_count, result.skipped_count) == (3, 2, 1, 1)
    (f,) = finding(report, "childprops.name->types.name")       # GY belongs to MT_Y, not to CP_X's owner MT_X
    assert f.values == ("CP_X", "GY") and "MT_X" in f.message


# duplicates ----------------------------------------------------------------------------------------
def test_duplicate_keys_are_reported_with_all_lines(root):
    files = {
        "go_types": "MT_X;GA;ch;@A;1;\r\nMT_X;GB;ch;@A;1;\r\nMT_X;GA;ch;@B;1;\r\nMT_X;GA;ch;@C;1;\r\n",
        "go_properties": "MT_X;S;GA;1;;\r\nMT_X;S;GA;2;;\r\nMT_X;S;GB;1;;\r\n",
        "go_childprops": "# c\r\nC;GA;V;K\r\nC;GA;V;K\r\n",
    }
    report = resolve(build(root, files=files))
    assert report.status is ReportStatus.ISSUES

    types = report.duplicate_check("types(id,name)")
    assert (types.status, types.row_count, types.duplicate_groups, types.extra_rows) == (
        DuplicateStatus.DUPLICATES, 4, 1, 2)
    (f,) = finding(report, "types(id,name)")
    assert (f.code, f.severity, f.line, f.related_lines, f.values) == ("DUPLICATE_KEY", "error", 1, [3, 4], ("MT_X", "GA"))
    assert "lines 1, 3, 4" in f.message
    (p,) = finding(report, "properties(id,key,name)")
    assert (p.line, p.related_lines, p.severity) == (1, [2], "warning")
    (c,) = finding(report, "childprops(key,name,value)")
    assert (c.line, c.related_lines) == (2, [3])      # source line numbers count the comment line
    assert report.duplicate_check("setup(id,key)").status is DuplicateStatus.UNIQUE


# empty tables ----------------------------------------------------------------------------------------
def test_empty_and_comment_only_tables_have_nothing_to_check(root):
    files = {name: "" for name in COLUMNS}
    files["go_children"] = "# only a header\r\n\r\n"
    tables = build(root, files=files)
    assert tables.table("go_children").state is TableLoadState.NO_DATA
    report = resolve(tables)

    assert report.status is ReportStatus.OK and report.findings == []
    assert all(r.status is RelationshipStatus.NO_REFERENCES for r in report.relationships)
    assert report.relationship("articles.id->types.id").reason == "go_articles.csv holds no data rows"
    assert all(d.status is DuplicateStatus.UNIQUE and d.row_count == 0 for d in report.duplicate_checks)


def test_references_into_an_empty_target_are_unresolved_not_skipped(root):
    report = resolve(build(root, files={"go_types": ""}))
    result = report.relationship("articles.id->types.id")
    assert result.status is RelationshipStatus.UNRESOLVED and result.unresolved_count == 3
    assert report.status is ReportStatus.ISSUES


# partial loads ----------------------------------------------------------------------------------------
def test_undecodable_source_table_cannot_be_checked(root):
    tables = build(root, files={"go_properties": b"MT_X;SET_1;G\xfcX;1;;\r\n"})
    assert tables.table("go_properties").state is TableLoadState.DECODE_ERROR
    report = resolve(tables)

    for rule in ("properties.id->types.id", "properties.name->types.name"):
        r = report.relationship(rule)
        assert r.status is RelationshipStatus.NOT_CHECKABLE and r.reason == "go_properties.csv is decode_error"
    # A rule that needs go_properties as its TARGET also cannot run, because the articles carry references.
    r = report.relationship("articles.prm_key->properties.key")
    assert r.status is RelationshipStatus.NOT_CHECKABLE and "decode_error" in r.reason
    assert report.duplicate_check("properties(id,key,name)").status is DuplicateStatus.NOT_CHECKABLE
    assert report.status is ReportStatus.INCOMPLETE and report.summary.not_checkable == 3
    assert report.findings == []                       # nothing is claimed about unreadable data


def test_missing_target_file_is_not_checkable_only_when_there_are_references(root):
    report = resolve(build(root, files={"go_childprops": None, "go_children": None}))
    assert report.relationship("articles.chprm_key->childprops.key").reason == "go_childprops.csv is missing"
    assert report.relationship("childprops.child_key->children.child_key").status is RelationshipStatus.NOT_CHECKABLE
    assert report.relationship("actions.foreign_key->children.child_key").status is RelationshipStatus.NOT_CHECKABLE
    assert report.status is ReportStatus.INCOMPLETE


def test_empty_source_is_not_blocked_by_an_unreadable_target(root):
    files = {"go_attpt": "", "go_types": b"MT_X;G\xfc;ch;@A;1;\r\n"}
    report = resolve(build(root, files=files))
    assert report.relationship("attpt.id->types.id").status is RelationshipStatus.NO_REFERENCES
    assert report.relationship("articles.id->types.id").status is RelationshipStatus.NOT_CHECKABLE


def test_partly_loaded_target_makes_findings_uncertain(root):
    files = {"go_types": GOOD["go_types"] + "TRUNCATED\r\n"}                  # one-field line: rejected by the loader
    tables = build(root, files=files)
    assert tables.table("go_types").state is TableLoadState.MALFORMED
    report = resolve(tables)
    assert tables.status is LoadStatus.PARTIAL and any("problems" in m for m in report.messages)
    assert report.status is ReportStatus.INCOMPLETE                            # nothing unresolved, but partial data used
    assert "go_types" in report.relationship("articles.id->types.id").partial_tables

    broken = {"go_types": GOOD["go_types"].replace("MT_Y ;GY_Type", "MT_Z ;GY_Type") + "TRUNCATED\r\n"}
    report = resolve(build(root, name="fam2", files=broken))
    f = finding(report, "articles.id->types.id")[0]
    assert f.values == ("MT_Y ",) and f.uncertain and "partly loaded" in f.message
    assert report.status is ReportStatus.ISSUES


def test_malformed_source_with_clean_references_is_incomplete(root):
    tables = build(root, files={"go_setup": "MT_X;NoMTOrderRep;1\r\nBROKEN\r\n"})
    report = resolve(tables)
    assert report.relationship("setup.id->types.id").status is RelationshipStatus.RESOLVED
    assert report.relationship("setup.id->types.id").partial_tables == ["go_setup"]
    assert report.status is ReportStatus.INCOMPLETE


def test_table_not_declared_or_column_missing_is_not_checkable(root):
    smaller = {k: v for k, v in COLUMNS.items() if k != "go_setup"}
    report = resolve(build(root, tables=smaller))
    r = report.relationship("setup.id->types.id")
    assert r.status is RelationshipStatus.NOT_CHECKABLE and r.reason == "go_setup is not declared by mt.inp_descr"
    assert report.duplicate_check("setup(id,key)").reason == "go_setup is not declared by mt.inp_descr"

    renamed = dict(COLUMNS, go_setup="ident key value")
    report = resolve(build(root, name="fam2", tables=renamed))
    assert report.relationship("setup.id->types.id").reason == "go_setup.csv has no column id"


def test_failed_load_gives_a_failed_report(root):
    tables = MetatypeTableLoader().load_family(root, "nope")
    report = resolve(tables)
    assert tables.status is LoadStatus.FAILED and report.status is ReportStatus.FAILED
    assert report.messages and "FAMILY_NOT_FOUND" in report.messages[0]
    assert report.relationships == [] and report.findings == []


# misc -------------------------------------------------------------------------------------------------------------
def test_finding_lists_are_capped_but_counts_stay_exact(root, monkeypatch):
    monkeypatch.setattr(resolver_module, "MAX_FINDINGS_PER_RULE", 2)
    articles = "".join(f"MT_BAD{i};h;x;A{i};SET_1;\r\n" for i in range(5))
    report = resolve(build(root, files={"go_articles": articles}))
    result = report.relationship("articles.id->types.id")
    assert result.unresolved_count == 5 and result.findings_truncated
    assert len(report.findings_for("articles.id->types.id")) == 2


def test_report_serialises_to_json(root):
    report = resolve(build(root, files={"go_setup": "MT_UNDEFINED;K;1\r\n"}))
    document = json.loads(json.dumps(report.to_dict()))
    assert document["status"] == "issues" and document["findings"][0]["code"] == "UNRESOLVED_REFERENCE"
    assert document["relationships"][0]["status"] in {"resolved", "unresolved", "no_references", "not_checkable"}
    assert document["findings"][0]["values"] == ["MT_UNDEFINED"]


def test_resolver_is_pure_and_repeatable(root):
    tables = build(root)
    source = Path(resolver_module.__file__).read_text(encoding="utf-8")
    for forbidden in ("open(", "os.", "pathlib", "subprocess", "shutil"):
        assert forbidden not in source
    first, second = resolve(tables).to_dict(), resolve(tables).to_dict()
    first.pop("resolved_at"), second.pop("resolved_at")
    assert first == second


def test_rule_catalogue_is_consistent():
    ids = [r.id for r in RELATIONSHIPS] + [d.id for d in DUPLICATES]
    assert len(ids) == len(set(ids))
    for spec in RELATIONSHIPS:
        assert spec.basis in {"documented", "observed"} and spec.severity in {"error", "warning"}
        assert spec.note
        for table, columns in ((spec.source_table, spec.source_columns), (spec.target_table, spec.target_columns)):
            assert table in COLUMNS or table == "go_types"
            assert set(columns) <= set(COLUMNS[table].split()), (spec.id, table, columns)
        assert len(spec.source_columns) == len(spec.target_columns) or spec.custom
    for dup in DUPLICATES:
        assert set(dup.key_columns) <= set(COLUMNS[dup.table].split()), dup.id
        assert dup.basis in {"documented", "inferred"}


# integration with the Metatype module --------------------------------------------------------------------------------
def test_service_resolves_a_family_through_the_context(root):
    build(root, "fam", files={"go_setup": "MT_UNDEFINED;K;1\r\n"})
    context = ApplicationContext(AppConfig(metatype_repository_root=str(root)))
    service = context.metatype_relationship_service

    assert service is context.metatype_relationship_service and service.last_result is None
    report = service.resolve_family("fam")
    assert report.status is ReportStatus.ISSUES and service.last_result is report
    assert context.metatype_table_loader_service.last_result.family_id == "fam"
    text = service.summary_text(report)
    assert "UNRESOLVED setup.id->types.id: 1 of 1" in text and "issues" in text
    assert service.resolve_family("nope").status is ReportStatus.FAILED
    assert "failed" in service.summary_text(service.last_result)


def test_page_resolves_the_selected_product_family(root):
    from PySide6.QtWidgets import QApplication
    from ui.pages.metatype_repository_page import MetatypeRepositoryPage

    app = QApplication.instance() or QApplication([])
    build(root, "fam")
    page = MetatypeRepositoryPage(ApplicationContext(AppConfig(metatype_repository_root=str(root))))
    page.scan_button.click()
    assert not page.resolve_button.isEnabled()
    page.table.selectRow(0)
    assert page.resolve_button.isEnabled()
    page.resolve_button.click()
    text = page.load_output.toPlainText()
    assert "Tables of fam/1" in text and "Relationships of fam/1 - ok" in text
    app.processEvents()
