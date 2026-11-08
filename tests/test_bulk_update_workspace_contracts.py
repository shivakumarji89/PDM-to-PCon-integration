"""Contract checks for the series-oriented Bulk Update workspaces."""
from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def _classes(source: str) -> dict[str, ast.ClassDef]:
    tree = ast.parse(source)
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef)
    }


def _methods(node: ast.ClassDef) -> set[str]:
    return {
        child.name
        for child in node.body
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def test_bulk_update_pages_are_syntactically_valid_and_have_series_workspaces():
    source = _source("ui/pages/bulk_update_pages.py")
    classes = _classes(source)

    assert "QTabWidget" in source
    assert "BulkPriceUpdatePage" in classes
    assert "BulkVersionUpdatePage" in classes
    assert "BulkRepositoryLinkPage" in classes

    price = _methods(classes["BulkPriceUpdatePage"])
    version = _methods(classes["BulkVersionUpdatePage"])
    repository_link = _methods(classes["BulkRepositoryLinkPage"])

    assert {"_prepared_results", "_export_active", "_export_all", "_exported"} <= price
    assert {"_scanned", "_apply", "_applied"} <= version
    assert {"_scanned", "_link_selected", "_linked"} <= repository_link


def test_price_calculation_is_separate_from_mdb_export():
    source = _source("services/bulk_pdm_price_update_service.py")
    assert "export: bool = True" in source
    assert 'if not export:' in source
    assert 'result.status = "Ready"' in source
    assert "def export_prepared(" in source
    assert "expected_plan=item.plan_digest" in source


def test_version_results_keep_exact_series_folder_identity():
    source = _source("services/version_update_service.py")
    classes = _classes(source)
    result = classes["VersionUpdateResult"]
    fields = {
        item.target.id
        for item in result.body
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
    }
    assert "folder" in fields
    assert "folder=str(sv.folder)" in source


def test_repository_link_remains_one_series_at_a_time():
    source = _source("ui/pages/bulk_update_pages.py")
    assert "if len(selected) != 1:" in source
    assert "Link one series at a time." in source
    assert "self._tabs = QTabWidget(self)" in source
