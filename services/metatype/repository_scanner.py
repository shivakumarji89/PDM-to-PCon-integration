"""Read-only scanner for the OFML ``hmx`` Metatype repository.

Discovers families, numbered data directories, ``go_*`` tables and build
indicators, and classifies each family as built / unbuilt / uncertain from
explicit rules. It performs no Qt work and never writes, renames, deletes or
executes anything; the only file content it reads is ``mt.inp_descr`` (to learn
which tables the family declares).

Layout the scanner relies on (REPOSITORY FACT, see
``docs/02_Domain/Engineering/Metatype.md`` section 2 and the scan notes):
``<root>/<family>/<number>/`` holds the Metatype data. Sibling directories such
as ``ANY``/``EURO``/``GBP``/``NOPRICE`` are listed but never entered.

Traversal is bounded to three directory levels (root -> family -> numbered
directory) and only directory *listings* are read below that, so the large
geometry/binary trees are never walked.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from services.metatype.schema_parser import MAX_SCHEMA_BYTES, parse_mt_schema
from models.metatype_scan import (
    BuildIndicator,
    BuildStatus,
    Classification,
    ClassificationEvidence,
    EntryKind,
    ExpectedTable,
    FamilyScan,
    GoFileRecord,
    MetatypeScanResult,
    NumberedDirectoryScan,
    ScanIssue,
    ScanStatus,
    ScanSummary,
    TableState,
)

SCANNER_VERSION = "1.0.0"

SCHEMA_FILE = "mt.inp_descr"
BUILD_TOOL = "ebmkdb.exe"
BUILD_SCRIPT = "make_ebase.bat"
#: Documented alternative name for a compiled Metatype database [MT section 5].
GENERIC_EBASE = "mt.ebase"
#: Tables without which no metatype exists [MT go_types / go_articles intro].
CORE_TABLES = ("go_types.csv", "go_articles.csv")
#: Tables whose manual heading (MT_1.18.0) says "(obsolete)": go_propindex line
#: 1215, go_propmapping 1241, go_attptgeo 2224, go_metainfo 2690, go_feedback
#: 2800, go_itemplates 3146, go_interactors 3250. Verified against the manual.
OBSOLETE_TABLES = frozenset({
    "go_propindex", "go_propmapping", "go_metainfo", "go_feedback",
    "go_attptgeo", "go_itemplates", "go_interactors",
})
#: Subset whose absence is tolerated. The manual says "all tables must be
#: present", but calls go_propindex "an optional ... representation" (line 1217)
#: and go_propmapping only has to match it. In all 49 real mt.inp_descr files
#: both declarations sit inside a comment block (not compiled, see
#: schema_parser), so they are never "declared" there; the tolerance only
#: matters for a schema that declares them live. UNRESOLVED: the manual does not call the other five
#: obsolete tables optional and no real family lacks them while declaring them,
#: so their absence stays blocking rather than guessed to be harmless.
OPTIONAL_TABLES = frozenset({"go_propindex", "go_propmapping"})
#: OFML product-data files seen in every product directory of the repository,
#: including families with no Metatype data (comma, knot, hush, ...).
PRODUCT_DATA_FILES = ("odb.inp_descr", "odb.ebase", "ofml.inp_descr", "ofml.ebase")


SCAN_POLICY = (
    "Traversal is limited to root -> family directory -> numbered directory; "
    "files inside numbered directories are listed, not recursed.",
    "Directories whose name starts with '.' (e.g. .svn) are skipped.",
    "Non-numbered family subdirectories (e.g. ANY, EURO, GBP, NOPRICE) are "
    "listed but never entered.",
    "Loose files in the root and in family directories are ignored.",
    "File timestamps are not used for classification.",
    "Nothing is executed, written or modified; only mt.inp_descr is read.",
    "Symbolic links and junctions are never followed: a linked family or numbered "
    "directory is skipped and reported as LINKED_DIRECTORY_SKIPPED. The configured "
    "root itself is used as given, even if it is a link.",
)


@dataclass(frozen=True)
class _Entry:
    name: str
    path: str
    is_dir: bool
    is_file: bool
    size: int | None
    stat_error: str = ""
    #: Symbolic link or Windows junction. Never followed.
    is_link: bool = False


class MetatypeRepositoryScanner:
    """Scan an ``hmx`` repository root and return a :class:`MetatypeScanResult`."""

    # -- filesystem seam (overridden in tests to simulate failures) ----------
    def _list_dir(self, path: Path) -> list[_Entry]:
        """List one directory. Raises ``OSError`` if it cannot be listed."""
        entries: list[_Entry] = []
        with os.scandir(path) as iterator:
            for item in iterator:
                is_dir = is_file = is_link = False
                size: int | None = None
                error = ""
                try:
                    is_link = item.is_symlink() or bool(getattr(item, "is_junction", lambda: False)())
                    is_dir = item.is_dir()
                    is_file = item.is_file()
                    if is_file and not is_link:  # a link's size would describe its target
                        size = item.stat().st_size
                except OSError as exc:
                    error = str(exc)
                entries.append(_Entry(item.name, item.path, is_dir, is_file, size, error, is_link))
        return sorted(entries, key=lambda entry: entry.name.casefold())

    def _read_schema_text(self, path: str) -> str:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_SCHEMA_BYTES)
        return raw.decode("utf-8", errors="replace")

    # -- public API ------------------------------------------------------------
    def scan(self, root: str | Path) -> MetatypeScanResult:
        root_path = Path(root) if str(root).strip() else Path("")
        result = MetatypeScanResult(
            repository_root=str(root),
            scanned_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            scanner_version=SCANNER_VERSION,
            status=ScanStatus.OK,
            scan_policy=list(SCAN_POLICY),
        )

        if not str(root).strip():
            return self._fail(result, "ROOT_NOT_CONFIGURED", "No repository root was provided.")
        try:
            if not root_path.exists():
                return self._fail(result, "ROOT_NOT_FOUND", "Repository root does not exist.")
            if not root_path.is_dir():
                return self._fail(result, "ROOT_NOT_DIRECTORY", "Repository root is not a directory.")
            entries = self._list_dir(root_path)
        except OSError as exc:
            return self._fail(result, "ROOT_UNREADABLE", f"Repository root cannot be read: {exc}")

        skipped_hidden = [e.name for e in entries if e.is_dir and e.name.startswith(".")]
        if skipped_hidden:
            result.scan_policy.append("Skipped hidden directories: " + ", ".join(skipped_hidden))

        for entry in entries:
            if not entry.is_dir or entry.name.startswith("."):
                continue
            try:
                family = self._linked_family(entry) if entry.is_link else self._scan_family(entry)
            except Exception as exc:  # one family must never end the scan
                family = FamilyScan(series_id=entry.name, family_id=entry.name, path=entry.path)
                family.errors.append(ScanIssue("FAMILY_SCAN_FAILED", f"{type(exc).__name__}: {exc}", entry.path))
                family.entry_kind_evidence = [ClassificationEvidence(
                    "inspection", "failed before the entry could be typed", "uncertain")]
                family.classification = Classification(
                    BuildStatus.UNCERTAIN, "uncertain.inspection_failed",
                    "The family could not be inspected.",
                    [ClassificationEvidence("inspection", f"{type(exc).__name__}: {exc}", "uncertain")],
                )
            result.families.append(family)

        self._finish(result)
        return result

    # -- families --------------------------------------------------------------
    @staticmethod
    def _linked_family(entry: _Entry) -> FamilyScan:
        """Report a linked root entry without listing or typing its target."""
        family = FamilyScan(series_id=entry.name, family_id=entry.name, path=entry.path)
        family.warnings.append(_linked_issue(entry))
        family.entry_kind_evidence = [ClassificationEvidence(
            "directory link", "not followed, so the entry could not be typed", "uncertain")]
        family.classification = Classification(
            BuildStatus.UNCERTAIN, "uncertain.linked_directory_not_followed",
            "The entry is a symbolic link or junction and was not followed.",
            [ClassificationEvidence("directory link", "skipped", "uncertain")],
        )
        return family

    def _scan_family(self, entry: _Entry) -> FamilyScan:
        family = FamilyScan(series_id=entry.name, family_id=entry.name, path=entry.path)
        try:
            children = self._list_dir(Path(entry.path))
        except OSError as exc:
            family.errors.append(ScanIssue("FAMILY_UNREADABLE", f"Cannot list family directory: {exc}", entry.path))
            family.entry_kind_evidence = [ClassificationEvidence(
                "family directory", "unreadable, so the entry could not be typed", "uncertain")]
            family.classification = Classification(
                BuildStatus.UNCERTAIN, "uncertain.inspection_failed",
                "The family directory could not be listed.",
                [ClassificationEvidence("family directory", f"unreadable: {exc}", "uncertain")],
            )
            return family

        for child in children:
            if not child.is_dir or child.name.startswith("."):
                continue
            if child.is_link:
                family.warnings.append(_linked_issue(child))
            if child.name.isdigit():
                if not child.is_link:
                    family.numbered_directories.append(self._scan_numbered(family, child))
            else:
                family.other_directories.append(child.name)

        if not family.numbered_directories:
            reason = "empty directory" if not children else "no numbered subdirectory"
            family.warnings.append(ScanIssue(
                "NO_NUMBERED_DIRECTORY",
                f"Unexpected layout: {reason}; Metatype data is expected in <family>/<number>/.",
                entry.path,
            ))
        for numbered in family.numbered_directories:
            family.warnings.extend(numbered.warnings)
            family.errors.extend(numbered.errors)
        family.classification = self._family_classification(family)
        self._assign_entry_kind(family)
        return family

    @staticmethod
    def _assign_entry_kind(family: FamilyScan) -> None:
        """Tag the entry from file evidence only; no names are special-cased."""
        evidence: list[ClassificationEvidence] = []
        for directory in family.numbered_directories:
            metatype = [i.name for i in directory.build_indicators if i.present and i.name.casefold() == SCHEMA_FILE]
            metatype += [f.name for f in directory.go_files]
            if metatype:
                evidence.append(ClassificationEvidence(
                    f"{directory.name}/ Metatype files", ", ".join(sorted(metatype)[:5]), "built"))
            if directory.product_data_files:
                evidence.append(ClassificationEvidence(
                    f"{directory.name}/ OFML product data", ", ".join(directory.product_data_files), "info"))
        if evidence:
            family.entry_kind = EntryKind.PRODUCT_FAMILY
        else:
            family.entry_kind = EntryKind.UNCLASSIFIED
            incomplete = any(d.errors for d in family.numbered_directories)
            evidence.append(ClassificationEvidence(
                "Metatype or OFML product-data files",
                "none found, but a numbered directory could not be fully inspected" if incomplete
                else "none found in any numbered directory",
                "uncertain"))
        family.entry_kind_evidence = evidence

    @staticmethod
    def _family_classification(family: FamilyScan) -> Classification:
        directories = family.numbered_directories
        if not directories:
            return Classification(
                BuildStatus.UNCERTAIN, "family.no_numbered_directory",
                "No numbered data directory was found, so no Metatype indicators could be evaluated.",
                [ClassificationEvidence("numbered directory", "none found", "uncertain")],
            )
        if len(directories) == 1:
            only = directories[0].classification
            assert only is not None
            return Classification(only.status, only.rule, only.summary, list(only.evidence))
        statuses = {d.classification.status for d in directories if d.classification}
        evidence = [
            ClassificationEvidence(f"directory {d.name}", d.classification.status.value, "info")
            for d in directories if d.classification
        ]
        if len(statuses) == 1:
            return Classification(
                next(iter(statuses)), "family.numbered_directories_agree",
                "All numbered directories received the same classification.", evidence,
            )
        return Classification(
            BuildStatus.UNCERTAIN, "family.numbered_directories_disagree",
            "Numbered directories have different classifications.", evidence,
        )

    # -- numbered directories --------------------------------------------------
    def _scan_numbered(self, family: FamilyScan, entry: _Entry) -> NumberedDirectoryScan:
        scan = NumberedDirectoryScan(name=entry.name, path=entry.path)
        try:
            entries = self._list_dir(Path(entry.path))
        except OSError as exc:
            scan.errors.append(ScanIssue("DIRECTORY_UNREADABLE", f"Cannot list directory: {exc}", entry.path))
            scan.classification = Classification(
                BuildStatus.UNCERTAIN, "uncertain.inspection_failed",
                "The directory could not be listed.",
                [ClassificationEvidence("directory", f"unreadable: {exc}", "uncertain")],
            )
            return scan

        files = {e.name.casefold(): e for e in entries if e.is_file}
        for item in entries:
            if item.stat_error:
                scan.errors.append(ScanIssue("ENTRY_STAT_FAILED", f"{item.name}: {item.stat_error}", item.path))
            if item.is_link and item.is_file:
                scan.warnings.append(ScanIssue(
                    "LINKED_FILE_NOT_FOLLOWED",
                    f"{item.name} is a link; its size and content were not read.", item.path,
                ))

        self._read_declared_tables(scan, files)
        self._record_go_files(scan, files)
        self._record_build_indicators(scan, files, family.family_id)
        scan.classification = self._classify(scan, files)
        return scan

    def _read_declared_tables(self, scan: NumberedDirectoryScan, files: dict[str, _Entry]) -> None:
        schema = files.get(SCHEMA_FILE)
        if schema is None:
            # Expected set stays unknown (never assumed). Whether that deserves a
            # warning depends on the other indicators, so _classify reports it.
            return
        if schema.is_link:
            scan.errors.append(ScanIssue(
                "SCHEMA_LINKED", f"{SCHEMA_FILE} is a link and was not read.", schema.path))
            return
        try:
            text = self._read_schema_text(schema.path)
        except OSError as exc:
            scan.errors.append(ScanIssue("SCHEMA_UNREADABLE", f"Cannot read {SCHEMA_FILE}: {exc}", schema.path))
            return
        # Compiled declarations only: tables inside "comment ... end comment"
        # blocks (go_propindex/go_propmapping in every real file) are skipped.
        declared = [(t.name, t.file_name) for t in parse_mt_schema(text)]
        if not declared:
            scan.warnings.append(ScanIssue(
                "SCHEMA_NO_TABLES", f"{SCHEMA_FILE} declares no tables; expected set unknown.", schema.path,
            ))
            return
        scan.expected_tables_source = SCHEMA_FILE
        for table, file_name in declared:
            found = files.get(file_name.casefold())
            if found is None:
                scan.expected_tables.append(ExpectedTable(
                    table, file_name, TableState.MISSING, obsolete=table.casefold() in OBSOLETE_TABLES,
                ))
                scan.missing_tables.append(table)
                continue
            state = TableState.ZERO_BYTE if found.size == 0 else TableState.PRESENT
            scan.expected_tables.append(ExpectedTable(
                table, file_name, state, found.path, found.size,
                obsolete=table.casefold() in OBSOLETE_TABLES,
            ))
            if state is TableState.ZERO_BYTE:
                scan.zero_byte_tables.append(table)

    @staticmethod
    def _record_go_files(scan: NumberedDirectoryScan, files: dict[str, _Entry]) -> None:
        declared_files = {e.file_name.casefold(): e.table for e in scan.expected_tables}
        for key, item in files.items():
            if not key.startswith("go_"):
                continue
            table = declared_files.get(key, "")
            state = TableState.ZERO_BYTE if item.size == 0 else TableState.PRESENT
            scan.go_files.append(GoFileRecord(
                name=item.name, path=item.path, size_bytes=item.size,
                is_declared_table=bool(table), table=table, state=state,
            ))
            if not table:
                scan.warnings.append(ScanIssue(
                    "UNLISTED_GO_FILE",
                    f"{item.name} is not a table declared by {SCHEMA_FILE} "
                    "(backup, variant, or table the schema omits).",
                    item.path,
                ))

    @staticmethod
    def _record_build_indicators(scan: NumberedDirectoryScan, files: dict[str, _Entry], family_id: str) -> None:
        def indicator(name: str, note: str = "") -> BuildIndicator:
            found = files.get(name.casefold())
            if found is None:
                return BuildIndicator(name, False, note=note)
            return BuildIndicator(found.name, True, found.path, found.size, note)

        family_ebase = f"{family_id}.ebase"
        scan.build_indicators = [
            indicator(SCHEMA_FILE, "schema for every go_* table"),
            indicator(BUILD_TOOL, "compiler; presence alone is not evidence of a build"),
            indicator(BUILD_SCRIPT, "build script; presence alone is not evidence of a build"),
            indicator(family_ebase, "compiled Metatype database named after the family"),
            indicator(GENERIC_EBASE, "alternative compiled name documented in MT section 5"),
        ]
        named = {family_ebase.casefold(), GENERIC_EBASE}
        scan.other_ebase_files = sorted(
            item.name for key, item in files.items() if key.endswith(".ebase") and key not in named
        )
        scan.product_data_files = sorted(files[name].name for name in PRODUCT_DATA_FILES if name in files)

    # -- classification --------------------------------------------------------
    def _classify(self, scan: NumberedDirectoryScan, files: dict[str, _Entry]) -> Classification:
        by_name = {i.name.casefold(): i for i in scan.build_indicators}
        schema = by_name[SCHEMA_FILE]
        tool = by_name[BUILD_TOOL]
        script = by_name[BUILD_SCRIPT]
        compiled = [i for i in scan.build_indicators if i.name.casefold().endswith(".ebase") and i.present]
        compiled_nonempty = [i for i in compiled if i.size_bytes]
        go_files_present = bool(scan.go_files)
        core = {name: files.get(name) for name in CORE_TABLES}
        core_populated = all(item is not None and bool(item.size) for item in core.values())
        expected_known = bool(scan.expected_tables_source)
        missing_required = [t for t in scan.missing_tables if t.casefold() not in OPTIONAL_TABLES]
        missing_obsolete = [t for t in scan.missing_tables if t.casefold() in OPTIONAL_TABLES]
        core_names = {name[:-4] for name in CORE_TABLES}
        zero = [t.table for t in scan.expected_tables if t.state is TableState.ZERO_BYTE]
        zero_optional = [t for t in zero if t.casefold() in OPTIONAL_TABLES]
        zero_obsolete = [t for t in zero if t.casefold() in OBSOLETE_TABLES - OPTIONAL_TABLES]
        zero_required = [
            t for t in zero
            if t.casefold() not in OBSOLETE_TABLES and t.casefold() not in core_names
        ]

        evidence = [
            ClassificationEvidence(
                SCHEMA_FILE, "present" if schema.present else "absent",
                "built" if schema.present else "unbuilt",
            ),
            ClassificationEvidence(
                "compiled .ebase",
                ", ".join(f"{i.name} ({i.size_bytes} bytes)" for i in compiled) or "absent",
                "built" if compiled_nonempty else "unbuilt",
            ),
            ClassificationEvidence(
                "go_* files", f"{len(scan.go_files)} found",
                "built" if go_files_present else "unbuilt",
            ),
            ClassificationEvidence(
                "core tables (go_types, go_articles)",
                ", ".join(
                    f"{name}: " + ("missing" if item is None else "empty" if not item.size else "populated")
                    for name, item in core.items()
                ),
                "built" if core_populated else "uncertain" if go_files_present else "unbuilt",
            ),
            ClassificationEvidence(
                "declared tables missing",
                ", ".join(missing_required) if missing_required
                else "none" if expected_known else "unknown (no schema)",
                "uncertain" if missing_required else "info",
            ),
            ClassificationEvidence(
                "declared optional tables missing",
                ", ".join(missing_obsolete) or "none",
                "info",
            ),
            ClassificationEvidence(
                "zero-byte required tables (non-core)", _zero_note(zero_required), "info"),
            ClassificationEvidence(
                "zero-byte optional tables", ", ".join(zero_optional) or "none", "info"),
            ClassificationEvidence(
                "zero-byte obsolete tables", ", ".join(zero_obsolete) or "none", "info"),
            ClassificationEvidence(BUILD_TOOL, "present" if tool.present else "absent", "info"),
            ClassificationEvidence(BUILD_SCRIPT, "present" if script.present else "absent", "info"),
        ]

        if scan.errors:
            return Classification(
                BuildStatus.UNCERTAIN, "uncertain.inspection_failed",
                "Errors occurred while inspecting this directory; indicators may be incomplete.",
                evidence + [ClassificationEvidence("errors", f"{len(scan.errors)} recorded", "uncertain")],
            )

        if schema.present and compiled_nonempty and core_populated and expected_known and not missing_required:
            if missing_obsolete:
                scan.warnings.append(ScanIssue(
                    "MISSING_OBSOLETE_TABLE",
                    "Optional (obsolete) declared table(s) have no file: " + ", ".join(missing_obsolete)
                    + ". The manual calls go_propindex optional and a compiled database exists.",
                    scan.path,
                ))
            for name, item in ((BUILD_TOOL, tool), (BUILD_SCRIPT, script)):
                if not item.present:
                    scan.warnings.append(ScanIssue(
                        "BUILD_TOOL_MISSING",
                        f"{name} not found. The compiled database exists, so the family is still "
                        "classified built, but it cannot be rebuilt from this directory.",
                        scan.path,
                    ))
            summary = (
                f"{SCHEMA_FILE}, a non-empty compiled database and populated core tables are all present, "
                "and every declared non-obsolete table has a file."
            )
            if zero_required:
                summary += (
                    f" {len(zero_required)} non-core required table(s) are zero bytes ("
                    + ", ".join(zero_required) + "): " + _ZERO_BYTE_REASON
                )
            return Classification(BuildStatus.BUILT, "built.schema_ebase_core_data", summary, evidence)

        metatype_indicators = (schema.present, bool(compiled), go_files_present, script.present)
        if not any(metatype_indicators):
            if tool.present:
                scan.warnings.append(ScanIssue(
                    "BUILD_TOOL_ALONE",
                    f"{BUILD_TOOL} is present without any Metatype indicator; ignored as evidence.",
                    scan.path,
                ))
            return Classification(
                BuildStatus.UNBUILT, "unbuilt.no_metatype_indicators",
                f"No go_* files, {SCHEMA_FILE}, compiled database or {BUILD_SCRIPT} were found.",
                evidence,
            )

        missing = []
        if not schema.present:
            missing.append(SCHEMA_FILE + " absent")
        if not compiled:
            missing.append("no compiled .ebase")
        elif not compiled_nonempty:
            missing.append("compiled .ebase is zero bytes")
        if not core_populated:
            missing.append("core tables not populated")
        if missing_required:
            missing.append(f"{len(missing_required)} declared table(s) missing")
        if schema.present and not expected_known:
            missing.append("declared tables could not be determined")
        scan.warnings.append(ScanIssue(
            "AMBIGUOUS_BUILD_STATE",
            "Some Metatype indicators are present but the set is incomplete: " + "; ".join(missing) + ".",
            scan.path,
        ))
        return Classification(
            BuildStatus.UNCERTAIN, "uncertain.partial_or_conflicting_indicators",
            "Metatype indicators are only partly present: " + "; ".join(missing) + ".",
            evidence,
        )

    # -- results ---------------------------------------------------------------
    @staticmethod
    def _fail(result: MetatypeScanResult, code: str, message: str) -> MetatypeScanResult:
        result.status = ScanStatus.FAILED
        result.errors.append(ScanIssue(code, message, result.repository_root))
        return result

    @staticmethod
    def _finish(result: MetatypeScanResult) -> None:
        summary = ScanSummary()
        for family in result.families:
            summary.families_with_errors += bool(family.errors)
            summary.families_with_warnings += bool(family.warnings)
            if family.entry_kind is not EntryKind.PRODUCT_FAMILY:
                summary.unclassified_count += 1
                continue
            status = family.classification.status if family.classification else BuildStatus.UNCERTAIN
            if status is BuildStatus.BUILT:
                summary.built += 1
            elif status is BuildStatus.UNBUILT:
                summary.unbuilt += 1
            else:
                summary.uncertain += 1
        products = [f for f in result.families if f.entry_kind is EntryKind.PRODUCT_FAMILY]
        summary.family_count = len(products)
        result.series = sorted({family.series_id for family in products}, key=str.casefold)
        summary.series_count = len(result.series)
        result.summary = summary
        if summary.families_with_errors or result.errors:
            result.status = ScanStatus.PARTIAL


def _linked_issue(entry: _Entry) -> ScanIssue:
    return ScanIssue(
        "LINKED_DIRECTORY_SKIPPED",
        f"{entry.name} is a symbolic link or junction; it was not followed or inspected.",
        entry.path,
    )


#: Why a zero-byte non-core required table does not by itself block "built".
#: DOCUMENTED: MT_1.18.0 section 2 "Unused tables should be empty". REPOSITORY
#: FACT: compiled families routinely have empty non-core tables (e.g. go_setup,
#: go_actions, go_proporder, even go_texts). UNRESOLVED: whether a given empty
#: table is intentionally unused cannot be verified from the file alone.
_ZERO_BYTE_REASON = (
    "allowed by the manual (unused tables should be empty) and common in compiled "
    "families, but not verifiable as intentionally unused."
)


def _zero_note(tables: list[str]) -> str:
    return f"{', '.join(tables)} - {_ZERO_BYTE_REASON}" if tables else "none"


def format_scan_summary(result: MetatypeScanResult) -> str:
    """Plain-text summary for consoles and logs (UIs should use the model)."""
    lines = [
        f"Metatype repository scan - {result.status.value}",
        f"  Root:    {result.repository_root}",
        f"  Scanned: {result.scanned_at} (scanner {result.scanner_version})",
    ]
    for issue in result.errors:
        lines.append(f"  ERROR [{issue.code}] {issue.message}")
    if result.status is ScanStatus.FAILED:
        return "\n".join(lines)
    s = result.summary
    lines += [
        f"  Series: {s.series_count}   Product families: {s.family_count}   Unclassified entries: {s.unclassified_count}",
        f"  Built: {s.built}   Unbuilt: {s.unbuilt}   Uncertain: {s.uncertain}",
        f"  Families with errors: {s.families_with_errors}   with warnings: {s.families_with_warnings}",
        "",
    ]
    products = [f for f in result.families if f.entry_kind is EntryKind.PRODUCT_FAMILY]
    for status in (BuildStatus.BUILT, BuildStatus.UNCERTAIN, BuildStatus.UNBUILT):
        group = [f for f in products if f.classification and f.classification.status is status]
        if not group:
            continue
        lines.append(f"{status.value.upper()} ({len(group)})")
        for family in group:
            note = family.classification.summary if status is BuildStatus.UNCERTAIN else ""
            lines.append(f"  - {family.family_id}" + (f": {note}" if note else ""))
    unclassified = [f for f in result.families if f.entry_kind is not EntryKind.PRODUCT_FAMILY]
    if unclassified:
        lines.append(f"UNCLASSIFIED - no Metatype or OFML product-data files ({len(unclassified)})")
        lines.extend(f"  - {f.family_id}" for f in unclassified)
    return "\n".join(lines)
