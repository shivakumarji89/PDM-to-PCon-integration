"""Run the Workbench VARCOND generator on a parity fixture or snapshot.

    python -m scripts.varcond_parity.run_python --fixture F.json --mode legacy_exact --out run.json
    python -m scripts.varcond_parity.run_python --snapshot snapshot.json --category-id 42 --article-code PARENT.1 --out run.json

The result keeps the generated text byte-for-byte (``text``) next to the input
manifest the generator consumed, ready for ``compare.py``. ``--mode default``
runs the Workbench's refined behaviour; ``legacy_exact`` runs the literal
``execThread`` port. Neither mode touches a database.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from models.snapshot import Snapshot
from scripts.varcond_parity.inputs import build_manifest, fixture_to_snapshot, load_fixture
from services.snapshot_serialization import snapshot_from_dict
from services.varcond_service import VarCondService


def run_snapshot(
    snapshot: Snapshot,
    request: dict,
    mode: str,
    *,
    fixture: str = "",
    provenance: str = "",
) -> dict:
    service = VarCondService.__new__(VarCondService)  # generate() needs no context
    article_codes = request.get("article_codes")
    scoped_snapshot = snapshot
    id_by_code: dict[str, str] = {}
    selected_ids: set[str] = set()
    if mode == "default" and article_codes is not None:
        for article in snapshot.articles:
            if article.id is not None:
                id_by_code.setdefault(article.code or "", str(article.id))
        selected_ids = {
            id_by_code[code] for code in article_codes if code in id_by_code
        }
        scoped_snapshot = copy.copy(snapshot)
        scoped_snapshot.article_components = {
            article_id: components
            for article_id, components in (snapshot.article_components or {}).items()
            if str(article_id) in selected_ids
        }
    result = service.generate(
        prefix=request.get("prefix", ""),
        property_exclusions=request.get("property_exclusions", ""),
        property_substitutions=request.get("property_substitutions", ""),
        snapshot=scoped_snapshot,
        legacy_exact=(mode == "legacy_exact"),
        article_codes=article_codes if mode == "legacy_exact" else None,
    )
    manifest_article_codes = article_codes
    if mode == "default" and article_codes is not None:
        code_by_id = {article_id: code for code, article_id in id_by_code.items()}
        manifest_article_codes = [
            code_by_id[str(article_id)]
            for article_id in (snapshot.article_components or {})
            if str(article_id) in selected_ids and str(article_id) in code_by_id
        ]
    return {
        "fixture": fixture,
        "provenance": provenance,
        "mode": mode,
        "text": result.text,
        "rules": [r.rule for r in result.rules],
        "warnings": result.warnings,
        "excluded": result.excluded,
        "inputs": build_manifest(snapshot, manifest_article_codes, request),
    }


def run(fixture_data: dict, mode: str) -> dict:
    request = dict(fixture_data.get("request", {}))
    return run_snapshot(
        fixture_to_snapshot(fixture_data),
        request,
        mode,
        fixture=fixture_data.get("name", ""),
        provenance=fixture_data.get("provenance", ""),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--fixture")
    source.add_argument("--snapshot")
    parser.add_argument("--category-id", type=int)
    parser.add_argument("--article-code", action="append", dest="article_codes")
    parser.add_argument("--prefix", default="")
    parser.add_argument("--property-exclusions", default="")
    parser.add_argument("--property-substitutions", default="")
    parser.add_argument("--mode", choices=("default", "legacy_exact"), default="legacy_exact")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.fixture:
        payload = run(load_fixture(args.fixture), args.mode)
    else:
        if args.category_id is None:
            parser.error("--category-id is required with --snapshot")
        snapshot_path = Path(args.snapshot)
        snapshot = snapshot_from_dict(json.loads(snapshot_path.read_text(encoding="utf-8-sig")))
        request = {
            "article_codes": args.article_codes,
            "category_id": args.category_id,
            "prefix": args.prefix,
            "property_exclusions": args.property_exclusions,
            "property_substitutions": args.property_substitutions,
        }
        payload = run_snapshot(
            snapshot,
            request,
            args.mode,
            fixture=snapshot_path.name,
            provenance="serialized Workbench snapshot",
        )
    Path(args.out).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{payload['mode']}: {len(payload['rules'])} rule(s), {len(payload['warnings'])} warning(s) -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
