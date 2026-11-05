"""Price lookup against real repository price rows, the three price layouts, and the diagnostics.

Real-data provenance
--------------------
``fixtures/real_price_rows_layout_studio.csv`` holds the 70 rows of the live ``layout_studio`` repository
(``ocd_price.csv``, region ANY) that belong to article ``GEPMF`` and to the nine variant conditions its
price relations assign for the SKU ``GEPMFB.1424S4M NN 0B 0B DB3``. pCon.planner priced that SKU in
``Layout_MeetingTables_BasicQA_GBP.obx`` at **1856.00 GBP on 2025-06-06** with seven price components;
those pCon numbers are copied below as the expectation, not computed from the code under test.

Layouts exercised
-----------------
* base price without a variant condition (Dalby: ``NODLE100;;S;B``)         - covered by the parity suite
* base price keyed by a variant condition (Lino/Aeron: ``MI7E315AF;15AF;S;B``)
* no base price at all, only extra charges on ``*`` (Layout Studio, Bay Work Pod, Everywhere ...)
"""
from __future__ import annotations

import csv
import re
from decimal import Decimal
from pathlib import Path

import pytest

from services.article_obx.ocd_repository_obx import export_obx
from services.ocd_engine import diagnostics as dg
from services.ocd_engine.generator import GenerationError, OcdArticleGenerator
from services.ocd_engine.pricing import PriceCalculator, PriceRow
from tests.ocd_engine.ocd_repo_fixture import write_demo_range

D = Decimal
COLUMNS = ["article_nr", "var_cond", "price_type", "price_level", "price_rule", "price_textnr", "price",
           "is_fix", "currency", "date_from", "date_to", "scale_quantity", "rounding_id"]
FIXTURE = Path(__file__).parent / "fixtures" / "real_price_rows_layout_studio.csv"

KNOWN_ARTICLE = "GEPMF"
KNOWN_FINAL = "GEPMFB.1424S4M NN 0B 0B DB3"
# $VARCOND values and $SET_PRICING_FACTOR calls of the price relations for that SKU (engine output, checked
# below against the repository's own relation text only through the resulting price)
KNOWN_VARCONDS = ["GETM.1424FS4M", "GETM.1424FS4M 9168=NN", "GETM.1424FS4M 3831=0B", "GEBR.12", "GELBEN.14",
                  "GELBEN.14 3867=DB3", "GELBSN.14", "GELBSN.14 3867=DB3", "GE2HPF."]
KNOWN_FACTORS = {"GEBR.12": 4.0, "GELBEN.14": 2.0, "GELBEN.14 3867=DB3": 2.0, "GE2HPF.": 4.0}
# pCon's seven price components of that SKU, as percentages of the 1856.00 total
PCON_PERCENTAGES = ["40.625", "15.94827586206896551724137931034483", "20.79741379310344827586206896551724",
                    "2.155172413793103448275862068965517", "10.9375", "1.131465517241379310344827586206897",
                    "8.405172413793103448275862068965517"]


def read_rows(path: Path) -> list[PriceRow]:
    with open(path, encoding="latin-1", newline="") as handle:
        return [PriceRow.from_csv(dict(zip(COLUMNS, r))) for r in csv.reader(handle, delimiter=";")]


@pytest.fixture(scope="module")
def real_calculator():
    return PriceCalculator(read_rows(FIXTURE))


def known(calc, *, date="2025-06-06", currency="GBP", varconds=None):
    return calc.price(KNOWN_ARTICLE, KNOWN_VARCONDS if varconds is None else varconds, price_date=date,
                      currency=currency, factors=KNOWN_FACTORS)


# =============================================================== real rows: a known priced SKU
def test_known_sku_gets_the_price_pcon_gave_it(real_calculator):
    result = known(real_calculator)
    assert result.total == D("1856.00")                                  # pCon: 1856.0 GBP
    assert result.base is None                                           # this layout has no base price row
    assert [c.amount for c in result.components] == [D(x) for x in
                                                    ("754.00", "296.00", "386.00", "40.00", "203.00", "21.00", "156.00")]
    assert any(d.code == dg.PRICE_FROM_EXTRA_CHARGES for d in result.diagnostics)
    assert not any(d.severity is dg.Severity.ERROR for d in result.diagnostics)


def test_known_sku_components_equal_pcons_percentages(real_calculator):
    result = known(real_calculator)
    shares = [amount * 100 / result.total for amount in (c.amount for c in result.components)]
    assert len(shares) == len(PCON_PERCENTAGES)
    for got, want in zip(shares, PCON_PERCENTAGES):
        assert abs(got - D(want)) < D("1e-20")


# =============================================================== key derivation
def test_expected_keys_are_the_unconditioned_key_then_each_assigned_variant_condition(real_calculator):
    diagnosis = real_calculator.diagnose(KNOWN_ARTICLE, ["getm.1424fs4m", "GEBR.12", "GEBR.12", ""],
                                         price_date="2025-06-06", currency="GBP")
    assert diagnosis.expected_keys == ("", "GETM.1424FS4M", "GEBR.12")    # upper-cased, de-duplicated, '' first
    x = {look.key: look for look in diagnosis.lookups if look.level == "X"}
    assert x["GEBR.12"].joker and x["GEBR.12"].chosen.value == D(74)
    # 5 date windows x 2 currencies -> the valid window leaves one GBP row
    assert (x["GEBR.12"].candidates, x["GEBR.12"].after_date, x["GEBR.12"].after_currency) == (10, 2, 1)
    b = next(look for look in diagnosis.lookups if look.level == "B")
    assert b.candidates == 0 and b.chosen is None and "no B-level row exists" in b.reason
    assert not diagnosis.has_base_rows


def test_diagnosis_describes_the_table_without_dumping_it(real_calculator):
    diagnosis = real_calculator.diagnose(KNOWN_ARTICLE, KNOWN_VARCONDS, price_date="2025-06-06", currency="EUR")
    assert (diagnosis.table_rows, diagnosis.article_rows, diagnosis.joker_rows) == (70, 0, 70)
    assert diagnosis.types == ("S",) and diagnosis.currencies == ("EUR", "GBP") and diagnosis.levels == ("X",)
    assert len(diagnosis.date_windows) == 5
    lines = diagnosis.lines()
    assert len(lines) < 30 and any("joker '*'" in line for line in lines)


# =============================================================== currency and validity date
def test_currency_selects_the_matching_rows_only(real_calculator):
    assert known(real_calculator, currency="GBP").total == D("1856.00")
    assert known(real_calculator, currency="EUR").total == D("2096.00")   # EUR rows of the same windows
    assert known(real_calculator, currency="eur").total == D("2096.00")   # case-insensitive


def test_validity_date_picks_the_window_that_contains_it(real_calculator):
    assert known(real_calculator, date="2025-06-06").total == D("1856.00")
    assert known(real_calculator, date="2026-06-01").total == D("1856.00")    # 20250602-20260405 / 20260406-20260906
    assert known(real_calculator, date="2026-09-07").total == D("1911.00")    # the window opening 20260907
    assert known(real_calculator, date="20260907", currency="EUR").total == D("2155.00")


def test_date_outside_every_window_is_unpriced_and_says_which_windows_exist(real_calculator):
    result = known(real_calculator, date="2000-01-01")
    assert result.total is None
    error = next(d for d in result.diagnostics if d.severity is dg.Severity.ERROR)
    assert "no usable price on 20000101 in GBP" in error.message
    warning = next(d for d in result.diagnostics if d.code == dg.NO_PRICE_FOR_KEY and d.value == "GETM.1424FS4M")
    assert "no row is valid on 20000101; valid windows:" in warning.message


def test_unknown_currency_is_never_substituted_and_names_the_available_ones(real_calculator):
    result = known(real_calculator, currency="USD")
    assert result.total is None
    warning = next(d for d in result.diagnostics if d.code == dg.NO_PRICE_FOR_KEY and d.value == "GEBR.12")
    assert "no row in USD on 20250606; currencies valid then: EUR, GBP" in warning.message


# =============================================================== no matching row / unusable data
def test_variant_conditions_without_rows_leave_the_sku_unpriced(real_calculator):
    result = known(real_calculator, varconds=["NOT.A.KEY", "ALSO.MISSING"])
    assert result.total is None and result.components == []
    error = next(d for d in result.diagnostics if d.severity is dg.Severity.ERROR)
    assert error.code == dg.NO_BASE_PRICE
    assert "no extra-charge (X) item matched the configuration's variant conditions" in error.message
    assert known(real_calculator, varconds=[]).total is None             # no key at all: nothing to add up


def test_an_article_with_no_rows_anywhere_is_unpriced():
    result = PriceCalculator([]).price("GHOST", ["K"], price_date="2026-01-01", currency="EUR")
    assert result.total is None
    assert result.diagnostics[-1].code == dg.NO_BASE_PRICE and result.diagnostics[-1].severity is dg.Severity.ERROR


def test_extra_charges_that_sum_to_zero_are_not_a_price():
    rows = [PriceRow(article="*", var_cond="K", level="X", value=D(0), currency="EUR", date_from="20250101",
                      date_to="99991231")]
    result = PriceCalculator(rows).price("A", ["K"], price_date="2026-01-01", currency="EUR")
    assert result.total is None
    assert "sum to zero" in result.diagnostics[-1].message


def test_percentage_only_base_rows_are_reported_as_such():
    rows = [PriceRow(article="A", level="B", value=D(10), is_fix=False, currency="EUR", date_from="20250101")]
    result = PriceCalculator(rows).price("A", [], price_date="2026-01-01", currency="EUR")
    assert result.total is None
    assert "percentages; a base price must be a fixed amount" in result.diagnostics[-1].message


def test_malformed_price_rows_are_rejected_not_skipped():
    with pytest.raises(Exception):
        PriceRow.from_csv(dict(zip(COLUMNS, "A;;S;B;;;12x;1;EUR;20250101;99991231;1;".split(";"))))


# =============================================================== base price keyed by a variant condition
# Real rows of lino/ANY (EUR, valid 20260406-99991231): the base price of MI7E315AF is keyed by "15AF".
LINO_ROWS = [
    PriceRow(article="MI7E315AF", var_cond="15AF", level="B", value=D(1085), currency="EUR", date_from="20260406", date_to="99991231"),
    PriceRow(article="MI7E315AF", var_cond="15AF 7603=AJ", level="X", value=D(33), currency="EUR", date_from="20260406", date_to="99991231"),
    PriceRow(article="MI7E315AF", var_cond="15AF 7608=68", level="X", value=D(82), currency="EUR", date_from="20260406", date_to="99991231"),
    PriceRow(article="MI7E315AF", var_cond="15AF 8=1FD", level="X", value=D(54), currency="EUR", date_from="20260406", date_to="99991231"),
]


def test_a_base_price_keyed_by_a_variant_condition_is_the_base_price():
    keys = ["15AF", "15AF 7603=AJ", "15AF 7608=68", "15AF 7605=BB", "15AF 7607=4RM01", "15AF 8=1FD"]
    result = PriceCalculator(LINO_ROWS).price("MI7E315AF", keys, price_date="2026-09-07", currency="EUR")
    assert result.total == D("1254.00") and result.base == D("1085.00")      # 1085 + 33 + 82 + 54
    assert [c.level for c in result.components] == ["B", "X", "X", "X"]      # pCon also shows "baseprice" + 3 surcharges
    assert not any(d.severity is dg.Severity.ERROR for d in result.diagnostics)


def test_keyed_base_prices_without_their_condition_say_which_conditions_exist():
    result = PriceCalculator(LINO_ROWS).price("MI7E315AF", ["15AF 7603=AJ"], price_date="2026-09-07", currency="EUR")
    assert result.total is None
    message = next(d.message for d in result.diagnostics if d.severity is dg.Severity.ERROR)
    assert message.startswith("no usable B price row for key (none) on 20260907 in EUR: ")
    assert "keyed by other variant conditions (15AF)" in message


def test_percentage_extra_charge_uses_the_keyed_base():
    rows = [*LINO_ROWS[:1], PriceRow(article="MI7E315AF", var_cond="P", level="X", value=D(10), is_fix=False,
                                     currency="", date_from="20260406", date_to="99991231")]
    result = PriceCalculator(rows).price("MI7E315AF", ["15AF", "P"], price_date="2026-09-07", currency="EUR")
    assert result.total == D("1193.50")


# =============================================================== generated SKUs and export share one price
def rewrite_prices(db: Path, text: str) -> None:
    (db / "ocd_price.csv").write_bytes(text.encode("latin-1"))


def generate(db, **kw):
    return OcdArticleGenerator(db).generate(["CHAIR1"], currency=kw.pop("currency", "EUR"),
                                            price_date=kw.pop("price_date", "2026-01-15"), **kw)


def test_generated_skus_are_priced_from_a_keyed_base(tmp_path):
    db = write_demo_range(tmp_path)
    rewrite_prices(db, "CHAIR1;SIZE=S;S;B;;;100;1;EUR;20250101;99991231;1;\r\n"
                       "CHAIR1;SIZE=L;S;B;;;125;1;EUR;20250101;99991231;1;\r\n")
    outcome = generate(db)
    assert {s.final_article: s.price for s in outcome.skus} == {
        "CHAIR1 W S": D("100.00"), "CHAIR1 W L": D("125.00"), "CHAIR1 M S": D("100.00")}
    assert outcome.unpriced == 0 and all(s.status == "ok" and s.message == "" for s in outcome.skus)


def test_generated_skus_are_priced_from_extra_charges_only(tmp_path):
    db = write_demo_range(tmp_path)
    rewrite_prices(db, "*;SIZE=S;S;X;;;100;1;EUR;20250101;99991231;1;\r\n"
                       "*;SIZE=L;S;X;;;125;1;EUR;20250101;99991231;1;\r\n")
    outcome = generate(db)
    assert {s.final_article: s.price for s in outcome.skus} == {
        "CHAIR1 W S": D("100.00"), "CHAIR1 W L": D("125.00"), "CHAIR1 M S": D("100.00")}
    assert outcome.unpriced == 0


def test_generated_skus_stay_unpriced_when_the_price_relation_keys_have_no_rows(tmp_path):
    db = write_demo_range(tmp_path)
    rewrite_prices(db, "*;OTHER;S;X;;;100;1;EUR;20250101;99991231;1;\r\n")
    outcome = generate(db)
    assert outcome.unpriced == 3 and outcome.exportable == []
    assert "no extra-charge (X) item matched" in outcome.skus[0].message


def test_malformed_price_file_stops_generation_with_a_clear_message(tmp_path):
    db = write_demo_range(tmp_path)
    rewrite_prices(db, "CHAIR1;;S;B;;;abc;1;EUR;20250101;99991231;1;\r\n")
    with pytest.raises(GenerationError, match="Malformed price table"):
        generate(db)


def test_a_missing_price_file_leaves_every_sku_unpriced_and_names_the_problem(tmp_path):
    db = write_demo_range(tmp_path)
    (db / "ocd_price.csv").unlink()
    generator = OcdArticleGenerator(db)
    with pytest.raises(GenerationError, match="Choose a currency"):
        generator.generate(["CHAIR1"], price_date="2026-01-15")
    lines = generator.price_diagnostics("CHAIR1", currency="EUR", price_date="2026-01-15")
    assert any("(no ocd_price.csv)" in line and "0 row(s) loaded" in line for line in lines)
    assert lines[-1].startswith("result: unpriced")


def test_exported_obx_carries_exactly_the_generated_price(tmp_path):
    db = write_demo_range(tmp_path)
    rewrite_prices(db, "*;SIZE=S;S;X;;;100;1;EUR;20250101;99991231;1;\r\n"
                       "*;SIZE=L;S;X;;;125.5;1;EUR;20250101;99991231;1;\r\n")
    outcome = generate(db)
    target = tmp_path / "out.obx"
    summary = export_obx(outcome.exportable, str(target), manufacturer_id="MK", price_date="2026-01-15")
    assert summary.exported == 3 and summary.skipped_unpriced == 0 and summary.ok
    xml = target.read_text(encoding="utf-8")
    written = re.findall(r'<itemPrice type="sale" value="([^"]+)" currency="([^"]+)"', xml)
    assert sorted(written) == [("100.00", "EUR"), ("100.00", "EUR"), ("125.50", "EUR")]
    assert sorted(s.price for s in outcome.skus) == [D("100.00"), D("100.00"), D("125.50")]


def test_price_diagnostics_for_a_generated_sku(tmp_path):
    db = write_demo_range(tmp_path)
    generator = OcdArticleGenerator(db)
    sku = next(s for s in generator.generate(["CHAIR1"], currency="EUR", price_date="2026-01-15").skus
               if s.final_article == "CHAIR1 W L")
    lines = generator.price_diagnostics("CHAIR1", varconds=sku.varconds, currency="EUR", price_date="2026-01-15")
    text = "\n".join(lines)
    assert f"repository folder: {db}" in text and "ocd_price.csv" in text and "4 row(s) loaded" in text
    assert "price types ['S']" in text and "currencies ['EUR', 'GBP']" in text
    assert "keys ['', 'SIZE=L']" in text
    assert "B:(none): 125" not in text and "B:(none): 100" in text and "X:SIZE=L: 25" in text
    assert lines[-1] == "result: 125.00 EUR"
    with pytest.raises(GenerationError, match="price date"):
        generator.price_diagnostics("CHAIR1", currency="EUR", price_date="")


# =============================================================== real repository (skipped where absent)
ROOT = Path("C:/HermanMillerOFMLSVN/Staging/HermanMiller/_repository/hmx")
REFERENCE = Path("C:/Users/siaoca/Downloads/Layout_MeetingTables_BasicQA_GBP.obx")
needs_real = pytest.mark.skipif(not (ROOT / "layout_studio").exists() or not REFERENCE.exists(),
                                reason="real repository / pCon reference not available")


@needs_real
def test_every_layout_studio_reference_sku_gets_pcons_price_from_the_live_repository():
    import dataclasses

    from services.ocd_engine.codescheme_engine import CodeSchemeEncoder
    from services.ocd_engine.configuration_engine import ConfigurationEngine, EnumerationLimits
    from services.ocd_engine.csv_loader import OcdCsvLoader, build_article_model
    from services.ocd_engine.obx_reference import read_reference_obx

    dataset = OcdCsvLoader().load(ROOT / "layout_studio" / "ANY" / "1" / "db")
    dataset._index()
    calculator = PriceCalculator([PriceRow.from_csv(r) for r in dataset.tables["price"]])
    references = read_reference_obx(str(REFERENCE))
    assert len(references) == 67
    for ref in references:
        model = build_article_model(dataset, ref.base)
        pins = dict(item.split("=", 1) for item in ref.ofml_varcode.split(";") if item)
        pinned = dataclasses.replace(model, properties=tuple(
            dataclasses.replace(p, values=tuple(v for v in p.values if v.value == pins[f"{p.class_name}.{p.name}"]))
            if f"{p.class_name}.{p.name}" in pins else p for p in model.properties))
        engine = ConfigurationEngine(pinned, limits=EnumerationLimits(max_configurations=50_000))
        encoder = CodeSchemeEncoder(dataset.code_scheme(model.scheme_id))
        match = next(result for config, result in engine.generate()
                     if encoder.encode(ref.base, engine.view(config.assignments, result.computed)).final_article
                     == ref.final)
        priced = calculator.price(ref.base, match.varconds, price_date=ref.price_date, currency=ref.currency,
                                  factors=dict(match.pricing_factors))
        assert priced.total == D(ref.price), (ref.final, priced.total, ref.price)
        assert len(priced.components) == len(ref.price_components)


# ================================= accessories / NOCUS: the case reported as "500 without price"
# ``fixtures/real_price_rows_accessories_nocus.csv`` holds all 12 ``S``/``B`` rows of article NOCUS from the
# live ``accessories`` repository (ocd_price.csv, region ANY). Every one is keyed by the variant condition
# ``1`` (the code-scheme base the price relation assigns); NOCUS has no unconditioned B row. In the live
# repository the generator produced 500 SKUs (1017 nodes evaluated, 38852 values pruned) and the earlier
# calculator, which only looked for an unconditioned B row, left all 500 unpriced.
NOCUS_FIXTURE = Path(__file__).parent / "fixtures" / "real_price_rows_accessories_nocus.csv"


@pytest.fixture(scope="module")
def nocus_calculator():
    return PriceCalculator(read_rows(NOCUS_FIXTURE))


def test_nocus_is_priced_from_its_keyed_base_row(nocus_calculator):
    result = nocus_calculator.price("NOCUS", ["1", "1 8=1HA"], price_date="2026-11-02", currency="EUR")
    assert result.total == D("162.00") and result.base == D("162.00")   # row NOCUS;1;S;B;;;162;1;EUR;20260406;99991231
    assert result.components[0].row.currency == "EUR" and result.components[0].key == "1"


def test_nocus_keyed_lookup_selects_currency_and_date_window(nocus_calculator):
    gbp = nocus_calculator.price("NOCUS", ["1"], price_date="2026-11-02", currency="GBP")
    assert gbp.total is not None and gbp.components[0].row.currency == "GBP"
    old = nocus_calculator.price("NOCUS", ["1"], price_date="2022-03-01", currency="EUR")
    assert old.total is not None and old.components[0].row.date_from <= "20220301" <= old.components[0].row.date_to
    assert nocus_calculator.price("NOCUS", ["1"], price_date="2019-01-01", currency="EUR").total is None


def test_nocus_without_the_assigned_key_is_unpriced_and_says_why(nocus_calculator):
    result = nocus_calculator.price("NOCUS", [], price_date="2026-11-02", currency="EUR")
    assert result.total is None
    assert "keyed by other variant conditions (1)" in next(
        d.message for d in result.diagnostics if d.severity is dg.Severity.ERROR)


def test_assigned_keys_with_no_base_row_name_both_sides(nocus_calculator):
    result = nocus_calculator.price("NOCUS", ["ZZ"], price_date="2026-11-02", currency="EUR")
    message = next(d.message for d in result.diagnostics if d.severity is dg.Severity.ERROR)
    assert "assigned ZZ" in message and "keyed by other variant conditions (1)" in message


def test_nocus_diagnosis_reports_the_derived_key_and_chosen_row(nocus_calculator):
    diagnosis = nocus_calculator.diagnose("NOCUS", ["1"], price_date="2026-11-02", currency="EUR")
    assert diagnosis.expected_keys == ("", "1") and diagnosis.has_base_rows
    base_keyed = next(look for look in diagnosis.lookups if look.level == "B" and look.key == "1")
    assert (base_keyed.candidates, base_keyed.after_date, base_keyed.after_currency) == (12, 2, 1)
    assert base_keyed.chosen.value == D(162)
    assert next(look for look in diagnosis.lookups if look.level == "B" and not look.key).candidates == 0


@pytest.mark.skipif(not (ROOT / "accessories").exists(), reason="real repository not available")
def test_live_nocus_generation_prices_every_sku_and_the_obx_agrees(tmp_path):
    generator = OcdArticleGenerator(ROOT / "accessories" / "ANY" / "1" / "db")
    outcome = generator.generate(["NOCUS"], currency="EUR", price_date="2026-11-02", fabric_default_only=False)
    assert len(outcome.skus) == 2181 and outcome.unpriced == 0 and not outcome.truncated
    # NOCUS has fabric type/colour properties, so the default-only set is smaller (first valid colour each)
    assert len(generator.generate(["NOCUS"], currency="EUR", price_date="2026-11-02").skus) == 49
    first = outcome.skus[0]
    assert first.final_article == "NOCUS1 1HA01" and first.price == D("162.00") and first.currency == "EUR"
    target = tmp_path / "nocus.obx"
    summary = export_obx(outcome.skus, target, manufacturer_id="HM", price_date="2026-11-02")
    assert summary.ok and summary.exported == 2181
    assert "162" in target.read_text(encoding="utf-8")


# ============================= how the two price sources combine (OCD 4.3 spec 2.17 and 3.1-3.3)
# Own-article rows (unconditioned or keyed by an assigned $VARCOND) and joker ``*`` rows are not alternatives:
# the levels B, X, D are accumulated, and the joker only supplies an X/D key the article has no row for.
# Spec-derived behaviour; the real-data evidence is the Dalby / Layout Studio / NOCUS tests above.
def _row(article, key, level, value, *, currency="EUR", start="20260101", end="99991231", ptype="S"):
    return PriceRow(article=article, var_cond=key, level=level, value=D(value), currency=currency,
                    date_from=start, date_to=end, price_type=ptype)


def test_own_base_and_joker_extra_charge_both_contribute():
    calc = PriceCalculator([_row("A", "", "B", 100), _row("*", "SURCH", "X", 25)])
    result = calc.price("A", ["SURCH"], price_date="2026-11-02", currency="EUR")
    assert result.total == D("125.00") and [c.level for c in result.components] == ["B", "X"]


def test_own_row_for_a_key_shadows_the_joker_row():
    calc = PriceCalculator([_row("A", "", "B", 100), _row("A", "SURCH", "X", 10), _row("*", "SURCH", "X", 25)])
    assert calc.price("A", ["SURCH"], price_date="2026-11-02", currency="EUR").total == D("110.00")


def test_a_joker_row_is_never_a_base_price():
    calc = PriceCalculator([_row("A", "", "B", 100, end="20260101"), _row("*", "B", "B", 500), _row("*", "S", "X", 5)])
    result = calc.price("A", ["B", "S"], price_date="2026-11-02", currency="EUR")
    assert result.total is None            # A has a base row, expired; neither the joker B nor the X rescues it


def test_extra_charges_never_stand_in_for_an_inapplicable_base_price():
    calc = PriceCalculator([_row("A", "", "B", 100, currency="GBP"), _row("*", "SURCH", "X", 25)])
    result = calc.price("A", ["SURCH"], price_date="2026-11-02", currency="EUR")
    assert result.total is None
    assert any(d.code == dg.NO_BASE_PRICE for d in result.diagnostics)


def test_sales_and_purchase_prices_are_separate_lookups():
    calc = PriceCalculator([_row("A", "", "B", 100), _row("A", "", "B", 60, ptype="P")])
    assert calc.price("A", price_date="2026-11-02", currency="EUR").total == D("100.00")
    assert calc.price("A", price_date="2026-11-02", currency="EUR", price_type="P").total == D("60.00")
