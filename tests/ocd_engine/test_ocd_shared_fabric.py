"""Shared fabric selection (opt-in): positions that offer the same fabric types are one choice.

Synthetic models only. Two fabric positions (a primary and a follower, e.g. Back/Arms and Seat) that offer the same set
of type codes carry the same type and the same colour; the follower is restricted at its own node, so the independent
product is never enumerated. The SKU still encodes both positions.
"""
from __future__ import annotations

import inspect

import pytest

from core.cancellation import CancellationToken, OperationCancelled, cancellation_scope
from services.ocd_engine import diagnostics as dg
from services.ocd_engine import fabric
from services.ocd_engine import model as m
from services.ocd_engine.codescheme_engine import CodeSchemeDef, CodeSchemeEncoder
from services.ocd_engine.configuration_engine import ConfigurationEngine
from services.ocd_engine.generator import OcdArticleGenerator
from tests.ocd_engine import ocd_helpers
from tests.ocd_engine.ocd_helpers import chosen, model, prop, rel
from tests.ocd_engine.test_ocd_fabric_resolver import colour, typed

BACK_T, BACK_C, SEAT_T, SEAT_C = "Back_Fabric_Type", "Back_Fabric_Colour", "Seat_Fabric_Type", "Seat_Fabric_Colour"

BACK_COLOURS = [("A1", "A"), ("A2", "A"), ("B1", "B"), ("B2", "B"), ("C1", "C")]
SEAT_COLOURS = [("A1", "A"), ("A2", "A"), ("B2", "B"), ("B3", "B"), ("C1", "C")]      # B1 is back-only, B3 seat-only


def positions(back=BACK_COLOURS, seat=SEAT_COLOURS, *, back_types="ABC", seat_types="ABC", extra=(), names=None,
              seat_rule=None, seat_colour_rules=None, back_rule=None):
    bt, bc, st, sc = names or (BACK_T, BACK_C, SEAT_T, SEAT_C)
    seat_colour_rules = seat_colour_rules or {}

    def colours(pairs, type_name, rules=None):
        rules = rules or {}
        return [colour(code, f"{type_name} = '{t}'" + (f" AND {rules[code]}" if code in rules else ""),
                       key=f"{type_name}:{code}") for code, t in pairs]

    seat_props = [prop(st, [typed(t) for t in seat_types], rels=[rel(seat_rule)] if seat_rule else ()),
                  prop(sc, colours(seat, st, seat_colour_rules), rels=[rel(seat_rule)] if seat_rule else ())]
    back_rels = [rel(back_rule)] if back_rule else ()
    return model("ML1", [prop(bt, [typed(t) for t in back_types], rels=back_rels),
                         prop(bc, colours(back, bt), rels=back_rels), *seat_props, *extra])


def run(mdl, **kwargs):
    """The constraint is opt-in; these tests switch it on unless a test says otherwise."""
    kwargs.setdefault("shared_fabric", True)
    return ocd_helpers.run(mdl, **kwargs)


def pairs(configs, names=(BACK_T, BACK_C, SEAT_T, SEAT_C)):
    bt, bc, st, sc = names
    return [(c[bt], c[bc], c[st], c[sc]) for c in (chosen(cfg) for cfg, _ in configs)]


# ------------------------------------------------------------------ what is tied (derived from the data)
@pytest.mark.parametrize("names", [(BACK_T, BACK_C, SEAT_T, SEAT_C),
                                   ("Frame_Fabric_Type", "Frame_Fabric_Colour", "Cushion_Fabric_Type", "Cushion_Fabric_Colour")])
def test_ties_are_derived_from_the_data_not_from_property_or_type_names(names):
    mdl = positions(names=names)
    (tie,) = fabric.shared_fabric_ties(mdl, fabric.discover_schemes(mdl))
    assert (tie.primary_type, tie.primary_colour, tie.follower_type, tie.follower_colour) == names
    assert ConfigurationEngine(mdl, shared_fabric=True).fabric_ties == (tie,)


def test_positions_with_different_type_lists_are_independent_choices():
    mdl = positions(back_types="ABC", seat_types="ABD", seat=[("A1", "A"), ("B2", "B"), ("D1", "D")])
    assert fabric.shared_fabric_ties(mdl, fabric.discover_schemes(mdl)) == ()
    tied = run(mdl)[0]
    independent = run(mdl, shared_fabric=False)[0]
    assert pairs(tied) == pairs(independent) and len(tied) == 3 * 3


# ------------------------------------------------------------------ one shared type and colour
def test_both_positions_use_the_same_type_and_colour_by_default_colour():
    configs, _ = run(positions())
    got = pairs(configs)
    assert all(bt == st and bc == sc for bt, bc, st, sc in got)
    # B1 (the back's first colour) is not valid on the seat: the pick is the first colour valid in BOTH positions
    assert sorted(got) == [("A", "A1", "A", "A1"), ("B", "B2", "B", "B2"), ("C", "C1", "C", "C1")]


def test_the_same_code_in_both_positions_stays_valid():
    """The ``1HA01 1HA01`` shape: one fabric code in the back and the seat is a valid configuration."""
    assert ("A", "A1", "A", "A1") in pairs(run(positions())[0])
    assert ("A", "A1", "A", "A1") in pairs(run(positions(), fabric_default_only=False)[0])


def test_every_valid_colour_keeps_only_tied_pairs_and_excludes_different_colours_and_types():
    configs, _ = run(positions(), fabric_default_only=False)
    got = pairs(configs)
    assert sorted(got) == [("A", "A1", "A", "A1"), ("A", "A2", "A", "A2"), ("B", "B2", "B", "B2"), ("C", "C1", "C", "C1")]
    independent = pairs(run(positions(), fabric_default_only=False, shared_fabric=False)[0])
    assert len(independent) == 5 * 5 and ("A", "A1", "A", "A2") in independent    # 5 back x 5 seat (type, colour) pairs
    assert not any(bc != sc for _, bc, _, sc in got)                                                       # excluded
    assert not any(bt != st for bt, _, st, _ in got)                                                       # different types


def test_a_colour_that_exists_in_one_position_only_never_leaves_the_other_position_unassigned():
    for default_only in (True, False):
        for cfg, _ in run(positions(), fabric_default_only=default_only)[0]:
            assert all(v is not None for v in chosen(cfg).values())
    got = {(bc, sc) for _, bc, _, sc in pairs(run(positions(), fabric_default_only=False)[0])}
    assert ("B1", "B1") not in got and ("B3", "B3") not in got        # back-only / seat-only colours are not shared


def test_the_independent_product_is_not_enumerated_and_then_filtered():
    tied_configs, tied = run(positions())
    _, independent = run(positions(), shared_fabric=False)
    assert tied.stats.emitted == len(tied_configs) == 3                # every emitted configuration is a tied one
    assert independent.stats.emitted == 3 * 3
    assert tied.stats.nodes < independent.stats.nodes

    many = [(f"{t}{n}", t) for t in "ABCDEFGHIJKL" for n in range(1, 6)]
    big = positions(back=many, seat=many, back_types="ABCDEFGHIJKL", seat_types="ABCDEFGHIJKL")
    _, tied_big = run(big, fabric_default_only=False)
    assert tied_big.stats.emitted == 12 * 5                             # not (12 * 5) ** 2
    assert tied_big.stats.nodes < 12 * 5 * 12                           # far below a per-pair walk


def test_the_sku_still_encodes_both_fabric_positions():
    mdl = positions()
    engine = ConfigurationEngine(mdl, shared_fabric=True)
    encoder = CodeSchemeEncoder(CodeSchemeDef(scheme=f"@,@, ,CLS:{BACK_C}, ,CLS:{SEAT_C}"))
    finals = set()
    for config, result in engine.generate():
        encoded = encoder.encode("NOHAN3", engine.view(config.assignments, result.computed))
        finals.add(encoded.final_article)
    assert finals == {"NO A1 A1", "NO B2 B2", "NO C1 C1"}
    assert all(len(f.split()) == 3 for f in finals)                      # base + back position + seat position


# ------------------------------------------------------------------ existing conditions still decide
def test_relations_and_preconditions_of_both_positions_are_still_evaluated():
    finish = prop("Finish", ["F1", "F2"])
    mdl = positions(extra=[finish], seat_colour_rules={"A2": "Finish = 'F2'"})
    got = {(chosen(c)["Finish"], chosen(c)[BACK_C]) for c, _ in run(mdl, fabric_default_only=False)[0]}
    assert ("F2", "A2") in got and ("F1", "A2") not in got               # the seat colour's own precondition applies
    assert {("F1", "A1"), ("F1", "B2"), ("F1", "C1"), ("F2", "A1"), ("F2", "B2"), ("F2", "C1")} <= got


def test_an_explicit_second_fabric_option_stays_independent():
    """The seat is only offered when Fabrics = 2: the data deliberately offers a second fabric, so it is not tied."""
    count = prop("Fabrics", ["1", "2"])
    mdl = positions(extra=[count], seat_rule="Fabrics = '2'")
    tied, engine = run(mdl)
    independent = run(mdl, shared_fabric=False)[0]
    rows = [chosen(c) for c, _ in tied]
    one = [r for r in rows if r["Fabrics"] == "1"]
    two = [r for r in rows if r["Fabrics"] == "2"]
    assert {r[BACK_T] for r in one} == {"A", "B", "C"} and all(r[SEAT_T] == "<hidden>" for r in one)
    assert len(two) == 9 and any(r[BACK_T] != r[SEAT_T] for r in two)       # different fabrics remain selectable
    assert [chosen(c) for c, _ in tied] == [chosen(c) for c, _ in independent]
    assert engine.fabric_ties == ()
    (skip,) = engine.fabric_tie_skips
    assert (skip.primary_type, skip.follower_type) == (BACK_T, SEAT_T) and "Fabrics = '2'" in skip.reason
    assert skip.describe().startswith("shared fabric not applied:")


def test_positions_gated_by_the_same_precondition_are_still_tied():
    count = prop("Fabrics", ["1", "2"])
    mdl = positions(extra=[count], seat_rule="Fabrics = '2'", back_rule="Fabrics = '2'")
    configs, engine = run(mdl)
    rows = [chosen(c) for c, _ in configs]
    visible = [r for r in rows if r["Fabrics"] == "2"]
    assert len(visible) == 3 and all(r[BACK_T] == r[SEAT_T] and r[BACK_C] == r[SEAT_C] for r in visible)
    assert len(engine.fabric_ties) == 1 and engine.fabric_tie_skips == ()


def test_no_tie_diagnostics_when_the_constraint_is_off():
    count = prop("Fabrics", ["1", "2"])
    mdl = positions(extra=[count], seat_rule="Fabrics = '2'")
    assert run(mdl, shared_fabric=False)[1].fabric_tie_skips == ()


def test_the_constraint_is_off_by_default_so_other_products_keep_independent_positions():
    configs, engine = ocd_helpers.run(positions())
    assert engine.fabric_ties == () and len(configs) == 3 * 3


# ------------------------------------------------------------------ pins and diagnostics
def test_ties_from_the_unrestricted_model_survive_a_pin_that_narrows_the_type_lists():
    full = positions()
    ties = fabric.shared_fabric_ties(full, fabric.discover_schemes(full))
    pinned = positions()
    pinned = m.ArticleModel(base_code=pinned.base_code, tables=pinned.tables, properties=tuple(
        p if p.name not in (BACK_T, SEAT_T) else
        m.PropertyDef(key=p.key, name=p.name, class_name=p.class_name, scope=p.scope, order=p.order,
                      values=tuple(v for v in p.values if v.value == ("A" if p.name == BACK_T else "B")))
        for p in pinned.properties))
    configs, engine = run(pinned, fabric_ties=ties)
    assert configs == [] and any(d.code == dg.SHARED_FABRIC_UNAVAILABLE for d in engine.sink)
    assert len(run(pinned)[0]) == 1                                      # a tie derived from the pinned model alone is lost


def test_generator_exposes_the_switch_and_defaults_to_independent():
    parameter = inspect.signature(OcdArticleGenerator.generate).parameters["shared_fabric"]
    assert parameter.default is False


# ------------------------------------------------------------------ cancellation and progress
def test_cancellation_and_progress_still_work_with_shared_positions():
    many = [(f"{t}{n}", t) for t in "ABCDEFGHIJKL" for n in range(1, 40)]
    mdl = positions(back=many, seat=many, back_types="ABCDEFGHIJKL", seat_types="ABCDEFGHIJKL")
    token, seen, ticks = CancellationToken(), 0, []
    engine = ConfigurationEngine(mdl, shared_fabric=True, fabric_default_only=False, progress=lambda st: ticks.append(st.nodes), progress_every=50)
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        for _ in engine.enumerate():
            seen += 1
            if seen == 5:
                token.request_cancel()
    assert 5 <= seen < 12 * 39
    full = ConfigurationEngine(mdl, shared_fabric=True, fabric_default_only=False, progress=lambda st: ticks.append(st.nodes), progress_every=50)
    assert len(list(full.enumerate())) == 12 * 39 and ticks and ticks[-1] == full.stats.nodes
