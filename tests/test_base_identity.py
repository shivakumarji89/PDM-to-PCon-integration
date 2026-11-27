"""Canonical base-article identity: one resolver for Articles, Classes and both exports."""
from __future__ import annotations

from types import SimpleNamespace

from services.article_mdb_export_service import ArticleMdbExportService
from services.engineering.base_identity import explicit_base, resolve_base_identities
from services.engineering.engineering_class_service import EngineeringClassService
from services.xocd_export_service import XocdExportService

from test_base_article_classes import _snapshot as class_snapshot

# RY3X-shaped data: two article sets that BOTH contain bases RY3XS and RY3XT.
CODES = {
    "s1": "RY3XSDABAD.C0812", "s2": "RY3XSDABAD.C0814", "s3": "RY3XSDBBAD.C0812",
    "t1": "RY3XTDABAD.C0812", "t2": "RY3XTDABAD.C0814", "t3": "RY3XTDBBAD.C0812",
}
SETS = [("RY3X", ["s1", "s2", "t1", "t2"]), ("RY3X_2", ["s3", "t3"])]
TEXT_FIELDS = ("relation_object", "code_scheme", "short_description", "long_description")


def _member(article_id, reduced):
    return SimpleNamespace(id=f"m-{article_id}", article_id=article_id, reduced_article=reduced,
                           **{f: "" for f in TEXT_FIELDS})


def _ry3x(reduced=True, overrides=None, sets=SETS):
    return SimpleNamespace(
        articles=[SimpleNamespace(id=i, code=c, product_id="p") for i, c in CODES.items()],
        base_length_overrides=dict(overrides or {}),
        article_sets=[SimpleNamespace(id=n, article_ids=ids) for n, ids in sets],
        engineering=SimpleNamespace(families=[SimpleNamespace(members=[
            _member(i, c[:5] if reduced else "") for i, c in CODES.items()])]),
    )


def _xocd(price_bases=None):
    xocd = XocdExportService(SimpleNamespace())
    xocd._price_base_of = lambda snapshot: dict(price_bases or {})
    return xocd


def test_bases_sharing_article_sets_stay_distinct():
    ident = resolve_base_identities(_ry3x())
    assert list(ident.bases) == ["RY3XS", "RY3XT"]
    assert ident.bases["RY3XS"].article_ids == ["s1", "s2", "s3"]
    assert ident.bases["RY3XT"].article_ids == ["t1", "t2", "t3"]


def test_a_base_in_several_article_sets_is_one_identity_with_both_sets_recorded():
    ident = resolve_base_identities(_ry3x())
    assert ident.bases["RY3XS"].set_ids == ["RY3X", "RY3X_2"]
    assert ident.bases["RY3XT"].set_ids == ["RY3X", "RY3X_2"]


def test_identity_does_not_depend_on_article_set_layout():
    swapped = [("RY3X_2", ["s1", "t3"]), ("RY3X", ["s2", "s3", "t1", "t2"])]
    base = resolve_base_identities(_ry3x())
    assert base.by_article == resolve_base_identities(_ry3x(sets=swapped)).by_article
    assert base.entries == resolve_base_identities(_ry3x(sets=[])).entries


def test_reduced_article_beats_override_and_price_base():
    snap = _ry3x(overrides={"RY3XSDABAD.C0812": 8})
    prices = {c: c[:4] for c in CODES.values()}      # a set-level 4-char base would merge S and T
    ident = resolve_base_identities(snap, prices)
    assert set(ident.bases) == {"RY3XS", "RY3XT"}
    assert set(ident.sources.values()) == {"reduced_article"}


def test_override_beats_price_base_when_no_reduced_article():
    snap = _ry3x(reduced=False, overrides={c: 5 for c in CODES.values()})
    ident = resolve_base_identities(snap, {c: c[:4] for c in CODES.values()})
    assert set(ident.bases) == {"RY3XS", "RY3XT"}
    assert set(ident.sources.values()) == {"base_length_override"}


def test_price_base_is_only_the_fallback_and_can_merge_bases():
    ident = resolve_base_identities(_ry3x(reduced=False), {c: c[:4] for c in CODES.values()})
    assert list(ident.bases) == ["RY3X"]             # the hazard that explicit bases avoid
    assert set(ident.sources.values()) == {"price_base"}


def test_unresolved_member_yields_empty_base_and_is_not_an_identity():
    ident = resolve_base_identities(_ry3x(reduced=False), {})
    assert ident.bases == {} and all(base == "" for _a, base in ident.entries)


def test_divergence_from_the_price_base_is_reported_not_rekeyed():
    ident = resolve_base_identities(_ry3x(), {"RY3XSDABAD.C0812": "RY3X"})
    assert ident.divergences == [("s1", "RY3XS", "RY3X")]
    assert ident.by_article["s1"] == "RY3XS"


def test_case_insensitive_collisions_are_reported():
    snap = _ry3x()
    snap.engineering.families[0].members[3].reduced_article = "ry3xs"
    assert resolve_base_identities(snap).case_collisions == [("RY3XS", "ry3xs")]


def test_explicit_base_tiers_for_the_articles_page():
    member = SimpleNamespace(reduced_article="")
    assert explicit_base(member, "ABCDEF", {}) == ("", "")
    assert explicit_base(member, "ABCDEF", {"ABCDEF": 3}) == ("ABC", "base_length_override")
    member.reduced_article = " AB "
    assert explicit_base(member, "ABCDEF", {"ABCDEF": 3}) == ("AB", "reduced_article")


def test_full_series_and_incremental_exports_resolve_the_same_bases():
    snap = _ry3x()
    snap.articles.append(SimpleNamespace(id="x", code="ZZZ1.01", product_id="p"))
    snap.engineering.families[0].members.append(_member("x", ""))
    prices = {"ZZZ1.01": "ZZZ"}
    xocd = _xocd(prices)
    incremental = ArticleMdbExportService(SimpleNamespace(xocd_export_service=xocd))
    full = xocd._base_codes(snap)
    assert full == ["RY3XS", "RY3XT", "ZZZ"]
    assert [r["code"] for r in incremental._base_articles(snap)] == full
    picked = {"s1", "t3", "x"}
    assert [r["code"] for r in incremental._base_articles(snap, picked)] == xocd._base_codes(snap, picked)
    assert xocd.base_code_entries(snap) == resolve_base_identities(snap, prices).entries


def test_class_standardisation_gives_one_class_set_per_base_whatever_the_sets():
    def run(sets):
        snap = class_snapshot()
        snap.engineering.families = [SimpleNamespace(members=[
            SimpleNamespace(id=f"m{n}", article_id=a.id, reduced_article=r)
            for n, (a, r) in enumerate(zip(snap.articles, ("AAA", "AAA", "BBB", "CCC")))])]
        snap.article_sets = [SimpleNamespace(id=n, article_ids=ids, properties=[], options=[])
                             for n, ids in sets]
        ctx = SimpleNamespace(
            xocd_export_service=_xocd(),
            material_picking_service=SimpleNamespace(ensure_package_defaults=lambda s: None))
        EngineeringClassService(ctx).standardise_by_base_article(snap)
        return snap

    first = run([("S1", ["a1", "a3"]), ("S2", ["a2", "a4"])])     # AAA and BBB share a set
    second = run([("X", ["a1", "a2", "a3", "a4"])])
    names = sorted(c.name for c in first.engineering.classes)
    assert names == sorted(c.name for c in second.engineering.classes)
    assert names.count("AAA_ATTRIBUTE") == 1 and "S1_ATTRIBUTE" not in names
    assert sorted({n.rsplit("_", 1)[0] for n in names}) == ["AAA", "BBB", "CCC"]
