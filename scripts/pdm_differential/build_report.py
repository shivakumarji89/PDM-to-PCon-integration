"""Turn the raw differential output into the committed, machine-readable report.

usage: python scripts/pdm_differential/build_report.py <raw differential.json> <report.json>

The raw file holds, per scenario, what the REAL PDM wrote (and its status lines / dialogs), what the Pricing export
wrote for the same inputs, and the row-level differences between the two result states. This script adds the
classification of every remaining difference. A difference is only ``explained`` when it matches the exact
predicate recorded for it below; anything else stays ``UNEXPLAINED`` and fails the build.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

#: scenario -> list of (classification, reason, predicate over the two difference lists)
def _rows(diff, key):
    return [json.loads(x) for x in diff[key]]


def _only(diff, pdm_pred=None, pricing_pred=None):
    pdm, pr = _rows(diff, "only_in_pdm_result"), _rows(diff, "only_in_pricing_result")
    return all((pdm_pred or (lambda r: False))(r) for r in pdm) and all((pricing_pred or (lambda r: False))(r) for r in pr)


def _is_ge2hdf_base(r):
    return r[0] == "global" and r[3] == "GE2HDF."


EXPLANATIONS = {
    "S4b_duplicates_both_stale": (
        "intentional",
        "PDM updates only the LAST duplicate row it reads and leaves the other stale; Pricing corrects every duplicate "
        "row whose value differs (pCon may read either). Real-MDB scope has no duplicate identities "
        "(duplicate_matches 0), so current data is unaffected.",
        lambda d: _only(d, lambda r: r[2] == "GEWQ" and r[3] == ".", lambda r: r[2] == "GEWQ" and r[3] == "."),
    ),
    "S5_global_update": (
        "intentional",
        "PDM's global value update never inserts a missing global row ('not found'); PDM needs its separate "
        "'create placeholders' step first. Pricing inserts the row with its value in one step; the two-step PDM "
        "workflow is compared with it in S6/S7/S9/S11 and matches.",
        lambda d: _only(d, None, _is_ge2hdf_base),
    ),
    "S8_global_eur": (
        "intentional",
        "As S5 on the EUR list 21: PDM's global value update never inserts the missing global row; Pricing inserts it with its value (the two-step PDM workflow is compared in S6/S7/S9/S11).",
        lambda d: _only(d, None, _is_ge2hdf_base),
    ),
    "S13_lookalike_orphan_list": (
        "intentional_protective",
        "PDM matches the target list with LIKE 'GBP%2026%2', which also matches the unlinked orphan list 23 "
        "('GBP 2026_2'): it updated only ONE of the two stale base rows and counted list 23's surcharge rows as "
        "'up to date', so the linked list 22 never received them. Pricing writes only the validated target list 22 "
        "(inserting the 13 missing surcharge rows) and never touches list 23.",
        lambda d: _only(d, None, lambda r: r[0] == "global" and r[1] == "GBP_2026_2" and r[3].startswith("GESNNU.105508F")),
    ),
    "S5b_global_update_variableincs_false": (
        "negative_control",
        "PDM forced to variableincs=false (not what the button computes for layout_studio): its surcharge matcher "
        "then cannot match the item-prefixed rows. Shows the input that S5 must use; no Pricing change implied.",
        lambda d: True,
    ),
    "S10_existing_text_label_refresh": (
        "intentional",
        "PDM rewrites the language columns of an existing price text on every placeholder run (a hand-edited label "
        "is reset to '<item>  (<Product_Code>)'); Pricing preserves existing text content.",
        lambda d: _only(d, lambda r: r[3] == "GE2HBS.", lambda r: r[3] == "GE2HBS.") and not d["texts_equal"],
    ),
    "S11_non_price_text_name_collision": (
        "intentional_protective",
        "PDM's text lookup has no com_TextTypeCode filter: it linked the new global row to the existing ARTLONG text "
        "that shared the item's name AND rewrote that text's language columns. Pricing links only 'price' texts and "
        "creates its own. On the real MDB no non-price text shares a price-text name (0 collisions).",
        lambda d: _only(d, lambda r: r[3] == "GE2HDF.", lambda r: r[3] == "GE2HDF."),
    ),
}


def slim(raw: dict) -> dict:
    scenarios = []
    unexplained = []
    for sc in raw["scenarios"]:
        pdm = sc.get("pdm") or []
        diff = sc.get("differences")
        entry = {
            "scenario": sc["scenario"], "title": sc["title"], "covers_checklist_items": sc["covers"],
            "source_inputs": sc["inputs"],
            "pdm_output": [{k: o.get(k) for k in ("executed", "pdmVersion", "mode", "variableincs", "status",
                                                  "noPDMprice", "notfound", "dialogs", "error")} for o in pdm],
            "pricing_output": {k: v for k, v in (sc.get("pricing") or {}).items()
                               if k not in ("plan", "list_plan", "verification_failures", "mdb_path")},
            "pricing_inputs": sc.get("pricing_inputs"),
        }
        if diff is None:
            entry["verification_status"] = "UNVERIFIED (PDM did not execute)"
            entry["resolution"] = sc.get("status")
            unexplained.append(sc["scenario"])
        else:
            entry["differences"] = {
                "pdm_changed_rows": len(diff["pdm_changed"]["added"]) + len(diff["pdm_changed"]["removed"]),
                "pricing_changed_rows": len(diff["pricing_changed"]["added"]) + len(diff["pricing_changed"]["removed"]),
                "only_in_pdm_result": diff["only_in_pdm_result"][:60],
                "only_in_pricing_result": diff["only_in_pricing_result"][:60],
                "lists_equal": diff["lists_equal"], "texts_equal": diff["texts_equal"],
                "texts_added_pdm_pricing": diff["texts_added"],
            }
            clean = not diff["only_in_pdm_result"] and not diff["only_in_pricing_result"] \
                and diff["lists_equal"] and diff["texts_equal"]
            if clean:
                entry["verification_status"] = "MATCH"
                entry["resolution"] = "identical normalized result state"
            elif sc["scenario"] in EXPLANATIONS and EXPLANATIONS[sc["scenario"]][2](diff):
                cls, why, _ = EXPLANATIONS[sc["scenario"]]
                entry["verification_status"] = "DIFFERENCE_EXPLAINED"
                entry["classification"], entry["resolution"] = cls, why
            else:
                entry["verification_status"] = "UNEXPLAINED"
                entry["resolution"] = "difference not matched by a recorded explanation"
                unexplained.append(sc["scenario"])
            if sc.get("second_run"):
                entry["second_run_idempotency"] = sc["second_run"]
        scenarios.append(entry)
    return {"scenarios": scenarios, "unexplained": unexplained}


def main():
    raw = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = slim(raw)
    out["pdm_application"] = {
        "binary": "PDMMaintenance.exe (installed build, loaded as a library from a copy)",
        "assembly_version": next((o.get("pdmVersion") for s in raw["scenarios"] for o in (s.get("pdm") or [])
                                  if o.get("pdmVersion")), None),
        "entry_point": "PDMMaintenance.UpdatePriceThread.execThread (what PConPriceUpdate's buttons start)",
        "isolation": "pConPath redirected to a per-scenario MDB copy; SQL Server is read-only in these code paths",
    }
    Path(sys.argv[2]).write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    for s in out["scenarios"]:
        print(s["scenario"], s["verification_status"])
    if out["unexplained"]:
        print("UNEXPLAINED:", out["unexplained"])
        sys.exit(1)


if __name__ == "__main__":
    main()
