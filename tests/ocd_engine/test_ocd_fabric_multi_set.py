"""Several independent fabric type/colour sets in one article: one valid colour per set, never cross-paired.

Synthetic models only. Every set is its own (type, colour) scheme discovered from the data; a colour is only ever a
candidate for the type its own relations / code prefix tie it to.
"""
from __future__ import annotations

from services.ocd_engine import diagnostics as dg
from services.ocd_engine import fabric
from services.ocd_engine import fabric_resolver as fr
from services.ocd_engine import model as m
from tests.ocd_engine.ocd_helpers import chosen, model, prop, run
from tests.ocd_engine.test_ocd_fabric_resolver import colour, label, typed

SEAT, BACK = "Seat_Fabric_Type", "Back_Fabric_Type"
SEAT_C, BACK_C = "Seat_Fabric_Colour", "Back_Fabric_Colour"


def seat(t):
    return f"{SEAT} = '{t}'"


def back(t):
    return f"{BACK} = '{t}'"


def two_sets(seat_colours=None, back_colours=None, *, extra=None, seat_type=SEAT, back_type=BACK):
    seat_colours = seat_colours or [colour(f"{t}{n}", seat(t)) for t in "AB" for n in (1, 2, 3)]
    back_colours = back_colours or [colour(f"{t}{n}", back(t)) for t in "XY" for n in (1, 2, 3)]
    extra = [prop("Grade", ["G1", "G2"])] if extra is None else extra
    return model("ML1", [prop(seat_type, [typed("A"), typed("B")]), prop(SEAT_C, seat_colours),
                         prop(back_type, [typed("X"), typed("Y")]), prop(BACK_C, back_colours), *extra])


def rows(configs):
    return [chosen(c) for c, _ in configs]


# ------------------------------------------------------------------ one colour per set
def test_each_set_keeps_exactly_one_valid_colour_and_non_fabric_combinations_stay():
    mdl = two_sets()
    assert {(s.type_property, s.colour_property) for s in fabric.discover_schemes(mdl)} == {
        (SEAT, SEAT_C), (BACK, BACK_C)}
    got = rows(run(mdl)[0])
    assert len(got) == 2 * 2 * 2                                      # seat type x back type x Grade, one colour each
    assert {(r[SEAT], r[SEAT_C], r[BACK], r[BACK_C], r["Grade"]) for r in got} == {
        (s, f"{s}1", b, f"{b}1", g) for s in "AB" for b in "XY" for g in ("G1", "G2")}
    assert all(r[SEAT_C].startswith(r[SEAT]) and r[BACK_C].startswith(r[BACK]) for r in got)   # no cross-pairing


def test_identical_colour_codes_in_both_sets_are_not_cross_paired():
    """Both sets use the types ``A``/``B`` and the codes ``A1``..; each colour only follows its own type property."""
    mdl = model("ML1", [prop(SEAT, [typed("A"), typed("B")]),
                        prop(SEAT_C, [colour(f"{t}{n}", seat(t)) for t in "AB" for n in (1, 2)]),
                        prop(BACK, [typed("A"), typed("B")]),
                        prop(BACK_C, [colour(f"{t}{n}", back(t), key=f"b:{t}{n}") for t in "AB" for n in (2, 1)])])
    assert {(s.type_property, s.colour_property) for s in fabric.discover_schemes(mdl)} == {
        (SEAT, SEAT_C), (BACK, BACK_C)}
    got = {(r[SEAT], r[SEAT_C], r[BACK], r[BACK_C]) for r in rows(run(mdl)[0])}
    assert got == {("A", "A1", "A", "A2"), ("A", "A1", "B", "B2"), ("B", "B1", "A", "A2"), ("B", "B1", "B", "B2")}


def test_the_full_colour_set_stays_when_the_rule_is_switched_off():
    got = rows(run(two_sets(), fabric_default_only=False)[0])
    assert len(got) == 2 * 3 * 2 * 3 * 2


def test_a_colour_valid_for_one_set_only_by_a_relation_on_the_other_property_is_checked_by_the_evaluator():
    """A set's colours may read a property of the other set; the shared evaluator decides, no cross list is built."""
    seat_colours = [colour("A1", f"{seat('A')} AND {BACK} = 'Y'"), colour("A2", seat("A")), colour("B1", seat("B"))]
    got = {(r[SEAT], r[BACK]): r[SEAT_C] for r in rows(run(two_sets(seat_colours=seat_colours, extra=[]))[0])}
    assert got[("A", "Y")] == "A1" and got[("A", "X")] == "A2" and got[("B", "X")] == "B1"


# ------------------------------------------------------------------ defaults
def test_each_set_chooses_its_own_flagged_default():
    seat_colours = [colour("A1", seat("A")), colour("A2", seat("A"), default=True), colour("B1", seat("B"))]
    back_colours = [colour("X1", back("X")), colour("X2", back("X")), colour("X3", back("X"), default=True),
                    colour("Y1", back("Y")), colour("Y2", back("Y"), default=True)]
    configs, engine = run(two_sets(seat_colours, back_colours, extra=[]))
    got = {(r[SEAT], r[BACK]): (r[SEAT_C], r[BACK_C]) for r in rows(configs)}
    assert got == {("A", "X"): ("A2", "X3"), ("A", "Y"): ("A2", "Y2"),
                   ("B", "X"): ("B1", "X3"), ("B", "Y"): ("B1", "Y2")}
    selections = {(r.colour_property, r.type_value): r.selection for r in engine.fabric_resolutions.values()}
    assert selections[(SEAT_C, "A")] == fr.SELECTED_EXPLICIT and selections[(SEAT_C, "B")] == fr.SELECTED_FIRST


def test_an_excluded_default_in_one_set_does_not_affect_the_other_set():
    seat_colours = [colour("A1", seat("A")), colour("A2", f"{seat('A')} AND Grade = 'G2'", default=True),
                    colour("B1", seat("B"))]
    back_colours = [colour("X1", back("X")), colour("X2", back("X"), default=True), colour("Y1", back("Y"))]
    got = {(r[SEAT], r["Grade"], r[BACK]): (r[SEAT_C], r[BACK_C])
           for r in rows(run(two_sets(seat_colours, back_colours))[0])}
    assert got[("A", "G1", "X")] == ("A1", "X2")                    # seat default invalid -> first valid; back default valid
    assert got[("A", "G2", "X")] == ("A2", "X2")
    assert got[("B", "G1", "Y")] == ("B1", "Y1")


# ------------------------------------------------------------------ mixed relation patterns
def test_value_level_relation_in_one_set_and_a_group_chain_in_the_other():
    groups = [colour("X1", back("X")), colour("X2", back("X")), colour("Y1", back("Y"))]
    colours = [colour("X101", "Back_Fabric_Group = 'X1'"), colour("X102", "Back_Fabric_Group = 'X1'"),
               colour("X201", "Back_Fabric_Group = 'X2'"), colour("X202", "Back_Fabric_Group = 'X2'"),
               colour("Y101", "Back_Fabric_Group = 'Y1'"), colour("Y102", "Back_Fabric_Group = 'Y1'")]
    seat_colours = [colour("A1", f"{seat('A')} AND Grade = 'G2'"), colour("A2", seat("A")), colour("B1", seat("B"))]
    mdl = model("ML1", [prop(SEAT, [typed("A"), typed("B")]), prop(SEAT_C, seat_colours),
                        prop(BACK, [typed("X"), typed("Y")]), prop("Back_Fabric_Group", groups),
                        prop(BACK_C, colours), prop("Grade", ["G1", "G2"])])
    assert {(s.type_property, s.colour_property) for s in fabric.discover_schemes(mdl)} == {
        (SEAT, SEAT_C), (BACK, "Back_Fabric_Group"), ("Back_Fabric_Group", BACK_C)}
    got = {(r[SEAT], r["Grade"], r[BACK]): (r[SEAT_C], r["Back_Fabric_Group"], r[BACK_C])
           for r in rows(run(mdl)[0])}
    assert len(got) == 2 * 2 * 2
    assert got[("A", "G1", "X")] == ("A2", "X1", "X101") and got[("A", "G2", "Y")] == ("A1", "Y1", "Y101")
    assert got[("B", "G2", "X")] == ("B1", "X1", "X101")


def test_value_text_fallback_works_per_set():
    mdl = model("ML1", [
        prop(SEAT, [typed(t, labels=label(t)) for t in ("1D", "1F")]),
        prop(SEAT_C, [colour(c, labels=label(c)) for c in ("1D01", "1D02", "1F01", "1F02")]),
        prop(BACK, [typed(t, labels=label(t)) for t in ("2D", "2F")]),
        prop(BACK_C, [colour(c, labels=label(c)) for c in ("2D01", "2D02", "2F01", "2F02")])])
    assert {s.mechanism for s in fabric.discover_schemes(mdl)} == {fabric.MECH_PREFIX_TEXT}
    assert {(r[SEAT_C], r[BACK_C]) for r in rows(run(mdl)[0])} == {
        ("1D01", "2D01"), ("1D01", "2F01"), ("1F01", "2D01"), ("1F01", "2F01")}


# ------------------------------------------------------------------ safety
def test_an_unrelated_keyword_property_is_not_reduced():
    care = prop("Fabric_Care", ["Wash", "Dry", "Iron"])
    got = rows(run(two_sets(extra=[care]))[0])
    assert {r["Fabric_Care"] for r in got} == {"Wash", "Dry", "Iron"} and len(got) == 2 * 2 * 3


def test_type_values_are_never_reduced():
    got = rows(run(two_sets(extra=[]))[0])
    assert {r[SEAT] for r in got} == {"A", "B"} and {r[BACK] for r in got} == {"X", "Y"}


def test_a_colour_set_that_fits_two_types_equally_is_not_guessed_and_the_other_set_is_still_reduced():
    """``Seat_Fabric_Colour`` reads both ``Seat_Fabric_Type`` and ``Seat_Trim_Type`` with the same strength."""
    both = lambda t, u: f"{SEAT} = '{t}' AND Seat_Trim_Type = '{u}'"          # noqa: E731
    seat_colours = [colour(f"{t}{n}", both(t, t), key=f"s:{t}{n}") for t in "AB" for n in (1, 2)]
    mdl = model("ML1", [prop(SEAT, [typed("A"), typed("B")]), prop("Seat_Trim_Type", [typed("A"), typed("B")]),
                        prop(SEAT_C, seat_colours), prop(BACK, [typed("X"), typed("Y")]),
                        prop(BACK_C, [colour(f"{t}{n}", back(t)) for t in "XY" for n in (1, 2)])])
    found = fabric.discover(mdl)
    assert {(s.type_property, s.colour_property) for s in found.schemes} == {(BACK, BACK_C)}
    assert [(c, set(types)) for c, types in found.ambiguous] == [(SEAT_C, {SEAT, "Seat_Trim_Type"})]
    configs, engine = run(mdl)
    got = rows(configs)
    assert {r[SEAT_C] for r in got} >= {"A1", "A2", "B1", "B2"}               # left unreduced
    assert {r[BACK_C] for r in got} == {"X1", "Y1"}                           # other set reduced
    note = engine.sink.by_code(dg.FABRIC_PAIR_AMBIGUOUS)
    assert note and SEAT_C in note[0].message and "Seat_Trim_Type" in note[0].message


# ------------------------------------------------------------------ manual override
def test_the_manual_property_does_not_merge_or_replace_the_other_set():
    mdl = model("ML1", [prop("Seat_Type", [typed("A"), typed("B")]), prop("Seat_Colour", [
        colour(f"{t}{n}", "Seat_Type = '%s'" % t) for t in "AB" for n in (1, 2, 3)]),
        prop("Back_Type", [typed("X"), typed("Y")]), prop("Back_Colour", [
            colour(f"{t}{n}", "Back_Type = '%s'" % t) for t in "XY" for n in (1, 2, 3)])])
    assert fabric.discover(mdl).schemes == ()                                  # no keyword: reported, nothing reduced
    found = fabric.discover(mdl, "Seat_Colour")
    assert [(s.type_property, s.colour_property) for s in found.schemes] == [("Seat_Type", "Seat_Colour")]
    got = rows(run(mdl, fabric_property="Seat_Colour")[0])
    assert {r["Seat_Colour"] for r in got} == {"A1", "B1"}                    # selected set reduced
    assert {r["Back_Colour"] for r in got} == {f"{t}{n}" for t in "XY" for n in (1, 2, 3)}


def test_selecting_one_detected_set_keeps_the_other_detected_set():
    mdl = two_sets()
    auto = {(s.type_property, s.colour_property) for s in fabric.discover(mdl).schemes}
    chosen_one = {(s.type_property, s.colour_property) for s in fabric.discover(mdl, SEAT_C).schemes}
    assert auto == chosen_one == {(SEAT, SEAT_C), (BACK, BACK_C)}
    assert rows(run(mdl, fabric_property=SEAT_C)[0]) == rows(run(mdl)[0])
