"""Keyword discovery (``fabric`` / ``upholstery``), Property-text labels and the one manual fabric property.

A synthetic repository range ``FO`` goes through the real loader, so Property-text rows reach ``PropertyDef.labels``.
Article FO1: class ``F`` with ``Cover`` A|B (the fabric type, no keyword in its *name*), ``Shade`` (colours A1 A2 A3 |
B1 B2 with preconditions on ``Cover``), ``Fabric_Care`` X|Y (a keyword hit that is neither type nor colour) and
``Grade`` G1|G2. Roles are never read from names: only relations, codes and texts decide them.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from services.ocd_engine import diagnostics as dg
from services.ocd_engine import fabric
from services.ocd_engine import fabric_resolver as fr
from services.ocd_engine.configuration_engine import ConfigurationEngine
from services.ocd_engine.generator import GenerationError, OcdArticleGenerator
from tests.ocd_engine.ocd_repo_fixture import TEXT_DESCRIPTOR, write

DATE = "2026-01-15"
SCHEME = 'U1;@,@,@,@, ,F:Cover,F:Shade,F:Fabric_Care,F:Grade;"";"";0;"-";"X";1;"";""'
COLOURS = [("A1", "Cover = 'A'"), ("A2", "Cover = 'A'"), ("A3", "Cover = 'A'"), ("B1", "Cover = 'B'"),
           ("B2", "Cover = 'B'")]


def texts(db: Path, table: str, entries: dict[str, dict[str, str]]) -> None:
    rows = [f'{number};{lang}; 1;\\;"{text}"' for number, by_lang in entries.items() for lang, text in by_lang.items()]
    write(db, f"{table}.csv", "\n".join(rows))
    (db / f"pdata.{table}.inp_descr").write_text(TEXT_DESCRIPTOR.format(table=table), encoding="latin-1")


def build(root: Path, *, labels: dict[str, dict[str, str]] | None = None, colour_texts=True,
          relations=True, colours=None) -> Path:
    db = root / "fo" / "ANY" / "1" / "db"
    db.mkdir(parents=True)
    write(db, "ocd_article.csv", "FO1;C;MK;DM;T1;;0;0;1;C62;U1")
    write(db, "ocd_propertyclass.csv", "FO1;1;F;10;0")
    # property rows: class;name;pos;prop_textnr;rel_obj;type;digits;dec;need;add;restr;multi;scope;txt_ctrl;hint
    names = [("Cover", "P1"), ("Shade", "P2"), ("Fabric_Care", "P3"), ("Grade", "P4")]
    write(db, "ocd_property.csv", "\n".join(f"F;{n};{i};{t};0;C;1;0;1;0;1;0;C;0;"
                                            for i, (n, t) in enumerate(names, 1)))
    values = ["F;Cover;1;V1;0;0;0;EQ;A;;;;;", "F;Cover;2;V2;0;0;0;EQ;B;;;;;",
              "F;Fabric_Care;1;;0;0;0;EQ;X;;;;;", "F;Fabric_Care;2;;0;0;0;EQ;Y;;;;;",
              "F;Grade;1;;0;0;0;EQ;G1;;;;;", "F;Grade;2;;0;0;0;EQ;G2;;;;;"]
    relobj, relation = [], []
    colours = colours or COLOURS
    for i, (colour, text) in enumerate(colours, 1):
        rel = i if relations else 0
        if relations:
            relobj.append(f"{i};1;{i:018d};1;C")
            relation.append(f'{i:018d}; 1;"{text}"')
        values.append(f"F;Shade;{i};C{i};{rel};0;0;EQ;{colour};;;;;")
    write(db, "ocd_propertyvalue.csv", "\n".join(values))
    write(db, "ocd_artbase.csv", "")
    write(db, "ocd_relationobj.csv", "\n".join(relobj))
    write(db, "ocd_relation.csv", "\n".join(relation))
    write(db, "ocd_codescheme.csv", SCHEME)
    write(db, "ocd_price.csv", "FO1;;S;B;;;100;1;EUR;20250101;99991231;1;")
    texts(db, "ocd_propertytext", labels if labels is not None else {
        "P1": {"en": "Upholstery type", "de": "Polsterart"}, "P2": {"en": "Shade", "de": "Farbton"},
        "P3": {"en": "Care", "de": "Pflege"}, "P4": {"en": "Grade", "de": "Stufe"}})
    if colour_texts:
        entries = {"V1": {"en": "Wool - A", "de": "Wolle - A"}, "V2": {"en": "Linen - B", "de": "Leinen - B"}}
        entries.update({f"C{i}": {"en": f"Tone - {c}", "de": f"Ton - {c}"} for i, (c, _) in enumerate(colours, 1)})
        texts(db, "ocd_propvaluetext", entries)
    return db


def generate(db, **kw):
    return OcdArticleGenerator(db).generate(["FO1"], currency="EUR", price_date=DATE, **kw)


def colours_of(outcome):
    return sorted({dict((n, v) for _, n, v, _ in s.values)["Shade"] for s in outcome.skus})


# ------------------------------------------------------------------ keyword discovery
def test_the_keyword_fabric_in_a_property_name_makes_a_candidate_without_a_full_phrase(tmp_path):
    model = OcdArticleGenerator(build(tmp_path))._build_model("FO1")
    names = [p.name for p in fabric.fabric_candidates(model)]
    assert "Fabric_Care" in names                            # "Fabric" alone is enough; no "Type"/"Colour" needed


def test_the_keyword_upholstery_is_found_in_the_property_text(tmp_path):
    model = OcdArticleGenerator(build(tmp_path))._build_model("FO1")
    cover = next(p for p in model.properties if p.name == "Cover")
    assert dict(cover.labels) == {"en": "Upholstery type", "de": "Polsterart"}
    assert "Cover" in [p.name for p in fabric.fabric_candidates(model)]     # name has no keyword, the text does


def test_any_language_of_the_property_text_is_searched(tmp_path):
    labels = {"P1": {"en": "Cover", "de": "Fabric type"}, "P2": {"en": "Shade"}, "P3": {"en": "Care"},
              "P4": {"en": "Grade"}}
    model = OcdArticleGenerator(build(tmp_path, labels=labels))._build_model("FO1")
    assert [p.name for p in fabric.fabric_candidates(model) if p.name != "Fabric_Care"] == ["Cover"]


def test_missing_property_text_is_tolerated(tmp_path):
    model = OcdArticleGenerator(build(tmp_path, labels={}))._build_model("FO1")
    assert all(p.labels == () for p in model.properties)
    assert [p.name for p in fabric.fabric_candidates(model)] == ["Fabric_Care"]


def test_a_keyword_property_that_is_neither_type_nor_colour_is_not_reduced(tmp_path):
    outcome = generate(build(tmp_path))
    care = {dict((n, v) for _, n, v, _ in s.values)["Fabric_Care"] for s in outcome.skus}
    assert care == {"X", "Y"}                                # both values stay: the keyword is discovery only
    model = OcdArticleGenerator(build(tmp_path / "again"))._build_model("FO1")
    assert all(s.colour_property != "Fabric_Care" and s.type_property != "Fabric_Care"
               for s in fabric.discover_schemes(model))


def test_automatic_discovery_reduces_through_the_label_keyword_with_the_real_loader(tmp_path):
    outcome = generate(build(tmp_path))
    assert colours_of(outcome) == ["A1", "B1"] and len(outcome.skus) == 2 * 2 * 2     # types x care x grade, 1 colour


# ------------------------------------------------------------------ the one manual property
NO_KEYWORDS = {"P1": {"en": "Cover"}, "P2": {"en": "Shade"}, "P3": {"en": "Care"}, "P4": {"en": "Grade"}}


@pytest.fixture
def plain(tmp_path):
    """Same structure, but no keyword anywhere (``Fabric_Care`` renamed away is not needed: it is not a pair)."""
    return build(tmp_path, labels=NO_KEYWORDS)


def test_without_a_keyword_the_structure_is_reported_and_every_colour_stays(plain):
    model = OcdArticleGenerator(plain)._build_model("FO1")
    found = fabric.discover(model)
    assert found.schemes == () and [(s.type_property, s.colour_property) for s in found.unconfirmed] == [
        ("Cover", "Shade")]
    outcome = generate(plain)
    assert colours_of(outcome) == ["A1", "A2", "A3", "B1", "B2"] and len(outcome.skus) == 5 * 2 * 2


@pytest.mark.parametrize("choice", ["Shade", "Cover", "shade"])
def test_selecting_one_property_makes_the_resolver_read_the_pair_from_the_data(plain, choice):
    """Either side of the pair works: the roles come from relations and values, never from which one was chosen."""
    outcome = generate(plain, fabric_property=choice)
    assert colours_of(outcome) == ["A1", "B1"] and len(outcome.skus) == 8


def test_resetting_to_automatic_restores_the_automatic_result(plain):
    chosen = generate(plain, fabric_property="Shade")
    reset = generate(plain, fabric_property="")
    assert len(chosen.skus) == 8 and len(reset.skus) == 20 and colours_of(reset) == ["A1", "A2", "A3", "B1", "B2"]


def test_selecting_an_already_detected_property_changes_nothing(tmp_path):
    db = build(tmp_path)
    auto = generate(db)
    for choice in ("Shade", "Cover"):
        again = generate(db, fabric_property=choice)
        assert [s.final_article for s in again.skus] == [s.final_article for s in auto.skus]


def test_a_selection_without_any_type_colour_relationship_is_a_clear_error_not_an_enumeration(plain):
    with pytest.raises(GenerationError, match="Grade.*no fabric type/colour relationship"):
        generate(plain, fabric_property="Grade")
    engine = ConfigurationEngine(OcdArticleGenerator(plain)._build_model("FO1"), fabric_property="Grade")
    with pytest.raises(fr.FabricOverrideError):
        list(engine.enumerate())
    assert engine.sink.by_code(dg.FABRIC_OVERRIDE_UNRESOLVED)


def test_the_selection_does_not_bypass_relation_validation(tmp_path):
    """A colour whose relation is FALSE is rejected under the override exactly as in automatic mode."""
    colours = [("A1", "Cover = 'A' AND Grade = 'G2'"), ("A2", "Cover = 'A'"), ("A3", "Cover = 'A'"),
               ("B1", "Cover = 'B'"), ("B2", "Cover = 'B'")]
    db = build(tmp_path, labels=NO_KEYWORDS, colours=colours)
    picked = {}
    for sku in generate(db, fabric_property="Shade").skus:
        v = {n: val for _, n, val, _ in sku.values}
        picked[(v["Cover"], v["Grade"])] = v["Shade"]
    assert picked[("A", "G1")] == "A2" and picked[("A", "G2")] == "A1"      # first *valid* colour per Grade
    assert len(set(picked.values())) == 3                                  # never the full set of five


def test_a_value_without_relations_cannot_be_forced_into_a_fabric_by_the_selection(tmp_path):
    db = build(tmp_path, labels=NO_KEYWORDS, relations=False, colour_texts=False)
    with pytest.raises(GenerationError, match="Shade.*no fabric type/colour relationship"):
        generate(db, fabric_property="Shade")


def test_the_value_text_fallback_works_under_the_override(tmp_path):
    db = build(tmp_path, labels=NO_KEYWORDS, relations=False)         # no relations; codes A1.. extend A/B; texts "- A1"
    model = OcdArticleGenerator(db)._build_model("FO1")
    found = fabric.discover(model, "Shade")
    assert [(s.type_property, s.colour_property, s.mechanism) for s in found.schemes] == [
        ("Cover", "Shade", fabric.MECH_PREFIX_TEXT)]
    outcome = generate(db, fabric_property="Shade")
    assert colours_of(outcome) == ["A1", "B1"]


def test_an_article_without_the_selected_property_falls_back_to_automatic_with_a_warning(tmp_path):
    db = build(tmp_path)
    outcome = generate(db, fabric_property="Not_There")
    assert colours_of(outcome) == ["A1", "B1"]
    assert any("Not_There" in w and "automatic" in w for w in outcome.warnings)


def test_fabric_notes_name_the_type_mechanism_candidates_and_choice(tmp_path):
    outcome = generate(build(tmp_path))
    assert any("Shade for Cover='A'" in n and "relation" in n and "A1 (first-valid)" in n for n in outcome.fabric_notes)


# ------------------------------------------------------------------ ambiguity
def test_a_colour_that_fits_two_types_equally_is_ambiguous_and_the_selection_is_refused(tmp_path):
    db = build(tmp_path, labels=NO_KEYWORDS)
    model = OcdArticleGenerator(db)._build_model("FO1")
    import dataclasses
    from services.ocd_engine import model as m
    twin = dataclasses.replace(next(p for p in model.properties if p.name == "Cover"), key="F:Cover2", name="Cover2")
    mdl = dataclasses.replace(model, properties=model.properties + (twin,))
    # Cover2 has the same values as Cover, and Shade's relations read "Cover" only -> Cover is strictly better
    assert fabric.discover(mdl, "Shade").override_error == ""
    tied = []
    for p in mdl.properties:
        if p.name == "Shade":
            shade = dataclasses.replace(p, values=tuple(
                dataclasses.replace(v, relations=tuple(
                    m.RelationRef(name=f"{r.name}x", rel_type=r.rel_type, domain=r.domain, order=r.order,
                                  text=r.text + " AND " + r.text.replace("Cover", "Cover2"))
                    for r in v.relations)) for v in p.values))
            tied.append(shade)
        else:
            tied.append(p)
    ambiguous = dataclasses.replace(mdl, properties=tuple(tied))
    found = fabric.discover(ambiguous, "Shade")
    assert "several fabric types" in found.override_error
