from services.syteline_export.item_selection_query import (
    ItemSelection,
    build_item_selection_query,
)


def test_catalogue_query_uses_bound_site_and_language_values_and_unreleased_union():
    query = build_item_selection_query(ItemSelection(
        site_id=3, catalogue_id=12, language_id=1, other_language_id=2,
    ))
    assert "pc.SiteId = ?" in query.sql
    assert "CatalogueItems.CatalogueId = ?" in query.sql
    assert " UNION " in query.sql
    assert "CatalogueItemsUnreleased" in query.sql
    assert 3 in query.parameters
    assert 12 in query.parameters
    assert "WHERE pc.SiteId = ?" in query.sql
    assert "WHERE pc.SiteId = 3" not in query.sql


def test_range_query_uses_bound_item_values_and_preserves_browning_exception():
    query = build_item_selection_query(ItemSelection(
        site_id=1, catalogue_id=2, language_id=3, other_language_id=4,
        scope_mode="range", min_item="A'1", max_item="Z",
    ))
    assert "Item.Item > ?" in query.sql
    assert "A'1" not in query.sql
    assert "A'1" in query.parameters

    brw = build_item_selection_query(ItemSelection(
        site_id=1, catalogue_id=2, language_id=3, other_language_id=4,
        scope_mode="range", min_item="BRW", max_item="BRW",
    ))
    assert "BREF.CL" not in brw.sql
    assert "BREF.CL" in brw.parameters


def test_product_and_list_scopes_are_parameterized():
    products = build_item_selection_query(ItemSelection(
        site_id=1, catalogue_id=2, language_id=3, other_language_id=4,
        scope_mode="products", product_code_id=55, active_only=True,
    ))
    assert "pc.ProductCodeId = ?" in products.sql
    assert 55 in products.parameters
    assert " UNION " not in products.sql

    listed = build_item_selection_query(ItemSelection(
        site_id=1, catalogue_id=2, language_id=3, other_language_id=4,
        scope_mode="list", item_list=("A'B", "C"),
    ))
    assert "Item.Item IN (?, ?)" in listed.sql
    assert "A'B" not in listed.sql
    assert "A'B" in listed.parameters


def test_invalid_scope_inputs_fail_before_sql_execution():
    import pytest

    with pytest.raises(ValueError, match="product code"):
        build_item_selection_query(ItemSelection(
            site_id=1, catalogue_id=2, language_id=3, other_language_id=4,
            scope_mode="products",
        ))
    with pytest.raises(ValueError, match="minimum and maximum"):
        build_item_selection_query(ItemSelection(
            site_id=1, catalogue_id=2, language_id=3, other_language_id=4,
            scope_mode="range", min_item="A",
        ))


def test_list_scope_binds_stripped_item_codes_matching_validation():
    query = build_item_selection_query(ItemSelection(
        site_id=1, catalogue_id=2, language_id=3, other_language_id=4,
        scope_mode="list", item_list=(" AB.1 ", "CD.2"), active_only=True,
    ))
    assert "Item.Item IN (?, ?)" in query.sql
    assert "AB.1" in query.parameters and " AB.1 " not in query.parameters
    assert query.sql.count("?") == len(query.parameters)
