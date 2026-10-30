"""OCD price determination: base + conditional increments, dates, currency, rounding."""
from decimal import Decimal

import pytest

from services.ocd_engine import diagnostics as dg
from services.ocd_engine.pricing import PriceCalculator, PriceRow, RoundingStep, ymd

D = Decimal


def row(var_cond="", level="B", value="100", currency="EUR", date_from="20250101", date_to="99991231",
        article="A1", is_fix=True, **kw):
    return PriceRow(article=article, var_cond=var_cond, level=level, value=D(value), currency=currency,
                    date_from=date_from, date_to=date_to, is_fix=is_fix, **kw)


def price(rows, varconds=(), **kw):
    kw.setdefault("price_date", "20260101")
    kw.setdefault("currency", "EUR")
    return PriceCalculator(rows, kw.pop("rounding", None)).price("A1", varconds, **kw)


def test_base_plus_one_conditional_increment_per_varcond_key():
    rows = [row(), row("6699=OAK", "X", "50"), row("6695=Q75", "X", "25.5")]
    result = price(rows, ["6699=OAK", "6695=Q75"])
    assert result.total == D("175.50") and result.base == D("100")
    assert [(c.key, c.amount) for c in result.components] == [("", D("100.00")), ("6699=OAK", D("50.00")), ("6695=Q75", D("25.50"))]


def test_key_without_price_row_adds_no_component():
    result = price([row(), row("K1", "X", "10")], ["K1", "NOROW"])
    assert result.total == D("110.00") and len(result.components) == 2
    assert not any(d.severity is dg.Severity.ERROR for d in result.diagnostics)


def test_unconditioned_extra_charge_always_applies():
    result = price([row(), row("", "X", "7")], [])
    assert result.total == D("107.00")


def test_effective_date_window_and_latest_date_from_wins():
    rows = [row(value="100", date_from="20240101", date_to="20251231"),
            row(value="110", date_from="20260101"), row(value="105", date_from="20250601", date_to="20251231")]
    assert price(rows, price_date="20250301").total == D("100.00")
    assert price(rows, price_date="20250801").total == D("105.00")        # latest DateFrom of the valid rows
    assert price(rows, price_date="20260301").total == D("110.00")
    assert price(rows, price_date="20230101").total is None               # outside every window


def test_price_date_accepts_any_date_layout():
    assert ymd("2025-10-27") == "20251027" and ymd("20251027") == "20251027"
    assert price([row(date_from="20251027")], price_date="2025-10-27").total == D("100.00")


def test_currency_is_never_substituted_by_default():
    result = price([row(currency="GBP")], currency="EUR")
    assert result.total is None
    assert any(d.code == dg.NO_BASE_PRICE for d in result.diagnostics)


def test_currency_fallback_follows_spec_text_when_enabled():
    calc = PriceCalculator([row(currency="GBP")], currency_fallback=True)
    assert calc.price("A1", price_date="20260101", currency="EUR").total == D("100.00")


def test_missing_base_price_means_no_total_and_error_diagnostic():
    result = price([row("K", "X", "5")], ["K"])
    assert result.total is None and result.diagnostics[0].code == dg.NO_BASE_PRICE
    assert result.diagnostics[0].severity is dg.Severity.ERROR


def test_percentage_base_is_ignored_and_percentage_extra_is_of_base():
    rows = [row(value="10", is_fix=False), row(value="200"), row("K", "X", "10", is_fix=False, currency="")]
    result = price(rows, ["K"])
    assert result.base == D("200.00") and result.total == D("220.00")


def test_standard_rounding_is_commercial_two_digits():
    rows = [row(value="10"), row("K", "X", "0.005")]
    assert price(rows, ["K"]).total == D("10.01")                         # X.5 rounds up
    assert price([row(value="10"), row("K", "X", "0.004")], ["K"]).total == D("10.00")


def test_rounding_rule_table_replaces_standard_rounding():
    steps = {"R1": [RoundingStep(1, D("0"), D("10"), "COM", D("0.1"), D(0), D(0)),
                    RoundingStep(2, D("10"), D("100"), "COM", D("0.5"), D(0), D(0)),
                    RoundingStep(3, D("100"), None, "UP", D("1"), D(0), D("-0.01"))]}
    for raw, expected in [("7.26", "7.30"), ("12.3", "12.50"), ("101.2", "101.99")]:
        assert price([row(value=raw, rounding_id="R1")], rounding=steps).total == D(expected)


def test_rounding_methods_down_and_ecom():
    down = {"D": [RoundingStep(1, None, None, "DOWN", D("1"), D(0), D(0))]}
    ecom = {"E": [RoundingStep(1, None, None, "ECOM", D("1"), D(0), D(0))]}
    assert price([row(value="9.9", rounding_id="D")], rounding=down).total == D("9")
    assert price([row(value="2.5", rounding_id="E")], rounding=ecom).total == D("2")
    assert price([row(value="3.5", rounding_id="E")], rounding=ecom).total == D("4")


def test_scale_price_uses_largest_scale_not_above_quantity():
    rows = [row(value="100"), row(value="90", scale_quantity=10)]
    assert price(rows, quantity=1).total == D("100.00") and price(rows, quantity=12).total == D("90.00")


def test_joker_article_applies_only_without_own_row_for_the_key():
    joker = row("K", "X", "9", article="*")
    assert price([row(), joker], ["K"]).total == D("109.00")
    own = row("K", "X", "4")
    assert price([row(), joker, own], ["K"]).total == D("104.00")


def test_pricing_factor_scales_the_conditional_item():
    result = price([row(), row("K", "X", "10")], ["K"], factors={"k": 1.5})
    assert result.total == D("115.00")


def test_discount_is_computed_but_flagged_unverified():
    rows = [row(), row("", "D", "10", is_fix=False, rule="1", currency="")]
    result = price(rows)
    assert result.total == D("90.00")
    assert any(d.code == dg.UNSUPPORTED_PRICE_FEATURE for d in result.diagnostics)


def test_price_date_and_currency_are_required():
    with pytest.raises(ValueError):
        PriceCalculator([row()]).price("A1", price_date="", currency="EUR")
    with pytest.raises(ValueError):
        PriceCalculator([row()]).price("A1", price_date="20260101", currency=" ")


def test_ambiguous_rows_are_reported():
    rows = [row(value="100"), row(value="101")]
    result = price(rows)
    assert any(d.code == dg.AMBIGUOUS_PRICE_WINDOW for d in result.diagnostics)


def test_components_as_percentages_match_obx_shape():
    result = price([row(value="75"), row("K", "X", "25")], ["K"])
    assert result.percentages() == [("", D("75")), ("K", D("25"))]
    assert price([row()]).percentages() == []                             # base-only: no components


def test_csv_row_conversion_strips_and_upper_cases():
    r = PriceRow.from_csv({"article_nr": "A1", "var_cond": "6695=q75", "price_type": "S", "price_level": "X",
                           "price": " 12.5", "is_fix": "1", "currency": "gbp", "date_from": "20250204",
                           "date_to": "", "scale_quantity": " 1", "rounding_id": ""})
    assert r.var_cond == "6695=Q75" and r.value == D("12.5") and r.currency == "GBP" and r.date_to == "99991231"
