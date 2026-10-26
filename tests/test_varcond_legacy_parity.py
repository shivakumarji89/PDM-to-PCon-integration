"""Legacy VARCOND parity regression tests.

Evidence classes (kept distinct on purpose):

* ``test_helper_*``  - Python ports versus RECORDED OUTPUT OF THE REAL legacy
  assembly (``fixtures/helper_legacy_results.json``, produced by
  ``run_legacy_helpers.ps1`` against PDMMaintenance 1.0.9686.24988).
* ``test_legacy_exact_case_*`` - expectations derived by hand from the compiled
  ``execThread`` IL. Source-level only; NOT captured legacy generator output.
* ``test_compare_*`` - behaviour of the comparison harness itself.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from models.article import Article
from models.snapshot import Snapshot
from scripts.varcond_parity import compare as cmp
from scripts.varcond_parity import run_python
from scripts.varcond_parity.run_python import run
from services.snapshot_serialization import snapshot_to_dict
from services.varcond_service import VarCondService

FIXTURES = Path(__file__).resolve().parents[1] / "scripts" / "varcond_parity" / "fixtures"
HELPERS = json.loads((FIXTURES / "helper_legacy_results.json").read_text(encoding="utf-8-sig"))
CASES = json.loads((FIXTURES / "legacy_exact_cases.json").read_text(encoding="utf-8"))["cases"]


def _service() -> VarCondService:
    return VarCondService.__new__(VarCondService)


# -- helper ports versus real legacy output -------------------------------------

def test_helper_vectors_come_from_the_expected_legacy_build() -> None:
    assert HELPERS["assemblyVersion"] == "1.0.9686.24988"
    assert len(HELPERS["assemblySha256"]) == 64


@pytest.mark.parametrize("row", HELPERS["parseAttributeNameAsPConProperty"],
                         ids=lambda r: f"{r['context']}|{r['name']}")
def test_helper_parse_attribute_name_matches_real_legacy(row) -> None:
    assert VarCondService._parse_attr_as_pcon(row["name"], row["context"]) == row["result"]


@pytest.mark.parametrize("row", HELPERS["camelCase"], ids=lambda r: repr(r["input"]))
def test_helper_camel_case_matches_real_legacy(row) -> None:
    assert VarCondService._camel_case(row["input"]) == row["result"]


@pytest.mark.parametrize("row", HELPERS["ParsePConPropertyName"], ids=lambda r: repr(r["input"]))
def test_helper_parse_pcon_property_name_matches_real_legacy(row) -> None:
    assert VarCondService._parse_pcon_property_name(row["input"]) == row["result"]


@pytest.mark.parametrize("row", [r for r in HELPERS["isInteger"] if not r["allowNegative"]],
                         ids=lambda r: repr(r["input"]))
def test_helper_quantity_rule_matches_real_is_integer(row) -> None:
    # execThread: Quantity text replaces the default 1 only when isInteger(text, False).
    expected = int(row["input"]) if row["result"] else 1
    assert VarCondService._legacy_quantity(row["input"]) == expected


# -- legacy_exact generator: IL-derived regression cases ------------------------

@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_legacy_exact_case_matches_il_derived_expectation(case) -> None:
    out = run(case["fixture"], "legacy_exact")
    assert out["rules"] == case["expected_legacy_exact_rules"]
    # legacy joins with ",\r\n" and terminates with "\r\n"
    assert out["text"] == ",\r\n".join(case["expected_legacy_exact_rules"]) + "\r\n"


def test_ry3vnn_hw_case_keeps_suffix_source_warning_and_manifest_prefixes() -> None:
    case = next(c for c in CASES if c["name"] == "ry3vnn_hw_and_ry2u_suffix_property_names")
    out = run(case["fixture"], "legacy_exact")

    assert any("PDMOptionDataReportWithIncBase" in warning for warning in out["warnings"])
    assert out["inputs"]["option_increments"] == {
        "RY2U123.": [{"option_id": 703, "option_name": "hardware pack finish"}],
        "RY3VNN123HW": [{"option_id": 700, "option_name": "fabric type"}],
    }


@pytest.mark.parametrize("case", [c for c in CASES if "expected_default_rules" in c], ids=lambda c: c["name"])
def test_default_mode_is_unchanged_and_documented_as_different(case) -> None:
    default = run(case["fixture"], "default")
    assert default["rules"] == case["expected_default_rules"]
    assert default["rules"] != case["expected_legacy_exact_rules"]


def test_legacy_exact_is_opt_in_so_default_callers_are_unaffected() -> None:
    import inspect
    parameter = inspect.signature(VarCondService.generate).parameters["legacy_exact"]
    assert parameter.default is False


def _single_parent(code: str = "PAR1", **extra) -> Snapshot:
    snap = Snapshot()
    snap.articles = [Article(id="p", code=code)]
    snap.article_prefix_length = {"p": 3}
    snap.article_varcond_terms = {"p": [{"name": "Leg", "order": 1, "has_dependent_options": 0, "order_code": "C"}]}
    snap.article_components = {"p": [{"sub_item": "S.1", "quantity": 1, "sequence": "1"}]}
    for key, value in extra.items():
        setattr(snap, key, value)
    return snap


def test_legacy_exact_warns_about_missing_prefix_length() -> None:
    snap = _single_parent(article_prefix_length={})
    result = _service().generate(snapshot=snap, legacy_exact=True)
    assert any("prefix length undefined" in w for w in result.warnings)
    assert result.rules  # legacy proceeds when the operator answers Yes


def test_legacy_exact_warns_instead_of_inventing_a_non_bom_rule() -> None:
    snap = _single_parent(article_components={})
    result = _service().generate(snapshot=snap, article_codes=["PAR1"], legacy_exact=True)
    assert result.rules == [] and result.text == ""
    assert any("no BOM components" in w and "Product name" in w for w in result.warnings)


def test_legacy_exact_reports_codes_missing_from_the_snapshot() -> None:
    result = _service().generate(snapshot=_single_parent(), article_codes=["NOPE"], legacy_exact=True)
    assert result.rules == []
    assert any("NOPE" in w and "not in the snapshot" in w for w in result.warnings)


def test_legacy_exact_flags_unverified_suffix_input_source() -> None:
    snap = _single_parent(option_increments={"S.": [{"option_id": 1, "option_name": "finish"}]})
    result = _service().generate(snapshot=snap, legacy_exact=True)
    assert any("PDMOptionDataReportWithIncBase" in w for w in result.warnings)


def test_legacy_exact_without_article_codes_follows_snapshot_order_and_keeps_text_format() -> None:
    result = _service().generate(snapshot=_single_parent(), legacy_exact=True)
    assert result.text == "$VARCOND = 'S.1' IF Leg = 'C'\r\n"


# -- comparison harness ---------------------------------------------------------

def test_compare_exact_match_preserves_text() -> None:
    text = "$VARCOND = 'A' IF X = '1',\r\n$VARCOND = 'B' IF X = '1'\r\n"
    report = cmp.compare(text, text)
    assert report["verdict"] == "exact_match" and report["exact_equal"]
    assert report["counts"] == {"legacy_rules": 2, "python_rules": 2}
    assert report["first_text_difference"] is None


def test_compare_separates_formatting_only_from_rule_differences() -> None:
    legacy = "$VARCOND = 'A' IF X = '1'\r\n"
    python = "$VARCOND = 'A'  IF X = '1'\n"            # spacing and line-ending drift only
    report = cmp.compare(legacy, python)
    assert report["verdict"] == "formatting_only_difference"
    assert not report["exact_equal"] and report["normalised_equal"]
    assert report["missing_rules"] and report["extra_rules"]
    assert not report["missing_rules_normalised"] and not report["extra_rules_normalised"]
    assert report["formatting_differences"] == [
        "line endings differ (CRLF vs LF)",
        "rule whitespace differs",
    ]
    assert report["exact_text_diff"]


def test_compare_reports_missing_extra_duplicates_and_order() -> None:
    legacy = "R1,\r\nR2,\r\nR2,\r\nR3\r\n"
    python = "R3,\r\nR1,\r\nR4\r\n"
    report = cmp.compare(legacy, python)
    assert report["verdict"] == "rule_difference"
    assert report["missing_rules"] == ["R2", "R2"]
    assert report["extra_rules"] == ["R4"]
    assert report["duplicate_rules"] == {"legacy": {"R2": 2}, "python": {}}
    reordered = cmp.compare("R1,\r\nR2\r\n", "R2,\r\nR1\r\n")
    assert reordered["verdict"] == "ordering_difference" and reordered["ordering_changed"]


def test_compare_reports_pricing_factor_quantity_changes() -> None:
    legacy = "$VARCOND = 'A' IF X = '1',\r\n$SET_PRICING_FACTOR('A', 2) IF X = '1'\r\n"
    python = "$VARCOND = 'A' IF X = '1',\r\n$SET_PRICING_FACTOR('A', 3) IF X = '1'\r\n"
    report = cmp.compare(legacy, python)
    assert report["pricing_factor_differences"] == [
        {"rule": "'A' IF X = '1'", "legacy_quantities": [2], "python_quantities": [3]}
    ]


def test_compare_reports_option_suffix_differences_and_multiline_formatting() -> None:
    legacy = "$VARCOND = 'PART.1 700=' + Fabric_Type IF Width = '20',\r\n"
    python = "$VARCOND = 'PART.1 701=' + Fabric_Type IF Width = '20'\n"

    report = cmp.compare(legacy, python)

    assert report["missing_option_suffix_rules"] == [
        "$VARCOND = 'PART.1 700=' + Fabric_Type IF Width = '20'"
    ]
    assert report["extra_option_suffix_rules"] == [
        "$VARCOND = 'PART.1 701=' + Fabric_Type IF Width = '20'"
    ]
    assert report["formatting_differences"] == [
        "line endings differ (CRLF vs LF)",
        "rule comma delimiters differ",
    ]
    assert report["exact_text_diff"]


def test_compare_recognises_alternate_family_suffix_rules() -> None:
    legacy = "$VARCOND = '3848=RYMPSH.12SW_' + Panel_Finish IF Leg = 'C'\r\n"
    python = "$VARCOND = '3849=RYMPSH.12SW_' + Panel_Finish IF Leg = 'C'\r\n"

    report = cmp.compare(legacy, python)

    assert report["missing_option_suffix_rules"] == [
        "$VARCOND = '3848=RYMPSH.12SW_' + Panel_Finish IF Leg = 'C'"
    ]
    assert report["extra_option_suffix_rules"] == [
        "$VARCOND = '3849=RYMPSH.12SW_' + Panel_Finish IF Leg = 'C'"
    ]


def test_compare_attributes_difference_to_algorithm_only_when_inputs_match() -> None:
    case = next(c for c in CASES if c["name"] == "shared_if_no_component_filtering")
    legacy_like = run(case["fixture"], "legacy_exact")
    default = run(case["fixture"], "default")
    report = cmp.compare(legacy_like["text"], default["text"], legacy_like["inputs"], default["inputs"])
    assert report["verdict"] == "rule_difference"
    assert report["inputs"]["status"] == "identical"
    assert report["attribution"] == "generation_algorithm"


def test_compare_does_not_blame_algorithm_when_inputs_differ_or_are_missing() -> None:
    case = next(c for c in CASES if c["name"] == "shared_if_no_component_filtering")
    a = run(case["fixture"], "legacy_exact")
    changed = json.loads(json.dumps(case["fixture"]))
    changed["article_prefix_length"]["p1"] = 3        # shifts the parametric slice
    b = run(changed, "legacy_exact")
    differing = cmp.compare(a["text"], b["text"], a["inputs"], b["inputs"])
    assert differing["verdict"] == "rule_difference"
    assert differing["attribution"] == "input_data_differs_first"
    assert any(d["path"].endswith("/prefix_length") for d in differing["inputs"]["differences"])
    unverified = cmp.compare(a["text"], b["text"])
    assert unverified["attribution"] == "inputs_unverified_cannot_attribute"


def test_compare_flags_identical_text_produced_from_different_inputs() -> None:
    case = next(c for c in CASES if c["name"] == "shared_if_no_component_filtering")
    a = run(case["fixture"], "legacy_exact")
    changed = json.loads(json.dumps(case["fixture"]))
    changed["article_components"]["p1"][0]["sequence"] = "1.0"   # input differs, output does not
    b = run(changed, "legacy_exact")
    report = cmp.compare(a["text"], b["text"], a["inputs"], b["inputs"])
    assert report["verdict"] == "exact_match"
    assert report["attribution"] == "match_despite_input_differences"


def test_compare_cli_reads_bridge_response_and_run_output(tmp_path: Path) -> None:
    case = CASES[0]
    produced = run(case["fixture"], "legacy_exact")
    legacy = tmp_path / "bridge.json"
    legacy.write_text(json.dumps({"ok": True, "generatedText": produced["text"]}), encoding="utf-8")
    python = tmp_path / "run.json"
    python.write_text(json.dumps(produced), encoding="utf-8")
    out = tmp_path / "report.json"
    assert cmp.main(["--legacy", str(legacy), "--python", str(python), "--out", str(out)]) == 0
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["verdict"] == "exact_match"
    assert report["attribution"] == "match (inputs not proven identical)"


def test_snapshot_capture_keeps_order_and_option_increment_inputs(tmp_path: Path) -> None:
    snapshot = Snapshot(
        articles=[
            Article(id="a", code="PARENT.A"),
            Article(id="b", code="PARENT.B"),
        ],
        article_components={
            "a": [{"sub_item": "PART.A", "quantity": 1, "sequence": "1"}],
            "b": [{"sub_item": "PART.B", "quantity": 2, "sequence": "2"}],
        },
        article_varcond_terms={"a": [], "b": []},
        article_prefix_length={"a": 6, "b": 6},
        option_increments={"PART.": [{"option_id": 7, "option_name": "finish"}]},
    )
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot_to_dict(snapshot)), encoding="utf-8")
    output_path = tmp_path / "python.json"
    assert run_python.main([
        "--snapshot", str(snapshot_path),
        "--category-id", "42",
        "--article-code", "PARENT.B",
        "--article-code", "PARENT.A",
        "--mode", "default",
        "--out", str(output_path),
    ]) == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))

    assert artifact["inputs"]["request"] == {
        "article_codes": ["PARENT.B", "PARENT.A"],
        "category_id": 42,
        "prefix": "",
        "property_exclusions": "",
        "property_substitutions": "",
    }
    assert [parent["code"] for parent in artifact["inputs"]["parents"]] == [
        "PARENT.A",
        "PARENT.B",
    ]
    assert artifact["inputs"]["option_increments"] == {
        "PART.": [{"option_id": 7, "option_name": "finish"}]
    }
    assert artifact["text"].startswith("$VARCOND = 'PART.A' IF")
    assert "$VARCOND = 'PART.B' IF" in artifact["text"]


def test_split_rules_handles_empty_and_unterminated_text() -> None:
    assert cmp.split_rules("") == []
    assert cmp.split_rules("A") == ["A"]
    assert cmp.split_rules("A,\r\nB\r\n") == ["A", "B"]
    assert cmp.split_rules("A,\nB\n") == ["A", "B"]
