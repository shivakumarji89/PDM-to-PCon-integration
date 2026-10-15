"""Linked-directory handling and zero-byte table classification."""
import os
import sys
from pathlib import Path

import pytest

from models.metatype_scan import BuildStatus, EntryKind, TableState
from services.metatype.repository_scanner import MetatypeRepositoryScanner, _Entry
from tests.test_metatype_repository_scanner import SCHEMA, SCHEMA_TABLES, codes, evidence, make_family


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "hmx"
    path.mkdir()
    return path


@pytest.fixture
def outside(tmp_path):
    """A complete Metatype family *outside* the repository root."""
    base = tmp_path / "outside"
    base.mkdir()
    make_family(base, "ext")
    return base


class Spy(MetatypeRepositoryScanner):
    """Records every directory listed and every schema read."""

    def __init__(self):
        self.listed: list[str] = []
        self.read: list[str] = []

    def _list_dir(self, path):
        self.listed.append(os.path.normcase(os.path.abspath(path)))
        return super()._list_dir(path)

    def _read_schema_text(self, path):
        self.read.append(os.path.normcase(os.path.abspath(path)))
        return super()._read_schema_text(path)

    def touched(self, folder: Path) -> list[str]:
        prefix = os.path.normcase(os.path.abspath(folder))
        return [p for p in self.listed + self.read if p.startswith(prefix)]


def make_windows_junction(link: Path, target: Path) -> None:
    """Create a directory junction without spawning a process (a subprocess spawn hung in full runs)."""
    try:
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
    except (ImportError, AttributeError, OSError) as exc:
        pytest.skip(f"cannot create junction: {exc}")


def make_link(kind: str, link: Path, target: Path) -> None:
    if kind == "junction":
        if sys.platform != "win32":
            pytest.skip("directory junctions exist only on Windows")
        make_windows_junction(link, target)
    else:
        try:
            os.symlink(target, link, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            pytest.skip(f"cannot create directory symlink (OS permission): {exc}")


# 1. linked directories ---------------------------------------------------------
@pytest.mark.parametrize("kind", ["symlink", "junction"])
def test_linked_family_directory_is_not_followed(root, outside, kind):
    make_family(root, "real")
    make_link(kind, root / "linked", outside / "ext")
    spy = Spy()
    result = spy.scan(root)

    linked = result.family("linked")
    assert codes(linked.warnings) == ["LINKED_DIRECTORY_SKIPPED"]
    assert linked.numbered_directories == [] and linked.other_directories == []
    assert linked.entry_kind is EntryKind.UNCLASSIFIED
    assert linked.classification.rule == "uncertain.linked_directory_not_followed"
    assert spy.touched(outside) == []                     # external contents never inspected
    assert result.family("real").classification.status is BuildStatus.BUILT
    assert (result.summary.family_count, result.summary.unclassified_count) == (1, 1)


@pytest.mark.parametrize("kind", ["symlink", "junction"])
def test_linked_numbered_directory_is_not_followed(root, outside, kind):
    (root / "fam").mkdir()
    make_link(kind, root / "fam" / "1", outside / "ext" / "1")
    spy = Spy()
    family = spy.scan(root).family("fam")

    assert "LINKED_DIRECTORY_SKIPPED" in codes(family.warnings)
    assert family.numbered_directories == []
    assert family.entry_kind is EntryKind.UNCLASSIFIED            # not typed by following the link
    assert family.classification.rule == "family.no_numbered_directory"
    assert spy.touched(outside) == []


def test_linked_directories_are_skipped_in_simulation_without_link_privileges(root, outside):
    """Runs everywhere: the scanner is told these real directories are links."""
    make_family(root, "fam")
    make_family(root, "whole_link")
    link_paths = {
        os.path.normcase(str(root / "whole_link")),
        os.path.normcase(str(root / "fam" / "1")),
    }

    class Linked(Spy):
        def _list_dir(self, path):
            entries = super()._list_dir(path)
            return [
                _Entry(e.name, e.path, e.is_dir, e.is_file, e.size, e.stat_error,
                       is_link=os.path.normcase(e.path) in link_paths)
                for e in entries
            ]

    spy = Linked()
    result = spy.scan(root)

    for name in ("whole_link", "fam"):
        family = result.family(name)
        assert "LINKED_DIRECTORY_SKIPPED" in codes(family.warnings)
        assert family.numbered_directories == [] and family.entry_kind is EntryKind.UNCLASSIFIED
    # The linked targets were never listed or read (only the family-level listing of "fam").
    assert spy.touched(root / "whole_link") == []
    assert spy.touched(root / "fam" / "1") == []
    assert result.summary.family_count == 0


def test_linked_schema_file_is_reported_and_not_read(root):
    data = make_family(root, "fam")
    schema_path = os.path.normcase(str(data / "mt.inp_descr"))

    class Linked(Spy):
        def _list_dir(self, path):
            return [
                _Entry(e.name, e.path, e.is_dir, e.is_file, e.size, e.stat_error,
                       is_link=os.path.normcase(e.path) == schema_path)
                for e in super()._list_dir(path)
            ]

    spy = Linked()
    directory = spy.scan(root).family("fam").numbered_directories[0]
    assert "SCHEMA_LINKED" in codes(directory.errors)
    assert "LINKED_FILE_NOT_FOLLOWED" in codes(directory.warnings)
    assert spy.read == []
    assert directory.classification.status is BuildStatus.UNCERTAIN


def test_ordinary_directories_still_scan_normally(root):
    make_family(root, "plain")
    result = Spy().scan(root)
    family = result.family("plain")

    assert family.classification.status is BuildStatus.BUILT
    assert not [c for c in codes(family.warnings) if c.startswith("LINKED")]
    assert family.other_directories == ["ANY", "EURO"]


# 2. zero-byte table classification ---------------------------------------------
def scan_family(root, name):
    return MetatypeRepositoryScanner().scan(root).family(name)


def test_zero_byte_core_table_is_uncertain(root):
    make_family(root, "core0", populate=("go_articles",))
    family = scan_family(root, "core0")
    ev = evidence(family.classification)

    assert family.classification.status is BuildStatus.UNCERTAIN
    assert "go_types.csv: empty" in ev["core tables (go_types, go_articles)"].observed
    assert "go_types" not in ev["zero-byte required tables (non-core)"].observed
    assert "AMBIGUOUS_BUILD_STATE" in codes(family.warnings)
    assert "core tables not populated" in family.classification.summary


def test_zero_byte_non_core_required_table_stays_built_with_explicit_evidence(root):
    make_family(root, "req0")          # go_properties and go_texts are zero bytes
    family = scan_family(root, "req0")
    ev = evidence(family.classification)

    assert family.classification.status is BuildStatus.BUILT
    note = ev["zero-byte required tables (non-core)"]
    assert note.supports == "info"
    assert note.observed.startswith("go_properties, go_texts - ")
    assert "unused tables should be empty" in note.observed and "not verifiable" in note.observed
    assert "go_properties, go_texts" in family.classification.summary
    assert "not verifiable" in family.classification.summary
    assert not family.errors and "AMBIGUOUS_BUILD_STATE" not in codes(family.warnings)


def test_zero_byte_optional_table_is_reported_separately(root):
    make_family(root, "opt0", populate=("go_types", "go_articles", "go_properties", "go_texts"))
    family = scan_family(root, "opt0")
    ev = evidence(family.classification)

    assert family.classification.status is BuildStatus.BUILT
    assert ev["zero-byte optional tables"].observed == "go_propindex, go_propmapping"
    assert ev["zero-byte required tables (non-core)"].observed == "none"
    assert family.warnings == []                              # present but empty: no warning


def test_zero_byte_obsolete_non_optional_table_is_its_own_category(root):
    data = make_family(root, "obs0", populate=SCHEMA_TABLES)
    (data / "mt.inp_descr").write_text(SCHEMA + "table   go_feedback\tgo_feedback.csv\t\tcsv\n")
    (data / "go_feedback.csv").write_text("")
    family = scan_family(root, "obs0")
    ev = evidence(family.classification)

    assert family.classification.status is BuildStatus.BUILT
    assert ev["zero-byte obsolete tables"].observed == "go_feedback"
    assert ev["zero-byte optional tables"].observed == "none"
    assert ev["zero-byte required tables (non-core)"].observed == "none"


def test_missing_required_table_is_uncertain_not_a_zero_byte_case(root):
    make_family(root, "miss", skip=("go_properties",))
    family = scan_family(root, "miss")
    directory = family.numbered_directories[0]
    ev = evidence(family.classification)

    assert family.classification.status is BuildStatus.UNCERTAIN
    assert ev["declared tables missing"].observed == "go_properties"
    assert "go_properties" not in ev["zero-byte required tables (non-core)"].observed
    assert [t.state for t in directory.expected_tables if t.table == "go_properties"] == [TableState.MISSING]
    assert "AMBIGUOUS_BUILD_STATE" in codes(family.warnings)


def test_fully_populated_family_is_cleanly_built(root):
    make_family(root, "full", populate=SCHEMA_TABLES)
    family = scan_family(root, "full")
    ev = evidence(family.classification)

    assert family.classification.status is BuildStatus.BUILT
    assert family.classification.rule == "built.schema_ebase_core_data"
    for label in ("zero-byte required tables (non-core)", "zero-byte optional tables",
                  "zero-byte obsolete tables", "declared optional tables missing"):
        assert ev[label].observed == "none"
    assert "zero bytes" not in family.classification.summary
    assert family.warnings == [] and family.errors == []


# real-repository rules, reproduced with synthetic fixtures ----------------------
def test_real_repository_classification_rules_on_synthetic_fixtures(root):
    make_family(root, "typical")                                                # empty non-core tables
    make_family(root, "no_propindex", skip=("go_propindex", "go_propmapping"))  # 16 real families
    make_family(root, "leeway_like", bat=False)                                 # compiled, no .bat
    make_family(root, "accessories_like", schema=False, ebase=False, tools=False, bat=False)
    geometry = root / "comma_like" / "1"                                        # geometry-only family
    geometry.mkdir(parents=True)
    (geometry / "odb.ebase").write_bytes(b"x")
    (geometry / "odb.inp_descr").write_text("x")
    (root / "catalogue_like" / "1").mkdir(parents=True)

    result = MetatypeRepositoryScanner().scan(root)
    status = {f.family_id: (f.entry_kind.value, f.classification.status.value) for f in result.families}
    assert status == {
        "typical": ("product_family", "built"),
        "no_propindex": ("product_family", "built"),
        "leeway_like": ("product_family", "built"),
        "accessories_like": ("product_family", "uncertain"),
        "comma_like": ("product_family", "unbuilt"),
        "catalogue_like": ("unclassified", "unbuilt"),
    }
    assert codes(result.family("no_propindex").warnings).count("MISSING_OBSOLETE_TABLE") == 1
    assert codes(result.family("leeway_like").warnings).count("BUILD_TOOL_MISSING") == 1
    s = result.summary
    assert (s.family_count, s.built, s.unbuilt, s.uncertain, s.unclassified_count) == (5, 3, 1, 1, 1)
