from pathlib import Path

from services.syteline_export.config import SyteLineExportConfig


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
