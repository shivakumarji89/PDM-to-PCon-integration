"""Validate export-readiness checks (core.export_readiness.scan_snapshot).

Headless, PDM-free: builds a snapshot with deliberately-bad values and asserts
the expected findings (disallowed characters, empty required columns,
export-transformed characters).

Run:  $env:PYTHONPATH="."; python scripts/validate_export_readiness.py
"""
from __future__ import annotations

from core.export_readiness import ERROR, WARNING, scan_snapshot, summarise
from models.engineering import Engineering
from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.relation_object import RelationObject
from models.snapshot import Snapshot
from models.text_block import TextBlock


def _snapshot() -> Snapshot:
    m_ok = MemberArticle(
        id="1", article_id="A1", reduced_article="NOALE1",
        relation_object="P_NOALE1", code_scheme="NOALE1",
        short_description="Always Lounge", long_description="4 leg base",
    )
    m_bad_rel = MemberArticle(
        id="2", article_id="A2", reduced_article="NOALE2",
        relation_object="P_NOALE 2!", code_scheme="NOALE2",  # space + '!'
        short_description="Sofa & chair", long_description="ok",  # '&' -> warning
    )
    m_no_base = MemberArticle(
        id="3", article_id="A3", reduced_article="",  # not reduced -> error
        relation_object="", code_scheme="",
    )
    eng = Engineering(families=[EngineeringFamily(
        id="f", name="Default", members=[m_ok, m_bad_rel, m_no_base])])
    snap = Snapshot(id="p", engineering=eng)
    snap.text_blocks = [
        TextBlock(name="Leg_Base", en="Leg base"),
        TextBlock(name="Bad Name", en="x"),         # space in identifier
        TextBlock(name="No_En", en=""),              # empty EN -> warning
    ]
    snap.relation_objects = [
        RelationObject(name="B_Type_Chair"),
        RelationObject(name="B_Type Chair"),         # space -> error
    ]
    return snap


def _has(findings, kind, entity_id, field, severity):
    return any(
        f.kind == kind and f.entity_id == entity_id and f.field == field
        and f.severity == severity for f in findings
    )


def main() -> int:
    findings = scan_snapshot(_snapshot())

    assert _has(findings, "article", "A2", "Relation Object", ERROR), findings
    print("OK: disallowed chars in Relation Object flagged (error)")

    assert _has(findings, "article", "A3", "Base Article", ERROR)
    assert _has(findings, "article", "A3", "Relation Object", ERROR) is False, \
        "no relation-required error when base is empty"
    print("OK: empty base article flagged; dependent checks skipped")

    assert _has(findings, "article", "A2", "Short Text", WARNING), findings
    print("OK: '&' in Short Text flagged (warning - rewritten on export)")

    assert _has(findings, "text_block", "Bad Name", "Name", ERROR)
    assert _has(findings, "text_block", "No_En", "EN", WARNING)
    print("OK: text-block bad name (error) + empty EN (warning)")

    assert _has(findings, "relation", "B_Type Chair", "Name", ERROR)
    print("OK: relation object bad name flagged (error)")

    # The clean member/text/relation produce no findings.
    assert not any(f.entity_id in ("A1", "Leg_Base", "B_Type_Chair") for f in findings)
    print("OK: clean entities produce no findings")

    errors, warnings = summarise(findings)
    assert errors >= 3 and warnings >= 2, (errors, warnings)
    print(f"OK: summary counts errors={errors} warnings={warnings}")

    print("ALL EXPORT-READINESS CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
