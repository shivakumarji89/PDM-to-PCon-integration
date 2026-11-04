"""Unified fabric colour resolver: discovery from data, one evaluator, one colour per configuration.

Synthetic models only (the real series are in ``test_ocd_fabric_real_data``). Colour relations are ordinary
preconditions run by the engine's own evaluator; the resolver contributes candidate discovery, the type/colour
structure and the choice of one colour.
"""
from __future__ import annotations

from services.ocd_engine import diagnostics as dg
from services.ocd_engine import fabric
from services.ocd_engine import fabric_resolver as fr
from services.ocd_engine import model as m
from services.ocd_engine.configuration_engine import ConfigurationEngine
from services.ocd_engine.relation_evaluator import EvalContext
from tests.ocd_engine.ocd_helpers import chosen, model, prop, rel, run


def colour(code, text=None, *, default=False, labels=(), rel_type=m.PRECONDITION, key=None, domain="C"):
    relations = (rel(text, rel_type, domain, name=f"R-{key or code}"),) if text else ()
    return m.ValueDef(key=key or f"c:{code}", value=code, code=code, relations=relations, is_default=default,
                      labels=tuple(labels))


def typed(code, text=None, labels=()):
    return m.ValueDef(key=f"t:{code}", value=code, code=code, labels=tuple(labels),
                      relations=(rel(text, name=f"RT-{code}"),) if text else ())


def label(code, description="Name"):
    return (("en", f"{description} - {code}"), ("de", f"{description} - {code}"))


def fabric_model(colours, *, types=("A", "B"), extra=(), type_name="Fabric_Type", colour_name="Fabric_Colour"):
    props = [prop(type_name, [typed(t) if isinstance(t, str) else t for t in types]),
             prop(colour_name, colours), *extra]
    return model("FD1", props)


A, B = "Fabric_Type = 'A'", "Fabric_Type = 'B'"


def pairs(configs, type_name="Fabric_Type", colour_name="Fabric_Colour"):
    return sorted((chosen(c)[type_name], chosen(c)[colour_name]) for c, _ in configs)


# ------------------------------------------------------------------ the mapping mechanisms
def test_direct_type_to_colour_relations_select_the_first_colour_of_each_type():
    configs, engine = run(fabric_model([colour("A1", A), colour("A2", A), colour("B1", B), colour("B2", B)]))
    assert pairs(configs) == [("A", "A1"), ("B", "B1")]
    assert engine.fabric_resolutions                                   # the decision is explained, not implied


def test_precondition_with_specified_and_in_form_is_evaluated_like_any_relation():
    spec = "(SPECIFIED Fabric_Type) AND (Fabric_Type IN ('A', 'B'))"
    configs, _ = run(fabric_model([colour("A1", "(SPECIFIED Fabric_Type) AND (Fabric_Type IN ('A'))"),
                                   colour("A2", spec), colour("B1", spec)]))
    assert pairs(configs) == [("A", "A1"), ("B", "A2")]               # A2 is valid for both types, B1 is second


def test_colour_precondition_on_another_property_changes_the_choice_per_configuration():
    grade = prop("Grade", ["G1", "G2"])
    mdl = fabric_model([colour("A1", "Fabric_Type = 'A' AND Grade = 'G2'"), colour("A2", A), colour("B1", B)],
                       extra=[grade])
    configs, _ = run(mdl)
    got = sorted((chosen(c)["Fabric_Type"], chosen(c)["Grade"], chosen(c)["Fabric_Colour"]) for c, _ in configs)
    assert got == [("A", "G1", "A2"), ("A", "G2", "A1"), ("B", "G1", "B1"), ("B", "G2", "B1")]


def test_a_selection_relation_on_a_colour_value_is_not_defined_by_ocd_and_is_not_guessed():
    sel = colour("A1", "Fabric_Type = 'A'", rel_type=m.SELECTION, key="c:A1sel")
    mdl = fabric_model([sel, colour("A2", A), colour("A3", A), colour("B1", B)])
    configs, engine = run(mdl)
    assert pairs(configs) == [("A", "A2"), ("B", "B1")]               # A1 is never offered
    uncertain = engine.sink.by_code(dg.FABRIC_COLOUR_UNCERTAIN)
    assert uncertain and "selection condition" in uncertain[0].message


def test_group_between_type_and_colour_is_resolved_through_the_same_evaluator():
    """Type -> group (group preconditions read the type) -> colours (colour preconditions read the group)."""
    groups = [colour("A1", "Fabric_Type = 'A'"), colour("A2", "Fabric_Type = 'A'"), colour("B1", "Fabric_Type = 'B'")]
    colours = [colour("A101", "Fabric_Group = 'A1'"), colour("A102", "Fabric_Group = 'A1'"),
               colour("A201", "Fabric_Group = 'A2'"), colour("A202", "Fabric_Group = 'A2'"),
               colour("B101", "Fabric_Group = 'B1'"), colour("B102", "Fabric_Group = 'B1'")]
    mdl = model("FD1", [prop("Fabric_Type", [typed("A"), typed("B")]), prop("Fabric_Group", groups),
                        prop("Fabric_Colour", colours)])
    names = {(s.type_property, s.colour_property) for s in fabric.discover_schemes(mdl)}
    assert names == {("Fabric_Type", "Fabric_Group"), ("Fabric_Group", "Fabric_Colour")}
    configs, _ = run(mdl)
    got = sorted((chosen(c)["Fabric_Type"], chosen(c)["Fabric_Group"], chosen(c)["Fabric_Colour"]) for c, _ in configs)
    assert got == [("A", "A1", "A101"), ("B", "B1", "B101")]


def test_group_colour_relation_constraints_decide_which_colour_is_first_valid():
    groups = [colour("A1", "Fabric_Type = 'A'"), colour("A2", "Fabric_Type = 'A'")]
    colours = [colour("A101", "Fabric_Group = 'A1' AND Grade = 'G2'"), colour("A102", "Fabric_Group = 'A1'"),
               colour("A201", "Fabric_Group = 'A2'"), colour("A202", "Fabric_Group = 'A2'")]
    mdl = model("FD1", [prop("Fabric_Type", [typed("A"), typed("A2x")]), prop("Fabric_Group", groups),
                        prop("Grade", ["G1", "G2"]), prop("Fabric_Colour", colours)])
    configs, _ = run(mdl)
    got = {(chosen(c)["Grade"], chosen(c)["Fabric_Group"]): chosen(c)["Fabric_Colour"] for c, _ in configs}
    assert got[("G1", "A1")] == "A102" and got[("G2", "A1")] == "A101"


# ------------------------------------------------------------------ value text fallback
def fallback_model(types=("1D", "1FD"), colours=("1D01", "1D02", "1D03", "1FD01", "1FD02"), **kw):
    desc = kw.get("desc", label)
    return model("FD1", [
        prop("Fabric_Type", [typed(t, labels=desc(t)) for t in types]),
        prop("Fabric_Colour", [colour(c, labels=desc(c)) for c in colours]),
    ])


def test_value_text_fallback_without_any_colour_relation():
    mdl = fallback_model()
    (scheme,) = fabric.discover_schemes(mdl)
    assert scheme.mechanism == fabric.MECH_PREFIX_TEXT
    configs, engine = run(mdl)
    assert pairs(configs) == [("1D", "1D01"), ("1FD", "1FD01")]
    resolution = next(iter(engine.fabric_resolutions.values()))
    assert resolution.mechanism == fabric.MECH_PREFIX_TEXT and dict(resolution.rejected_counts)[fr.REASON_UNMAPPED] >= 2


def test_code_prefix_alone_is_not_a_fabric_relationship():
    """Same codes, but the value texts do not follow ``<description> - <code>``: nothing is classified or reduced."""
    mdl = fallback_model(desc=lambda code: (("en", f"Plain {code.lower()} text"),))
    assert fabric.discover_schemes(mdl) == ()
    configs, _ = run(mdl)
    assert len(configs) == 2 * 5                                      # every colour stays offered, as without a rule


def test_the_value_text_must_name_the_code_the_value_carries():
    mdl = fallback_model(desc=lambda code: (("en", f"Name - X{code}"),))      # description disagrees with the code
    assert fabric.discover_schemes(mdl) == ()


def test_a_single_language_confirming_the_code_is_enough_and_missing_translations_are_tolerated():
    def one_language(code):
        return (("de", f"Name - {code}"),)                             # no English / no other translation
    assert fabric.discover_schemes(fallback_model(desc=one_language))

    many = tuple(f"1D{i:02d}" for i in range(1, 30)) + tuple(f"1FD{i:02d}" for i in range(1, 30))

    def mostly_missing(code):
        return label(code) if code != "1D02" else ()                   # one value of 60 without any translation
    assert fabric.discover_schemes(fallback_model(colours=many, desc=mostly_missing))
    assert fabric.discover_schemes(fallback_model(desc=lambda code: ())) == ()   # no texts: fallback has no evidence


def test_relation_data_does_not_need_translations():
    mdl = fabric_model([colour("A1", A), colour("A2", A), colour("B1", B)])        # no labels anywhere
    (scheme,) = fabric.discover_schemes(mdl)
    assert scheme.mechanism == fabric.MECH_RELATION and scheme.evidence.text_confirmed == 0


def test_ambiguous_prefix_values_are_excluded_not_guessed():
    """Type codes 7O and 7O5: colour 7O576 extends both, so the fallback cannot say which type it belongs to."""
    types, colours = ("7O", "7O5", "ZZ"), ("7O005", "7O009", "7O576", "7O501", "7O502", "ZZ01", "ZZ02")
    mdl = fallback_model(types=types, colours=colours)
    configs, engine = run(mdl)
    got = dict(pairs(configs))
    assert got["7O"] == "7O005" and got["ZZ"] == "ZZ01"
    members, ambiguous = fabric.prefix_members("7O", [v for v in mdl.properties[1].values], list(types))
    assert [v.value for v in ambiguous] == ["7O576", "7O501", "7O502"]
    assert [v.value for v in members] == ["7O005", "7O009"]
    resolved = [r for r in engine.fabric_resolutions.values() if r.type_value == "7O"]
    assert dict(resolved[0].rejected_counts)[fr.REASON_AMBIGUOUS] == 3
    assert "7O5" not in got or got["7O5"] not in ("7O576",)           # an ambiguous colour is never picked for 7O5


def test_relation_literals_resolve_what_the_fallback_cannot():
    """The same ambiguous codes with explicit relations: the evaluator knows 7O576 belongs to 7O."""
    colours = [colour("7O576", "Fabric_Type = '7O'"), colour("7O501", "Fabric_Type = '7O5'"),
               colour("7O502", "Fabric_Type = '7O5'")]
    mdl = fabric_model(colours, types=("7O", "7O5"))
    assert pairs(run(mdl)[0]) == [("7O", "7O576"), ("7O5", "7O501")]


# ------------------------------------------------------------------ classification is evidence, not a name
def test_property_names_alone_do_not_make_a_fabric():
    colours = [colour("X1"), colour("Y2"), colour("Z3")]                  # named like a fabric, no structure
    mdl = fabric_model(colours)
    assert fabric.discover_schemes(mdl) == ()
    configs, _ = run(mdl)
    assert len(configs) == 2 * 3


def test_a_fabric_type_without_the_word_type_in_its_name_is_found_by_structure():
    mdl = fabric_model([colour("A1", "Upholstered_Base = 'A'"), colour("A2", "Upholstered_Base = 'A'"),
                        colour("B1", "Upholstered_Base = 'B'")],
                       type_name="Upholstered_Base", colour_name="Upholstered_Base_Colour")
    (scheme,) = fabric.discover_schemes(mdl)
    assert (scheme.type_property, scheme.colour_property) == ("Upholstered_Base", "Upholstered_Base_Colour")
    configs, _ = run(mdl)
    assert pairs(configs, "Upholstered_Base", "Upholstered_Base_Colour") == [("A", "A1"), ("B", "B1")]


def test_the_same_structure_without_a_fabric_word_is_reported_and_left_alone():
    colours = [colour("A1", "Edge = 'A'"), colour("A2", "Edge = 'A'"), colour("B1", "Edge = 'B'")]
    mdl = fabric_model(colours, type_name="Edge", colour_name="Material")
    assert fabric.discover_schemes(mdl) == ()
    assert len(fabric.discover_schemes(mdl, confirmed_only=False)) == 1
    configs, engine = run(mdl)
    assert len(configs) == 3                                              # nothing collapsed
    assert engine.sink.by_code(dg.FABRIC_PAIR_UNCONFIRMED)


def test_a_dependent_finish_without_the_prefix_shape_is_not_a_fabric():
    mdl = model("FD1", [prop("Fabric_Type", ["A", "B"]),
                        prop("Fabric_Colour", [colour("Red", A), colour("Blue", A), colour("Green", B)])])
    assert fabric.discover_schemes(mdl) == ()                             # codes do not extend the type codes


# ------------------------------------------------------------------ selection
def test_flagged_default_wins_over_an_earlier_valid_colour():
    configs, engine = run(fabric_model([colour("A1", A), colour("A2", A, default=True), colour("B1", B)]))
    assert pairs(configs) == [("A", "A2"), ("B", "B1")]
    picked = {r.type_value: r.selection for r in engine.fabric_resolutions.values()}
    assert picked == {"A": fr.SELECTED_EXPLICIT, "B": fr.SELECTED_FIRST}


def test_a_flagged_default_that_is_not_valid_is_ignored():
    grade = prop("Grade", ["G1", "G2"])
    mdl = fabric_model([colour("A1", A), colour("A2", "Fabric_Type = 'A' AND Grade = 'G2'", default=True),
                        colour("B1", B)], extra=[grade])
    got = {(chosen(c)["Fabric_Type"], chosen(c)["Grade"]): chosen(c)["Fabric_Colour"] for c, _ in run(mdl)[0]}
    assert got[("A", "G1")] == "A1" and got[("A", "G2")] == "A2"


def test_source_order_is_kept_not_sorted():
    mdl = fabric_model([colour("A2", A), colour("A10", A), colour("A1", A), colour("B1", B)])
    configs, engine = run(mdl)
    assert dict(pairs(configs))["A"] == "A2"
    resolution = next(r for r in engine.fabric_resolutions.values() if r.type_value == "A")
    assert resolution.candidates[:3] == ("A2", "A10", "A1") and resolution.valid == ("A2", "A10", "A1")


def test_duplicate_candidates_are_collapsed_keeping_the_first_occurrence():
    dup = fabric_model([colour("A1", A, key="c:A1a"), colour("A2", A), colour("A1", A, key="c:A1b"), colour("B1", B)])
    configs, engine = run(dup)
    assert pairs(configs) == [("A", "A1"), ("B", "B1")]
    resolution = next(r for r in engine.fabric_resolutions.values() if r.type_value == "A")
    assert resolution.candidates == ("A1", "A2", "B1") and resolution.valid == ("A1", "A2")
    assert resolution.duplicates == 1 and len(resolution.candidates) == len(set(resolution.candidates))


def test_no_valid_colour_rejects_the_configuration_and_explains_why():
    grade = prop("Grade", ["G1", "G2"])
    g2 = "Fabric_Type = 'A' AND Grade = 'G2'"
    mdl = fabric_model([colour("A1", g2), colour("A2", g2), colour("B1", B), colour("B2", B)], extra=[grade])
    configs, engine = run(mdl)
    assert ("A", "G1") not in {(chosen(c)["Fabric_Type"], chosen(c)["Grade"]) for c, _ in configs}
    assert len(configs) == 3                                              # (A,G2), (B,G1), (B,G2)
    (diag,) = engine.sink.by_code(dg.NO_FABRIC_COLOUR)
    assert "precondition FALSE" in diag.message and "no valid colour" in diag.message


def test_an_unreadable_colour_relation_is_never_read_as_valid():
    broken = colour("A1", "Fabric_Type = = 'A' AND")                      # does not parse
    mdl = fabric_model([broken, colour("A2", A), colour("A3", A), colour("B1", B), colour("B2", B)])
    configs, engine = run(mdl)
    assert pairs(configs) == [("A", "A2"), ("B", "B1")]
    assert engine.sink.by_code(dg.FABRIC_COLOUR_UNCERTAIN)


def test_when_every_colour_relation_is_unreadable_nothing_is_enumerated():
    mdl = fabric_model([colour("A1", "Fabric_Type = = 'A' AND"), colour("A2", "Fabric_Type = = 'A' AND")], types=("A",))
    # discovery needs readable literals: with none the pair is not a fabric, so the colours are plain values
    assert fabric.discover_schemes(mdl) == ()
    scheme = fabric.FabricScheme("Fabric_Type", "Fabric_Colour", fabric.MECH_RELATION,
                                 fabric.FabricEvidence(2, 2, 2, name_hint=True))
    engine = ConfigurationEngine(mdl)
    engine._fabric = fr.FabricColourResolver(mdl, engine._tri_checked, [scheme])
    engine._fabric_colours = engine._fabric.colour_properties
    assert list(engine.generate()) == []
    assert engine.sink.by_code(dg.NO_FABRIC_COLOUR) and engine.sink.by_code(dg.FABRIC_COLOUR_UNCERTAIN)


def test_the_rule_can_be_switched_off_for_the_full_colour_set():
    mdl = fabric_model([colour("A1", A), colour("A2", A), colour("B1", B)])
    assert len(run(mdl, fabric_default_only=False)[0]) == 3
    assert len(run(mdl)[0]) == 2


# ------------------------------------------------------------------ reduction happens before expansion
def test_the_colour_node_offers_one_value_so_no_colour_is_ever_expanded():
    pad = prop("Pad", [f"P{i}" for i in range(7)])
    colours = [colour(f"A{i:02d}", A) for i in range(1, 31)] + [colour(f"B{i:02d}", B) for i in range(1, 31)]
    mdl = fabric_model(colours, extra=[pad])
    engine = ConfigurationEngine(mdl)
    offered = []
    original = engine._candidates

    def spy(dim, ctx):
        found = original(dim, ctx)
        if dim.name == "Fabric_Colour":
            offered.append(len(found))
        return found

    engine._candidates = spy
    configs = list(engine.enumerate())
    assert offered and max(offered) == 1
    assert len(configs) == 2 * 7                                          # not 2 x 30 x 7
    full = ConfigurationEngine(mdl, fabric_default_only=False)
    assert len(list(full.enumerate())) == 2 * 30 * 7
    assert engine.stats.nodes < full.stats.nodes / 10


# ------------------------------------------------------------------ cache correctness
def test_candidate_cache_keys_on_the_selected_type_even_when_no_relation_reads_it():
    mdl = fallback_model()
    engine = ConfigurationEngine(mdl)
    got = {chosen(c)["Fabric_Type"]: chosen(c)["Fabric_Colour"] for c in engine.enumerate()}
    assert got == {"1D": "1D01", "1FD": "1FD01"}
    assert engine._candidate_refs["CLS:Fabric_Colour"] == ("FABRIC_TYPE",)


def test_candidate_cache_does_not_leak_a_colour_between_dependent_states():
    grade = prop("Grade", ["G1", "G2"])
    mdl = fabric_model([colour("A1", "Fabric_Type = 'A' AND Grade = 'G2'"), colour("A2", A), colour("B1", B)],
                       extra=[grade])
    engine = ConfigurationEngine(mdl)
    seen = [(chosen(c)["Grade"], chosen(c)["Fabric_Type"], chosen(c)["Fabric_Colour"]) for c in engine.enumerate()]
    again = [(chosen(c)["Grade"], chosen(c)["Fabric_Type"], chosen(c)["Fabric_Colour"]) for c in engine.enumerate()]
    assert sorted(seen) == sorted(again) == [("G1", "A", "A2"), ("G1", "B", "B1"), ("G2", "A", "A1"), ("G2", "B", "B1")]
    assert len({k[1] for k in engine.fabric_resolutions}) == 2            # one explained decision per type value


def test_resolver_explains_selected_type_mechanism_candidates_rejections_and_choice():
    mdl = fabric_model([colour("A1", "Fabric_Type = 'A' AND Grade = 'G2'"), colour("A2", A), colour("A3", A),
                        colour("B1", B), colour("B2", B)], extra=[prop("Grade", ["G1", "G2"])])
    engine = ConfigurationEngine(mdl)
    ctx = EvalContext(values={"FABRIC_TYPE": "A", "GRADE": "G1"}, ban="FD1", tables={})
    resolution, picked = engine._fabric.resolve(mdl.properties[1], ctx)
    assert (resolution.type_value, resolution.mechanism) == ("A", fabric.MECH_RELATION)
    assert resolution.candidates == ("A1", "A2", "A3", "B1", "B2") and resolution.valid == ("A2", "A3")
    assert [(r.value, r.reason) for r in resolution.rejected] == [("A1", fr.REASON_PRECONDITION),
                                                                  ("B1", fr.REASON_PRECONDITION),
                                                                  ("B2", fr.REASON_PRECONDITION)]
    assert resolution.selected == "A2" and resolution.selection == fr.SELECTED_FIRST and picked[0].value == "A2"
    assert "A2 (first-valid)" in resolution.describe()


def test_structure_preview_matches_the_resolver_for_the_relation_mechanism():
    mdl = fabric_model([colour("A1", A), colour("A2", A, default=True), colour("B1", B)])
    by_type = {t.type_value: t for t in fabric.fabric_structure(mdl)}
    assert by_type["A"].colours == ("A1", "A2") and by_type["A"].default_colour == "A2"
    assert by_type["B"].default_colour == "B1"
