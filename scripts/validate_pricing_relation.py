"""Headless validation for the PA_PRICING relation generator.

Builds a synthetic non-super product (config attributes + option increments) and
a super product (BOM) and checks :class:`PricingRelationService` produces the
PDM-style PA_PRICING body for each. No database access.

Run:  $env:PYTHONPATH="."; python scripts/validate_pricing_relation.py
"""
from __future__ import annotations

from models.article import Article
from models.snapshot import Snapshot
from services.pricing_relation_service import PricingRelationService


def _non_super_snapshot() -> Snapshot:
    snap = Snapshot()
    snap.articles = [Article(id="a1", code="NOALE211")]
    # Two config attributes contribute codes; options carry increments.
    snap.article_varcond_terms = {
        "a1": [
            {"name": "Type", "order": 1, "has_dependent_options": 0, "order_code": "1"},
            {"name": "Number of Fabrics", "order": 2, "has_dependent_options": 0,
             "order_code": "1"},
        ]
    }
    snap.option_increments = {
        "NOALE211": [
            {"item": "NOALE211", "option_id": 6530, "option_name": "Base Finish",
             "value_name": "Chrome", "code": "CHR"},
            {"item": "NOALE211", "option_id": 6530, "option_name": "Base Finish",
             "value_name": "R02", "code": "R02"},  # same option -> one line
            {"item": "NOALE211", "option_id": 9269, "option_name": "Castors Glides",
             "value_name": "Castors", "code": "CA"},
        ]
    }
    return snap


def _super_snapshot() -> Snapshot:
    snap = Snapshot()
    snap.articles = [Article(id="s1", code="DWE362S4C.0812")]
    snap.article_components = {
        "s1": [{"sub_item": "DWE3UH4.", "quantity": 1, "sequence": "1"}]
    }
    snap.article_varcond_terms = {
        "s1": [
            {"name": "Width", "order": 1, "has_dependent_options": 4, "order_code": ""},
        ]
    }
    snap.article_prefix_length = {"s1": 6}
    return snap


def main() -> int:
    svc = PricingRelationService.__new__(PricingRelationService)

    # 1) Non-super: property-concatenation PA_PRICING.
    res = svc.generate(snapshot=_non_super_snapshot())
    assert not res.is_super, res
    assert res.article_price_lines == ["$VARCOND = Type + Number_Of_Fabrics"], \
        res.article_price_lines
    # one incremental line per distinct option id (deduped)
    assert res.incremental_lines == [
        "$VARCOND = Type + Number_Of_Fabrics + ' 6530=' + Base_Finish",
        "$VARCOND = Type + Number_Of_Fabrics + ' 9269=' + Castors_Glides",
    ], res.incremental_lines
    assert "* Article prices" in res.body and "* Incremental prices" in res.body
    assert res.relation_name == "PA_PRICING_PRODUCT"  # no product code on bare snapshot
    print("OK: non-super PA_PRICING body matches PDM concatenation format")

    # 2) Super: delegated to the VARCOND generator.
    res2 = svc.generate(snapshot=_super_snapshot())
    assert res2.is_super, res2
    assert "$VARCOND = 'DWE3UH4.'" in res2.body, res2.body
    # Character-count stamp: total >= component chars, one component definition.
    assert res2.char_count_total == len(res2.body), res2.char_count_total
    assert res2.definition_count >= 1, res2.definition_count
    assert 0 < res2.char_count_components <= res2.char_count_total, res2
    print("OK: super product delegates to VARCOND generator")

    # 3) Empty snapshot warns.
    empty = svc.generate(snapshot=Snapshot())
    assert any("article_varcond_terms" in w for w in empty.warnings), empty.warnings
    print("OK: no config attributes -> warns")

    # 4) commit() upserts the relation and it survives serialization.
    from services.snapshot_serialization import snapshot_to_dict, snapshot_from_dict
    snap = _non_super_snapshot()
    res = svc.generate(snapshot=snap)
    rel = svc.commit(snap, res)
    assert rel is not None and rel.domain == "P" and rel.type_code == "3", rel
    assert len(snap.relation_objects) == 1, snap.relation_objects
    # re-commit replaces (no duplicate)
    svc.commit(snap, svc.generate(snapshot=snap))
    assert len(snap.relation_objects) == 1, snap.relation_objects
    restored = snapshot_from_dict(snapshot_to_dict(snap))
    assert len(restored.relation_objects) == 1, restored.relation_objects
    assert restored.relation_objects[0].name == "PA_PRICING_PRODUCT"
    assert "$VARCOND = Type + Number_Of_Fabrics" in restored.relation_objects[0].body
    print("OK: commit() persists PA_PRICING (upsert + serialization round-trip)")

    # 5) Split by article prefix -> PA_<prefix> relations (RelObj P_<prefix>).
    sp = Snapshot()
    sp.articles = [
        Article(id="p1", code="DWE36ABAD"),
        Article(id="p2", code="DWE36ABFD"),
        Article(id="p3", code="DWE33DXXX"),
    ]
    sp.article_prefix_length = {"p1": 5, "p2": 5, "p3": 5}
    terms = [{"name": "LegStyle", "order": 1, "has_dependent_options": 0,
              "order_code": "C"}]
    sp.article_varcond_terms = {"p1": terms, "p2": terms, "p3": terms}
    sp.article_components = {
        "p1": [{"sub_item": "COMP1.", "quantity": 1, "sequence": "1"}],
        "p2": [{"sub_item": "COMP2.", "quantity": 1, "sequence": "1"}],
        "p3": [{"sub_item": "COMP3.", "quantity": 1, "sequence": "1"}],
    }
    # Prefix length 5 -> two groups: 'DWE36' (p1,p2) and 'DWE33' (p3).
    splits = svc.generate_split(sp, prefix_length=5)
    names = sorted(r.relation_name for r in splits)
    assert names == ["PA_DWE33", "PA_DWE36"], names
    by_name = {r.relation_name: r for r in splits}
    assert by_name["PA_DWE36"].relobj_name == "P_DWE36"
    assert "COMP1." in by_name["PA_DWE36"].body
    assert "COMP2." in by_name["PA_DWE36"].body
    assert "COMP3." in by_name["PA_DWE33"].body
    assert "COMP3." not in by_name["PA_DWE36"].body
    assert all(r.char_count_total > 0 for r in splits)
    # commit_split stores one relation per group.
    stored = svc.commit_split(sp, splits)
    assert {r.name for r in stored} == {"PA_DWE33", "PA_DWE36"}, stored
    assert len(sp.relation_objects) == 2, sp.relation_objects
    print("OK: split by article prefix -> PA_<prefix> relations (P_/PA_)")

    # 6) Component-relation model: a shared component's rules stored ONCE, and
    #    the BOM alignment links each article to its component relations.
    cr = Snapshot()
    cr.articles = [Article(id="p1", code="DWE36A"), Article(id="p2", code="DWE36B")]
    cr.article_prefix_length = {"p1": 6, "p2": 6}
    terms = [{"name": "LegStyle", "order": 1, "has_dependent_options": 0,
              "order_code": "C"}]
    cr.article_varcond_terms = {"p1": terms, "p2": terms}
    cr.article_components = {
        "p1": [{"sub_item": "SHARED.", "quantity": 1, "sequence": "1"},
               {"sub_item": "UNIQ1.", "quantity": 1, "sequence": "2"}],
        "p2": [{"sub_item": "SHARED.", "quantity": 1, "sequence": "1"},
               {"sub_item": "UNIQ2.", "quantity": 1, "sequence": "2"}],
    }
    comps = svc.generate_component_relations(cr)
    names = sorted(r.relation_name for r in comps)
    assert names == ["PA_SHARED", "PA_UNIQ1", "PA_UNIQ2"], names
    shared = next(r for r in comps if r.relation_name == "PA_SHARED")
    # SHARED. is in both articles but its rule is stored ONCE (deduped).
    assert shared.body.count("$VARCOND = 'SHARED.'") == 1, shared.body
    align = svc.component_alignment(cr)
    assert "PA_SHARED" in align["DWE36A"] and "PA_SHARED" in align["DWE36B"]
    assert "PA_UNIQ1" in align["DWE36A"] and "PA_UNIQ1" not in align["DWE36B"]
    print("OK: component relations dedupe shared component + BOM alignment")

    # 7) Chunking: a component family too big for 64000 splits into ordered parts.
    big = ["a" * 30000, "b" * 30000, "c" * 30000]
    ch = PricingRelationService._chunk_rules(big, 64000)
    assert len(ch) == 2 and ch[0] == big[:2] and ch[1] == [big[2]], [len(c) for c in ch]
    solo = PricingRelationService._chunk_rules(["z" * 70000], 64000)
    assert len(solo) == 1, solo   # a single over-limit rule gets its own chunk
    print("OK: oversized component chunked into ordered parts under the limit")

    print("ALL PRICING RELATION CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
