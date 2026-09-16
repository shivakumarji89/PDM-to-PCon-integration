from services.engineering.legacy_pdm_reduction_engine import (
    LegacyPDMReductionEngine,
    ReductionProduct,
    products_from_pdm_rows,
)


def make_product(product_id, values, range_id=1, eligible=True):
    return ReductionProduct(
        product_id=product_id,
        product=f"P{product_id}",
        product_range_id=range_id,
        attribute_value_ids=frozenset(values),
        eligible=eligible,
    )


def test_legacy_match_requires_all_selected_values():
    engine = LegacyPDMReductionEngine()
    product = make_product(1, {10, 20, 30})
    assert engine.legacy_match(product, {10, 30})
    assert not engine.legacy_match(product, {10, 40})


def test_same_attribute_multiple_values_behaves_like_legacy_value_id_join():
    engine = LegacyPDMReductionEngine()
    product = make_product(1, {10, 11, 20})
    assert engine.legacy_match(product, {10, 11})


def test_range_scope_is_enforced_by_engine():
    engine = LegacyPDMReductionEngine()
    product = make_product(1, {10}, range_id=2)
    assert not engine.legacy_match(product, {10}, product_range_id=1)
    assert engine.legacy_match(product, {10}, product_range_id=2)


def test_discover_exact_group_and_common_values():
    engine = LegacyPDMReductionEngine()
    products = [
        make_product(1, {10, 20}),
        make_product(2, {10, 20}),
        make_product(3, {10, 20}),
        make_product(4, {10, 30}),
    ]
    groups = engine.discover_exact_groups(products)
    assert groups
    first = groups[0]
    assert first.product_ids == (1, 2, 3)
    assert first.common_attribute_value_ids == (10, 20)


def test_non_overlapping_selection_is_deterministic():
    engine = LegacyPDMReductionEngine()
    products = [
        make_product(1, {10, 20}),
        make_product(2, {10, 20}),
        make_product(3, {10, 20}),
        make_product(4, {10, 30}),
        make_product(5, {10, 30}),
    ]
    groups = engine.discover_exact_groups(products)
    selected = engine.select_non_overlapping_groups(groups)
    assert selected[0].product_ids == (1, 2, 3)


def test_ineligible_products_are_not_grouped():
    engine = LegacyPDMReductionEngine()
    products = [
        make_product(1, {10}, eligible=True),
        make_product(2, {10}, eligible=False),
    ]
    assert engine.discover_exact_groups(products) == ()


def test_products_from_pdm_rows_merges_attribute_rows():
    products = products_from_pdm_rows(
        [
            {"ProductId": 1, "Product": "P1", "ProductRangeId": 2, "AttributeValueId": 10},
            {"ProductId": 1, "Product": "P1", "ProductRangeId": 2, "AttributeValueId": 20},
        ]
    )
    assert len(products) == 1
    assert products[0].attribute_value_ids == frozenset({10, 20})
