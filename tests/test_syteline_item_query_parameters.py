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
