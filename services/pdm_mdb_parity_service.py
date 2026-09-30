"""Semantic PDM Snapshot ↔ reference MDB parity checks.

The parity engine is deliberately read-only. It compares the PDM snapshot with
a manually authored/reference MDB by importing the MDB through the existing
MdbReverseEngineeringService and normalizing both sides into semantic keys.
It never changes either source.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from models.snapshot import Snapshot


MATCH = "MATCH"
MISSING = "MISSING"
EXTRA = "EXTRA"
DIFFERENT = "DIFFERENT"


@dataclass(frozen=True)
class ParityDifference:
    domain: str
    status: str
    key: str
    expected: str = ""
    actual: str = ""
    detail: str = ""


@dataclass
class ParityReport:
    differences: list[ParityDifference] = field(default_factory=list)
    compared: dict[str, int] = field(default_factory=dict)

    @property
    def match_count(self) -> int:
        return sum(1 for d in self.differences if d.status == MATCH)

    @property
    def missing_count(self) -> int:
        return sum(1 for d in self.differences if d.status == MISSING)

    @property
    def extra_count(self) -> int:
        return sum(1 for d in self.differences if d.status == EXTRA)

    @property
    def different_count(self) -> int:
        return sum(1 for d in self.differences if d.status == DIFFERENT)

    @property
    def passed(self) -> bool:
        return not (
            self.missing_count or self.extra_count or self.different_count
        )


class PdmMdbParityService:
    """Compare semantic PDM Snapshot data with an existing OCD MDB."""

    def __init__(self, context) -> None:
        self.context = context

    def compare(
        self,
        pdm_snapshot: Snapshot,
        mdb_path: str,
        *,
        progress: Callable[[str], None] | None = None,
    ) -> ParityReport:
        if pdm_snapshot is None:
            raise ValueError("A PDM snapshot is required.")
        if not mdb_path:
            raise ValueError("An MDB path is required.")

        def report_progress(message: str) -> None:
            if progress:
                progress(message)

        report = ParityReport()
        report_progress("Reading reference MDB...")
        mdb_data = self.context.mdb_reverse_engineering_service.read(
            mdb_path, include_prices=True
        )
        report_progress("Normalizing reference MDB...")
        mdb_snapshot = self.context.mdb_reverse_engineering_service.import_snapshot(
            mdb_data
        )

        comparisons = (
            ("Articles", self._articles(pdm_snapshot), self._articles(mdb_snapshot)),
            ("Properties", self._properties(pdm_snapshot), self._properties(mdb_snapshot)),
            (
                "Property Values",
                self._property_values(pdm_snapshot),
                self._property_values(mdb_snapshot),
            ),
            ("Options", self._options(pdm_snapshot), self._options(mdb_snapshot)),
            (
                "Option Values",
                self._option_values(pdm_snapshot),
                self._option_values(mdb_snapshot),
            ),
            ("Price Lists", self._price_lists(pdm_snapshot), self._price_lists(mdb_snapshot)),
            ("Prices", self._prices(pdm_snapshot), self._prices(mdb_snapshot)),
        )

        for domain, expected, actual in comparisons:
            report_progress(f"Comparing {domain}...")
            self._compare_domain(report, domain, expected, actual)

        return report

    @staticmethod
    def _compare_domain(
        report: ParityReport,
        domain: str,
        expected: dict[str, str],
        actual: dict[str, str],
    ) -> None:
        report.compared[domain] = len(expected)
        for key in sorted(expected.keys() & actual.keys()):
            if expected[key] == actual[key]:
                report.differences.append(
                    ParityDifference(domain, MATCH, key, expected[key], actual[key])
                )
            else:
                report.differences.append(
                    ParityDifference(
                        domain, DIFFERENT, key, expected[key], actual[key],
                        "Normalized values differ",
                    )
                )
        for key in sorted(expected.keys() - actual.keys()):
            report.differences.append(
                ParityDifference(
                    domain, MISSING, key, expected[key], "",
                    "Present in PDM Snapshot but missing in MDB",
                )
            )
        for key in sorted(actual.keys() - expected.keys()):
            report.differences.append(
                ParityDifference(
                    domain, EXTRA, key, "", actual[key],
                    "Present in MDB but missing in PDM Snapshot",
                )
            )

    @staticmethod
    def _articles(snapshot: Snapshot) -> dict[str, str]:
        return {
            _norm(a.code): _pack(a.name, a.description, a.is_super_item)
            for a in snapshot.articles
            if a.code
        }

    @staticmethod
    def _properties(snapshot: Snapshot) -> dict[str, str]:
        return {
            _norm(p.code or p.name): _pack(
                p.name, p.data_type, p.display_order, p.code_width
            )
            for p in snapshot.properties
            if p.code or p.name
        }

    @staticmethod
    def _property_values(snapshot: Snapshot) -> dict[str, str]:
        props = {
            str(p.id): _norm(p.code or p.name)
            for p in snapshot.properties
        }
        return {
            f"{props.get(str(v.property_id), '')}|{_norm(v.code)}":
                _pack(v.value, v.model_suffix, v.display_order)
            for v in snapshot.property_values
            if v.code
        }

    @staticmethod
    def _options(snapshot: Snapshot) -> dict[str, str]:
        return {
            _norm(o.code or o.name): _pack(
                o.name, o.display_order, o.is_fabric
            )
            for o in snapshot.options
            if o.code or o.name
        }

    @staticmethod
    def _option_values(snapshot: Snapshot) -> dict[str, str]:
        options = {
            str(o.id): _norm(o.code or o.name)
            for o in snapshot.options
        }
        return {
            f"{options.get(str(v.option_id), '')}|{_norm(v.code)}":
                _pack(v.value, v.supplier_code, v.display_order)
            for v in snapshot.option_values
            if v.code
        }

    @staticmethod
    def _price_lists(snapshot: Snapshot) -> dict[str, str]:
        return {
            f"{_norm(p.label or p.id)}|{_norm(p.currency)}":
                _pack(p.date_from, p.date_to)
            for p in snapshot.price_lists
            if p.label or p.id
        }

    @staticmethod
    def _prices(snapshot: Snapshot) -> dict[str, str]:
        return {
            _price_key(p): _pack(p.value, p.valid_from, p.valid_to)
            for p in snapshot.price_records
        }


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def _pack(*values: Any) -> str:
    return " | ".join(_norm(v) for v in values)


def _price_key(record) -> str:
    # PriceRecord has no business PriceList id. Include the validity start in
    # the identity so multiple yearly lists for the same article/currency do
    # not collapse into one comparison row.
    return "|".join(
        (
            "G" if record.is_global else "A",
            _norm(record.article_code),
            _norm(record.variant_condition),
            _norm(record.level),
            _norm(record.currency),
            _norm(record.valid_from),
        )
    )
