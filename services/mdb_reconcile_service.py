"""MDB -> XOCD reconciliation engine (the Thinker).

Diffs the exported XOCD package (source of truth) against an imported, possibly
hand-edited MDB, per entity and name-keyed, and classifies every delta
(added / removed / modified) so the user can choose which to fold back. XOCD
stays authoritative; the MDB is a disposable import artifact.

This slice is the schema-agnostic diff core plus the XOCD CSV reader. Mapping the
MDB ``tCOMd_*`` tables to name-keyed rows (resolving autonumber FKs to names)
is layered on top per table as those mappings are verified against a live MDB.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Callable, Sequence

from models.mdb_recon import (
    KIND_ADDED,
    KIND_MODIFIED,
    KIND_REMOVED,
    VERDICT_BLOCKED,
    VERDICT_REVIEW,
    VERDICT_SAFE,
    ReconChange,
    ReconFieldChange,
    ReconReport,
)
from services.base_service import BaseService

_ENCODING = "latin-1"
_DELIM = ";"


class MdbReconcileService(BaseService):
    """Diff an XOCD baseline against an MDB and classify the deltas."""

    def read_xocd_table(
        self, folder: str | Path, filename: str, columns: Sequence[str]
    ) -> list[dict[str, str]]:
        """Read one XOCD CSV (Latin-1, ``;``-delimited, positional) into a list
        of dicts keyed by ``columns``. Missing file -> empty list."""
        path = Path(folder) / filename
        rows: list[dict[str, str]] = []
        if not path.is_file():
            return rows
        with path.open("r", encoding=_ENCODING, newline="") as handle:
            for raw in csv.reader(handle, delimiter=_DELIM):
                if not raw:
                    continue
                rows.append({
                    col: (raw[i] if i < len(raw) else "")
                    for i, col in enumerate(columns)
                })
        return rows

    def diff_rows(
        self,
        table: str,
        baseline: Sequence[dict[str, Any]],
        current: Sequence[dict[str, Any]],
        key_fields: Sequence[str],
        *,
        ignore: Sequence[str] = (),
        classify: Callable[[ReconChange], None] | None = None,
    ) -> list[ReconChange]:
        """Name-keyed diff of ``baseline`` (XOCD truth) vs ``current`` (MDB).

        An entity is identified by ``key_fields``; ``ignore`` columns are not
        compared. Returns classified :class:`ReconChange`s (added / removed /
        modified with field-level detail). ``classify`` may refine each change's
        verdict/reason.
        """
        ignored = set(ignore) | set(key_fields)

        def key(row: dict[str, Any]) -> tuple[str, ...]:
            return tuple(str(row.get(k, "")) for k in key_fields)

        base_by = {key(r): r for r in baseline}
        curr_by = {key(r): r for r in current}
        changes: list[ReconChange] = []

        for k, cur in curr_by.items():
            entity = self._entity(k)
            base = base_by.get(k)
            if base is None:
                changes.append(ReconChange(
                    table=table, entity=entity, kind=KIND_ADDED,
                    summary=f"{table} '{entity}' added in the MDB",
                    verdict=VERDICT_REVIEW, new_row=dict(cur),
                ))
                continue
            field_changes = [
                ReconFieldChange(col, str(base.get(col, "")), str(cur.get(col, "")))
                for col in (set(base) | set(cur))
                if col not in ignored
                and str(base.get(col, "")) != str(cur.get(col, ""))
            ]
            if field_changes:
                field_changes.sort(key=lambda f: f.field)
                changes.append(ReconChange(
                    table=table, entity=entity, kind=KIND_MODIFIED,
                    fields=field_changes,
                    summary=self._modified_summary(table, entity, field_changes),
                    verdict=VERDICT_REVIEW, new_row=dict(cur),
                ))

        for k, base in base_by.items():
            if k not in curr_by:
                entity = self._entity(k)
                changes.append(ReconChange(
                    table=table, entity=entity, kind=KIND_REMOVED,
                    summary=f"{table} '{entity}' removed in the MDB",
                    verdict=VERDICT_REVIEW,
                ))

        changes.sort(key=lambda c: (c.table, c.entity, c.kind))
        if classify is not None:
            for change in changes:
                classify(change)
        return changes

    @staticmethod
    def _entity(key_tuple: Sequence[str]) -> str:
        return " / ".join(part for part in key_tuple if part) or "(blank)"

    @staticmethod
    def _modified_summary(
        table: str, entity: str, fields: Sequence[ReconFieldChange]
    ) -> str:
        parts = ", ".join(f"{f.field} {f.old!r}->{f.new!r}" for f in fields)
        return f"{table} '{entity}': {parts}"

    # -- per-table adapters (XOCD file <-> MDB tCOMd mapping) ------------
    #: XOCD price columns (the order _prices writes them in).
    _PRICE_COLUMNS = (
        "program", "price_list", "article", "variant_condition", "op", "level",
        "c6", "c7", "value", "fix", "currency", "date_from", "date_to", "c13",
    )

    def _adapters(self) -> dict[str, dict]:
        """Per logical table: the XOCD CSV shape + key + MDB reader/mapper.

        The MDB SQL/mapping is best-effort against the documented ``tCOMd_*``
        schema; verify column names on a live MDB (marked for polish). Only Price
        is wired for now - PropValue and Text follow the same shape.
        """
        return {
            "price": {
                "file": "xocd_price.csv",
                "columns": self._PRICE_COLUMNS,
                "key": ("article", "variant_condition", "price_list", "level", "currency"),
                "ignore": ("program", "op", "c6", "c7", "fix", "c13"),
                "classify": self._classify_price,
                "mdb_sql": (
                    "SELECT com_ArticleCode, com_PriceListID, com_VariantCondition, "
                    "com_PriceLevelCode, com_PriceValue, com_ISOCurrencyCode, "
                    "com_DateFrom, com_DateTo FROM tCOMd_Price"
                ),
                "mdb_map": self._map_price_row,
            },
        }

    @staticmethod
    def _map_price_row(row: dict) -> dict:
        """Map one ``tCOMd_Price`` MDB row to the XOCD name-keyed price shape.
        (Column names best-effort - verify on a live MDB.)"""
        return {
            "price_list": str(row.get("com_PriceListID", "")),
            "article": str(row.get("com_ArticleCode", "")),
            "variant_condition": str(row.get("com_VariantCondition", "") or ""),
            "level": str(row.get("com_PriceLevelCode", "") or "B"),
            "value": str(row.get("com_PriceValue", "")),
            "currency": str(row.get("com_ISOCurrencyCode", "") or ""),
            "date_from": str(row.get("com_DateFrom", "")),
            "date_to": str(row.get("com_DateTo", "")),
        }

    @staticmethod
    def _classify_price(change: ReconChange) -> None:
        """Verdict for a price delta: value/validity edits are representable and
        safe; new rows need review; MDB removals are not folded back."""
        if change.kind == KIND_ADDED:
            change.verdict = VERDICT_REVIEW
            change.reason = "new price row - confirm before adding"
        elif change.kind == KIND_REMOVED:
            change.verdict = VERDICT_BLOCKED
            change.reason = (
                "price removed in the MDB - not folded back (discontinue in "
                "PDM/XOCD instead)"
            )
        else:
            cols = {f.field for f in change.fields}
            if cols <= {"value", "date_from", "date_to"}:
                change.verdict = VERDICT_SAFE
                change.reason = "price value/validity edit - representable"
            else:
                change.verdict = VERDICT_REVIEW
                change.reason = "non-price columns changed - review"

    # -- orchestration --------------------------------------------------
    def reconcile(
        self, folder: str | Path, mdb_path: str | Path | None = None, *,
        mdb_reader: Callable[[Any, str], list[dict]] | None = None,
        current_by_table: dict[str, list[dict]] | None = None,
    ) -> ReconReport:
        """Diff the XOCD package at ``folder`` against the MDB, returning a
        classified :class:`ReconReport`. ``current_by_table`` injects the MDB
        side directly (tests); otherwise each table is read from ``mdb_path`` via
        ``mdb_reader`` (defaults to the MDB service). A table whose MDB read
        fails is skipped with a note (baseline left untouched).
        """
        report = ReconReport()
        for table, adapter in self._adapters().items():
            baseline = self.read_xocd_table(folder, adapter["file"], adapter["columns"])
            if current_by_table is not None and table in current_by_table:
                current = current_by_table[table]
            else:
                current = self._read_mdb_table(adapter, mdb_path, mdb_reader)
            if current is None:
                report.notes.append(
                    f"{table}: MDB not read - {adapter['file']} baseline only."
                )
                continue
            report.changes.extend(self.diff_rows(
                table, baseline, current, adapter["key"],
                ignore=adapter["ignore"], classify=adapter["classify"],
            ))
        return report

    def _read_mdb_table(
        self, adapter: dict, mdb_path, mdb_reader
    ) -> list[dict] | None:
        """Read + name-key one MDB table; None if it can't be read."""
        if mdb_path is None:
            return None
        reader = mdb_reader or (
            lambda path, sql: self.context.mdb_service.read_table(path, sql)
        )
        try:
            raw = reader(mdb_path, adapter["mdb_sql"])
        except Exception:
            return None
        mapper = adapter["mdb_map"]
        return [mapper(row) for row in raw]

    def apply_changes(
        self, folder: str | Path, table: str, accepted: Sequence[ReconChange]
    ) -> int:
        """Fold accepted added/modified changes back into the XOCD CSV (blocked
        and removed changes are skipped). Returns the number applied."""
        adapter = self._adapters().get(table)
        if adapter is None:
            return 0
        columns = adapter["columns"]
        keys = adapter["key"]

        def key(row: dict) -> tuple[str, ...]:
            return tuple(str(row.get(k, "")) for k in keys)

        by_key = {
            key(r): r
            for r in self.read_xocd_table(folder, adapter["file"], columns)
        }
        applied = 0
        for change in accepted:
            if (change.kind == KIND_REMOVED or change.verdict == VERDICT_BLOCKED
                    or not change.new_row):
                continue
            existing = by_key.get(key(change.new_row), {})
            merged = {**existing, **change.new_row}
            by_key[key(change.new_row)] = merged
            applied += 1
        if applied:
            rows = [[str(r.get(c, "")) for c in columns] for r in by_key.values()]
            self._write_xocd_table(folder, adapter["file"], rows)
        return applied

    # -- repository (OCD CSV) reconciliation ----------------------------
    #: Repository ocd_price.csv columns (per pdata.ocd_price.inp_descr).
    _OCD_PRICE_COLUMNS = (
        "article", "var_cond", "price_type", "price_level", "price_rule",
        "price_textnr", "value", "is_fix", "currency", "date_from", "date_to",
        "scale_quantity", "rounding_id",
    )
    #: Common price key both formats map onto (validity-aware).
    _COMMON_PRICE_KEY = (
        "article", "var_cond", "price_type", "price_level", "currency", "date_from",
    )

    @staticmethod
    def _read_csv_with_lines(path: Path, columns: Sequence[str]) -> list[dict]:
        """Read a ``;``-delimited CSV, tagging each row with its 1-based line."""
        rows: list[dict] = []
        if not path.is_file():
            return rows
        with path.open("r", encoding=_ENCODING, newline="") as handle:
            for line_no, raw in enumerate(csv.reader(handle, delimiter=_DELIM), start=1):
                if not raw:
                    continue
                row = {
                    col: (raw[i] if i < len(raw) else "")
                    for i, col in enumerate(columns)
                }
                row["__line__"] = line_no
                rows.append(row)
        return rows

    def _xocd_price_common(self, folder: str | Path, program: str | None = None) -> list[dict]:
        rows = self._read_csv_with_lines(
            Path(folder) / "xocd_price.csv", self._PRICE_COLUMNS
        )
        return [{
            "article": r["article"], "var_cond": r["variant_condition"],
            "price_type": r["op"], "price_level": r["level"],
            "currency": r["currency"], "date_from": r["date_from"],
            "value": r["value"], "date_to": r["date_to"], "__line__": r["__line__"],
        } for r in rows if program is None or r["program"] == program]

    def _repo_price_common(self, db_folder: str | Path) -> list[dict]:
        rows = self._read_csv_with_lines(
            Path(db_folder) / "ocd_price.csv", self._OCD_PRICE_COLUMNS
        )
        return [{
            "article": r["article"], "var_cond": r["var_cond"],
            "price_type": r["price_type"], "price_level": r["price_level"],
            "currency": r["currency"], "date_from": r["date_from"],
            "value": r["value"], "date_to": r["date_to"],
        } for r in rows]

    def xocd_programs(self, xocd_folder: str | Path) -> list[str]:
        """All exported series (products) in the XOCD package.

        Read from the series registry (xocd_programs.csv) so EVERY exported
        series is offered - not just those that happen to have price rows. Falls
        back to the distinct programs in xocd_price.csv when the registry is
        missing. The reconcile is scoped to the chosen series so other products
        are never flagged as removed."""
        registry = self.read_xocd_table(
            xocd_folder, "xocd_programs.csv",
            ("program", "program_id", "label", "extra"),
        )
        progs = {r["program"] for r in registry if r["program"]}
        if not progs:
            rows = self.read_xocd_table(xocd_folder, "xocd_price.csv", self._PRICE_COLUMNS)
            progs = {r["program"] for r in rows if r["program"]}
        return sorted(progs)

    def _detect_program(self, xocd_folder: str | Path, repo_db_folder: str | Path) -> str | None:
        """The XOCD program matching this repo product folder.

        The repo path is ``.../<product>/<region>/1/db``; match its product name
        to a program in xocd_price.csv (single program -> that one).
        """
        rows = self.read_xocd_table(xocd_folder, "xocd_price.csv", self._PRICE_COLUMNS)
        programs = {r["program"] for r in rows if r["program"]}
        if len(programs) == 1:
            return next(iter(programs))
        try:
            product = Path(repo_db_folder).resolve().parents[2].name
        except IndexError:
            return None
        low = product.lower()
        for prog in programs:
            if prog.lower() == low:
                return prog
        for prog in programs:
            if low and (low in prog.lower() or prog.lower() in low):
                return prog
        return None

    def reconcile_repo(
        self, xocd_folder: str | Path, repo_db_folder: str | Path,
        program: str | None = None,
    ) -> ReconReport:
        """Diff the repository OCD package (final output, ``ocd_*.csv``) against
        our XOCD source (``xocd_*.csv``), like an SVN diff.

        The XOCD holds ALL products, but the repo folder is ONE product, so the
        XOCD is filtered to the matching ``program`` (auto-detected from the repo
        product folder when not given). Maps both price formats to a common
        validity-aware schema and returns classified changes - each modified/
        removed change links back to the XOCD line (``source_ref``).
        """
        report = ReconReport()
        prog = program or self._detect_program(xocd_folder, repo_db_folder)
        report.program = prog or ""
        baseline = self._xocd_price_common(xocd_folder, prog)
        current = self._repo_price_common(repo_db_folder)
        key = self._COMMON_PRICE_KEY
        changes = self.diff_rows(
            "price", baseline, current, key,
            ignore=("__line__",), classify=self._classify_price,
        )
        ref_by_entity = {
            self._entity(tuple(str(r.get(k, "")) for k in key)): r.get("__line__", 0)
            for r in baseline
        }
        for change in changes:
            line = ref_by_entity.get(change.entity)
            if line:
                change.source_ref = f"xocd_price.csv:{line}"
        report.changes.extend(changes)
        if prog:
            report.notes.append(
                f"Program '{prog}' (XOCD holds all products; repo is one)."
            )
        else:
            report.notes.append(
                "No program matched the repo folder - compared ALL XOCD price rows."
            )
        # Heuristic: many removed AND many added but no modified => the two sides
        # differ by KEY (var_cond / dates), i.e. a column-format mismatch, not
        # real removals. Warn instead of implying every line was deleted.
        added = sum(1 for c in changes if c.kind == KIND_ADDED)
        removed = sum(1 for c in changes if c.kind == KIND_REMOVED)
        modified = sum(1 for c in changes if c.kind == KIND_MODIFIED)
        if removed and added and not modified:
            report.notes.append(
                "Rows differ by KEY, not value (likely an XOCD<->repo column/"
                "variant-condition format mismatch) - these are not real removals."
            )
        if not (Path(repo_db_folder) / "ocd_price.csv").is_file():
            report.notes.append("repo ocd_price.csv not found - nothing compared.")
        return report

    def apply_repo_changes(
        self, xocd_folder: str | Path, accepted: Sequence[ReconChange]
    ) -> int:
        """Fold accepted MODIFIED price edits back into ``xocd_price.csv`` (value
        + date_to), matched by the common key. Added/removed/blocked skipped."""
        rows = self.read_xocd_table(xocd_folder, "xocd_price.csv", self._PRICE_COLUMNS)

        def xocd_entity(r: dict) -> str:
            return self._entity((
                r["article"], r["variant_condition"], r["op"], r["level"],
                r["currency"], r["date_from"],
            ))

        by_entity = {xocd_entity(r): r for r in rows}
        applied = 0
        for change in accepted:
            if (change.kind != KIND_MODIFIED or change.verdict == VERDICT_BLOCKED
                    or not change.new_row):
                continue
            target = by_entity.get(change.entity)
            if target is None:
                continue
            target["value"] = change.new_row.get("value", target["value"])
            target["date_to"] = change.new_row.get("date_to", target["date_to"])
            applied += 1
        if applied:
            out = [[str(r.get(c, "")) for c in self._PRICE_COLUMNS] for r in rows]
            self._write_xocd_table(xocd_folder, "xocd_price.csv", out)
        return applied

    @staticmethod
    def _write_xocd_table(folder: str | Path, filename: str, rows: list) -> None:
        """Rewrite an XOCD CSV (Latin-1, ``;``-delimited, CRLF)."""
        path = Path(folder) / filename
        with path.open("w", encoding=_ENCODING, newline="") as handle:
            csv.writer(handle, delimiter=_DELIM, lineterminator="\r\n").writerows(rows)
