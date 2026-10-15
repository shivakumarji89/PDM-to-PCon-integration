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


def test_existing_template_file_is_reported_as_template_conflict(tmp_path):
    root = tmp_path / "repo"
    target = root / "atlas" / "1"
    target.mkdir(parents=True)
    (target / "go_types.csv").write_text("partial")
    archive = make_archive(tmp_path / "templates.zip")
    service = MetatypeTemplateService(root, archive)

    result = service.inspect("atlas")
    initialized = service.initialize("atlas")

    assert result.status == "conflict"
    assert result.existing == ("go_types.csv",)
    assert initialized.status == "conflict"
    assert (target / "go_types.csv").read_text() == "partial"
    assert not (target / "mt.inp_descr").exists()


def test_initialization_refuses_name_conflicts_without_overwriting(tmp_path):
    root = tmp_path / "repo"
    target = root / "atlas" / "1"
    target.mkdir(parents=True)
    archive = make_archive(tmp_path / "templates.zip")
    # A race/conflict can occur after inspection; the copy method still refuses it.
    service = MetatypeTemplateService(root, archive)
    stale = service.inspect("atlas")
    (target / "go_types.csv").write_text("keep")
    service.inspect = lambda series: stale  # file appeared after the "empty" inspection
    result = service.initialize("atlas")
    assert result.status == "conflict"
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


import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

REAL_ARCHIVE = Path(__file__).resolve().parents[1] / "resources" / "_emptyMT.zip"


def snapshot(directory: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in directory.iterdir() if p.is_file()}


def test_real_bundled_archive_extracts_flat_into_numbered_directory(tmp_path):
    assert REAL_ARCHIVE.is_file()
    root = tmp_path / "repo"
    (root / "atlas").mkdir(parents=True)

    result = MetatypeTemplateService(root).initialize("atlas")

    target = root / "atlas" / "1"
    assert result.status == "initialized"
    assert not (target / "_emptyMT").exists()
    assert not (root / "atlas" / "_emptyMT").exists()
    with zipfile.ZipFile(REAL_ARCHIVE) as z:
        expected = {Path(i.filename).name: z.read(i) for i in z.infolist() if not i.is_dir()}
    assert snapshot(target) == expected
    assert "mt.inp_descr" in expected and "go_types.csv" in expected
    assert [p.name for p in target.iterdir() if p.is_dir()] == []  # no staging leftovers


def test_uses_existing_first_numbered_directory_when_empty(tmp_path):
    root = tmp_path / "repo"
    (root / "atlas" / "2").mkdir(parents=True)

    result = MetatypeTemplateService(root, make_archive(tmp_path / "t.zip")).initialize("atlas")

    assert result.status == "initialized"
    assert (root / "atlas" / "2" / "mt.inp_descr").is_file()
    assert not (root / "atlas" / "1").exists()


def test_unrelated_existing_files_do_not_block_template_initialization(tmp_path):
    root = tmp_path / "repo"
    target = root / "atlas" / "1"
    target.mkdir(parents=True)
    (target / "notes.txt").write_text("mine")

    result = MetatypeTemplateService(root, make_archive(tmp_path / "t.zip")).initialize("atlas")

    assert result.status == "initialized"
    assert (target / "notes.txt").read_bytes() == b"mine"
    assert (target / "mt.inp_descr").read_text() == "schema"
    assert (target / "go_types.csv").read_text() == "types"
    assert (target / "go_articles.csv").exists()


def test_missing_archive_raises_and_changes_nothing(tmp_path):
    root = tmp_path / "repo"
    (root / "atlas").mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        MetatypeTemplateService(root, tmp_path / "missing.zip").initialize("atlas")
    assert list((root / "atlas").iterdir()) == []


def test_corrupt_archive_raises_clear_error_and_changes_nothing(tmp_path):
    root = tmp_path / "repo"
    (root / "atlas").mkdir(parents=True)
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"this is not a zip file")
    with pytest.raises(ValueError, match="corrupt"):
        MetatypeTemplateService(root, bad).initialize("atlas")
    assert list((root / "atlas").iterdir()) == []


def test_corrupt_member_data_leaves_no_files(tmp_path):
    root = tmp_path / "repo"
    (root / "atlas").mkdir(parents=True)
    path = tmp_path / "crc.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
        z.writestr("_emptyMT/mt.inp_descr", "schema-content")
    data = bytearray(path.read_bytes())
    data[data.index(b"schema-content")] ^= 0xFF  # break stored bytes so the CRC check fails
    path.write_bytes(bytes(data))

    with pytest.raises(ValueError, match="corrupt"):
        MetatypeTemplateService(root, path).initialize("atlas")

    target = root / "atlas" / "1"
    assert not target.exists() or list(target.iterdir()) == []


@pytest.mark.parametrize("member", ["_emptyMT/../evil.txt", "../evil.txt", "/abs.txt", "_emptyMT/sub/x.csv"])
def test_unsafe_archive_members_are_rejected_before_writing(tmp_path, member):
    root = tmp_path / "repo"
    (root / "atlas").mkdir(parents=True)
    path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("_emptyMT/mt.inp_descr", "schema")
        z.writestr(member, "x")
    with pytest.raises(ValueError):
        MetatypeTemplateService(root, path).initialize("atlas")
    assert not (tmp_path / "evil.txt").exists()
    assert not (root / "atlas" / "1").exists() or list((root / "atlas" / "1").iterdir()) == []


def test_archive_without_schema_is_rejected(tmp_path):
    root = tmp_path / "repo"
    (root / "atlas").mkdir(parents=True)
    path = tmp_path / "noschema.zip"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("_emptyMT/go_types.csv", "")
    with pytest.raises(ValueError, match="incomplete"):
        MetatypeTemplateService(root, path).initialize("atlas")


def test_missing_series_directory_is_rejected(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    with pytest.raises(FileNotFoundError):
        MetatypeTemplateService(root, make_archive(tmp_path / "t.zip")).initialize("nope")


def test_series_cannot_be_a_symlink(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (root / "atlas").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(ValueError):
        MetatypeTemplateService(root, make_archive(tmp_path / "t.zip")).initialize("atlas")
    assert list(outside.iterdir()) == []


def test_publish_failure_rolls_back_published_files(tmp_path, monkeypatch):
    import services.metatype.metatype_template_service as module

    root = tmp_path / "repo"
    (root / "atlas").mkdir(parents=True)
    real_link = os.link
    calls = {"n": 0}

    def flaky(src, dst):
        calls["n"] += 1
        if calls["n"] == 3:
            raise OSError("disk failure")
        real_link(src, dst)

    monkeypatch.setattr(module.os, "link", flaky)
    with pytest.raises(OSError):
        MetatypeTemplateService(root, make_archive(tmp_path / "t.zip")).initialize("atlas")
    assert list((root / "atlas" / "1").iterdir()) == []


def test_packaging_spec_bundles_resources_directory():
    spec = (Path(__file__).resolve().parents[1] / "MK_Workbench_Phase1_Test.spec").read_text(encoding="utf-8")
    assert "('resources', 'resources')" in spec
    assert REAL_ARCHIVE.parent.name == "resources"


# -- UI wiring ------------------------------------------------------------------------------------------------------
def _page(root: Path, archive: Path):
    from PySide6.QtWidgets import QApplication

    from core.application_context import ApplicationContext
    from core.config import AppConfig
    from ui.pages.metatype_creation_page import MetatypeCreationPage

    QApplication.instance() or QApplication([])
    page = MetatypeCreationPage(ApplicationContext(AppConfig(metatype_repository_root=str(root))))
    page._template_service = MetatypeTemplateService(root, archive)
    return page


@pytest.fixture
def quiet_boxes(monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    seen: list[tuple[str, str]] = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    for kind in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, kind, lambda parent, title, text, *a, _k=kind, **k: seen.append((_k, title)))
    return seen


def test_scratch_button_click_initializes_selected_series(tmp_path, quiet_boxes):
    root = tmp_path / "repo"
    (root / "atlas").mkdir(parents=True)
    page = _page(root, make_archive(tmp_path / "t.zip"))
    page.refresh()
    page.series_combo.setCurrentIndex(page.series_combo.findData("atlas"))

    assert page.start_scratch_button.isEnabled()
    page.start_scratch_button.click()

    assert (root / "atlas" / "1" / "mt.inp_descr").is_file()
    assert any(title == "Metatype templates copied" for _, title in quiet_boxes)


def test_scratch_button_shows_error_for_corrupt_archive(tmp_path, quiet_boxes):
    root = tmp_path / "repo"
    (root / "atlas").mkdir(parents=True)
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"junk")
    page = _page(root, bad)
    page.refresh()
    page.series_combo.setCurrentIndex(page.series_combo.findData("atlas"))

    page.start_scratch_button.click()

    assert ("critical", "Metatype initialization failed") in quiet_boxes
    assert "corrupt" in page.status_output.toPlainText()
    assert list((root / "atlas").iterdir()) == []
