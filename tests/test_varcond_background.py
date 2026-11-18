"""Phase 2 / area 3: Development VARCOND generation off the GUI thread.

* ``VarCondService.generate_live`` returns exactly what it did (golden digests taken from the original code on
  the fixed fake PDM in ``tests/varcond_fakes.py``) but asks PDM for each component prefix's option increments
  once instead of once per component occurrence.
* The relation export is split into ``prepare_relation_export`` (GUI thread) and ``build_relation_objects``
  (worker-safe); the result equals the original implementation (copied below as an oracle) and the golden
  digests, and the base codes are computed once instead of once per relation.
* The Development panel debounces the filter, coalesces repeated requests, generates on a worker thread, drops
  stale results and still shows only the selected relation's rules. The Maintenance path is untouched.
"""
from __future__ import annotations

import os
import random
import threading
import time
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QSettings, QThread, QThreadPool
from PySide6.QtWidgets import QApplication, QMessageBox

from services.varcond_service import VarCondResult, VarCondRule, VarCondService
from tests import varcond_fakes as fakes
from ui.dialogs.varcond_generation_dialog import VarCondGenerationPanel


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path):
    previous = QSettings.defaultFormat()
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path / "settings"))
    yield
    QSettings.setDefaultFormat(previous)


def pump(condition, timeout=15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        if condition():
            return True
        time.sleep(0.005)
    QCoreApplication.processEvents()
    return condition()


def on_gui_thread() -> bool:
    return QThread.currentThread() is QCoreApplication.instance().thread()


# --------------------------------------------------------------------------------------
# generate_live
# --------------------------------------------------------------------------------------
ALL = list(fakes.PARENTS)
GOLDEN_LIVE = {
    "all_parents": (dict(article_codes=ALL),
                    "62eda23c4f6f6a7ae1ac64fc9fb8b9edcbeb78641837c79196f19658818c89e8", 31, 7),
    "prefix_exclusion_substitution": (
        dict(article_codes=ALL, prefix="Cls", property_exclusions="Overall_width",
             property_substitutions="Fabric_Type=FT,Chair_type=Seat"),
        "6228ef4603f83ebbe22d00ea1dcf67db8ebd5502870142eb8015b3e7ebfb524f", 31, 7),
    "subset_unknown_and_no_bom": (
        dict(article_codes=["RYTWKRNU.220110F", "NOPE.1", "RYTWKRPU.330220F"]),
        "e09f3b411ce7ddad647670320ebd556ba75eb8793f376c823792c9858bbdbce9", 8, 3),
    "duplicated_codes": (dict(article_codes=[ALL[0], ALL[0], ALL[1], " " + ALL[1]]),
                         "ac52dbaa9e198a8216d80468c7d48f784b79ccc673bcb7255e2bb26d8fee0644", 13, 4),
}


def _live_digest(result) -> str:
    import hashlib
    import json

    blob = json.dumps({"text": result.text, "rules": [r.rule for r in result.rules],
                       "warnings": result.warnings, "excluded": result.excluded}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


@pytest.mark.parametrize("case", sorted(GOLDEN_LIVE))
def test_generate_live_output_is_unchanged_and_asks_for_each_prefix_once(monkeypatch, case):
    kwargs, digest, rule_count, increment_queries = GOLDEN_LIVE[case]
    fakes.install(monkeypatch)

    result = VarCondService(SimpleNamespace()).generate_live(**kwargs)

    assert _live_digest(result) == digest
    assert len(result.rules) == rule_count
    assert fakes.increment_queries() == increment_queries     # 13 / 13 / 3 / 6 before


def test_a_shared_increment_cache_serves_later_calls_without_queries(monkeypatch):
    fakes.install(monkeypatch)
    service = VarCondService(SimpleNamespace())
    cache = {}

    first = service.generate_live(ALL[:3], increment_cache=cache)
    asked = fakes.increment_queries()
    second = service.generate_live(ALL[:3], increment_cache=cache)

    assert fakes.increment_queries() == asked
    assert _live_digest(first) == _live_digest(second)
    assert set(cache) <= set(fakes.INCREMENTS)


def test_an_empty_increment_result_is_cached_too(monkeypatch):
    fakes.install(monkeypatch)
    cache = {}
    VarCondService(SimpleNamespace()).generate_live([ALL[1], ALL[3]], increment_cache=cache)
    assert cache["GEST."] == [] and cache["GESG."] == []
    assert fakes.increment_queries() == len(cache)


# --------------------------------------------------------------------------------------
# base codes in one pass
# --------------------------------------------------------------------------------------
def test_base_codes_from_entries_equal_base_codes_for_any_selection():
    from tests.perf_synthetic import build_class_creation_snapshot
    from core.application_context import ApplicationContext

    ctx = ApplicationContext()
    snapshot = build_class_creation_snapshot(120, structures=3, members_per_family=40)
    ctx.register_pdm_snapshot(snapshot)
    ctx.activate_snapshot_source("pdm")
    ctx.engineering_reduction_service.materialize_class_creation_article_sets(snapshot)
    xocd = ctx.xocd_export_service
    rng = random.Random(5)
    ids = [a.id for a in snapshot.articles]
    members = [m for f in snapshot.engineering.families for m in f.members]
    for member in rng.sample(members, 20):
        member.reduced_article = ""                      # exercise the fallback to the price base
    for member in rng.sample(members, 10):
        member.article_id = "ghost"

    entries = xocd.base_code_entries(snapshot)

    selections = [None, set(), set(ids), {"ghost"}] + [set(rng.sample(ids, rng.randint(1, 60))) for _ in range(40)]
    for selection in selections:
        assert xocd.base_codes_from_entries(entries, selection) == xocd._base_codes(
            snapshot, selected_article_ids=selection), selection
    assert xocd.base_codes_from_entries(entries, {int(i[1:]) for i in ids[:5]}) == xocd._base_codes(
        snapshot, selected_article_ids={int(i[1:]) for i in ids[:5]})       # ids are compared as strings


# --------------------------------------------------------------------------------------
# relation export
# --------------------------------------------------------------------------------------
GOLDEN_EXPORT = {
    "default": (None, "", "", "a79f95f4a7c406ddfb05a76284079a9bf2d44c26c8365d3168bf064d8d04aa26", 5),
    "len6_excl_subst": (6, "Overall_width", "Fabric_Type=FT",
                        "383eeeb08f2496c584508404f22d679f477f74a175a0764984833a7813c2b61c", 2),
}


def _with_price_relation_names(relations):
    """The oracle predates the naming fix: only the names differ (``PA_x`` object -> ``P_x`` / ``PA_x``)."""
    import dataclasses

    return [dataclasses.replace(r, name="P_" + r.name[3:], relation_name=r.name) for r in relations]


def _reference_relation_objects_for_export(self):
    """Verbatim copy of ``VarCondGenerationPanel.relation_objects_for_export`` before the change."""
    from models.relation_object import RelationObject

    if self._maintenance_load_task is not None:
        raise RuntimeError("Wait for PDM source loading to finish before exporting VARCOND relations.")

    parent_codes = [row[0] for row in self._article_rows]
    if not parent_codes:
        raise RuntimeError("No parent articles with BOM data are available to export.")

    if self._maintenance_check():
        service = self._ensure_maintenance_service()
        if not service.has_sources(parent_codes):
            raise RuntimeError("PDM source data is not fully loaded. Wait for all relations to finish loading.")

    length = self._relation_length.value()
    groups = {}
    for code, _label, article_id in self._article_rows:
        prefix = code[:length] if len(code) > length else code
        groups.setdefault("PA_" + prefix, []).append((code, article_id))

    relations = []
    xocd = getattr(self._context, "xocd_export_service", None)
    for order, relation_name in enumerate(sorted(groups, key=str.casefold), start=100):
        parent_rows = groups[relation_name]
        codes = [code for code, _article_id in parent_rows]
        if self._maintenance_check():
            result = self._maintenance_service.generate(
                codes, prefix="",
                property_exclusions=self._exclusions.text(),
                property_substitutions=self._substitutions.text(),
            )
        else:
            result = VarCondService(self._context).generate_live(
                article_codes=codes, prefix="",
                property_exclusions=self._exclusions.text(),
                property_substitutions=self._substitutions.text(),
            )
        body = "\r\n".join(rule.rule for rule in result.rules if rule.rule)
        if not body.strip():
            continue
        selected_ids = {article_id for _code, article_id in parent_rows}
        base_codes = (
            xocd._base_codes(self._snapshot, selected_article_ids=selected_ids)
            if xocd is not None else list(codes)
        )
        relations.append(RelationObject(
            name=relation_name, type_code="3", domain="P", order=order, body=body, article_codes=base_codes,
        ))

    if not relations:
        raise RuntimeError("No VARCOND rules were generated; nothing was exported.")
    return relations


def _panel(maintenance=False):
    context = fakes.build_context()
    return VarCondGenerationPanel(context, maintenance_check=(lambda: maintenance))


def _maintenance_panel(monkeypatch):
    """A panel in Maintenance mode that never starts the real background PDM source load.

    It is built in Development mode (so construction starts no load, no progress dialog and no worker) and
    switched afterwards; the tests then install a stand-in cached service."""
    mode = {"maintenance": False}
    context = fakes.build_context()
    panel = VarCondGenerationPanel(context, maintenance_check=lambda: mode["maintenance"])
    mode["maintenance"] = True
    return panel


@pytest.mark.parametrize("case", sorted(GOLDEN_EXPORT))
def test_relation_export_equals_the_original_and_asks_for_each_prefix_once(app, monkeypatch, case):
    length, exclusions, substitutions, digest, count = GOLDEN_EXPORT[case]
    fakes.install(monkeypatch)
    panel = _panel()
    if length is not None:
        panel._relation_length.setValue(length)
    panel._exclusions.setText(exclusions)
    panel._substitutions.setText(substitutions)

    fakes.FakeLiveRepo.calls = []
    relations = panel.relation_objects_for_export()
    shared_queries = fakes.increment_queries()
    fakes.FakeLiveRepo.calls = []
    reference = _with_price_relation_names(_reference_relation_objects_for_export(panel))

    assert fakes.relation_digest(relations) == digest and len(relations) == count
    assert fakes.relation_digest(reference) == digest
    assert shared_queries == 7                                   # one per distinct component prefix (13 before)


def test_relation_export_base_codes_are_computed_once(app, monkeypatch):
    fakes.install(monkeypatch)
    panel = _panel()
    xocd = panel._context.xocd_export_service
    calls = {"entries": 0, "per_relation": 0}
    real_entries, real_base_codes = xocd.base_code_entries, xocd._base_codes
    monkeypatch.setattr(type(xocd), "base_code_entries",
                        lambda self, snapshot: calls.__setitem__("entries", calls["entries"] + 1) or real_entries(snapshot))
    monkeypatch.setattr(type(xocd), "_base_codes",
                        lambda self, snapshot, selected_article_ids=None:
                        calls.__setitem__("per_relation", calls["per_relation"] + 1)
                        or real_base_codes(snapshot, selected_article_ids))

    relations = panel.relation_objects_for_export()

    assert len(relations) == 5 and calls == {"entries": 1, "per_relation": 0}


def test_relation_export_still_falls_back_to_the_per_relation_call_for_other_services(app, monkeypatch):
    fakes.install(monkeypatch)
    panel = _panel()
    seen = []
    fake_xocd = SimpleNamespace(
        _base_codes=lambda snapshot, selected_article_ids=None: seen.append(selected_article_ids) or ["BASE"])
    monkeypatch.setattr(type(panel._context), "xocd_export_service", property(lambda self: fake_xocd))

    relations = panel.relation_objects_for_export()

    assert len(seen) == 5 and all(r.article_codes == ["BASE"] for r in relations)


def test_relation_export_reports_the_same_user_messages(app, monkeypatch):
    fakes.install(monkeypatch)
    panel = _panel()
    panel._article_rows = []
    with pytest.raises(RuntimeError, match="No parent articles with BOM data are available to export."):
        panel.prepare_relation_export()

    panel = _panel()
    panel._maintenance_load_task = object()
    with pytest.raises(RuntimeError, match="Wait for PDM source loading to finish"):
        panel.prepare_relation_export()

    panel = _panel()
    monkeypatch.setattr(VarCondService, "generate_live", lambda self, *a, **k: VarCondResult())
    with pytest.raises(RuntimeError, match="No VARCOND rules were generated; nothing was exported."):
        panel.relation_objects_for_export()


def test_maintenance_relation_export_uses_the_cached_service_and_equals_the_original(app, monkeypatch):
    panel = _maintenance_panel(monkeypatch)

    class Service:
        def has_sources(self, codes):
            return True

        def generate(self, codes, prefix="", property_exclusions="", property_substitutions=""):
            return VarCondResult(rules=[VarCondRule(article=c, body="IF", rule=f"$VARCOND = '{c}' IF") for c in codes])

    panel._maintenance_service = Service()

    relations = panel.relation_objects_for_export()
    reference = _with_price_relation_names(_reference_relation_objects_for_export(panel))

    assert fakes.relation_digest(relations) == fakes.relation_digest(reference) and len(relations) == 5


# --------------------------------------------------------------------------------------
# the panel
# --------------------------------------------------------------------------------------
class LiveRecorder:
    """Stands in for ``generate_live``: records where it ran, optionally blocks, returns marker rules."""

    def __init__(self, monkeypatch):
        self.calls = []
        self.gates = {}                 # call number -> Event that releases it
        self.fail_with = None
        monkeypatch.setattr(VarCondService, "generate_live", self._generate)

    def _generate(self, article_codes, prefix="", property_exclusions="", property_substitutions="",
                  increment_cache=None):
        number = len(self.calls) + 1
        self.calls.append({"codes": list(article_codes), "on_gui": on_gui_thread(),
                           "exclusions": property_exclusions})
        gate = self.gates.get(number)
        if gate is not None:
            gate.wait(10)
        if self.fail_with:
            raise RuntimeError(self.fail_with)
        return VarCondResult(
            rules=[VarCondRule(article=c, body="IF", rule=f"call{number}: $VARCOND = '{c}' IF") for c in article_codes],
            warnings=[f"warning {number}"])


def _select(panel, name):
    for row in range(panel._relations.count()):
        if panel._relations.item(row).text() == name:
            panel._relations.setCurrentRow(row)
            return
    raise AssertionError(name)


def _table_rules(panel):
    return [panel._output.item(r, 0).text() for r in range(panel._output.rowCount())]


@pytest.fixture
def panel(app):
    panel = _panel()
    panel._filter_timer.setInterval(30)
    yield panel
    QThreadPool.globalInstance().waitForDone(10000)
    QCoreApplication.processEvents()
    panel.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QCoreApplication.processEvents()


def test_opening_the_panel_does_not_generate_until_a_relation_is_selected(panel, monkeypatch):
    live = LiveRecorder(monkeypatch)
    panel.refresh_from_snapshot()
    pump(lambda: False, timeout=0.1)
    assert live.calls == []


def test_typing_in_the_filter_regenerates_once_after_a_pause_on_a_worker(panel, monkeypatch):
    live = LiveRecorder(monkeypatch)
    _select(panel, "PA_GESCRNNS.105508F")
    for text in ("G", "GE", "GES", "GESC", "GESCR", "GESCRN", "GESCRNN"):
        panel._filter.setText(text)
    assert live.calls == [], "no generation per keystroke"
    assert panel._relations.count() == 5, "the list is rebuilt only after the pause"

    assert pump(lambda: len(live.calls) == 1 and _table_rules(panel))
    pump(lambda: False, timeout=0.15)

    assert len(live.calls) == 1 and live.calls[0]["on_gui"] is False
    assert panel._relations.count() == 2 and panel._filter.text() == "GESCRNN"
    assert live.calls[0]["codes"] == ["GESCRNNS.105508F"]
    assert _table_rules(panel) == ["call1: $VARCOND = 'GESCRNNS.105508F' IF"]


def test_reentering_the_panel_asks_twice_but_generates_once(panel, monkeypatch):
    live = LiveRecorder(monkeypatch)
    _select(panel, "PA_GESCRNNU.105508F")

    panel.refresh_from_snapshot()                    # _refresh_relations + the explicit _generate_all

    assert pump(lambda: live.calls and _table_rules(panel))
    pump(lambda: False, timeout=0.1)
    assert len(live.calls) == 1 and live.calls[0]["on_gui"] is False        # two sync calls before


def test_the_table_shows_only_the_selected_relations_rules(panel, monkeypatch):
    live = LiveRecorder(monkeypatch)
    gate = live.gates[1] = threading.Event()
    _select(panel, "PA_GESCRNNU.105508F")
    panel._generate_all()
    assert pump(lambda: live.calls)

    _select(panel, "PA_RYTWKRNU.220110F")           # the user moves on while PDM is still working
    gate.set()
    assert pump(lambda: panel._live_task is None)

    assert _table_rules(panel) == [], "another relation's rules must not appear"
    assert "Waiting for this relation to finish loading" in panel._summary.text()
    _select(panel, "PA_GESCRNNU.105508F")           # coming back shows the finished result
    assert _table_rules(panel) == ["call1: $VARCOND = 'GESCRNNU.105508F' IF"]


def test_a_newer_generation_supersedes_a_slow_older_one(panel, monkeypatch):
    live = LiveRecorder(monkeypatch)
    gate = live.gates[1] = threading.Event()
    _select(panel, "PA_GESCRNNU.105508F")
    panel._exclusions.setText("Height")
    panel._generate_all()
    assert pump(lambda: len(live.calls) == 1)

    panel._exclusions.setText("Width")
    panel._generate_all()
    assert pump(lambda: len(live.calls) == 2 and _table_rules(panel))
    gate.set()
    pump(lambda: False, timeout=0.2)

    assert [c["exclusions"] for c in live.calls] == ["Height", "Width"]
    assert _table_rules(panel) == ["call2: $VARCOND = 'GESCRNNU.105508F' IF"], "the stale result was shown"


def test_a_failed_generation_is_reported_and_the_table_is_empty(panel, monkeypatch):
    live = LiveRecorder(monkeypatch)
    live.fail_with = "connection lost"
    _select(panel, "PA_GESCRNNU.105508F")

    panel._generate_all()
    assert pump(lambda: "Could not generate" in panel._summary.text())

    assert panel._summary.text() == "PA_GESCRNNU.105508F · Could not generate from PDM: connection lost"
    assert _table_rules(panel) == []


def test_clearing_the_selection_or_the_codes_drops_a_pending_result(panel, monkeypatch):
    live = LiveRecorder(monkeypatch)
    gate = live.gates[1] = threading.Event()
    _select(panel, "PA_GESCRNNU.105508F")
    panel._generate_all()
    assert pump(lambda: live.calls)

    panel._article_rows = []
    panel._generate_all()                            # nothing left to generate: shows the empty relation
    gate.set()
    pump(lambda: False, timeout=0.2)

    assert _table_rules(panel) == []


def test_maintenance_generation_stays_synchronous_and_cached(app, monkeypatch):
    live = LiveRecorder(monkeypatch)
    panel = _maintenance_panel(monkeypatch)
    generated = []

    class Service:
        def has_sources(self, codes):
            return True

        def generate(self, codes, prefix="", property_exclusions="", property_substitutions=""):
            generated.append(list(codes))
            return VarCondResult(rules=[VarCondRule(article=c, body="IF", rule=f"m: {c}") for c in codes])

    panel._maintenance_service = Service()
    panel._relations.blockSignals(True)
    _select(panel, "PA_GESCRNNU.105508F")
    panel._relations.blockSignals(False)

    panel._generate_all()                            # no event loop turn needed

    assert generated == [["GESCRNNU.105508F"]] and live.calls == []
    assert _table_rules(panel) == ["m: GESCRNNU.105508F"]


def test_spin_changes_still_rebuild_immediately(panel, monkeypatch):
    LiveRecorder(monkeypatch)
    before = panel._relations.count()
    panel._relation_length.setValue(6)
    assert panel._relations.count() != before          # no debounce on the prefix length


# --------------------------------------------------------------------------------------
# the export handler
# --------------------------------------------------------------------------------------
@pytest.fixture
def window(app, monkeypatch, tmp_path):
    from core.modules import WorkbenchModule
    from ui.main_window import MainWindow

    window = MainWindow()
    window._active_module = WorkbenchModule.DEVELOPMENT
    context = fakes.build_context()
    window._context.register_pdm_snapshot(context.active_snapshot)
    window._context.activate_snapshot_source("pdm")
    yield window
    window.close()
    assert QThreadPool.globalInstance().waitForDone(10000)
    QCoreApplication.processEvents()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QCoreApplication.processEvents()


def _messages(monkeypatch):
    messages = []
    for kind in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, kind, staticmethod(
            lambda parent, title, text, *a, _kind=kind, **k: messages.append((_kind, title, text))))
    # The "creates a NEW full MDB" notice: the tests accept it.
    monkeypatch.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    return messages


def test_varcond_relation_export_generates_on_a_worker_then_exports(window, monkeypatch):
    messages = _messages(monkeypatch)
    fakes.install(monkeypatch)
    snapshot = window._context.active_snapshot
    from models.relation_object import RelationObject
    snapshot.relation_objects = [RelationObject(name="PA_OLD", type_code="3", domain="P", body="x"),
                                 RelationObject(name="KEEP_ME", type_code="3", domain="C", body="y")]
    panel = VarCondGenerationPanel(window._context)
    page = SimpleNamespace(is_mdb_view=lambda: False, _varcond_panel=panel)
    threads, exported = [], []
    real_build = VarCondGenerationPanel.build_relation_objects
    monkeypatch.setattr(VarCondGenerationPanel, "build_relation_objects", staticmethod(
        lambda plan, emit=None: threads.append(on_gui_thread()) or real_build(plan, emit)))
    window._on_export_mdb = lambda *a, **k: exported.append([r.name for r in k["generated_relations"]])
    before = list(snapshot.relation_objects)

    window._on_export_varcond_relations_mdb(page)
    assert window._exports().busy                      # returned while the worker runs
    assert pump(lambda: exported)

    assert threads == [False]
    assert not window._exports().busy and messages == []
    # Generated relation objects are P_<prefix>; the live snapshot is not touched by the export.
    assert exported[0] == ["P_GESCRNNS.105508F", "P_GESCRNNU.105508F", "P_GESCRNPU.105508F",
                           "P_RYTWKRNS.220110F", "P_RYTWKRNU.220110F"]
    assert snapshot.relation_objects == before and [r.name for r in before] == ["PA_OLD", "KEEP_ME"]


def test_varcond_relation_export_declining_the_new_mdb_notice_exports_nothing(window, monkeypatch):
    messages = _messages(monkeypatch)
    asked = []
    monkeypatch.setattr(QMessageBox, "question", staticmethod(
        lambda parent, title, text, *a, **k: asked.append(text) or QMessageBox.StandardButton.No))
    fakes.install(monkeypatch)
    panel = VarCondGenerationPanel(window._context)
    page = SimpleNamespace(is_mdb_view=lambda: False, _varcond_panel=panel)
    window._on_export_mdb = lambda *a, **k: pytest.fail("must not export after the user declined")

    window._on_export_varcond_relations_mdb(page)

    assert len(asked) == 1 and "creates a NEW full MDB" in asked[0]
    assert not window._exports().busy and messages == []


def test_varcond_relation_export_tells_the_user_when_nothing_was_generated(window, monkeypatch):
    messages = _messages(monkeypatch)
    monkeypatch.setattr(VarCondService, "generate_live", lambda self, *a, **k: VarCondResult())
    fakes.install(monkeypatch)
    panel = VarCondGenerationPanel(window._context)
    page = SimpleNamespace(is_mdb_view=lambda: False, _varcond_panel=panel)
    exported = []
    window._on_export_mdb = lambda *a, **k: exported.append(1)

    window._on_export_varcond_relations_mdb(page)
    assert pump(lambda: messages and not window._exports().busy)

    assert messages[-1] == ("information", "Export VARCOND Relations",
                            "No VARCOND rules were generated; nothing was exported.")
    assert exported == []


def test_varcond_relation_export_reports_unexpected_errors(window, monkeypatch):
    messages = _messages(monkeypatch)
    monkeypatch.setattr(VarCondService, "generate_live",
                        lambda self, *a, **k: (_ for _ in ()).throw(OSError("PDM unreachable")))
    panel = VarCondGenerationPanel(window._context)
    page = SimpleNamespace(is_mdb_view=lambda: False, _varcond_panel=panel)
    window._on_export_mdb = lambda *a, **k: pytest.fail("must not export after a failure")

    window._on_export_varcond_relations_mdb(page)
    assert pump(lambda: messages and not window._exports().busy)

    assert messages[-1] == ("warning", "Export VARCOND Relations",
                            "Could not generate the VARCOND relations:\nPDM unreachable")
