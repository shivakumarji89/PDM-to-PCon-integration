"""ArtBase candidate values and the enumeration of properties that cannot change a SKU.

ArtBase semantics checked against the real repositories (80+ ranges): ``ocd_artbase`` lists, per base article,
the properties it restricts, each with its permitted values - it lists a *minority* of an article's properties
(LN10: 1 of 13; Dalby: 26 of 208). A property that ArtBase lists is offered with exactly its ArtBase values; a
property it does not list is offered with every value of ``ocd_propertyvalue``. Applying "only ArtBase values"
to unlisted properties would leave LN10, Dalby and Lino without any value.

Synthetic range ``AB``: class ``K`` shared by articles AB1 and AB2 with Colour R|G|B|Y, Size S|L and a
read-only Grp (scope RG) of three values.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from services.ocd_engine.configuration_engine import ConfigurationEngine
from services.ocd_engine.generator import MODE_FIXED, OcdArticleGenerator, PropertyRule
from tests.ocd_engine.ocd_repo_fixture import write

DATE = "2026-01-15"
SCHEME_COLOUR_SIZE = 'U1;@,@,@,@, ,K:Colour, ,K:Size;"";"";0;"-";"X";1;"";""'
PRICE = "{a};;S;B;;;100;1;EUR;20250101;99991231;1;"


def build(root: Path, *, artbase="", scheme=SCHEME_COLOUR_SIZE, relations="", relobj="", colours="RGBY",
          grp_scope="RG", price_extra="", articles=("AB1",), colour_relobj=None, colour_prop_relobj=0, article_relobj=0, grp_first=False) -> Path:
    db = root / "ab" / "ANY" / "1" / "db"
    db.mkdir(parents=True)
    write(db, "ocd_article.csv", "\n".join(f"{a};C;MK;DM;T1;;{article_relobj};0;1;C62;U1" for a in articles))
    write(db, "ocd_propertyclass.csv", "\n".join(f"{a};1;K;10;0" for a in articles))
    write(db, "ocd_property.csv",
          f"K;Colour;1;;{colour_prop_relobj};C;1;0;1;0;1;0;C;0;\nK;Size;2;;0;C;1;0;1;0;0;0;C;0;\n"
          f"K;Grp;{0 if grp_first else 3};;0;C;1;0;1;0;0;0;{grp_scope};0;")
    rows = []
    for i, c in enumerate(colours, 1):
        rows.append(f"K;Colour;{i};;{(colour_relobj or {}).get(c, 0)};0;0;EQ;{c};;;;;")
    rows += ["K;Size;1;;0;0;0;EQ;S;;;;;", "K;Size;2;;0;0;0;EQ;L;;;;;"]
    rows += [f"K;Grp;{i};;0;0;0;EQ;G{i};;;;;" for i in (1, 2, 3)]
    write(db, "ocd_propertyvalue.csv", "\n".join(rows))
    write(db, "ocd_artbase.csv", artbase)
    write(db, "ocd_relationobj.csv", relobj)
    write(db, "ocd_relation.csv", relations)
    write(db, "ocd_codescheme.csv", scheme)
    write(db, "ocd_price.csv", "\n".join(PRICE.format(a=a) for a in articles) + price_extra)
    return db


def run(db, articles=("AB1",)):
    return OcdArticleGenerator(db).generate(list(articles), currency="EUR", price_date=DATE)


def finals(outcome):
    return [s.final_article for s in outcome.skus]


def colours_of(outcome):
    return {s.final_article.split()[1] for s in outcome.skus}


# ------------------------------------------------------------------------------ ArtBase
def test_a_listed_property_is_offered_with_exactly_its_artbase_values(tmp_path):
    outcome = run(build(tmp_path, artbase="AB1;K;Colour;R\nAB1;K;Colour;G"))   # B and Y exist globally
    assert colours_of(outcome) == {"R", "G"} and len(outcome.skus) == 2 * 2


def test_values_do_not_leak_between_bases_sharing_a_class(tmp_path):
    db = build(tmp_path, articles=("AB1", "AB2"), artbase="AB1;K;Colour;R\nAB2;K;Colour;B\nAB2;K;Colour;Y")
    generator = OcdArticleGenerator(db)
    assert colours_of(generator.generate(["AB1"], currency="EUR", price_date=DATE)) == {"R"}
    assert colours_of(generator.generate(["AB2"], currency="EUR", price_date=DATE)) == {"B", "Y"}


def test_an_unlisted_property_keeps_every_value_of_the_repository(tmp_path):
    outcome = run(build(tmp_path, artbase="AB1;K;Colour;R"))
    assert {s.final_article.split()[-1] for s in outcome.skus} == {"S", "L"}   # Size is not in ArtBase


def test_an_artbase_value_without_a_propertyvalue_row_is_still_offered(tmp_path):
    assert colours_of(run(build(tmp_path, artbase="AB1;K;Colour;R\nAB1;K;Colour;Z"))) == {"R", "Z"}


def test_a_relation_can_invalidate_an_artbase_value_but_cannot_add_one(tmp_path):
    db = build(tmp_path, artbase="AB1;K;Colour;R\nAB1;K;Colour;G", colour_relobj={"R": 100, "B": 101},
               relobj="100;1;000000000000000001;1;C\n101;1;000000000000000002;1;C",
               relations='000000000000000001; 1;"Size = \'S\'"\n000000000000000002; 1;"Size = \'S\'"')
    # R is offered only with Size S (its precondition); B satisfies its own precondition but is not in ArtBase.
    assert sorted(finals(run(db))) == sorted(["AB1 R S", "AB1 G S", "AB1 G L"])


def test_artbase_does_not_change_how_a_valid_sku_is_encoded(tmp_path):
    restricted = run(build(tmp_path, artbase="AB1;K;Colour;R\nAB1;K;Colour;G"))
    other = tmp_path / "second"
    other.mkdir()
    unrestricted = run(build(other))
    assert len(restricted.skus) == 4 and set(finals(restricted)) <= set(finals(unrestricted))


# ---------------------------------------------------------------- enumeration of inert properties
def test_a_read_only_property_nothing_reads_is_not_enumerated_independently(tmp_path):
    outcome = run(build(tmp_path))
    assert len(outcome.skus) == 8 and outcome.configurations == 8             # 4 colours x 2 sizes, Grp not x3
    assert outcome.duplicates == 0 and outcome.inert_properties == ("Grp",)
    assert all("Grp=G1" in s.configuration_text for s in outcome.skus)         # the first offered value is kept


def test_collapsing_gives_the_same_skus_as_the_full_enumeration(tmp_path, monkeypatch):
    db = build(tmp_path)
    collapsed = run(db)
    monkeypatch.setattr(ConfigurationEngine, "inert_properties", staticmethod(lambda model, texts: frozenset()))
    full = run(db)
    assert full.configurations == 24 and full.duplicates == 16               # what the engine used to do

    def key(outcome):
        return [(s.final_article, s.ofml_varcode, s.configuration_text, s.price) for s in outcome.skus]

    assert key(collapsed) == key(full)


def test_a_read_only_property_the_code_scheme_uses_is_still_enumerated(tmp_path):
    scheme = 'U1;@,@,@,@, ,K:Colour, ,K:Grp;"";"";0;"-";"X";1;"";""'
    outcome = run(build(tmp_path, scheme=scheme, colours="RG"))
    assert len(outcome.skus) == 2 * 3 and outcome.inert_properties == ()       # Colour x Grp (Size is not coded)


def test_a_read_only_property_a_precondition_reads_is_still_enumerated(tmp_path):
    db = build(tmp_path, colours="RG", colour_relobj={"G": 100}, relobj="100;1;000000000000000001;1;C",
               relations='000000000000000001; 1;"Grp = \'G2\'"')
    outcome = run(db)
    assert outcome.inert_properties == ()
    assert colours_of(outcome) == {"R", "G"}                                    # G exists only where Grp = G2
    assert all("Grp=G2" in s.configuration_text for s in outcome.skus if s.final_article.split()[1] == "G")


def test_a_read_only_property_a_price_relation_reads_is_not_collapsed(tmp_path):
    db = build(tmp_path, colours="R", article_relobj=900, relobj="900;1;000000000000000001;3;P",
               relations='000000000000000001; 1;"$VARCOND = \'GRP=\' + Grp,"',
               price_extra="\nAB1;GRP=G1;S;X;;;5;1;EUR;20250101;99991231;1;")
    outcome = run(db)
    assert outcome.inert_properties == () and outcome.configurations == 6      # 2 sizes x 3 Grp values
    assert len(outcome.skus) == 2 and {str(s.price) for s in outcome.skus} == {"105.00"}   # first Grp (G1) kept


def test_a_configurable_property_is_never_collapsed_even_when_the_code_ignores_it(tmp_path):
    outcome = run(build(tmp_path, grp_scope="C"))
    assert outcome.inert_properties == () and outcome.duplicates == 16         # deduplicated by final article, as before


def test_a_reaction_is_a_default_not_a_constraint(tmp_path):
    db = build(tmp_path, colours="RG", colour_prop_relobj=200, relobj="200;1;000000000000000001;5;C",
               relations='000000000000000001; 1;"Size = \'L\' IF Colour = \'R\'"')
    assert sorted(finals(run(db))) == sorted(["AB1 R S", "AB1 R L", "AB1 G S", "AB1 G L"])   # R+S stays valid


def test_the_collapse_needs_the_identity_texts_and_reads_them(tmp_path):
    model = OcdArticleGenerator(build(tmp_path))._build_model("AB1")
    assert ConfigurationEngine(model).stats.inert == ()
    assert ConfigurationEngine.inert_properties(model, [SCHEME_COLOUR_SIZE]) == frozenset({"GRP"})
    assert ConfigurationEngine.inert_properties(model, ["K:Grp"]) == frozenset()


# ------------------------------------------------- value preconditions: type before colour, evaluated once
def typed_colours(tmp_path, **kw):
    """Colours R,G need Size S; B,Y need Size L (the Size plays the part of LN10's fabric type)."""
    return build(tmp_path, colour_relobj={"R": 100, "G": 100, "B": 101, "Y": 101},
                 relobj="100;1;000000000000000001;1;C\n101;1;000000000000000002;1;C",
                 relations='000000000000000001; 1;"Size = \'S\'"\n000000000000000002; 1;"Size = \'L\'"', **kw)


def test_a_colour_is_only_expanded_under_the_type_its_precondition_requires(tmp_path):
    outcome = run(typed_colours(tmp_path))
    assert sorted(finals(outcome)) == sorted(["AB1 R S", "AB1 G S", "AB1 B L", "AB1 Y L"])
    assert outcome.configurations == 4 and outcome.invalid == 0            # no R+L / B+S is built then rejected


def test_the_colour_filter_runs_once_per_state_of_the_properties_it_reads(tmp_path, monkeypatch):
    calls = []
    real = ConfigurationEngine._filter_values

    def spy(self, dim, ctx):
        calls.append((dim.name, ctx.values.get("SIZE")))
        return real(self, dim, ctx)

    monkeypatch.setattr(ConfigurationEngine, "_filter_values", spy)
    outcome = run(typed_colours(tmp_path, grp_scope="C", grp_first=True))       # 3 Grp values precede Colour
    assert outcome.configurations == 4 * 3
    assert sorted(c for c in calls if c[0] == "Colour") == [("Colour", "L"), ("Colour", "S")]


def test_the_cached_filter_never_serves_a_list_computed_for_another_type(tmp_path):
    db = typed_colours(tmp_path, grp_scope="C", grp_first=True)
    engine = ConfigurationEngine(OcdArticleGenerator(db)._build_model("AB1"))
    by_type = {}
    for config in engine.enumerate():
        a = {x.prop.name: x.value.value for x in config.assignments if x.value is not None}
        by_type.setdefault(a["Size"], set()).add(a["Colour"])
    assert by_type == {"S": {"R", "G"}, "L": {"B", "Y"}}


# --------------------------------------------------------------------- real data: Betwixt LN10
LN10_DB = Path(r"C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx\betwixt\ANY\1\db")
needs_ln10 = pytest.mark.skipif(not (LN10_DB / "ocd_article.csv").is_file(), reason="Betwixt OCD data not available")


@needs_ln10
def test_ln10_only_seating_type_is_inert():
    generator = OcdArticleGenerator(LN10_DB)
    model = generator._build_model("LN10")
    scheme = generator.dataset.code_scheme(model.scheme_id)
    assert ConfigurationEngine.inert_properties(model, [scheme.scheme]) == frozenset({"SEATING_TYPE"})
    by_name = {p.name: p for p in model.properties}
    assert by_name["Seating_Type"].scope == "RG" and len(by_name["Seating_Type"].values) == 4
    assert by_name["Seat_Fabric_Colour"].scope == "C"                           # colours are never collapsed


@needs_ln10
def test_ln10_subset_is_identical_with_and_without_the_collapse(monkeypatch):
    fixed = dict(Frame="N", Seat="O", Back="U", Frame_Finish="BK", Back_Fabric_Type="Z24")
    keys = {"Frame": "FEATURES", "Seat": "FEATURES", "Back": "FEATURES"}
    rules = [PropertyRule(f"{keys.get(n, 'FINISHES')}:{n}", MODE_FIXED, v) for n, v in fixed.items()]
    full = dict(currency="GBP", price_date="2026-11-02", fabric_default_only=False)   # every valid colour
    after = OcdArticleGenerator(LN10_DB).generate(["LN10"], rules, **full)
    monkeypatch.setattr(ConfigurationEngine, "inert_properties", staticmethod(lambda model, texts: frozenset()))
    before = OcdArticleGenerator(LN10_DB).generate(["LN10"], rules, **full)

    def key(outcome):
        return [(s.final_article, s.ofml_varcode, s.configuration_text) for s in outcome.skus]

    assert len(after.skus) == 62 and key(after) == key(before)
    assert before.configurations == 4 * after.configurations and before.duplicates == 3 * len(before.skus)
    assert after.duplicates == 0 and after.inert_properties == ("Seating_Type",)
    monkeypatch.undo()
    default_only = OcdArticleGenerator(LN10_DB).generate(["LN10"], rules, currency="GBP", price_date="2026-11-02")
    assert len(default_only.skus) == 1 and default_only.skus[0].final_article in {s.final_article for s in after.skus}


@needs_ln10
def test_ln10_artbase_assigns_no_colour_so_the_colours_come_from_the_class_values():
    generator = OcdArticleGenerator(LN10_DB)
    assert generator.dataset.artbase["LN10"] == [
        {"article_nr": "LN10", "prop_class": "PLC", "property": "PLC", "prop_value": "LN"}]
    model = generator._build_model("LN10")
    colour = {p.name: p for p in model.properties}["Seat_Fabric_Colour"]
    assert colour.allowed_keys is None and len(colour.values) == 448          # unrestricted: class-global list


@needs_ln10
def test_ln10_z2401_is_a_candidate_only_under_fabric_type_z24():
    from services.ocd_engine.relation_evaluator import EvalContext
    model = OcdArticleGenerator(LN10_DB)._build_model("LN10")
    props = {p.name: p for p in model.properties}
    z2401 = next(v for v in props["Seat_Fabric_Colour"].values if v.value == "Z2401")
    assert [(r.name, r.rel_type, r.text) for r in z2401.relations] == [("36/42", 1, "Seat_Fabric_Type = 'Z24'")]
    engine = ConfigurationEngine(model, fabric_default_only=False)      # the relation-valid candidates
    engine._prepare([p for p in model.properties if p.values])

    def candidates(fabric):
        ctx = EvalContext(values={"SEAT": "U", "SEAT_FABRIC_TYPE": fabric}, ban="LN10", tables=model.tables)
        return [v.value for v in engine._candidates(props["Seat_Fabric_Colour"], ctx)]

    z24, zmd = candidates("Z24"), candidates("ZMD")
    assert len(z24) == 62 and "Z2401" in z24 and len(zmd) == 43 and "Z2401" not in zmd
    assert not set(z24) & set(zmd) and all(c.startswith("Z24") for c in z24)
    seat_types = [v.value for v in engine._candidates(props["Seat_Fabric_Type"], EvalContext(
        values={"SEAT": "U"}, ban="LN10", tables=model.tables))]
    assert len(seat_types) == 10 and "VZ" not in seat_types                    # 7 types withdrawn by $BAN IN ('1')
