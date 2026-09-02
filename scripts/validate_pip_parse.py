"""Validate the PIP parser against the real Everywhere Tables vocabulary sheet.

Parses one product sheet and checks the ordered properties, their value/code
pairs, the base/tail separator and notes come through as expected.

Run:  $env:PYTHONPATH="."; python scripts/validate_pip_parse.py [xlsx] [sheet]
"""
from __future__ import annotations

import sys
from pathlib import Path

from core.application_context import ApplicationContext

_DEFAULT_XLSX = Path.home() / "Downloads" / "Everywhere Tables Vocabulary 2025.xlsx"
_DEFAULT_SHEET = "Rectangle, Post Leg"


def main() -> int:
    xlsx = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_XLSX
    sheet = sys.argv[2] if len(sys.argv) > 2 else _DEFAULT_SHEET
    if not xlsx.is_file():
        print(f"workbook not found: {xlsx}")
        return 1

    svc = ApplicationContext().pip_service
    product = svc.parse_sheet(xlsx, sheet)
    print(f"title: {product.title!r}  sheet: {product.sheet!r}")
    print(f"properties: {len(product.properties)}")
    for p in product.properties:
        tag = " [.]" if p.is_separator else ""
        sample = ", ".join(f"{v.value}={v.code}" for v in p.values[:4])
        print(f"  {p.order:>2} {p.name!r}{tag}: {len(p.values)} values  [{sample}]")
    if product.properties and product.properties[-1].notes:
        print("notes:")
        for n in product.properties[-1].notes[:5]:
            print(f"  - {n}")

    # Assertions: real Rectangle sheet shape.
    names = [p.name for p in product.properties]
    assert product.title, "missing title"
    assert any(p.is_separator for p in product.properties), "no base/tail '.' separator"
    # Assertions: structure holds on any sheet; value codes on the Rectangle.
    assert product.title, "missing title"
    assert product.properties, "no properties parsed"
    assert any(p.is_separator for p in product.properties), "no base/tail '.' separator"
    if sheet == _DEFAULT_SHEET:
        depth = next((p for p in product.properties if p.name == "Depth"), None)
        assert depth is not None, "Depth property not parsed"
        dcodes = {v.value: v.code for v in depth.values}
        assert dcodes.get("450") == "04" and dcodes.get("900") == "09", f"Depth codes wrong: {dcodes}"
        width = next((p for p in product.properties if p.name == "Width"), None)
        assert width is not None, "Width property not parsed"
        wcodes = {v.value: v.code for v in width.values}
        assert wcodes.get("2000") == "20", f"Width codes wrong: {wcodes}"
    print("\nvalidate_pip_parse: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
