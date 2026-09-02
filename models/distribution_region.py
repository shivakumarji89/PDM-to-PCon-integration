"""Distribution region (OFML/OCD): a market/currency scope for a package.

A distribution region is a logical partition of a product's commercial data
(prices, market-specific articles) that becomes a directory level in the
repository - ``<manufacturer>/<program>/<REGION>/<version>/db`` - and one row in
the OCD MDB table ``tCOMd_DistributionRegion``.

Regions form a shallow tree: one **master** region (OFML standard code ``ANY``,
parent ``None``) holds the full master data, and market regions (e.g. ``EURO``,
``GBP``, ``NOPRICE``) hang off it. See ``docs/pcon_reference/dsr-3.7_en.md`` [6].
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DistributionRegion:
    """One distribution region.

    ``code`` is the repository directory name and the ``ocd_version.csv`` region
    field (``ANY``/``EURO``/``GBP``/``NOPRICE``). ``parent_code`` is ``None`` for
    the master region and the master's code for market regions.
    """

    code: str
    label: str = ""
    parent_code: str | None = None

    @property
    def is_master(self) -> bool:
        """True for the root/master region (no parent) - the full master data."""
        return self.parent_code is None
