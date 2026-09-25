"""XOCD-vs-golden parity check.

Exports a cached family as XOCD, then reads the manufacturer's golden OCD MDB
(via the 32-bit ADODB bridge) and diffs property names, value codes, article
codes and text ids. This is the parity oracle: it measures how close our
generated data is to the real pCon data, and keeps ``MDBService`` earning its
keep as the golden reader.

Run:  $env:PYTHONPATH="."; python scripts/validate_xocd_parity.py [family.json]
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

_GOLDEN = {
    "always.json": r"C:\HermanMillerOFMLSVN\Staging\HermanMiller_old\WS\Seating\Seating\Always\pcr_data_com_ocd.mdb",
    "aeron.json": r"C:\HermanMillerOFMLSVN\Staging\HermanMiller_old\WS\Seating\Seating\Aeron\pcr_data_com_ocd.mdb",
    "nevi.json": r"C:\HermanMillerOFMLSVN\Staging\HermanMiller_old\WS\Tables\Tables\Nevi_enhanced\pcr_data_com_ocd.mdb",
}


def _prepare(ctx, snapshot):
    ctx.snapshot_manager.load_snapshot(snapshot)
    ctx.engineering_reduction_service.materialize_article_sets(snapshot)
    ctx.engineering_initialization_service.initialize(snapshot)
    ctx.engineering_member_service.auto_reduce(snapshot)
    category = (snapshot.product.category if snapshot.product else "") or "Class"
    ctx.engineering_class_service.ensure_standard_classes(snapshot, category)
    ctx.engineering_class_service.commit_config_codes(snapshot)


def _col_set(path: Path, idx: int) -> set[str]:
    """Distinct non-empty values of column ``idx`` across a semicolon CSV."""
    out: set[str] = set()
    if path.is_file():
        with path.open("r", encoding="utf-8", newline="") as fh:
            for row in csv.reader(fh, delimiter=";"):
                if len(row) > idx and row[idx]:
                    out.add(row[idx])
    return out


def _golden_set(ctx, mdb: str, sql: str, col: str) -> set[str]:
    return {
        str(r[col]).strip() for r in ctx.mdb_service.read_table(mdb, sql)
        if r.get(col) not in (None, "")
    }


def _compare(name: str, ours: set[str], golden: set[str]) -> None:
    both, only_ours, only_golden = ours & golden, ours - golden, golden - ours
    denom = len(golden) or 1
    print(f"\n{name}:  match={len(both)}/{len(golden)} ({100 * len(both) // denom}%)  "
          f"only_ours={len(only_ours)}  only_golden={len(only_golden)}")
    if only_golden:
        print(f"   missing (in golden, not ours): {sorted(only_golden)[:10]}")
    if only_ours:
        print(f"   extra   (in ours, not golden): {sorted(only_ours)[:10]}")


def main() -> int:
    name = sys.argv[1] if len(sys.argv) > 1 else "always.json"
    src = _CACHE / name
    if not src.is_file():
        print(f"snapshot not found: {src}")
        return 1
    golden = _GOLDEN.get(name)
    if not golden or not Path(golden).is_file():
        print(f"no golden MDB mapped/found for {name}")
        return 1

    snapshot = snapshot_from_dict(json.loads(src.read_text(encoding="utf-8")))
    ctx = ApplicationContext()
    if not ctx.mdb_service.is_available():
        print("MDB bridge unavailable (needs 32-bit PowerShell + ACE OLEDB).")
        return 1
    _prepare(ctx, snapshot)

    folder = Path(tempfile.gettempdir()) / "validate_xocd_parity"
    for f in folder.glob("*.csv"):
        f.unlink()
    result = ctx.xocd_export_service.export_series(snapshot, folder, force=True)
    print(f"exported program='{result.program}' ok={result.ok}")

    # ours (from XOCD csv) vs golden (from tCOMd_ MDB)
    ours_props = _col_set(folder / "xocd_property.csv", 2)
    ours_values = _col_set(folder / "xocd_propertyvalue.csv", 10)
    ours_articles = _col_set(folder / "xocd_article.csv", 2)
    ours_text = (_col_set(folder / "xocd_propertytext.csv", 2)
                 | _col_set(folder / "xocd_artlongtext.csv", 2))

    g_props = _golden_set(ctx, golden, "SELECT com_PropName FROM tCOMd_Property", "com_PropName")
    g_values = _golden_set(ctx, golden, "SELECT com_PropValueFrom FROM tCOMd_PropValue", "com_PropValueFrom")
    g_articles = _golden_set(ctx, golden, "SELECT com_ArticleCode FROM tCOMd_Article", "com_ArticleCode")
    g_text = _golden_set(ctx, golden, "SELECT com_TextName FROM tCOMd_Text", "com_TextName")

    _compare("Property names", ours_props, g_props)
    _compare("Value codes", ours_values, g_values)
    _compare("Article codes", ours_articles, g_articles)
    _compare("Text ids", ours_text, g_text)
    print("\n(Note: cache is often a subset of the full golden family; gaps are expected.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
