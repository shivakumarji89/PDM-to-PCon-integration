"""Headless validation for base-length STANDARDISE (registry -> source split).

Proves the guarded source fix: with no registry the base article split is the
article-set base length (unchanged); after applying the registry, the base is
sliced to the authoritative length (Override_Length, else CAD_Length). Also
checks the (program, item) filtering. No PDM, no export - pure slicing.

Run:  $env:PYTHONPATH="."; python scripts/validate_base_length_standardise.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from core.application_context import ApplicationContext
from models.article import Article
from models.article_set import ArticleSet
from models.product import Product
from models.snapshot import Snapshot
from services.pricing_service import PricingService


def _snapshot() -> Snapshot:
    snap = Snapshot()
    snap.product = Product(code="AERON", name="Aeron", range_name="Aeron")
    snap.articles = [Article(id="1", code="AER1A11AF")]
    snap.article_sets = [ArticleSet(id="s", base_length=3, base_code="AER", article_ids=["1"])]
    return snap


def main() -> int:
    ctx = ApplicationContext()
    pricing = PricingService(ctx)
    reg = ctx.price_update_service
    checks: dict[str, bool] = {}

    snap = _snapshot()

    # No overrides -> unchanged: base = code[:base_length] = 'AER'.
    checks["no registry: base = AER (unchanged)"] = \
        pricing._prefix_by_item(snap)["AER1A11AF"] == "AER"

    path = Path(tempfile.gettempdir()) / "std_registry.csv"
    if path.is_file():
        path.unlink()

    # CAD length only (no override) -> standardise to 'AER1A11'.
    reg.write_base_length_registry(path, [{
        "Program": "aeron", "Item": "AER1A11AF", "CurrentBase": "AER",
        "CAD_Length": "7", "Expected_Base": "AER1A11", "Override_Length": "",
        "Status": "MISMATCH"}])
    n = reg.apply_registry(snap, path)
    checks["apply_registry count = 1"] = n == 1
    checks["CAD length: base = AER1A11"] = \
        pricing._prefix_by_item(snap)["AER1A11AF"] == "AER1A11"

    # User Override_Length wins over CAD.
    snap2 = _snapshot()
    reg.write_base_length_registry(path, [{
        "Program": "aeron", "Item": "AER1A11AF", "CurrentBase": "AER",
        "CAD_Length": "7", "Expected_Base": "AER1A11", "Override_Length": "5",
        "Status": "MISMATCH"}])
    reg.apply_registry(snap2, path)
    checks["override wins: base = AER1A (len 5)"] = \
        pricing._prefix_by_item(snap2)["AER1A11AF"] == "AER1A"

    # A different series' rows are ignored.
    snap3 = _snapshot()
    path.unlink(missing_ok=True)  # fresh registry: only the other series' row
    reg.write_base_length_registry(path, [{
        "Program": "nevi", "Item": "AER1A11AF", "CurrentBase": "AER",
        "CAD_Length": "7", "Expected_Base": "AER1A11", "Override_Length": "",
        "Status": "MISMATCH"}])
    n3 = reg.apply_registry(snap3, path)
    checks["other series ignored (count 0)"] = n3 == 0
    checks["other series: base stays AER"] = \
        pricing._prefix_by_item(snap3)["AER1A11AF"] == "AER"

    print("checks:")
    ok = True
    for name, passed in checks.items():
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and bool(passed)
    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
