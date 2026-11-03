"""Colours distinguish SKUs; the price is looked up once per distinct price key, never per colour.

Synthetic range ``COL1``: Type A | B, Colour with a per-colour precondition on Type (A1 A2 A3 | B1 B2) plus
one colour that is never offered (``1=2``). Only Colour feeds the code scheme. Which values share a price is
read from the price relations (``$VARCOND``) of the data, not from any property or value name.
"""
from __future__ import annotations

from pathlib import Path

from services.ocd_engine.generator import OcdArticleGenerator
from tests.ocd_engine.ocd_repo_fixture import write

DATE = "2026-01-15"
COLOURS_A, COLOURS_B = ["A1", "A2", "A3"], ["B1", "B2"]
ALL_COLOURS = COLOURS_A + COLOURS_B


def write_colour_range(root: Path, price_relation: str) -> Path:
    db = root / "col" / "ANY" / "1" / "db"
    db.mkdir(parents=True)
    write(db, "ocd_article.csv", "COL1;C;MK;DM;T1;;900;0;1;C62;U1")
    write(db, "ocd_propertyclass.csv", "COL1;1;COL;10;0")
    write(db, "ocd_property.csv",
          "COL;Type;1;;0;C;1;0;1;0;0;0;C;0;\n"
          "COL;Colour;2;;0;C;1;0;1;0;0;0;C;0;")
    values = [("Type", "A", 0), ("Type", "B", 0)]
    relobj = {"A1": 101, "A2": 101, "A3": 101, "A4": 103, "B1": 102, "B2": 102}
    values += [("Colour", c, rel) for c, rel in relobj.items()]
    write(db, "ocd_propertyvalue.csv", "\n".join(
        f"COL;{prop};{i};;{rel};0;0;EQ;{value};;;;;" for i, (prop, value, rel) in enumerate(values, 1)))
    write(db, "ocd_relationobj.csv",
          "101;1;000000000000000001;1;C\n102;1;000000000000000002;1;C\n103;1;000000000000000003;1;C\n"
          "900;1;000000000000000004;3;P")
    write(db, "ocd_relation.csv",
          '000000000000000001; 1;"Type = \'A\'"\n000000000000000002; 1;"Type = \'B\'"\n'
          '000000000000000003; 1;"1=2"\n'
          f'000000000000000004; 1;"{price_relation}"')
    write(db, "ocd_codescheme.csv", 'U1;@,@,@,@, ,COL:Colour;"";"";0;"-";"X";1;"";""')
    write(db, "ocd_price.csv",
          "COL1;;S;B;;;100;1;EUR;20250101;99991231;1;\n"
          "COL1;TYPE=B;S;X;;;10;1;EUR;20250101;99991231;1;\n"
          + "\n".join(f"COL1;COLOUR={c};S;X;;;{n};1;EUR;20250101;99991231;1;"
                      for n, c in enumerate(ALL_COLOURS, 1)))
    return db


def generate(tmp_path, price_relation):
    return OcdArticleGenerator(write_colour_range(tmp_path, price_relation)).generate(
        ["COL1"], currency="EUR", price_date=DATE)


def test_every_valid_colour_is_a_sku_and_the_invalid_colour_is_not(tmp_path):
    outcome = generate(tmp_path, "$VARCOND = 'TYPE=' + Type,")
    assert [s.final_article for s in outcome.skus] == [f"COL1 {c}" for c in ALL_COLOURS]
    assert (outcome.invalid, outcome.duplicates, outcome.truncated) == (0, 0, False)
    assert not any("A4" in s.final_article for s in outcome.skus)       # colour-specific validity preserved


def test_colours_sharing_a_price_key_trigger_one_price_lookup(tmp_path):
    outcome = generate(tmp_path, "$VARCOND = 'TYPE=' + Type,")
    # Keys TYPE=A and TYPE=B: two lookups for five SKUs; only TYPE=B has an extra-charge row.
    assert (outcome.price_evaluations, outcome.price_reused) == (2, 3)
    prices = {s.final_article: f"{s.price:.2f}" for s in outcome.skus}
    assert prices == {**{f"COL1 {c}": "100.00" for c in COLOURS_A}, **{f"COL1 {c}": "110.00" for c in COLOURS_B}}


def test_reused_price_is_identical_to_a_direct_lookup_for_every_sku(tmp_path):
    generator = OcdArticleGenerator(write_colour_range(tmp_path, "$VARCOND = 'TYPE=' + Type,"))
    outcome = generator.generate(["COL1"], currency="EUR", price_date=DATE)
    calculator = generator._price_calculator()
    for sku in outcome.skus:
        direct = calculator.price("COL1", sku.varconds, price_date=DATE, currency="EUR", factors=dict(sku.pricing_factors))
        assert direct.total == sku.price


def test_a_price_relation_that_reads_the_colour_gives_each_colour_its_own_lookup(tmp_path):
    outcome = generate(tmp_path, "$VARCOND = 'COLOUR=' + Colour,")
    assert (outcome.price_evaluations, outcome.price_reused) == (len(ALL_COLOURS), 0)
    assert {s.final_article: f"{s.price:.2f}" for s in outcome.skus} == {
        f"COL1 {c}": f"{100 + n}.00" for n, c in enumerate(ALL_COLOURS, 1)}


def test_a_relation_that_ignores_both_properties_is_one_group(tmp_path):
    outcome = generate(tmp_path, "$VARCOND = 'FIXED',")
    assert len(outcome.skus) == len(ALL_COLOURS)
    assert (outcome.price_evaluations, outcome.price_reused) == (1, len(ALL_COLOURS) - 1)
