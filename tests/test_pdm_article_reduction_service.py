from types import SimpleNamespace

from models.article import Article
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.engineering.pdm_article_reduction_service import PDMArticleReductionService


def make_snapshot(rows, functional_values, ranges=None):
    """Build the smallest real Snapshot needed by the reduction service."""
    ranges = ranges or {}
    snapshot = Snapshot()
    snapshot.properties = [
        Property(
            id=attribute_id,
            name=f"A{attribute_id}",
            attribute_type=0,
            values=[PropertyValue(id=value_id, property_id=attribute_id, code=code)],
        )
        for attribute_id, value_id, code in functional_values
    ]
    snapshot.product_property_value_ids = {
        str(product_id): list(value_ids)
        for product_id, _code, value_ids in rows
    }
    snapshot.product_range = {
        str(product_id): str(ranges.get(product_id, "R"))
        for product_id, _code, _value_ids in rows
    }
    snapshot.articles = [
        Article(id=str(product_id), product_id=str(product_id), code=code)
        for product_id, code, _value_ids in rows
    ]
    return snapshot


def test_exact_filter_uses_complete_common_functional_intersection():
    snapshot = make_snapshot(
        [
            ("1", "ABC1.tail", ["10", "20"]),
            ("2", "ABC2.tail", ["10", "20"]),
            ("3", "ABD3.tail", ["11", "20"]),
        ],
        [("A", "10", ""), ("B", "20", "") , ("C", "11", "")],
    )

    result = PDMArticleReductionService(None).discover(snapshot)

    abc = next(group for group in result.groups if group.base_article == "ABC")
    assert abc.product_ids == ("1", "2")
    assert abc.filter_attribute_value_ids == ("10", "20")


def test_non_exact_common_intersection_is_rejected():
    snapshot = make_snapshot(
        [
            ("1", "ABC1.tail", ["10", "20"]),
            ("2", "ABC2.tail", ["10", "21"]),
            ("3", "ABD3.tail", ["10", "20", "21"]),
        ],
        [("A", "10", ""), ("B", "20", ""), ("C", "21", "")],
    )

    result = PDMArticleReductionService(None).discover(snapshot)

    assert not any(group.base_article == "ABC" for group in result.groups)


def test_order_code_values_are_not_functional_reduction_dimensions():
    snapshot = make_snapshot(
        [
            ("1", "ABC1.tail", ["10", "99"]),
            ("2", "ABC2.tail", ["10", "98"]),
        ],
        [("A", "10", ""), ("B", "99", "X"), ("C", "98", "Y")],
    )

    result = PDMArticleReductionService(None).discover(snapshot)

    abc = next(group for group in result.groups if group.base_article == "ABC")
    assert abc.filter_attribute_value_ids == ("10",)


def test_product_ranges_are_never_mixed():
    snapshot = make_snapshot(
        [
            ("1", "ABC1.tail", ["10"]),
            ("2", "ABC2.tail", ["10"]),
        ],
        [("A", "10", "")],
        ranges={"1": "R1", "2": "R2"},
    )

    result = PDMArticleReductionService(None).discover(snapshot)

    assert not any(group.base_article == "ABC" for group in result.groups)


def test_only_pre_dot_article_is_reduced():
    snapshot = make_snapshot(
        [
            ("1", "ABC1.0812SM", ["10"]),
            ("2", "ABC2.1012SM", ["10"]),
        ],
        [("A", "10", "")],
    )

    result = PDMArticleReductionService(None).discover(snapshot)

    assert any(group.base_article == "ABC" for group in result.groups)
    assert all("." not in group.base_article for group in result.groups)


def test_apply_changes_only_member_reduced_article():
    snapshot = make_snapshot(
        [
            ("1", "ABC1.tail", ["10"]),
            ("2", "ABC2.tail", ["10"]),
        ],
        [("A", "10", "")],
    )
    member1 = SimpleNamespace(article_id="1", reduced_article="OLD")
    member2 = SimpleNamespace(article_id="2", reduced_article="OLD")
    snapshot.engineering.families = [SimpleNamespace(members=[member1, member2])]

    result = PDMArticleReductionService(None).apply(snapshot)

    assert result.groups
    assert member1.reduced_article == "ABC"
    assert member2.reduced_article == "ABC"
    assert snapshot.articles[0].code == "ABC1.tail"
    assert snapshot.articles[1].code == "ABC2.tail"
