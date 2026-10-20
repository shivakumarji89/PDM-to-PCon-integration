"""Tests for bundled HM/KNOLL MDB template discovery."""
from pathlib import Path

from services import ocd_export_service as export_module


def test_resolves_hm_seating_from_preserved_template_tree(tmp_path, monkeypatch):
    root = tmp_path / "resources" / "templates"
    expected = root / "1_WS_Templates" / "Seating_Template" / "pcr_data_com_ocd.mdb"
    expected.parent.mkdir(parents=True)
    expected.write_bytes(b"test")
    monkeypatch.setattr(export_module, "_TEMPLATE_ROOT", root)

    assert export_module._template_for_kind("hm_seating") == expected
    assert export_module._template_for_kind("seating") == expected


def test_resolves_hm_tables_from_direct_template_folder(tmp_path, monkeypatch):
    root = tmp_path / "resources" / "templates"
    expected = root / "Tables_Template" / "pcr_data_com_ocd.mdb"
    expected.parent.mkdir(parents=True)
    expected.write_bytes(b"test")
    monkeypatch.setattr(export_module, "_TEMPLATE_ROOT", root)

    assert export_module._template_for_kind("hm_tables") == expected
    assert export_module._template_for_kind("tables") == expected


def test_resolves_knoll_template_with_extra_wrapper_folder(tmp_path, monkeypatch):
    root = tmp_path / "resources" / "templates"
    expected = root / "1_WS_Templates" / "_TEMPLATE_KNOLL" / "pcr_data_com_ocd.mdb"
    expected.parent.mkdir(parents=True)
    expected.write_bytes(b"test")
    monkeypatch.setattr(export_module, "_TEMPLATE_ROOT", root)

    assert export_module._template_for_kind("knoll") == expected
    assert export_module._template_for_kind("_TEMPLATE_KNOLL") == expected


def test_missing_template_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(export_module, "_TEMPLATE_ROOT", tmp_path / "templates")

    assert export_module._template_for_kind("knoll") is None
    assert export_module._template_for_kind("unknown") is None
