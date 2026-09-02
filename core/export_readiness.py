"""Export-readiness checks (pure - no Qt, no DB).

Scans the engineering data that feeds the OCD/XOCD export for two problems the
export cannot tolerate:

  * disallowed characters in names / codes / text, and
  * required columns left empty.

Returns immutable :class:`ExportFinding` records the UI lists in a summary.
Read-only; never mutates the snapshot.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from models.snapshot import Snapshot

# OCD identifiers (text-block names, relation objects, code scheme) are
# alphanumeric + underscore; article codes also allow the '.' separator and '-'.
_IDENT_BAD = re.compile(r"[^A-Za-z0-9_]")
_CODE_BAD = re.compile(r"[^A-Za-z0-9_.\-]")
# Non-printable control characters are never valid in exported text.
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Characters the OCD Layout export silently rewrites (',' -> '/', '&' -> 'and').
_TEXT_TRANSFORMED = ("&", ",")

ERROR = "error"
WARNING = "warning"

KIND_ARTICLE = "article"
KIND_TEXT_BLOCK = "text_block"
KIND_RELATION = "relation"


@dataclass(frozen=True)
class ExportFinding:
    """One export-readiness problem. ``entity_id`` identifies the row (article id,
    text-block name or relation name); ``field`` is the column label."""

    kind: str
    entity_id: str
    field: str
    severity: str
    message: str


def _distinct_chars(pattern: re.Pattern, value: str) -> str:
    return "".join(sorted({m.group() for m in pattern.finditer(value or "")}))


def _check_identifier(value: str) -> str | None:
    bad = _distinct_chars(_IDENT_BAD, value)
    if bad:
        return f"disallowed character(s) '{bad}' (use letters, digits, '_')"
    return None


def _check_code(value: str) -> str | None:
    bad = _distinct_chars(_CODE_BAD, value)
    if bad:
        return f"disallowed character(s) '{bad}' in code"
    return None


def _text_issues(value: str) -> list[tuple[str, str]]:
    """(severity, message) for a free-text field: control chars are errors,
    export-transformed chars ('&', ',') are warnings."""
    out: list[tuple[str, str]] = []
    if _CONTROL.search(value or ""):
        out.append((ERROR, "contains a control (non-printable) character"))
    hit = [c for c in _TEXT_TRANSFORMED if c in (value or "")]
    if hit:
        out.append((
            WARNING,
            f"contains {', '.join(repr(c) for c in hit)} - rewritten on OCD export",
        ))
    return out


def scan_snapshot(snapshot: Snapshot | None) -> list[ExportFinding]:
    """All export-readiness findings for the active snapshot (read-only)."""
    findings: list[ExportFinding] = []
    if snapshot is None:
        return findings
    _scan_members(snapshot, findings)
    _scan_text_blocks(snapshot, findings)
    _scan_relations(snapshot, findings)
    return findings


def _scan_members(snapshot: Snapshot, out: list[ExportFinding]) -> None:
    engineering = getattr(snapshot, "engineering", None)
    if engineering is None:
        return
    for family in getattr(engineering, "families", []) or []:
        for member in getattr(family, "members", []) or []:
            aid = str(getattr(member, "article_id", "") or "")
            if not aid:
                continue
            base = (getattr(member, "reduced_article", "") or "").strip()
            relation = (getattr(member, "relation_object", "") or "").strip()
            scheme = (getattr(member, "code_scheme", "") or "").strip()
            short = getattr(member, "short_description", "") or ""
            long = getattr(member, "long_description", "") or ""

            # A reduced article must carry a base article number for the export.
            if not base:
                out.append(ExportFinding(KIND_ARTICLE, aid, "Base Article", ERROR,
                                      "empty - article not reduced"))
            else:
                bad = _check_code(base)
                if bad:
                    out.append(ExportFinding(KIND_ARTICLE, aid, "Base Article", ERROR, bad))
            # Relation Object / Code Scheme have deterministic defaults
            # (P_<base> / <base>), so only a NON-empty override is character-
            # checked - an empty value is filled on export, not a problem.
            if relation:
                bad = _check_identifier(relation)
                if bad:
                    out.append(ExportFinding(KIND_ARTICLE, aid, "Relation Object", ERROR, bad))
            if scheme:
                bad = _check_identifier(scheme)
                if bad:
                    out.append(ExportFinding(KIND_ARTICLE, aid, "Code Scheme", ERROR, bad))
            for label, text in (("Short Text", short), ("Long Text", long)):
                for severity, message in _text_issues(text):
                    out.append(ExportFinding(KIND_ARTICLE, aid, label, severity, message))


def _scan_text_blocks(snapshot: Snapshot, out: list[ExportFinding]) -> None:
    for block in getattr(snapshot, "text_blocks", []) or []:
        name = (getattr(block, "name", "") or "").strip()
        if not name:
            out.append(ExportFinding(KIND_TEXT_BLOCK, name, "Name", ERROR, "empty name"))
            continue
        bad = _check_identifier(name)
        if bad:
            out.append(ExportFinding(KIND_TEXT_BLOCK, name, "Name", ERROR, bad))
        if not (getattr(block, "en", "") or "").strip():
            out.append(ExportFinding(KIND_TEXT_BLOCK, name, "EN", WARNING,
                                  "empty - EN text recommended"))
        for lang in ("de", "en", "fr", "nl"):
            for severity, message in _text_issues(getattr(block, lang, "") or ""):
                out.append(ExportFinding(KIND_TEXT_BLOCK, name, lang.upper(), severity, message))


def _scan_relations(snapshot: Snapshot, out: list[ExportFinding]) -> None:
    for relation in getattr(snapshot, "relation_objects", []) or []:
        name = (getattr(relation, "name", "") or "").strip()
        if not name:
            out.append(ExportFinding(KIND_RELATION, name, "Name", ERROR, "empty name"))
            continue
        bad = _check_identifier(name)
        if bad:
            out.append(ExportFinding(KIND_RELATION, name, "Name", ERROR, bad))


def summarise(findings: list[ExportFinding]) -> tuple[int, int]:
    """Return ``(errors, warnings)`` counts."""
    errors = sum(1 for f in findings if f.severity == ERROR)
    return errors, len(findings) - errors
