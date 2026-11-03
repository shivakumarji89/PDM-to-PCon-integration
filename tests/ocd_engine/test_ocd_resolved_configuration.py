"""SKU generation and pricing consume one resolved configuration state (variant conditions + factors).

Synthetic range ``RES1``: Type A | B, Colour constrained by Type through value preconditions (A1 A2 | B1 B2) plus
a colour that is never offered (``1=2``). The price relation ``$VARCOND = 'TYPE=' + Type`` is the only link
between the configuration and the price table.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from services.ocd_engine.generator import GenerationError, OcdArticleGenerator
from services.ocd_engine.pricing import PriceCalculator, PriceRow
from services.ocd_engine.resolved import ResolvedConfiguration
from tests.ocd_engine.ocd_repo_fixture import write

DATE = "2026-01-15"
PRICES = ("RES1;;S;B;;;100;1;EUR;20250101;99991231;1;\n"
          "RES1;TYPE=B;S;X;;;10;1;EUR;20250101;99991231;1;")
SCHEME_COLOUR = 'U1;@,@,@,@, ,RES:Colour;"";"";0;"-";"X";1;"";""'
SCHEME_BASE_ONLY = 'U1;@,@,@,@;"";"";0;"-";"X";1;"";""'


def build(root: Path, *, scheme=SCHEME_COLOUR, prices=PRICES, relation="$VARCOND = 'TYPE=' + Type,") -> Path:
    db = root / "res" / "ANY" / "1" / "db"
    db.mkdir(parents=True)
    write(db, "ocd_article.csv", "RES1;C;MK;DM;T1;;900;0;1;C62;U1")
    write(db, "ocd_propertyclass.csv", "RES1;1;RES;10;0")
    write(db, "ocd_property.csv", "RES;Type;1;;0;C;1;0;1;0;0;0;C;0;\nRES;Colour;2;;0;C;1;0;1;0;0;0;C;0;")
    rel = {"A1": 101, "A2": 101, "B1": 102, "B2": 102, "X9": 103}
    values = [("Type", "A", 0), ("Type", "B", 0)] + [("Colour", c, r) for c, r in rel.items()]
    write(db, "ocd_propertyvalue.csv", "\n".join(
        f"RES;{p};{i};;{r};0;0;EQ;{v};;;;;" for i, (p, v, r) in enumerate(values, 1)))
    write(db, "ocd_relationobj.csv",
          "101;1;000000000000000001;1;C\n102;1;000000000000000002;1;C\n103;1;000000000000000003;1;C\n"
          "900;1;000000000000000004;3;P")
    write(db, "ocd_relation.csv",
          '000000000000000001; 1;"Type = \'A\'"\n000000000000000002; 1;"Type = \'B\'"\n'
          '000000000000000003; 1;"1=2"\n' f'000000000000000004; 1;"{relation}"')
    write(db, "ocd_codescheme.csv", scheme)
    write(db, "ocd_price.csv", prices)
    return db


def run(tmp_path, **kw):
    generator = OcdArticleGenerator(build(tmp_path, **kw))
    return generator, generator.generate(["RES1"], currency="EUR", price_date=DATE)


def test_relations_decide_validity_colour_follows_type_and_the_withdrawn_colour_is_excluded(tmp_path):
    _, outcome = run(tmp_path)
    assert [s.final_article for s in outcome.skus] == [f"RES1 {c}" for c in ("A1", "A2", "B1", "B2")]
    assert outcome.invalid == 0                    # no Type=A/Colour=B1 pair is ever built, nothing is filtered later


def test_the_price_comes_from_the_state_the_relations_resolved(tmp_path):
    _, outcome = run(tmp_path)
    assert {s.final_article: s.price for s in outcome.skus} == {
        "RES1 A1": Decimal("100.00"), "RES1 A2": Decimal("100.00"),
        "RES1 B1": Decimal("110.00"), "RES1 B2": Decimal("110.00")}
    assert {s.final_article: s.varconds for s in outcome.skus}["RES1 B1"] == ("TYPE=B",)


def test_generator_prices_exactly_what_the_shared_entry_point_prices(tmp_path):
    generator, outcome = run(tmp_path)
    calculator = PriceCalculator([PriceRow.from_csv(r) for r in generator.dataset.tables["price"]])
    for sku in outcome.skus:
        resolved = ResolvedConfiguration.of(sku.base_article, sku.varconds, sku.pricing_factors)
        assert calculator.price_resolved(resolved, price_date=DATE, currency="EUR").total == sku.price


def test_resolved_configuration_normalises_like_the_calculator():
    a = ResolvedConfiguration.of("X", ["b=1", "", "B=1", "a"], {"f": 2})
    assert a.varconds == ("B=1", "A") and a.pricing_factors == (("F", 2.0),)
    assert a.price_key == ResolvedConfiguration.of("X", ("B=1", "A"), (("F", 2),)).price_key
    assert a.price_key != ResolvedConfiguration.of("X", ("B=1",), (("F", 2),)).price_key


def test_no_matching_price_row_leaves_the_sku_unpriced_with_the_reason(tmp_path):
    only_a = "RES1;TYPE=A;S;B;;;100;1;EUR;20250101;99991231;1;"
    _, outcome = run(tmp_path, prices=only_a)
    by_final = {s.final_article: s for s in outcome.skus}
    assert by_final["RES1 A1"].price == Decimal("100.00")
    assert by_final["RES1 B1"].price is None and by_final["RES1 B1"].status == "unpriced"
    assert "TYPE=B" in by_final["RES1 B1"].message and "keyed by other variant conditions" in by_final["RES1 B1"].message
    assert [s.final_article for s in outcome.exportable] == ["RES1 A1", "RES1 A2"]


def test_a_missing_price_relation_assigns_no_key_and_is_not_guessed(tmp_path):
    _, outcome = run(tmp_path, prices="RES1;TYPE=A;S;B;;;100;1;EUR;20250101;99991231;1;", relation="")
    assert all(s.varconds == () and s.price is None for s in outcome.skus)
    assert "price relations assigned none of them" in outcome.skus[0].message


def test_final_articles_that_collide_with_different_price_conditions_are_reported(tmp_path):
    _, outcome = run(tmp_path, scheme=SCHEME_BASE_ONLY)
    assert [s.final_article for s in outcome.skus] == ["RES1"]
    assert outcome.duplicates == 3
    assert any("different price conditions" in w and "RES1" in w for w in outcome.warnings)
    assert sum("different price conditions" in w for w in outcome.warnings) == 1     # reported once per number


def test_colliding_final_articles_with_the_same_price_state_are_not_reported(tmp_path):
    _, outcome = run(tmp_path, scheme=SCHEME_BASE_ONLY, relation="$VARCOND = 'FIXED',",
                     prices="RES1;;S;B;;;100;1;EUR;20250101;99991231;1;")
    assert outcome.duplicates == 3 and not any("different price conditions" in w for w in outcome.warnings)


def test_an_article_that_is_not_in_the_repository_is_an_error_not_an_empty_result(tmp_path):
    generator = OcdArticleGenerator(build(tmp_path))
    with pytest.raises(GenerationError, match="not in"):
        generator.generate(["NOPE"], currency="EUR", price_date=DATE)


# ------------------------------------------------------------- real data: Betwixt LN10 (skipped when absent)
LN10_DB = Path(r"C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx\betwixt\ANY\1\db")
needs_ln10 = pytest.mark.skipif(not (LN10_DB / "ocd_article.csv").is_file(), reason="Betwixt OCD data not available")


def _rules(**fixed):
    from services.ocd_engine.generator import MODE_FIXED, PropertyRule
    keys = {"Frame": "FEATURES", "Seat": "FEATURES", "Back": "FEATURES", "Seating_Type": "FEATURES"}
    return [PropertyRule(f"{keys.get(n, 'FINISHES')}:{n}", MODE_FIXED, v) for n, v in fixed.items()]


@needs_ln10
@pytest.mark.parametrize("withdrawn", [
    {"Frame": "A", "Seat": "O"},          # Frame A: ``$ BAN NOT IN ('LN10', ...)`` (rel_obj 77 -> relation 84)
    {"Frame": "N", "Seat": "C"},          # Seat C:  ``$ BAN IN ('1')``             (rel_obj 76 -> relation 83)
])
def test_ln10_withdrawn_values_are_excluded_by_their_relation_objects(withdrawn):
    fixed = {"Seating_Type": "chair", "Frame_Finish": "BK", "Seat": "O", "Back": "O",
             "Seat_Finish": "WHN", "Back_Finish": "WHN", "Seat_Fabric_Type": "172", "Back_Fabric_Type": "172"}
    outcome = OcdArticleGenerator(LN10_DB).generate(
        ["LN10"], _rules(**{**fixed, **withdrawn}), currency="GBP", price_date="2026-11-02")
    assert outcome.skus == []


@needs_ln10
def test_ln10_colour_is_constrained_by_fabric_type_not_an_independent_dimension():
    generator = OcdArticleGenerator(LN10_DB)
    outcome = generator.generate(
        ["LN10"], _rules(Frame="N", Seat="U", Back="U", Seating_Type="stool_counter",
                         Seat_Fabric_Type="Z24", Back_Fabric_Type="ZMD", Frame_Finish="BK"),
        currency="GBP", price_date="2026-11-02", fabric_default_only=False)
    colours = {(dict((n, v) for _, n, v, _ in s.values)["Seat_Fabric_Colour"][:3],
                dict((n, v) for _, n, v, _ in s.values)["Back_Fabric_Colour"][:3]) for s in outcome.skus}
    assert colours == {("Z24", "ZMD")}
    assert len(outcome.skus) == 62 * 43      # 62 Z24 colours x 43 ZMD colours; not 448 x 448
    default_only = generator.generate(
        ["LN10"], _rules(Frame="N", Seat="U", Back="U", Seating_Type="stool_counter",
                         Seat_Fabric_Type="Z24", Back_Fabric_Type="ZMD", Frame_Finish="BK"),
        currency="GBP", price_date="2026-11-02")
    assert [s.final_article for s in default_only.skus] == ["LN10NUU BK Z2401 ZMD01"]   # first valid colour each


@needs_ln10
def test_ln10_is_unpriced_because_the_staging_data_has_no_price_relations_not_because_of_a_lookup_bug():
    generator = OcdArticleGenerator(LN10_DB)
    outcome = generator.generate(
        ["LN10"], _rules(Frame="N", Seat="O", Back="O", Seating_Type="chair", Frame_Finish="BK"),
        currency="GBP", price_date="2026-11-02")
    sku = outcome.skus[0]
    assert sku.final_article == "LN10NOO BK WHN WHN" and sku.varconds == ()
    assert sku.price is None and "price relations assigned none of them" in sku.message
    assert not any(r.get("var_cond") == "" and r.get("price_level") == "B"
                   for r in generator.dataset.tables["price"] if r["article_nr"] == "LN10")
