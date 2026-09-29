# MK Product Workbench

A modular PySide6 desktop application for engineering product management: it connects to legacy PDM (SQL Server), builds a read-only repository `Snapshot` from the OCD MDB set, and drives article/permutation/OBX generation workflows on top of that data.

**Full documentation:** see [`docs/README.md`](docs/README.md) — architecture, domain model (PDM, Repository/Snapshot, Engineering, Product, Permutation, Article Encoding, Pricing, OBX), workflows, and reference material all live there.

## Layout

> **2026-09-27 correction:** this section previously described an early-scaffold layout ("dummy data", "future phases") that predates the current codebase. Corrected against the actual `ui/` and `services/` trees (2026-09-27); some detail (e.g. the exact right-hand panel content) has not been re-verified line-by-line and may need a closer follow-up pass — treat this as a corrected overview, not an exhaustive UI spec.

The main window (`ui/main_window.py`) hosts a `QStackedWidget` of workflow pages, driven by a `WorkflowNavigator` (`ui/navigation/workflow_navigator.py`) and a resizable `QSplitter`, with a status bar reporting the active module/snapshot state.

### Workflow steps

Driven by `core/workflow.py` (`WORKFLOW_ITEMS`, "pure metadata — no business logic"):

Product → Articles → Class Creation → Text → Relation Object → Pricing → Pricing Relation → Review → Engineering → Bulk Update

Plus three optionally-enabled, independently disconnectable steps: CET SIF Validation, OBX Validation, Article OBX Generator.

Each step maps to an independent page class under `ui/pages/`.

## Project structure

```
mk_product_workbench/
    main.py                 # Application entry point
    requirements.txt
    assets/                 # Icons / images
    core/
        workflow.py         # Workflow step metadata (no business logic)
        snapshot_manager.py # Holds the active in-memory Snapshot
        ...
    models/                 # Data models (Snapshot, Article, Property, RelationObject, ...)
    services/                # Application services — PDM read, OCD/XOCD export, MDB reverse-engineering,
                             # engineering (relations, dependencies, classes), pricing, snapshot persistence, ...
    resources/
        styles.qss          # Application theme
    ui/
        main_window.py      # Assembles the workflow navigator, page stack, and status bar
        navigation/
            workflow_navigator.py
        explorer/
            pdm_explorer.py
        widgets/            # Reusable widgets, incl. RepositoryWorkspace (shared repository browser/open/extract)
        dialogs/            # Dialogs
        pages/               # One page per workflow step — see core/workflow.py for the current list
```

See [`docs/README.md`](docs/README.md) for the full domain model and architecture documentation, which this section intentionally does not duplicate.

## Setup & run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Design principles

- UI and business logic are separated: pages consume services and models, not database/file access directly.
- Every workflow step is an independent page class.
- Workflow steps are metadata-driven (`core/workflow.py`) rather than hardcoded into the navigator.
