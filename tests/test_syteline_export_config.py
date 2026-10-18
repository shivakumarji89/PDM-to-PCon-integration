from pathlib import Path

import pytest

from services.syteline_export.config import (
    LEGACY_TSV_HEADERS,
    SyteLineExportConfig,
    parse_legacy_tsv,
)


def make_config(tmp_path: Path, **overrides) -> SyteLineExportConfig:
    values = {
        "server": "sql.example",
        "database": "SyteLine",
        "output_directory": tmp_path,
        "site": "uk",
        "currency": "GBP",
        "options": frozenset({"products", "base_prices"}),
    }
    values.update(overrides)
    return SyteLineExportConfig(**values)


def test_valid_configuration_passes(tmp_path):
    assert make_config(tmp_path).validate() == ()


def test_range_requires_ordered_endpoints(tmp_path):
    errors = make_config(
        tmp_path, scope_mode="range", min_item="Z99", max_item="A01"
    ).validate()
    assert "First item must not sort after last item." in errors


def test_item_list_must_be_nonempty_and_unique(tmp_path):
    assert "At least one item code is required." in make_config(
        tmp_path, scope_mode="list"
    ).validate()
    assert "Item list contains duplicates." in make_config(
        tmp_path, scope_mode="list", item_list=("A1", "A1")
    ).validate()


def test_output_directory_must_exist(tmp_path):
    errors = make_config(tmp_path, output_directory=tmp_path / "missing").validate()
    assert "Output folder must already exist." in errors


def test_captured_legacy_description_header_only_is_valid():
    rows = parse_legacy_tsv("Lang\tItem\tDescription\n", "description")
    assert rows == (LEGACY_TSV_HEADERS["description"],)


def test_captured_legacy_planning_header_matches_legacy_source():
    expected = (
        "Item", "Description", "Product Code", "Vendor Call", "Stocked",
        "Dock to Stock", "Fixed lead time", "Planner Code", "Days Supply",
        "Safety Stock", "Buyer", "CustomH", "CustomW", "CustomD",
        "Gross Weight", "LocRank", "Location", "Origin Country", "Pack qty",
        "Accept Requirement", "Pass Requirement", "Kanban qty",
    )
    assert LEGACY_TSV_HEADERS["planning"] == expected
    assert len(expected) == 22


def test_captured_legacy_planning_header_only_is_valid():
    header = "\t".join(LEGACY_TSV_HEADERS["planning"])
    assert parse_legacy_tsv(header + "\n", "planning") == (
        LEGACY_TSV_HEADERS["planning"],
    )


def test_captured_legacy_superprod_rows_keep_19_columns():
    header = "\t".join(LEGACY_TSV_HEADERS["superprod"])
    sample = (
        "GE2HPS.\tHardware Pack / Rectangular Primary / Sliding\t1\tGEHCS."
        "\t1\tHardware Pack / Sliding Top Rail\t0"
        "\t" + "\t".join([""] * 12) + "\n"
    )
    rows = parse_legacy_tsv(header + "\n" + sample, "superprod")
    assert len(rows) == 2
    assert len(rows[1]) == 19  # 7 descriptive columns + FP1..FP12


@pytest.mark.parametrize(
    ("output_name", "expected_header"),
    [
        ("material", "Parent Item\tFeature\tComponent\tOpt code\tInc. price\tMatl Qty\tScrap fact\tSeq\tEffect Date\tObs Date\tOper Num\tBackFlush"),
        ("priceformula", "Site\tCustPriceCode\tItemPriceCode\tPriceFormula\tPriceFactor\tEffectiveDate"),
        ("productcode", "Site\tProductCode\tDescription\tPriceCode\tUnitCode"),
    ],
)
def test_additional_legacy_output_headers_match_source(output_name, expected_header):
    rows = parse_legacy_tsv(expected_header + "\n", output_name)
    assert rows == (LEGACY_TSV_HEADERS[output_name],)


def test_product_code_accepts_legacy_four_field_rows_under_five_field_header():
    header = "\t".join(LEGACY_TSV_HEADERS["productcode"])
    row = "UK\tABC\tExample\tGBP"
    rows = parse_legacy_tsv(header + "\n" + row + "\n", "productcode")
    assert rows[1] == ("UK", "ABC", "Example", "GBP")


def test_empty_item_output_is_allowed_without_guessing_its_schema():
    assert parse_legacy_tsv("", "item") == ()


def test_empty_known_output_is_rejected_because_header_is_missing():
    with pytest.raises(ValueError, match="expected a header row"):
        parse_legacy_tsv("", "description")


def test_known_output_rejects_unexpected_header():
    with pytest.raises(ValueError, match="header mismatch"):
        parse_legacy_tsv("Lang\tItem\tWrong\n", "description")


def test_known_output_rejects_malformed_row_width():
    with pytest.raises(ValueError, match="row 2 has 2 columns"):
        parse_legacy_tsv("Lang\tItem\tDescription\nEN\tA1\n", "description")


def test_legacy_thread_argument_mapping_preserves_scope_and_flags(tmp_path):
    config = make_config(
        tmp_path,
        site_id=2,
        catalogue_id=10,
        language_id=3,
        other_language_id=4,
        currency_id=5,
        product_code_id=8,
        scope_mode="list",
        item_list=("A1", "B2"),
        export_mode="csi",
        active_only=False,
        export_base_prices=False,
        export_bom_data=True,
        length5_feats=True,
        ignore_option_dependencies=True,
        unique_components=False,
        flatten_fabrics=True,
    )
    mapped = config.legacy_thread_arguments()
    assert mapped["siteId"] == 2
    assert mapped["catalogueId"] == 10
    assert mapped["languageId"] == 3
    assert mapped["otherlanguageId"] == 4
    assert mapped["productCodeId"] == 8
    assert mapped["productcheck"] is False
    assert mapped["rangecheck"] is False
    assert mapped["listcheck"] is True
    assert mapped["itemlist"] == ["A1", "B2"]
    assert mapped["syteline"] is False
    assert mapped["formatCSI"] is True
    assert mapped["exportBasePrices"] is False
    assert mapped["exportBOMData"] is True
    assert mapped["length5Feats"] is True
    assert mapped["ignoreOptDeps"] is True
    assert mapped["uniqueComponents"] is False
    assert mapped["flattenFabrics"] is True


def test_execution_validation_requires_live_database_ids(tmp_path):
    errors = make_config(tmp_path).validate_for_execution()
    assert "Site must be selected from live database choices." in errors
    assert "Catalogue must be selected from live database choices." in errors
    assert "Language must be selected from live database choices." in errors
    assert "Currency must be selected from live database choices." in errors


def test_catalogue_scope_maps_to_no_product_range_or_list_filters(tmp_path):
    config = make_config(tmp_path, scope_mode="catalogue")
    mapped = config.legacy_thread_arguments()
    assert mapped["productcheck"] is False
    assert mapped["rangecheck"] is False
    assert mapped["listcheck"] is False


@pytest.mark.parametrize("name", ["", "folder/name", "folder\\\\name"])
def test_output_prefix_must_be_a_single_file_name(tmp_path, name):
    assert "Output file name" in " ".join(make_config(tmp_path, output_file_name=name).validate())


def test_legacy_thread_mapping_includes_output_destination(tmp_path):
    config = make_config(tmp_path, output_file_name="PDMExport")
    mapped = config.legacy_thread_arguments()
    assert mapped["filename"] == "PDMExport"
    assert mapped["directory"] == str(tmp_path)


def test_default_export_flags_match_legacy_export_thread_constructor(tmp_path):
    config = make_config(tmp_path)
    mapped = config.legacy_thread_arguments()
    assert mapped["activeonly"] is False
    assert mapped["exportAllCataloguesInSite"] is False
    assert mapped["length5Feats"] is True
    assert mapped["uniqueComponents"] is False
