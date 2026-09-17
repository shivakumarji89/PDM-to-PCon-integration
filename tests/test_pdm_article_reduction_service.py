from types import SimpleNamespace

from models.article_set import ArticleSet
from models.member_article import MemberArticle
from services.engineering.pdm_article_reduction_service import (
    PDMArticleReductionService,
    PDMAttributeValue,
)


class FakeLegacyRepository:
    def __init__(self, returned_by_xml):
        self.returned_by_xml = returned_by_xml
        self.calls = []

    def fetch_legacy_filtered_products(self, scope, language_id, xml, *, us_data=False):
        self.calls.append((scope, language_id, xml, us_data))
        return self.returned_by_xml.get(xml, ())


def value(value_id, attribute_id, *, name="", order_code_value=""):
    return PDMAttributeValue(
        str(value_id), str(attribute_id), f"A{attribute_id}", name, order_code_value
    )


def product(product_id, code, values, range_id=1, eligible=True):
    return SimpleNamespace(
        ProductId=product_id,
        Product=code,
        ProductRangeId=range_id,
        eligibility=eligible,
        attribute_values=tuple(values),
    )


def discover(products, returned=None):
    return PDMArticleReductionService(repository=FakeLegacyRepository(returned or {})).discover(products)


def test_valid_prefix_uses_common_functional_filter_and_exact_ids():
    products = [
        product(1, "ABC1.x", [value(10, 1), value(99, 9, order_code_value="W")]),
        product(2, "ABC2.y", [value(10, 1), value(99, 9, order_code_value="W")]),
    ]
    xml = '<attributes><attribute attributeid="1" attributevalueid="10"/></attributes>'
    results = discover(products, {xml: [SimpleNamespace(ProductId=1), SimpleNamespace(ProductId=2)]})
    assert any(r.base == "ABC" and r.product_ids == ("1", "2") for r in results)
    assert all(r.filter_attribute_value_ids == ("10",) for r in results if r.product_ids == ("1", "2"))


def test_ranges_never_mix():
    products = [product(1, "ABC1", [value(10, 1)], 1), product(2, "ABC2", [value(10, 1)], 2)]
    xml = '<attributes><attribute attributeid="1" attributevalueid="10"/></attributes>'
    results = discover(products, {xml: [SimpleNamespace(ProductId=1), SimpleNamespace(ProductId=2)]})
    assert not any(r.product_ids == ("1", "2") for r in results)


def test_order_code_and_size_values_are_excluded():
    products = [
        product(1, "ABC1", [value(10, 1), value(20, 2, order_code_value="100")]),
        product(2, "ABC2", [value(10, 1), value(20, 2, order_code_value="200")]),
    ]
    xml = '<attributes><attribute attributeid="1" attributevalueid="10"/></attributes>'
    results = discover(products, {xml: [SimpleNamespace(ProductId=1), SimpleNamespace(ProductId=2)]})
    assert any(r.base == "ABC" and r.filter_attribute_value_ids == ("10",) for r in results)


def test_extra_products_reject_candidate():
    products = [product(1, "ABC1", [value(10, 1)]), product(2, "ABC2", [value(10, 1)])]
    xml = '<attributes><attribute attributeid="1" attributevalueid="10"/></attributes>'
    repository = FakeLegacyRepository(
        {xml: [SimpleNamespace(ProductId=1), SimpleNamespace(ProductId=2), SimpleNamespace(ProductId=3)]}
    )
    results = PDMArticleReductionService(repository=repository).discover(products)
    assert results == ()
    assert repository.calls
    assert "attributevalueid=\"10\"" in repository.calls[0][2]


def test_product_id_set_equality_not_count_or_product_names():
    products = [product(1, "ABC1", [value(10, 1)]), product(2, "ABC2", [value(10, 1)])]
    xml = '<attributes><attribute attributeid="1" attributevalueid="10"/></attributes>'
    results = discover(products, {xml: [SimpleNamespace(ProductId=1), SimpleNamespace(ProductId=3)]})
    assert results == ()


def test_full_code_and_singleton_prefixes_are_never_legacy_validated():
    products = [
        product(1, "ABC1", [value(10, 1)]),
        product(2, "ABC2", [value(10, 1)]),
        product(3, "ABD3", [value(10, 1)]),
    ]
    xml = '<attributes><attribute attributeid="1" attributevalueid="10"/></attributes>'
    repository = FakeLegacyRepository(
        {
            xml: [
                SimpleNamespace(ProductId=1),
                SimpleNamespace(ProductId=2),
                SimpleNamespace(ProductId=3),
            ]
        }
    )
    results = PDMArticleReductionService(repository=repository).discover(products)
    assert results
    assert all(result.base not in {"ABC1", "ABC2", "ABD3"} for result in results)
    assert all(len(result.product_ids) >= 2 for result in results)
    assert repository.calls
    assert all(call[2] == xml for call in repository.calls)


def test_equivalent_valid_filters_are_reported_as_ambiguity():
    products = [
        product(1, "ABC1", [value(10, 1), value(11, 2)]),
        product(2, "ABC2", [value(10, 1), value(11, 2)]),
    ]
    combined = (
        '<attributes><attribute attributeid="1" attributevalueid="10"/>'
        '<attribute attributeid="2" attributevalueid="11"/></attributes>'
    )
    one = '<attributes><attribute attributeid="1" attributevalueid="10"/></attributes>'
    results = discover(
        products,
        {
            combined: [SimpleNamespace(ProductId=1), SimpleNamespace(ProductId=2)],
            one: [SimpleNamespace(ProductId=1), SimpleNamespace(ProductId=2)],
        },
    )
    abc = [r for r in results if r.base == "ABC"]
    assert abc and any(r.ambiguous_equivalent_filters for r in abc)


def test_equivalent_singleton_filter_is_reported_as_ambiguity():
    products = [
        product(1, "ABC1", [value(10, 1), value(11, 2)]),
        product(2, "ABC2", [value(10, 1), value(11, 2)]),
    ]
    combined = (
        '<attributes><attribute attributeid="1" attributevalueid="10"/>'
        '<attribute attributeid="2" attributevalueid="11"/></attributes>'
    )
    one = '<attributes><attribute attributeid="1" attributevalueid="10"/></attributes>'
    returned = {
        combined: [SimpleNamespace(ProductId=1), SimpleNamespace(ProductId=2)],
        one: [SimpleNamespace(ProductId=1), SimpleNamespace(ProductId=2)],
    }
    results = discover(products, returned)
    assert any(
        any(item.attribute_value_ids == ("10",) for item in result.ambiguous_equivalent_filters)
        for result in results
    )


def test_service_does_not_mutate_member_or_article_set():
    member = MemberArticle(id="m", article_id="a", reduced_article="OLD")
    article_set = ArticleSet(base_code="OLD", base_length=3, article_ids=["a"])
    products = [product(1, "ABC1", [value(10, 1)])]
    xml = '<attributes><attribute attributeid="1" attributevalueid="10"/></attributes>'
    discover(products, {xml: [SimpleNamespace(ProductId=1)]})
    assert member.reduced_article == "OLD"
    assert article_set.base_code == "OLD"
    assert article_set.base_length == 3


def test_us_validation_uses_category_scope_and_rejects_missing_category():
    products = [product(1, "ABC1", [value(10, 1)])]
    xml = '<attributes><attribute attributeid="1" attributevalueid="10"/></attributes>'
    repo = FakeLegacyRepository({xml: [SimpleNamespace(ProductId=1)]})
    service = PDMArticleReductionService(repository=repo)
    result = service.discover(products, us_data=True, product_category_id=77)
    assert result == ()
    assert repo.calls == []
    assert service.discover(products, us_data=True) == ()