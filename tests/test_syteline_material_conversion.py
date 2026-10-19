from services.syteline_export.material_conversion import (
    LegacyMaterialConversionRegistry,
    normalize_legacy_option_report_rows,
    order_legacy_option_report_rows,
    reconcile_legacy_option_child_ids,
    resolve_legacy_parent_material,
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



def test_option_report_order_matches_legacy_sort_keys():
    rows = [
        {"Range2": "R", "Product2": "P", "DisplayOrder": 1, "OrderCodeValue2": "A", "DisplayOrdinal": 1},
        {"Range2": "R", "Product2": "P", "DisplayOrder": 1, "OrderCodeValue2": "LONG", "DisplayOrdinal": 2},
        {"Range2": "R", "Product2": "P", "DisplayOrder": 0, "OrderCodeValue2": "Z", "DisplayOrdinal": 3},
        {"Range2": "A", "Product2": "P", "DisplayOrder": 9, "OrderCodeValue2": "Z", "DisplayOrdinal": 4},
    ]
    ordered = order_legacy_option_report_rows(rows)
    assert [row["DisplayOrdinal"] for row in ordered] == [4, 3, 2, 1]


def test_of_item_option_order_uses_legacy_9b_length_adjustment():
    rows = [
        {"Range2": "R", "Product2": "P", "DisplayOrder": 1, "OrderCodeValue2": "9B", "DisplayOrdinal": 1},
        {"Range2": "R", "Product2": "P", "DisplayOrder": 1, "OrderCodeValue2": "XYZ", "DisplayOrdinal": 2},
    ]
    ordinary = order_legacy_option_report_rows(rows, item_code="ITEM")
    of_ordered = order_legacy_option_report_rows(rows, item_code="OF123")
    assert [row["DisplayOrdinal"] for row in ordinary] == [2, 1]
    assert [row["DisplayOrdinal"] for row in of_ordered] == [1, 2]



def test_duplicate_option_rows_replace_missing_child_sentinel_with_real_child():
    rows = [
        {
            "OptionValueId": 10, "OptionId": 2, "IsFabric": 0,
            "OptDescId": 3, "optvalDescId": 4, "OrderCodeValue2": "LEG",
            "ParentOptValId": None, "OptChildCount": 1, "OptChildId": None,
            "optval_name": "Leg",
        },
        {
            "OptionValueId": 10, "OptionId": 2, "IsFabric": 0,
            "OptDescId": 3, "optvalDescId": 4, "OrderCodeValue2": "LEG",
            "ParentOptValId": None, "OptChildCount": 1, "OptChildId": 77,
            "optval_name": "Leg",
        },
    ]
    merged = reconcile_legacy_option_child_ids(rows)
    assert len(merged) == 1
    assert merged[0]["ResolvedChildOptionIds"] == (77,)


def test_duplicate_option_rows_keep_distinct_real_child_ids():
    rows = [
        {
            "OptionValueId": 11, "OptionId": 2, "IsFabric": 0,
            "OptDescId": 3, "optvalDescId": 4, "OrderCodeValue2": "LEG",
            "ParentOptValId": None, "OptChildCount": 2, "OptChildId": 77,
            "optval_name": "Leg",
        },
        {
            "OptionValueId": 11, "OptionId": 2, "IsFabric": 0,
            "OptDescId": 3, "optvalDescId": 4, "OrderCodeValue2": "LEG",
            "ParentOptValId": None, "OptChildCount": 2, "OptChildId": 78,
            "optval_name": "Leg",
        },
    ]
    merged = reconcile_legacy_option_child_ids(rows)
    assert merged[0]["ResolvedChildOptionIds"] == (77, 78)


def test_parent_material_substitution_uses_matching_parent_and_containment_rule():
    parents = [
        {"OptionValueId": 10, "Material": "PARENT-LEG-01"},
        {"OptionValueId": 11, "Material": "OTHER"},
    ]
    assert resolve_legacy_parent_material("LEG", 3, 10, parents) == ("PARENT-LEG-01", True)
    assert resolve_legacy_parent_material("LEG", 3, 11, parents) == ("LEG", True)
    assert resolve_legacy_parent_material("LEG", 3, 99, parents) == ("LEG", False)


def test_parent_material_substitution_preserves_legacy_special_option_cases():
    parents = [{"OptionValueId": 10, "Material": "PARENT-MATERIAL"}]
    assert resolve_legacy_parent_material("LEG", 9275, 10, parents) == ("PARENT-MATERIAL", True)
    assert resolve_legacy_parent_material("GHS-OLD", 8, 10, parents) == ("PARENT-MATERIAL", True)
    assert resolve_legacy_parent_material("GHG-OLD", 9487, 10, parents) == ("PARENT-MATERIAL", True)
    assert resolve_legacy_parent_material("OTHER", 8, 10, parents) == ("OTHER", True)


def test_parent_material_substitution_rejects_invalid_parent_ids():
    import pytest
    with pytest.raises(ValueError, match="Invalid parent OptionValueId"):
        resolve_legacy_parent_material("LEG", 3, 10, [{"OptionValueId": "bad", "Material": "P"}])



def test_dependency_material_code_obeys_legacy_dependency_guards_and_format():
    from services.syteline_export.material_conversion import build_legacy_dependency_material

    args = dict(
        item_code="ITEM-1", parent_material="PARENT", feature_position="2|Oak Leg",
        option_position=3, option_value_id=55, child_option_count=1,
    )
    assert build_legacy_dependency_material(**args) == "9-PARENT-[opt3]-Oak_Leg"
    assert build_legacy_dependency_material(**{**args, "is_fabric": True}) is None
    assert build_legacy_dependency_material(**{**args, "ignore_option_dependencies": True}) is None
    assert build_legacy_dependency_material(**{**args, "child_option_count": 0}) is None


def test_dependency_material_code_handles_superproduct_and_mrfn_rules():
    from services.syteline_export.material_conversion import build_legacy_dependency_material

    args = dict(
        item_code="CURRENT-ITEM", parent_material="MRFN-PARENT", feature_position="4|A B",
        option_position=2, option_value_id=300464, parent_option_code="PARENT-OPT",
        child_option_count=1,
    )
    assert build_legacy_dependency_material(**args) == "9-MRFN-PARENT-[opt2]-A_B-PARENT-OPT"
    assert build_legacy_dependency_material(**{**args, "is_superproduct": True}) == "9-CURRENT-ITEM-[opt2]-A_B-PARENT-OPT"
    assert build_legacy_dependency_material(**{**args, "is_superproduct": True, "use_resolved_superproduct_parent": True}) == "9-MRFN-PARENT-[opt2]-A_B-PARENT-OPT"



def test_parent_material_substitution_does_not_match_empty_current_material_by_containment():
    parents = [{"OptionValueId": 10, "Material": "PARENT-MATERIAL"}]
    assert resolve_legacy_parent_material("", 3, 10, parents) == ("", True)


def test_dependency_material_code_rejects_malformed_feature_position():
    import pytest
    from services.syteline_export.material_conversion import build_legacy_dependency_material

    with pytest.raises(ValueError, match="feature_position"):
        build_legacy_dependency_material(
            item_code="ITEM", parent_material="PARENT", feature_position="bad",
            option_position=1, option_value_id=9, child_option_count=1,
        )
