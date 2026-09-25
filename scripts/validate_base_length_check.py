"""Headless validation for the base-length check (PDM CAD-maintenance vs package).

Builds XOCD packages whose base article rows reconstruct to a full item, injects
``Item.Notes`` values (as PDM's CAD Maintenance would hold them), and checks that
:meth:`PriceUpdateService.compare_base_lengths` flags where the package's stored
base article differs from ``full_item[:prefix_len]``. No PDM access (Notes are
injected); also unit-checks the Notes -> length parsing.

Run:  $env:PYTHONPATH="."; python scripts/validate_base_length_check.py
"""
from __future__ import annotations

import csv
import shutil
import tempfile
from pathlib import Path

from core.application_context import ApplicationContext

_DELIM = ";"
_ENC = "latin-1"


def _seed(folder: Path, article: str, varcond: str, extra_articles: tuple = ()) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    row = ["always", "EURO_2025", article, varcond, "S", "B", "", "", "100", "1",
           "EUR", "20250101", "99991231", ""]
    with (folder / "xocd_price.csv").open("w", encoding=_ENC, newline="") as fh:
        csv.writer(fh, delimiter=_DELIM, lineterminator="\r\n").writerow(row)
    # Authoritative article list: xocd_article.csv (Program, _, ArticleID, ...).
    art_rows = [["always", "", a, "C", "HM", "ALWAYS", a, a, "0", "1", "C62", a]
                for a in (article, *extra_articles)]
    with (folder / "xocd_article.csv").open("w", encoding=_ENC, newline="") as fh:
        csv.writer(fh, delimiter=_DELIM, lineterminator="\r\n").writerows(art_rows)


def main() -> int:
    ctx = ApplicationContext()
    svc = ctx.price_update_service
    checks: dict[str, bool] = {}

    # Notes -> prefix length parsing (PDM getArticlePrefixLength).
    plen = svc._prefix_len_from_notes
    checks["notes '7' -> 7"] = plen("7") == 7
    checks["notes '6,' -> 6"] = plen("6,") == 6
    checks["notes '5,11352,12182' -> 5"] = plen("5,11352,12182") == 5
    checks["notes '' -> 0"] = plen("") == 0
    checks["notes 'abc' -> 0"] = plen("abc") == 0
    checks["notes '7,2' -> 2 (last wins)"] = plen("7,2") == 2

    root = Path(tempfile.gettempdir()) / "validate_base_len"
    shutil.rmtree(root, ignore_errors=True)

    # Mismatch: base 'AER' (len 3) but PDM says prefix length 7 -> 'AER1A11'.
    # 'ORPHAN' is in the article table with no price row - it must still be listed.
    _seed(root / "wrong", "AER", "1A11AF", extra_articles=("ORPHAN",))
    r1 = svc.compare_base_lengths(root / "wrong", notes_by_item={"AER1A11AF": "7"})
    e1 = next(e for e in r1.entries if e.full_item == "AER1A11AF")
    checks["article list from xocd_article (orphan listed)"] = \
        any(e.full_item == "ORPHAN" for e in r1.entries)
    checks["mismatch: full item reconstructed"] = e1.full_item == "AER1A11AF"
    checks["mismatch: pdm_len 7"] = e1.pdm_len == 7
    checks["mismatch: expected AER1A11"] = e1.expected_base == "AER1A11"
    checks["mismatch: flagged not-match"] = e1.match is False
    checks["mismatch: report counts it"] = len(r1.mismatches) == 1

    # Match: base 'AER1A11' with varcond 'AF' and PDM prefix length 7.
    _seed(root / "right", "AER1A11", "AF")
    r2 = svc.compare_base_lengths(root / "right", notes_by_item={"AER1A11AF": "7"})
    e2 = r2.entries[0]
    checks["match: expected == stored base"] = e2.expected_base == "AER1A11" == e2.article
    checks["match: flagged match"] = e2.match is True
    checks["match: no mismatches"] = len(r2.mismatches) == 0

    # No Notes -> length 0 (undefined) is not counted as a mismatch.
    r3 = svc.compare_base_lengths(root / "right", notes_by_item={})
    checks["no notes: not a mismatch"] = len(r3.mismatches) == 0 and r3.entries[0].pdm_len == 0
    checks["entry carries program"] = r1.entries[0].program == "always"

    # Registry write/read preserves the user's Override_Length across a re-check.
    reg = root / "base_length_overrides.csv"
    base_row = {
        "Program": "aeron", "Item": "AER1A11AF", "CurrentBase": "AER",
        "CAD_Length": "7", "Expected_Base": "AER1A11", "Override_Length": "",
        "Status": "MISMATCH",
    }
    svc.write_base_length_registry(reg, [dict(base_row)])
    checks["registry: no override yet"] = svc.read_base_length_registry(reg) == {}
    svc.write_base_length_registry(reg, [{**base_row, "Override_Length": "5"}])
    checks["registry: override stored"] = svc.read_base_length_registry(reg) == {("aeron", "AER1A11AF"): "5"}
    # A fresh re-check (blank Override_Length) must NOT clobber the saved edit.
    svc.write_base_length_registry(reg, [dict(base_row)])
    checks["registry: edit preserved on re-check"] = \
        svc.read_base_length_registry(reg) == {("aeron", "AER1A11AF"): "5"}

    print("checks:")
    ok = True
    for name, passed in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and bool(passed)
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
