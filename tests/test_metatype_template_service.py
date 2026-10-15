from __future__ import annotations

import zipfile
from pathlib import Path

from services.metatype.metatype_template_service import MetatypeTemplateService


def make_archive(path: Path) -> Path:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("_emptyMT/mt.inp_descr", "schema")
        archive.writestr("_emptyMT/go_types.csv", "types")
        archive.writestr("_emptyMT/go_articles.csv", "")
        archive.writestr("_emptyMT/readme.txt", "readme")
    return path


def test_scratch_initialization_copies_all_template_files(tmp_path):
    root = tmp_path / "repo"
    series = root / "atlas"
    series.mkdir(parents=True)
    archive = make_archive(tmp_path / "templates.zip")

    result = MetatypeTemplateService(root, archive).initialize("atlas")

    target = series / "1"
    assert result.status == "initialized"
    assert set(result.copied) == {"mt.inp_descr", "go_types.csv", "go_articles.csv", "readme.txt"}
    assert (target / "mt.inp_descr").read_text() == "schema"
    assert (target / "go_types.csv").read_text() == "types"
    assert (target / "go_articles.csv").read_bytes() == b""
    assert not (target / "ebase").exists()


def test_existing_metatype_is_reused_without_modification(tmp_path):
    root = tmp_path / "repo"
    target = root / "atlas" / "1"
    target.mkdir(parents=True)
    (target / "mt.inp_descr").write_text("existing schema")
    (target / "go_types.csv").write_text("existing data")
    archive = make_archive(tmp_path / "templates.zip")

    result = MetatypeTemplateService(root, archive).initialize("atlas")

    assert result.status == "existing"
    assert (target / "mt.inp_descr").read_text() == "existing schema"
    assert (target / "go_types.csv").read_text() == "existing data"
    assert not (target / "go_articles.csv").exists()


def test_partial_series_is_reported_and_never_merged(tmp_path):
    root = tmp_path / "repo"
    target = root / "atlas" / "1"
    target.mkdir(parents=True)
    (target / "go_types.csv").write_text("partial")
    archive = make_archive(tmp_path / "templates.zip")
    service = MetatypeTemplateService(root, archive)

    result = service.inspect("atlas")
    initialized = service.initialize("atlas")

    assert result.status == "partial"
    assert "go_types.csv" in result.existing
    assert initialized.status == "partial"
    assert (target / "go_types.csv").read_text() == "partial"
    assert not (target / "mt.inp_descr").exists()


def test_initialization_refuses_name_conflicts_without_overwriting(tmp_path):
    root = tmp_path / "repo"
    target = root / "atlas" / "1"
    target.mkdir(parents=True)
    archive = make_archive(tmp_path / "templates.zip")
    # A race/conflict can occur after inspection; the copy method still refuses it.
    service = MetatypeTemplateService(root, archive)
    (target / "go_types.csv").write_text("keep")
    result = service.initialize("atlas")
    assert result.status == "partial"
    assert (target / "go_types.csv").read_text() == "keep"


def test_invalid_series_names_are_rejected(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    service = MetatypeTemplateService(root, tmp_path / "missing.zip")
    for name in ("../outside", ".", "..", "a/b", "a\\b"):
        try:
            service.series_directories(name)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected invalid series name to be rejected: {name}")
