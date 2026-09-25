"""PDM Change Monitor dialog.

Queries PDM for new OptionValues, Products and Items since the last run,
then shows a summary. Watermarks are persisted to cache/pdm_watermark.json
so each run only reports what is genuinely new.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ui import theme
from ui.components import DialogTemplate
from ui.components._styles import label_color_qss, secondary_button_qss

if TYPE_CHECKING:
    from core.application_context import ApplicationContext

def _watermark_path(preset: str) -> Path:
    slug = preset.lower().replace(" ", "_")
    return Path(f"cache/pdm_watermark_{slug}.json")


def _load_watermarks(preset: str) -> dict[str, int]:
    path = _watermark_path(preset)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"OptionValueId": 0, "ProductId": 0, "ItemId": 0, "PriceFormulaId": 0}


def _save_watermarks(preset: str, watermarks: dict[str, int]) -> None:
    path = _watermark_path(preset)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = dict(watermarks)
    data["last_run"] = str(date.today())
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


_STATUS_LABEL = {1: "Active", 2: "Discontinued", 0: "Inactive", -1: "Legacy", 3: "Superseded"}


class _Worker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, context: "ApplicationContext", old_marks: dict[str, int]) -> None:
        super().__init__()
        self._context = context
        self._old = old_marks

    def run(self) -> None:
        try:
            repo = self._context.pdm_service.repository
            new_marks = repo.fetch_watermarks()
            is_first_run = all(
                self._old.get(k, 0) == 0
                for k in ("OptionValueId", "ProductId", "ItemId")
            )
            result: dict[str, Any] = {
                "new_options":    [],
                "new_products":   [],
                "new_items":      [],
                "new_prices":     [],
                "status_changes": [],
                "watermarks":     new_marks,
                "is_first_run":   is_first_run,
            }
            if not is_first_run:
                if new_marks.get("OptionValueId", 0) > self._old.get("OptionValueId", 0):
                    result["new_options"] = repo.fetch_new_option_values(
                        self._old["OptionValueId"]
                    )
                if new_marks.get("ProductId", 0) > self._old.get("ProductId", 0):
                    result["new_products"] = repo.fetch_new_products(
                        self._old["ProductId"]
                    )
                if new_marks.get("ItemId", 0) > self._old.get("ItemId", 0):
                    result["new_items"] = repo.fetch_new_items(
                        self._old["ItemId"]
                    )
                if new_marks.get("PriceFormulaId", 0) > self._old.get("PriceFormulaId", 0):
                    result["new_prices"] = repo.fetch_new_price_formulas(
                        self._old["PriceFormulaId"]
                    )
                last_run = self._old.get("last_run")
                if last_run:
                    result["status_changes"] = repo.fetch_changed_option_value_statuses(
                        last_run
                    )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class PdmChangesDialog(DialogTemplate):
    """Shows PDM changes (new options/products/items) since the last check."""

    def __init__(self, context: "ApplicationContext", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._context = context
        self._preset = context.config.active_pdm_preset() or "PDM"
        self.set_title(f"PDM Change Monitor — {self._preset}")
        self.setMinimumWidth(560)
        self.setMinimumHeight(420)

        self._status = QLabel("Connecting to PDM…", self)
        self._status.setFont(theme.font("subtitle"))
        self._status.setStyleSheet(label_color_qss(theme.MUTED))
        self.add_content(self._status)

        # Scrollable results area.
        self._results_widget = QWidget()
        self._results_layout = QVBoxLayout(self._results_widget)
        self._results_layout.setContentsMargins(0, 0, 0, 0)
        self._results_layout.setSpacing(theme.SPACE_2)
        self._results_layout.addStretch(1)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        scroll.setWidget(self._results_widget)
        self.add_content(scroll)

        self._lines: list[str] = []

        self._copy_btn = QPushButton("Copy to Clipboard", self)
        self._copy_btn.setObjectName("pdmChangesCopy")
        self._copy_btn.setStyleSheet(secondary_button_qss("pdmChangesCopy"))
        self._copy_btn.clicked.connect(self._on_copy)
        self._copy_btn.setEnabled(False)
        self.add_footer_button(self._copy_btn)

        close_btn = QPushButton("Close", self)
        close_btn.setObjectName("pdmChangesClose")
        close_btn.setStyleSheet(secondary_button_qss("pdmChangesClose"))
        close_btn.clicked.connect(self.accept)
        self.add_footer_button(close_btn)

        self._old_marks = _load_watermarks(self._preset)
        self._worker = _Worker(context, self._old_marks)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    # -- slots -------------------------------------------------------------

    def _on_finished(self, result: dict[str, Any]) -> None:
        new_marks = result["watermarks"]
        last_run  = self._old_marks.get("last_run", "never")

        if result.get("is_first_run"):
            self._status.setText(
                f"Baseline saved for {self._preset}. "
                "Run again tomorrow to see what changed."
            )
        else:
            stat_grouped    = self._group_by_ov(result["status_changes"])
            new_opt_grouped = self._group_by_ov(result["new_options"])
            new_prods       = result["new_products"]
            new_items       = result["new_items"]
            new_prices      = result["new_prices"]

            total = (len(stat_grouped) + len(new_opt_grouped)
                     + len(new_prods) + len(new_items) + len(new_prices))
            if total == 0:
                self._status.setText(
                    f"No changes detected since last run ({last_run})."
                )
            else:
                self._status.setText(
                    f"Found {total} change(s) since last run ({last_run})."
                )
                self._add_section(
                    f"Status Changes — Fabrics / Finishes ({len(stat_grouped)})",
                    [
                        f"{_STATUS_LABEL.get(rows[0].NewStatus, str(rows[0].NewStatus))}  "
                        f"{rows[0].OptionName} / \"{rows[0].ValueName}\"  →  "
                        f"{self._product_summary(rows)}  [{str(rows[0].NewStatusDate)[:10]}]"
                        for rows in stat_grouped.values()
                    ],
                )
                self._add_section(
                    f"New Option Values / Fabrics / Finishes ({len(new_opt_grouped)})",
                    [
                        f"{rows[0].OptionName} / \"{rows[0].ValueName}\"  →  "
                        f"{self._product_summary(rows)}"
                        for rows in new_opt_grouped.values()
                    ],
                )
                self._add_section(
                    f"New Products ({len(new_prods)})",
                    [f"{r.ProductCode}  {r.ProductName}  [{r.SeriesName}]"
                     for r in new_prods],
                )
                self._add_section(
                    f"New SKUs / Articles ({len(new_items)})",
                    [f"{r.ArticleCode}  →  {r.ProductCode}  {r.ProductName}  [{r.SeriesName}]"
                     for r in new_items],
                )
                self._add_section(
                    f"New Price Formulas ({len(new_prices)})",
                    [f"Site {r.SiteCode}  ({r.DomCurrCode})  Effective {str(r.EffectiveDate)[:10]}"
                     for r in new_prices],
                )

        _save_watermarks(self._preset, new_marks)
        self._copy_btn.setEnabled(bool(self._lines))

    def _on_error(self, message: str) -> None:
        self._status.setText(f"Error: {message}")
        self._status.setStyleSheet(label_color_qss(theme.COLOR_ERROR))

    def _on_copy(self) -> None:
        QApplication.clipboard().setText("\n".join(self._lines))

    def closeEvent(self, event) -> None:
        if self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(2000)
        super().closeEvent(event)

    @staticmethod
    def _group_by_ov(rows: list[Any]) -> dict[int, list[Any]]:
        grouped: dict[int, list[Any]] = defaultdict(list)
        for r in rows:
            grouped[r.OptionValueId].append(r)
        return grouped

    @staticmethod
    def _product_summary(rows: list[Any]) -> str:
        prods = [f"{r.ProductCode} {r.ProductName}" for r in rows]
        if len(prods) <= 3:
            return ", ".join(prods)
        return ", ".join(prods[:3]) + f"  +{len(prods) - 3} more"

    def _add_section(self, title: str, lines: list[str]) -> None:
        if not lines:
            return
        self._lines.append(title)
        # Insert before the trailing stretch.
        insert_pos = self._results_layout.count() - 1

        heading = QLabel(title, self._results_widget)
        heading.setFont(theme.font("label"))
        heading.setStyleSheet(label_color_qss(theme.INK))
        self._results_layout.insertWidget(insert_pos, heading)
        insert_pos += 1

        for line in lines:
            self._lines.append(f"  • {line}")
            lbl = QLabel(f"  • {line}", self._results_widget)
            lbl.setFont(theme.font("body"))
            lbl.setStyleSheet(label_color_qss(theme.MUTED))
            lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            lbl.setWordWrap(True)
            self._results_layout.insertWidget(insert_pos, lbl)
            insert_pos += 1
