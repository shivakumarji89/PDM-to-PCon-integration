from pathlib import Path

from services.syteline_export.legacy_output import (
    LegacyRecordDeduplicator,
    allocate_legacy_output_paths,
    normalize_legacy_record,
    remove_legacy_nonstandard_characters,
)


def test_standard_paths_match_legacy_names_and_csi_suffix(tmp_path):
    paths = allocate_legacy_output_paths(tmp_path, "PDMExport", "UK", "GBP")
    assert paths.item == tmp_path / "temp" / "PDMExport_item_data.txt"
    assert paths.material == tmp_path / "temp" / "PDMExport_material_data.txt"
    assert paths.superprod == tmp_path / "temp" / "PDMExport_superprod_data.txt"
    csi = allocate_legacy_output_paths(tmp_path, "PDMExport", "UK", "GBP", format_csi=True)
    assert csi.item.name == "PDMExport_item_data_csi.txt"
    assert csi.productcode.name == "PDMExport_productcode_data_csi.txt"


def test_miller_cad_paths_use_site_currency_and_optional_filename_suffix(tmp_path):
    default = allocate_legacy_output_paths(
        tmp_path, "b-ukGBP", "UK", "GBP", miller_cad=True
    )
    assert default.item == tmp_path / "b-ukGBP.asc"
    assert default.material == tmp_path / "o-ukGBP.asc"
    assert default.superprod is None
    custom = allocate_legacy_output_paths(
        tmp_path, "b-ukGBP_special", "UK", "GBP", miller_cad=True
    )
    assert custom.item == tmp_path / "b-ukGBP_special.asc"
    assert custom.material == tmp_path / "o-ukGBP_special.asc"


def test_legacy_character_filter_keeps_only_source_allow_list_and_controls():
    assert remove_legacy_nonstandard_characters("AéB🙂\tC\r\n") == "AB\tC\r\n"


def test_legacy_record_normalization_preserves_source_replacements():
    assert normalize_legacy_record("HAR-F\tBOCFAB-OF-2-HAR\té") == "H-F\tBOCFAB-OF-2-HAR\t"
    assert normalize_legacy_record("x-BOCFAB-y") == "x-BOCFAB-y"
    assert normalize_legacy_record("x-BOCFAB-OF-2-HAR") == "x-OF-2-HAR"


def test_item_records_are_deduplicated_and_9f_materials_deduplicate_by_first_field():
    dedupe = LegacyRecordDeduplicator()
    assert dedupe.accept("ITEM\tA", is_item=True)
    assert not dedupe.accept("ITEM\tA", is_item=True)
    assert dedupe.accept("9-FABC\tfeature1", is_item=False)
    assert not dedupe.accept("9-FABC\tfeature2", is_item=False)
    assert dedupe.accept("9-FDEF\tfeature1", is_item=False)


def test_non_item_records_are_not_globally_deduplicated():
    dedupe = LegacyRecordDeduplicator()
    assert dedupe.accept("MAT\tA", is_item=False)
    assert dedupe.accept("MAT\tA", is_item=False)
