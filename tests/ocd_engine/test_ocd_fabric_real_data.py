"""Fabric colours of the real Lino, Tun and Bay Work Pod OCD data (skipped when the repository is absent).

Each series is read from ``<root>/<range>/ANY/1/db``. The expectations are *derived from the raw tables* by an
oracle that uses only the CSV rows and plain regular expressions (not ``fabric.py`` / the resolver): per type value
the colours its relation names, in ``pos_pval`` order, minus the types a ``$ BAN IN (...)`` precondition withdraws for
the article. The generator is then run with every other property pinned to the values of the first valid
configuration (the three series have far too many combinations of unrelated finishes to enumerate), once with the
default rule and once with ``fabric_default_only=False`` (every valid colour).

Findings the numbers rest on (see docs/04_Reference/pCon/Article_OBX_Generator/FABRIC_COLOUR_RESOLVER.md):

* Lino   - colour values carry ``Seat_Fabric_Type = '<type>'``; some values/types carry ``$ BAN IN ('1')`` (withdrawn).
* Tun    - the type property is ``Upholstered_Base_Fabric`` (no "Type" in its name); colour values carry
           ``(SPECIFIED T) AND (T IN ('<type>'))`` or ``T = '<type>'``; the *type* value ``1HA`` is flagged default.
* Bay    - one type (``1HS``), eight colours with ``(SPECIFIED T) AND (T IN ('1HS'))``, colour ``1HS10`` flagged default.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

import pytest

from services.ocd_engine import diagnostics as dg
from services.ocd_engine import fabric
from services.ocd_engine import fabric_resolver as fr
from services.ocd_engine.configuration_engine import ConfigurationEngine
from services.ocd_engine.generator import MODE_FIXED, OcdArticleGenerator, PropertyRule
from tests.ocd_engine.ocd_helpers import REAL_OCD_ROOT

DATE = "2026-11-04"


def db(range_name: str) -> Path:
    return Path(REAL_OCD_ROOT) / range_name / "ANY" / "1" / "db"


def needs(range_name: str):
    return pytest.mark.skipif(not (db(range_name) / "ocd_article.csv").is_file(),
                              reason=f"{range_name} OCD data not available")


# ------------------------------------------------------------------ oracle from the raw tables
def relation_texts(dataset, rel_obj: str) -> list[str]:
    if rel_obj.strip() in ("", "0"):
        return []
    return [dataset.relation_text(r["rel_name"]) or "" for r in dataset.relobjs.get(str(int(rel_obj)), [])]


def oracle(generator: OcdArticleGenerator, article: str, class_name: str, type_prop: str, colour_prop: str):
    """``({type: [colours in pos_pval order]}, [valid type values in order], flagged colours)`` from the raw rows."""
    ds = generator.dataset
    by_type: dict[str, list[str]] = defaultdict(list)
    flagged: list[str] = []
    for row in sorted(ds.values[(class_name, colour_prop)], key=lambda r: int(r["pos_pval"])):
        if row["is_default"].strip() == "1":
            flagged.append(row["value_from"])
        for text in relation_texts(ds, row["rel_obj"]):
            if "BAN" in text.upper():
                continue                                            # withdrawn for some articles, names no type
            if re.search(rf"\b{type_prop}\b", text):
                for literal in re.findall(r"'([^']+)'", text):
                    by_type[literal].append(row["value_from"])
    valid = []
    for row in sorted(ds.values[(class_name, type_prop)], key=lambda r: int(r["pos_pval"])):
        withdrawn = False
        for text in relation_texts(ds, row["rel_obj"]):
            ban = re.search(r"BAN\s+IN\s*\(([^)]*)\)", text)
            if ban and article not in re.findall(r"'([^']*)'", ban.group(1)):
                withdrawn = True
        if not withdrawn:
            valid.append(row["value_from"])
    return by_type, valid, flagged


def pinned_rules(generator: OcdArticleGenerator, article: str, vary: set[str]):
    """Pin every configurable property but ``vary`` to its value in the first valid configuration."""
    engine = ConfigurationEngine(generator._build_model(article))
    for config in engine.enumerate():
        if engine.finalize(config.assignments).valid:
            return [PropertyRule(a.prop.key, MODE_FIXED, a.value.value) for a in config.assignments
                    if a.value is not None and not a.hidden and a.prop.scope.upper() == "C"
                    and a.prop.name_upper not in vary]
    raise AssertionError("no valid configuration")


def colours_by_type(outcome, type_prop, colour_prop):
    found = defaultdict(set)
    for sku in outcome.skus:
        values = {name: value for _, name, value, _ in sku.values}
        found[values[type_prop]].add(values[colour_prop])
    return found


def run_series(range_name, article, class_name, type_prop, colour_prop):
    generator = OcdArticleGenerator(db(range_name))
    rules = pinned_rules(generator, article, {type_prop.upper(), colour_prop.upper()})
    kw = dict(currency=generator.currencies()[0], price_date=DATE)
    reduced = generator.generate([article], rules, **kw)
    full = generator.generate([article], rules, fabric_default_only=False, **kw)
    return generator, reduced, full, *oracle(generator, article, class_name, type_prop, colour_prop)


def check_against_oracle(reduced, full, by_type, valid, flagged, type_prop, colour_prop):
    expected = {t: cols for t, cols in by_type.items() if t in valid and cols}
    got_full = colours_by_type(full, type_prop, colour_prop)
    got_one = colours_by_type(reduced, type_prop, colour_prop)
    assert {t: sorted(c) for t, c in got_full.items()} == {t: sorted(c) for t, c in expected.items()}
    assert len(full.skus) == sum(len(c) for c in expected.values())                  # the full set, from the tables
    assert set(got_one) == set(expected) and all(len(c) == 1 for c in got_one.values())
    for type_value, cols in expected.items():                                        # explicit default, else first
        pick = next((c for c in cols if c in flagged), cols[0])
        assert got_one[type_value] == {pick}, type_value
    assert len(reduced.skus) == len(expected) < len(full.skus) or len(full.skus) == len(reduced.skus) == 1
    assert {s.final_article for s in reduced.skus} <= {s.final_article for s in full.skus}
    assert reduced.invalid == 0 and reduced.duplicates == 0 and not reduced.truncated


# ------------------------------------------------------------------ Lino
LINO = ("MI1E3", "MI2E3", "MI7E3")


@needs("lino")
@pytest.mark.parametrize("article", LINO)
def test_lino_one_colour_per_valid_type_from_the_type_relations(article):
    generator, reduced, full, by_type, valid, flagged = run_series(
        "lino", article, "LINO_OPT", "Seat_Fabric_Type", "Fabric_Colour")
    assert flagged == []                                                             # no flagged colour in Lino
    check_against_oracle(reduced, full, by_type, valid, flagged, "Seat_Fabric_Type", "Fabric_Colour")
    types_with_colours = {t for t in valid if by_type.get(t)}
    assert 0 < len(types_with_colours) < len(valid) or len(valid) == len(types_with_colours)
    (scheme,) = fabric.discover_schemes(generator._build_model(article))
    assert (scheme.type_property, scheme.colour_property, scheme.mechanism) == (
        "Seat_Fabric_Type", "Fabric_Colour", fabric.MECH_RELATION)


@needs("lino")
def test_lino_selected_colour_is_the_first_in_source_order_and_explained():
    generator = OcdArticleGenerator(db("lino"))
    engine = ConfigurationEngine(generator._build_model("MI1E3"))
    for _ in engine.generate():
        pass
    by_type, valid, _ = oracle(generator, "MI1E3", "LINO_OPT", "Seat_Fabric_Type", "Fabric_Colour")
    resolutions = {r.type_value: r for r in engine.fabric_resolutions.values() if r.selected}
    assert resolutions and all(r.selection == fr.SELECTED_FIRST for r in resolutions.values())
    for type_value, resolution in resolutions.items():
        assert resolution.selected == by_type[type_value][0]
        assert resolution.mechanism == fabric.MECH_RELATION and resolution.candidates and resolution.valid


# ------------------------------------------------------------------ Tun
TUN = ("NOTUN420", "NOTUN620", "NOTUN920")


@needs("tun")
@pytest.mark.parametrize("article", TUN)
def test_tun_type_without_the_word_type_is_reduced_to_one_colour_per_type(article):
    generator, reduced, full, by_type, valid, flagged = run_series(
        "tun", article, "TUN_OPT", "Upholstered_Base_Fabric", "Upholstered_Base_Fabric_Colour")
    assert flagged == []                                      # the flagged default is a *type* (1HA), not a colour
    check_against_oracle(reduced, full, by_type, valid, flagged,
                         "Upholstered_Base_Fabric", "Upholstered_Base_Fabric_Colour")
    assert len(full.skus) > 10 * len(reduced.skus)                                   # the old all-colour expansion
    (scheme,) = fabric.discover_schemes(generator._build_model(article))
    assert scheme.type_property == "Upholstered_Base_Fabric" and scheme.mechanism == fabric.MECH_RELATION
    assert not re.search("type", scheme.type_property, re.IGNORECASE)               # a name rule cannot see it


@needs("tun")
def test_tun_a_property_precondition_hides_the_colour_before_any_colour_is_chosen():
    generator = OcdArticleGenerator(db("tun"))
    model = generator._build_model("NOTUN420")
    colour = next(p for p in model.properties if p.name == "Upholstered_Base_Fabric_Colour")
    assert any("Base_Material" in r.text for r in colour.relations)                  # (SPECIFIED B) AND (B NOT IN ('ST'))


# ------------------------------------------------------------------ Bay Work Pod
BAY = ("PEP100", "PEP200")


@needs("bay_work_pod")
@pytest.mark.parametrize("article", BAY)
def test_bay_work_pod_uses_the_flagged_default_colour(article):
    generator, reduced, full, by_type, valid, flagged = run_series(
        "bay_work_pod", article, "BAY_POD_OPT", "Exterior_Fabric_Type", "Exterior_Fabric_Colour")
    assert flagged == ["1HS10"] and valid == ["1HS"] and len(by_type["1HS"]) == 8
    check_against_oracle(reduced, full, by_type, valid, flagged, "Exterior_Fabric_Type", "Exterior_Fabric_Colour")
    assert len(full.skus) == 8 and len(reduced.skus) == 1
    engine = ConfigurationEngine(generator._build_model(article))
    list(engine.enumerate())
    (resolution,) = [r for r in engine.fabric_resolutions.values() if r.selected]
    assert (resolution.selected, resolution.selection) == ("1HS10", fr.SELECTED_EXPLICIT)
    assert resolution.valid[0] == "1HS01"                                            # first valid is *not* chosen


# ------------------------------------------------------------------ the value-text fallback in real data
@needs("comma")
def test_comma_has_no_colour_relations_and_uses_the_code_and_text_fallback():
    generator = OcdArticleGenerator(db("comma"))
    model = generator._build_model("WA10")
    (scheme,) = fabric.discover_schemes(model)
    assert scheme.mechanism == fabric.MECH_PREFIX_TEXT and scheme.evidence.text_confirmed >= 0.9
    colour = next(p for p in model.properties if p.name == scheme.colour_property)
    assert not any(v.relations for v in colour.values)                              # no relation to rely on
    kw = dict(currency=generator.currencies()[0], price_date=DATE)
    reduced, full = generator.generate(["WA10"], **kw), generator.generate(["WA10"], fabric_default_only=False, **kw)
    assert 0 < len(reduced.skus) < len(full.skus)
    first = next(v.value for v in colour.values)
    used = {dict((n, v) for _, n, v, _ in s.values).get(scheme.colour_property) for s in reduced.skus}
    assert used - {None} == {first}                       # one type, so one colour; None = colour hidden by the data


@needs("always")
def test_always_has_two_parallel_fabric_sets_the_data_cannot_tell_apart_so_none_is_paired():
    """Chair_ and Seat_Pad_ fabric colours share one code space and identical type lists, no colour relations: which
    colour property follows which type is not in the data. It used to be settled by taking the first type (which
    paired Seat_Pad_Fabric_Colour with Chair_Fabric_Type); now both are reported and left unreduced."""
    generator = OcdArticleGenerator(db("always"))
    model = generator._build_model("NOALE1")
    found = fabric.discover(model)
    assert found.schemes == ()
    assert {c: set(t) for c, t in found.ambiguous} == {
        "Chair_Fabric_Colour": {"Chair_Fabric_Type", "Seat_Pad_Fabric_Type"},
        "Seat_Pad_Fabric_Colour": {"Chair_Fabric_Type", "Seat_Pad_Fabric_Type"}}
    engine = ConfigurationEngine(model)
    assert {d.property for d in engine.sink.by_code(dg.FABRIC_PAIR_AMBIGUOUS)} == {
        "Chair_Fabric_Colour", "Seat_Pad_Fabric_Colour"}


# ------------------------------------------------------------------ the one manual property, on real data
import hashlib  # noqa: E402

from services.ocd_engine.generator import GenerationError  # noqa: E402

LN10_HASH = "69e06593d7131dd994401c14ef85e43992fda8c12f62afde2a6f0ba63caaf377"
OVERRIDE_CASES = [
    ("lino", "MI1E3", "LINO_OPT", "Seat_Fabric_Type", "Fabric_Colour"),
    ("tun", "NOTUN420", "TUN_OPT", "Upholstered_Base_Fabric", "Upholstered_Base_Fabric_Colour"),
    ("bay_work_pod", "PEP100", "BAY_POD_OPT", "Exterior_Fabric_Type", "Exterior_Fabric_Colour"),
]


def finals(outcome):
    return sorted(s.final_article for s in outcome.skus)


@pytest.mark.parametrize("range_name,article,_cls,type_prop,colour_prop", OVERRIDE_CASES)
def test_selecting_the_detected_property_leaves_the_automatic_result_unchanged(range_name, article, _cls, type_prop,
                                                                                colour_prop):
    if not (db(range_name) / "ocd_article.csv").is_file():
        pytest.skip(f"{range_name} OCD data not available")
    generator = OcdArticleGenerator(db(range_name))
    rules = pinned_rules(generator, article, {type_prop.upper(), colour_prop.upper()})
    kw = dict(currency=generator.currencies()[0], price_date=DATE)
    automatic = finals(generator.generate([article], rules, **kw))
    for choice in (type_prop, colour_prop, colour_prop.lower()):
        assert finals(generator.generate([article], rules, fabric_property=choice, **kw)) == automatic
    assert finals(generator.generate([article], rules, fabric_property="", **kw)) == automatic


@pytest.mark.parametrize("range_name,article,prop", [("tun", "NOTUN420", "Power_Standard"),
                                                     ("bay_work_pod", "PEP100", "Surface_Finish"),
                                                     ("lino", "MI1E3", "Arms")])
def test_selecting_a_property_that_is_not_a_fabric_is_refused_before_anything_is_enumerated(range_name, article, prop):
    if not (db(range_name) / "ocd_article.csv").is_file():
        pytest.skip(f"{range_name} OCD data not available")
    generator = OcdArticleGenerator(db(range_name))
    with pytest.raises(GenerationError, match="no fabric type/colour relationship"):
        generator.generate([article], currency=generator.currencies()[0], price_date=DATE, fabric_property=prop)


@needs("tun")
def test_tun_property_choices_carry_the_translated_label_and_the_keyword_flag():
    generator = OcdArticleGenerator(db("tun"))
    choices = {c.name: c for c in generator.fabric_property_choices(["NOTUN420"])}
    assert choices["Upholstered_Base_Fabric"].candidate and choices["Upholstered_Base_Fabric_Colour"].candidate
    assert choices["Upholstered_Base_Fabric"].label and choices["Upholstered_Base_Fabric"].display.startswith(
        "Upholstered_Base_Fabric - ")
    assert not choices["Power_Standard"].candidate
    assert fabric.is_candidate(next(p for p in generator._build_model("NOTUN420").properties
                                    if p.name == "Upholstered_Base_Fabric"))


BETWIXT = Path(REAL_OCD_ROOT) / "betwixt" / "ANY" / "1" / "db"


@pytest.mark.skipif(not (BETWIXT / "ocd_article.csv").is_file(), reason="Betwixt OCD data not available")
@pytest.mark.parametrize("choice", ["", "Seat_Fabric_Type", "Seat_Fabric_Colour", "Back_Fabric_Colour"])
def test_betwixt_ln10_keeps_its_432_sku_baseline_with_or_without_a_selection(choice):
    generator = OcdArticleGenerator(BETWIXT)
    outcome = generator.generate(["LN10"], currency="GBP", price_date="2026-11-02", fabric_property=choice)
    digest = hashlib.sha256(chr(10).join(finals(outcome)).encode()).hexdigest()
    assert len(outcome.skus) == 432 and digest == LN10_HASH
