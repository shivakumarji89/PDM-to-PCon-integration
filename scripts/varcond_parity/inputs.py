"""Fixture loading and input manifests for the VARCOND parity harness.

A *fixture* is a JSON description of exactly the snapshot fields the Python
generator reads plus the request (parent order, prefix, exclusions,
substitutions). An *input manifest* lists the raw rows the legacy worker's SQL
reads (components, attribute rows, prefix length, option rows) so the same
manifest can be produced for the legacy side from a verified non-production
database and diffed against the Python side. Only fields the legacy worker
actually reads are in the manifest (``component_head_attrs`` is Workbench-only).
"""
from __future__ import annotations

import json
from pathlib import Path

from models.article import Article
from models.snapshot import Snapshot

SNAPSHOT_FIELDS = (
    "article_components",
    "article_varcond_terms",
    "article_prefix_length",
    "component_head_attrs",
    "option_increments",
)


def load_fixture(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def fixture_to_snapshot(fixture: dict) -> Snapshot:
    snapshot = Snapshot()
    snapshot.articles = [Article(id=a["id"], code=a["code"]) for a in fixture.get("articles", [])]
    for name in SNAPSHOT_FIELDS:
        if name in fixture:
            setattr(snapshot, name, fixture[name])
    return snapshot


def build_manifest(snapshot: Snapshot, article_codes: list[str] | None, request: dict) -> dict:
    """Raw legacy-relevant inputs, in the order the legacy worker consumes them."""
    id_by_code: dict[str, str] = {}
    for article in snapshot.articles:
        if article.id is not None:
            id_by_code.setdefault(article.code or "", str(article.id))
    code_by_id = {str(a.id): (a.code or "") for a in snapshot.articles if a.id is not None}
    if article_codes is None:
        article_codes = [code_by_id.get(str(aid), "") for aid in (snapshot.article_components or {})]

    parents = []
    prefixes: set[str] = set()
    for code in article_codes:
        aid = id_by_code.get(code)
        comps = (snapshot.article_components or {}).get(aid, []) if aid is not None else []
        parents.append(
            {
                "code": code,
                "found_in_snapshot": aid is not None,
                "prefix_length": (snapshot.article_prefix_length or {}).get(aid, 0) if aid is not None else None,
                "components": [
                    {"sub_item": c.get("sub_item"), "quantity": c.get("quantity"), "sequence": str(c.get("sequence", ""))}
                    for c in comps
                ],
                "terms": [
                    {
                        "name": t.get("name"),
                        "order": t.get("order"),
                        "has_dependent_options": t.get("has_dependent_options"),
                        "order_code": t.get("order_code") or "",
                    }
                    for t in ((snapshot.article_varcond_terms or {}).get(aid, []) if aid is not None else [])
                ],
            }
        )
        for c in comps:
            sub = (c.get("sub_item") or "").strip()
            if sub:
                dot = sub.find(".")
                prefixes.add(sub[: dot + 1] if dot > -1 else sub)

    increments = {}
    for prefix in sorted(prefixes):
        rows = (snapshot.option_increments or {}).get(prefix, [])
        if rows:
            increments[prefix] = [{"option_id": r.get("option_id"), "option_name": r.get("option_name")} for r in rows]
    return {"request": request, "parents": parents, "option_increments": increments}
