"""Price Relation source rows are read from PDM once per product and persisted."""

import json
import threading
from types import SimpleNamespace

import pytest

from services.maintenance_varcond_service import (
    MaintenanceVarCondService,
    ParentSource,
    RelationReloadInProgressError,
    StaleRelationLoadError,
)
from services.relation_source_store import (
    RelationSourceStore,
    StaleRelationCacheError,
    relation_scope,
)
from tests.test_maintenance_varcond import SOURCES

CODES = sorted(SOURCES)


def _loader(calls, sources=SOURCES):
    def load(codes):
        calls.append(list(codes))
        return {c: sources[c] for c in codes if c in sources}
    return load


def _service(store, scope, calls, sources=SOURCES):
    service = MaintenanceVarCondService(loader=_loader(calls, sources))
    service.bind_store(store, scope)
    return service


def _rules(service, codes=CODES):
    return [r.rule for r in service.generate(codes, prefix="").rules]


@pytest.fixture
def store(tmp_path):
    return RelationSourceStore(tmp_path / "relations")


def test_first_open_fetches_from_pdm_and_saves(store):
    calls = []
    service = _service(store, "pdm|1|bolster", calls)

    service.sources_for(CODES)

    assert calls == [CODES]
    stored = store.load("pdm|1|bolster")
    assert stored is not None and sorted(stored.sources) == CODES


def test_reopening_after_restart_uses_saved_data_without_pdm(store):
    first_calls = []
    first = _service(store, "pdm|1|bolster", first_calls)
    first.sources_for(CODES)
    expected = _rules(first)

    restart_calls = []
    restarted = _service(store, "pdm|1|bolster", restart_calls)

    assert restarted.has_sources(CODES)
    restarted.sources_for(CODES)
    assert restart_calls == []
    assert _rules(restarted) == expected      # identical generation from saved rows


def test_navigating_away_and_back_does_not_refetch(store):
    calls = []
    service = _service(store, "pdm|1|a", calls)
    service.sources_for(CODES)
    service.bind_store(store, "pdm|2|b")           # another product opens
    assert not service.has_sources(CODES)
    service.bind_store(store, "pdm|1|a")           # back to the first

    service.sources_for(CODES)

    assert calls == [CODES]


def test_saved_sources_round_trip_every_field(store):
    original = ParentSource(
        parent="P1", found=True, prefix_length=7,
        attributes=[("Application", "P"), ("Colour", "RED")],
        components=[("C.1F", 2, "1", "|8|28|"), ("C.2F", 1, "2", "")],
        increments={"C.1F": [(8, "Fabric type"), (28, "Fabric colour")], "C.2F": []},
        warnings=["note"],
    )
    store.save("scope", {"P1": original}, 0)

    restored = store.load("scope").sources["P1"]

    assert restored == original
    assert isinstance(restored.components[0], tuple)
    assert isinstance(restored.increments["C.1F"][0], tuple)


def test_different_products_use_separate_caches(store):
    a_calls, b_calls = [], []
    a = _service(store, "pdm|1|a", a_calls)
    a.sources_for(CODES[:1])
    b = _service(store, "pdm|2|b", b_calls)

    assert not b.has_sources(CODES[:1])
    b.sources_for(CODES[1:2])

    assert store.path_for("pdm|1|a") != store.path_for("pdm|2|b")
    assert sorted(store.load("pdm|1|a").sources) == CODES[:1]
    assert sorted(store.load("pdm|2|b").sources) == CODES[1:2]


def test_scope_includes_source_database_and_product():
    context = SimpleNamespace(config=SimpleNamespace(pdm_server="S", pdm_database="D"))
    snap = SimpleNamespace(product=SimpleNamespace(id="7", code="BOL", name="Bolster"))
    other_db = SimpleNamespace(config=SimpleNamespace(pdm_server="S", pdm_database="D2"))

    assert relation_scope(snap, context) != relation_scope(snap, other_db)
    assert relation_scope(SimpleNamespace(product=None), context) is None


def test_explicit_reload_fetches_again_and_replaces_the_saved_copy(store):
    calls = []
    service = _service(store, "scope", calls)
    service.sources_for(CODES)
    before = store.revision("scope")
    changed = {
        c: ParentSource(parent=c, attributes=SOURCES[c].attributes,
                        components=SOURCES[c].components,
                        increments=SOURCES[c].increments, warnings=["fresh"])
        for c in CODES
    }
    service._loader = _loader(calls, changed)

    service.sources_for(CODES, refresh=True)

    assert calls == [CODES, CODES]
    assert store.revision("scope") == before + 1
    assert all(s.warnings == ["fresh"] for s in store.load("scope").sources.values())
    assert service._cache[CODES[0]].warnings == ["fresh"]


def test_failed_reload_keeps_previous_memory_and_disk_cache(store):
    service = _service(store, "scope", [])
    service.sources_for(CODES)
    saved = store.path_for("scope").read_text(encoding="utf-8")
    rules = _rules(service)

    def failing(_codes):
        raise ConnectionError("PDM unavailable")

    service._loader = failing
    with pytest.raises(ConnectionError):
        service.sources_for(CODES, refresh=True)

    assert store.path_for("scope").read_text(encoding="utf-8") == saved
    assert service.has_sources(CODES) and _rules(service) == rules


def test_reload_with_unusable_result_is_not_saved(store):
    service = _service(store, "scope", [])
    service.sources_for(CODES)
    saved = store.path_for("scope").read_text(encoding="utf-8")
    service._loader = lambda codes: {c: SimpleNamespace(parent="WRONG") for c in codes}

    with pytest.raises(ValueError):
        service.sources_for(CODES, refresh=True)

    assert store.path_for("scope").read_text(encoding="utf-8") == saved


def test_valid_empty_result_is_cached_and_distinct_from_a_failed_fetch(store):
    calls = []
    service = _service(store, "scope", calls, sources={})
    service.sources_for(["MISSING1"])

    stored = store.load("scope").sources["MISSING1"]
    assert stored.found is False                     # valid "not found", persisted

    again_calls = []
    again = _service(store, "scope", again_calls, sources={})
    again.sources_for(["MISSING1"])
    assert again_calls == []                         # not re-read

    failing = MaintenanceVarCondService(loader=lambda c: (_ for _ in ()).throw(OSError("x")))
    failing.bind_store(store, "other")
    with pytest.raises(OSError):
        failing.sources_for(["MISSING1"])
    assert store.load("other") is None               # a failed fetch saves nothing


def test_concurrent_reload_is_refused(store):
    entered, release = threading.Event(), threading.Event()

    def slow(codes):
        entered.set()
        release.wait(5)
        return {c: SOURCES[c] for c in codes}

    service = MaintenanceVarCondService(loader=slow)
    service.bind_store(store, "scope")
    worker = threading.Thread(target=lambda: service.sources_for(CODES, refresh=True))
    worker.start()
    assert entered.wait(5)

    with pytest.raises(RelationReloadInProgressError):
        service.sources_for(CODES, refresh=True)

    release.set()
    worker.join(5)
    assert store.load("scope") is not None


def test_reload_finishing_after_the_product_changed_is_discarded(store):
    service = MaintenanceVarCondService(loader=lambda c: {})
    service.bind_store(store, "old")

    def loader(codes):
        service.bind_store(store, "new")             # user opens another product mid-read
        return {c: SOURCES[c] for c in codes}

    service._loader = loader
    with pytest.raises(StaleRelationLoadError):
        service.sources_for(CODES, refresh=True)

    assert store.load("old") is None and store.load("new") is None
    assert not service.has_sources(CODES)            # nothing from the old read leaked in


def test_stale_writer_cannot_overwrite_newer_stored_data(store):
    store.save("scope", {CODES[0]: SOURCES[CODES[0]]}, 0)       # revision 1

    with pytest.raises(StaleRelationCacheError):
        store.save("scope", {CODES[1]: SOURCES[CODES[1]]}, 0)   # writer read revision 0

    assert sorted(store.load("scope").sources) == [CODES[0]]


def test_reload_loses_to_a_newer_save_made_while_it_was_reading(store):
    service = _service(store, "scope", [])
    service.sources_for(CODES)
    other = RelationSourceStore(store._dir)

    def loader(codes):
        other.save("scope", {}, other.revision("scope"))       # a newer revision lands
        return {c: SOURCES[c] for c in codes}

    service._loader = loader
    with pytest.raises(StaleRelationCacheError):
        service.sources_for(CODES, refresh=True)

    assert service.has_sources(CODES)                # previous memory cache restored


def test_corrupt_or_foreign_cache_files_read_as_no_cache(store):
    store.save("scope", {CODES[0]: SOURCES[CODES[0]]}, 0)
    path = store.path_for("scope")

    path.write_text("{not json", encoding="utf-8")
    assert store.load("scope") is None

    payload = {"schema_version": 999, "scope": "scope", "revision": 1, "sources": {}}
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert store.load("scope") is None

    payload = {"schema_version": 1, "scope": "another", "revision": 1, "sources": {}}
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert store.load("scope") is None


def test_service_without_a_store_behaves_as_before():
    calls = []
    service = MaintenanceVarCondService(loader=_loader(calls))

    service.sources_for(CODES)
    service.sources_for(CODES)
    assert calls == [CODES]
    service.sources_for(CODES, refresh=True)
    assert calls == [CODES, CODES]
