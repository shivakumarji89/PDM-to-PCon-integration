"""Maintenance → Pricing Relation → Article VARCOND Relations.

Covers the cached, legacy-faithful incremental source
(``services.maintenance_varcond_service``) and the Maintenance-only gate in the
Pricing Relation panel. PDM is faked throughout; no live connection is needed.

Fixture data for the three relations (``PA_GESCRNNP/S/U.105508F``) was captured
read-only from live PDM (2026-10-27): BOM + FeaturePositionString from
``ItemComponents`` and ``PDMOptionDataReportWithIncBase @siteId=1,
@excludeFabricColours=1`` per component. Legacy site/exclusion constants were read
from the compiled ``PriceMaintenance.getOptionIncrementSuffixes`` IL.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from services.maintenance_varcond_service import (
    LEGACY_EXCLUDE_FABRIC_COLOURS,
    LEGACY_SITE_ID,
    MaintenanceVarCondService,
    ParentSource,
)
from services.varcond_service import VarCondResult, VarCondService

ATTRS = [
    ("Application", "U"), ("Height", "1055"), ("Width", "08"), ("Material", "F"),
]
# Procedure rows with an increment for GESNNU/GESNNS option 8: one row per
# fabric-type value, all named "Fabric type" -> a single rule after name de-dup.
FABRIC_ROWS = [(8, "Fabric type")] * 13


def _attrs(app: str):
    return [("Application", app)] + ATTRS[1:]


def _source(parent, comps, increments, app):
    return ParentSource(
        parent=parent,
        components=[(c, q, str(i + 1), "") for i, (c, q) in enumerate(comps)],
        attributes=_attrs(app),
        increments=increments,
    )


SOURCES = {
    "GESCRNNP.105508F": _source(
        "GESCRNNP.105508F", [("GESNNU.105508F", 1), ("GESY.", 1)],
        {"GESNNU.105508F": FABRIC_ROWS, "GESY.": []}, "P"),
    "GESCRNNS.105508F": _source(
        "GESCRNNS.105508F", [("GESNNS.105508F", 1), ("GESG.", 2), ("GEST.", 1)],
        {"GESNNS.105508F": FABRIC_ROWS, "GESG.": [], "GEST.": []}, "S"),
    "GESCRNNU.105508F": _source(
        "GESCRNNU.105508F", [("GESNNU.105508F", 1), ("GESG.", 2), ("GESU.", 1)],
        {"GESNNU.105508F": FABRIC_ROWS, "GESG.": [], "GESU.": []}, "U"),
}


def _service():
    calls = []

    def loader(codes):
        calls.append(list(codes))
        return {c: SOURCES[c] for c in codes if c in SOURCES}

    svc = MaintenanceVarCondService(loader=loader)
    return svc, calls


def _body(app):
    return (f"IF Application = '{app}' AND Height = '1055' "
            "AND Width = '08' AND Material = 'F'")


EXPECTED = {
    "GESCRNNP.105508F": [
        f"$VARCOND = 'GESNNU.105508F' {_body('P')}",
        f"$VARCOND = 'GESNNU.105508F 8=' + Fabric_Type {_body('P')}",
        f"$VARCOND = 'GESY.' {_body('P')}",
    ],
    "GESCRNNS.105508F": [
        f"$VARCOND = 'GESNNS.105508F' {_body('S')}",
        f"$VARCOND = 'GESNNS.105508F 8=' + Fabric_Type {_body('S')}",
        f"$VARCOND = 'GESG.' {_body('S')}",
        f"$SET_PRICING_FACTOR('GESG.', 2) {_body('S')}",
        f"$VARCOND = 'GEST.' {_body('S')}",
    ],
    "GESCRNNU.105508F": [
        f"$VARCOND = 'GESNNU.105508F' {_body('U')}",
        f"$VARCOND = 'GESNNU.105508F 8=' + Fabric_Type {_body('U')}",
        f"$VARCOND = 'GESG.' {_body('U')}",
        f"$SET_PRICING_FACTOR('GESG.', 2) {_body('U')}",
        f"$VARCOND = 'GESU.' {_body('U')}",
    ],
}


# -- the three reproduced relations -----------------------------------------
@pytest.mark.parametrize("parent", sorted(EXPECTED))
def test_three_relations_match_captured_legacy_source_output(parent):
    svc, _ = _service()
    result = svc.generate([parent])
    assert [r.rule for r in result.rules] == EXPECTED[parent]
    assert result.text == ",\r\n".join(EXPECTED[parent]) + "\r\n"


def test_fabric_type_incremental_is_concatenation_rule_deduped_by_name():
    svc, _ = _service()
    rules = [r.rule for r in svc.generate(["GESCRNNU.105508F"]).rules]
    incremental = [r for r in rules if "8=' +" in r]
    assert len(incremental) == 1          # 13 procedure rows, one property name
    assert incremental[0].startswith("$VARCOND = 'GESNNU.105508F 8=' + Fabric_Type IF ")
    # components without an increment get no suffix rule
    assert not any("'GESU. " in r or "'GESG. " in r for r in rules)


def test_non_incremental_rules_unchanged_and_in_legacy_order():
    svc, _ = _service()
    rules = [r.rule for r in svc.generate(["GESCRNNU.105508F"]).rules]
    # base, (incremental), pricing factor, next component - never reordered
    assert rules[0].startswith("$VARCOND = 'GESNNU.105508F' IF")
    assert rules[2].startswith("$VARCOND = 'GESG.' IF")
    assert rules[3].startswith("$SET_PRICING_FACTOR('GESG.', 2) IF")
    assert rules[4].startswith("$VARCOND = 'GESU.' IF")


def test_quantity_factor_applies_to_incremental_rule():
    src = _source("P1", [("ABC.1F", 3)], {"ABC.1F": [(8, "Fabric type")]}, "U")
    svc = MaintenanceVarCondService(loader=lambda codes: {"P1": src})
    rules = [r.rule for r in svc.generate(["P1"]).rules]
    assert rules[1].startswith("$SET_PRICING_FACTOR('ABC.1F', 3) IF")
    assert rules[2].startswith("$VARCOND = 'ABC.1F 8=' + Fabric_Type IF")
    assert rules[3].startswith("$SET_PRICING_FACTOR('ABC.1F 8=' + Fabric_Type, 3) IF")


def test_hz13_fabric_rename_and_multiple_options_keep_first_seen_order():
    src = _source(
        "P1", [("HZ13.X", 1)],
        {"HZ13.X": [(8, "Fabric type"), (3344, "Internal fabric type")]}, "U")
    svc = MaintenanceVarCondService(loader=lambda codes: {"P1": src})
    rules = [r.rule for r in svc.generate(["P1"]).rules]
    # both names are fabric -> renamed identically -> de-duplicated to the first
    assert len([r for r in rules if "=' +" in r]) == 1
    assert "'HZ13.X 8=' + Upper_Front_Fabric_Type" in rules[1]
    src2 = _source("P2", [("ABC.1", 1)],
                   {"ABC.1": [(8, "Fabric type"), (9728, "Trim finish")]}, "U")
    svc2 = MaintenanceVarCondService(loader=lambda codes: {"P2": src2})
    names = [r.rule.split("' + ")[1].split(" ")[0]
             for r in svc2.generate(["P2"]).rules if "=' +" in r.rule]
    assert names == ["Fabric_Type", "Trim_Finish"]


# -- exclusion / substitution keep valid incremental rules -------------------
def test_property_exclusion_keeps_incremental_rule():
    svc, _ = _service()
    result = svc.generate(["GESCRNNU.105508F"], property_exclusions="Height,Width")
    rules = [r.rule for r in result.rules]
    assert len(rules) == 5
    assert rules[1] == (
        "$VARCOND = 'GESNNU.105508F 8=' + Fabric_Type "
        "IF Application = 'U' AND Material = 'F'")
    assert result.excluded == ["Height", "Width"]


def test_substitution_applies_to_properties_and_incremental_name():
    svc, _ = _service()
    rules = [r.rule for r in svc.generate(
        ["GESCRNNU.105508F"],
        property_substitutions="Fabric_Type=Fabric_Kind,Material=Mat").rules]
    assert rules[1] == (
        "$VARCOND = 'GESNNU.105508F 8=' + Fabric_Kind "
        "IF Application = 'U' AND Height = '1055' AND Width = '08' AND Mat = 'F'")


def test_prefix_applies_to_if_properties_only():
    svc, _ = _service()
    rules = [r.rule for r in svc.generate(["GESCRNNU.105508F"], prefix="Cls").rules]
    assert "+ Fabric_Type IF Cls.Application = 'U'" in rules[1]


# -- cache: no repeated PDM reads, correct invalidation ----------------------
def test_edits_do_not_reread_pdm_and_start_from_original_data():
    svc, calls = _service()
    first = svc.generate(["GESCRNNU.105508F"]).text
    svc.generate(["GESCRNNU.105508F"], property_exclusions="Height")
    svc.generate(["GESCRNNU.105508F"], property_substitutions="Material=Mat")
    svc.generate(["GESCRNNU.105508F"], prefix="Cls")
    again = svc.generate(["GESCRNNU.105508F"]).text
    assert len(calls) == 1 and svc.load_count == 1
    assert again == first                  # edits never mutated the cached rows


def test_new_selection_loads_only_missing_parents():
    svc, calls = _service()
    svc.generate(["GESCRNNU.105508F"])
    svc.generate(["GESCRNNU.105508F", "GESCRNNP.105508F"])
    svc.generate(["GESCRNNP.105508F"])
    assert calls == [["GESCRNNU.105508F"], ["GESCRNNP.105508F"]]


def test_explicit_refresh_reloads_and_clear_cache_replaces_dataset():
    svc, calls = _service()
    svc.generate(["GESCRNNU.105508F"])
    svc.generate(["GESCRNNU.105508F"], refresh=True)
    assert len(calls) == 2
    svc.clear_cache()
    svc.generate(["GESCRNNU.105508F"])
    assert len(calls) == 3


def test_unknown_parent_is_reported_not_silently_cached_as_found():
    svc, _ = _service()
    result = svc.generate(["NOPE"])
    assert result.rules == [] and result.text == ""


# -- legacy source access (fake DB) -------------------------------------------
class _Row:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class _FakeRepo:
    def __init__(self, items=(), parents=()):
        self.items, self.parents, self.sql = list(items), list(parents), []

    def _execute(self, sql, params=(), connection=None):
        self.sql.append((sql, params))
        if "LIKE ?" in sql:
            return [_Row(Item=i) for i in self.items[:1]]
        return [_Row(Item=i) for i in self.parents]


@pytest.mark.parametrize("code,items,parents,expected,queried", [
    ("GESNNU.105508F", ["X"], ["P"], "GESNNU.105508F", False),   # dotted: unchanged
    ("GESG.", [], [], "GESG.", True),                            # trailing dot, no F match
    ("GESG", ["GESG.1F"], [], "GESG.1F", True),                  # dotless -> LIKE '%F'
    ("GESG", ["GESG.1F"], [], "GESG.1F", True),
    ("ABCF", ["Z"], [], "ABCF", False),                          # ends in F: skip
    ("METX", ["Z"], [], "METX", False),                          # starts with MET: skip
    ("AB-1.2", [], ["P1", "P2"], "P2", False),                   # '-' -> last parent
])
def test_legacy_item_resolution(code, items, parents, expected, queried):
    repo = _FakeRepo(items, parents)
    assert MaintenanceVarCondService._resolve_item(repo, None, code) == expected
    assert any("LIKE ?" in s for s, _ in repo.sql) is queried


class _FakeCursor:
    """Emulates the procedure: row-count result sets first, data set last."""

    def __init__(self, rows):
        self._rows, self.description, self.executed, self._stage = rows, None, None, 0

    def execute(self, sql, params):
        self.executed = (sql, params)
        self.description = None
        self._stage = 0

    def nextset(self):
        self._stage += 1
        if self._stage == 1:
            self.description = [("Other",)]
            return True
        if self._stage == 2:
            self.description = [(n,) for n in
                                ("OptionId", "Option2", "IncPriceBase", "Component")]
            return True
        return False

    def fetchall(self):
        return self._rows

    def close(self):
        pass


class _FakeConn:
    def __init__(self, rows):
        self.cur = _FakeCursor(rows)

    def cursor(self):
        return self.cur


def test_procedure_uses_legacy_constants_and_advances_to_incpricebase_set():
    rows = [
        (8, "Fabric type", 58, "GESNNU.105508F"),
        (8, "Fabric type", None, "GESNNU.105508F"),     # no increment -> dropped
        (9728, "Trim Finish", None, "GESU."),
        (28, "Fabric colour", "", "GESNNU.105508F"),   # empty increment -> dropped
    ]
    conn = _FakeConn(rows)
    svc = MaintenanceVarCondService(loader=lambda c: {})
    out = svc._fetch_increments(_FakeRepo(), conn, "GESNNU.105508F")
    sql, params = conn.cur.executed
    assert "PDMOptionDataReportWithIncBase" in sql
    assert params == (
        "GESNNU.105508F", LEGACY_SITE_ID, LEGACY_EXCLUDE_FABRIC_COLOURS)
    assert (LEGACY_SITE_ID, LEGACY_EXCLUDE_FABRIC_COLOURS) == (1, 1)
    assert out == [(8, "Fabric type")]


def test_procedure_without_incpricebase_result_set_yields_no_rules():
    class _NoData(_FakeCursor):
        def nextset(self):
            return False

    conn = _FakeConn([])
    conn.cur = _NoData([])
    svc = MaintenanceVarCondService(loader=lambda c: {})
    assert svc._fetch_increments(_FakeRepo(), conn, "X.1") == []


# -- Maintenance-only gate in the Pricing Relation panel ---------------------
def _gui():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _context_with_bom():
    from core.application_context import ApplicationContext
    from models.article import Article
    from models.snapshot import Snapshot

    snap = Snapshot()
    snap.metadata.source = "PDM"
    snap.articles = [Article(id="1", code="GESCRNNU.105508F")]
    snap.article_components = {"1": [{"sub_item": "GESNNU.105508F", "quantity": 1}]}
    ctx = ApplicationContext()
    ctx.register_pdm_snapshot(snap)
    ctx.activate_snapshot_source("pdm")
    return ctx


def _panel_page(module, monkeypatch):
    from core.modules import WorkbenchModule
    from ui.pages.pricing_relation_page import PricingRelationPage

    _gui()
    live_calls = []

    def fake_live(self, article_codes, **kw):
        live_calls.append((list(article_codes), kw))
        return VarCondResult()

    monkeypatch.setattr(VarCondService, "generate_live", fake_live)
    loads = []

    def fake_load(self, codes):
        loads.append(list(codes))
        return {c: SOURCES[c] for c in codes if c in SOURCES}

    monkeypatch.setattr(MaintenanceVarCondService, "_load_live", fake_load)
    page = PricingRelationPage(_context_with_bom())
    page._active_module = module
    live_calls.clear()
    loads.clear()
    page.on_enter()
    return page, live_calls, loads


def _select_relation(page):
    """Select the first relation the way a user does and wait for any PDM load.

    Opening the workflow only builds the local relation list; generation (and the
    Maintenance background PDM read) starts on selection.
    """
    panel = page._varcond_panel
    if panel._relations.currentRow() == 0:
        # Already selected (list rebuilt with the selection kept): no change signal.
        panel._generate_selected()
    else:
        panel._relations.setCurrentRow(0)
    _wait_for_load(panel)


def _wait_for_load(panel):
    import time
    from PySide6.QtWidgets import QApplication

    deadline = time.monotonic() + 10
    while panel._maintenance_load_task is not None:
        assert time.monotonic() < deadline, "Maintenance PDM load did not finish"
        QApplication.processEvents()
        time.sleep(0.01)
    QApplication.processEvents()


def test_development_keeps_generate_live_and_never_uses_maintenance_service(monkeypatch):
    from core.modules import WorkbenchModule

    page, live_calls, loads = _panel_page(WorkbenchModule.DEVELOPMENT, monkeypatch)
    panel = page._varcond_panel
    assert live_calls == [], "Opening the workflow must not generate until a relation is selected"
    _select_relation(page)
    assert live_calls, "Development must still call VarCondService.generate_live"
    panel._on_generate_clicked()
    assert panel._maintenance_service is None and loads == []


def test_maintenance_uses_cached_service_not_generate_live(monkeypatch):
    from core.modules import WorkbenchModule

    page, live_calls, loads = _panel_page(WorkbenchModule.MAINTENANCE, monkeypatch)
    panel = page._varcond_panel
    assert live_calls == [] and loads == [], "Opening the workflow must not read PDM"
    _select_relation(page)
    assert live_calls == [] and loads == [["GESCRNNU.105508F"]]
    assert "8=' + Fabric_Type" in panel._output.toPlainText()
    # prefix / exclusion / substitution edits are local transformations
    panel._prefix.setText("Cls")
    panel._exclusions.setText("Height")
    panel._substitutions.setText("Fabric_Type=FT")
    panel._generate_selected()
    panel._relation_length.setValue(max(1, panel._relation_length.value() - 1))
    panel._relation_length.setValue(panel._relation_length.maximum())
    assert loads == [["GESCRNNU.105508F"]] and live_calls == []
    assert "+ FT IF Cls.Application = 'U'" in panel._output.toPlainText()
    # re-entering the workspace with the same snapshot keeps the cache
    page.on_enter()
    assert len(loads) == 1
    # length changes drop the selection; reselecting is served from the cache
    _select_relation(page)
    assert len(loads) == 1
    # explicit Generate / Refresh re-reads PDM
    panel._on_generate_clicked()
    _wait_for_load(panel)
    assert len(loads) == 2


def test_maintenance_cache_replaced_when_snapshot_changes(monkeypatch):
    from core.modules import WorkbenchModule

    page, live_calls, loads = _panel_page(WorkbenchModule.MAINTENANCE, monkeypatch)
    _select_relation(page)
    assert len(loads) == 1
    ctx = page._varcond_panel._context
    new_ctx = _context_with_bom()
    ctx.register_pdm_snapshot(new_ctx.pdm_snapshot)
    ctx.activate_snapshot_source("pdm")
    page._varcond_panel.refresh_from_snapshot()
    _select_relation(page)
    assert len(loads) == 2
