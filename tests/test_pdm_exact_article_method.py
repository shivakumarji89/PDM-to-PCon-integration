from dataclasses import dataclass

from services.engineering.pdm_exact_article_method import (
    build_pdm_exact_article_index,
    extract_pdm_exact_article_code,
)


@dataclass
class Article:
    id: str
    product_id: str
    code: str


def test_extracts_only_the_source_code_before_first_dot():
    row = extract_pdm_exact_article_code(
        "ABC.123.456", article_id=7, product_id=9, source_order=3
    )

    assert row.article_id == "7"
    assert row.product_id == "9"
    assert row.source_code == "ABC.123.456"
    assert row.match_key == "ABC"
    assert row.suffix == "123.456"
    assert row.source_order == 3


def test_code_without_dot_matches_full_source_code():
    row = extract_pdm_exact_article_code("ABC123")

    assert row.source_code == "ABC123"
    assert row.match_key == "ABC123"
    assert row.suffix == ""


def test_none_and_empty_codes_are_safe_and_not_normalized():
    none_row = extract_pdm_exact_article_code(None)
    empty_row = extract_pdm_exact_article_code("")
    spaced_row = extract_pdm_exact_article_code(" ABC.01 ")

    assert none_row.source_code == none_row.match_key == ""
    assert empty_row.source_code == empty_row.match_key == ""
    assert spaced_row.source_code == " ABC.01 "
    assert spaced_row.match_key == " ABC"


def test_index_preserves_source_order_and_reports_duplicate_keys():
    articles = [
        Article("1", "p1", "ABC.01"),
        Article("2", "p2", "XYZ"),
        Article("3", "p3", "ABC.02"),
    ]

    index = build_pdm_exact_article_index(articles)

    assert [row.article_id for row in index.rows] == ["1", "2", "3"]
    assert [row.source_order for row in index.rows] == [0, 1, 2]
    assert index.duplicate_keys == ("ABC",)
    assert [row.source_code for row in index.by_match_key["ABC"]] == [
        "ABC.01", "ABC.02"
    ]
    assert index.by_article_id["2"].match_key == "XYZ"


def test_multiple_dots_use_only_the_first_as_the_separator():
    row = extract_pdm_exact_article_code("A.B.C")

    assert row.match_key == "A"
    assert row.suffix == "B.C"
