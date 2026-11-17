"""Phase 1 performance work: every optimised path must return exactly what it did before.

The golden digests below were produced by the implementation at commit ea18115 (before the
optimisations) from the deterministic data in ``tests/perf_synthetic.py``. The ``_reference_*``
functions are verbatim copies of the replaced algorithms, kept as oracles. Scale bounds are
deliberately generous (>10x headroom on a developer machine) so they only trip on a return to
quadratic behaviour, not on a slow CI runner.
"""
from __future__ import annotations

import json
import math
import os
import random
import subprocess
import time
from collections import deque
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from core.cancellation import CancellationToken, OperationCancelled, cancellation_scope
from models.article import Article
from models.snapshot import Snapshot
from tests.perf_synthetic import (
    build_class_creation_snapshot,
    canonical_article_sets,
    digest,
    reduction_service,
)

# --------------------------------------------------------------------------------------
# materialize_class_creation_article_sets
# --------------------------------------------------------------------------------------
GOLDEN_MATERIALIZE = {
    "small_default": (
        dict(count=60),
        "0cd3611665abf85fb779ca5dd4fe93f21abd25eb43d1cb09c26fa177321e3691", 2,
    ),
    "three_structures_manual_boundaries": (
        dict(count=60, structures=3, manual_boundaries=True),
        "51da8d86fb1cc2062c21e807892a55deeb37c0cf8b245e162379ddeac165360e", 3,
    ),
    "wide_vocabulary_manual_boundaries": (
        dict(count=400, structures=3, width_values=20, manual_boundaries=True, members_per_family=150),
        "d31099a571a5a0373fbb52f95a39f2ef0d9f8e5da2c824dc676902baa4e99d0f", 3,
    ),
    "single_class_multi_product": (
        dict(count=300, structures=1, products=4),
        "420a577d76447fa0f4bccc139c177c34a73f909708d51165fd766b24d76a38ac", 1,
    ),
}


@pytest.mark.parametrize("case", sorted(GOLDEN_MATERIALIZE))
def test_materialize_class_creation_output_is_unchanged(case):
    kwargs, expected, set_count = GOLDEN_MATERIALIZE[case]
    kwargs = dict(kwargs)
    snapshot = build_class_creation_snapshot(kwargs.pop("count"), **kwargs)

    sets = reduction_service().materialize_class_creation_article_sets(snapshot)

    assert len(sets) == set_count
    assert digest(canonical_article_sets(snapshot, sets)) == expected


def test_materialize_class_creation_is_not_quadratic_in_class_size():
    """One 2,000-article class took ~9 s when the class prefix was recomputed per article."""
    snapshot = build_class_creation_snapshot(2000, structures=1)
    service = reduction_service()

    started = time.perf_counter()
    sets = service.materialize_class_creation_article_sets(snapshot)
    elapsed = time.perf_counter() - started

    assert len(sets) == 1 and len(sets[0].article_ids) == 2000
    assert elapsed < 3.0, f"materialisation took {elapsed:.2f}s"


# --------------------------------------------------------------------------------------
# EngineeringMemberService.get_article with a prebuilt index
# --------------------------------------------------------------------------------------
def _reference_get_article(snapshot, member):
    if snapshot is None or member is None:
        return None
    article_id = getattr(member, "article_id", "")
    if not article_id:
        return None
    for article in snapshot.articles:
        if article.id == article_id:
            return article
    return None


def test_member_service_index_matches_linear_lookup_including_duplicates_and_gaps():
    from models.member_article import MemberArticle
    from services.engineering.engineering_member_service import EngineeringMemberService

    first = Article(id="dup", code="FIRST")
    second = Article(id="dup", code="SECOND")
    snapshot = Snapshot(articles=[Article(id="a1", code="A1"), first, second, Article(id=7, code="N7"),
                                  Article(id=None, code="NONE")])
    members = [
        MemberArticle(id="m1", article_id="a1"), MemberArticle(id="m2", article_id="dup"),
        MemberArticle(id="m3", article_id="missing"), MemberArticle(id="m4", article_id=""),
        MemberArticle(id="m5", article_id=7), MemberArticle(id="m6", article_id=None),
    ]
    service = EngineeringMemberService(SimpleNamespace())
    index = service.index_articles(snapshot)

    for member in members:
        expected = _reference_get_article(snapshot, member)
        assert service.get_article(snapshot, member) is expected
        assert service.get_article(snapshot, member, index=index) is expected
    assert service.get_article(snapshot, members[1], index=index) is first      # first match wins
    assert service.get_article(None, members[0], index={}) is None
    assert service.get_article(snapshot, None, index=index) is None


def test_auto_reduce_result_is_unchanged_by_the_index():
    snapshot = build_class_creation_snapshot(300, structures=1, products=3)
    from services.engineering.engineering_member_service import EngineeringMemberService

    service = EngineeringMemberService(SimpleNamespace())
    changed = service.auto_reduce(snapshot)

    by_product = {}
    for article in snapshot.articles:
        by_product.setdefault(article.product_id, []).append(article.code)
    expected = {}
    for product, codes in by_product.items():
        prefix = codes[0]
        for code in codes[1:]:
            n = 0
            while n < min(len(prefix), len(code)) and prefix[n] == code[n]:
                n += 1
            prefix = prefix[:n]
        expected[product] = prefix
    article_by_id = {a.id: a for a in snapshot.articles}
    for family in snapshot.engineering.families:
        for member in family.members:
            assert member.reduced_article == expected[article_by_id[member.article_id].product_id]
    assert changed == 300


# --------------------------------------------------------------------------------------
# Articles / Class Creation pages
# --------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _context(count, **kwargs):
    from core.application_context import ApplicationContext

    ctx = ApplicationContext()
    snapshot = build_class_creation_snapshot(count, **kwargs)
    ctx.register_pdm_snapshot(snapshot)
    ctx.activate_snapshot_source("pdm")
    ctx.engineering_reduction_service.materialize_class_creation_article_sets(snapshot)
    return ctx, snapshot


def _articles_page(ctx, reduced=None):
    """An Articles page in Development; ``reduced(index) -> str`` stamps each member afterwards
    (constructing the page refreshes it, which re-stamps the members itself)."""
    from core.modules import WorkbenchModule
    from ui.pages.articles_page import ArticlesPage

    page = ArticlesPage(ctx)
    page._active_module = WorkbenchModule.DEVELOPMENT
    page._validate_articles = lambda: ctx.article_service.validate()
    if reduced is not None:
        members = [m for f in ctx.active_snapshot.engineering.families for m in f.members]
        for index, member in enumerate(members):
            member.reduced_article = reduced(index)
    page._rows = page._collect_rows()
    return page


def test_collect_rows_matches_linear_lookup(qapp):
    ctx, snapshot = _context(120, structures=2)
    snapshot.articles.append(Article(id="a5", code="SHADOWED"))     # duplicate id: first must win
    snapshot.engineering.families[0].members[0].article_id = "no-such-article"
    page = _articles_page(ctx)

    rows = page._collect_rows()

    expected = [
        (family, member, _reference_get_article(snapshot, member))
        for family in snapshot.engineering.families for member in family.members
    ]
    assert len(rows) == len(expected) == 120
    for (f1, m1, a1), (f2, m2, a2) in zip(rows, expected):
        assert f1 is f2 and m1 is m2 and a1 is a2
    assert rows[0][2] is None


def _reference_export_ids(rows, members):
    return tuple(sorted({
        str(article.id)
        for _family, member, article in rows
        if article is not None and any(member is grouped for grouped in members)
    }))


@pytest.mark.parametrize("reduced", [True, False])
def test_grouped_export_checkbox_ids_match_the_original_quadratic_expression(qapp, reduced):
    from ui.pages.articles_page import _COL_SOURCE

    ctx, snapshot = _context(180, structures=3, members_per_family=60)
    members = [m for f in snapshot.engineering.families for m in f.members]
    members[3].article_id = "ghost"                      # a row without an article
    page = _articles_page(ctx, reduced=lambda i: f"DSK{i % 5}" if reduced else "")
    page._group_by_base = True
    rows = page._rows
    page._populating = True                              # as ``_populate`` sets it around the build
    page._table.setRowCount(0)
    page._populate_grouped(rows)

    table = page._table
    assert table.rowCount() > 1
    seen_members = 0
    for row in range(table.rowCount()):
        meta = table.item(row, _COL_SOURCE).data(0x0100)
        group_members = meta[2]
        seen_members += len(group_members)
        expected = _reference_export_ids(rows, group_members)
        assert table.item(row, 9).data(0x0100) == expected
    assert seen_members == len(rows)


def test_grouped_view_scales_linearly(qapp):
    ctx, snapshot = _context(2500, structures=3)
    page = _articles_page(ctx, reduced=lambda i: f"DSK{i % 40:02d}")
    page._group_by_base = True
    rows = page._rows
    page._populating = True
    page._table.setRowCount(0)

    started = time.perf_counter()
    page._populate_grouped(rows)
    elapsed = time.perf_counter() - started

    assert page._table.rowCount() == 40
    assert elapsed < 6.0, f"grouped populate took {elapsed:.2f}s"


def _reference_set_rows_development(snapshot):
    """Verbatim copy of the Development branch of ``ArticlesPage._set_rows`` before the change."""
    members_by_article = {
        str(member.article_id): member
        for family in (getattr(snapshot.engineering, "families", []) or [])
        for member in (getattr(family, "members", []) or [])
    }
    by_base: dict[str, dict] = {}
    set_props = {
        str(aid): {
            str(getattr(attr, "name", "") or "")
            for attr in getattr(aset, "properties", []) or []
            if getattr(attr, "name", "")
        }
        for aset in (getattr(snapshot, "article_sets", []) or [])
        for aid in getattr(aset, "article_ids", []) or []
    }
    for aset in getattr(snapshot, "article_sets", []) or []:
        for aid in getattr(aset, "article_ids", []) or []:
            member = members_by_article.get(str(aid))
            base = (getattr(member, "reduced_article", "") if member else "") or ""
            base = base or "Set"
            entry = by_base.setdefault(base, {"ids": [], "props": set()})
            if str(aid) not in entry["ids"]:
                entry["ids"].append(str(aid))
            entry["props"].update(set_props.get(str(aid), set()))
    return [(base, e["ids"], len(base), len(e["props"]), ()) for base, e in by_base.items()]


def test_set_rows_keep_first_seen_order_and_uniqueness(qapp):
    ctx, snapshot = _context(150, structures=3)
    # Duplicate an article id inside a set and leave some members without a reduced base.
    snapshot.article_sets[0].article_ids.append(snapshot.article_sets[0].article_ids[0])
    page = _articles_page(ctx, reduced=lambda i: "" if i % 4 == 0 else f"DSK{i % 3}")

    actual = list(page._set_rows(snapshot))

    assert actual == _reference_set_rows_development(snapshot)
    assert any(base == "Set" for base, *_rest in actual)


def test_set_code_helpers_give_the_same_answer_with_a_prebuilt_code_map(qapp):
    from ui.pages.articles_page import ArticlesPage

    ctx, snapshot = _context(90, structures=2)
    code_of = {str(a.id): (a.code or "") for a in snapshot.articles}
    ids = [a.id for a in snapshot.articles[:40]] + ["unknown-id"]

    assert ArticlesPage._set_max_code_len(snapshot, ids, code_of) == ArticlesPage._set_max_code_len(snapshot, ids)
    assert ArticlesPage._set_prefix(snapshot, ids, code_of) == ArticlesPage._set_prefix(snapshot, ids)
    assert ArticlesPage._set_prefix(None, ids) == "" and ArticlesPage._set_max_code_len(None, ids) == 0


def _reference_linked_articles(snapshot, value):
    """The expression ``_populate_visible_values`` evaluated per value before the change."""
    article_codes = {str(a.id): a.code for a in snapshot.articles}
    article_values = snapshot.article_property_value_ids or {}
    product_values = snapshot.product_property_value_ids or {}
    return [
        article_codes[str(article.id)]
        for article in snapshot.articles
        if str(value.id) in (
            article_values.get(str(article.id))
            or product_values.get(str(article.product_id), [])
        )
    ] if article_values or product_values else []


def test_class_creation_value_panel_links_match_the_original_scan(qapp):
    from core.modules import WorkbenchModule
    from ui.pages.class_creation_page import ClassCreationPage

    ctx, snapshot = _context(160, structures=3, products=3, width_values=12)
    # Articles without their own value links fall back to the product-level list; a duplicated
    # article id must keep appending the *last* code once per occurrence.
    for index in range(0, 160, 5):
        snapshot.article_property_value_ids.pop(f"a{index}", None)
    snapshot.articles.append(Article(id="a3", product_id="prod0", code="DUPLICATE-OF-A3"))
    page = ClassCreationPage(ctx)
    page._active_module = WorkbenchModule.DEVELOPMENT
    page.refresh()

    target = None
    for row in range(page._attr_master.rowCount()):
        meta = page._attr_master.item(row, 0).data(0x0100)
        if meta and getattr(meta[0], "name", "") == "Width":
            target = row
    assert target is not None
    page._attr_master.clearSelection()
    page._attr_master.selectRow(target)

    table = page._attr_values
    assert table.rowCount() == 12
    for row in range(table.rowCount()):
        item = table.item(row, 0)
        _prop, value, _cv, _group = item.data(0x0100)
        linked = _reference_linked_articles(snapshot, value)
        assert item.text() == (value.value or "-") + (" (linked)" if linked else " (remaining)")
        assert item.toolTip() == ("Linked articles: " + ", ".join(linked) if linked else "")
    assert any("DUPLICATE-OF-A3" in table.item(r, 0).toolTip() for r in range(table.rowCount()))


# --------------------------------------------------------------------------------------
# SyteLine: ArrayList lookups and the item query
# --------------------------------------------------------------------------------------
def _reference_list_index_of(items, value):
    value_is_number = isinstance(value, (int, float)) and not isinstance(value, bool)
    for position, item in enumerate(items):
        item_is_number = isinstance(item, (int, float)) and not isinstance(item, bool)
        if (item_is_number and value_is_number) or type(item) is type(value):
            if item == value:
                return position
    return -1


_NAN = float("nan")
_POOL = [0, 1, 2, 1.0, 2.5, True, False, "1", "a", "A", "", None, (1,), Decimal(1), Decimal("2.5"),
         10 ** 20, _NAN, b"a", "1~2"]


def test_list_index_of_matches_the_reference_for_mixed_types():
    from services.syteline_export.pipeline.netsem import list_contains, list_index_of, list_remove

    rng = random.Random(20260517)
    for _ in range(4000):
        items = [rng.choice(_POOL) for _ in range(rng.randint(0, 12))]
        value = rng.choice(_POOL)
        expected = _reference_list_index_of(items, value)
        assert list_index_of(items, value) == expected, (items, value)
        assert list_contains(items, value) is (expected > -1)
        removed = list(items)
        list_remove(removed, value)
        reference = list(items)
        if expected > -1:
            del reference[expected]
        assert removed == reference or all(
            (a is b) or a == b for a, b in zip(removed, reference)
        )


def test_list_index_of_edge_semantics():
    from services.syteline_export.pipeline.netsem import list_index_of

    assert list_index_of([True, 1, 1.0], 1) == 1          # bool is not a number
    assert list_index_of([1, True], True) == 1            # and only matches bool
    assert list_index_of([1.0, 1], 1) == 0                # int/float interoperate
    assert list_index_of([_NAN], _NAN) == -1              # NaN is never equal, even to itself
    assert list_index_of([Decimal(1)], 1) == -1           # different types do not coerce
    assert list_index_of((3, 4, 5), 5) == 2               # tuples take the fast path too
    assert list_index_of("abc", "b") == 1                 # other iterables keep the original scan
    assert list_index_of(deque([5, "x", 5.0]), 5.0) == 0
    assert list_index_of({"k": 1}.keys(), "k") == 0
    assert list_index_of([], 1) == -1
    token = CancellationToken()
    with cancellation_scope(token):
        token.cancel()
        assert list_index_of([], 1) == -1                 # nothing to scan: no checkpoint, as before
        with pytest.raises(OperationCancelled):
            list_index_of([1, 2, 3], 9)


def test_list_index_of_is_fast_on_a_large_catalogue_list():
    from services.syteline_export.pipeline.netsem import list_contains

    catalogue = list(range(100_000))
    started = time.perf_counter()
    for k in range(100):
        assert not list_contains(catalogue, -1 - k)
    elapsed = time.perf_counter() - started
    assert elapsed < 3.0, f"100 misses over 100k entries took {elapsed:.2f}s"      # ~6 s before


def test_p00_runs_the_item_query_once_and_keeps_the_count_list(tmp_path):
    from tests.test_syteline_pipeline_stage_p00 import ITEM_Q, make, sql_calls

    rows = [{"LongItem": "A1"}, {"LongItem": 17}, {"LongItem": None}, {"LongItem": "B2"}]
    h = make(tmp_path, items=rows)
    try:
        assert h.p00_setup() is None
        assert len(sql_calls(h, ITEM_Q)) == 1
        assert h.v.item_rows is not None and [r["LongItem"] for r in h.v.item_rows] == ["A1", 17, None, "B2"]
        assert h.v.arrayList23 == ["A1", "17", "", "B2"]
        assert h.v.item_count == 4
    finally:
        for name in list(vars(h.v)):
            if name.startswith("streamWriter") and hasattr(getattr(h.v, name), "close"):
                getattr(h.v, name).close()


def test_p00_cancellation_still_stops_the_count_loop(tmp_path):
    from tests.test_syteline_pipeline_stage_p00 import make

    h = make(tmp_path, items=[{"LongItem": f"I{i}"} for i in range(50)])
    seen = {"n": 0}
    original = h.check_abort

    def counting_abort():
        seen["n"] += 1
        return original()

    h.check_abort = counting_abort
    try:
        h.p00_setup()
        assert seen["n"] >= 50                              # still checked once per item row
    finally:
        for name in list(vars(h.v)):
            if name.startswith("streamWriter") and hasattr(getattr(h.v, name), "close"):
                getattr(h.v, name).close()


# --------------------------------------------------------------------------------------
# JSON caches: same content, no indentation
# --------------------------------------------------------------------------------------
def test_family_snapshot_cache_is_compact_and_has_the_same_content(tmp_path):
    from services.pdm_service import PDMService

    snapshot = build_class_creation_snapshot(40, structures=2)
    service = PDMService(SimpleNamespace(config=SimpleNamespace(pdm_server="s", pdm_database="d")))
    service._SNAPSHOT_CACHE_DIR = tmp_path

    path = service.save_family_snapshot(snapshot, "Family X")

    text = path.read_text(encoding="utf-8")
    payload = json.loads(text)
    assert "\n" not in text, "cache file should not be pretty-printed"
    assert [a["id"] for a in payload["articles"]] == [a.id for a in snapshot.articles]
    assert [a["code"] for a in payload["articles"]] == [a.code for a in snapshot.articles]
    assert len(payload["properties"]) == len(snapshot.properties)
    assert payload["family_name"] == "Family X" and payload["source"] == "s/d"
    assert len(payload["engineering"]["families"]) == len(snapshot.engineering.families)
    # The compact text is the same document a pretty-printed dump would contain.
    assert json.loads(json.dumps(payload, ensure_ascii=False, indent=1)) == payload


def test_registry_cache_round_trips(tmp_path):
    from models.product import Product
    from services.pdm_service import PDMService

    service = PDMService(SimpleNamespace(config=SimpleNamespace(pdm_server="s", pdm_database="d")))
    service._REGISTRY_CACHE = tmp_path / "registry.json"
    products = [Product(id=str(i), code=f"P{i}", name=f"Name {i}", category="Cat",
                        description="d", catalogue_id=5, range_name="R", series_id=i) for i in range(5)]

    service._save_registry_cache(products)
    loaded = service._load_registry_cache()

    assert "\n" not in service._REGISTRY_CACHE.read_text(encoding="utf-8")
    assert [(p.id, p.code, p.name, p.catalogue_id, p.range_name, p.series_id) for p in loaded] == \
           [(p.id, p.code, p.name, p.catalogue_id, p.range_name, p.series_id) for p in products]


# --------------------------------------------------------------------------------------
# PowerShell MDB bridge: result shape, order and counts (real ACE; skipped when unavailable)
# --------------------------------------------------------------------------------------
@pytest.fixture
def scratch_mdb(tmp_path):
    from services.mdb_service import MDBService, _PS32

    if not Path(_PS32).is_file():
        pytest.skip("32-bit Windows PowerShell / ACE integration unavailable")
    path = tmp_path / "bridge.mdb"
    script = (
        "$ErrorActionPreference='Stop'; $c=New-Object -ComObject ADOX.Catalog; "
        f"$c.Create(\"Provider=Microsoft.ACE.OLEDB.16.0;Data Source={path};\"); $c.ActiveConnection.Close(); "
        "$conn=New-Object -ComObject ADODB.Connection; "
        f"$conn.Open('Provider=Microsoft.ACE.OLEDB.16.0;Data Source={path};'); "
        "$conn.Execute('CREATE TABLE tT (id LONG, code TEXT(40), val DOUBLE, flag YESNO, descr TEXT(40))') | Out-Null; "
        "$conn.Execute('CREATE TABLE tEmpty (id LONG)') | Out-Null; $conn.Close()"
    )
    made = subprocess.run([_PS32, "-NoProfile", "-Command", script], capture_output=True, text=True)
    if made.returncode:
        if any(m in made.stderr.lower() for m in ("provider cannot be found", "class not registered", "80040154")):
            pytest.skip("32-bit ACE provider is not installed")
        pytest.fail(f"Could not create scratch MDB: {made.stderr}")
    return MDBService(SimpleNamespace()), path


def _seed(service, path, count):
    """Fill ``tT`` with ``count`` (<= 10,000) rows in one Jet statement and return the expected rows."""
    from services.mdb_service import _PS32

    x = "(a.n + 10*b.n + 100*c.n + 1000*d.n)"
    script = (
        "$ErrorActionPreference='Stop'; $conn=New-Object -ComObject ADODB.Connection; "
        f"$conn.Open('Provider=Microsoft.ACE.OLEDB.16.0;Data Source={path};'); "
        "$conn.Execute('CREATE TABLE tDigit (n LONG)') | Out-Null; "
        "foreach ($i in 0..9) { $conn.Execute(\"INSERT INTO tDigit (n) VALUES ($i)\") | Out-Null }; "
        "$conn.Execute(\"INSERT INTO tT (id, code, val, flag, descr) SELECT "
        f"{x}, 'C' & Format({x}, '0000'), {x} * 1.5, IIf({x} Mod 2 = 0, True, False), "
        f"IIf({x} Mod 3 = 0, Null, 'descr ' & CStr({x})) "
        f"FROM tDigit AS a, tDigit AS b, tDigit AS c, tDigit AS d WHERE {x} < {count}\") | Out-Null; "
        "$conn.Close()"
    )
    made = subprocess.run([_PS32, "-NoProfile", "-Command", script], capture_output=True, text=True)
    assert made.returncode == 0, made.stderr
    return [
        {"id": i, "code": f"C{i:04d}", "val": i * 1.5, "flag": i % 2 == 0,
         "descr": None if i % 3 == 0 else f"descr {i}"}
        for i in range(count)
    ]


def test_bridge_query_returns_lists_of_dicts_for_zero_one_and_many_rows(scratch_mdb):
    service, path = scratch_mdb
    rows = _seed(service, path, 300)

    assert service.read_table(path, "SELECT * FROM tEmpty") == []
    one = service.read_table(path, "SELECT * FROM tT WHERE id = 7")
    assert isinstance(one, list) and len(one) == 1
    assert one[0] == {"id": 7, "code": "C0007", "val": 10.5, "flag": False, "descr": "descr 7"}
    many = service.read_table(path, "SELECT * FROM tT ORDER BY id")
    assert len(many) == 300 and [r["id"] for r in many] == list(range(300))
    assert all(list(r) == ["id", "code", "val", "flag", "descr"] for r in many)     # column order kept
    assert many[0]["descr"] is None and many[1]["descr"] == "descr 1"                  # NULL stays null
    assert many == rows                                                              # every cell
    assert many[299]["val"] == 448.5 and many[298]["flag"] is True


def test_bridge_batches_keep_result_order_counts_and_transaction_semantics(scratch_mdb):
    service, path = scratch_mdb
    _seed(service, path, 10)
    ops = (
        [{"op": "query", "sql": f"SELECT id FROM tT WHERE id = {i}"} for i in range(150)]
        + [{"op": "update", "table": "tT", "set": {"val": 99.0}, "where": {"id": 3}},
           {"op": "delete", "table": "tT", "where": {"id": 4}},
           {"op": "query", "sql": "SELECT COUNT(*) AS n FROM tT"}]
    )

    batch = service.execute_batch(path, ops, transaction=True)

    assert batch.ok and len(batch.results) == 153
    assert [r.op for r in batch.results] == ["query"] * 150 + ["update", "delete", "query"]
    assert [len(r.rows) for r in batch.results[:150]] == [1] * 10 + [0] * 140
    assert batch.results[150].updated == 1
    assert batch.results[152].rows[0]["n"] == 9

    failing = service.execute_batch(
        path, [{"op": "delete", "table": "tT", "where": {"id": 5}},
               {"op": "query", "sql": "SELECT * FROM no_such_table"},
               {"op": "delete", "table": "tT", "where": {"id": 6}}], transaction=True)
    assert not failing.ok and len(failing.results) == 2                      # stops at the failure
    assert service.read_table(path, "SELECT COUNT(*) AS n FROM tT")[0]["n"] == 9     # rolled back

    tables = service.read_tables(path, {"a": "SELECT id FROM tT WHERE id < 2 ORDER BY id",
                                        "b": "SELECT * FROM tEmpty"})
    assert tables == {"a": [{"id": 0}, {"id": 1}], "b": []}


def test_bridge_scales_with_result_size(scratch_mdb):
    service, path = scratch_mdb
    _seed(service, path, 6000)

    started = time.perf_counter()
    rows = service.read_table(path, "SELECT * FROM tT ORDER BY id")
    elapsed = time.perf_counter() - started

    assert len(rows) == 6000 and rows[-1]["id"] == 5999
    assert elapsed < 60.0, f"reading 6,000 rows took {elapsed:.1f}s"
