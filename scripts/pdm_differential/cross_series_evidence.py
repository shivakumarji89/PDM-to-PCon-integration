"""Condense cross_series.py raw outputs into a reviewable evidence file.

    python scripts/pdm_differential/cross_series_evidence.py raw1.json [raw2.json ...] --out evidence.json

Keeps inputs, compiled-PDM status/logs, per-variant status, row-level difference counts (all differences up to a
cap), option-id histograms and sample records; drops the full record dumps.
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

CAP = 60


def _option(condition: str) -> str:
    _, _, tail = condition.partition(" ")
    return tail.partition("=")[0] if "=" in tail else "-"


def reclassify(w: dict, legacy_unresolved: int) -> str:
    """Same rule as cross_series._variant_status, applied uniformly to runs made before it existed."""
    exp, diff = w.get("export") or {}, w.get("differences") or {}
    if w.get("compute_error"):
        return "INCOMPLETE"
    if not exp.get("ok") or legacy_unresolved:
        return "INCOMPLETE"
    clean = (not diff.get("only_in_pdm_result") and not diff.get("only_in_pricing_result")
             and diff.get("lists_equal") and diff.get("texts_equal"))
    return "PASS" if clean and not w.get("unresolved") else "FAIL"


def condense(scenario: dict) -> dict:
    out = {k: scenario.get(k) for k in ("scenario", "title", "series", "status", "reason", "error", "inputs")}
    out["pdm"] = [{k: o.get(k) for k in ("mode", "executed", "returncode", "status", "noPDMprice", "notfound",
                                          "dialogs", "variableincs", "pdmVersion", "log_dir", "error")}
                  for o in scenario.get("pdm", [])]
    pdm_rows = scenario.get("pdm_result_rows") or {}
    out["pdm_rows_added"], out["pdm_rows_removed"] = len(pdm_rows.get("added", [])), len(pdm_rows.get("removed", []))
    out["variants"] = {}
    legacy_unresolved = sum(len(o.get("noPDMprice") or []) + len(o.get("notfound") or [])
                            for o in scenario.get("pdm", []))
    for name, w in (scenario.get("workbench") or {}).items():
        v = {k: w.get(k) for k in ("generation_program", "compute_error")}
        v["legacy_unresolved"] = legacy_unresolved
        v["status"] = reclassify(w, legacy_unresolved)
        recs = w.get("records") or []
        v["records"] = len(recs)
        v["option_ids_in_conditions"] = dict(collections.Counter(_option(r["variant_condition"]) for r in recs))
        v["routed_source_ne_target"] = sum(
            1 for r in recs if r["global"] if "=" in r["pdm_lookup_code"].partition(" ")[2]
            and _option(r["variant_condition"]) != _option(r["pdm_lookup_code"]))
        v["sample_records"] = [{k: r[k] for k in ("variant_condition", "pdm_lookup_code", "value")} for r in recs[:3]]
        exp = w.get("export") or {}
        v["export"] = {k: exp.get(k) for k in ("ok", "error", "inserted_prices", "inserted_global_prices",
                                                "updated_prices", "updated_global_prices", "skipped_existing",
                                                "skipped_text_blocked", "text_summary", "text_result")}
        v["export_blocking_errors"] = ((exp.get("plan") or {}).get("blocking_errors") or [])[:3]
        diff = w.get("differences") or {}
        v["only_in_pdm_result"] = {"count": len(diff.get("only_in_pdm_result", [])),
                                   "rows": diff.get("only_in_pdm_result", [])[:CAP]}
        v["only_in_pricing_result"] = {"count": len(diff.get("only_in_pricing_result", [])),
                                       "rows": diff.get("only_in_pricing_result", [])[:CAP]}
        v["lists_equal"], v["texts_equal"] = diff.get("lists_equal"), diff.get("texts_equal")
        out["variants"][name] = v
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("raw", nargs="+")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    merged: dict[str, dict] = {}
    for path in args.raw:
        for scenario in json.loads(Path(path).read_text(encoding="utf-8"))["scenarios"]:
            merged[scenario["scenario"]] = condense(scenario)
    Path(args.out).write_text(json.dumps({"scenarios": list(merged.values())}, indent=1, default=str),
                              encoding="utf-8")
    print(f"{len(merged)} scenarios -> {args.out}")


if __name__ == "__main__":
    main()
