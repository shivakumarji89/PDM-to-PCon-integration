"""Headless validation for the MDB -> XOCD reconciliation diff core (Slice 1).

Verifies the name-keyed diff engine classifies added/removed/modified deltas
with field-level detail, honours ignored columns and a classify callback, and
that the XOCD CSV reader parses positional Latin-1 rows into named dicts.

Run:  $env:PYTHONPATH="."; python scripts/validate_mdb_reconcile.py
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from core.application_context import ApplicationContext
from models.mdb_recon import (
    KIND_ADDED,
    KIND_MODIFIED,
    KIND_REMOVED,
    VERDICT_BLOCKED,
)


def main() -> int:
    ctx = ApplicationContext()
    svc = ctx.mdb_reconcile_service

    baseline = [
        {"article": "NOALE211", "list": "STD", "value": "100"},
        {"article": "NOALE212", "list": "STD", "value": "120"},
        {"article": "NOALE221", "list": "STD", "value": "80"},
    ]
    current = [
        {"article": "NOALE211", "list": "STD", "value": "110"},  # modified 100->110
        {"article": "NOALE221", "list": "STD", "value": "80"},   # unchanged
        {"article": "NOALE999", "list": "STD", "value": "50"},   # added
        # NOALE212 removed
    ]
    changes = svc.diff_rows("price", baseline, current, ["article", "list"])
    by_kind: dict[str, list] = {}
    for change in changes:
        by_kind.setdefault(change.kind, []).append(change)
    modified = by_kind.get(KIND_MODIFIED, [])
    assert len(modified) == 1 and modified[0].entity == "NOALE211 / STD", changes
    assert modified[0].fields[0].old == "100" and modified[0].fields[0].new == "110"
    assert len(by_kind.get(KIND_ADDED, [])) == 1
    assert by_kind[KIND_ADDED][0].entity == "NOALE999 / STD"
    assert len(by_kind.get(KIND_REMOVED, [])) == 1
    assert by_kind[KIND_REMOVED][0].entity == "NOALE212 / STD"
    print("OK: diff_rows classifies added / modified / removed with field detail")

    def block_removals(change) -> None:
        if change.kind == KIND_REMOVED:
            change.verdict = VERDICT_BLOCKED
            change.reason = "removals are not folded back automatically"

    changes = svc.diff_rows(
        "price", baseline, current, ["article", "list"], classify=block_removals
    )
    removed = [c for c in changes if c.kind == KIND_REMOVED][0]
    assert removed.verdict == VERDICT_BLOCKED and removed.reason
    print("OK: classify callback refines verdict/reason")

    changes = svc.diff_rows(
        "price", baseline, current, ["article", "list"], ignore=["value"]
    )
    assert not any(c.kind == KIND_MODIFIED for c in changes), "value ignored"
    print("OK: ignored columns are not diffed")

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "xocd_price.csv"
        path.write_text(
            "PROG;NOALE211;STD;100\nPROG;NOALE212;STD;120\n", encoding="latin-1"
        )
        rows = svc.read_xocd_table(
            tmp, "xocd_price.csv", ["program", "article", "list", "value"]
        )
        assert len(rows) == 2 and rows[0]["article"] == "NOALE211", rows
        assert rows[0]["value"] == "100"
        assert svc.read_xocd_table(tmp, "missing.csv", ["a"]) == []
    print("OK: read_xocd_table reads positional CSV into named dicts")

    # -- Slices 2-4: reconcile (price adapter) + classify + apply -------
    from models.mdb_recon import VERDICT_SAFE, VERDICT_REVIEW

    with tempfile.TemporaryDirectory() as tmp:
        # XOCD baseline (14-col price rows). NOALE211 base 100, NOALE212 base 120.
        Path(tmp, "xocd_price.csv").write_text(
            "PROG;STD;NOALE211;;S;B;;;100;True;GBP;20200101;99991231;\r\n"
            "PROG;STD;NOALE212;;S;B;;;120;True;GBP;20200101;99991231;\r\n",
            encoding="latin-1",
        )
        # MDB current (name-keyed, as _map_price_row would produce): 211 edited
        # to 110, 212 removed, 999 added.
        current = {"price": [
            {"price_list": "STD", "article": "NOALE211", "variant_condition": "",
             "level": "B", "value": "110", "currency": "GBP",
             "date_from": "20200101", "date_to": "99991231"},
            {"price_list": "STD", "article": "NOALE999", "variant_condition": "",
             "level": "B", "value": "50", "currency": "GBP",
             "date_from": "20260101", "date_to": "99991231"},
        ]}
        report = svc.reconcile(tmp, current_by_table=current)
        kinds = {c.entity.split(" / ")[0]: (c.kind, c.verdict) for c in report.changes}
        assert kinds["NOALE211"][0] == "modified" and kinds["NOALE211"][1] == VERDICT_SAFE, kinds
        assert kinds["NOALE999"][0] == "added" and kinds["NOALE999"][1] == VERDICT_REVIEW, kinds
        assert kinds["NOALE212"][0] == "removed" and kinds["NOALE212"][1] == "blocked", kinds
        print(f"OK: reconcile classifies price deltas -> {report.summary()}")

        # Apply the SAFE edit + the REVIEW add; the BLOCKED removal is skipped.
        accepted = [
            c for c in report.changes
            if c.entity.split(" / ")[0] in ("NOALE211", "NOALE999", "NOALE212")
        ]
        applied = svc.apply_changes(tmp, "price", accepted)
        assert applied == 2, applied
        after = {r["article"]: r for r in svc.read_xocd_table(
            tmp, "xocd_price.csv", svc._PRICE_COLUMNS)}
        assert after["NOALE211"]["value"] == "110", after["NOALE211"]
        assert "NOALE999" in after and after["NOALE999"]["value"] == "50"
        assert "NOALE212" in after, "blocked removal must NOT drop the baseline row"
        print("OK: apply folds SAFE/REVIEW back to XOCD, skips BLOCKED removal")

    # -- Repository OCD reconcile (XOCD xocd_*.csv vs repo ocd_*.csv) ----
    with tempfile.TemporaryDirectory() as xocd_dir, tempfile.TemporaryDirectory() as repo_dir:
        # XOCD holds ALL products (multi-program): ALWAYS + AERON.
        Path(xocd_dir, "xocd_price.csv").write_text(
            "ALWAYS;STD;NOALE1;;S;B;;;926;1;GBP;20240701;20250203;\r\n"
            "ALWAYS;STD;NOALE1;;S;B;;;963;1;GBP;20250204;99991231;\r\n"
            "AERON;STD;AER1;;S;B;;;500;1;GBP;20240701;99991231;\r\n",
            encoding="latin-1",
        )
        # Repo = ONE product (ALWAYS): first period edited 926 -> 940.
        Path(repo_dir, "ocd_price.csv").write_text(
            "NOALE1;;S;B;;;940;1;GBP;20240701;20250203;1;\r\n"
            "NOALE1;;S;B;;;963;1;GBP;20250204;99991231;1;\r\n",
            encoding="latin-1",
        )
        report = svc.reconcile_repo(xocd_dir, repo_dir, program="ALWAYS")
        assert not any("AER1" in c.entity for c in report.changes), \
            "other program's rows must be filtered out (not flagged removed)"
        mods = [c for c in report.changes if c.kind == "modified"]
        assert len(mods) == 1, report.changes
        assert mods[0].fields[0].field == "value" and mods[0].fields[0].new == "940"
        assert mods[0].source_ref == "xocd_price.csv:1", mods[0].source_ref
        print(f"OK: reconcile_repo filters by program, diffs, links to {mods[0].source_ref}")

        assert svc.apply_repo_changes(xocd_dir, mods) == 1
        after = svc.read_xocd_table(xocd_dir, "xocd_price.csv", svc._PRICE_COLUMNS)
        assert after[0]["value"] == "940", after[0]
        print("OK: apply_repo_changes folds the price edit back into xocd_price.csv")

    print("\nvalidate_mdb_reconcile: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
