"""OCD price determination (spec section 3) on ``Decimal``.

A configuration's price is accumulated level by level - base (``B``), extra
charges (``X``), discounts (``D``) - from the price table. For each level the
relevant items are the article's rows *without* a variant condition plus the
rows whose variant condition was assigned to ``$VARCOND`` by the price
relations (see ``varcond_engine``). For each item the most appropriate row is
chosen by 3.3: valid on the price date, requested currency, scale quantity not
above the ordered quantity, latest ``DateFrom`` wins.

Deliberate deviations from the text, both safety choices for OBX generation:

* a price in a *different currency* is never substituted for a missing one
  (spec 3.3 would fall back to all currencies); the item is reported instead.
  Pass ``currency_fallback=True`` to follow the text.
* an ambiguous row choice (several rows, same ``DateFrom``) is reported with
  ``AMBIGUOUS_PRICE_WINDOW`` rather than silently picking one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_CEILING, ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal, localcontext
from typing import Iterable, Mapping, Sequence

from services.ocd_engine import diagnostics as dg

_CENT = Decimal("0.01")


def ymd(value: str) -> str:
    """``YYYYMMDD`` digits of a date written in any common layout."""
    digits = "".join(ch for ch in str(value or "") if ch.isdigit())
    return digits[:8]


@dataclass(frozen=True)
class PriceRow:
    article: str
    var_cond: str = ""
    price_type: str = "S"
    level: str = "B"                  # B / X / D
    rule: str = ""
    text_id: str = ""
    value: Decimal = Decimal(0)
    is_fix: bool = True
    currency: str = ""
    date_from: str = ""
    date_to: str = ""
    scale_quantity: int = 1
    rounding_id: str = ""

    @classmethod
    def from_csv(cls, row: Mapping[str, str]) -> "PriceRow":
        def number(text: str, default: str = "0") -> Decimal:
            return Decimal(str(text).strip() or default)

        return cls(
            article=row["article_nr"], var_cond=row.get("var_cond", "").strip().upper(),
            price_type=(row.get("price_type") or "S").upper(), level=(row.get("price_level") or "B").upper(),
            rule=row.get("price_rule", ""), text_id=row.get("price_textnr", ""),
            value=number(row.get("price", "0")), is_fix=row.get("is_fix", "1").strip() not in {"0", ""},
            currency=row.get("currency", "").upper(), date_from=ymd(row.get("date_from", "")) or "00000000",
            date_to=ymd(row.get("date_to", "")) or "99991231",
            scale_quantity=int(number(row.get("scale_quantity", "1"), "1")),
            rounding_id=row.get("rounding_id", ""),
        )


@dataclass(frozen=True)
class RoundingStep:
    number: int
    minimum: Decimal | None
    maximum: Decimal | None
    method: str
    precision: Decimal
    add_before: Decimal
    add_after: Decimal

    @classmethod
    def from_csv(cls, row: Mapping[str, str]) -> "RoundingStep":
        def optional(text: str) -> Decimal | None:
            return Decimal(text.strip()) if text.strip() else None

        return cls(
            number=int(row.get("nr", "0") or 0), minimum=optional(row.get("min", "")),
            maximum=optional(row.get("max", "")), method=row.get("type", "COM").strip().upper(),
            precision=Decimal(row.get("precision", "0.01").strip() or "0.01"),
            add_before=Decimal(row.get("add_before", "0").strip() or "0"),
            add_after=Decimal(row.get("add_after", "0").strip() or "0"),
        )


_METHODS = {"DOWN": ROUND_DOWN, "UP": ROUND_CEILING, "COM": ROUND_HALF_UP, "ECOM": ROUND_HALF_EVEN}


def _round_step(amount: Decimal, step: RoundingStep) -> Decimal:
    """Apply one rounding rule line (spec 2.18). Outside [min, max) the amount is untouched."""
    if (step.minimum is not None and amount < step.minimum) or \
            (step.maximum is not None and amount >= step.maximum):
        return amount
    amount += step.add_before
    if step.precision > 0:
        units = (amount / step.precision).quantize(Decimal(1), rounding=_METHODS.get(step.method, ROUND_HALF_UP))
        amount = units * step.precision
    return amount + step.add_after


@dataclass(frozen=True)
class PriceComponent:
    key: str                          # variant condition ('' = unconditioned)
    level: str
    amount: Decimal
    row: PriceRow
    factor: Decimal = Decimal(1)


@dataclass
class PriceResult:
    article: str
    currency: str
    price_date: str
    total: Decimal | None = None
    base: Decimal | None = None
    components: list[PriceComponent] = field(default_factory=list)
    diagnostics: list[dg.Diagnostic] = field(default_factory=list)

    @property
    def resolved(self) -> bool:
        return self.total is not None

    def percentages(self) -> list[tuple[str, Decimal]]:
        """Each component as a percentage of the total (the OBX ``priceComponents`` form)."""
        if not self.total or all(c.level == "B" for c in self.components):
            return []                        # reference files show no components for a base-only price
        with localcontext() as ctx:
            ctx.prec = 34
            return [(c.key, c.amount / self.total * 100) for c in self.components]


class PriceCalculator:
    def __init__(self, rows: Iterable[PriceRow], rounding: Mapping[str, Sequence[RoundingStep]] | None = None,
                 *, currency_fallback: bool = False) -> None:
        self._by_article: dict[str, list[PriceRow]] = {}
        for row in rows:
            self._by_article.setdefault(row.article, []).append(row)
        self._rounding = {k: sorted(v, key=lambda s: s.number) for k, v in (rounding or {}).items()}
        self._currency_fallback = currency_fallback

    # ------------------------------------------------------------------ row choice (3.3)
    def _choose(self, rows: list[PriceRow], *, price_date: str, currency: str, quantity: int,
                result: PriceResult, label: str) -> PriceRow | None:
        valid = [r for r in rows if r.date_from <= price_date <= r.date_to and r.scale_quantity <= quantity]
        in_currency = [r for r in valid if r.currency == currency or not r.is_fix and not r.currency]
        if not in_currency and self._currency_fallback:
            in_currency = valid
        if not in_currency:
            return None
        latest = max(r.date_from for r in in_currency)
        best = [r for r in in_currency if r.date_from == latest]
        # largest applicable scale quantity is the most specific entry
        top_scale = max(r.scale_quantity for r in best)
        best = [r for r in best if r.scale_quantity == top_scale]
        if len({(r.value, r.is_fix, r.currency) for r in best}) > 1:
            result.diagnostics.append(dg.Diagnostic(
                dg.AMBIGUOUS_PRICE_WINDOW, f"{len(best)} different price rows valid for {label}",
                dg.Severity.WARNING, article=result.article, value=label))
        return best[0]

    def _round(self, amount: Decimal, row: PriceRow) -> Decimal:
        steps = self._rounding.get(row.rounding_id) if row.rounding_id else None
        if steps:
            for step in steps:
                amount = _round_step(amount, step)
            return amount
        return amount.quantize(_CENT, rounding=ROUND_HALF_UP)       # standard commercial rounding (3.1)

    # ------------------------------------------------------------------ public
    def price(self, article: str, varconds: Sequence[str] = (), *, price_date: str, currency: str,
              price_type: str = "S", quantity: int = 1,
              factors: Mapping[str, float] | None = None) -> PriceResult:
        """Total price of one configuration. ``price_date`` and ``currency`` are required."""
        if not currency.strip() or not ymd(price_date):
            raise ValueError("price_date and currency are required for price determination")
        date, cur, ptype = ymd(price_date), currency.strip().upper(), price_type.upper()
        result = PriceResult(article, cur, date)
        own = [r for r in self._by_article.get(article, []) if r.price_type == ptype]
        joker = [r for r in self._by_article.get("*", []) if r.price_type == ptype]
        keys = [""] + [k.upper() for k in dict.fromkeys(varconds) if k]
        factors = {k.upper(): Decimal(str(v)) for k, v in (factors or {}).items()}

        total = Decimal(0)
        base: Decimal | None = None
        for level in ("B", "X", "D"):
            for key in keys:
                rows = [r for r in own if r.level == level and r.var_cond == key]
                if not rows and level in ("X", "D") and key:
                    # joker article: only if the article has no row of its own for this key
                    rows = [r for r in joker if r.level == level and r.var_cond == key]
                label = f"{level}:{key or '-'}"
                if level == "B":
                    rows = [r for r in rows if r.is_fix]          # 3.3(1): a base price must be fixed
                row = self._choose(rows, price_date=date, currency=cur, quantity=quantity,
                                   result=result, label=label) if rows else None
                if row is None:
                    if rows or (level == "B" and key == ""):
                        code = dg.NO_BASE_PRICE if level == "B" and key == "" else dg.NO_PRICE_FOR_KEY
                        result.diagnostics.append(dg.Diagnostic(
                            code, f"no usable {level} price row for key {key or '(none)'} on {date} in {cur}",
                            dg.Severity.ERROR if code == dg.NO_BASE_PRICE else dg.Severity.WARNING,
                            article=article, value=key))
                    elif level in ("X", "D") and key:
                        result.diagnostics.append(dg.Diagnostic(
                            dg.NO_PRICE_FOR_KEY, f"variant condition {key} has no price row",
                            dg.Severity.INFO, article=article, value=key))
                    continue
                if row.is_fix:
                    raw = row.value
                elif level == "D" and row.rule == "2":
                    raw = total * row.value / 100                  # percentage of the accumulated price
                else:
                    raw = (base if base is not None else total) * row.value / 100
                factor = factors.get(key, Decimal(1)) if key else Decimal(1)
                amount = self._round(raw * factor, row)
                if level == "D":
                    # No reference data exercises discounts: a percentage is taken as a
                    # reduction, a fixed amount is added as stored. Flagged, not claimed.
                    if not row.is_fix and amount > 0:
                        amount = -amount
                    result.diagnostics.append(dg.Diagnostic(
                        dg.UNSUPPORTED_PRICE_FEATURE,
                        "discount (level D) applied by the specification text only; unverified against data",
                        dg.Severity.WARNING, article=article, value=key))
                total += amount
                if level == "B" and key == "":
                    base = amount
                result.components.append(PriceComponent(key, level, amount, row, factor))
        if base is None:
            return result                                          # NO_BASE_PRICE already reported
        result.base, result.total = base, total
        return result
