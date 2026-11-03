"""The price-relevant state of one resolved article configuration.

``ConfigurationEngine.finalize`` evaluates the relations once and yields the variant conditions
(``$VARCOND``) and pricing factors (``$SET_PRICING_FACTOR``) of a valid configuration. Both consumers -
the standalone generator and the Snapshot permutation/price services - carry exactly that state to
``PriceCalculator.price_resolved``; nothing re-derives it from property or value names.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class ResolvedConfiguration:
    article: str
    varconds: tuple[str, ...] = ()
    pricing_factors: tuple[tuple[str, float], ...] = ()

    @classmethod
    def of(cls, article: str, varconds: Sequence[str] = (),
           pricing_factors: Mapping[str, float] | Sequence[tuple[str, float]] = ()) -> "ResolvedConfiguration":
        """Normalise exactly as ``PriceCalculator.price`` reads it: upper-case, de-duplicated, empties dropped."""
        items = pricing_factors.items() if isinstance(pricing_factors, Mapping) else pricing_factors
        return cls(
            article,
            tuple(dict.fromkeys(str(k).upper() for k in varconds if k)),
            tuple(sorted((str(k).upper(), float(v)) for k, v in items)),
        )

    @property
    def price_key(self) -> tuple:
        """Configurations with the same key are priced identically for a fixed date, currency and quantity."""
        return self.article, self.varconds, self.pricing_factors
