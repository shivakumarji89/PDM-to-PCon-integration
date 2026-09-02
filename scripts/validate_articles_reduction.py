"""Headless smoke test for the reorganized Articles reduction page.

Run with an offscreen Qt platform:
    $env:QT_QPA_PLATFORM="offscreen"; python scripts/validate_articles_reduction.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from core.application_context import ApplicationContext  # noqa: E402
from models.article import Article  # noqa: E402
from models.product import Product  # noqa: E402
from ui.pages.articles_page import (  # noqa: E402
    ArticlesPage,
    _COL_BASE,
    _COL_LEN,
    _COL_LONG,
    _COL_REMAINING,
    _COL_SHORT,
    _COL_SOURCE,
)


def cell(table, row, col):
    item = table.item(row, col)
    return item.text() if item is not None else None


def main() -> int:
    app = QApplication.instance() or QApplication([])
    ctx = ApplicationContext()

    # 1) Constructs cleanly with no snapshot.
    page = ArticlesPage(ctx)
    page._group_by_base = False  # line-item mode for the per-row assertions below
    assert page._table.rowCount() == 0, "empty page should have no rows"

    # 2) Build a snapshot: three articles sharing the prefix 'ABC-', with mixed
    #    code lengths (7 and 8), distinct product ids and names.
    product = Product(id="p1", code="P1", name="Prod")
    snapshot = ctx.snapshot_manager.create_empty_snapshot(product)
    snapshot.articles = [
        Article(id="a1", product_id="P100", code="ABC-100", name="Name One", description="First", status="Active"),
        Article(id="a2", product_id="P200", code="ABC-200", name="Name Two", description="Second", status="Active"),
        Article(id="a3", product_id="P300", code="ABC-3500", name="Name Three", description="Third", status="Active"),
    ]
    # Share the product registry (id -> descriptive name), as the Product page
    # does once its navigator hierarchy has loaded.
    ctx.set_product_registry([
        Product(id="P100", code="ABC-100", name="Chair Product"),
        Product(id="P200", code="ABC-200", name="Sofa Product"),
        Product(id="P300", code="ABC-3500", name="Chaise Product"),
    ])
    ctx.engineering_initialization_service.initialize(snapshot)
    assert ctx.active_snapshot is snapshot

    page.refresh()
    assert page._table.rowCount() == 3, f"expected 3 rows, got {page._table.rowCount()}"

    # Default base = the FULL article code, so base == source and remaining is
    # empty for every row.
    for row in range(3):
        base = cell(page._table, row, _COL_BASE)
        remaining = cell(page._table, row, _COL_REMAINING)
        source = cell(page._table, row, _COL_SOURCE)
        assert base == source, f"row {row} base={base!r} source={source!r}"
        assert remaining == "", f"row {row} remaining should be empty, got {remaining!r}"
    print("OK: default base = full article length (base == source)")

    # 3) Each set's base length is derived (Class Creation) and seeds to the full
    #    length (8 = the longest code). Len is EMPTY until reduced - auto-reduce on
    #    entry only fires once the MATERIALISED article_sets exist, which this
    #    synthetic snapshot has none of.
    set_ids = next(iter(page._set_len_by_ids))
    assert page._set_len_by_ids[set_ids] == 8, page._set_len_by_ids[set_ids]
    lens = {
        cell(page._table, r, _COL_SOURCE): cell(page._table, r, _COL_LEN)
        for r in range(3)
    }
    assert lens["ABC-100"] == "", lens
    assert lens["ABC-3500"] == "", lens
    print("OK: Len empty by default (no materialised sets to auto-reduce)")

    # Apply the set's base length (3) via its per-set Apply.
    page._apply_set(set_ids, 3)
    for row in range(3):
        assert cell(page._table, row, _COL_BASE) == "ABC"
        assert cell(page._table, row, _COL_LEN) == "3"
    # Applying also selects the set's articles (they flow to the Builder).
    assert len(ctx.article_service.selected_articles()) == 3, "apply should select the set"
    print("OK: per-set Apply stamps base length + selects the set")

    # 4) Short/Long defaults: Short Text = generic product-TYPE name (product
    #    name up to the first '/'; here no '/' so the full name); Long Text = the
    #    article's PRODUCT name from the shared registry (per-row).
    assert cell(page._table, 0, _COL_SHORT) == "Chair Product", cell(page._table, 0, _COL_SHORT)
    assert cell(page._table, 0, _COL_LONG) == "Chair Product", cell(page._table, 0, _COL_LONG)
    assert cell(page._table, 1, _COL_LONG) == "Sofa Product", cell(page._table, 1, _COL_LONG)
    page._table.item(0, _COL_SHORT).setText("Short override")
    page._table.item(0, _COL_LONG).setText("Long one")
    member0 = page._table.item(0, _COL_SOURCE).data(Qt.ItemDataRole.UserRole)[1]
    assert member0.short_description == "Short override", member0.short_description
    assert member0.long_description == "Long one", member0.long_description
    print("OK: short/long per-row defaults (product name) and persist on edit")

    # Copy Text: copy each shown article's Long Text into its Short Text.
    page._on_copy_long_to_short()
    assert member0.short_description == "Long one", member0.short_description
    print("OK: Copy Text copies long text into short text")

    # Clear menu: Long reverts to the default product name (not blank); Short and
    # Length reset fully on the shown rows.
    page._on_clear_long()
    assert member0.long_description == "", member0.long_description
    assert cell(page._table, 0, _COL_LONG) == "Chair Product", cell(page._table, 0, _COL_LONG)
    page._on_clear_short()
    assert member0.short_description == "", member0.short_description
    page._on_clear_length()
    assert page._base_len_by_member == {}, page._base_len_by_member
    for row in range(page._table.rowCount()):
        assert cell(page._table, row, _COL_LEN) == "", cell(page._table, row, _COL_LEN)
    print("OK: Clear resets Length/Short fully; Long reverts to product name; Len empty")

    # 5) Switching to a different product rebuilds the sets and clears the stale
    #    base-length override (family id is reused across products).
    product2 = Product(id="p2", code="P2", name="Prod2")
    snapshot2 = ctx.snapshot_manager.create_empty_snapshot(product2)
    snapshot2.id = product2.id
    snapshot2.articles = [
        Article(id="b1", code="XY9", description="One", status="Active"),
        Article(id="b2", code="XY8", description="Two", status="Active"),
    ]
    ctx.engineering_initialization_service.initialize(snapshot2)
    page.refresh()
    assert page._base_len_by_member == {}, f"stale overrides not cleared: {page._base_len_by_member}"
    set2 = next(iter(page._set_len_by_ids))
    # New product's full code length is 3 ('XY9'/'XY8').
    assert page._set_len_by_ids[set2] == 3, page._set_len_by_ids[set2]
    print("OK: product change rebuilds the set + resets base length")

    # 6) Grouped view collapses line items to one row per Base Article, and a
    #    text edit on the base row applies to every member under it.
    page._apply_set(set2, 2)              # XY9 / XY8 -> base 'XY'
    page._group_by_base = True
    page._apply_filter()
    assert page._table.rowCount() == 1, page._table.rowCount()
    assert cell(page._table, 0, _COL_SOURCE) == "XY", cell(page._table, 0, _COL_SOURCE)
    assert cell(page._table, 0, _COL_LEN) == "2", cell(page._table, 0, _COL_LEN)
    page._table.item(0, _COL_LONG).setText("Revive Desk")
    grouped_members = page._table.item(0, _COL_SOURCE).data(Qt.ItemDataRole.UserRole)[2]
    assert all(m.long_description == "Revive Desk" for m in grouped_members), \
        [m.long_description for m in grouped_members]
    print("OK: grouped view = 1 row per base; edit applies to all members")

    # 7) Dot-delimiter boundary: some bases end at '.', others keep a tail.
    assert page._dot_boundary_warning(["RY3XTDABFAD.", "RY3XTDABAS.C"]) != ""
    assert page._dot_boundary_warning(["RY3XTDABFAD.", "RY3XTDABND."]) == ""
    assert page._dot_boundary_warning(["RY3XB", "RY3XT"]) == ""
    print("OK: inconsistent '.' boundary flagged (ends-at-dot vs tail-after-dot)")

    print("ALL ARTICLES REDUCTION CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
