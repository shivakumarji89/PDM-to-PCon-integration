"""Headless validation for project save/open (``.mkproj``).

Builds a snapshot, saves it to a temp ``.mkproj`` via ``ProjectService``, then
loads it back and checks the full session round-trips (product, articles, the
per-article link, BOM, VARCOND terms, prefix lengths, option increments and the
workflow step). No Qt, no database.

Run:  $env:PYTHONPATH="."; python scripts/validate_project.py
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from core.enums import WorkflowStep
from core.snapshot_manager import SnapshotManager
from models.article import Article
from models.product import Product
from models.snapshot import Snapshot
from services.project_service import ProjectService


class _Ctx:
    """Minimal stand-in for ApplicationContext (snapshot manager only)."""

    def __init__(self) -> None:
        self.snapshot_manager = SnapshotManager()

    @property
    def active_snapshot(self):
        return self.snapshot_manager.get_active_snapshot()


def _snapshot() -> Snapshot:
    snap = Snapshot(product=Product(id="p1", code="DWE36", name="Bolster"))
    snap.articles = [Article(id="sup1", code="DWE362S4C.0812")]
    snap.article_property_value_ids = {"sup1": ["v1", "v2"]}
    snap.article_components = {
        "sup1": [{"sub_item": "DWE3UH4.", "quantity": 1, "sequence": "1"}],
    }
    snap.article_varcond_terms = {
        "sup1": [{"name": "LegStyle", "order": 1,
                  "has_dependent_options": 0, "order_code": "C"}],
    }
    snap.article_prefix_length = {"sup1": 5}
    snap.option_increments = {
        "DWE3UH4.": [{"item": "DWE3UH4.", "option_id": 9502,
                      "option_name": "Finish", "value_name": "Oak",
                      "code": "OK", "increment": 25.0}],
    }
    return snap


def main() -> int:
    ctx = _Ctx()
    ctx.snapshot_manager.load_snapshot(_snapshot())
    svc = ProjectService(ctx)

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bolster"

        # 1) Save (extension auto-added) and remember path/name.
        saved = svc.save_project(path, name="Bolster", current_step="options")
        assert saved.suffix == ".mkproj", saved
        assert svc.path == saved and svc.name == "Bolster"
        assert saved.exists()
        print("OK: project saved as .mkproj")

        # 2) New project clears the snapshot and path.
        svc.new_project()
        assert ctx.snapshot_manager.get_active_snapshot() is None
        assert svc.path is None
        print("OK: new project clears the session")

        # 3) Load restores everything, incl. the workflow step and product.
        project = svc.load_project(saved)
        assert project.name == "Bolster"
        assert project.current_step == WorkflowStep.OPTIONS
        snap = ctx.snapshot_manager.get_active_snapshot()
        assert snap is not None
        assert snap.product is not None and snap.product.code == "DWE36"
        assert snap.article_components["sup1"][0]["sub_item"] == "DWE3UH4."
        assert snap.article_varcond_terms["sup1"][0]["name"] == "LegStyle"
        assert snap.article_prefix_length == {"sup1": 5}
        assert snap.option_increments["DWE3UH4."][0]["increment"] == 25.0
        print("OK: load restores snapshot + product + workflow step")

    # 4) Loading a non-mkproj file is rejected.
    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "bad.mkproj"
        bad.write_text('{"format": "nope"}', encoding="utf-8")
        try:
            svc.load_project(bad)
            raise AssertionError("expected ValueError for bad format")
        except ValueError:
            pass
    print("OK: unrecognised file rejected")

    print("ALL PROJECT CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
