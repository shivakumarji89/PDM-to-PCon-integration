"""Protocol contract between the Workbench and the pCon.planner plugin."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from services.pcon_sdk_obx import protocol
from services.pcon_sdk_obx.protocol import (
    ArticleProperty,
    CatalogPackage,
    GenerationPlan,
    GenerationResult,
    PluginProtocolError,
    PropertyRule,
    ArticleSelection,
)

PLUGIN_DIR = Path(__file__).resolve().parents[1] / "tools" / "pcon_obx_plugin"


def test_request_envelope_carries_version_id_and_kind():
    body = protocol.build_request("abc", protocol.KIND_ARTICLES, {"packageName": "::mk::demo::1"})
    assert body == {"protocolVersion": protocol.PROTOCOL_VERSION, "id": "abc",
                    "kind": "articles", "packageName": "::mk::demo::1"}
    assert json.loads(protocol.encode(body)) == body


def test_parse_result_rejects_bad_json_wrong_id_version_and_failure():
    with pytest.raises(PluginProtocolError, match="not valid JSON"):
        protocol.parse_result("{", "x")
    with pytest.raises(PluginProtocolError, match="does not match"):
        protocol.parse_result(json.dumps({"id": "y", "protocolVersion": 1, "ok": True}), "x")
    with pytest.raises(PluginProtocolError, match="protocol version"):
        protocol.parse_result(json.dumps({"id": "x", "protocolVersion": 99, "ok": True}), "x")
    with pytest.raises(PluginProtocolError, match="planner says no"):
        protocol.parse_result(json.dumps({"id": "x", "protocolVersion": 1, "ok": False,
                                          "error": "planner says no"}), "x")
    data = protocol.parse_result(json.dumps({"id": "x", "protocolVersion": 1, "ok": True, "n": 1}), "x")
    assert data["n"] == 1


def test_catalog_package_splits_program_ids_and_builds_label():
    package = CatalogPackage.from_dict({"packageName": "::eg::office::2", "manufacturerId": "EG",
                                        "programIds": "AX;BX", "programName": "Office", "type": "Catalog"})
    assert package.program_ids == ("AX", "BX")
    assert package.label == "Office [AX,BX]"


def test_article_property_marks_choice_properties():
    prop = ArticleProperty.from_dict({"key": "Material", "type": "Choice",
                                      "choices": [{"key": "W", "text": "Wood"}]})
    assert prop.is_choice and prop.choices[0].text == "Wood"
    assert not ArticleProperty.from_dict({"key": "H", "type": "Length"}).is_choice


def test_property_rule_validation():
    with pytest.raises(ValueError):
        PropertyRule(key="Material", mode="random")
    with pytest.raises(ValueError):
        PropertyRule(key="Material", mode=protocol.MODE_FIXED)
    assert PropertyRule(key="Material", mode=protocol.MODE_VARY).to_dict()["mode"] == "vary"


def test_generation_plan_serialises_for_the_plugin():
    plan = GenerationPlan(
        manufacturer_id="MK", series_id="DM", catalog_package="::mk::demo::1",
        articles=(ArticleSelection("CHAIR1", "", "::mk::demo::1"),),
        rules=(PropertyRule("Material", protocol.MODE_VARY),),
        output_path="out.obx", max_configurations=10,
    )
    body = plan.to_dict()
    assert body["articles"] == [{"articleNumber": "CHAIR1", "variantCode": "", "packageName": "::mk::demo::1"}]
    assert body["properties"] == [{"key": "Material", "mode": "vary", "valueKey": ""}]
    assert body["maxConfigurations"] == 10 and body["discardUnsavedPlanning"] is False
    assert body["varyAll"] is True and body["deduplicate"] is True


def test_generation_result_counts_only_ok_rows():
    result = GenerationResult.from_dict({
        "outputPath": "x.obx", "exported": True,
        "configurations": [
            {"index": 1, "baseArticle": "A", "finalArticle": "A 1", "status": "ok",
             "assignments": [{"key": "K", "name": "Key", "valueKey": "v", "valueText": "Value"}]},
            {"index": 2, "baseArticle": "A", "finalArticle": "", "status": "error", "message": "no number"},
        ],
    })
    assert result.generated == 1
    assert result.configurations[0].configuration_text == "Key=Value"


def test_csharp_plugin_mirrors_protocol_constants():
    """The C# side must agree on the version, kinds, modes and file names."""
    source = (PLUGIN_DIR / "JobProtocol.cs").read_text(encoding="utf-8")
    assert re.search(rf"ProtocolVersion = {protocol.PROTOCOL_VERSION};", source)
    for name in (protocol.KIND_PING, protocol.KIND_CATALOG, protocol.KIND_ARTICLES,
                 protocol.KIND_PROPERTIES, protocol.KIND_GENERATE,
                 protocol.MODE_DEFAULT, protocol.MODE_FIXED, protocol.MODE_VARY,
                 protocol.HEARTBEAT_FILE, protocol.REQUEST_SUFFIX, protocol.RESULT_SUFFIX,
                 protocol.PROGRESS_SUFFIX, protocol.CANCEL_SUFFIX):
        assert f'"{name}"' in source, name


def test_plugin_manifest_identity_matches_plugin_class():
    """X3gGetGlobalIdentifier/X3gGetName/X3gGetVendor must match the plugin XML."""
    manifest = (PLUGIN_DIR / "res" / "MKObxGenerator.xml").read_text(encoding="utf-8")
    main = (PLUGIN_DIR / "PluginMain.cs").read_text(encoding="utf-8")
    plugin_id = re.search(r'<plugin id="([^"]+)" hash="([^"]+)" version="([^"]+)"', manifest)
    assert plugin_id is not None
    name, hash_value, version = plugin_id.groups()
    assert f'X3gGetName() {{ return "{name}"; }}' in main
    assert f'X3gGetGlobalIdentifier() {{ return "{hash_value}"; }}' in main
    assert f'PluginVersion = "{version}"' in main
    vendor = re.search(r'vendorName="([^"]+)"', manifest).group(1)
    assert f'X3gGetVendor() {{ return "{vendor}"; }}' in main
