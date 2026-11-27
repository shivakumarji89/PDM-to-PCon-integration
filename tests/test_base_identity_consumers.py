"""Stage 1 corrections: duplicate article ids, price/base consistency, Articles-page identity."""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QTableWidgetItem

from services.article_mdb_export_service import ArticleMdbExportService
from services.engineering.base_identity import (
    BaseIdentityConflict,
    resolve_base_identities,
    stale_price_bases,
)
from services.ocd_export_service import OcdExportService
from services.price_mdb_export_service import PriceMdbExportService
from services.pricing_service import PricingService
from services.xocd_export_service import XocdExportService
from ui.pages.articles_page import ArticlesPage

from test_base_identity import CODES, _member, _ry3x, _xocd


@pytest.fixture(scope="module", autouse=True)
def app():
    return QApplication.instance() or QApplication([])


def _record(article_code, condition="", level="B", is_global=False):
    return SimpleNamespace(is_global=is_global, article_code=article_code,
                           variant_condition=condition, level=level, currency="EUR")


# -- duplicate article ids ------------------------------------------------------------------

def _with_duplicate(second_reduced):
    snap = _ry3x()
    snap.engineering.families.append(SimpleNamespace(members=[_member("s1", second_reduced)]))
    return snap


def test_same_article_id_and_same_base_is_deduplicated():
    ident = resolve_base_identities(_with_duplicate("RY3XS"))
    assert ident.id_conflicts == []
    assert [a for a, _b in ident.entries].count("s1") == 1
    assert ident.bases["RY3XS"].article_ids.count("s1") == 1


def test_same_article_id_with_different_bases_is_a_recorded_conflict():
    ident = resolve_base_identities(_with_duplicate("RY3X"))
    assert ident.id_conflicts == [("s1", "RY3XS", "RY3X")]
    assert ident.by_article["s1"] == "RY3XS"            # never merged into the second identity
    assert "RY3X" not in ident.bases


def test_conflict_stops_the_full_series_resolver_and_both_exports(tmp_path):
    snap = _with_duplicate("RY3X")
    xocd = _xocd()
    with pytest.raises(BaseIdentityConflict, match="s1"):
        xocd._base_codes(snap)
    with pytest.raises(BaseIdentityConflict):
        xocd.resolve_base_identities(snap)

    snap.product = object()
    snap.relation_objects = []
    full = OcdExportService(SimpleNamespace(xocd_export_service=xocd)).export(snap, tmp_path)
    assert not full.ok and "more than one base article" in full.error

    mdb = tmp_path / "x.mdb"
    mdb.write_bytes(b"")
    incremental = ArticleMdbExportService(SimpleNamespace(xocd_export_service=xocd)).export(
        snap, mdb, selected_article_ids={"s1"})
    assert incremental["ok"] is False and "more than one base article" in incremental["error"]


# -- stored prices vs canonical base --------------------------------------------------------

ITEM = CODES["s1"]                                       # RY3XSDABAD.C0812, canonical base RY3XS


def test_price_keyed_to_the_canonical_base_is_consistent():
    snap = _ry3x()
    snap.price_records = [_record("RY3XS", ITEM[5:]), _record("RY3XS", ITEM[5:] + " 9502=OK", "X")]
    assert stale_price_bases(snap, resolve_base_identities(snap)) == []


def test_price_keyed_to_another_base_is_detected_for_base_and_upcharge_rows():
    snap = _ry3x()
    snap.price_records = [_record("RY3X", ITEM[4:]), _record("RY3X", ITEM[4:] + " 9502=OK", "X")]
    stale = stale_price_bases(snap, resolve_base_identities(snap))
    assert [(c.item, c.stored_base, c.canonical_base) for c in stale] == [(ITEM, "RY3X", "RY3XS")]


def test_global_unknown_item_and_empty_records_are_not_judged():
    snap = _ry3x()
    snap.price_records = [_record("", ITEM, is_global=True), _record("ZZZ", "9.99"), _record("")]
    assert stale_price_bases(snap, resolve_base_identities(snap)) == []


def test_full_series_export_refuses_stale_prices_instead_of_dropping_them(tmp_path):
    snap = _ry3x()
    snap.product, snap.relation_objects = object(), []
    snap.price_records = [_record("RY3X", ITEM[4:])]
    result = OcdExportService(SimpleNamespace(xocd_export_service=_xocd())).export(snap, tmp_path)
    assert not result.ok
    assert "keyed to a different base article" in result.error and "RY3XS" in result.error
    assert not (tmp_path / "pcr_data_com_ocd.mdb").exists()


def test_price_export_refuses_stale_prices(tmp_path):
    snap = _ry3x()
    snap.price_records = [_record("RY3X", ITEM[4:])]
    mdb = tmp_path / "p.mdb"
    mdb.write_bytes(b"")
    result = PriceMdbExportService(SimpleNamespace(xocd_export_service=_xocd())).export(snap, mdb)
    assert result["ok"] is False and "keyed to a different base article" in result["error"]


# -- pricing follows the canonical base at computation time ---------------------------------

def _pricing_snapshot():
    snap = _ry3x()
    snap.article_prefix_length = {}
    snap.article_sets = []            # no set slice: the dot rule applies, as in a fresh PDM load
    snap.articles.append(SimpleNamespace(id="x", code="ZZZ1.01", product_id="p"))
    return snap


def test_pricing_prefix_overlays_canonical_bases_and_keeps_the_fallback_elsewhere():
    snap = _pricing_snapshot()
    service = PricingService(SimpleNamespace())
    legacy = service._set_prefix_by_item(snap)
    assert legacy[ITEM] == "RY3XSDABAD."                  # the dot rule: not the Article-workflow base
    prefixes = service._prefix_by_item(snap)
    assert prefixes[ITEM] == "RY3XS" and prefixes[CODES["t3"]] == "RY3XT"
    assert prefixes["ZZZ1.01"] == legacy["ZZZ1.01"]     # not an engineering member


def test_records_computed_from_the_overlay_are_consistent_and_legacy_keys_are_not():
    snap = _pricing_snapshot()
    service = PricingService(SimpleNamespace())

    def base_record(prefixes):
        prefix = prefixes[ITEM]
        return _record(prefix, ITEM[len(prefix):])

    snap.price_records = [base_record(service._prefix_by_item(snap))]
    assert stale_price_bases(snap, resolve_base_identities(snap)) == []
    snap.price_records = [base_record(service._set_prefix_by_item(snap))]
    assert [c.stored_base for c in stale_price_bases(snap, resolve_base_identities(snap))] == ["RY3XSDABAD."]


def test_export_base_key_stays_the_fallback_tier_so_there_is_no_recursion():
    snap = _pricing_snapshot()
    xocd = XocdExportService(SimpleNamespace())
    assert xocd._price_base_of(snap)[ITEM] == "RY3XSDABAD."


# -- Articles page identity -----------------------------------------------------------------

def test_page_resolves_the_same_identity_and_source_as_the_exports():
    snap = _ry3x(reduced=False)
    page = SimpleNamespace(_context=SimpleNamespace(
        active_snapshot=snap, xocd_export_service=SimpleNamespace(_price_base_of=lambda s: {ITEM: "RY3X"})))
    ident = ArticlesPage._identities(page)
    article = next(a for a in snap.articles if a.id == "s1")
    assert ArticlesPage._canonical_base(ident, snap.engineering.families[0].members[0], article) == (
        "RY3X", "price_base")
    assert ident.entries == resolve_base_identities(snap, {ITEM: "RY3X"}).entries


def test_page_unresolved_row_is_a_proposal_and_member_without_article_keeps_its_reduced_base():
    member = SimpleNamespace(reduced_article="AB")
    assert ArticlesPage._canonical_base(None, member, None) == ("AB", "reduced_article")
    assert ArticlesPage._canonical_base(resolve_base_identities(_ry3x(reduced=False)),
                                        member, SimpleNamespace(id="s1")) == ("", "")


def test_page_marks_unconfirmed_bases_and_leaves_confirmed_ones_plain():
    plain, fallback, proposal = QTableWidgetItem("A"), QTableWidgetItem("B"), QTableWidgetItem("C")
    ArticlesPage._mark_base_status(plain, "reduced_article")
    ArticlesPage._mark_base_status(fallback, "price_base")
    ArticlesPage._mark_base_status(proposal, "proposal")
    assert not plain.font().italic() and plain.toolTip() == ""
    assert fallback.font().italic() and "not confirmed" in fallback.toolTip()
    assert proposal.font().italic() and "Proposal only" in proposal.toolTip()


def test_page_group_is_confirmed_only_when_every_member_is():
    assert ArticlesPage._group_status({"reduced_article", "base_length_override"}) in (
        "reduced_article", "base_length_override")
    assert ArticlesPage._group_status({"reduced_article", "price_base"}) == "price_base"
    assert ArticlesPage._group_status({"price_base", "proposal"}) == "proposal"
