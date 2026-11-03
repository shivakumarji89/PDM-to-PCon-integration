"""Catalogue discovery over an OCD repository (read-only, stdlib only).

Layout: ``<root>/<program>/<region>/<version>/db/ocd_article.csv`` where
``<root>`` is the ``hmx`` repository folder. The hierarchy shown to the user
comes straight from the data:

* manufacturer - the ``manufacturer`` column of ``ocd_article``,
* program      - the range folder under ``<root>``,
* series       - the ``series`` column of ``ocd_article``.

Article labels are the short texts of ``ocd_artshorttext``. OCD carries no
pCon variant code, so articles have none.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

from services.ocd_engine.csv_loader import OcdCsvLoader

#: Region folders are searched in this order; the article table is region independent.
_PREFERRED_REGION = "ANY"
_LANGUAGE_PREFERENCE = ("en", "en-us", "en-gb", "de")


class CatalogueError(Exception):
    """The catalogue root cannot be read; the message is shown to the user."""


@dataclass(frozen=True)
class OcdProgram:
    """One manufacturer's articles within one range folder."""

    program: str                    # range folder name
    manufacturer_id: str
    series_ids: tuple[str, ...]
    db_dir: Path
    article_count: int = 0


@dataclass(frozen=True)
class OcdArticle:
    article_number: str
    label: str
    series_id: str
    program: str


@dataclass
class CatalogueScan:
    root: Path
    programs: list[OcdProgram] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)   # (range folder, reason)
    fingerprint: str = ""             # content fingerprint of the repository this scan read (see ``fingerprint``)

    def manufacturers(self) -> list[str]:
        return sorted({p.manufacturer_id for p in self.programs}, key=str.lower)

    def programs_for(self, manufacturer_id: str) -> list[OcdProgram]:
        return sorted((p for p in self.programs if p.manufacturer_id == manufacturer_id),
                      key=lambda p: p.program.lower())


def find_db_dir(program_dir: Path) -> Path | None:
    """The ``db`` folder holding ``ocd_article.csv`` (preferred region, highest version)."""
    regions = sorted(
        (d for d in program_dir.iterdir() if d.is_dir() and not d.name.startswith(".")),
        key=lambda d: (d.name != _PREFERRED_REGION, d.name),
    )
    for region in regions:
        versions = sorted((d for d in region.iterdir() if d.is_dir() and d.name.isdigit()),
                          key=lambda d: int(d.name), reverse=True)
        for version in versions:
            db = version / "db"
            if (db / "ocd_article.csv").is_file():
                return db
    return None


#: Files whose content the catalogue (manufacturer/program/series/article list and labels) is built from.
CATALOGUE_FILES = ("ocd_article.csv", "pdata.ocd_article.inp_descr",
                   "ocd_artshorttext.csv", "pdata.ocd_artshorttext.inp_descr")

#: Process-wide record of the last catalogue each repository root was loaded with, so a second page instance
#: (or a re-initialised page) starts from it instead of reloading unchanged data.
_LOADED: dict[str, tuple[str, "CatalogueScan"]] = {}


def remember_loaded(scan: "CatalogueScan") -> None:
    _LOADED[str(scan.root)] = (scan.fingerprint, scan)


def recall_loaded(root: str | Path) -> "CatalogueScan | None":
    found = _LOADED.get(str(root))
    return found[1] if found else None


def forget_loaded(root: str | Path | None = None) -> None:
    if root is None:
        _LOADED.clear()
    else:
        _LOADED.pop(str(root), None)


class OcdCatalogueService:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root) if str(root or "").strip() else None
        self._loader = OcdCsvLoader()
        self._digests: dict[Path, tuple[int, int, str]] = {}     # file -> (size, mtime_ns, sha256 of content)
        self.scans = 0                                            # catalogue reads performed (for diagnostics/tests)
        self.fingerprints = 0
        self._scan_cache: dict[str, tuple[tuple[str, int, int], list[OcdProgram], tuple[str, str] | None]] = {}

    def _checked_root(self) -> Path:
        if self.root is None:
            raise CatalogueError("No OCD repository folder is configured.")
        if not self.root.is_dir():
            raise CatalogueError(f"OCD repository folder not found: {self.root}")
        return self.root

    def _digest(self, path: Path) -> str:
        """sha256 of a file's content, re-read only when its size or modification time changed."""
        try:
            stat = path.stat()
        except OSError:
            return "-"
        cached = self._digests.get(path)
        if cached is not None and cached[:2] == (stat.st_size, stat.st_mtime_ns):
            return cached[2]
        sha = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                sha.update(block)
        self._digests[path] = (stat.st_size, stat.st_mtime_ns, sha.hexdigest())
        return sha.hexdigest()

    def fingerprint(self) -> str:
        """Deterministic content fingerprint of everything the catalogue is built from.

        For every range folder (name, in sorted order) the sha256 of each of :data:`CATALOGUE_FILES` in the range's
        chosen ``db`` folder (``-`` when absent; a range without OCD data contributes ``-``). The fingerprint
        contains no absolute path, timestamp or object identity, so the same data in another folder, a touched file
        or a new service instance gives the same value; any change to an article row, a label or a column layout
        gives a different one. Files are hashed once and re-hashed only when their size or mtime changes, so a
        repeated check is a directory listing plus one ``stat`` per file - no catalogue is loaded.
        """
        root = self._checked_root()
        self.fingerprints += 1
        lines: list[str] = []
        try:
            folders = sorted((d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")),
                             key=lambda d: d.name.lower())
        except OSError as exc:
            raise CatalogueError(f"Cannot read {root}: {exc}") from exc
        for folder in folders:
            try:
                db = find_db_dir(folder)
            except OSError:
                db = None
            parts = ["-"] if db is None else [f"{name}={self._digest(db / name)}" for name in CATALOGUE_FILES]
            lines.append(f"{folder.name}" + ";".join(parts))
        return hashlib.sha256(chr(10).join(lines).encode("utf-8")).hexdigest()

    def scan(self, progress=None) -> CatalogueScan:
        """Read changed catalogue article tables only; reuse unchanged parsed entries."""
        self.scans += 1
        root = self._checked_root()
        try:
            folders = sorted((d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")),
                             key=lambda d: d.name.lower())
        except OSError as exc:
            raise CatalogueError(f"Cannot read {root}: {exc}") from exc
        result = CatalogueScan(root=root)
        next_cache: dict[str, tuple[tuple[str, int, int], list[OcdProgram], tuple[str, str] | None]] = {}
        for index, folder in enumerate(folders):
            if progress is not None:
                progress(index, len(folders), folder.name)
            try:
                db = find_db_dir(folder)
                if db is None:
                    signature = ("", 0, 0)
                    skipped = (folder.name, "no OCD data (ocd_article.csv)")
                    programs: list[OcdProgram] = []
                else:
                    stat = (db / "ocd_article.csv").stat()
                    signature = (str(db), stat.st_mtime_ns, stat.st_size)
                    cached = self._scan_cache.get(folder.name)
                    if cached is not None and cached[0] == signature:
                        programs, skipped = cached[1], cached[2]
                    else:
                        rows = self._loader.read_table(db, "article")
                        by_manufacturer: dict[str, dict[str, int]] = {}
                        for row in rows:
                            manufacturer = (row.get("manufacturer") or "").strip()
                            if not manufacturer or not (row.get("article_nr") or "").strip():
                                continue
                            counts = by_manufacturer.setdefault(manufacturer, {})
                            series = (row.get("series") or "").strip()
                            counts[series] = counts.get(series, 0) + 1
                        programs = [OcdProgram(folder.name, manufacturer,
                            tuple(sorted(series for series in counts if series)), db,
                            sum(counts.values())) for manufacturer, counts in by_manufacturer.items()]
                        skipped = (folder.name, "no articles") if not programs else None
            except OSError as exc:
                signature = ("", 0, 0)
                programs = []
                skipped = (folder.name, f"unreadable: {exc}")
            next_cache[folder.name] = (signature, programs, skipped)
            result.programs.extend(programs)
            if skipped is not None:
                result.skipped.append(skipped)
        self._scan_cache = next_cache
        result.fingerprint = self.fingerprint()
        return result

    def _short_texts(self, db_dir: Path) -> dict[str, str]:
        return texts_by_number(self._loader.read_table(db_dir, "artshorttext"))

    def list_articles(self, program: OcdProgram, series_id: str = "") -> list[OcdArticle]:
        """Articles of ``program`` (one manufacturer in one range), optionally one series."""
        try:
            rows = self._loader.read_table(program.db_dir, "article")
            texts = self._short_texts(program.db_dir)
        except OSError as exc:
            raise CatalogueError(f"Cannot read articles of {program.program}: {exc}") from exc
        found: dict[str, OcdArticle] = {}
        for row in rows:
            number = (row.get("article_nr") or "").strip()
            if (not number or (row.get("manufacturer") or "").strip() != program.manufacturer_id
                    or number in found):
                continue
            series = (row.get("series") or "").strip()
            if series_id and series != series_id:
                continue
            found[number] = OcdArticle(
                article_number=number, label=texts.get((row.get("short_textnr") or "").strip(), ""),
                series_id=series, program=program.program,
            )
        return sorted(found.values(), key=lambda a: a.article_number)


def texts_by_number(rows) -> dict[str, str]:
    """Label per ``textnr`` from rows of any OCD text table (artshorttext, propertytext, propvaluetext...).

    All of them share ``textnr, language, line_nr, text``; the preferred language wins, else the first.
    """
    per_text: dict[str, dict[str, list[tuple[int, str]]]] = {}
    for row in rows:
        number = (row.get("textnr") or "").strip()
        language = (row.get("language") or "").strip().lower()
        try:
            line = int((row.get("line_nr") or "0").strip() or 0)
        except ValueError:
            line = 0
        per_text.setdefault(number, {}).setdefault(language, []).append(
            (line, (row.get("text") or "").strip()))
    labels: dict[str, str] = {}
    for number, by_language in per_text.items():
        language = next((l for l in _LANGUAGE_PREFERENCE if l in by_language), None)
        if language is None:
            language = sorted(by_language)[0]
        labels[number] = " ".join(t for _, t in sorted(by_language[language]) if t)
    return labels


__all__ = ["CATALOGUE_FILES", "forget_loaded", "recall_loaded", "remember_loaded", "CatalogueError", "CatalogueScan", "OcdArticle", "OcdCatalogueService", "OcdProgram", "find_db_dir",
           "texts_by_number"]
