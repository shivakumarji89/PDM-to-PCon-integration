"""Metatype repository scanner: synthetic-tree tests (no real HMX access)."""
import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from core.application_context import ApplicationContext
from core.config import AppConfig
from core.enums import WorkflowStep
from core.modules import WorkbenchModule, module_workflows
from models.metatype_scan import BuildStatus, ScanStatus, TableState
from services.metatype.metatype_repository_service import MetatypeRepositoryService
from services.metatype.repository_scanner import MetatypeRepositoryScanner, format_scan_summary

SCHEMA_TABLES = (
    "go_types", "go_articles", "go_properties", "go_propindex", "go_propmapping", "go_texts",
)
SCHEMA = "# schema\nname go_tables\n\n" + "".join(
    f"table   {t}\t{t}.csv\t\tcsv\nfields  1\nfield   1  id\t\tvstring\tdelim ;\n" for t in SCHEMA_TABLES
)


def make_family(
    root: Path, name: str, *, schema=True, ebase=True, tools=True, bat=True,
    populate=("go_types", "go_articles"), skip=(), zero=("go_properties", "go_texts"),
) -> Path:
    """Create ``root/<name>/1`` with the requested Metatype indicators."""
    data = root / name / "1"
    data.mkdir(parents=True)
    for currency in ("ANY", "EURO"):
        (root / name / currency / "1").mkdir(parents=True)
    (data / "odb.ebase").write_bytes(b"odb")
    if schema:
        (data / "mt.inp_descr").write_text(SCHEMA, encoding="utf-8")
    for table in SCHEMA_TABLES:
        if table in skip:
            continue
        content = "A;B;C\n" if table in populate else ""
        if table in zero and table not in populate:
            content = ""
        (data / f"{table}.csv").write_text(content, encoding="utf-8")
    if ebase:
        (data / f"{name}.ebase").write_bytes(b"ebase-bytes")
    if tools:
        (data / "ebmkdb.exe").write_bytes(b"exe")
    if bat:
        (data / "make_ebase.bat").write_text("pause\n")
    return data


def evidence(classification):
    return {e.indicator: e for e in classification.evidence}


def codes(issues):
    return [i.code for i in issues]


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "hmx"
    path.mkdir()
    return path


def scan(root):
    return MetatypeRepositoryScanner().scan(root)


# 1 ---------------------------------------------------------------------------
def test_built_family_with_build_indicators_and_ebase(root):
    make_family(root, "alpha")
    result = scan(root)
    family = result.family("alpha")

    assert result.status is ScanStatus.OK
    assert family.classification.status is BuildStatus.BUILT
    assert family.classification.rule == "built.schema_ebase_core_data"
    ev = evidence(family.classification)
    assert ev["mt.inp_descr"].observed == "present" and ev["mt.inp_descr"].supports == "built"
    assert "alpha.ebase" in ev["compiled .ebase"].observed
    assert ev["core tables (go_types, go_articles)"].supports == "built"
    assert ev["ebmkdb.exe"].supports == "info"
    # odb.ebase is not a Metatype output and must not count as one.
    directory = family.numbered_directories[0]
    assert directory.other_ebase_files == ["odb.ebase"]
    assert result.summary.built == 1
    # The currency directories are listed, never entered.
    assert family.other_directories == ["ANY", "EURO"]


# 2 ---------------------------------------------------------------------------
def test_unbuilt_family_has_no_metatype_indicators(root):
    data = root / "beta" / "1"
    data.mkdir(parents=True)
    (data / "odb.ebase").write_bytes(b"odb")
    (data / "odb.inp_descr").write_text("x")
    family = scan(root).family("beta")

    assert family.classification.status is BuildStatus.UNBUILT
    assert family.classification.rule == "unbuilt.no_metatype_indicators"
    ev = evidence(family.classification)
    assert ev["mt.inp_descr"].observed == "absent" and ev["go_* files"].observed == "0 found"
    assert not family.warnings and not family.errors


# 3 ---------------------------------------------------------------------------
def test_missing_required_table_makes_family_uncertain(root):
    make_family(root, "gamma", skip=("go_properties",))
    directory = scan(root).family("gamma").numbered_directories[0]

    assert directory.missing_tables == ["go_properties"]
    assert directory.classification.status is BuildStatus.UNCERTAIN
    ev = evidence(directory.classification)
    assert ev["declared tables missing"].observed == "go_properties"
    assert "AMBIGUOUS_BUILD_STATE" in codes(directory.warnings)
    missing = [t for t in directory.expected_tables if t.state is TableState.MISSING]
    assert [t.table for t in missing] == ["go_properties"]


def test_missing_obsolete_tables_warn_but_do_not_block_built(root):
    make_family(root, "delta", skip=("go_propindex", "go_propmapping"))
    directory = scan(root).family("delta").numbered_directories[0]

    assert directory.classification.status is BuildStatus.BUILT
    assert directory.missing_tables == ["go_propindex", "go_propmapping"]
    assert all(t.obsolete for t in directory.expected_tables if t.state is TableState.MISSING)
    assert "MISSING_OBSOLETE_TABLE" in codes(directory.warnings)
    assert evidence(directory.classification)["declared optional tables missing"].observed == (
        "go_propindex, go_propmapping"
    )


# 4 ---------------------------------------------------------------------------
def test_zero_byte_tables_are_reported(root):
    make_family(root, "eps")
    directory = scan(root).family("eps").numbered_directories[0]

    assert set(directory.zero_byte_tables) == {"go_properties", "go_propindex", "go_propmapping", "go_texts"}
    record = next(f for f in directory.go_files if f.name == "go_texts.csv")
    assert record.state is TableState.ZERO_BYTE and record.size_bytes == 0 and record.is_declared_table
    # Zero-byte non-core tables are normal ("unused tables should be empty").
    assert directory.classification.status is BuildStatus.BUILT


def test_zero_byte_core_table_is_not_built(root):
    make_family(root, "zeta", populate=("go_articles",))
    classification = scan(root).family("zeta").classification

    assert classification.status is BuildStatus.UNCERTAIN
    core = evidence(classification)["core tables (go_types, go_articles)"]
    assert "go_types.csv: empty" in core.observed and core.supports == "uncertain"


# 5 ---------------------------------------------------------------------------
@pytest.mark.parametrize("kind, code", [
    ("missing", "ROOT_NOT_FOUND"), ("file", "ROOT_NOT_DIRECTORY"), ("blank", "ROOT_NOT_CONFIGURED"),
])
def test_invalid_root_fails_cleanly(tmp_path, kind, code):
    target = {
        "missing": tmp_path / "nope",
        "file": tmp_path / "file.txt",
        "blank": "",
    }[kind]
    if kind == "file":
        target.write_text("x")
    result = scan(target)

    assert result.status is ScanStatus.FAILED
    assert codes(result.errors) == [code]
    assert result.families == []
    assert "ERROR" in format_scan_summary(result)


def test_unreadable_root_fails(root):
    class Denied(MetatypeRepositoryScanner):
        def _list_dir(self, path):
            raise PermissionError("denied")

    result = Denied().scan(root)
    assert result.status is ScanStatus.FAILED
    assert codes(result.errors) == ["ROOT_UNREADABLE"]


# 6 ---------------------------------------------------------------------------
def test_missing_build_tools_warn_but_stay_built(root):
    make_family(root, "eta", tools=False, bat=False)
    directory = scan(root).family("eta").numbered_directories[0]

    assert directory.classification.status is BuildStatus.BUILT
    assert codes(directory.warnings).count("BUILD_TOOL_MISSING") == 2
    ev = evidence(directory.classification)
    assert ev["ebmkdb.exe"].observed == "absent" and ev["make_ebase.bat"].observed == "absent"


def test_build_tool_alone_is_not_evidence(root):
    data = root / "theta" / "1"
    data.mkdir(parents=True)
    (data / "ebmkdb.exe").write_bytes(b"exe")
    family = scan(root).family("theta")

    assert family.classification.status is BuildStatus.UNBUILT
    assert "BUILD_TOOL_ALONE" in codes(family.warnings)


# 7 ---------------------------------------------------------------------------
@pytest.mark.parametrize("name, kwargs, expected", [
    ("csv_no_ebase", dict(ebase=False), "no compiled .ebase"),
    ("no_schema", dict(schema=False), "mt.inp_descr absent"),
    ("bat_only", dict(schema=False, ebase=False, populate=(), skip=SCHEMA_TABLES), "mt.inp_descr absent"),
])
def test_partial_indicators_are_uncertain(root, name, kwargs, expected):
    make_family(root, name, **kwargs)
    classification = scan(root).family(name).classification

    assert classification.status is BuildStatus.UNCERTAIN
    assert classification.rule == "uncertain.partial_or_conflicting_indicators"
    assert expected in classification.summary


def test_zero_byte_ebase_is_not_built(root):
    data = make_family(root, "iota")
    (data / "iota.ebase").write_bytes(b"")
    classification = scan(root).family("iota").classification

    assert classification.status is BuildStatus.UNCERTAIN
    assert "zero bytes" in classification.summary


def test_ebase_without_any_go_data_is_uncertain(root):
    data = root / "kappa" / "1"
    data.mkdir(parents=True)
    (data / "kappa.ebase").write_bytes(b"x")
    assert scan(root).family("kappa").classification.status is BuildStatus.UNCERTAIN


def test_unlisted_go_files_are_flagged_not_counted_as_tables(root):
    data = make_family(root, "lambda")
    (data / "go_texts.csv.bak").write_text("x")
    (data / "go_resetnativeprops.csv").write_text("")
    directory = scan(root).family("lambda").numbered_directories[0]

    unlisted = {f.name for f in directory.go_files if not f.is_declared_table}
    assert unlisted == {"go_texts.csv.bak", "go_resetnativeprops.csv"}
    assert codes(directory.warnings).count("UNLISTED_GO_FILE") == 2
    assert directory.classification.status is BuildStatus.BUILT


def test_family_without_numbered_directory_is_uncertain(root):
    (root / "empty_one").mkdir()
    (root / "odd").mkdir()
    (root / "odd" / "ANY").mkdir()
    result = scan(root)

    for name in ("empty_one", "odd"):
        family = result.family(name)
        assert family.classification.status is BuildStatus.UNCERTAIN
        assert family.classification.rule == "family.no_numbered_directory"
        assert "NO_NUMBERED_DIRECTORY" in codes(family.warnings)


def test_hidden_directories_and_loose_files_are_skipped(root):
    make_family(root, "mu")
    (root / ".svn").mkdir()
    (root / "readme.txt").write_text("x")
    result = scan(root)

    assert [f.family_id for f in result.families] == ["mu"]
    assert any(".svn" in line for line in result.scan_policy)


# 8 ---------------------------------------------------------------------------
class FailingScanner(MetatypeRepositoryScanner):
    def __init__(self, deny):
        self.deny = {os.path.normcase(str(p)) for p in deny}

    def _list_dir(self, path):
        if os.path.normcase(str(path)) in self.deny:
            raise PermissionError(f"[Errno 13] Permission denied: {path}")
        return super()._list_dir(path)


def test_unreadable_numbered_directory_is_recorded(root):
    make_family(root, "nu")
    result = FailingScanner([root / "nu" / "1"]).scan(root)
    family = result.family("nu")

    assert result.status is ScanStatus.PARTIAL
    assert family.classification.status is BuildStatus.UNCERTAIN
    assert family.classification.rule == "uncertain.inspection_failed"
    assert codes(family.errors) == ["DIRECTORY_UNREADABLE"]
    assert result.summary.families_with_errors == 1


def test_unreadable_family_directory_is_recorded(root):
    make_family(root, "xi")
    result = FailingScanner([root / "xi"]).scan(root)
    family = result.family("xi")

    assert codes(family.errors) == ["FAMILY_UNREADABLE"]
    assert family.classification.status is BuildStatus.UNCERTAIN


def test_unreadable_schema_is_recorded(root):
    make_family(root, "omicron")

    class BadSchema(MetatypeRepositoryScanner):
        def _read_schema_text(self, path):
            raise PermissionError("denied")

    directory = BadSchema().scan(root).family("omicron").numbered_directories[0]
    assert codes(directory.errors) == ["SCHEMA_UNREADABLE"]
    assert directory.classification.status is BuildStatus.UNCERTAIN


# 9 ---------------------------------------------------------------------------
def test_one_failing_family_does_not_stop_the_scan(root):
    make_family(root, "good_a")
    make_family(root, "boom")
    make_family(root, "good_b")

    class Exploding(MetatypeRepositoryScanner):
        def _scan_numbered(self, family, entry):
            if family.family_id == "boom":
                raise RuntimeError("unexpected")
            return super()._scan_numbered(family, entry)

    result = Exploding().scan(root)
    assert result.status is ScanStatus.PARTIAL
    assert [f.family_id for f in result.families] == ["boom", "good_a", "good_b"]
    assert result.family("boom").classification.status is BuildStatus.UNCERTAIN
    assert codes(result.family("boom").errors) == ["FAMILY_SCAN_FAILED"]
    assert result.family("good_a").classification.status is BuildStatus.BUILT
    assert result.family("good_b").classification.status is BuildStatus.BUILT
    # A family that could not be inspected cannot be typed: it is reported as
    # unclassified (with its error), never silently counted as built/unbuilt.
    assert result.family("boom").entry_kind.value == "unclassified"
    assert (result.summary.built, result.summary.uncertain, result.summary.unclassified_count) == (2, 0, 1)
    assert result.summary.families_with_errors == 1


# 10 --------------------------------------------------------------------------
def test_result_serialises_to_json_and_exports_outside_repository(root, tmp_path):
    make_family(root, "pi")
    make_family(root, "rho", schema=False)
    result = scan(root)

    document = json.loads(json.dumps(result.to_dict()))
    assert document["status"] == "ok" and document["schema_version"] == 1
    assert document["summary"]["family_count"] == 2
    family = next(f for f in document["families"] if f["family_id"] == "pi")
    assert family["classification"]["status"] == "built"
    assert family["numbered_directories"][0]["expected_tables"][0]["state"] in {"present", "zero_byte", "missing"}

    out = tmp_path / "reports" / "scan.json"
    MetatypeRepositoryService.export_json(result, out)
    assert json.loads(out.read_text(encoding="utf-8")) == document
    assert not out.with_suffix(".json.tmp").exists()

    with pytest.raises(ValueError):
        MetatypeRepositoryService.export_json(result, root / "pi" / "report.json")
    assert not (root / "pi" / "report.json").exists()


def test_scan_is_read_only_deterministic_and_rerunnable(root):
    make_family(root, "sigma")
    make_family(root, "tau", ebase=False)

    def snapshot():
        return sorted(
            (str(p.relative_to(root)), p.stat().st_size, p.stat().st_mtime_ns) for p in root.rglob("*")
        )

    before = snapshot()
    first, second = scan(root).to_dict(), scan(root).to_dict()
    assert snapshot() == before
    first.pop("scanned_at"), second.pop("scanned_at")
    assert first == second


# 11 --------------------------------------------------------------------------
def test_metatype_module_invokes_scanner_through_context(root):
    make_family(root, "upsilon")
    make_family(root, "phi", ebase=False)
    context = ApplicationContext(AppConfig(metatype_repository_root=str(root)))

    # The scanner is development-time backend logic: the runtime Metatype module offers the creation
    # workflow only, and repository analysis stays registered as a diagnostic page outside any module.
    assert WorkflowStep.METATYPE_REPOSITORY_ANALYSIS not in module_workflows(WorkbenchModule.METATYPE)
    assert module_workflows(WorkbenchModule.METATYPE) == (
        WorkflowStep.METATYPE_ARTICLES, WorkflowStep.METATYPE_PROPERTIES,
        WorkflowStep.METATYPE_VALUES, WorkflowStep.METATYPE_TEXTS,
        WorkflowStep.METATYPE_SETUP, WorkflowStep.METATYPE_RELATIONS,
        WorkflowStep.METATYPE_REVIEW,
    )
    assert WorkflowStep.METATYPE_REPOSITORY_ANALYSIS not in module_workflows(WorkbenchModule.DEVELOPMENT)
    service = context.metatype_repository_service
    assert service is context.get_service(MetatypeRepositoryService)
    assert service.last_result is None

    result = service.scan()
    assert result.repository_root == str(root)
    assert (result.summary.built, result.summary.uncertain) == (1, 1)
    assert service.last_result is result
    assert service.scan(root / "missing").status is ScanStatus.FAILED


def test_repository_analysis_page_shows_scan_result(root):
    from PySide6.QtWidgets import QApplication
    from ui.pages.metatype_repository_page import MetatypeRepositoryPage

    app = QApplication.instance() or QApplication([])
    make_family(root, "chi")
    make_family(root, "psi", schema=False)
    context = ApplicationContext(AppConfig(metatype_repository_root=str(root)))
    page = MetatypeRepositoryPage(context)

    assert not page.export_button.isEnabled()
    page.scan_button.click()
    rows = {page.table.item(r, 0).text(): page.table.item(r, 2).text() for r in range(page.table.rowCount())}
    assert rows == {"chi": "built", "psi": "uncertain"}
    assert page.export_button.isEnabled()
    assert "Built: 1" in page.summary_label.text()
    app.processEvents()
