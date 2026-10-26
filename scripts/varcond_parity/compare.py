"""Compare legacy VARCOND text with Workbench VARCOND text.

Inputs are never altered: both texts are kept verbatim and compared exactly
first. Normalisation (line endings / whitespace only) is a *separate* second
view, so formatting-only differences are distinguishable from rule differences.

The report also carries an ``attribution`` verdict. A rule difference is only
attributed to the generation algorithm when both sides supplied an input
manifest and the manifests are identical; differing or missing manifests are
reported as such so a data-source mismatch is never blamed on the algorithm.

CLI::

    python -m scripts.varcond_parity.compare --legacy bridge_response.json \
        --python run.json [--legacy-inputs legacy_inputs.json] --out report.json

``--legacy`` accepts the bridge JSON response (``generatedText``) or a raw text
file. ``--python`` accepts a ``run_python.py`` result or a raw text file.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path

_FACTOR = re.compile(r"^\$SET_PRICING_FACTOR\((?P<target>.*), (?P<qty>-?\d+)\) (?P<body>IF.*)$")
_OPTION_SUFFIX = re.compile(
    r"""['"][^'"]+\s+\d+=['"]\s*\+|['"]\d+=[^'"]+_['"]\s*\+"""
)
_SENSITIVE_INPUT = re.compile(r"password|secret|token|credential|connection.?string", re.I)


def split_rules(text: str) -> list[str]:
    """Split generated text on line endings, removing only a final rule comma."""
    rules = []
    for line in re.split(r"\r\n|\r|\n", text):
        if not line.strip():
            continue
        rules.append(line[:-1] if line.endswith(",") else line)
    return rules


def normalise_rule(rule: str) -> str:
    """Formatting-only normalisation: unify line endings, collapse whitespace."""
    return re.sub(r"\s+", " ", rule.replace("\r\n", "\n")).strip()


def _first_difference(a: str, b: str) -> dict | None:
    if a == b:
        return None
    limit = min(len(a), len(b))
    index = next((i for i in range(limit) if a[i] != b[i]), limit)
    return {
        "offset": index,
        "legacy_context": a[max(0, index - 40): index + 40],
        "python_context": b[max(0, index - 40): index + 40],
    }


def _multiset_diff(left: list[str], right: list[str]) -> tuple[list[str], list[str]]:
    """(in left only, in right only), respecting multiplicity, in input order."""
    left_counts, right_counts = Counter(left), Counter(right)
    only_left, only_right = [], []
    remaining = Counter(right_counts)
    for rule in left:
        if remaining[rule] > 0:
            remaining[rule] -= 1
        else:
            only_left.append(rule)
    remaining = Counter(left_counts)
    for rule in right:
        if remaining[rule] > 0:
            remaining[rule] -= 1
        else:
            only_right.append(rule)
    return only_left, only_right


def _factors(rules: list[str]) -> dict[str, list[int]]:
    found: dict[str, list[int]] = {}
    for rule in rules:
        match = _FACTOR.match(rule)
        if match:
            key = f"{match['target']} {match['body']}"
            found.setdefault(key, []).append(int(match["qty"]))
    return found


def compare_inputs(legacy: dict | None, python: dict | None) -> dict:
    """Describe differences between two input manifests (see ``inputs.py``)."""
    if legacy is None or python is None:
        return {"status": "unverified", "detail": "legacy and/or python input manifest missing", "differences": []}
    differences: list[dict] = []

    def safe_value(path: str, value):
        return "<redacted>" if _SENSITIVE_INPUT.search(path) else value

    def walk(path: str, a, b) -> None:
        if isinstance(a, dict) and isinstance(b, dict):
            for key in sorted(set(a) | set(b)):
                if key not in a:
                    child_path = f"{path}/{key}"
                    differences.append({"path": child_path, "legacy": None, "python": safe_value(child_path, b[key]), "kind": "only_python"})
                elif key not in b:
                    child_path = f"{path}/{key}"
                    differences.append({"path": child_path, "legacy": safe_value(child_path, a[key]), "python": None, "kind": "only_legacy"})
                else:
                    walk(f"{path}/{key}", a[key], b[key])
        elif isinstance(a, list) and isinstance(b, list):
            for i in range(max(len(a), len(b))):
                child_path = f"{path}[{i}]"
                if i >= len(a):
                    differences.append({"path": child_path, "legacy": None, "python": safe_value(child_path, b[i]), "kind": "only_python"})
                elif i >= len(b):
                    differences.append({"path": child_path, "legacy": safe_value(child_path, a[i]), "python": None, "kind": "only_legacy"})
                else:
                    walk(child_path, a[i], b[i])
        elif type(a) is not type(b) or a != b:
            differences.append({"path": path, "legacy": safe_value(path, a), "python": safe_value(path, b), "kind": "changed"})

    walk("", legacy, python)
    return {"status": "identical" if not differences else "differ", "differences": differences}


def compare(
    legacy_text: str,
    python_text: str,
    legacy_inputs: dict | None = None,
    python_inputs: dict | None = None,
) -> dict:
    legacy_rules, python_rules = split_rules(legacy_text), split_rules(python_text)
    legacy_norm = [normalise_rule(r) for r in legacy_rules]
    python_norm = [normalise_rule(r) for r in python_rules]

    exact_equal = legacy_text == python_text
    normalised_equal = legacy_norm == python_norm
    missing, extra = _multiset_diff(legacy_rules, python_rules)
    missing_norm, extra_norm = _multiset_diff(legacy_norm, python_norm)
    same_multiset = not missing and not extra
    missing_suffix, extra_suffix = _multiset_diff(
        [r for r in legacy_rules if _OPTION_SUFFIX.search(r)],
        [r for r in python_rules if _OPTION_SUFFIX.search(r)],
    )
    legacy_factors, python_factors = _factors(legacy_rules), _factors(python_rules)
    factor_diffs = []
    for key in sorted(set(legacy_factors) | set(python_factors)):
        if legacy_factors.get(key) != python_factors.get(key):
            factor_diffs.append(
                {"rule": key, "legacy_quantities": legacy_factors.get(key), "python_quantities": python_factors.get(key)}
            )
    legacy_dupes = {r: n for r, n in Counter(legacy_rules).items() if n > 1}
    python_dupes = {r: n for r, n in Counter(python_rules).items() if n > 1}
    inputs = compare_inputs(legacy_inputs, python_inputs)

    def newline_style(text: str) -> str:
        without_crlf = text.replace("\r\n", "")
        has_crlf = "\r\n" in text
        has_lf = "\n" in without_crlf
        has_cr = "\r" in without_crlf
        if (has_crlf and (has_lf or has_cr)) or (has_lf and has_cr):
            return "mixed"
        if has_crlf:
            return "CRLF"
        if has_lf:
            return "LF"
        if has_cr:
            return "CR"
        return "none"

    formatting_differences = []
    legacy_newlines, python_newlines = newline_style(legacy_text), newline_style(python_text)
    if legacy_newlines != python_newlines:
        formatting_differences.append(f"line endings differ ({legacy_newlines} vs {python_newlines})")
    if legacy_text.endswith(("\r", "\n")) != python_text.endswith(("\r", "\n")):
        formatting_differences.append("trailing newline differs")
    if normalised_equal and legacy_rules != python_rules:
        formatting_differences.append("rule whitespace differs")

    def comma_delimiters(text: str) -> list[bool]:
        return [
            line.endswith(",")
            for line in re.split(r"\r\n|\r|\n", text)
            if line.strip()
        ]

    if comma_delimiters(legacy_text) != comma_delimiters(python_text):
        formatting_differences.append("rule comma delimiters differ")

    exact_text_diff = ""
    if not exact_equal:
        exact_text_diff = "".join(
            difflib.unified_diff(
                legacy_text.splitlines(keepends=True),
                python_text.splitlines(keepends=True),
                fromfile="legacy",
                tofile="python",
            )
        )

    if exact_equal:
        verdict = "exact_match"
    elif normalised_equal:
        verdict = "formatting_only_difference"
    elif same_multiset:
        verdict = "ordering_difference"
    else:
        verdict = "rule_difference"

    if verdict == "exact_match":
        attribution = {
            "identical": "match (inputs identical)",
            "differ": "match_despite_input_differences",
        }.get(inputs["status"], "match (inputs not proven identical)")
    elif inputs["status"] == "identical":
        attribution = "generation_algorithm"
    elif inputs["status"] == "differ":
        attribution = "input_data_differs_first"
    else:
        attribution = "inputs_unverified_cannot_attribute"

    return {
        "verdict": verdict,
        "attribution": attribution,
        "exact_equal": exact_equal,
        "normalised_equal": normalised_equal,
        "first_text_difference": _first_difference(legacy_text, python_text),
        "counts": {"legacy_rules": len(legacy_rules), "python_rules": len(python_rules)},
        "missing_rules": missing,                      # legacy has, python lacks
        "extra_rules": extra,                          # python has, legacy lacks
        "missing_rules_normalised": missing_norm,
        "extra_rules_normalised": extra_norm,
        "missing_option_suffix_rules": missing_suffix,
        "extra_option_suffix_rules": extra_suffix,
        "duplicate_rules": {"legacy": legacy_dupes, "python": python_dupes},
        "ordering_changed": same_multiset and legacy_rules != python_rules,
        "formatting_differences": formatting_differences,
        "exact_text_diff": exact_text_diff,
        "pricing_factor_differences": factor_diffs,
        "inputs": inputs,
    }


def render_text(report: dict) -> str:
    lines = [
        f"verdict: {report['verdict']}",
        f"attribution: {report['attribution']}",
        f"rules: legacy={report['counts']['legacy_rules']} python={report['counts']['python_rules']}",
        f"exact text equal: {report['exact_equal']}   normalised equal: {report['normalised_equal']}",
        f"inputs: {report['inputs']['status']} ({len(report['inputs'].get('differences', []))} difference(s))",
    ]
    for title, key in (("missing in python", "missing_rules"), ("extra in python", "extra_rules")):
        if report[key]:
            lines.append(f"{title} ({len(report[key])}):")
            lines.extend(f"  {rule}" for rule in report[key])
    for side in ("legacy", "python"):
        if report["duplicate_rules"][side]:
            lines.append(f"duplicate rules in {side}:")
            lines.extend(f"  x{n}: {rule}" for rule, n in report["duplicate_rules"][side].items())
    if report["ordering_changed"]:
        lines.append("ordering changed (same rules, different order)")
    for title, key in (("missing option suffix rules", "missing_option_suffix_rules"),
                       ("extra option suffix rules", "extra_option_suffix_rules")):
        if report[key]:
            lines.append(f"{title}:")
            lines.extend(f"  {rule}" for rule in report[key])
    for difference in report["formatting_differences"]:
        lines.append(f"formatting: {difference}")
    for diff in report["pricing_factor_differences"]:
        lines.append(f"pricing factor: {diff['rule']} legacy={diff['legacy_quantities']} python={diff['python_quantities']}")
    for diff in report["inputs"].get("differences", []):
        lines.append(f"input {diff['kind']}: {diff['path']} legacy={diff['legacy']!r} python={diff['python']!r}")
    if report["exact_text_diff"]:
        lines.append("exact text diff:")
        lines.extend(report["exact_text_diff"].rstrip().splitlines())
    return "\n".join(lines)


def _load(path: str, key: str) -> tuple[str, dict | None]:
    with open(path, encoding="utf-8-sig", newline="") as handle:   # newline="" keeps CRLF verbatim
        raw = handle.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw, None
    if isinstance(data, dict):
        if data.get("ok") is False:
            raise SystemExit(f"{path}: legacy response is a failure: {data.get('error')}")
        return str(data.get(key, "")), data.get("inputs")
    raise SystemExit(f"{path}: unexpected JSON shape")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--legacy", required=True)
    parser.add_argument("--python", required=True, dest="python_path")
    parser.add_argument("--legacy-inputs", help="legacy input manifest JSON (same schema as run_python output 'inputs')")
    parser.add_argument("--out", help="write the JSON report here")
    args = parser.parse_args(argv)

    legacy_text, embedded_legacy_inputs = _load(args.legacy, "generatedText")
    python_text, python_inputs = _load(args.python_path, "text")
    legacy_inputs = embedded_legacy_inputs
    if args.legacy_inputs:
        legacy_inputs = json.loads(Path(args.legacy_inputs).read_text(encoding="utf-8-sig"))
    report = compare(legacy_text, python_text, legacy_inputs, python_inputs)
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(render_text(report))
    return 0 if report["verdict"] == "exact_match" else 1


if __name__ == "__main__":
    sys.exit(main())
