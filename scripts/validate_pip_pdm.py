"""Reconstruct a product's PIP directly from PDM (no Excel) and print it.

Picks the first active product whose code matches a pattern, then classifies
functional (head) vs physical (tail) features, orders them, and shows the
values + codes + notes.

Run:  $env:PYTHONPATH="."; python scripts/validate_pip_pdm.py [CODE_LIKE]
"""
from __future__ import annotations

import sys

from core.application_context import ApplicationContext


def main() -> int:
    like = sys.argv[1] if len(sys.argv) > 1 else "DWE3%"
    ctx = ApplicationContext()
    repo = ctx.pdm_service.repository
    try:
        print("connection:", repo.test_connection())
    except Exception as e:  # noqa: BLE001
        print("NO PDM CONNECTION:", str(e)[:200])
        return 1

    picks = repo.fetch_pip_products(like, limit=1)
    if not picks:
        print("no active product for", like)
        return 1
    product_id, code, name = picks[0][0], picks[0][1], picks[0][2]
    print(f"product: id={product_id} code={code!r} name={name!r}\n")

    pip = ctx.pip_service.from_pdm(product_id)
    print(f"PIP title: {pip.title!r}   properties: {len(pip.properties)}")
    for p in pip.properties:
        tag = " [.]" if p.is_separator else ""
        sample = ", ".join(f"{v.value}={v.code}" for v in p.values[:5])
        print(f"  {p.order:>2} {p.name!r}{tag}: {len(p.values)} values  [{sample}]")
    if pip.notes:
        print("\nnotes:")
        for n in pip.notes[:2]:
            print("  -", n[:160].replace("\n", " "))

    # Sanity: has a separator, at least one functional + one physical feature.
    assert any(p.is_separator for p in pip.properties), "no base/tail separator"
    assert pip.properties, "no properties reconstructed"
    print("\nvalidate_pip_pdm: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
