"""Relation-aware default fabric colour: the first colour that is valid for the current configuration.

Synthetic range ``FD``: class ``F`` with Fabric_Type A|B, Fabric_Colour (values and their relation texts are
parameters, listed in ``pos_pval`` order), Grade G1|G2 and an optional padding property that only adds nodes.
Colour relations are ordinary preconditions, evaluated by the normal relation evaluator.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.cancellation import CancellationToken, OperationCancelled, cancellation_scope
from services.ocd_engine.generator import OcdArticleGenerator
from tests.ocd_engine.ocd_repo_fixture import write

DATE = "2026-01-15"
A, B = "Fabric_Type = 'A'", "Fabric_Type = 'B'"
A_G2 = "Fabric_Type = 'A' AND Grade = 'G2'"
SCHEME = 'U1;@,@,@,@, ,F:Fabric_Type,F:Fabric_Colour,F:Grade;"";"";0;"-";"X";1;"";""'
SCHEME_PLAIN = 'U1;@,@,@,@, ,F:Grade;"";"";0;"-";"X";1;"";""'
SCHEME_PAD = 'U1;@,@,@,@, ,F:Fabric_Type,F:Fabric_Colour,F:Grade,F:Pad;"";"";0;"-";"X";1;"";""'


def build(root: Path, colours, *, fabric=True, pad=0, flagged=()) -> Path:
    """``colours``: [(value, relation text)] in source order."""
    db = root / "fd" / "ANY" / "1" / "db"
    db.mkdir(parents=True)
    write(db, "ocd_article.csv", "FD1;C;MK;DM;T1;;0;0;1;C62;U1")
    write(db, "ocd_propertyclass.csv", "FD1;1;F;10;0")
    props = ["F;Grade;3;;0;C;1;0;1;0;0;0;C;0;"]
    values = ["F;Grade;1;;0;0;0;EQ;G1;;;;;", "F;Grade;2;;0;0;0;EQ;G2;;;;;"]
    relobj, relation = [], []
    if fabric:
        props += ["F;Fabric_Type;1;;0;C;1;0;1;0;1;0;C;0;", "F;Fabric_Colour;2;;0;C;1;0;1;0;1;0;C;0;"]
        values += ["F;Fabric_Type;1;;0;0;0;EQ;A;;;;;", "F;Fabric_Type;2;;0;0;0;EQ;B;;;;;"]
        for i, (colour, text) in enumerate(colours, 1):
            relobj.append(f"{i};1;{i:018d};1;C")
            relation.append(f'{i:018d}; 1;"{text}"')
            values.append(f"F;Fabric_Colour;{i};;{i};{int(colour in flagged)};0;EQ;{colour};;;;;")
    if pad:
        props.append("F;Pad;4;;0;C;1;0;1;0;0;0;C;0;")
        values += [f"F;Pad;{i};;0;0;0;EQ;P{i};;;;;" for i in range(pad)]
    write(db, "ocd_property.csv", "\n".join(props))
    write(db, "ocd_propertyvalue.csv", "\n".join(values))
    write(db, "ocd_artbase.csv", "")
    write(db, "ocd_relationobj.csv", "\n".join(relobj))
    write(db, "ocd_relation.csv", "\n".join(relation))
    write(db, "ocd_codescheme.csv", SCHEME_PAD if pad else SCHEME if fabric else SCHEME_PLAIN)
    write(db, "ocd_price.csv", "FD1;;S;B;;;100;1;EUR;20250101;99991231;1;")
    return db


def run(db, **kw):
    return OcdArticleGenerator(db).generate(["FD1"], currency="EUR", price_date=DATE, **kw)


def chosen(outcome):
    """{(type, grade): colour}; a second colour for the same pair fails the test."""
    out = {}
    for sku in outcome.skus:
        values = {name: value for _, name, value, _ in sku.values}
        key = (values["Fabric_Type"], values["Grade"])
        assert key not in out, f"two colours for {key}"
        out[key] = values["Fabric_Colour"]
    return out


def test_1_several_valid_colours_select_the_first_only(tmp_path):
    outcome = run(build(tmp_path, [("A1", A), ("A2", A), ("A3", A), ("B1", B)]))
    assert chosen(outcome)[("A", "G1")] == "A1" and chosen(outcome)[("A", "G2")] == "A1"
    assert len(outcome.skus) == 4                                    # (A, B) x (G1, G2): one colour each


def test_2_first_colour_rejected_by_a_relation_selects_the_next(tmp_path):
    outcome = run(build(tmp_path, [("A1", A_G2), ("A2", A), ("A3", A)]))
    assert chosen(outcome)[("A", "G1")] == "A2"                      # A1 needs Grade G2
    assert chosen(outcome)[("A", "G2")] == "A1"                      # ... and is the default once it is valid


def test_3_first_two_rejected_selects_the_third(tmp_path):
    outcome = run(build(tmp_path, [("A1", A_G2), ("A2", A_G2), ("A3", A)]))
    assert chosen(outcome)[("A", "G1")] == "A3" and chosen(outcome)[("A", "G2")] == "A1"


def test_4_no_valid_colour_rejects_the_configuration_with_a_diagnostic(tmp_path):
    outcome = run(build(tmp_path, [("A1", A_G2), ("A2", A_G2), ("B1", B)]))
    assert ("A", "G1") not in chosen(outcome) and chosen(outcome)[("A", "G2")] == "A1"
    assert chosen(outcome)[("B", "G1")] == "B1"
    assert any("no colour of Fabric_Colour is valid" in w for w in outcome.warnings)
    assert outcome.pruned >= 1


def test_5_the_default_follows_another_selected_property(tmp_path):
    outcome = run(build(tmp_path, [("A1", "Fabric_Type = 'A' AND Grade = 'G1'"),
                                   ("A2", "Fabric_Type = 'A' AND Grade = 'G2'")]))
    assert {k: v for k, v in chosen(outcome).items() if k[0] == "A"} == {("A", "G1"): "A1", ("A", "G2"): "A2"}


def test_6_fabric_types_have_their_own_colour_sets_and_defaults(tmp_path):
    outcome = run(build(tmp_path, [("A1", A), ("B1", B), ("B2", B), ("A2", A)]))
    assert chosen(outcome) == {("A", "G1"): "A1", ("A", "G2"): "A1", ("B", "G1"): "B1", ("B", "G2"): "B1"}


def test_7_without_fabric_nothing_is_selected_or_rejected(tmp_path):
    outcome = run(build(tmp_path, [], fabric=False))
    assert len(outcome.skus) == 2 and outcome.pruned == 0
    assert not any("colour" in w for w in outcome.warnings)


def test_8_order_is_the_source_order_not_numeric_or_lexical(tmp_path):
    outcome = run(build(tmp_path, [("A2", A), ("A10", A), ("A1", A)]))
    assert {v for (t, _), v in chosen(outcome).items() if t == "A"} == {"A2"}   # lexical/numeric would be A1


def test_8b_a_flagged_default_wins_when_it_is_valid(tmp_path):
    outcome = run(build(tmp_path, [("A1", A), ("A2", A)], flagged=("A2",)))
    assert {v for (t, _), v in chosen(outcome).items() if t == "A"} == {"A2"}


def test_9_no_duplicate_configurations(tmp_path):
    outcome = run(build(tmp_path, [("A1", A), ("A2", A), ("B1", B), ("B2", B)]))
    finals = [s.final_article for s in outcome.skus]
    assert len(finals) == len(set(finals)) and outcome.duplicates == 0
    assert outcome.configurations == len(outcome.skus) == 4


def test_the_full_colour_set_is_still_available_when_the_rule_is_off(tmp_path):
    outcome = run(build(tmp_path, [("A1", A), ("A2", A), ("B1", B)]), fabric_default_only=False)
    assert len(outcome.skus) == (2 + 1) * 2


def test_10_cancellation_stays_responsive_during_colour_selection(tmp_path):
    db = build(tmp_path, [("A1", A_G2), ("A2", A), ("B1", B)], pad=400)
    token = CancellationToken()

    class Canceller:
        def note(self, _text):
            token.request_cancel()

        def advance(self, _text=""):
            pass

    with cancellation_scope(token), pytest.raises(OperationCancelled):
        OcdArticleGenerator(db).generate(["FD1"], currency="EUR", price_date=DATE, reporter=Canceller())
