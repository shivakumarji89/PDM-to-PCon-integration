from services.syteline_export.item_selection_query import (
    ItemSelection,
    build_item_selection_query,
)


def test_placeholder_count_matches_bound_parameters_for_supported_scopes():
    selections = [
        ItemSelection(site_id=1, catalogue_id=2, language_id=3, other_language_id=4),
        ItemSelection(
            site_id=1, catalogue_id=2, language_id=3, other_language_id=4,
            active_only=True, export_base_prices=False,
        ),
        ItemSelection(
            site_id=1, catalogue_id=2, language_id=3, other_language_id=4,
            scope_mode="products", product_code_id=5,
        ),
        ItemSelection(
            site_id=1, catalogue_id=2, language_id=3, other_language_id=4,
            scope_mode="range", min_item="A", max_item="Z",
        ),
        ItemSelection(
            site_id=1, catalogue_id=2, language_id=3, other_language_id=4,
            scope_mode="list", item_list=("A", "B"),
        ),
        ItemSelection(
            site_id=1, catalogue_id=2, language_id=3, other_language_id=4,
            active_only=True, exclude_superproducts=True,
        ),
    ]
    for selection in selections:
        query = build_item_selection_query(selection)
        assert query.sql.count("?") == len(query.parameters), selection


def test_superproduct_exclusion_selects_parent_status_without_corrupting_where():
    query = build_item_selection_query(ItemSelection(
        site_id=1,
        catalogue_id=2,
        language_id=3,
        other_language_id=4,
        active_only=True,
        exclude_superproducts=True,
    ))

    assert "INNER JOIN ItemComponents itco ON Item.ItemId = itco.SubItemId" in query.sql
    assert "INNER JOIN Item sp_item ON itco.ItemId = sp_item.ItemId" in query.sql
    assert "sp_item.Status AS Status" in query.sql
    assert "AND Item.Status = 1" in query.sql
    assert "AND sp_item.Status = 1" in query.sql
    assert "0 AS Status = 1" not in query.sql
    assert query.sql.count("?") == len(query.parameters)


def test_list_scope_rejects_empty_blank_and_duplicate_items():
    import pytest

    base = dict(site_id=1, catalogue_id=2, language_id=3, other_language_id=4,
                scope_mode="list")
    for item_list in ((), ("",), ("ITEM-1", "  "), ("ITEM-1", " ITEM-1 ")):
        with pytest.raises(ValueError, match="List scope"):
            build_item_selection_query(ItemSelection(**base, item_list=item_list))


def test_range_scope_rejects_reversed_endpoints():
    import pytest

    with pytest.raises(ValueError, match="must not sort after"):
        build_item_selection_query(ItemSelection(
            site_id=1,
            catalogue_id=2,
            language_id=3,
            other_language_id=4,
            scope_mode="range",
            min_item="Z",
            max_item="A",
        ))
