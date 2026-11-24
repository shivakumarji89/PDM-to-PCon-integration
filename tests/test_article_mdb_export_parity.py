"""Article incremental mapping parity with the Development/full MDB exporter."""

from types import SimpleNamespace

from services.article_mdb_export_service import ArticleMdbExportService


def _service(price_bases=None):
    xocd = SimpleNamespace(
        _price_base_of=lambda snapshot: dict(price_bases or {})
    )
    return ArticleMdbExportService(SimpleNamespace(xocd_export_service=xocd))


def _snapshot(articles, members):
    return SimpleNamespace(
        articles=articles,
        engineering=SimpleNamespace(
            families=[SimpleNamespace(members=members)]
        ),
    )


def _article(article_id, code):
    return SimpleNamespace(id=article_id, code=code)


def _member(article_id, reduced, **extra):
    values = {
        "id": f"member-{article_id}",
        "article_id": article_id,
        "reduced_article": reduced,
        "relation_object": "",
        "code_scheme": "",
        "short_description": "",
        "long_description": "",
    }
    values.update(extra)
    return SimpleNamespace(**values)


def test_no_dot_split_fallback_when_development_has_no_reduced_base():
    snapshot = _snapshot(
        [_article("a1", "AAA.01")],
        [_member("a1", "")],
    )

    assert _service()._base_articles(snapshot) == []


def test_missing_source_article_still_uses_member_reduced_base_like_development():
    snapshot = _snapshot(
        [],
        [_member("a1", "AAA")],
    )

    rows = _service()._base_articles(snapshot)

    assert [row["code"] for row in rows] == ["AAA"]
    assert rows[0]["source_ids"] == ["a1"]
    assert rows[0]["source_codes"] == []


def test_member_reduced_base_takes_precedence_over_price_base():
    """Canonical rule (approved): reduced_article, then base_length_overrides, then price base."""
    snapshot = _snapshot(
        [_article("a1", "AAA.01")],
        [_member("a1", "AAA_REDUCED")],
    )

    rows = _service({"AAA.01": "AAA"}) ._base_articles(snapshot)

    assert [row["code"] for row in rows] == ["AAA_REDUCED"]


def test_price_base_is_the_fallback_when_the_member_has_no_reduced_base():
    snapshot = _snapshot([_article("a1", "AAA.01")], [_member("a1", "")])

    rows = _service({"AAA.01": "AAA"})._base_articles(snapshot)

    assert [row["code"] for row in rows] == ["AAA"]


def test_code_scheme_name_matches_development_base_code_not_member_override():
    snapshot = _snapshot(
        [_article("a1", "AAA.01")],
        [_member("a1", "AAA", code_scheme="CUSTOM_SCHEME")],
    )

    rows = _service()._base_articles(snapshot)

    assert rows[0]["scheme_name"] == "AAA"


def test_selected_articles_keep_development_member_order_and_deduplicate_base_codes():
    snapshot = _snapshot(
        [_article("a1", "AAA.01"), _article("a2", "AAA.02"), _article("b1", "BBB.01")],
        [_member("a1", "AAA"), _member("a2", "AAA"), _member("b1", "BBB")],
    )

    rows = _service()._base_articles(snapshot, {"a2", "b1"})

    assert [row["code"] for row in rows] == ["AAA", "BBB"]
    assert rows[0]["source_ids"] == ["a2"]
