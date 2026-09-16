from types import SimpleNamespace

from models.article import Article
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.engineering.pdm_article_reduction_service import PDMArticleReductionService


def _snapshot(products):
    """Build the smallest snapshot needed by the reduction service.

    products: iterable of (product_id, code, functional_value_ids, range_name)
    """
    snapshot = Snapshot()
    snapshot.properties = [
        Property(
            id="functional",
            name="Functional",
            attribute_type=0,
            values=[
                PropertyValue(id=value_id, value=value_id, code="")
                for value_id in sorted(
                    {value for _pid, _code, values, _range in products for value in values}
                )
            ],
        ),
        Property(
            id="size",
            name="Size",
            attribute_type=0,
            values=[PropertyValue(id="SIZE", value="1200", code="1200")],
        ),
    ]
    snapshot.articles = [
        Article(
            id=f"item-{pid}",
            product_id=pid,
            code=f"{code}.TAIL",
        )
        for pid, code, _values, _range in products
    ]
    snapshot.product_property_value_ids = {
        pid: list(values) + ["SIZE"]
        for pid, _code, values, _range in products
    }
    snapshot.product_range = {pid: range_name for pid, _code, _values, range_name in products}
    return snapshot


def test_reduces_only_when_functional_filter_exactly_matches_prefix():
    products = [
        ("1", "RY3XAA", {"A"}, "Ratio"),
        ("2", "RY3XAB", {"A"}, "Ratio"),
        ("3", "RY3XBA", {"B"}, "Ratio"),
        ("4", "RY3XBB", {"B"}, "Ratio"),
    ]
    snapshot = _snapshot(products)

    result = PDMArticleReductionService(None).discover(snapshot)

    assert {g.base_article: set(g.product_ids) for g in result.groups} == {
        "RY3XA": {"1", "2"},
        "RY3XB": {"3", "4"},
    }
    assert all(g.filter_attribute_value_ids for g in result.groups)
    assert result.uncovered_product_ids == ()


def test_order_code_values_are_not_used_as_reduction_filters():
    products = [
        ("1", "ABCA", {"A"}, "Ratio"),
        ("2", "ABCB", {"A"}, "Ratio"),
        ("3", "ABCC", {"B"}, "Ratio"),
    ]
    snapshot = _snapshot(products)

    result = PDMArticleReductionService(None).discover(snapshot)

    assert {g.base_article for g in result.groups} == {"ABCA", "ABCB"} or not result.groups
    assert all("SIZE" not in g.filter_attribute_value_ids for g in result.groups)


def test_apply_changes_only_member_reduced_article():
    products = [
        ("1", "RY3XAA", {"A"}, "Ratio"),
        ("2", "RY3XAB", {"A"}, "Ratio"),
    ]
    snapshot = _snapshot(products)
    snapshot.engineering.families = [
        SimpleNamespace(
            members=[
                SimpleNamespace(article_id="item-1", reduced_article="OLD"),
                SimpleNamespace(article_id="item-2", reduced_article="OLD"),
            ]
        )
    ]

    result = PDMArticleReductionService(None).apply(snapshot)

    assert len(result.groups) == 1
    assert [m.reduced_article for m in snapshot.engineering.families[0].members] == ["RY3XA", "RY3XA"]
    assert [a.code for a in snapshot.articles] == ["RY3XAA.TAIL", "RY3XAB.TAIL"]
