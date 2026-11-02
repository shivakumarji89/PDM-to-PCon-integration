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


@dataclass
class KeyLookup:
    """One (level, variant-condition) lookup and what became of its candidate rows."""
    level: str
    key: str                          # '' = unconditioned
    candidates: int = 0               # rows of the article (or joker) for this level and key
    joker: bool = False               # the candidates came from the joker article '*'
    after_fixed: int = 0              # base prices must be fixed amounts
    after_date: int = 0
    after_scale: int = 0
    after_currency: int = 0
    chosen: PriceRow | None = None
    reason: str = ""                  # why no row was usable ('' when one was chosen)


@dataclass
class PriceDiagnosis:
    """What the price table holds for one article and how a lookup treated it (never the whole table)."""
    article: str
    price_type: str
    price_date: str
    currency: str
    quantity: int
    table_rows: int = 0               # rows in the whole price table
    article_rows: int = 0             # rows keyed by the article
    joker_rows: int = 0               # rows keyed by '*'
    types: tuple[str, ...] = ()       # price types present for the article (own and joker rows)
    levels: tuple[str, ...] = ()      # price levels present for the requested type (own and joker rows)
    currencies: tuple[str, ...] = ()  # currencies present for the requested type (own and joker rows)
    date_windows: tuple[str, ...] = ()  # "<from>-<to>" windows of the requested type (own and joker rows)
    expected_keys: tuple[str, ...] = ()
    has_base_rows: bool = False       # the article itself holds B rows of this type (the joker never does)
    lookups: list[KeyLookup] = field(default_factory=list)

    def lines(self) -> list[str]:
        out = [
            f"article {self.article!r}: {self.article_rows} row(s) of {self.table_rows} in the price table"
            f" ({self.joker_rows} joker '*' row(s))",
            f"price types {list(self.types)}; for type {self.price_type}: levels {list(self.levels)}, "
            f"currencies {list(self.currencies)}, {len(self.date_windows)} date window(s)",
            f"lookup: date {self.price_date}, currency {self.currency}, quantity {self.quantity}; "
            f"keys {list(self.expected_keys)}",
        ]
        empty = []
        for look in self.lookups:
            label = f"{look.level}:{look.key or '(none)'}"
            if not look.candidates and not (look.level == "B" and not look.key):
                empty.append(label)                      # nothing to filter: listed once, below
            elif look.chosen is not None:
                out.append(f"  {label}: {look.chosen.value} {look.chosen.currency} "
                           f"({look.chosen.date_from}-{look.chosen.date_to})"
                           f"{' [joker *]' if look.joker else ''}")
            else:
                out.append(f"  {label}: {look.candidates} candidate(s) -> fixed {look.after_fixed} -> date "
                           f"{look.after_date} -> scale {look.after_scale} -> currency {look.after_currency}; "
                           f"{look.reason}")
        if empty:
            out.append(f"  no row of any kind for: {', '.join(empty)}")
        return out


class PriceCalculator:
    def __init__(self, rows: Iterable[PriceRow], rounding: Mapping[str, Sequence[RoundingStep]] | None = None,
                 *, currency_fallback: bool = False) -> None:
        self._by_article: dict[str, list[PriceRow]] = {}
        for row in rows:
            self._by_article.setdefault(row.article, []).append(row)
        self._rounding = {k: sorted(v, key=lambda s: s.number) for k, v in (rounding or {}).items()}
        self._currency_fallback = currency_fallback

    # ------------------------------------------------------------------ row choice (3.3)
    def _narrow(self, rows: list[PriceRow], *, level: str, price_date: str, currency: str, quantity: int):
        """The 3.3 filters in order; returns the surviving rows after each stage."""
        fixed = [r for r in rows if r.is_fix] if level == "B" else list(rows)   # 3.3(1)
        dated = [r for r in fixed if r.date_from <= price_date <= r.date_to]
        scaled = [r for r in dated if r.scale_quantity <= quantity]
        in_currency = [r for r in scaled if r.currency == currency or not r.is_fix and not r.currency]
        if not in_currency and self._currency_fallback:
            in_currency = scaled
        return fixed, dated, scaled, in_currency

    @staticmethod
    def _rejection(rows, fixed, dated, scaled, in_currency, *, level, price_date, currency, quantity) -> str:
        """The first filter that emptied the candidate list, in words an author can act on."""
        if not rows:
            return f"no {level}-level row exists for this key (any date or currency)"
        if not fixed:
            return f"all {len(rows)} {level}-level row(s) are percentages; a base price must be a fixed amount"
        if not dated:
            windows = sorted({f"{r.date_from}-{r.date_to}" for r in fixed})
            return f"no row is valid on {price_date}; valid windows: {', '.join(windows[:4])}" \
                   + (" ..." if len(windows) > 4 else "")
        if not scaled:
            return f"no row has a scale quantity of at most {quantity}"
        available = sorted({r.currency or "(none)" for r in scaled})
        return f"no row in {currency} on {price_date}; currencies valid then: {', '.join(available)}"

    def _choose(self, in_currency: list[PriceRow], *, result: PriceResult, label: str) -> PriceRow:
        """Most appropriate of the rows that survived every 3.3 filter."""
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

    @staticmethod
    def _candidates(own: list[PriceRow], joker: list[PriceRow], level: str, key: str) -> tuple[list[PriceRow], bool]:
        rows = [r for r in own if r.level == level and r.var_cond == key]
        if not rows and level in ("X", "D") and key:
            # joker article: only if the article has no row of its own for this key
            rows = [r for r in joker if r.level == level and r.var_cond == key]
            return rows, bool(rows)
        return rows, False

    def _lookup(self, own: list[PriceRow], joker: list[PriceRow], level: str, key: str, *, price_date: str,
                currency: str, quantity: int, result: PriceResult) -> KeyLookup:
        rows, from_joker = self._candidates(own, joker, level, key)
        fixed, dated, scaled, in_currency = self._narrow(rows, level=level, price_date=price_date,
                                                         currency=currency, quantity=quantity)
        look = KeyLookup(level, key, len(rows), from_joker, len(fixed), len(dated), len(scaled), len(in_currency))
        if in_currency:
            look.chosen = self._choose(in_currency, result=result, label=f"{level}:{key or '-'}")
        else:
            look.reason = self._rejection(rows, fixed, dated, scaled, in_currency, level=level,
                                          price_date=price_date, currency=currency, quantity=quantity)
        return look

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

        has_base = any(r.level == "B" for r in own)
        total = Decimal(0)
        base: Decimal | None = None                  # sum of the level-B items found (keyed or not)
        base_misses: list[tuple[str, KeyLookup]] = []
        for level in ("B", "X", "D"):
            for key in keys:
                look = self._lookup(own, joker, level, key, price_date=date, currency=cur, quantity=quantity,
                                    result=result)
                row = look.chosen
                if row is None:
                    if level == "B":
                        base_misses.append((key, look))
                    if look.candidates:
                        result.diagnostics.append(dg.Diagnostic(
                            dg.NO_PRICE_FOR_KEY,
                            f"no usable {level} price row for key {key or '(none)'} on {date} in {cur}: "
                            f"{look.reason}", dg.Severity.WARNING, article=article, value=key))
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
                if level == "B":
                    base = (base or Decimal(0)) + amount
                result.components.append(PriceComponent(key, level, amount, row, factor))
        if base is not None:
            result.base, result.total = base, total
            return result
        if has_base:
            # The article has base prices, but none applies to this configuration/date/currency.
            key, look = next(((k, lk) for k, lk in base_misses if lk.candidates), base_misses[0])
            reason = look.reason
            if not look.candidates:
                held = sorted({r.var_cond or "(none)" for r in own if r.level == "B"})
                shown = f"({', '.join(held[:5])}{' ...' if len(held) > 5 else ''})"
                assigned = [k for k in keys if k]
                if assigned:
                    reason = (f"the price relations assigned {', '.join(assigned[:3])}"
                              f"{' ...' if len(assigned) > 3 else ''}, but the article's base prices are keyed by "
                              f"other variant conditions {shown}")
                else:
                    reason = ("the article's base prices are keyed by other variant conditions "
                              f"{shown} and the price relations assigned none of them")
            result.diagnostics.append(dg.Diagnostic(
                dg.NO_BASE_PRICE, f"no usable B price row for key {key or '(none)'} on {date} in {cur}: {reason}",
                dg.Severity.ERROR, article=article, value=key))
            return result
        # The repository gives this article no base price at all (typical of programs that price every
        # configuration through variant conditions). Only real rows are summed, and only when at least one
        # matched and the sum is not zero.
        if result.components and total != 0:
            result.total = total
            result.diagnostics.append(dg.Diagnostic(
                dg.PRICE_FROM_EXTRA_CHARGES,
                "the repository has no base (B) price row for this article; the price is the sum of "
                f"{len(result.components)} extra-charge (X) item(s)", dg.Severity.INFO, article=article))
            return result
        reason = ("no extra-charge (X) item matched the configuration's variant conditions"
                  if not result.components else "the matching extra-charge items sum to zero")
        result.diagnostics.append(dg.Diagnostic(
            dg.NO_BASE_PRICE,
            f"no usable price on {date} in {cur}: the repository has no base (B) row for this article and {reason}",
            dg.Severity.ERROR, article=article))
        return result

    def diagnose(self, article: str, varconds: Sequence[str] = (), *, price_date: str, currency: str,
                 price_type: str = "S", quantity: int = 1) -> PriceDiagnosis:
        """The same lookups as :meth:`price`, with every stage's survivor count and the rejection reason."""
        if not currency.strip() or not ymd(price_date):
            raise ValueError("price_date and currency are required for price determination")
        date, cur, ptype = ymd(price_date), currency.strip().upper(), price_type.upper()
        everything = self._by_article.get(article, [])
        joker_all = self._by_article.get("*", [])
        own = [r for r in everything if r.price_type == ptype]
        joker = [r for r in joker_all if r.price_type == ptype]
        keys = [""] + [k.upper() for k in dict.fromkeys(varconds) if k]
        scratch = PriceResult(article, cur, date)
        diagnosis = PriceDiagnosis(
            article=article, price_type=ptype, price_date=date, currency=cur, quantity=quantity,
            table_rows=sum(len(v) for v in self._by_article.values()), article_rows=len(everything),
            joker_rows=len(joker_all), types=tuple(sorted({r.price_type for r in everything + joker_all})),
            levels=tuple(sorted({r.level for r in own + joker})),
            currencies=tuple(sorted({r.currency for r in own + joker} - {""})),
            date_windows=tuple(sorted({f"{r.date_from}-{r.date_to}" for r in own + joker})),
            expected_keys=tuple(keys), has_base_rows=any(r.level == "B" for r in own))
        for level in ("B", "X", "D"):
            for key in keys:
                diagnosis.lookups.append(self._lookup(own, joker, level, key, price_date=date, currency=cur,
                                                      quantity=quantity, result=scratch))
        return diagnosis
