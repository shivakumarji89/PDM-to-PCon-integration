"""Headless validation for the XOCD CSV exporter.

Loads a cached family snapshot, runs the engineering pipeline, then exports the
XOCD package into a temp folder and prints a summary. Runs the export twice (a
second series into the same folder) to prove per-series upsert keeps both.

Run:  $env:PYTHONPATH="."; python scripts/validate_xocd_export.py [family.json]
"""
from __future__ import annotations

import csv
import json
import sys
import tempfile
from pathlib import Path

from core.application_context import ApplicationContext
from services.snapshot_serialization import snapshot_from_dict

_CACHE = Path(__file__).resolve().parents[1] / "cache" / "pdm_snapshots"


def _prepare(ctx, snapshot):
    ctx.snapshot_manager.load_snapshot(snapshot)
    ctx.engineering_reduction_service.materialize_article_sets(snapshot)
    ctx.engineering_initialization_service.initialize(snapshot)
    ctx.engineering_member_service.auto_reduce(snapshot)
    category = (snapshot.product.category if snapshot.product else "") or "Class"
    ctx.engineering_class_service.ensure_standard_classes(snapshot, category)
    ctx.engineering_class_service.commit_config_codes(snapshot)


def _count(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open("r", encoding="utf-8", newline="") as fh:
        return sum(1 for _ in csv.reader(fh, delimiter=";"))


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else "always.json"
    src = _CACHE / name
    if not src.is_file():
        print(f"snapshot not found: {src}")
        return 1

    snapshot = snapshot_from_dict(json.loads(src.read_text(encoding="utf-8")))
    ctx = ApplicationContext()
    _prepare(ctx, snapshot)

    folder = Path(tempfile.gettempdir()) / "validate_xocd"
    for f in folder.glob("xocd_*.csv"):
        f.unlink()

    # 1) New series -> applied straight away.
    result = ctx.xocd_export_service.export_series(snapshot, folder)
    print(f"new series: ok={result.ok} applied={result.applied} "
          f"needs_validation={result.needs_validation} program={result.program}")
    for fn, n in sorted(result.files.items()):
        print(f"  {fn}: {n} rows")

    # 2) A second, different series is just added (no conflict).
    ctx.xocd_export_service.export_series(snapshot, folder, program="other", program_id="OTHER")
    art = folder / "xocd_article.csv"
    programs = {row[0] for row in csv.reader(art.open(encoding="utf-8", newline=""), delimiter=";") if row}
    print(f"\nafter adding 'other': article programs = {sorted(programs)} (expect both), rows={_count(art)}")

    # 3) Re-exporting the SAME series without force -> diff, nothing written.
    again = ctx.xocd_export_service.export_series(snapshot, folder)
    print(f"\nre-export same series: applied={again.applied} needs_validation={again.needs_validation}")
    print(f"  changed files: {sorted(again.diff)} (expect empty - no data changed)")
    rows_before = _count(art)

    # 4) Mutate one article code, re-export -> the diff should surface the change.
    snapshot.engineering.families[0].members[0].reduced_article = "NOALE_X"
    changed = ctx.xocd_export_service.export_series(snapshot, folder)
    print(f"\nafter a change, needs_validation={changed.needs_validation}, "
          f"article.csv rows unchanged on disk={_count(art) == rows_before}")
    adiff = changed.diff.get("xocd_article.csv", {})
    print(f"  xocd_article diff: +{len(adiff.get('added', []))} / -{len(adiff.get('removed', []))}")

    # 5) Apply with force -> written.
    forced = ctx.xocd_export_service.export_series(snapshot, folder, force=True)
    print(f"\nforced apply: applied={forced.applied}")

    # 6) Text (T) properties must emit NO property values (pCon rejects them;
    #    otherwise the import warns "values not allowed for text properties").
    classes = ctx.engineering_class_service.get_classes(snapshot)
    xocd = ctx.xocd_export_service
    cctx = {"program": result.program, "price_list": "STD"}
    base_rows = xocd._property_values(snapshot, cctx, classes, {})
    flipped = None
    for cls in classes:
        for a in cls.properties:
            key = xocd._prop_ident(a.property_name)
            if any(r[3] == key for r in base_rows):
                a.type = "T"
                flipped = key
                break
        if flipped:
            break
    if flipped:
        after = xocd._property_values(snapshot, cctx, classes, {})
        assert not any(r[3] == flipped for r in after), \
            f"text property '{flipped}' still emitted values"
        print(f"OK: text (T) property '{flipped}' emits no property values")

    # 7) Productline (Program_ID / OCD 'series'): derived from the product RANGE
    #    (commercial series), consistent with the lower-case program key - NOT
    #    the specific product code. Aeron => program 'aeron', series 'AERON'.
    from models.product import Product
    probe = Product(code="AER1A11AF", range_name="Aeron")
    assert xocd.program_key(probe) == "aeron", xocd.program_key(probe)
    assert xocd.series_id(probe) == "AERON", xocd.series_id(probe)
    assert xocd.series_id(Product(code="XZ-9")) == "XZ9"  # code-only fallback
    print("OK: productline Program_ID from range ('Aeron'->'AERON'), not code")

    # Every exported article carries program(field0) + series_id(field5).
    prod = snapshot.product
    prog, sid = xocd.program_key(prod), xocd.series_id(prod)
    with (folder / "xocd_article.csv").open(encoding="utf-8", newline="") as fh:
        arows = [r for r in csv.reader(fh, delimiter=";") if r and r[0] == prog]
    assert arows and all(r[5] == sid for r in arows), "article series != Program_ID"
    print(f"OK: {len(arows)} exported articles stamped series='{sid}'")

    # xocd_programs Label = the series designation (range), NOT the product name.
    with (folder / "xocd_programs.csv").open(encoding="utf-8", newline="") as fh:
        prow = next(r for r in csv.reader(fh, delimiter=";") if r and r[0] == prog)
    assert prow[1] == sid, prow
    assert prow[2] == (prod.range_name or prod.name or prog), prow
    if prod.range_name and prod.range_name != prod.name:
        assert prow[2] != prod.name, f"Label is the product name, not the series: {prow[2]!r}"
    print(f"OK: xocd_programs Label = series designation '{prow[2]}'")

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
