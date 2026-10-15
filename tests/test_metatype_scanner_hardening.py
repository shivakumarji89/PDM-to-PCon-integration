"""Review follow-ups: workflow flag, entry typing, export safety, schema parsing."""
import json
import os
import sys
import types
from pathlib import Path

import pytest

import core.workflow as workflow_module
from core.enums import WorkflowStep
from core.modules import WorkbenchModule, module_workflows
from models.metatype_scan import BuildStatus, EntryKind, ScanStatus, TableState
from services.metatype.metatype_repository_service import MetatypeRepositoryService
from services.metatype.repository_scanner import (
    OBSOLETE_TABLES, OPTIONAL_TABLES, MetatypeRepositoryScanner, format_scan_summary,
)
from tests.test_metatype_repository_scanner import SCHEMA, codes, make_family
from tests.test_metatype_links_and_zero_bytes import make_windows_junction


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "hmx"
    path.mkdir()
    return path


def scan(root):
    return MetatypeRepositoryScanner().scan(root)


# 1. workflow registration vs. CET feature flag -------------------------------
def _load_workflow_with_cet_flag(enabled: bool):
    source = Path(workflow_module.__file__).read_text(encoding="utf-8")
    flag_line = "CET_SIF_VALIDATION_ENABLED = True"
    assert flag_line in source
    name = "core_workflow_flag_test"
    module = types.ModuleType(name)
    sys.modules[name] = module      # dataclasses resolves string annotations via sys.modules
    try:
        exec(compile(source.replace(flag_line, f"CET_SIF_VALIDATION_ENABLED = {enabled}"), "workflow", "exec"), module.__dict__)
    finally:
        sys.modules.pop(name, None)
    return module


@pytest.mark.parametrize("enabled", [True, False])
def test_metatype_workflow_registered_regardless_of_cet_flag(enabled):
    module = _load_workflow_with_cet_flag(enabled)
    steps = {item.step for item in module.WORKFLOW_ITEMS}

    assert WorkflowStep.METATYPE_REPOSITORY_ANALYSIS in steps
    assert (WorkflowStep.CET_SIF_VALIDATION in steps) is enabled
    # Every step a module exposes must have a workflow item (navigator/manager need it).
    for step in module_workflows(WorkbenchModule.METATYPE):
        assert step in steps


# 2. entry typing --------------------------------------------------------------
def test_entries_are_typed_from_file_evidence_only(root):
    make_family(root, "built_one")                                    # Metatype data
    product = root / "geometry_only" / "1"                            # OFML data, no Metatype
    product.mkdir(parents=True)
    (product / "odb.ebase").write_bytes(b"x")
    other = root / "catalogue_like" / "1"                             # no evidence at all
    other.mkdir(parents=True)
    (other / "brochure.pdf").write_bytes(b"x")
    (root / "empty_dir").mkdir()

    result = scan(root)
    kinds = {f.family_id: f.entry_kind for f in result.families}
    assert kinds == {
        "built_one": EntryKind.PRODUCT_FAMILY,
        "geometry_only": EntryKind.PRODUCT_FAMILY,
        "catalogue_like": EntryKind.UNCLASSIFIED,
        "empty_dir": EntryKind.UNCLASSIFIED,
    }
    assert result.family("geometry_only").classification.status is BuildStatus.UNBUILT
    assert "odb.ebase" in result.family("geometry_only").entry_kind_evidence[0].observed
    assert result.family("catalogue_like").entry_kind_evidence[0].supports == "uncertain"

    s = result.summary
    assert (s.family_count, s.series_count, s.unclassified_count) == (2, 2, 2)
    assert (s.built, s.unbuilt, s.uncertain) == (1, 1, 0)   # unclassified entries are not counted here
    assert result.series == ["built_one", "geometry_only"]
    text = format_scan_summary(result)
    assert "UNCLASSIFIED" in text and "catalogue_like" in text
    assert json.loads(json.dumps(result.to_dict()))["families"][0]["entry_kind"] in {"product_family", "unclassified"}


def test_unreadable_entry_is_unclassified_with_explicit_reason(root):
    make_family(root, "locked")

    class Denied(MetatypeRepositoryScanner):
        def _list_dir(self, path):
            if Path(path).name == "locked":
                raise PermissionError("denied")
            return super()._list_dir(path)

    family = Denied().scan(root).family("locked")
    assert family.entry_kind is EntryKind.UNCLASSIFIED
    assert "could not be typed" in family.entry_kind_evidence[0].observed


# 4. tables / parser -------------------------------------------------------------
def test_obsolete_and_optional_table_sets_match_the_manual_review():
    assert OBSOLETE_TABLES == {
        "go_propindex", "go_propmapping", "go_attptgeo", "go_metainfo",
        "go_feedback", "go_itemplates", "go_interactors",
    }
    assert OPTIONAL_TABLES == {"go_propindex", "go_propmapping"} and OPTIONAL_TABLES <= OBSOLETE_TABLES


def test_missing_obsolete_but_not_optional_table_blocks_built(root):
    data = make_family(root, "feedbacky")
    (data / "mt.inp_descr").write_text(SCHEMA + "table   go_feedback\tgo_feedback.csv\t\tcsv\n")
    directory = scan(root).family("feedbacky").numbered_directories[0]

    assert directory.missing_tables == ["go_feedback"]
    assert next(t for t in directory.expected_tables if t.table == "go_feedback").obsolete
    assert directory.classification.status is BuildStatus.UNCERTAIN


@pytest.mark.parametrize("schema_text", [
    "table go_types go_types.csv csv\nfields 1\n",                      # single spaces
    "TABLE\tgo_types\tgo_types.csv\tcsv\r\nfields 1\r\n",               # tabs, CRLF, upper case
    "# table go_ignored go_ignored.csv csv\ntable go_types go_types.csv csv\n",  # commented line
    "﻿table go_types go_types.csv csv\n",                           # BOM is not stripped: unresolved
])
def test_schema_parser_variants(root, schema_text):
    data = make_family(root, "parse", populate=("go_types", "go_articles"))
    (data / "mt.inp_descr").write_text(schema_text, encoding="utf-8", newline="")
    directory = scan(root).family("parse").numbered_directories[0]

    if schema_text.startswith("﻿"):
        # UNRESOLVED: no real file has a BOM (checked on all 49), so this is
        # recorded as "no tables declared" instead of guessed at.
        assert directory.expected_tables == [] and "AMBIGUOUS_BUILD_STATE" in codes(directory.warnings)
    else:
        assert [t.table for t in directory.expected_tables] == ["go_types"]
        assert "go_ignored" not in [t.table for t in directory.expected_tables]


def test_missing_schema_leaves_expected_tables_unknown(root):
    make_family(root, "noschema", schema=False)
    directory = scan(root).family("noschema").numbered_directories[0]
    assert directory.expected_tables_source == "" and directory.expected_tables == []
    assert directory.zero_byte_tables == [] and directory.missing_tables == []


# 3. export safety ------------------------------------------------------------
def _junction(link: Path, target: Path) -> None:
    if sys.platform != "win32":
        os.symlink(target, link, target_is_directory=True)
        return
    make_windows_junction(link, target)


def _symlink(link: Path, target: Path, directory: bool) -> None:
    try:
        os.symlink(target, link, target_is_directory=directory)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable: {exc}")


@pytest.fixture
def scanned(root, tmp_path):
    data = make_family(root, "fam")
    result = scan(root)
    assert result.status is ScanStatus.OK
    guard = data / "go_types.csv"
    return result, root, guard, guard.read_bytes(), tmp_path


def repo_listing(root: Path):
    return sorted((str(p.relative_to(root)), p.stat().st_size) for p in root.rglob("*"))


def test_export_rejects_direct_and_dotdot_paths_into_repository(scanned):
    result, root, _guard, _data, tmp = scanned
    before = repo_listing(root)
    for bad in (
        root / "fam" / "report.json",
        root / "fam" / ".." / "fam" / "1" / "report.json",
        tmp / "elsewhere" / ".." / "hmx" / "report.json",
        root,
        Path(str(root).upper()) / "report.json",     # case-insensitive filesystems
    ):
        with pytest.raises(ValueError):
            MetatypeRepositoryService.export_json(result, bad)
    assert repo_listing(root) == before


def test_export_rejects_junction_into_repository_and_creates_nothing(scanned):
    result, root, _guard, _data, tmp = scanned
    link = tmp / "junction"
    _junction(link, root / "fam")
    before = repo_listing(root)
    for bad in (link / "report.json", link / "newdir" / "report.json"):
        with pytest.raises(ValueError):
            MetatypeRepositoryService.export_json(result, bad)
    assert repo_listing(root) == before            # no file and no new directory


def test_export_rejects_symlinked_directory_into_repository(scanned):
    result, root, _guard, _data, tmp = scanned
    link = tmp / "symdir"
    _symlink(link, root, directory=True)
    before = repo_listing(root)
    with pytest.raises(ValueError):
        MetatypeRepositoryService.export_json(result, link / "fam" / "report.json")
    assert repo_listing(root) == before


def test_export_rejects_file_symlink_pointing_at_repository_file(scanned):
    result, _root, guard, original, tmp = scanned
    link = tmp / "report.json"
    _symlink(link, guard, directory=False)
    with pytest.raises(ValueError):
        MetatypeRepositoryService.export_json(result, link)
    assert guard.read_bytes() == original


def test_export_rejects_repository_root_reached_through_a_junction(root, tmp_path):
    make_family(root, "fam")
    link = tmp_path / "hmx_alias"
    _junction(link, root)
    result = scan(link)                              # repository_root is the alias
    before = repo_listing(root)
    with pytest.raises(ValueError):
        MetatypeRepositoryService.export_json(result, root / "report.json")   # real path of the same tree
    assert repo_listing(root) == before


def test_export_never_writes_through_existing_links_at_destination(scanned):
    result, _root, guard, original, tmp = scanned
    out = tmp / "out"
    out.mkdir()
    # Hostile leftovers: a *.tmp symlink and a hard link to a repository file.
    _symlink(out / "scan.json.tmp", guard, directory=False)
    try:
        os.link(guard, out / "scan.json")
    except OSError as exc:
        pytest.skip(f"hard links unavailable: {exc}")

    MetatypeRepositoryService.export_json(result, out / "scan.json")

    assert guard.read_bytes() == original                         # repository file untouched
    assert json.loads((out / "scan.json").read_text(encoding="utf-8"))["status"] == "ok"
    assert (out / "scan.json").stat().st_ino != guard.stat().st_ino   # link was replaced, not written through
    assert [p.name for p in out.glob("*.tmp")] == ["scan.json.tmp"]    # only the hostile one remains


def test_export_rejects_alternate_data_stream_names(scanned):
    result, _root, _guard, _data, tmp = scanned
    with pytest.raises(ValueError):
        MetatypeRepositoryService.export_json(result, tmp / "scan.json:stream")


def test_export_succeeds_for_a_safe_destination_and_cleans_up(scanned):
    result, _root, _guard, _data, tmp = scanned
    out = MetatypeRepositoryService.export_json(result, tmp / "new" / "deeper" / "scan.json")
    assert json.loads(out.read_text(encoding="utf-8")) == result.to_dict()
    assert list(out.parent.glob("*.tmp")) == []
