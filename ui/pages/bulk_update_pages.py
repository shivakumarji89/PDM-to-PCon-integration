"""Dedicated Bulk Update workflow pages.

These pages are intentionally isolated from Maintenance and Development UI.
They reuse the existing bulk-update services while keeping the work tables
resident in the workflow workspace.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDateEdit, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView, QAbstractItemView,
)

from ui.pages.base_page import BasePage
from ui.workers.background_task import ReportedTask

_UK_SITE_ID = 1
_DEFAULT_REPOS = [
    r"C:\HermanMillerOFMLSVN\Staging\HermanMiller\WS\Seating\Seating",
    r"C:\HermanMillerOFMLSVN\Staging\HermanMiller\WS\Tables\Tables",
]


def _repo_field(parent, value=""):
    row = QHBoxLayout()
    edit = QLineEdit(parent)
    edit.setText(value)
    edit.setPlaceholderText("Repository root(s), separated by ';'")
    browse = QPushButton("Browse...", parent)
    def choose():
        path = QFileDialog.getExistingDirectory(parent, "Select repository root")
        if path:
            parts = [p.strip() for p in edit.text().split(";") if p.strip()]
            if path not in parts:
                parts.append(path)
            edit.setText(";".join(parts))
    browse.clicked.connect(choose)
    row.addWidget(edit, 1)
    row.addWidget(browse)
    return row, edit


def _table(parent, headers):
    table = QTableWidget(0, len(headers), parent)
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
    if len(headers) > 1:
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
    return table


def _item(value):
    item = QTableWidgetItem(str(value if value is not None else ""))
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    return item


class _BulkPage(BasePage):
    def __init__(self, title, description, context, parent=None):
        super().__init__(title, description, parent, show_placeholder=False)
        self._context = context
        self._task = None
        self._monitor = None

    def _start(self, work, finished, title):
        if self._task is not None and self._task.active:
            return
        from ui.dialogs.progress_dialog import ProgressDialog
        self._task = ReportedTask(self)
        reporter = self._task.reporter
        if self._monitor is None:
            self._monitor = ProgressDialog(self)
        self._monitor.bind(reporter)
        self._monitor.show()
        self._monitor.raise_()
        self._task.start(lambda _emit: work(reporter), finished=finished,
                         failed=lambda msg: QMessageBox.warning(self, title, msg),
                         cancelled=lambda msg: QMessageBox.information(self, title, msg))

    def _busy(self):
        return self._task is not None and self._task.active


class BulkPriceUpdatePage(_BulkPage):
    def __init__(self, context, parent=None):
        super().__init__("Price Update", "Roll published price lists forward and review each package before applying.", context, parent)
        root = QVBoxLayout()
        form = QFormLayout()
        defaults = ";".join(p for p in _DEFAULT_REPOS if Path(p).is_dir())
        repo_row, self._repo = _repo_field(self, defaults)
        form.addRow("Repository", repo_row)
        self._target = QComboBox(self)
        self._target.addItems(["XOCD packages (folders)", "OCD MDBs (files)"])
        form.addRow("Repository holds", self._target)
        self._effective = QDateEdit(self)
        self._effective.setCalendarPopup(True)
        self._effective.setDisplayFormat("dd-MMM-yyyy")
        self._effective.setDate(QDate.currentDate())
        form.addRow("Effective date", self._effective)
        self._token = QLineEdit(self)
        self._token.setPlaceholderText("e.g. 2026 or 2026_2")
        form.addRow("New list token", self._token)
        self._fresh = QCheckBox("Pull fresh prices from PDM (off = dates only)", self)
        self._fresh.setChecked(True)
        form.addRow("", self._fresh)
        root.addLayout(form)
        actions = QHBoxLayout()
        scan = QPushButton("Scan", self); scan.clicked.connect(self._scan)
        apply = QPushButton("Apply Selected", self); apply.clicked.connect(self._apply)
        actions.addWidget(scan); actions.addWidget(apply); actions.addStretch(1)
        root.addLayout(actions)
        self._status = QLabel("Enter repository, effective date and list token, then scan.", self)
        root.addWidget(self._status)
        self._table = _table(self, ["Apply", "Series", "Package", "Current open lists", "Preview / Result"])
        root.addWidget(self._table, 1)
        self.add_content(QWidget(self)); self._content.itemAt(self._content.count()-1).widget().setLayout(root)
        self._packages = []
        self._last_scan = None

    def _selected_paths(self):
        return [self._packages[r] for r in range(self._table.rowCount())
                if self._table.item(r, 0).checkState() == Qt.CheckState.Checked]

    def _scan(self):
        if self._busy(): return
        repo = self._repo.text().strip()
        if not repo:
            QMessageBox.information(self, "Price Update", "Choose a repository root."); return
        svc = self._context.price_update_service
        is_mdb = self._target.currentIndex() == 1
        effective = self._effective.date().toString("yyyyMMdd")
        token = self._token.text().strip()
        if not token:
            QMessageBox.information(self, "Price Update", "Enter the new list token."); return
        def work(reporter):
            packages = svc._discover_packages(repo, is_mdb)
            reporter.begin(max(len(packages), 1), title="Scan Price Lists", subject=Path(repo.split(";")[0]).name)
            result = svc.run_batch(repo, is_mdb, effective, token, None, apply=False,
                                   packages=packages, progress=lambda d,t,n: reporter.advance(n))
            return packages, result
        self._start(work, self._scanned, "Price Update")

    def _scanned(self, payload):
        self._packages, result = payload
        self._last_scan = result
        self._table.setRowCount(len(self._packages))
        by_path = {str(Path(p.package)): p for p in result.packages}
        for row, path in enumerate(self._packages):
            pkg = by_path.get(str(path))
            check = QTableWidgetItem()
            check.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            check.setCheckState(Qt.CheckState.Unchecked)
            self._table.setItem(row, 0, check)
            name = path.parent.name if self._target.currentIndex() == 1 else path.name
            self._table.setItem(row, 1, _item(name))
            self._table.setItem(row, 2, _item(path))
            lists = ", ".join(f"{x.currency}: {x.old_list}" for x in getattr(pkg, "lists", [])) if pkg else ""
            preview = getattr(pkg, "error", "") or ("; ".join(f"{x.currency}: {x.old_list} → {x.new_list}" for x in getattr(pkg, "lists", [])) if pkg else "No result")
            self._table.setItem(row, 3, _item(lists or "No open price list"))
            self._table.setItem(row, 4, _item(preview))
        self._status.setText(f"Scanned {len(self._packages)} packages. Select rows to apply.")

    def _apply(self):
        if self._busy(): return
        selected = self._selected_paths()
        if not selected:
            QMessageBox.information(self, "Price Update", "Select at least one package."); return
        if not self._token.text().strip():
            QMessageBox.information(self, "Price Update", "Enter the new list token."); return
        answer = QMessageBox.question(self, "Confirm Price Update",
            f"Apply price-list roll-over to {len(selected)} selected package(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes: return
        svc = self._context.price_update_service
        is_mdb = self._target.currentIndex() == 1
        effective = self._effective.date().toString("yyyyMMdd")
        token = self._token.text().strip()
        lookup = svc.make_pdm_lookup(self._effective.date().toString("dd-MMM-yyyy"), _UK_SITE_ID,
                                     special_map=svc.load_special_map()) if self._fresh.isChecked() else None
        def work(reporter):
            reporter.begin(max(len(selected), 1), title="Apply Price Update", subject="")
            try:
                return svc.run_batch(self._repo.text().strip(), is_mdb, effective, token, lookup,
                    apply=True, packages=selected, progress=lambda d,t,n: reporter.advance(n),
                    special_map=svc.load_special_map() if lookup else None)
            finally:
                if lookup is not None and hasattr(lookup, "close"): lookup.close()
        self._start(work, self._applied, "Price Update")

    def _applied(self, result):
        if result.error:
            QMessageBox.warning(self, "Price Update", result.error)
        self._status.setText(f"Applied to {sum(1 for p in result.packages if p.error is None)} of {len(result.packages)} packages. Commit repository changes to publish.")
        self._scan()


class BulkVersionUpdatePage(_BulkPage):
    def __init__(self, context, parent=None):
        super().__init__("Version Update", "Review OCD and ODB export versions and update selected series.", context, parent)
        root = QVBoxLayout()
        form = QFormLayout()
        defaults = ";".join(p for p in _DEFAULT_REPOS if Path(p).is_dir())
        repo_row, self._repo = _repo_field(self, defaults)
        form.addRow("Repository", repo_row)
        self._version = QLineEdit(self); self._version.setPlaceholderText("Major.Minor.Build, e.g. 1.34.0")
        form.addRow("New version", self._version)
        root.addLayout(form)
        actions = QHBoxLayout()
        scan = QPushButton("Scan", self); scan.clicked.connect(self._scan)
        all_btn = QPushButton("Select All", self); all_btn.clicked.connect(lambda: self._set_all(True))
        clear = QPushButton("Clear", self); clear.clicked.connect(lambda: self._set_all(False))
        apply = QPushButton("Apply Selected", self); apply.clicked.connect(self._apply)
        for b in (scan, all_btn, clear, apply): actions.addWidget(b)
        actions.addStretch(1); root.addLayout(actions)
        self._status = QLabel("Scan repository to inspect versions.", self); root.addWidget(self._status)
        self._table = _table(self, ["Apply", "Series", "OCD version", "ODB version", "Files", "Folder"])
        root.addWidget(self._table, 1)
        body = QWidget(self); body.setLayout(root); self.add_content(body)
        self._series = []

    def _scan(self):
        if self._busy(): return
        repo = self._repo.text().strip()
        if not repo:
            QMessageBox.information(self, "Update Version", "Choose a repository root."); return
        svc = self._context.version_update_service
        def work(reporter):
            folders = svc.series_folders(repo)
            reporter.begin(max(len(folders), 1), title="Scan Versions", subject=Path(repo.split(";")[0]).name)
            return svc.read_series(folders, progress=lambda d,t,n: reporter.advance(n))
        self._start(work, self._scanned, "Update Version")

    def _scanned(self, series):
        self._series = list(series)
        self._table.setRowCount(len(series))
        for r, sv in enumerate(series):
            check = QTableWidgetItem(); check.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable); check.setCheckState(Qt.CheckState.Unchecked)
            self._table.setItem(r, 0, check)
            files = "OCD + ODB" if sv.ocd_path and sv.odb_path else ("OCD only" if sv.ocd_path else ("ODB only" if sv.odb_path else "Missing"))
            values = [sv.program, sv.ocd_version or "-", sv.odb_version or "-", files, sv.folder]
            for c, value in enumerate(values, 1): self._table.setItem(r, c, _item(value))
        self._status.setText(f"{len(series)} series found.")

    def _set_all(self, checked):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for r in range(self._table.rowCount()): self._table.item(r, 0).setCheckState(state)

    def _apply(self):
        if self._busy(): return
        version = self._context.version_update_service.parse_version(self._version.text())
        if version is None:
            QMessageBox.information(self, "Update Version", "Enter version as Major.Minor.Build."); return
        selected = [self._series[r] for r in range(self._table.rowCount())
                    if self._table.item(r, 0).checkState() == Qt.CheckState.Checked]
        if not selected:
            QMessageBox.information(self, "Update Version", "Select at least one series."); return
        answer = QMessageBox.question(self, "Confirm Version Update",
            f"Write {'.'.join(map(str, version))} and today's release date to {len(selected)} selected series?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes: return
        svc = self._context.version_update_service
        def work(reporter):
            reporter.begin(max(len(selected), 1), title="Update Versions", subject="")
            return svc.update(selected, *version, progress=lambda d,t,n: reporter.advance(n))
        self._start(work, self._applied, "Update Version")

    def _applied(self, results):
        ok = sum(1 for r in results if r.error is None)
        failed = [r for r in results if r.error]
        self._status.setText(f"Updated {ok} of {len(results)} series." + (f" {len(failed)} failed." if failed else ""))
        self._scan()


class BulkRepositoryLinkPage(_BulkPage):
    def __init__(self, context, parent=None):
        super().__init__("Repository Link", "Discover published series, inspect existing PDM links and establish or repair a selected link.", context, parent)
        root = QVBoxLayout()
        form = QFormLayout()
        defaults = ";".join(p for p in _DEFAULT_REPOS if Path(p).is_dir())
        repo_row, self._repo = _repo_field(self, defaults)
        form.addRow("Repository roots", repo_row)
        root.addLayout(form)
        actions = QHBoxLayout()
        scan = QPushButton("Discover Series", self); scan.clicked.connect(self._scan)
        link = QPushButton("Link Selected to Loaded PDM Product", self); link.clicked.connect(self._link_selected)
        actions.addWidget(scan); actions.addWidget(link); actions.addStretch(1); root.addLayout(actions)
        self._product = QLabel("Loaded PDM product: checking…", self); root.addWidget(self._product)
        self._status = QLabel("Discover repository series to begin.", self); root.addWidget(self._status)
        self._table = _table(self, ["Select", "Series", "Program Code", "Version", "PDM Link", "Linked Product", "Alignment"])
        root.addWidget(self._table, 1)
        body = QWidget(self); body.setLayout(root); self.add_content(body)
        self._repositories = []
        self._refresh_product()

    def _refresh_product(self):
        snap = self._context.pdm_snapshot
        product = snap.product if snap is not None else None
        self._loaded_product = product
        self._product.setText(
            f"Loaded PDM product: {product.code or '-'} — {product.name or '-'}" if product
            else "No PDM product loaded. Load the intended PDM product before establishing links.")

    def _scan(self):
        if self._busy(): return
        repo = self._repo.text().strip()
        if not repo:
            QMessageBox.information(self, "Repository Link", "Choose repository roots."); return
        price_svc = self._context.price_update_service
        link_svc = self._context.maintenance_repository_link_service
        def work(reporter):
            files = price_svc._discover_packages(repo, True)
            reporter.begin(max(len(files), 1), title="Discover Published Series", subject=Path(repo.split(";")[0]).name)
            rows = []
            for i, file in enumerate(files, 1):
                folder = file.parent
                try:
                    info = link_svc.inspect_repository(folder)
                    connection = link_svc.get(info["path"])
                    pdm = (connection or {}).get("pdm", {})
                    status = (connection or {}).get("connection", {}).get("status", "Not linked")
                    rows.append((info, status, pdm.get("product_code", ""), "Stored link" if connection else "Not evaluated"))
                except Exception as exc:
                    rows.append(({"path": str(folder), "name": folder.name, "code": "-", "version": ""}, "Inspection error", "", str(exc)))
                reporter.advance(folder.name)
            return rows
        self._start(work, self._scanned, "Repository Link")

    def _scanned(self, rows):
        self._repositories = rows
        self._table.setRowCount(len(rows))
        for r, (info, status, pdm_code, alignment) in enumerate(rows):
            check = QTableWidgetItem(); check.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable); check.setCheckState(Qt.CheckState.Unchecked)
            self._table.setItem(r, 0, check)
            for c, value in enumerate((info.get("name"), info.get("code"), info.get("version") or "-", status, pdm_code or "-", alignment), 1):
                self._table.setItem(r, c, _item(value))
        self._status.setText(f"Discovered {len(rows)} published series. Select rows to establish or repair links.")

    def _link_selected(self):
        if self._busy(): return
        self._refresh_product()
        if self._loaded_product is None:
            QMessageBox.information(self, "Repository Link", "Load the PDM product you want to link first."); return
        selected = [self._repositories[r] for r in range(self._table.rowCount())
                    if self._table.item(r, 0).checkState() == Qt.CheckState.Checked]
        if not selected:
            QMessageBox.information(self, "Repository Link", "Select at least one published series."); return
        answer = QMessageBox.question(self, "Confirm Repository Links",
            f"Link {len(selected)} selected series to {self._loaded_product.code} — {self._loaded_product.name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes: return
        service = self._context.maintenance_repository_link_service
        product = self._loaded_product
        def work(reporter):
            reporter.begin(max(len(selected), 1), title="Establish Repository Links", subject="")
            outcomes = []
            for i, (info, *_rest) in enumerate(selected, 1):
                try:
                    service.establish(repository=info, pdm_candidate=product)
                    outcomes.append((info["name"], "Linked", ""))
                except Exception as exc:
                    outcomes.append((info["name"], "Failed", str(exc)))
                reporter.advance(info["name"])
            return outcomes
        self._start(work, self._linked, "Repository Link")

    def _linked(self, outcomes):
        ok = sum(1 for _, status, _ in outcomes if status == "Linked")
        errors = [f"{name}: {error}" for name, status, error in outcomes if status != "Linked"]
        self._status.setText(f"Established {ok} of {len(outcomes)} links." + (f" {len(errors)} failed." if errors else ""))
        if errors: QMessageBox.warning(self, "Repository Link", "\n".join(errors[:10]))
        self._scan()
