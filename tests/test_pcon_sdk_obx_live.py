"""Genuine SDK integration test: requires pCon.planner with the plugin loaded.

Opt in with ``MK_PCON_SDK_LIVE=1``. Nothing here is mocked: the requests go
to the real MK OBX Generator plugin running inside pCon.planner, which calls
the Plugin SDK. Optional environment variables narrow the run:

* ``MK_PCON_SDK_PACKAGE`` - versioned package name (e.g. ``::hmx::nevi::1``)
* ``MK_PCON_SDK_ARTICLE`` - base article number to configure
* ``MK_PCON_SDK_OUTPUT``  - output .obx path (defaults to a temp file)
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from services.pcon_sdk_obx import (
    PconCatalogService,
    PconConfigurationService,
    PconObxGenerationService,
    PconPluginBridge,
)
from services.pcon_sdk_obx.configuration_service import MODE_VARY
from services.pcon_sdk_obx.protocol import PropertyRule

pytestmark = pytest.mark.skipif(
    os.environ.get("MK_PCON_SDK_LIVE") != "1",
    reason="Set MK_PCON_SDK_LIVE=1 with pCon.planner + MK OBX Generator plugin running.",
)


@pytest.fixture(scope="module")
def bridge():
    bridge = PconPluginBridge()
    if not bridge.is_plugin_alive():
        pytest.skip(f"Plugin not reachable: {bridge.describe_status()}")
    return bridge


def test_live_ping_reports_languages(bridge):
    info = bridge.ping()
    assert info["pluginVersion"]
    assert isinstance(info["languages"], list)


def test_live_catalogue_and_generation(bridge, tmp_path):
    catalog = PconCatalogService(bridge)
    packages = catalog.list_packages()
    assert packages, "pCon.planner reports no registered packages"
    wanted = os.environ.get("MK_PCON_SDK_PACKAGE", "")
    package = next((p for p in packages if p.package_name == wanted), None) if wanted else \
        next((p for p in packages if p.has_catalog), None)
    assert package is not None, "No package with a catalogue"

    articles = catalog.list_articles(package)
    assert articles, f"No catalogue articles in {package.package_name}"
    wanted_article = os.environ.get("MK_PCON_SDK_ARTICLE", "")
    article = next((a for a in articles if a.article_number == wanted_article), articles[0])

    series = package.program_ids[0] if len(package.program_ids) == 1 else ""
    info, properties = catalog.describe_article(package, article, series)
    assert info.final_number, "pCon.planner returned no final article number"
    selectable = PconConfigurationService.selectable_properties(properties)
    rules = [PropertyRule(selectable[0].key, MODE_VARY)] if selectable else []

    output = Path(os.environ.get("MK_PCON_SDK_OUTPUT") or tmp_path / "live.obx")
    plan = PconConfigurationService().build_plan(
        package=package, series_id=series, articles=[article], properties=properties,
        rules=rules, output_path=str(output), max_configurations=10, discard_unsaved_planning=True)
    outcome = PconObxGenerationService(bridge).generate(plan)
    assert outcome.result.exported, outcome.result.warnings
    assert outcome.validation is not None and outcome.validation.article_lines >= 1
    assert outcome.success, outcome.errors
