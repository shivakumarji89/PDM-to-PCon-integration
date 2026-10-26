"""Run the Workbench VARCOND generator on a parity fixture.

    python -m scripts.varcond_parity.run_python --fixture F.json --mode legacy_exact --out run.json

The result keeps the generated text byte-for-byte (``text``) next to the input
manifest the generator consumed, ready for ``compare.py``. ``--mode default``
runs the Workbench's refined behaviour; ``legacy_exact`` runs the literal
``execThread`` port. Neither mode touches a database.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.varcond_parity.inputs import build_manifest, fixture_to_snapshot, load_fixture
from services.varcond_service import VarCondService


def run(fixture: dict, mode: str) -> dict:
    request = dict(fixture.get("request", {}))
    snapshot = fixture_to_snapshot(fixture)
    service = VarCondService.__new__(VarCondService)  # generate() needs no context
    article_codes = request.get("article_codes")
    result = service.generate(
        prefix=request.get("prefix", ""),
        property_exclusions=request.get("property_exclusions", ""),
        property_substitutions=request.get("property_substitutions", ""),
        snapshot=snapshot,
        legacy_exact=(mode == "legacy_exact"),
        article_codes=article_codes if mode == "legacy_exact" else None,
    )
    return {
        "fixture": fixture.get("name", ""),
        "provenance": fixture.get("provenance", ""),
        "mode": mode,
        "text": result.text,
        "rules": [r.rule for r in result.rules],
        "warnings": result.warnings,
        "excluded": result.excluded,
        "inputs": build_manifest(snapshot, article_codes, request),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--mode", choices=("default", "legacy_exact"), default="legacy_exact")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    payload = run(load_fixture(args.fixture), args.mode)
    Path(args.out).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{payload['mode']}: {len(payload['rules'])} rule(s), {len(payload['warnings'])} warning(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
