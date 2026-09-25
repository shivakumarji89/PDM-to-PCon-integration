# MK Product Workbench

A modular PySide6 desktop application for engineering product management.

> **Phase 1 - UI foundation only.** No PDM connection, SQL, MDB operations,
> snapshots, business logic, export, or validation. All data shown is
> placeholder data.

## Layout

The main window is divided into four sections:

| Section | Component | Purpose |
| ------- | --------- | ------- |
| Left    | Workflow Navigator | Switch the center workspace between steps |
| Center  | `QStackedWidget` of pages | One independent widget per workflow step |
| Right   | PDM Explorer | Search box, tree view, product information (dummy data) |
| Bottom  | Status bar | Shows `Ready` and `No Product Selected` |

The three panels are hosted in a resizable `QSplitter`.

### Workflow steps

Product -> Articles -> Properties -> Values -> Builder -> Review -> Generate

Each step maps to an independent page class under `ui/pages/`.

## Project structure

```
mk_product_workbench/
    main.py                 # Application entry point
    requirements.txt
    assets/                 # Icons / images
    core/
        workflow.py         # Workflow step metadata (no business logic)
    models/                 # Data models (future phases)
    services/               # Application services (future phases)
    resources/
        styles.qss          # Application theme
    ui/
        main_window.py      # Assembles the four sections
        navigation/
            workflow_navigator.py
        explorer/
            pdm_explorer.py
        widgets/            # Reusable widgets (future phases)
        dialogs/            # Dialogs (future phases)
        pages/
            base_page.py
            product_page.py
            articles_page.py
            builder_page.py
            review_page.py
            generate_page.py
```

## Setup & run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Design principles

- UI and business logic are completely separated.
- Every page is an independent class.
- No hardcoded business logic; placeholder data only.
- Modular, service-oriented structure ready for later phases.
