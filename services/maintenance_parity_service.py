"""Maintenance-only semantic PDM Snapshot ↔ reference MDB parity checks.

The parity engine is deliberately read-only. It compares the PDM snapshot with
a manually authored/reference MDB by importing the MDB through the existing
MdbReverseEngineeringService and normalizing both sides into semantic keys.
It never changes either source.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Callable

from models.snapshot import Snapshot
from models.maintenance_snapshot import MaintenanceSnapshot


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


class MaintenanceParityService:
    """Compare semantic PDM Snapshot data with an existing OCD MDB."""

    def __init__(self, context) -> None:
        self.context = context

    def compare(
        self,
        maintenance_snapshot: MaintenanceSnapshot,
        mdb_path: str,
        *,
        progress: Callable[[str], None] | None = None,
    ) -> ParityReport:
        if maintenance_snapshot is None or maintenance_snapshot.pdm_snapshot is None:
            raise ValueError("A Maintenance PDM snapshot is required.")
        pdm_snapshot = maintenance_snapshot.pdm_snapshot
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
            ("Articles", self._maintenance_article_keys(maintenance_snapshot), self._article_keys(mdb_snapshot)),
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
            ("Prices", self._maintenance_prices(maintenance_snapshot), self._mdb_prices(mdb_data, mdb_snapshot)),
        )

        for domain, expected, actual in comparisons:
            report_progress(f"Comparing {domain}...")
            self._compare_domain(report, domain, expected, actual)

        return report


    def compare_loaded(
        self,
        maintenance_snapshot: MaintenanceSnapshot,
        *,
        progress: Callable[[str], None] | None = None,
    ) -> ParityReport:
        """Compare the loaded Maintenance PDM scope directly with its released MDB snapshot."""
        if maintenance_snapshot is None or maintenance_snapshot.pdm_snapshot is None:
            raise ValueError("A Maintenance PDM snapshot is required.")
        if maintenance_snapshot.repository_snapshot is None:
            raise ValueError("A released MDB repository snapshot is required.")
        if not maintenance_snapshot.alignment.is_aligned:
            raise ValueError("Maintenance article alignment must be complete before comparison.")

        def report_progress(message: str) -> None:
            if progress:
                progress(message)

        report = ParityReport()
        pdm_snapshot = maintenance_snapshot.pdm_snapshot
        mdb_snapshot = maintenance_snapshot.repository_snapshot
        comparisons = (
            ("Articles", self._maintenance_article_keys(maintenance_snapshot), self._article_keys(mdb_snapshot)),
            ("Properties", self._properties(pdm_snapshot), self._properties(mdb_snapshot)),
            ("Property Values", self._property_values(pdm_snapshot), self._property_values(mdb_snapshot)),
            ("Options", self._options(pdm_snapshot), self._options(mdb_snapshot)),
            ("Option Values", self._option_values(pdm_snapshot), self._option_values(mdb_snapshot)),
            ("Price Lists", self._price_lists(pdm_snapshot), self._price_lists(mdb_snapshot)),
            ("Prices", self._maintenance_prices(maintenance_snapshot), self._prices(mdb_snapshot)),
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
    def _article_keys(snapshot: Snapshot) -> dict[str, str]:
        """Article identity-only map used when Maintenance aligns to MDB bases."""
        return {
            _norm(a.code): ""
            for a in snapshot.articles
            if a.code
        }

    @classmethod
    def _maintenance_article_keys(cls, state: MaintenanceSnapshot) -> dict[str, str]:
        """Collapse aligned PDM variants onto released MDB base identities."""
        snapshot = state.pdm_snapshot
        if snapshot is None:
            return {}
        if state.alignment.status not in {"ALIGNED", "PARTIAL"}:
            return cls._article_keys(snapshot)
        return {
            _norm(row.base_code): ""
            for row in state.alignment.relations
            if row.base_code.strip()
        }

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
        return _semantic_prices(snapshot.price_records, snapshot.price_lists)

    def _maintenance_prices(self, state: MaintenanceSnapshot) -> dict[str, str]:
        """Normalize Maintenance price article identity through MDB alignment."""
        snapshot = state.pdm_snapshot
        if snapshot is None:
            return {}
        if state.alignment.status not in {"ALIGNED", "PARTIAL"}:
            return self._prices(snapshot)
        if not state.alignment.relations:
            return self._prices(snapshot)

        code_to_base = {
            _norm(row.pdm_article_code): row.base_code
            for row in state.alignment.relations
            if row.pdm_article_code.strip() and row.base_code.strip()
        }
        records = [
            replace(
                record,
                article_code=code_to_base.get(
                    _norm(str(record.article_code or "")),
                    record.article_code,
                ),
            )
            for record in snapshot.price_records
        ]
        return _semantic_prices(records, snapshot.price_lists)


    @staticmethod
    def _mdb_prices(data, snapshot: Snapshot) -> dict[str, str]:
        """Compare MDB prices using the referenced PriceList's business identity."""
        price_lists_by_id = {
            _source_id(price_list.id): price_list
            for price_list in snapshot.price_lists
            if price_list.id
        }

        # import_snapshot preserves table row order, so normalized records can
        # be paired with the raw rows that contain the numeric PriceList ID.
        article_rows = list(data.rows("tCOMd_Price"))
        global_rows = list(data.rows("tCOMd_GlobalPrice"))
        imported_records = list(snapshot.price_records)
        article_records = imported_records[:len(article_rows)]
        global_records = imported_records[len(article_rows):len(article_rows) + len(global_rows)]

        out: dict[str, str] = {}
        for row, record in zip(article_rows, article_records):
            price_list = price_lists_by_id.get(_source_id(row.get("com_PriceListID")))
            out[_price_identity(record, price_list)] = _pack(
                record.value, record.valid_from, record.valid_to, record.currency
            )

        for row, record in zip(global_rows, global_records):
            price_list = price_lists_by_id.get(_source_id(row.get("com_PriceListID")))
            out[_price_identity(record, price_list)] = _pack(
                record.value, record.valid_from, record.valid_to, record.currency
            )
        return out


def _norm(value: Any) -> str:
    return str(value or "").strip().casefold()


def _pack(*values: Any) -> str:
    return " | ".join(_norm(v) for v in values)


def _source_id(value: Any) -> str:
    """Normalize Access integer ids such as 125.0 to 125."""
    text = str(value or "").strip()
    if text.endswith(".0"):
        try:
            return str(int(float(text)))
        except (TypeError, ValueError):
            pass
    return text


def _price_list_key(price_list) -> str:
    if price_list is None:
        return "UNRESOLVED"
    return "|".join(
        (
            _norm(price_list.label or price_list.id),
            _norm(price_list.currency),
            _norm(price_list.date_from),
            _norm(price_list.date_to),
        )
    )


def _resolve_price_list(record, price_lists):
    currency = _norm(record.currency)
    exact = [
        price_list
        for price_list in price_lists
        if _norm(price_list.currency) == currency
        and _norm(price_list.date_from) == _norm(record.valid_from)
        and _norm(price_list.date_to) == _norm(record.valid_to)
    ]
    if len(exact) == 1:
        return exact[0]

    contained = [
        price_list
        for price_list in price_lists
        if _norm(price_list.currency) == currency
        and (not record.valid_from or not price_list.date_from or _norm(record.valid_from) >= _norm(price_list.date_from))
        and (not record.valid_to or not price_list.date_to or _norm(record.valid_to) <= _norm(price_list.date_to))
    ]
    if len(contained) == 1:
        return contained[0]
    return None


def _price_identity(record, price_list=None) -> str:
    list_key = _price_list_key(price_list)
    if list_key == "UNRESOLVED" and record.currency:
        list_key = f"UNRESOLVED|{_norm(record.currency)}|{_norm(record.valid_from)}|{_norm(record.valid_to)}"
    return "|".join(
        (
            "G" if record.is_global else "A",
            _norm(record.article_code),
            _norm(record.variant_condition),
            _norm(record.level),
            list_key,
        )
    )


def _semantic_prices(records, price_lists) -> dict[str, str]:
    out: dict[str, str] = {}
    for record in records:
        price_list = _resolve_price_list(record, price_lists)
        out[_price_identity(record, price_list)] = _pack(
            record.value, record.valid_from, record.valid_to, record.currency
        )
    return out
