"""Parity of the engine against *real* OCD data and real pCon-resolved OBX files.

These tests read the live Herman Miller OFML repository and the pCon export
files on the developer machine; they are skipped where those are absent. Every
expected value below comes from the reference files or is derived by an
independent oracle written in the test, never from the engine under test.
"""
import dataclasses
import glob
from decimal import Decimal
from pathlib import Path

import pytest

from ocd_helpers import OBX_REFERENCE_DIR, REAL_OCD_ROOT
from services.ocd_engine.codescheme_engine import CodeSchemeEncoder, LiteralToken, PropToken, AtToken, tokenize
from services.ocd_engine.configuration_engine import ConfigurationEngine, EnumerationLimits
from services.ocd_engine.csv_loader import OcdCsvLoader, build_article_model
from services.ocd_engine.obx_reference import read_reference_obx
from services.ocd_engine.obx_serialization import ofml_varcode
from services.ocd_engine.pricing import PriceCalculator, PriceRow

ROOT = Path(REAL_OCD_ROOT)
needs_ocd = pytest.mark.skipif(not ROOT.exists(), reason="real OCD repository not available")
needs_obx = pytest.mark.skipif(not Path(OBX_REFERENCE_DIR).exists(), reason="reference OBX files not available")


def load(program):
    dataset = OcdCsvLoader().load(ROOT / program / "ANY" / "1" / "db")
    dataset._index()
    return dataset


@pytest.fixture(scope="module")
def dalby():
    return load("dalby")


def pinned(model, **pins):
    """Copy of ``model`` with the named properties restricted to one value each."""
    props = tuple(
        dataclasses.replace(p, values=tuple(v for v in p.values if v.value == pins[p.name]))
        if p.name in pins else p
        for p in model.properties
    )
    return dataclasses.replace(model, properties=props)


def generate(dataset, article, pins=None, **limits):
    model = build_article_model(dataset, article)
    if pins:
        model = pinned(model, **pins)
    engine = ConfigurationEngine(model, limits=EnumerationLimits(**limits) if limits else None)
    encoder = CodeSchemeEncoder(dataset.code_scheme(model.scheme_id))
    out = []
    for config, result in engine.generate():
        final = encoder.encode(article, engine.view(config.assignments, result.computed)).final_article
        out.append((config, result, final))
    return model, engine, out


def by_name(config):
    return {a.prop.name: (None if a.value is None else a.value.value) for a in config.assignments}


# ============================================================ Dalby: cascades
# Independent expectation, transcribed from ocd_relation.csv (rel 19530-19538, 19532-19535):
MDF_TOPS = {"Q01", "Q02", "Q03", "Q04", "Q05", "Q07", "Q08", "Q09", "Q10", "Q11", "Q12", "Q23", "Q32", "Q54",
            "Q55", "Q66", "Q72", "Q74", "Q75", "Q76", "Q77", "Q79", "Q83", "Q84"}
SAME_AS_TOP = {"OAK", "WLN", "BRC", "WRC"}
EDGE_TOPS = {"BSE", "WSE"}


def expected_dependents(top):
    material = "MDF" if top in MDF_TOPS else (top if top in SAME_AS_TOP else None)
    edge = top if top in EDGE_TOPS else None
    return material, edge, material or edge                       # Bottom_WFT = whichever is visible


@needs_ocd
def test_dalby_cascade_examples_from_the_task(dalby):
    _, _, results = generate(dalby, "NODLE150")
    pairs = {(by_name(c)["Top_Finish"], by_name(c)["Bottom_Material_G"]) for c, _, _ in results}
    assert ("Q75", "MDF") in pairs                                # Q75 + MDF: valid
    assert ("Q75", "OAK") not in pairs                            # Q75 + OAK: invalid
    assert ("OAK", "OAK") in pairs                                # OAK + OAK: valid
    assert ("WLN", "WLN") in pairs                                # WLN + WLN: valid


@needs_ocd
def test_dalby_every_dependent_property_for_every_top_finish(dalby):
    model, _, results = generate(dalby, "NODLE150")
    tops = {v.value for p in model.properties if p.name == "Top_Finish" for v in p.values}
    assert len(tops) == 30 and len(results) == 60                 # 30 Top_Finish x 2 Frame_Finish
    seen = set()
    for config, _, _ in results:
        values = by_name(config)
        material, edge, wft = expected_dependents(values["Top_Finish"])
        assert (values["Bottom_Material_G"], values["Bottom_Stright_Edge"], values["Bottom_WFT"]) == (material, edge, wft), \
            values["Top_Finish"]
        seen.add(values["Top_Finish"])
    assert seen == tops


@needs_ocd
def test_dalby_hidden_properties_and_article_dependent_preconditions(dalby):
    # NODLE1xx-2xx: Access_Cutout / Cable_leg precondition ($ BAN IN NODLE3xx..6xx) is FALSE => hidden
    _, _, low = generate(dalby, "NODLE150")
    assert all(next(a for a in c.assignments if a.prop.name == "Access_Cutout").hidden for c, _, _ in low)
    _, _, high = generate(dalby, "NODLE300")
    assert len(high) == 300 and all(by_name(c)["Access_Cutout"] for c, _, _ in high)


@needs_ocd
def test_dalby_nodle320_loses_exactly_brc_bse_wrc_wse(dalby):
    _, _, all_320 = generate(dalby, "NODLE320")
    _, _, all_300 = generate(dalby, "NODLE300")
    tops_320 = {by_name(c)["Top_Finish"] for c, _, _ in all_320}
    tops_300 = {by_name(c)["Top_Finish"] for c, _, _ in all_300}
    assert tops_300 - tops_320 == {"BRC", "BSE", "WRC", "WSE"} and len(all_320) == 260


@needs_ocd
def test_dalby_varconds_follow_price_relation(dalby):
    _, _, results = generate(dalby, "NODLE150")
    for config, result, _ in results:
        v = by_name(config)
        assert result.varconds == [f"6699={v['Frame_Finish']}".upper(), f"6695={v['Top_Finish']}".upper()]
    _, _, high = generate(dalby, "NODLE300")
    config, result, _ = high[0]
    v = by_name(config)
    assert result.varconds == [f"6821={v['Access_Cutout']}".upper(), f"7030={v['Cable_leg']}".upper(),
                               f"6699={v['Frame_Finish']}".upper(), f"6695={v['Top_Finish']}".upper()]


# ============================================================ Dalby: all 1,242 reference articles
def dalby_references():
    out = []
    for path in sorted(glob.glob(f"{OBX_REFERENCE_DIR}/*Dalby*.obx")):
        if "Mismatch" in path:
            continue
        out.extend(read_reference_obx(path))
    return out


@needs_ocd
@needs_obx
def test_dalby_reference_obx_final_ofmlvarcode_and_price_parity(dalby):
    references = dalby_references()
    assert len(references) == 1242
    calc = PriceCalculator([PriceRow.from_csv(r) for r in dalby.tables["price"]])
    cache = {}
    for ref in references:
        if ref.base not in cache:
            model, _, results = generate(dalby, ref.base)
            cache[ref.base] = (model, {final: (config, result) for config, result, final in results})
        model, configurations = cache[ref.base]
        assert ref.final in configurations, f"{ref.final} not generated"
        config, result = configurations[ref.final]
        assert ofml_varcode(config.assignments, model) == ref.ofml_varcode
        priced = calc.price(ref.base, result.varconds, price_date=ref.price_date, currency=ref.currency)
        assert priced.total == Decimal(ref.price), (ref.final, priced.total, ref.price)
        percentages = priced.percentages()
        assert len(percentages) == len(ref.price_components)
        for (_, got), (_, want) in zip(percentages, ref.price_components):
            assert abs(got - Decimal(want)) < Decimal("1e-20")


@needs_ocd
@needs_obx
def test_dalby_reference_final_equals_scheme_token_walk(dalby):
    """final = '@' consumes base chars, literals verbatim, values in order (independent re-derivation)."""
    scheme = dalby.code_scheme("U00000000000006335")
    tokens = tokenize(scheme.scheme)
    for ref in dalby_references()[:300]:
        values = dict(item.split("=", 1) for item in ref.ofml_varcode.split(";"))
        base = iter(ref.base)
        out = []
        for token in tokens:
            if isinstance(token, AtToken):
                out.append(next(base, ""))
            elif isinstance(token, LiteralToken):
                out.append(token.text)
            elif isinstance(token, PropToken):
                out.append(values.get(f"{token.property_class}.{token.property_name}", ""))
        assert "".join(out) == ref.final


# ============================================================ Lino (2,352 resolved articles)
@needs_ocd
@needs_obx
def test_lino_reference_configurations_are_valid_and_encode_identically():
    dataset = load("lino")
    references = []
    for path in sorted(glob.glob(f"{OBX_REFERENCE_DIR}/Lino*.obx")):
        references.extend(read_reference_obx(path))
    assert len(references) == 2352
    models = {}
    for ref in references:
        if ref.base not in models:
            models[ref.base] = build_article_model(dataset, ref.base)
        model = models[ref.base]
        pins = dict(item.split("=", 1) for item in ref.ofml_varcode.split(";") if item)
        pinned = tuple(
            dataclasses.replace(p, values=tuple(v for v in p.values if v.value == pins[f"{p.class_name}.{p.name}"]))
            if f"{p.class_name}.{p.name}" in pins else p
            for p in model.properties
        )
        pinned_model = dataclasses.replace(model, properties=pinned)
        engine = ConfigurationEngine(pinned_model, limits=EnumerationLimits(max_configurations=50_000))
        encoder = CodeSchemeEncoder(dataset.code_scheme(model.scheme_id))
        hit = any(
            encoder.encode(ref.base, engine.view(c.assignments, r.computed)).final_article == ref.final
            and ofml_varcode(c.assignments, pinned_model) == ref.ofml_varcode
            for c, r in engine.generate()
        )
        assert hit, f"{ref.base}: {ref.final} / {ref.ofml_varcode} not reproduced"


# ============================================================ Cosm: real user-defined CodeScheme
COSM_SCHEME = ("@,@,@,COSM_NORMAL:Assembly_Option,COSM_NORMAL:Back_Height,COSM_NORMAL:Height_Adjustment,"
               "COSM_NORMAL:Tilt,COSM_NORMAL:Seat_Depth,COSM_NORMAL:Arms, ,COSM_NORMAL:Frame_Finish, ,"
               "COSM_NORMAL:Chassis_Finish, ,COSM_NORMAL:Base_Finish, ,COSM_NORMAL:Castors_Glides, ,"
               "COSM_NORMAL:Armpad_Finish_H, ,COSM_NORMAL:Intercept_Finish")


@needs_ocd
def test_cosm_real_codescheme_encodes_per_the_grammar():
    cosm = load("cosm")
    scheme = cosm.code_scheme("U00000000000006297")
    assert scheme.scheme == COSM_SCHEME                           # the real CSV string, byte for byte
    tokens = tokenize(scheme.scheme)
    assert sum(isinstance(t, AtToken) for t in tokens) == 3 and tokens.count(LiteralToken(" ")) == 6

    model, _, results = generate(cosm, "FLC755", max_configurations=400)
    assert results
    names = [t.property_name for t in tokens if isinstance(t, PropToken)]
    for config, _, final in results[:200]:
        values = by_name(config)
        part = lambda n: values[n] or ""
        expected = (
            "FLC"                                                 # 3 x '@' consume F, L, C
            + "".join(part(n) for n in names[:6])                 # first six: no separators
            + " " + part("Frame_Finish") + " " + part("Chassis_Finish") + " " + part("Base_Finish")
            + " " + part("Castors_Glides") + " " + part("Armpad_Finish_H") + " " + part("Intercept_Finish")
        )
        assert final == expected


# ============================================================ Aeron: computed Code property
def aeron_oracle(ban, v):
    """The real Aeron ``Code`` relation (ocd_relation.csv 000000000000570755) re-implemented by hand."""
    code = None
    t = v.get("Aeron_Type")
    head = ["Assembly_Option", "Aeron_Type", "Height_Adjustment", "Tilt_Option", "Arms", "Armpads"] \
        if t in ("A", "B", "C") else ["Assembly_Option", "Height_Adjustment", "Tilt_Option", "Arms", "Armpads"]
    if t in ("A", "B", "C", "S"):
        code = ban[0:3]
    tails = {"W": ["Back_Support", "Frame_Finish", "Chassis_Finish", "Base_Finish", "Castors_Glides",
                   "Armpad_Finish", "Pellicle"],
             "F": ["Back_Support", "Frame_Finish", "Chassis_Finish", "Base_Finish", "Castors_Glides",
                   "Pellicle", "Armpad_Finish"],
             "N": ["Back_Support", "Frame_Finish", "Chassis_Finish", "Base_Finish", "Castors_Glides", "Pellicle"]}
    tail = tails.get(v.get("Armpads"))
    if code is not None and tail is not None:
        names = head + tail
        if all(v.get(n) is not None for n in names):              # undefined operand => assignment has no effect
            code = code + "".join(v[n] for n in head) + "".join(" " + v[n] for n in tail)
    return code


@needs_ocd
def test_aeron_computed_code_matches_independent_oracle_for_every_branch():
    aeron = load("aeron")
    types_seen, armpads_seen, checked = set(), set(), 0
    for article in aeron.article_numbers():
        for armpads in ("W", "F", "N"):                           # exercise every Code branch per article
            _, _, results = generate(aeron, article, pins={"Armpads": armpads, "Arms": "N" if armpads == "N" else "P"},
                                      max_configurations=40)       # real rule: W/F need Arms != N
            for config, result, final in results:
                values = by_name(config)
                expected = aeron_oracle(article, values)
                assert result.computed.get("CODE") == expected, (article, values)
                if expected is not None:
                    assert final == expected                      # scheme is the single token AERON_OPTIONS:Code
                types_seen.add(values.get("Aeron_Type"))
                armpads_seen.add(values.get("Armpads"))
                checked += 1
    assert {"A", "S"} <= types_seen and armpads_seen >= {"W", "F", "N"} and checked > 1000
