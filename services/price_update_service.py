"""Annual/mid-year price-list roll-over across a repository of published packages.

Mirrors PDM's *Update pCon Prices* button (``PConPriceUpdate``): it works
**in place** on already-published packages and touches **only the price
tables**. It does not re-export structure, text or relations.

A batch run points at a repository and loops every package one by one. For each
package it:

1. **finds the open list** per currency - the one whose validity ends in year
   9999 (``tCOMd_PriceList2.com_PriceValidTo`` for MDB, the price rows' ``DateTo``
   for XOCD), so EUR and GBP are both rolled;
2. **freezes** that list, setting its end to the day before the effective date;
3. **copies it forward** into a new list named ``<prefix>_<token>`` (the token is
   keyed once, e.g. ``2026`` or ``2026_2``), refreshing each value from PDM
   (``price_lookup``) or carrying the old value when none is available.

``apply=False`` reports the plan without writing. Two backends - XOCD CSV
packages and direct OCD MDBs - share the discovery, naming and loop.
"""
from __future__ import annotations

import csv
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from models.snapshot import Snapshot
from services.base_service import BaseService

#: XOCD CSV dialect (matches XocdExportService).
_DELIM = ";"
_LINEEND = "\r\n"
_ENCODING = "latin-1"

#: xocd_price column indices.
_PX_PROGRAM, _PX_LIST, _PX_ARTICLE, _PX_VARCOND = 0, 1, 2, 3
_PX_LEVEL, _PX_VALUE, _PX_CURRENCY = 5, 8, 10
_PX_DATE_FROM, _PX_DATE_TO = 11, 12

#: Central, editable registry of authoritative base article lengths.
_REGISTRY_NAME = "base_length_overrides.csv"
#: Confirmed special-case article -> PDM base item map (underscore SKUs).
_SPECIAL_MAP_NAME = "special_article_map.csv"
_REGISTRY_COLUMNS = ["Program", "Item", "CurrentBase", "CAD_Length",
                     "Expected_Base", "Override_Length", "Status"]
#: Default central folder for the registry (a writable location the user owns;
#: NOT a package/SVN subfolder, which may be read-only). Overridable in the UI.
_DEFAULT_REGISTRY_DIR = r"C:\HermanMillerOFMLSVN\Staging"

#: Folder names that are NOT published products (WS templates, training, value-
#: table/varcond helpers, translations, backups) - skipped by package discovery
#: so the whole WS parent can be scanned. Matched on a leading '#'/digit prefix
#: or these substrings, per path part relative to the chosen root.
_NONPRODUCT_DIR = re.compile(r"^(#|\d+[_-])|backup|template|training|translation", re.IGNORECASE)

#: Items pulled from PDM per warm query. Small enough that the running count
#: advances visibly during the slow scalar-UDF pricing, not just at the end.
_WARM_CHUNK = 100


def _as_roots(repository) -> list[Path]:
    """Normalise a repository argument into a list of root paths. Accepts a
    single path, or several ``;``-separated ones (so the two product workspaces
    - Seating and Tables - can be scanned together in one run)."""
    if isinstance(repository, (list, tuple, set)):
        parts = [str(p) for p in repository]
    else:
        parts = str(repository).split(";")
    return [Path(p.strip()) for p in parts if str(p).strip()]


def _mdb_date_literal(ymd: str) -> str:
    """A ``YYYYMMDD`` date as an Access date literal ``#YYYY-MM-DD 00:00:00#`` so
    the MDB bridge writes it to a DateTime column at local midnight - matching
    PDM's own dates (which store midnight, shown as a clean date with no time).
    :func:`PriceUpdateService._bridge_ymd` decodes it back timezone-aware, so the
    day is preserved. Left unchanged if it is not a full date."""
    s = re.sub(r"\D", "", str(ymd or ""))[:8]
    if len(s) < 8:
        return str(ymd or "")
    return f"#{s[0:4]}-{s[4:6]}-{s[6:8]} 00:00:00#"


@dataclass
class BaseLengthEntry:
    """One base article checked against PDM's CAD-maintenance prefix length."""

    program: str = ""       # series the article belongs to
    article: str = ""        # base article as stored in the package
    full_item: str = ""      # reconstructed article + varcond
    notes: str = ""          # PDM Item.Notes
    pdm_len: int = 0         # prefix length parsed from Notes (0 = none)
    expected_base: str = ""  # full_item[:pdm_len]
    match: bool = False


@dataclass
class BaseLengthReport:
    """Base-length comparison for one package (read-only, no writes)."""

    package: str = ""
    entries: list[BaseLengthEntry] = field(default_factory=list)
    error: str | None = None

    @property
    def matches(self) -> int:
        return sum(1 for e in self.entries if e.match)

    @property
    def mismatches(self) -> list[BaseLengthEntry]:
        return [e for e in self.entries if not e.match and e.pdm_len]


@dataclass
class OpenList:
    """A price list still open (validity ends 9999) - the one a roll-over ends."""

    currency: str = ""
    list_id: str = ""


@dataclass
class ListRoll:
    """One currency's roll-over within a package: old list -> new list."""

    currency: str = ""
    old_list: str = ""
    new_list: str = ""
    #: pending (to roll) | partial (interrupted, will be rebuilt) | done.
    status: str = "pending"
    rows: int = 0
    priced: int = 0      # value refreshed from PDM
    carried: int = 0     # no PDM value -> old value kept
    changed: int = 0     # refreshed value differs from the old one


@dataclass
class PackageRoll:
    """Roll-over outcome for a single package (one location in the repository)."""

    package: str = ""
    lists: list[ListRoll] = field(default_factory=list)
    applied: bool = False
    error: str | None = None
    #: Special-case (underscore) article codes that had NO PDM price and were
    #: carried - candidates for the end-of-roll clarification + targeted update.
    special_carried: list[str] = field(default_factory=list)


@dataclass
class BatchResult:
    """Outcome of a repository-wide roll-over (every package, one by one)."""

    repository: str = ""
    packages: list[PackageRoll] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and all(p.error is None for p in self.packages)


class PriceUpdateService(BaseService):
    """Roll every published package onto a new price list, in place, price-only."""

    # -- Discover the list to end (the "9999" open list) ----------------

    def open_lists(self, package: str | Path, is_mdb: bool = False) -> list[OpenList]:
        """Every currently-open price list in a package - the ones a roll-over
        ends. A list is open when its validity end is year 9999
        (``tCOMd_PriceList2.com_PriceValidTo`` for MDB, the price rows' ``DateTo``
        for XOCD). Returned per currency, so a batch can end each and start its
        successor. This is the seed of the batch loop: point at a package, find
        the open list(s), roll them over."""
        return self._open_lists_mdb(Path(package)) if is_mdb else self._open_lists_xocd(Path(package))

    def _open_lists_xocd(self, folder: Path) -> list[OpenList]:
        path = folder / "xocd_price.csv"
        by_list: dict[str, dict[str, Any]] = {}
        if path.is_file():
            with path.open("r", encoding=_ENCODING, newline="") as fh:
                for row in csv.reader(fh, delimiter=_DELIM):
                    if len(row) <= _PX_DATE_TO:
                        continue
                    rec = by_list.setdefault(
                        row[_PX_LIST], {"currency": row[_PX_CURRENCY], "open": False}
                    )
                    if str(row[_PX_DATE_TO]).startswith("9999"):
                        rec["open"] = True
        return [OpenList(v["currency"], lid) for lid, v in by_list.items()
                if v["open"] and self._is_dated_list(lid)]

    def _open_lists_mdb(self, mdb: Path) -> list[OpenList]:
        rows = self.context.mdb_service.read_table(
            mdb, "SELECT com_PriceListLabel, sys_ISOCurrencyCode, com_PriceValidTo "
                 "FROM tCOMd_PriceList2")
        out: list[OpenList] = []
        for r in rows:
            label = str(r.get("com_PriceListLabel") or "")
            if not self._is_open_ymd(r.get("com_PriceValidTo")) or not self._is_dated_list(label):
                continue
            out.append(OpenList(str(r.get("sys_ISOCurrencyCode") or ""), label))
        return out

    @staticmethod
    def _bridge_ymd(value: Any) -> str:
        """A price-list date as ``YYYYMMDD``. The 32-bit MDB bridge serialises
        dates as ``/Date(ms)/`` (UTC milliseconds since 1970-01-01, may be
        negative); XOCD gives a ``yyyymmdd`` string. The ms is decoded to the
        LOCAL wall-clock (adding the machine's UTC offset), so a date PDM stored
        at local midnight reads back as that same calendar day (not the day
        before). Returns ``""`` when unparseable."""
        s = str(value or "")
        if "/Date(" in s:
            match = re.search(r"-?\d+", s)
            if not match:
                return ""
            try:
                offset = datetime.now().astimezone().utcoffset() or timedelta(0)
                dt = datetime(1970, 1, 1) + timedelta(milliseconds=int(match.group(0))) + offset
            except (ValueError, OverflowError):
                return ""
            return dt.strftime("%Y%m%d")
        digits = re.sub(r"\D", "", s)
        return digits[:8] if len(digits) >= 8 else ""

    @classmethod
    def _is_open_ymd(cls, value: Any) -> bool:
        """An open (never-ending) list ends in year 9999 - after decoding the
        bridge's ``/Date(ms)/`` sentinel to a real ``YYYYMMDD``."""
        return cls._bridge_ymd(value).startswith("9999")

    @staticmethod
    def _is_dated_list(label: str) -> bool:
        """A roll-able price list carries a year (``EURO_2025``, ``GBP_2025``).
        Static market lists like ``NOPRICE`` carry none and are left untouched."""
        return bool(re.search(r"\d{4}", label or ""))

    @staticmethod
    def new_list_name(open_list_id: str, token: str) -> str:
        """The successor list id: the open list's region/currency prefix (its
        leading letters) plus the user's one-time ``token``. Keyed once and
        applied to every list in the loop, so ``EURO_2025`` + ``2026`` ->
        ``EURO_2026`` (annual) and + ``2026_2`` -> ``EURO_2026_2`` (a mid-year
        increase). Falls back to ``<open>_<token>`` when there is no letter
        prefix to keep."""
        token = (token or "").strip().lstrip("_")
        if not token:
            return open_list_id
        match = re.match(r"[A-Za-z]+", open_list_id or "")
        prefix = match.group(0) if match else (open_list_id or "").rstrip("_")
        return f"{prefix}_{token}"

    # -- Base-length check vs PDM CAD-maintenance Notes (read-only) ------

    @staticmethod
    def _prefix_len_from_notes(notes: str) -> int:
        """The pCon article prefix length from an ``Item.Notes`` value, exactly
        as PDM's ``getArticlePrefixLength``: comma-split, the last 1-2 char
        integer token wins (0 when none)."""
        num = -1
        for token in (notes or "").split(","):
            if 0 < len(token) < 3 and token.isdigit():
                num = int(token)
        return num if num >= 0 else 0

    def _base_pairs_xocd(self, folder: Path) -> list[tuple[str, str, str]]:
        """Distinct (program, base article, varcond). The article LIST is the
        authoritative ``xocd_article.csv`` (every published article); the varcond
        used to rebuild the full item comes from the base price rows. Articles
        with no base price keep an empty varcond. Falls back to the price rows
        when no article file is present."""
        arts: set[tuple[str, str]] = set()
        apath = folder / "xocd_article.csv"
        if apath.is_file():
            with apath.open("r", encoding=_ENCODING, newline="") as fh:
                for row in csv.reader(fh, delimiter=_DELIM):
                    if len(row) > 2 and row[2]:              # Program, _, ArticleID
                        arts.add((row[0], row[2]))
        varconds: dict[tuple[str, str], set[str]] = {}
        ppath = folder / "xocd_price.csv"
        if ppath.is_file():
            with ppath.open("r", encoding=_ENCODING, newline="") as fh:
                for row in csv.reader(fh, delimiter=_DELIM):
                    if len(row) <= _PX_LEVEL or row[_PX_ARTICLE] == "*":
                        continue
                    if "=" in row[_PX_VARCOND] or (row[_PX_LEVEL] or "B") != "B":
                        continue
                    varconds.setdefault(
                        (row[_PX_PROGRAM], row[_PX_ARTICLE]), set()).add(row[_PX_VARCOND])
        if not arts:
            arts = set(varconds)
        out: set[tuple[str, str, str]] = set()
        for key in arts:
            for vc in (varconds.get(key) or {""}):
                out.add((key[0], key[1], vc))
        return sorted(out)

    def _base_pairs_mdb(self, mdb: Path) -> list[tuple[str, str, str]]:
        """Distinct (program, base article, varcond). The article LIST is the
        authoritative ``tCOMd_Article`` table; the varcond comes from the base
        ``tCOMd_Price`` rows. All three reads run in ONE bridge call so a large
        workspace of MDBs stays fast."""
        batch = self.context.mdb_service.execute_batch(mdb, [
            {"op": "query", "sql": "SELECT TOP 1 reg_ProgramCode FROM tCOMd_Package"},
            {"op": "query", "sql": "SELECT com_ArticleCode FROM tCOMd_Article"},
            {"op": "query", "sql": "SELECT a.com_ArticleCode, p.com_VariantCondition "
                                   "FROM tCOMd_Price p INNER JOIN tCOMd_Article a "
                                   "ON p.com_ArticleID = a.com_ArticleID "
                                   "WHERE p.com_PriceLevelCode = 'B'"},
        ])
        res = batch.results
        if not batch.ok or len(res) < 3:      # not a commercial OCD MDB
            return []
        prog_rows, art_rows, price_rows = res[0].rows, res[1].rows, res[2].rows
        program = str(prog_rows[0].get("reg_ProgramCode") or "") if prog_rows else ""
        arts = {(program, str(r.get("com_ArticleCode") or ""))
                for r in art_rows if r.get("com_ArticleCode")}
        varconds: dict[tuple[str, str], set[str]] = {}
        for r in price_rows:
            varconds.setdefault(
                (program, str(r.get("com_ArticleCode") or "")), set()).add(
                    str(r.get("com_VariantCondition") or ""))
        if not arts:
            arts = set(varconds)
        out: set[tuple[str, str, str]] = set()
        for key in arts:
            for vc in (varconds.get(key) or {""}):
                out.add((key[0], key[1], vc))
        return sorted(out)

    def _fetch_notes(self, items: list[str]) -> dict[str, str]:
        """``{item code: Item.Notes}`` from PDM (empty on any failure)."""
        if not items:
            return {}
        try:
            from repositories.pdm_repository import PDMRepository
            repo = PDMRepository(self.context)
            conn = repo.get_connection()
            try:
                rows = repo.fetch_item_notes(items, conn)
            finally:
                conn.close()
            return {str(r.Item): (getattr(r, "Notes", "") or "") for r in rows}
        except Exception:
            return {}

    def compare_base_lengths(
        self, package: str | Path, is_mdb: bool = False,
        notes_by_item: dict[str, str] | None = None,
    ) -> BaseLengthReport:
        """Check each package base article against PDM's CAD-maintenance prefix
        length. Reconstructs the full item (base + varcond), reads its
        ``Item.Notes`` prefix length, and flags where the stored base article
        differs from ``full_item[:prefix_len]``. Read-only. ``notes_by_item`` can
        be injected (tests); otherwise the Notes are pulled from PDM."""
        report = BaseLengthReport(package=str(package))
        try:
            pairs = (self._base_pairs_mdb(Path(package)) if is_mdb
                     else self._base_pairs_xocd(Path(package)))
        except OSError as exc:
            report.error = str(exc)
            return report
        if notes_by_item is None:
            items = sorted({(b + v).strip() for _, b, v in pairs if (b + v).strip()})
            notes_by_item = self._fetch_notes(items)
        return self._build_report(package, pairs, notes_by_item)

    def _build_report(
        self, package, pairs: list[tuple[str, str, str]], notes_by_item: dict[str, str]
    ) -> BaseLengthReport:
        """Build a report from already-read pairs + a shared Notes map."""
        report = BaseLengthReport(package=str(package))
        full: dict[tuple[str, str], str] = {}  # (program, full item) -> stored base
        for program, base, varcond in pairs:
            item = (base + varcond).strip()
            if item:
                full.setdefault((program, item), base)
        for (program, item), base in sorted(full.items()):
            notes = notes_by_item.get(item, "")
            plen = self._prefix_len_from_notes(notes)
            expected = item[:plen] if plen else ""
            report.entries.append(BaseLengthEntry(
                program=program, article=base, full_item=item, notes=notes,
                pdm_len=plen, expected_base=expected,
                match=bool(plen) and expected == base))
        return report

    def check_base_lengths(
        self, repository: str | Path, is_mdb: bool = False, progress=None
    ) -> list[BaseLengthReport]:
        """Base-length check for every package under the repository (read-only).
        Reads each package's article list once, then does ONE PDM Notes fetch for
        every item across all packages (not one connection per package), so a
        large repository stays fast. ``progress(done, total, text)`` is called
        per package (and once for the PDM fetch) for a progress bar."""
        packages = self._discover_packages(repository, is_mdb)
        total = len(packages)
        pairs_by_pkg: dict[Path, object] = {}
        all_items: set[str] = set()
        for i, pkg in enumerate(packages, 1):
            if progress:
                progress(i, total, (pkg.parent.name if is_mdb else pkg.name))
            try:
                pairs = self._base_pairs_mdb(pkg) if is_mdb else self._base_pairs_xocd(pkg)
            except OSError as exc:
                pairs_by_pkg[pkg] = exc
                continue
            pairs_by_pkg[pkg] = pairs
            all_items.update((b + v).strip() for _, b, v in pairs if (b + v).strip())
        if progress:
            progress(total, total, "Fetching CAD lengths from PDM...")
        notes = self._fetch_notes(sorted(all_items))
        reports: list[BaseLengthReport] = []
        for pkg in packages:
            got = pairs_by_pkg[pkg]
            if isinstance(got, OSError):
                reports.append(BaseLengthReport(package=str(pkg), error=str(got)))
            else:
                reports.append(self._build_report(pkg, got, notes))
        return reports

    def registry_path(self, directory: str | Path | None = None) -> Path:
        """The central registry file: ``<directory>/base_length_overrides.csv``,
        defaulting to a writable central folder (not the read-only package/SVN
        tree). One file accumulates every series that has been checked."""
        return Path(directory or _DEFAULT_REGISTRY_DIR) / _REGISTRY_NAME

    def build_base_length_registry(
        self, repository: str | Path, is_mdb: bool = False, progress=None
    ) -> list[dict[str, str]]:
        """Registry rows from the package article list matched to PDM CAD
        Maintenance - one row per (series, item), so the file lists only the few
        articles actually published, not all of PDM."""
        rows: list[dict[str, str]] = []
        for report in self.check_base_lengths(repository, is_mdb, progress):
            for e in report.entries:
                status = "OK" if e.match else ("NO_CAD" if not e.pdm_len else "MISMATCH")
                rows.append({
                    "Program": e.program, "Item": e.full_item,
                    "CurrentBase": e.article, "CAD_Length": str(e.pdm_len or ""),
                    "Expected_Base": e.expected_base, "Override_Length": "",
                    "Status": status,
                })
        return rows

    def write_base_length_registry(
        self, path: str | Path, rows: list[dict[str, str]], preserve_edits: bool = True
    ) -> str:
        """Write/refresh the central registry. It ACCUMULATES: rows for series not
        in this run are kept. When ``preserve_edits`` (a re-check), an existing
        ``Override_Length`` is kept over a blank new one; when False (an explicit
        Save) the provided rows win, so an override can also be cleared."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        merged = self._read_registry_all(path)   # (Program, Item) -> row
        for r in rows:
            key = (r["Program"], r["Item"])
            prev = merged.get(key)
            if preserve_edits and prev and (prev.get("Override_Length") or "").strip():
                r = {**r, "Override_Length": prev["Override_Length"]}
            merged[key] = r
        with path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=_REGISTRY_COLUMNS, delimiter=";")
            writer.writeheader()
            for key in sorted(merged):
                writer.writerow({c: merged[key].get(c, "") for c in _REGISTRY_COLUMNS})
        return str(path)

    def _read_registry_all(self, path: str | Path) -> dict[tuple[str, str], dict[str, str]]:
        """Every registry row keyed by (Program, Item)."""
        path = Path(path)
        out: dict[tuple[str, str], dict[str, str]] = {}
        if not path.is_file():
            return out
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                out[(r.get("Program", ""), r.get("Item", ""))] = dict(r)
        return out

    def read_base_length_registry(self, path: str | Path) -> dict[tuple[str, str], str]:
        """``{(program, item): Override_Length}`` for the rows the user edited."""
        return {
            key: (row.get("Override_Length") or "").strip()
            for key, row in self._read_registry_all(path).items()
            if (row.get("Override_Length") or "").strip()
        }

    def snapshot_base_length_overrides(
        self, snapshot: Snapshot, registry_path: str | Path
    ) -> dict[str, int]:
        """Map this series' article codes to the registry's authoritative base
        length (``Override_Length`` else ``CAD_Length``) - the input to
        standardising a re-published series to CAD Maintenance."""
        if snapshot.product is None:
            return {}
        program = self.context.xocd_export_service.program_key(snapshot.product)
        out: dict[str, int] = {}
        for (prog, item), row in self._read_registry_all(registry_path).items():
            if prog and prog != program:
                continue
            length = ((row.get("Override_Length") or "").strip()
                      or (row.get("CAD_Length") or "").strip())
            if length.isdigit() and int(length) > 0:
                out[item] = int(length)
        return out

    def apply_registry(self, snapshot: Snapshot, registry_path: str | Path) -> int:
        """Load the base-length overrides for this series onto the snapshot so a
        re-publish slices its base articles to CAD Maintenance. Returns how many
        articles are overridden (0 = nothing changes)."""
        snapshot.base_length_overrides = self.snapshot_base_length_overrides(
            snapshot, registry_path)
        return len(snapshot.base_length_overrides)

    # -- Batch roll-over (repository loop) ------------------------------

    @staticmethod
    def _discover_packages(root: Path, is_mdb: bool) -> list[Path]:
        """Every published-product package under the root(s): the commercial
        ``pcr_data_com_ocd.mdb`` files (not backups or other ``pcr_*`` DBs), or
        the folders holding an ``xocd_price.csv``. Non-product WS folders
        (templates, training, MT/value-table helpers, translations, backups) are
        skipped so the whole ``WS`` parent can be scanned in one run. ``root`` may
        be a single path or several ``;``-separated ones (Seating + Tables)."""
        pattern = "pcr_data_com_ocd.mdb" if is_mdb else "xocd_price.csv"
        found: list[Path] = []
        for base in _as_roots(root):
            for hit in base.rglob(pattern):
                if any(_NONPRODUCT_DIR.search(part) for part in hit.relative_to(base).parts):
                    continue
                found.append(hit if is_mdb else hit.parent)
        return sorted(set(found))

    def run_batch(
        self, repository: str | Path, is_mdb: bool, effective_ymd: str, token: str,
        price_lookup=None, apply: bool = True, packages=None, progress=None, stage=None,
        special_map: dict[str, str] | None = None,
    ) -> BatchResult:
        """Roll every package under ``repository`` onto a new price list.

        Loops each package one by one: finds its open (9999) list per currency,
        copies that list forward into ``<prefix>_<token>`` with fresh values
        (``price_lookup``) and end-dates the old list at ``effective_ymd`` - 1.
        ``apply=False`` reports the plan without writing. ``price_lookup`` is a
        callable ``(currency, is_global, article, varcond, level) -> value|None``
        (None keeps the old value); pass :meth:`make_pdm_lookup` in production.
        Pass ``packages`` (an explicit list of package paths) to roll only a
        chosen subset; otherwise every package under ``repository`` is rolled.
        ``progress(done, total, text)`` is called per package for a progress bar."""
        result = BatchResult(repository=str(repository))
        if packages is None:
            roots = _as_roots(repository)
            missing = [r for r in roots if not r.exists()]
            if not roots or missing:
                result.error = f"Repository not found: {missing[0] if missing else repository}"
                return result
            packages = self._discover_packages(repository, is_mdb)
        else:
            packages = [Path(p) for p in packages]

        roll = self.roll_over_package_mdb if is_mdb else self.roll_over_package_xocd
        for i, pkg in enumerate(packages, 1):
            name = pkg.parent.name if is_mdb else pkg.name
            if stage:
                stage(f"Package {i}/{len(packages)}: {name}")
            result.packages.append(roll(pkg, effective_ymd, token, price_lookup, apply,
                                         stage=stage, special_map=special_map))
            # Advance one step AFTER the package is done, so a single package
            # doesn't jump straight to 100% before any work has happened.
            if progress:
                progress(i, len(packages), name)
        result.logs.append(
            f"{'Applied' if apply else 'Scanned'} {len(packages)} package(s)."
        )
        return result

    def roll_over_package_xocd(
        self, folder: str | Path, effective_ymd: str, token: str,
        price_lookup=None, apply: bool = True, stage=None,
        special_map: dict[str, str] | None = None,
    ) -> PackageRoll:
        """Roll one XOCD package, resumably. A list already carrying the token
        (``new_list_name == itself``) is **done** and skipped, so a re-run after
        an interruption only touches what is left. Leftover rows from a partial
        attempt (the target list already present) are dropped and rebuilt, and
        the file is replaced atomically - a re-run never double-writes."""
        folder = Path(folder)
        result = PackageRoll(package=str(folder))
        path = folder / "xocd_price.csv"
        if not path.is_file():
            result.error = "no xocd_price.csv"
            return result
        old_end = self.context.price_list_service._day_before(effective_ymd)

        # Split the open lists into already-done (target == itself) and pending.
        pending: dict[str, tuple[str, str]] = {}   # old_list -> (currency, target)
        for ol in self._open_lists_xocd(folder):
            target = self.new_list_name(ol.list_id, token)
            if target == ol.list_id:
                result.lists.append(ListRoll(
                    currency=ol.currency, old_list=ol.list_id,
                    new_list=ol.list_id, status="done"))
            else:
                pending[ol.list_id] = (ol.currency, target)
        if not pending:
            result.applied = apply
            return result  # nothing left to do

        targets = {t for _, t in pending.values()}
        tally: dict[str, ListRoll] = {}
        try:
            with path.open("r", encoding=_ENCODING, newline="") as fh:
                rows = [r for r in csv.reader(fh, delimiter=_DELIM) if r]
            kept: list[list[str]] = []
            new_rows: list[list[str]] = []
            partial = False
            for row in rows:
                if len(row) <= _PX_DATE_TO:
                    kept.append(row)
                    continue
                lid = row[_PX_LIST]
                if lid in targets:
                    partial = True  # leftover from an interrupted run -> rebuild
                    continue
                kept.append(row)
                if lid not in pending or not str(row[_PX_DATE_TO]).startswith("9999"):
                    continue
                currency, target = pending[lid]
                lr = tally.setdefault(lid, ListRoll(
                    currency=currency, old_list=lid, new_list=target))
                is_global = row[_PX_ARTICLE] == "*"
                try:
                    old_val = float(row[_PX_VALUE] or 0)
                except ValueError:
                    old_val = 0.0
                fresh = (price_lookup(currency, is_global, row[_PX_ARTICLE],
                                      row[_PX_VARCOND], row[_PX_LEVEL])
                         if price_lookup else None)
                value = old_val if fresh is None else float(fresh)
                lr.rows += 1
                if fresh is None:
                    lr.carried += 1
                else:
                    lr.priced += 1
                    if value != old_val:
                        lr.changed += 1
                if apply:
                    new_row = list(row)
                    new_row[_PX_LIST] = target
                    new_row[_PX_VALUE] = self._num(value)
                    new_row[_PX_DATE_FROM] = effective_ymd
                    new_row[_PX_DATE_TO] = "99991231"
                    new_rows.append(new_row)
                    row[_PX_DATE_TO] = old_end  # freeze + end-date the old row
            for lr in tally.values():
                lr.status = "done" if apply else ("partial" if partial else "pending")
            if apply:
                self._write_rows_atomic(path, kept + new_rows)
                for target in targets:
                    self._register_xocd_list(folder, target, target)
                result.applied = True
            result.lists.extend(tally.values())
        except OSError as exc:
            result.error = str(exc)
        return result

    @staticmethod
    def _lookup_key(is_global: bool, article: str, varcond: str,
                    special_map: dict[str, str] | None = None) -> tuple[str, str, str]:
        """Reconstruct the PDM query key from a price row's variant condition.

        Returns ``(item, option_id, code)``. For a base / global-base price
        ``option_id``/``code`` are empty (queried via ``fnGetListPriceByItem``);
        for an ``=`` upcharge/increment row they identify the option value
        (queried via the option-increment ``fnGetListPrice``). The article item is
        rebuilt from the base article plus its dimension suffix (the
        base-article-length split); the global item is the variant condition.

        ``special_map`` remaps a special-case article code (one that carries a
        non-standard ``_`` suffix and so has no direct PDM item) to its confirmed
        PDM base item, so it re-prices from that base instead of being carried.
        """
        if special_map and not is_global and article in special_map:
            article = special_map[article]
        vc = (varcond or "").strip()
        if "=" in vc:
            left, opt = vc.rsplit(" ", 1) if " " in vc else ("", vc)
            item = left.strip() if is_global else (article or "") + left.strip()
            option_id, _, code = opt.partition("=")
            return item, option_id.strip(), code.strip()
        item = vc if is_global else (article or "") + vc
        return item, "", ""

    def make_pdm_lookup(self, mydate: str, site_id: int,
                        special_map: dict[str, str] | None = None):
        """A PDM-backed price lookup for the roll-over, mirroring both pCon
        *Update Pricing* buttons: base and global-base values come from
        ``fnGetListPriceByItem``; ``=`` upcharge/increment rows (article and
        global) come from the option-increment ``fnGetListPrice`` - so the new
        list is fully re-priced. Guarded and cached: a PDM outage degrades to
        carrying the old value rather than failing. ``special_map`` remaps
        special-case ``_``-suffixed article codes to their confirmed PDM base."""
        from repositories.pdm_repository import PDMRepository

        repo = PDMRepository(self.context)
        base_cache: dict[tuple, float | None] = {}
        inc_cache: dict[tuple, dict[tuple, float]] = {}
        state: dict[str, Any] = {"conn": None, "dead": False}

        def _conn():
            if state["conn"] is None:
                state["conn"] = repo.get_connection()
            return state["conn"]

        def _base(currency, item):
            key = (currency, item)
            if key not in base_cache:
                try:
                    got = repo.fetch_item_base_prices([item], currency, mydate, _conn())
                    base_cache[key] = float(got[0].price) if got and got[0].price is not None else None
                except Exception:
                    state["dead"] = True
                    base_cache[key] = None
            return base_cache[key]

        def _increments(currency, item):
            key = (currency, item)
            if key not in inc_cache:
                found: dict[tuple, float] = {}
                try:
                    for r in repo.fetch_item_option_increment_prices(
                            [item], currency, mydate, site_id, _conn()):
                        if getattr(r, "IncPrice", None) is not None:
                            found[(str(r.OptionId), str(r.Code).replace("#", ""))] = float(r.IncPrice)
                except Exception:
                    state["dead"] = True
                inc_cache[key] = found
            return inc_cache[key]

        def lookup(currency, is_global, article, varcond, level):
            if state["dead"]:
                return None
            item, option_id, code = self._lookup_key(is_global, article, varcond, special_map)
            if not item:
                return None
            if option_id:
                return _increments(currency, item).get((option_id, code))
            return _base(currency, item)

        def warm_base(currency, items, progress=None):
            """Bulk-load base list prices for many items in chunked queries (vs
            one round-trip per item), so a big package re-prices in seconds.
            ``progress(n)`` is called with each chunk's size so the caller can
            show a running count while the slow PDM pricing is in flight."""
            todo = sorted({it for it in items if it and (currency, it) not in base_cache})
            for start in range(0, len(todo), _WARM_CHUNK):
                chunk = todo[start:start + _WARM_CHUNK]
                try:
                    got = repo.fetch_item_base_prices(chunk, currency, mydate, _conn())
                    found = {str(r.Item): (float(r.price) if r.price is not None else None) for r in got}
                except Exception:
                    state["dead"] = True
                    return
                for it in chunk:
                    base_cache[(currency, it)] = found.get(it)
                if progress:
                    progress(len(chunk))

        def warm_increments(currency, items, progress=None):
            """Bulk-load option-increment prices for many items in chunked
            queries, keyed back per item. ``progress(n)`` reports each chunk."""
            todo = sorted({it for it in items if it and (currency, it) not in inc_cache})
            for start in range(0, len(todo), _WARM_CHUNK):
                chunk = todo[start:start + _WARM_CHUNK]
                by_item: dict[str, dict[tuple, float]] = {}
                try:
                    for r in repo.fetch_item_option_increment_prices(
                            chunk, currency, mydate, site_id, _conn()):
                        if getattr(r, "IncPrice", None) is not None:
                            by_item.setdefault(str(r.Item), {})[
                                (str(r.OptionId), str(r.Code).replace("#", ""))] = float(r.IncPrice)
                except Exception:
                    state["dead"] = True
                    return
                for it in chunk:
                    inc_cache[(currency, it)] = by_item.get(it, {})
                if progress:
                    progress(len(chunk))

        lookup.warm_base = warm_base
        lookup.warm_increments = warm_increments
        return lookup

    # -- special-case (underscore) article mapping ----------------------

    def _special_map_path(self) -> Path:
        return Path(__file__).resolve().parents[1] / "cache" / _SPECIAL_MAP_NAME

    def load_special_map(self) -> dict[str, str]:
        """Confirmed special-case article-code -> PDM base-item mappings."""
        path = self._special_map_path()
        out: dict[str, str] = {}
        if path.is_file():
            with path.open("r", encoding=_ENCODING, newline="") as fh:
                for row in csv.reader(fh):
                    if len(row) >= 2 and row[0] and row[0] != "Article":
                        out[row[0]] = row[1]
        return out

    def save_special_map(self, mapping: dict[str, str]) -> None:
        """Merge and persist confirmed special-case article mappings."""
        merged = self.load_special_map()
        merged.update({k: v for k, v in mapping.items() if v})
        path = self._special_map_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding=_ENCODING, newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["Article", "BaseItem"])
            for key in sorted(merged):
                writer.writerow([key, merged[key]])

    def scan_special_articles(
        self, packages, mydate: str, site_id: int, currencies=("EUR", "GBP")
    ) -> list[dict[str, Any]]:
        """Special-case OCD article codes (a non-standard ``_`` suffix) whose
        direct code has NO PDM item - so the roll would carry the old value.

        For each, suggests the base part (before the first ``_``) and previews
        its PDM price. Articles that resolve directly are skipped (not special).
        Returns review records: ``{package, article, base, base_prices,
        suggested, known}`` (``known`` = already in the saved map)."""
        from repositories.pdm_repository import PDMRepository

        repo = PDMRepository(self.context)
        conn = repo.get_connection()
        known = self.load_special_map()
        out: list[dict[str, Any]] = []
        seen: set[str] = set()

        def price(item, cur):
            try:
                r = repo._execute(
                    "SELECT dbo.fnGetListPriceByItem(?, ?, ?, ?, NULL) AS p",
                    (item, cur, mydate, site_id), connection=conn)
                return float(r[0].p) if r and r[0].p is not None else None
            except Exception:
                return None

        for pkg in packages:
            mdb = Path(pkg)
            try:
                arts = self.context.mdb_service.read_table(
                    mdb, "SELECT DISTINCT com_ArticleCode FROM tCOMd_Article "
                         "WHERE com_ArticleCode LIKE '%[_]%'")
            except Exception:
                continue
            for a in arts:
                code = str(a.get("com_ArticleCode") or "")
                if not code or "_" not in code or code in seen:
                    continue
                seen.add(code)
                if any(price(code, c) is not None for c in currencies):
                    continue  # resolves directly -> not a special case
                base = known.get(code) or code.split("_", 1)[0]
                base_prices = {c: price(base, c) for c in currencies}
                out.append({
                    "package": mdb.parent.name, "article": code, "base": base,
                    "base_prices": base_prices,
                    "suggested": any(v is not None for v in base_prices.values()),
                    "known": code in known})
        return out

    def apply_special_articles(
        self, mdb: str | Path, base_map: dict[str, str], mydate: str,
        site_id: int, stage=None,
    ) -> tuple[int, str | None]:
        """Re-price ONLY the given special-case articles' rows, in place, in the
        package's OPEN price lists - everything else is left untouched (it was
        already updated by the bulk roll). ``base_map`` = ``{article: PDM base}``.
        Returns ``(rows_updated, error)``. Runs on the already-rolled list, so it
        also fixes specials without re-rolling the whole package."""
        mdb = Path(mdb)
        svc = self.context.mdb_service
        if not svc.is_available():
            return 0, "32-bit MDB bridge unavailable."
        articles = [a for a in base_map if a]
        if not articles:
            return 0, None
        lookup = self.make_pdm_lookup(mydate, site_id, special_map=base_map)
        open_lists = {
            r["com_PriceListID"]: str(r.get("sys_ISOCurrencyCode") or "")
            for r in svc.read_table(
                mdb, "SELECT com_PriceListID, com_PriceListLabel, sys_ISOCurrencyCode, "
                     "com_PriceValidTo FROM tCOMd_PriceList2")
            if self._is_open_ymd(r.get("com_PriceValidTo"))
            and self._is_dated_list(str(r.get("com_PriceListLabel") or ""))}
        codes_sql = ",".join("'" + a.replace("'", "''") + "'" for a in articles)
        ops: list[dict[str, Any]] = []
        for list_id, currency in open_lists.items():
            rows = svc.read_table(
                mdb, "SELECT p.com_PriceID, a.com_ArticleCode, p.com_VariantCondition, "
                     "p.com_PriceLevelCode, p.com_PriceValue FROM tCOMd_Price p "
                     "INNER JOIN tCOMd_Article a ON p.com_ArticleID = a.com_ArticleID "
                     f"WHERE p.com_PriceListID = {list_id} AND a.com_ArticleCode IN ({codes_sql})")
            for r in rows:
                old_val = float(r.get("com_PriceValue") or 0)
                fresh = lookup(currency, False, str(r.get("com_ArticleCode") or ""),
                               str(r.get("com_VariantCondition") or ""),
                               str(r.get("com_PriceLevelCode") or "B"))
                if fresh is not None and float(fresh) != old_val:
                    ops.append({"op": "update", "table": "tCOMd_Price",
                                "set": {"com_PriceValue": float(fresh)},
                                "where": {"com_PriceID": r["com_PriceID"]}})
            if stage:
                stage(f"{mdb.parent.name} [{currency}]: {len(ops)} special update(s)")
        if not ops:
            return 0, None
        batch = svc.execute_batch(mdb, ops, transaction=True)
        return (len(ops) if batch.ok else 0), (None if batch.ok else batch.first_error())

    def roll_over_package_mdb(
        self, mdb: str | Path, effective_ymd: str, token: str,
        price_lookup=None, apply: bool = True, stage=None,
        special_map: dict[str, str] | None = None,
    ) -> PackageRoll:
        """Roll one OCD MDB: for each open ``tCOMd_PriceList2`` (validity 9999),
        copy its ``tCOMd_Price``/``tCOMd_GlobalPrice`` rows into a new list with
        refreshed values and end-date the old list."""
        mdb = Path(mdb)
        result = PackageRoll(package=str(mdb))
        if not self.context.mdb_service.is_available():
            result.error = "32-bit MDB bridge unavailable."
            return result
        svc = self.context.mdb_service
        old_end = self.context.price_list_service._day_before(effective_ymd)
        lists = svc.read_table(
            mdb, "SELECT com_PriceListID, com_PriceListLabel, sys_ISOCurrencyCode, "
                 "com_PriceValidFrom, com_PriceValidTo FROM tCOMd_PriceList2")
        # Group the open, dated lists by currency. Real packages sometimes carry a
        # stale extra open list (an old one that was never end-dated); per currency
        # we roll only the NEWEST and end-date every open one, so the package ends
        # with a single open list per currency and never a duplicate target.
        groups: dict[str, dict[str, Any]] = {}
        for r in lists:
            label = str(r.get("com_PriceListLabel") or "")
            if not self._is_open_ymd(r.get("com_PriceValidTo")) or not self._is_dated_list(label):
                continue
            ccy = str(r.get("sys_ISOCurrencyCode") or "")
            grp = groups.setdefault(ccy, {"rows": [], "done": False, "newest": None})
            grp["rows"].append(r)
            if self.new_list_name(label, token) == label:
                grp["done"] = True  # already carries the token (resumable re-run)
            vf = self._bridge_ymd(r.get("com_PriceValidFrom"))
            if grp["newest"] is None or vf > self._bridge_ymd(grp["newest"].get("com_PriceValidFrom")):
                grp["newest"] = r

        pending: list[tuple[str, dict, str, list]] = []
        for ccy, grp in groups.items():
            target = self.new_list_name(str(grp["newest"].get("com_PriceListLabel") or ""), token)
            if grp["done"]:
                result.lists.append(ListRoll(
                    currency=ccy, old_list=target, new_list=target, status="done"))
                continue
            pending.append((ccy, grp["newest"], target,
                            [x["com_PriceListID"] for x in grp["rows"]]))
        if not pending:
            result.applied = apply
            return result
        next_list = self._max_referenced_list_id(mdb)
        list_proto = self._mdb_prototype(mdb, "tCOMd_PriceList2", None)
        src_pk = pending[0][1]["com_PriceListID"]
        price_proto = self._mdb_prototype(mdb, "tCOMd_Price", src_pk)
        global_proto = self._mdb_prototype(mdb, "tCOMd_GlobalPrice", src_pk)
        next_price = self._mdb_next_id(mdb, "tCOMd_Price", "com_PriceID")
        next_global = self._mdb_next_id(mdb, "tCOMd_GlobalPrice", "com_GlobalPriceID")
        next_drpl = self._mdb_next_id(
            mdb, "tCOMd_DistributionRegionPriceList", "com_DistributionRegionPriceListID")

        # Distribution-region links pointing at a price list that no longer
        # exists in tCOMd_PriceList2 - left behind when a prior roll's PriceList2
        # rows were reverted (e.g. via SVN) but its region links were not. We
        # drop them so a half-reverted package updates cleanly (no full import)
        # and no stale link keeps claiming the current/default list.
        valid_list_ids = {
            r.get("com_PriceListID")
            for r in svc.read_table(mdb, "SELECT com_PriceListID FROM tCOMd_PriceList2")}
        orphan_ids = {
            link.get("com_PriceListID")
            for link in svc.read_table(
                mdb, "SELECT com_PriceListID FROM tCOMd_DistributionRegionPriceList")
            if link.get("com_PriceListID") not in valid_list_ids}

        ops: list[dict[str, Any]] = []
        special_carried: set[str] = set()  # underscore articles with no PDM price
        for pl in orphan_ids:  # remove the stale links to non-existent lists
            ops.append({"op": "delete", "table": "tCOMd_DistributionRegionPriceList",
                        "where": {"com_PriceListID": pl}})
        for currency, src, new_label, open_pks in pending:
            old_pk = src["com_PriceListID"]
            label = str(src.get("com_PriceListLabel") or "")
            next_list += 1
            new_pk = next_list
            lr = ListRoll(currency=currency, old_list=label, new_list=new_label)
            ops.append({"op": "insert", "table": "tCOMd_PriceList2", "rows": [self._mdb_list_row(
                list_proto, new_pk, new_label, new_label, currency, effective_ymd)]})
            for pk in open_pks:  # end-date every open list of this currency
                ops.append({"op": "update", "table": "tCOMd_PriceList2",
                            "set": {"com_PriceValidTo": _mdb_date_literal(old_end)},
                            "where": {"com_PriceListID": pk}})

            # Assign the new list to the SAME distribution regions as its source
            # and mark every assignment as the default (current) list; the old
            # open lists we just end-dated are cleared below so the new one wins.
            src_links = list(svc.read_table(
                mdb, "SELECT com_DistributionRegionID "
                     f"FROM tCOMd_DistributionRegionPriceList WHERE com_PriceListID = {old_pk}"))
            for rl in src_links:
                ops.append({"op": "insert", "table": "tCOMd_DistributionRegionPriceList", "rows": [{
                    "com_DistributionRegionPriceListID": next_drpl,
                    "com_DistributionRegionID": rl.get("com_DistributionRegionID"),
                    "com_PriceListID": new_pk,
                    "com_DefaultPriceList": True,
                    "com_StatusInfoID": None}]})
                next_drpl += 1
            for pk in open_pks:
                ops.append({"op": "update", "table": "tCOMd_DistributionRegionPriceList",
                            "set": {"com_DefaultPriceList": False},
                            "where": {"com_PriceListID": pk}})

            # Read the source list's rows once, then bulk-warm PDM prices for all
            # their items in a couple of queries (instead of one round-trip per
            # row - which made a big package look frozen for minutes).
            price_src = list(svc.read_table(
                mdb, "SELECT p.com_ArticleID, a.com_ArticleCode, p.com_VariantCondition, "
                     "p.com_PriceLevelCode, p.com_PriceValue, p.com_TextID FROM tCOMd_Price p "
                     "INNER JOIN tCOMd_Article a ON p.com_ArticleID = a.com_ArticleID "
                     f"WHERE p.com_PriceListID = {old_pk}"))
            global_src = list(svc.read_table(
                mdb, "SELECT com_PackageID, com_VariantCondition, com_PriceValue, com_TextID "
                     f"FROM tCOMd_GlobalPrice WHERE com_PriceListID = {old_pk}"))
            if price_lookup is not None and hasattr(price_lookup, "warm_base"):
                base_items: set[str] = set()
                inc_items: set[str] = set()
                for r in price_src:
                    item, oid, _ = self._lookup_key(
                        False, str(r.get("com_ArticleCode") or ""),
                        str(r.get("com_VariantCondition") or ""), special_map)
                    (inc_items if oid else base_items).add(item)
                for r in global_src:
                    item, oid, _ = self._lookup_key(
                        True, "", str(r.get("com_VariantCondition") or ""), special_map)
                    (inc_items if oid else base_items).add(item)
                total_items = len(base_items) + len(inc_items)
                done = 0

                def _tick(n: int) -> None:
                    nonlocal done
                    done += n
                    if stage:
                        stage(f"{mdb.parent.name} [{currency}]: priced "
                              f"{done}/{total_items} items from PDM...")

                if stage:
                    stage(f"{mdb.parent.name} [{currency}]: pricing "
                          f"{total_items} items from PDM...")
                price_lookup.warm_base(currency, base_items, progress=_tick)
                price_lookup.warm_increments(currency, inc_items, progress=_tick)

            for r in price_src:
                old_val = float(r.get("com_PriceValue") or 0)
                varcond = str(r.get("com_VariantCondition") or "")
                level = str(r.get("com_PriceLevelCode") or "B")
                fresh = (price_lookup(currency, False, str(r.get("com_ArticleCode") or ""),
                                      varcond, level) if price_lookup else None)
                value = old_val if fresh is None else float(fresh)
                lr.rows += 1
                lr.carried += fresh is None
                lr.priced += fresh is not None
                lr.changed += fresh is not None and value != old_val
                if fresh is None:
                    code = str(r.get("com_ArticleCode") or "")
                    if "_" in code:
                        special_carried.add(code)
                if apply:
                    ops.append({"op": "insert", "table": "tCOMd_Price", "rows": [{
                        **price_proto, "com_PriceID": next_price, "com_ArticleID": r["com_ArticleID"],
                        "com_PriceListID": new_pk, "com_PriceLevelCode": level,
                        "com_PriceValue": value, "com_VariantCondition": varcond,
                        "com_TextID": r.get("com_TextID"), "sys_ISOCurrencyCode": currency,
                        "com_PriceValidFrom": _mdb_date_literal(effective_ymd),
                        "com_PriceValidTo": _mdb_date_literal("99991231")}]})
                    next_price += 1
            for r in global_src:
                old_val = float(r.get("com_PriceValue") or 0)
                varcond = str(r.get("com_VariantCondition") or "")
                fresh = (price_lookup(currency, True, "", varcond, "")
                         if price_lookup else None)
                value = old_val if fresh is None else float(fresh)
                lr.rows += 1
                lr.carried += fresh is None
                lr.priced += fresh is not None
                lr.changed += fresh is not None and value != old_val
                if apply:
                    ops.append({"op": "insert", "table": "tCOMd_GlobalPrice", "rows": [{
                        **global_proto, "com_GlobalPriceID": next_global,
                        "com_PackageID": r.get("com_PackageID"), "com_PriceListID": new_pk,
                        "com_PriceValue": value, "com_VariantCondition": varcond,
                        "com_TextID": r.get("com_TextID"), "sys_ISOCurrencyCode": currency,
                        "com_PriceValidFrom": _mdb_date_literal(effective_ymd),
                        "com_PriceValidTo": _mdb_date_literal("99991231")}]})
                    next_global += 1
            result.lists.append(lr)

        if apply and ops:
            if stage:
                stage(f"{mdb.parent.name}: writing {len(ops)} change(s)...")
            # One transaction per package: all-or-nothing, so an interrupted run
            # never leaves a package half-rolled (a re-run then skips or redoes it).
            batch = svc.execute_batch(mdb, ops, transaction=True)
            result.applied = batch.ok
            result.error = batch.first_error()
            for lr in result.lists:
                if lr.status != "done":
                    lr.status = "done" if batch.ok else "pending"
        result.special_carried = sorted(special_carried)
        return result

    # -- XOCD helpers (shared by the roll-over) -------------------------

    def _register_xocd_list(self, folder: Path, list_id: str, label: str) -> None:
        """Add the new list to xocd_pricelists.csv (idempotent)."""
        path = folder / "xocd_pricelists.csv"
        rows: list[list[str]] = []
        if path.is_file():
            with path.open("r", encoding=_ENCODING, newline="") as fh:
                rows = [r for r in csv.reader(fh, delimiter=_DELIM) if r]
        if any(r and r[0] == list_id for r in rows):
            return
        rows.append([list_id, label])
        self._write_rows(path, rows)

    @staticmethod
    def _num(value: Any) -> str:
        """Plain numeric string (no trailing ``.0`` on whole numbers)."""
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return str(value)

    @staticmethod
    def _write_rows(path: Path, rows: list[list[str]]) -> None:
        with path.open("w", encoding=_ENCODING, newline="") as fh:
            csv.writer(fh, delimiter=_DELIM, lineterminator=_LINEEND).writerows(rows)

    @staticmethod
    def _write_rows_atomic(path: Path, rows: list[list[str]]) -> None:
        """Write via a temp file + atomic replace so an interrupted run never
        leaves a half-written package."""
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding=_ENCODING, newline="") as fh:
            csv.writer(fh, delimiter=_DELIM, lineterminator=_LINEEND).writerows(rows)
        os.replace(tmp, path)

    # -- MDB helpers (shared by the roll-over) --------------------------

    def _mdb_prototype(
        self, mdb: Path, table: str, list_pk: Any
    ) -> dict[str, Any]:
        """A boilerplate row from the table (scoped to a list where given), minus
        its autonumber PK, to seed NOT-NULL columns on new rows."""
        where = f" WHERE com_PriceListID = {list_pk}" if list_pk is not None else ""
        rows = self.context.mdb_service.read_table(mdb, f"SELECT TOP 1 * FROM [{table}]{where}")
        if not rows:
            rows = self.context.mdb_service.read_table(mdb, f"SELECT TOP 1 * FROM [{table}]")
        if not rows:
            return {}
        proto = dict(rows[0])
        # Drop this table's autonumber PK (set explicitly per new row) + scratch cols.
        pk = {"tCOMd_Price": "com_PriceID", "tCOMd_GlobalPrice": "com_GlobalPriceID",
              "tCOMd_PriceList2": "com_PriceListID"}.get(table)
        proto.pop(pk, None)
        for col in [c for c in proto if c.startswith("sys_tmp")]:
            proto.pop(col, None)
        # Any DateTime column reads back as the bridge's '/Date(ms)/'; re-inserting
        # that string is a type mismatch, so turn it into an Access date literal.
        for col, val in proto.items():
            if isinstance(val, str) and "/Date(" in val:
                proto[col] = _mdb_date_literal(self._bridge_ymd(val))
        return proto

    def _mdb_next_id(self, mdb: Path, table: str, pk: str) -> int:
        """Next free integer PK for a table."""
        rows = self.context.mdb_service.read_table(mdb, f"SELECT MAX([{pk}]) AS m FROM [{table}]")
        top = rows[0].get("m") if rows else None
        return int(top) + 1 if top is not None else 1

    def _max_referenced_list_id(self, mdb: Path) -> int:
        """Highest ``com_PriceListID`` referenced anywhere in the package.

        A new list is allocated ABOVE this, not just above ``tCOMd_PriceList2``'s
        max - so a partially-reverted package (where a related table still holds
        rows for a list id that no longer exists in ``tCOMd_PriceList2``) never
        makes the roll REUSE that id, which would collide on that table's
        ``(region, list)`` / ``(list, ...)`` unique index."""
        top = 0
        for table in ("tCOMd_PriceList2", "tCOMd_Price", "tCOMd_GlobalPrice",
                      "tCOMd_DistributionRegionPriceList"):
            rows = self.context.mdb_service.read_table(
                mdb, f"SELECT MAX(com_PriceListID) AS m FROM [{table}]")
            m = rows[0].get("m") if rows else None
            if m is not None:
                top = max(top, int(m))
        return top

    @staticmethod
    def _mdb_list_row(
        proto: dict[str, Any], pk: int, list_id: str, label: str,
        currency: str, date_from: str,
    ) -> dict[str, Any]:
        return {**proto, **{
            "com_PriceListID": pk, "com_PriceListLabel": list_id,
            "com_PriceTypeCode": "S", "com_UseMultipleScopes": False,
            "sys_ISOCurrencyCode": currency,
            "com_PriceValidFrom": _mdb_date_literal(date_from),
            "com_PriceValidTo": _mdb_date_literal("99991231"),
        }}
