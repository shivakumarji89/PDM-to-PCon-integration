"""Catalogue, configuration-plan, generation and OBX validation services.

These run against ``tests/pcon_sdk_fake_plugin.py``, not pCon.planner. They
prove the Workbench side of the contract; real SDK behaviour is only covered
by ``tests/test_pcon_sdk_obx_live.py`` on a machine with the plugin loaded.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.progress import ProgressReporter
from services.pcon_sdk_obx import (
    BridgeSettings,
    PconCatalogService,
    PconConfigurationService,
    PconObxGenerationService,
    PconPluginBridge,
    PlanValidationError,
)
from services.pcon_sdk_obx.configuration_service import MODE_DEFAULT, MODE_FIXED, MODE_VARY
from services.pcon_sdk_obx.protocol import (
    ArticleProperty,
    CatalogArticle,
    GenerationResult,
    GeneratedConfiguration,
    PropertyAssignment,
    PropertyRule,
)
from services.pcon_sdk_obx.validation_service import ObxOutputValidator
from tests.pcon_sdk_fake_plugin import FakePconPlugin


@pytest.fixture
def bridge(tmp_path):
    settings = BridgeSettings(job_dir=tmp_path / "jobs", planner_exe="", plugin_install_dir=tmp_path / "plug",
                              request_timeout=10.0, generate_timeout=30.0, poll_interval=0.01)
    return PconPluginBridge(settings)


@pytest.fixture
def plugin(bridge):
    with FakePconPlugin(bridge.ensure_job_dir()) as fake:
        yield fake


@pytest.fixture
def catalog(bridge, plugin):
    return PconCatalogService(bridge)


def demo_package(catalog):
    packages = catalog.list_packages()
    return next(p for p in packages if p.package_name == "::mk::demo::1")


# ---------------------------------------------------------------- catalogue
def test_list_packages_groups_manufacturers_and_programs(catalog):
    packages = catalog.list_packages()
    assert [p.package_name for p in packages] == ["::eg::office::2", "::mk::demo::1", "::mk::found::1"]
    assert catalog.manufacturers(packages) == [("EG", "EasternGraphics"), ("MK", "MillerKnoll Demo")]
    programs = catalog.programs_for(packages, "MK")
    assert [p.label for p in programs] == ["Demo Seating [DM]"]   # Found packages have no catalogue


def test_list_articles_deduplicates_catalogue_references(catalog):
    articles = catalog.list_articles(demo_package(catalog))
    assert [a.article_number for a in articles] == ["BROKEN", "CHAIR1", "DUPE", "STOOL1"]
    assert articles[1].label == "Task chair"


def test_list_articles_reports_unknown_package(catalog):
    package = demo_package(catalog)
    bad = type(package)(**{**package.__dict__, "package_name": "::nope::1"})
    with pytest.raises(Exception, match="not registered"):
        catalog.list_articles(bad)


# --------------------------------------------------------------- properties
def test_describe_article_returns_live_properties(catalog):
    package = demo_package(catalog)
    info, properties = catalog.describe_article(package, CatalogArticle("CHAIR1"), "DM")
    assert info.final_number == "CHAIR1 WOS"
    keys = [p.key for p in properties]
    assert keys == ["Material", "Finish", "Size", "Height"]
    assert "Arm" not in keys   # only appears once Material=Metal (nested dependency)
    finish = next(p for p in properties if p.key == "Finish")
    assert [c.key for c in finish.choices] == ["Oak", "Walnut"]
    assert PconConfigurationService.selectable_properties(properties)[-1].key == "Size"


def test_dependent_property_changes_after_assignment(catalog):
    package = demo_package(catalog)
    _, properties = catalog.describe_article(
        package, CatalogArticle("CHAIR1"), "DM",
        assignments=(PropertyAssignment("Material", "Metal"),))
    finish = next(p for p in properties if p.key == "Finish")
    assert [c.key for c in finish.choices] == ["Silver"]
    assert finish.value_key == "Silver"
    assert any(p.key == "Arm" for p in properties)


# -------------------------------------------------------------------- plan
def make_properties():
    return [
        ArticleProperty.from_dict({"key": "Material", "name": "Material", "type": "Choice",
                                   "choices": [{"key": "Wood"}, {"key": "Metal"}]}),
        ArticleProperty.from_dict({"key": "Finish", "name": "Finish", "type": "Choice",
                                   "choices": [{"key": "Oak"}, {"key": "Walnut"}]}),
        ArticleProperty.from_dict({"key": "Size", "name": "Size", "type": "Choice",
                                   "choices": [{"key": "S"}, {"key": "L"}]}),
    ]


def test_build_plan_validates_inputs(catalog):
    package = demo_package(catalog)
    service = PconConfigurationService()
    props = make_properties()
    kwargs = dict(package=package, series_id="DM", articles=[CatalogArticle("CHAIR1")],
                  properties=props, rules=[], output_path="out.obx")
    with pytest.raises(PlanValidationError, match="at least one"):
        service.build_plan(**{**kwargs, "articles": []})
    with pytest.raises(PlanValidationError, match=".obx"):
        service.build_plan(**{**kwargs, "output_path": "out.txt"})
    with pytest.raises(PlanValidationError, match="Series"):
        service.build_plan(**{**kwargs, "series_id": "ZZ"})
    with pytest.raises(PlanValidationError, match="not part"):
        service.build_plan(**{**kwargs, "rules": [PropertyRule("Colour", MODE_VARY)]})
    with pytest.raises(PlanValidationError, match="not currently offered"):
        service.build_plan(**{**kwargs, "rules": [PropertyRule("Finish", MODE_FIXED, "Silver")]})
    with pytest.raises(PlanValidationError, match="twice"):
        service.build_plan(**{**kwargs, "rules": [PropertyRule("Size", MODE_VARY), PropertyRule("Size", MODE_VARY)]})
    plan = service.build_plan(**{**kwargs, "rules": [PropertyRule("Size", MODE_VARY)]})
    assert plan.rules == (PropertyRule("Size", MODE_VARY),)
    estimate = service.estimate(props, (PropertyRule("Material", MODE_VARY), PropertyRule("Finish", MODE_VARY)),
                                vary_all=False)
    assert (estimate.varied, estimate.upper_bound) == (2, 4)
    auto = service.estimate(props, (PropertyRule("Size", MODE_DEFAULT),), vary_all=True)
    assert (auto.varied, auto.upper_bound) == (2, 4)
    assert service.estimate(props, (), vary_all=True).upper_bound == 8


# --------------------------------------------------------------- generation
def generate(bridge, catalog, tmp_path, rules, articles=("CHAIR1",), max_configurations=50,
             inspect="CHAIR1", vary_all=False, **extra):
    package = demo_package(catalog)
    _, properties = catalog.describe_article(package, CatalogArticle(inspect), "DM")
    plan = PconConfigurationService().build_plan(
        package=package, series_id="DM", articles=[CatalogArticle(a) for a in articles],
        properties=properties, rules=rules, output_path=str(tmp_path / "out.obx"),
        max_configurations=max_configurations, vary_all=vary_all, **extra)
    return PconObxGenerationService(bridge).generate(plan, reporter=ProgressReporter())


# ---------------------------------------------------- automatic SKU mode
def test_automatic_mode_generates_every_valid_unique_sku(bridge, catalog, tmp_path, plugin):
    """No rules at all: every configurable property is varied, relations prune,
    and a property that only appears after a choice (Arm for Metal) is found."""
    outcome = generate(bridge, catalog, tmp_path, [], vary_all=True)
    finals = [c.final_article for c in outcome.result.configurations]
    assert finals == [
        "CHAIR1 WOS", "CHAIR1 WOL", "CHAIR1 WWS", "CHAIR1 WWL",
        "CHAIR1 MSSF", "CHAIR1 MSSA", "CHAIR1 MSLF", "CHAIR1 MSLA",
    ]
    # Naive Cartesian of the initial value sets would be 2*2*2 = 8 *different*
    # SKUs (Metal+Oak, Metal+Walnut...) and would never contain the Arm variants.
    assert all("Metal" not in c.configuration_text or "Arm" in c.configuration_text
               for c in outcome.result.configurations)
    assert outcome.result.visited >= len(finals)
    assert outcome.result.duplicates == 0 and outcome.result.skipped == 0
    assert outcome.success, outcome.errors
    assert outcome.validation.article_lines == 8
    assert len(set(finals)) == len(finals)
    assert plugin.requests[-1]["varyAll"] is True


def test_automatic_mode_honours_pinned_and_excluded_properties(bridge, catalog, tmp_path):
    outcome = generate(bridge, catalog, tmp_path,
                       [PropertyRule("Material", MODE_FIXED, "Metal"), PropertyRule("Size", MODE_DEFAULT)],
                       vary_all=True)
    finals = [c.final_article for c in outcome.result.configurations]
    assert finals == ["CHAIR1 MSSF", "CHAIR1 MSSA"]   # Size kept at default S, Material pinned


def test_duplicate_skus_are_removed(bridge, catalog, tmp_path):
    outcome = generate(bridge, catalog, tmp_path, [], articles=("DUPE",), inspect="DUPE", vary_all=True)
    finals = [c.final_article for c in outcome.result.configurations]
    assert finals == ["DUPE W", "DUPE M"]
    assert outcome.result.duplicates == 2
    assert outcome.validation.article_lines == 2


def test_cancellation_reaches_the_plugin(bridge, catalog, tmp_path, plugin):
    from core.cancellation import CancellationToken, OperationCancelled, cancellation_scope

    import time

    token = CancellationToken()

    def hook(_request):
        # Cancel from the Workbench side, then hold the plugin at the start of
        # the run until the cancel marker has reached the job folder, so the
        # enumeration sees it at its first node regardless of machine load.
        token.request_cancel()
        deadline = time.time() + 5
        while time.time() < deadline and not any(bridge.job_dir.glob("*.cancel")):
            time.sleep(0.01)

    plugin.generate_hook = hook
    with cancellation_scope(token):
        with pytest.raises(OperationCancelled):
            generate(bridge, catalog, tmp_path, [], vary_all=True)
    deadline = __import__("time").time() + 5
    while __import__("time").time() < deadline and any(bridge.job_dir.glob("*.cancel")):
        __import__("time").sleep(0.02)
    assert not any(bridge.job_dir.glob("*.cancel"))
    assert not (tmp_path / "out.obx").exists()


def test_reference_comparison_reports_parity(bridge, catalog, tmp_path):
    from services.pcon_sdk_obx import ReferenceObxComparer

    outcome = generate(bridge, catalog, tmp_path, [], vary_all=True)
    generated = Path(outcome.result.output_path)
    reference = tmp_path / "reference.obx"
    text = generated.read_text(encoding="utf-8")
    reference.write_text(text.replace("CHAIR1 MSLA", "CHAIR1 MSLZ"), encoding="utf-8")
    comparison = ReferenceObxComparer().compare(generated, reference)
    assert comparison.reference_lines == 8 and comparison.generated_lines == 8
    assert comparison.missing_in_generated == ["CHAIR1 MSLZ"]
    assert comparison.extra_in_generated == ["CHAIR1 MSLA"]
    assert not comparison.identical
    assert ReferenceObxComparer().compare(generated, generated).identical


def test_generation_respects_dependent_properties(bridge, catalog, tmp_path, plugin):
    outcome = generate(bridge, catalog, tmp_path,
                       [PropertyRule("Material", MODE_VARY), PropertyRule("Finish", MODE_VARY)])
    finals = [c.final_article for c in outcome.result.configurations]
    # Not a Cartesian 2x2=4: Metal only offers Silver, so 3 valid configurations
    # (explicit mode varies only Material and Finish; Arm keeps its default).
    assert finals == ["CHAIR1 WOS", "CHAIR1 WWS", "CHAIR1 MSSF"]
    assert outcome.success, outcome.errors
    assert outcome.validation.article_lines == 3
    assert outcome.validation.missing_final_articles == []
    assert plugin.plannings_started == 1
    assert Path(outcome.result.output_path).is_file()


def test_fixed_value_not_offered_is_skipped_not_forced(bridge, catalog, tmp_path):
    outcome = generate(bridge, catalog, tmp_path,
                       [PropertyRule("Material", MODE_VARY), PropertyRule("Finish", MODE_FIXED, "Oak")])
    finals = [c.final_article for c in outcome.result.configurations]
    assert finals == ["CHAIR1 WOS"]            # Metal+Oak is invalid and was skipped
    assert outcome.result.skipped == 1
    assert any("not offered" in w for w in outcome.result.warnings)


def test_vary_property_missing_on_second_article_is_ignored(bridge, catalog, tmp_path):
    outcome = generate(bridge, catalog, tmp_path, [PropertyRule("Finish", MODE_VARY)],
                       articles=("CHAIR1", "STOOL1"))
    finals = [c.final_article for c in outcome.result.configurations]
    assert finals == ["CHAIR1 WOS", "CHAIR1 WWS", "STOOL1 WS"]


def test_max_configurations_truncates(bridge, catalog, tmp_path):
    outcome = generate(bridge, catalog, tmp_path, [PropertyRule("Size", MODE_VARY)], max_configurations=1)
    assert outcome.result.truncated and outcome.result.generated == 1


def test_uninsertable_article_is_reported(bridge, catalog, tmp_path):
    outcome = generate(bridge, catalog, tmp_path, [], articles=("BROKEN",))
    assert not outcome.result.exported
    assert outcome.result.skipped == 1
    assert any("could not insert" in w for w in outcome.result.warnings)
    assert not outcome.success


def test_unsaved_planning_blocks_generation_unless_discard_allowed(bridge, catalog, tmp_path, plugin):
    plugin.document_modified = True
    with pytest.raises(Exception, match="unsaved changes"):
        generate(bridge, catalog, tmp_path, [])
    plugin.document_modified = True
    outcome = generate(bridge, catalog, tmp_path, [], discard_unsaved_planning=True)
    assert outcome.success


def test_export_failure_is_an_error(bridge, catalog, tmp_path, plugin):
    plugin.fail_export = True
    outcome = generate(bridge, catalog, tmp_path, [])
    assert not outcome.success and "did not succeed" in outcome.errors[0]


def test_truncated_obx_fails_validation(bridge, catalog, tmp_path, plugin):
    plugin.truncate_obx = True
    outcome = generate(bridge, catalog, tmp_path, [PropertyRule("Size", MODE_VARY)])
    assert not outcome.success
    assert outcome.validation is not None and not outcome.validation.well_formed


# -------------------------------------------------------------- validation
def test_validator_cross_checks_expected_articles(tmp_path):
    obx = tmp_path / "v.obx"
    obx.write_text(
        "<cutBuffer><items>"
        "<bskArticle itemType='BasketArticle'><artNr type='base'>A</artNr><artNr type='final'>A X</artNr>"
        "<itemPrice type='sale' pd='1' value='10' currency='GBP'/></bskArticle>"
        "<bskArticle itemType='BasketArticle'><artNr type='base'>A</artNr><artNr type='final'>A Z</artNr></bskArticle>"
        "</items></cutBuffer>", encoding="utf-8")
    result = GenerationResult(exported=True, configurations=[
        GeneratedConfiguration(1, "A", "A X"), GeneratedConfiguration(2, "A", "A Y")])
    summary = ObxOutputValidator().validate(obx, result)
    assert summary.well_formed and summary.article_lines == 2
    assert summary.missing_final_articles == ["A Y"]
    assert summary.unexpected_final_articles == ["A Z"]
    assert summary.lines_without_price == 1
    assert not summary.ok


def test_validator_reports_missing_or_empty_file(tmp_path):
    assert "Cannot read" in ObxOutputValidator().validate(tmp_path / "none.obx").problems[0]
    empty = tmp_path / "empty.obx"
    empty.write_text("", encoding="utf-8")
    assert "empty" in ObxOutputValidator().validate(empty).problems[0]
