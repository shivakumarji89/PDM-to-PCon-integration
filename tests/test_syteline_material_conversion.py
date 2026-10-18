from services.syteline_export.material_conversion import LegacyMaterialConversionRegistry


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
    assert result.description_key == "ABC-5-5"
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
