from services.syteline_export.material_conversion import (
    LegacyMaterialConversionRegistry,
    normalize_legacy_option_report_rows,
)


def test_registers_normalized_material_and_source_metadata():
    registry = LegacyMaterialConversionRegistry(previous_feature_length=5)
    result = registry.add(
        material="9-FAB-ABC-5-5#",
        description="Fabric",
        other_description="  ",
        status=1,
        dependent_option=True,
        is_superproduct=False,
        feature="F01",
        feature_length=-1,
        child_option_ids=[123, 456],
    )
    assert result is not None
    assert result.material == "9-FAB-ABC-5-5"
    assert result.description_key == "5-5"
    assert result.description == "Fabric"
    assert result.other_description == ""
    assert result.is_fabric is True
    assert result.dependent_option is True
    assert result.feature_length == 5
    assert result.child_feature_length == -1
    assert result.option_id == 123


def test_duplicate_or_already_exported_materials_are_ignored():
    registry = LegacyMaterialConversionRegistry(
        materials_on_item_tab=["9-F-EXIST"],
        previously_converted=["9-F-OLD"],
    )
    args = dict(
        description="x", other_description="", status=1,
        dependent_option=False, is_superproduct=False, feature="F01",
        feature_length=2, child_option_ids=[1],
    )
    assert registry.add("9-F-EXIST", **args) is None
    assert registry.add("9-F-OLD", **args) is None
    assert registry.add("9-F-NEW", **args) is not None
    assert registry.add("9-F-NEW", **args) is None
    assert len(registry.records) == 1


def test_special_description_keys_match_legacy_rules():
    registry = LegacyMaterialConversionRegistry()
    args = dict(
        description="d", other_description="other", status=2,
        dependent_option=False, is_superproduct=False, feature="F02",
        feature_length=3, child_option_ids=[7],
    )
    assert registry.add("9-FAB-5-5", **args).description_key == "5-5"
    assert registry.add("9-FAB-5-6", **args).description_key == "5-6"
    assert registry.add("9-MRFN-X-AJ-Z", **args).description_key == "AJ"


def test_requires_child_option_id():
    import pytest

    registry = LegacyMaterialConversionRegistry()
    with pytest.raises(ValueError, match="child option ID"):
        registry.add(
            "ABC", "desc", "", 1, False, False, "F01", 2, []
        )


def test_option_report_normalizes_legacy_matching_and_contrast_codes_and_fsc_marker():
    rows = normalize_legacy_option_report_rows([
        {"ParentOptValId": 149730, "OrderCodeValue2": "OAK", "fsccompliant": 1, "optval_name": "Oak"},
        {"ParentOptValId": 194397, "OrderCodeValue2": "ASH", "fsccompliant": 0, "optval_name": "Ash"},
        {"ParentOptValId": 12, "OrderCodeValue2": "BLK", "fsccompliant": 0, "optval_name": "Customers Own Fabric"},
    ])
    assert rows[0]["OrderCodeValue2"] == "mOAK"
    assert rows[0]["DisplayName"] == "Oak#"
    assert rows[1]["OrderCodeValue2"] == "cASH"
    assert rows[2]["OptChildCount"] == 1


def test_option_report_flattening_skips_hash_suffixed_values():
    rows = normalize_legacy_option_report_rows([
        {"ParentOptValId": 12, "OrderCodeValue2": "FAB#", "fsccompliant": 0, "optval_name": "Fabric"},
        {"ParentOptValId": 12, "OrderCodeValue2": "WOOD", "fsccompliant": 0, "optval_name": "Wood"},
    ], flatten_fabrics=True)
    assert [row["OrderCodeValue2"] for row in rows] == ["WOOD"]



def test_option_report_resolves_legacy_child_option_ids_and_sentinels():
    rows = normalize_legacy_option_report_rows([
        {"OptChildId": "42", "optval_name": "Leg", "OrderCodeValue2": "LEG", "fsccompliant": 0},
        {"OptChildId": None, "optval_name": "Customers Own Fabric", "OrderCodeValue2": "COF", "fsccompliant": 0},
        {"OptChildId": "", "optval_name": "Standard finish", "OrderCodeValue2": "STD", "fsccompliant": 0},
    ])
    assert rows[0]["ResolvedChildOptionIds"] == (42,)
    assert rows[1]["ResolvedChildOptionIds"] == (8512,)
    assert rows[2]["ResolvedChildOptionIds"] == (-2,)


def test_option_report_rejects_non_numeric_child_option_id():
    import pytest

    with pytest.raises(ValueError, match="Invalid OptChildId"):
        normalize_legacy_option_report_rows([
            {"OptChildId": "not-an-id", "optval_name": "Leg", "OrderCodeValue2": "LEG"}
        ])
