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
    rows = parse_legacy_tsv("Lang\tItem\tDescription\\n", "description")
    assert rows == (LEGACY_TSV_HEADERS["description"],)


def test_captured_legacy_planning_header_only_is_valid():
    header = "\t".join(LEGACY_TSV_HEADERS["planning"])
    assert parse_legacy_tsv(header + "\\n", "planning") == (
        LEGACY_TSV_HEADERS["planning"],
    )


def test_captured_legacy_superprod_rows_keep_19_columns():
    header = "\t".join(LEGACY_TSV_HEADERS["superprod"])
    sample = (
        "GE2HPS.\tHardware Pack / Rectangular Primary / Sliding\t1\tGEHCS."
        "\t1\tHardware Pack / Sliding Top Rail\t0"
        "\t" + "\t".join([""] * 12) + "\\n"
    )
    rows = parse_legacy_tsv(header + "\\n" + sample, "superprod")
    assert len(rows) == 2
    assert len(rows[1]) == 19  # 7 descriptive columns + FP1..FP12


def test_empty_item_output_is_allowed_without_guessing_its_schema():
    assert parse_legacy_tsv("", "item") == ()


def test_empty_known_output_is_rejected_because_header_is_missing():
    with pytest.raises(ValueError, match="expected a header row"):
        parse_legacy_tsv("", "description")


def test_known_output_rejects_unexpected_header():
    with pytest.raises(ValueError, match="header mismatch"):
        parse_legacy_tsv("Lang\tItem\tWrong\\n", "description")


def test_known_output_rejects_malformed_row_width():
    with pytest.raises(ValueError, match="row 2 has 2 columns"):
        parse_legacy_tsv("Lang\tItem\tDescription\\nEN\tA1\\n", "description")
