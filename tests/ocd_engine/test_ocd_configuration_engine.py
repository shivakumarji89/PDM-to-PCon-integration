"""Configuration engine: pruning, dependencies, ArtBase, computed properties, VARCOND, limits."""
import pytest

from core.cancellation import CancellationToken, OperationCancelled, cancellation_scope
from services.ocd_engine import diagnostics as dg
from services.ocd_engine import model as m
from services.ocd_engine.configuration_engine import ConfigurationEngine, EnumerationLimits
from ocd_helpers import chosen, model, prop, rel, run, val


def finals(results, name):
    return [chosen(c)[name] for c, _ in results]


# ------------------------------------------------------------------ pruning and dependencies
def test_unrestricted_product_without_relations():
    mdl = model("B", [prop("A", ["1", "2"]), prop("B", ["x", "y", "z"])])
    results, _ = run(mdl)
    assert len(results) == 6


def test_value_precondition_restricts_dependent_property():
    mdl = model("B", [
        prop("Top", ["Q75", "OAK"]),
        prop("Bottom", [val("MDF", rels=[rel("(SPECIFIED Top) AND (Top IN ('Q75'))")]),
                        val("OAK", rels=[rel("(SPECIFIED Top) AND (Top IN ('OAK'))")])]),
    ])
    results, _ = run(mdl)
    pairs = {(chosen(c)["Top"], chosen(c)["Bottom"]) for c, _ in results}
    assert pairs == {("Q75", "MDF"), ("OAK", "OAK")}          # Q75+OAK and OAK+MDF are rejected


def test_dependency_listed_after_dependent_is_still_ordered_correctly():
    # Bottom is declared *before* Top but depends on it; the engine must reorder.
    mdl = model("B", [
        prop("Bottom", [val("MDF", rels=[rel("Top = 'Q75'")]), val("OAK", rels=[rel("Top = 'OAK'")])]),
        prop("Top", ["Q75", "OAK"]),
    ])
    results, _ = run(mdl)
    assert {(chosen(c)["Top"], chosen(c)["Bottom"]) for c, _ in results} == {("Q75", "MDF"), ("OAK", "OAK")}


def test_multi_level_dependency_chain():
    mdl = model("B", [
        prop("A", ["a1", "a2"]),
        prop("B", [val("b1", rels=[rel("A = 'a1'")]), val("b2", rels=[rel("A = 'a2'")])]),
        prop("C", [val("c1", rels=[rel("B = 'b1'")]), val("c2", rels=[rel("B = 'b2'")])]),
    ])
    results, _ = run(mdl)
    assert {tuple(chosen(c)[n] for n in "ABC") for c, _ in results} == {("a1", "b1", "c1"), ("a2", "b2", "c2")}


def test_multi_parent_relation_and_or_not_in():
    cond = "(P1 = 'x' AND P2 NOT IN ('n')) OR P1 = 'y'"
    mdl = model("B", [prop("P1", ["x", "y"]), prop("P2", ["m", "n"]),
                      prop("Child", [val("c", rels=[rel(cond)])])])
    results, _ = run(mdl)
    got = {(chosen(c)["P1"], chosen(c)["P2"], chosen(c)["Child"]) for c, _ in results}
    assert got == {("x", "m", "c"), ("y", "m", "c"), ("y", "n", "c"),    # valid: child offered
                   ("x", "n", None)}                                      # no valid value => left unset


def test_property_precondition_false_hides_property():
    mdl = model("NODLE150", [prop("Cutout", ["NC", "FT"], rels=[rel("$ BAN IN ('NODLE300')")]),
                             prop("Frame", ["OAK"])])
    results, _ = run(mdl)
    assert len(results) == 1 and chosen(results[0][0]) == {"Cutout": "<hidden>", "Frame": "OAK"}
    mdl2 = model("NODLE300", [prop("Cutout", ["NC", "FT"], rels=[rel("$ BAN IN ('NODLE300')")]), prop("Frame", ["OAK"])])
    assert len(run(mdl2)[0]) == 2


def test_class_precondition_hides_every_property_of_the_class():
    cls = m.ClassDef(name="OPT", relations=(rel("Mode = 'on'"),))
    mdl = model("B", [prop("Mode", ["on", "off"], cls="BASE"), prop("X", ["1", "2"], cls="OPT"),
                      prop("Y", ["a"], cls="OPT")], classes=[cls])
    results, _ = run(mdl)
    by_mode = {chosen(c)["Mode"]: chosen(c) for c, _ in results}
    assert by_mode["off"]["X"] == "<hidden>" and by_mode["off"]["Y"] == "<hidden>"
    assert len([1 for c, _ in results if chosen(c)["Mode"] == "on"]) == 2


def test_undefined_precondition_is_not_a_violation():
    # Dependent references a property that has no value: UNDEFINED => value stays valid.
    mdl = model("B", [prop("Dep", [val("d", rels=[rel("Ghost = 'x'")])])])
    results, _ = run(mdl)
    assert len(results) == 1 and chosen(results[0][0])["Dep"] == "d"


def test_no_valid_value_leaves_property_unset_with_info_diagnostic():
    mdl = model("B", [prop("T", ["BSE"]), prop("Mat", [val("MDF", rels=[rel("T = 'Q75'")])])])
    results, engine = run(mdl)
    assert chosen(results[0][0])["Mat"] is None
    assert engine.sink.count(dg.NO_VALID_VALUE) == 1


def test_artbase_restriction_limits_values():
    mdl = model("B", [prop("A", ["1", "2", "3"], allowed=["2", "3"])])
    assert finals(run(mdl)[0], "A") == ["2", "3"]


def test_pruning_beats_cartesian_product():
    # 8 properties x 6 values with a chain of equalities: product 1.68M, valid 6.
    props = [prop("P0", [str(i) for i in range(6)])]
    for n in range(1, 8):
        props.append(prop(f"P{n}", [val(str(i), rels=[rel(f"P{n - 1} = '{i}'")]) for i in range(6)]))
    results, engine = run(model("B", props))
    assert len(results) == 6
    assert engine.stats.nodes < 500                                       # not 6**8


def test_configurations_with_identical_encoding_stay_distinct():
    mdl = model("B", [prop("Silent", ["a", "b"]), prop("Loud", ["x"])])
    results, _ = run(mdl)
    keys = {tuple((a.prop.name, a.value.value) for a in c.assignments) for c, _ in results}
    assert len(keys) == 2


def test_output_is_deterministic():
    mdl = model("B", [prop("A", ["2", "1"]), prop("B", ["y", "x"])])
    first = [chosen(c) for c, _ in run(mdl)[0]]
    assert first == [chosen(c) for c, _ in run(mdl)[0]]


# ------------------------------------------------------------------ constraints / selection
def test_constraint_prunes_early_and_reports_reason():
    constraint = rel("Objects: o IS_A c. Condition: Size = 'big'. Restrictions: Mat = 'steel'.",
                     rel_type=4, name="C1")
    mdl = model("B", [prop("Size", ["big", "small"]), prop("Mat", ["steel", "wood"])],
                article_relations=[constraint])
    results, engine = run(mdl)
    assert {(chosen(c)["Size"], chosen(c)["Mat"]) for c, _ in results} == {
        ("big", "steel"), ("small", "steel"), ("small", "wood")}
    assert any(d.relation == "C1" for d in engine.sink.by_code(dg.INVALID_CONFIGURATION))


def test_constraint_on_computed_value_is_checked_at_finalize():
    action = rel("Total = A + B", rel_type=3, order=1)
    constraint = rel("Objects: o IS_A c. Restrictions: Total = 'xy'.", rel_type=4, order=2)
    mdl = model("B", [prop("A", ["x", "q"]), prop("B", ["y"])], article_relations=[action, constraint])
    results, _ = run(mdl)
    assert finals(results, "A") == ["x"]


def test_selection_condition_met_requires_a_value():
    sel = rel("Mode = 'on'", rel_type=2)
    mdl = model("B", [prop("Mode", ["on", "off"]), prop("Extra", [val("e", rels=[rel("Mode = 'never'")])], rels=[sel])])
    results, _ = run(mdl)
    # Extra has no valid value; with Mode=on its selection condition is TRUE => configuration rejected
    assert {chosen(c)["Mode"] for c, _ in results} == {"off"}


def test_selection_condition_undefined_does_not_force_evaluation():
    sel = rel("Ghost = 'on'", rel_type=2)
    mdl = model("B", [prop("Extra", [val("e", rels=[rel("Mode = 'never'")])], rels=[sel])])
    assert len(run(mdl)[0]) == 1


# ------------------------------------------------------------------ computed properties
def test_computed_property_with_conditional_branches_concatenation_and_self_reference():
    code = rel(
        "Code = SUBSTR($BAN,0,3) IF Type IN ('A','B'),\n"
        "Code = Code + Type + ' ' + Finish IF Armpads = 'W' AND Type IN ('A','B'),\n"
        "Code = Code + Type IF Armpads = 'N' AND Type IN ('A','B'),\n"
        "Code = SUBSTR($BAN,0,2) IF Type IN ('S')", rel_type=3, name="CODE")
    codeprop = prop("Code", [], rels=[code], scope="R")
    mdl = model("AER1A11", [prop("Type", ["A", "S"]), prop("Armpads", ["W", "N"]), prop("Finish", ["G1"]), codeprop])
    results, _ = run(mdl)
    computed = {(chosen(c)["Type"], chosen(c)["Armpads"]): r.computed["CODE"] for c, r in results}
    assert computed == {("A", "W"): "AERA G1", ("A", "N"): "AERA", ("S", "W"): "AE", ("S", "N"): "AE"}


def test_action_bound_to_hidden_property_does_not_run():
    action = rel("Out = 'ran'", rel_type=3)
    mdl = model("B", [prop("Gate", ["on", "off"]),
                      prop("Holder", [], rels=[rel("Gate = 'on'"), action])])
    results, _ = run(mdl)
    ran = {chosen(c)["Gate"]: "OUT" in r.computed for c, r in results}
    assert ran == {"on": True, "off": False}


def test_value_bound_action_runs_only_when_value_is_set():
    mdl = model("B", [prop("A", [val("x", rels=[rel("Mark = 'x-chosen'", rel_type=3)]), "y"])])
    results, _ = run(mdl)
    assert {chosen(c)["A"]: r.computed.get("MARK") for c, r in results} == {"x": "x-chosen", "y": None}


def test_actions_run_in_relation_order_within_an_entity():
    a2 = rel("V = V + 'b'", rel_type=3, order=20)
    a1 = rel("V = 'a'", rel_type=3, order=10)
    results, _ = run(model("B", [prop("P", ["1"])], article_relations=[a2, a1]))
    assert results[0][1].computed["V"] == "ab"


# ------------------------------------------------------------------ VARCOND and domains
def test_varcond_is_a_list_and_skips_undefined_operands():
    price = rel("$VARCOND = '6821=' + Cut, $VARCOND = '7030=' + Leg, $VARCOND = '6695=' + Top",
                rel_type=3, domain="P")
    mdl = model("B", [prop("Cut", ["NC"], rels=[rel("$ BAN IN ('NOPE')")]), prop("Leg", ["WSL"]),
                      prop("Top", ["Q75"])], article_relations=[price])
    ((cfg, res),) = run(mdl)[0]
    assert res.varconds == ["7030=WSL", "6695=Q75"]                       # hidden Cut: no 6821 key


def test_price_domain_assignments_do_not_leak_into_configuration():
    price = rel("Aux = 'p', $VARCOND = 'K'", rel_type=3, domain="P")
    config_rel = rel("Probe = Aux", rel_type=3, domain="C", order=99)
    mdl = model("B", [prop("A", ["1"])], article_relations=[price, config_rel])
    ((cfg, res),) = run(mdl)[0]
    assert "AUX" not in res.computed and "PROBE" not in res.computed and res.varconds == ["K"]


def test_varconds_from_properties_and_values_follow_spec_order_and_dedupe():
    art = rel("$VARCOND = 'ART'", rel_type=3, domain="P")
    pr = rel("$VARCOND = 'PROP'", rel_type=3, domain="P")
    vr = rel("$VARCOND = 'VAL', $VARCOND = 'ART'", rel_type=3, domain="P")
    mdl = model("B", [prop("A", [val("x", rels=[vr])], rels=[pr])], article_relations=[art])
    assert run(mdl)[0][0][1].varconds == ["ART", "PROP", "VAL"]


# ------------------------------------------------------------------ safeguards
def test_cancellation_is_honoured_between_nodes():
    token = CancellationToken()
    mdl = model("B", [prop("A", [str(i) for i in range(50)]), prop("B", [str(i) for i in range(50)])])
    engine = ConfigurationEngine(mdl)
    seen = 0
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        for _ in engine.enumerate():
            seen += 1
            if seen == 10:
                token.request_cancel()
    assert seen < 2500


def test_explosion_limit_reports_truncation_instead_of_silently_stopping():
    mdl = model("B", [prop("A", [str(i) for i in range(20)]), prop("B", [str(i) for i in range(20)])])
    results, engine = run(mdl, limits=EnumerationLimits(max_configurations=50))
    assert len(results) == 50 and engine.stats.truncated
    (diag,) = engine.sink.by_code(dg.ENUMERATION_TRUNCATED)
    assert diag.severity is dg.Severity.ERROR and "incomplete" in diag.message


def test_node_limit_also_truncates_and_reports():
    mdl = model("B", [prop("A", [str(i) for i in range(30)]), prop("B", [str(i) for i in range(30)])])
    _, engine = run(mdl, limits=EnumerationLimits(max_nodes=40))
    assert engine.stats.truncated and engine.sink.count(dg.ENUMERATION_TRUNCATED) == 1


def test_progress_callback_receives_stats():
    seen = []
    mdl = model("B", [prop("A", [str(i) for i in range(40)]), prop("B", [str(i) for i in range(40)])])
    run(mdl, progress=lambda stats: seen.append(stats.nodes), progress_every=100)
    assert len(seen) >= 3 and seen[-1] > 1600


def test_unparsable_relation_is_reported_never_silently_true_or_false():
    mdl = model("B", [prop("A", [val("x", rels=[rel("A = = 'x'", name="BROKEN")]), "y"])])
    results, engine = run(mdl)
    assert len(results) == 2                                              # treated as undefined, not a violation
    (diag,) = engine.sink.by_code(dg.RELATION_PARSE_ERROR)
    assert diag.relation == "BROKEN"
    assert all(r.uncertain for _, r in results if chosen(_)["A"] == "x")


def test_cyclic_dependency_is_reported_and_enumeration_still_completes():
    mdl = model("B", [prop("A", [val("a", rels=[rel("B = 'b'")])]), prop("B", [val("b", rels=[rel("A = 'a'")])])])
    results, engine = run(mdl)
    assert engine.sink.count(dg.CYCLIC_DEPENDENCY) >= 1 and len(results) == 1


def test_limit_equal_to_the_result_size_is_not_reported_as_truncation():
    mdl = model("B", [prop("A", ["1", "2", "3"])])
    results, engine = run(mdl, limits=EnumerationLimits(max_configurations=3))
    assert len(results) == 3 and not engine.stats.truncated
    assert engine.sink.count(dg.ENUMERATION_TRUNCATED) == 0
    results, engine = run(mdl, limits=EnumerationLimits(max_configurations=2))
    assert len(results) == 2 and engine.stats.truncated
