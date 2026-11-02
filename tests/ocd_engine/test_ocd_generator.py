"""Standalone SKU generation over an OCD folder: describe, rules, relations, duplicates, pricing, errors."""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from core.cancellation import CancellationToken, OperationCancelled, cancellation_scope
from services.ocd_engine.generator import (
    MODE_DEFAULT, MODE_FIXED, GenerationError, OcdArticleGenerator, PropertyRule,
)
from tests.ocd_engine.ocd_helpers import OBX_REFERENCE_DIR, REAL_OCD_ROOT
from tests.ocd_engine.ocd_repo_fixture import (
    CHAIR1_FINALS, CHAIR1_PRICES_EUR, write, write_demo_range,
)

DATE = "2026-01-15"


@pytest.fixture
def db(tmp_path):
    return write_demo_range(tmp_path)


@pytest.fixture
def generator(db):
    return OcdArticleGenerator(db)


def finals(outcome):
    return [s.final_article for s in outcome.skus]


# ------------------------------------------------------------------ describe
def test_describe_reads_properties_values_defaults_labels_and_relations(generator):
    description = generator.describe("CHAIR1")
    assert description.label == "Demo Chair" and description.scheme_id == "U1"
    material, size = description.properties
    assert (material.key, material.label, material.scope) == ("DEMO_OPT:Material", "Material", "C")
    assert [(v.value, v.label, v.is_default) for v in material.values] == [("W", "Wood", False), ("M", "Metal", True)]
    assert material.default_value == "M" and size.default_value == "S"
    large = size.values[1]
    assert [(r.kind, r.text) for r in large.relations] == [("precondition", "Material = 'W'")]
    assert [(r.kind, r.domain) for r in description.relations] == [("action", "P")]
    assert description.relations[0].text == "$VARCOND = 'SIZE=' + Size,"


def test_describe_unknown_article_and_estimate(generator):
    with pytest.raises(GenerationError, match="NOPE is not in"):
        generator.describe("NOPE")
    props = generator.describe("CHAIR1").properties
    assert generator.estimate(props) == (2, 4)
    assert generator.estimate(props, [PropertyRule("DEMO_OPT:Material", MODE_FIXED, "W")]) == (1, 2)


# ------------------------------------------------------------ relation semantics
def test_valid_skus_follow_the_relations_and_the_code_scheme(generator):
    outcome = generator.generate(["CHAIR1"], currency="EUR", price_date=DATE)
    assert finals(outcome) == CHAIR1_FINALS            # Metal/Large is excluded by Size=L's precondition
    assert (outcome.invalid, outcome.duplicates, outcome.truncated, outcome.warnings) == (0, 0, False, [])
    assert outcome.pruned >= 1                         # the excluded value was pruned, not enumerated
    by_final = {s.final_article: s for s in outcome.skus}
    assert by_final["CHAIR1 W L"].ofml_varcode == "DEMO_OPT.Material=W;DEMO_OPT.Size=L"
    assert by_final["CHAIR1 W L"].varconds == ("SIZE=L",)
    assert {f: f"{s.price:.2f}" for f, s in by_final.items()} == CHAIR1_PRICES_EUR   # 100 base, +25 for SIZE=L
    assert all(s.status == "ok" and s.series_id == "DM" and s.label == "Demo Chair" for s in outcome.skus)


def test_fixed_and_default_rules_restrict_values_without_bypassing_relations(generator):
    fixed = generator.generate(["CHAIR1"], [PropertyRule("DEMO_OPT:Material", MODE_FIXED, "M")],
                               currency="EUR", price_date=DATE)
    assert finals(fixed) == ["CHAIR1 M S"]
    default = generator.generate(["CHAIR1"], [PropertyRule("DEMO_OPT:Material", MODE_DEFAULT),
                                              PropertyRule("DEMO_OPT:Size", MODE_DEFAULT)],
                                 currency="EUR", price_date=DATE)
    assert finals(default) == ["CHAIR1 M S"]
    # Pinning Metal + Large asks for a combination the data forbids: nothing valid, nothing invented.
    impossible = generator.generate(["CHAIR1"], [PropertyRule("DEMO_OPT:Material", MODE_FIXED, "M"),
                                                 PropertyRule("DEMO_OPT:Size", MODE_FIXED, "L")],
                                    currency="EUR", price_date=DATE)
    assert impossible.skus == [] and impossible.invalid == 1


def test_rule_errors_and_skipped_rules(generator):
    with pytest.raises(GenerationError, match="'Q' is not offered for Material"):
        generator.generate(["CHAIR1"], [PropertyRule("DEMO_OPT:Material", MODE_FIXED, "Q")],
                           currency="EUR", price_date=DATE)
    outcome = generator.generate(["CHAIR1"], [PropertyRule("DEMO_OPT:Nope", MODE_FIXED, "x")],
                                 currency="EUR", price_date=DATE)
    assert len(outcome.skus) == 3
    assert any("DEMO_OPT:Nope is not offered" in w for w in outcome.warnings)


def test_default_rule_without_a_default_value_varies_the_property_and_says_so(generator):
    outcome = generator.generate(["SIDE1"], [PropertyRule("DEMO_OPT2:Colour", MODE_DEFAULT)],
                                 currency="EUR", price_date=DATE)
    assert any("Colour has no default value; it is varied" in w for w in outcome.warnings)
    assert len(outcome.skus) + outcome.duplicates == 4


# ---------------------------------------------------------------- duplicates, limits
def test_duplicate_final_numbers_are_removed_and_counted(generator):
    outcome = generator.generate(["SIDE1"], currency="EUR", price_date=DATE)
    assert finals(outcome) == ["SIDE1 S", "SIDE1 L"]    # Colour does not feed scheme U2: 4 configurations, 2 SKUs
    assert outcome.duplicates == 2
    both = generator.generate(["CHAIR1", "CHAIR1"], currency="EUR", price_date=DATE)
    assert finals(both) == CHAIR1_FINALS and both.duplicates == 3      # a repeated base article adds nothing


def test_limit_truncates_and_reports(generator):
    outcome = generator.generate(["CHAIR1"], currency="EUR", price_date=DATE, max_configurations=2)
    assert finals(outcome) == CHAIR1_FINALS[:2] and outcome.truncated
    assert "Stopped at the limit of 2 SKU(s)." in outcome.warnings
    exact = generator.generate(["CHAIR1"], currency="EUR", price_date=DATE, max_configurations=3)
    assert len(exact.skus) == 3 and not exact.truncated        # flagged only when one more SKU exists


def test_cancellation_propagates_from_the_engine(tmp_path):
    db = tmp_path / "big" / "ANY" / "1" / "db"
    db.mkdir(parents=True)
    write(db, "ocd_article.csv", "BIG;C;MK;S;1;;0;0;1;C62;U1")
    write(db, "ocd_propertyclass.csv", "BIG;1;C1;10;0")
    write(db, "ocd_property.csv", "\n".join(f"C1;P{n};{n};;0;C;1;0;1;0;0;0;C;0;" for n in range(1, 4)))
    write(db, "ocd_propertyvalue.csv", "\n".join(
        f"C1;P{n};{i};;0;0;0;EQ;V{i};;;;;" for n in range(1, 4) for i in range(20)))
    write(db, "ocd_price.csv", "BIG;;S;B;;;1;1;EUR;20250101;99991231;1;")
    write(db, "ocd_codescheme.csv", 'U1;@,@,@;"";"";0;"-";"X";1;"";""')
    token = CancellationToken()

    class Canceller:
        """Requests cancellation as soon as enumeration starts; the engine must stop at its checkpoint."""
        def note(self, _text):
            token.request_cancel()

        def advance(self, *_args):
            pass

    generator = OcdArticleGenerator(db)
    _ = generator.dataset
    with cancellation_scope(token):
        with pytest.raises(OperationCancelled):
            generator.generate(["BIG"], currency="EUR", price_date=DATE, reporter=Canceller())


# ----------------------------------------------------------------------- pricing
def test_currency_must_be_chosen_when_ambiguous_and_is_listed(generator):
    assert generator.currencies() == ["EUR", "GBP"]
    with pytest.raises(GenerationError, match=r"Choose a currency \(EUR, GBP\)"):
        generator.generate(["CHAIR1"], price_date=DATE)
    gbp = generator.generate(["CHAIR1", "SIDE1"], currency="gbp", price_date=DATE)
    prices = {s.final_article: s.price for s in gbp.skus}
    assert prices["CHAIR1 W S"] == Decimal("90.00")
    assert prices["CHAIR1 W L"] == Decimal("90.00")             # no GBP price for SIZE=L: base only
    assert prices["SIDE1 S"] is None and gbp.unpriced == 2      # SIDE1 has no GBP price at all
    assert [s.status for s in gbp.skus if s.price is None] == ["unpriced"] * 2
    assert any("2 SKU(s) have no price in GBP" in w for w in gbp.warnings)
    assert [s.final_article for s in gbp.exportable if s.base_article == "SIDE1"] == []


def test_single_currency_is_chosen_automatically(tmp_path):
    db = write_demo_range(tmp_path)
    (db / "ocd_price.csv").write_bytes(b"CHAIR1;;S;B;;;100;1;EUR;20250101;99991231;1;\r\n")
    assert len(OcdArticleGenerator(db).generate(["CHAIR1"], price_date=DATE).skus) == 3


def test_price_date_outside_validity_leaves_skus_unpriced(generator):
    outcome = generator.generate(["CHAIR1"], currency="EUR", price_date="2024-06-01")
    assert len(outcome.skus) == 3 and outcome.unpriced == 3 and outcome.exportable == []
    assert outcome.skus[0].message == ("no usable B price row for key (none) on 20240601 in EUR: "
                                       "no row is valid on 20240601; valid windows: 20250101-99991231")


def test_article_without_a_code_scheme_uses_the_base_number(generator):
    outcome = generator.generate(["STOOL1"], currency="EUR", price_date=DATE)
    assert finals(outcome) == ["STOOL1"]
    assert any("STOOL1: no code scheme" in w for w in outcome.warnings)


# ------------------------------------------------------------------- bad input
def test_request_validation(generator):
    with pytest.raises(GenerationError, match="at least one article"):
        generator.generate([], currency="EUR", price_date=DATE)
    with pytest.raises(GenerationError, match="price date"):
        generator.generate(["CHAIR1"], currency="EUR", price_date="")
    with pytest.raises(GenerationError, match="positive"):
        generator.generate(["CHAIR1"], currency="EUR", price_date=DATE, max_configurations=0)


def test_malformed_article_data_is_a_clear_error(generator):
    with pytest.raises(GenerationError, match="Malformed OCD data for article BROKEN"):
        generator.describe("BROKEN")
    with pytest.raises(GenerationError, match="Malformed OCD data for article BROKEN"):
        generator.generate(["BROKEN"], currency="EUR", price_date=DATE)


def test_malformed_price_row_is_a_clear_error(tmp_path):
    db = write_demo_range(tmp_path)
    (db / "ocd_price.csv").write_bytes(b"CHAIR1;;S;B;;;not-a-number;1;EUR;20250101;99991231;1;\r\n")
    with pytest.raises(GenerationError, match="Malformed price table"):
        OcdArticleGenerator(db).generate(["CHAIR1"], currency="EUR", price_date=DATE)


def test_missing_folder_and_missing_tables_are_reported(tmp_path):
    with pytest.raises(GenerationError, match="OCD data folder not found"):
        _ = OcdArticleGenerator(tmp_path / "gone").dataset
    (tmp_path / "empty").mkdir()
    with pytest.raises(GenerationError, match="ocd_article, ocd_property, ocd_propertyvalue"):
        _ = OcdArticleGenerator(tmp_path / "empty").dataset


def test_schema_descriptor_changes_the_column_order(tmp_path):
    """Columns are bound by the ``pdata.*.inp_descr`` field names, not by position."""
    db = write_demo_range(tmp_path)
    (db / "pdata.ocd_price.inp_descr").write_text(
        "table\tocd_price\tocd_price.csv\tmscsv\nfields\t13\n" + "\n".join(
            f"field\t{i}\t{n}\tvstring\t\tdelim ;" for i, n in enumerate(
                "currency article_nr var_cond price_type price_level price_rule price_textnr price is_fix "
                "date_from date_to scale_quantity rounding_id".split(), 1)), encoding="latin-1")
    write(db, "ocd_price.csv", "EUR;CHAIR1;;S;B;;;77;1;20250101;99991231;1;")
    outcome = OcdArticleGenerator(db).generate(["CHAIR1"], currency="EUR", price_date=DATE)
    assert {s.price for s in outcome.skus} == {Decimal("77.00")}


# ------------------------------------------------------------------ real data
REAL = Path(REAL_OCD_ROOT)


@pytest.mark.skipif(not REAL.exists(), reason="real OCD repository not available")
def test_real_dalby_matches_the_verified_engine_results():
    generator = OcdArticleGenerator(REAL / "dalby" / "ANY" / "1" / "db")
    assert generator.currencies() == ["EUR", "GBP"]
    outcome = generator.generate(["NODLE150"], currency="EUR", price_date=DATE)
    assert len(outcome.skus) == 60 and outcome.unpriced == 0           # 30 Top_Finish x 2 Frame_Finish
    tops = {dict((n, v) for _, n, v, _ in s.values)["Top_Finish"] for s in outcome.skus}
    assert len(tops) == 30
    sku = next(s for s in outcome.skus if s.final_article == "NODLE150 OAK BRC")
    assert sku.ofml_varcode == "DALBY_OPT.Frame_Finish=OAK;DALBY_OPT.Top_Finish=BRC"
    assert len(generator.generate(["NODLE320"], currency="EUR", price_date=DATE).skus) == 260


@pytest.mark.skipif(not REAL.exists() or not Path(OBX_REFERENCE_DIR).exists(),
                    reason="real OCD repository or reference OBX files not available")
def test_real_dalby_export_contains_every_final_article_pCon_resolved(tmp_path):
    import glob
    from services.article_obx.ocd_repository_obx import compare_with_reference, export_obx
    from services.ocd_engine.obx_reference import read_reference_obx

    path = sorted(p for p in glob.glob(f"{OBX_REFERENCE_DIR}/*Dalby*.obx") if "Mismatch" not in p)[0]
    reference = read_reference_obx(path)
    bases = sorted({r.base for r in reference})
    generator = OcdArticleGenerator(REAL / "dalby" / "ANY" / "1" / "db")
    outcome = generator.generate(bases, currency="EUR", price_date="2026-04-07")
    out = tmp_path / "dalby.obx"
    summary = export_obx(outcome.exportable, out, manufacturer_id="HM", price_date="2026-04-07")
    assert summary.ok and summary.article_lines == len(outcome.exportable)
    comparison = compare_with_reference(out, path)
    assert comparison.missing_in_generated == [] and len(comparison.matched) == len(reference)
