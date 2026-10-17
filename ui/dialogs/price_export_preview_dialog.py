"""Preview / result dialog for the Pricing MDB export.

Shows the totals of a dry run (nothing written) or of a real export, and the
row-level text-block action of every priced row, so the operator can see exactly
which record is updated or inserted and which text block it references.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.price_text_blocks import ACTION_LABELS, STATUS_CREATED, text_block_cells

_HEADERS = ["Table", "Article", "Variant Condition", "Currency", "List", "Price",
            "Text action", "Text Block ID", "Text Block"]


def list_lines(result: dict) -> list[str]:
    """Computation date, target lists (name, currency, id, validity) and blocked rows."""
    lines = []
    if result.get("computation_date"):
        d = result["computation_date"]
        lines.append(f"Computation date: {d[:4]}-{d[4:6]}-{d[6:8]}")
    for p in result.get("list_plan") or []:
        what = ("reuse existing" if p["action"] == "reuse" else
                "create new" if p["action"] == "create" else "BLOCKED")
        lid = f"id {p['list_id']}" if p.get("list_id") is not None else "id assigned on write"
        lines.append(
            f"{p['currency']} -> {p.get('label') or p['name']} ({what}, {lid}, valid "
            f"{p['date_from'] or '?'} to {p['date_to'] or '?'}"
            + (", region-linked" if p.get("linked") else ", not region-linked") + ")")
    for err in result.get("blocking_errors") or []:
        lines.append("ERROR: " + err)
    for reason, n in (result.get("blocked_reasons") or {}).items():
        lines.append(f"Rows blocked ({n:,}): {reason}")
    if result.get("duplicate_matches"):
        lines.append(f"Records matching duplicate rows: {result['duplicate_matches']:,}")
    return lines


def summary_lines(result: dict) -> list[str]:
    """The totals shown above the table (planned for a dry run, actual after export)."""
    dry = bool(result.get("dry_run"))
    s = result.get("text_summary") or {}
    lines = list_lines(result) + [
        f"Price rows to update: {s.get('price_rows_to_update', 0):,}" if dry else
        f"Price rows updated: {result.get('updated_prices', 0) + result.get('updated_global_prices', 0):,}",
        f"Price rows to insert: {s.get('price_rows_to_insert', 0):,}" if dry else
        f"Price rows inserted: {result.get('inserted_prices', 0) + result.get('inserted_global_prices', 0):,}",
    ]
    if dry:
        lines += [
            f"Text blocks to reuse: {s.get('text_reuse', 0):,}",
            f"Text blocks to create: {s.get('text_create', 0):,}"
            f" (+{s.get('text_link_new', 0):,} further row(s) linking to them)",
            f"Existing text references to preserve: {s.get('text_preserve', 0):,}"
            f" (existing rows without a reference, left unchanged: {s.get('text_unlinked_existing', 0):,})",
            f"Missing or ambiguous text mappings: {s.get('text_missing_or_ambiguous', 0):,}",
            f"Rows skipped or blocked: {result.get('skipped_text_blocked', 0):,} blocked, "
            f"{result.get('skipped_unmapped', 0):,} unmapped, {result.get('skipped_zero_price', 0):,} zero price, "
            f"{result.get('skipped_existing', 0):,} already current",
        ]
        return lines
    t = result.get("text_result") or {}
    linked = t.get("rows_linked")
    lines += [
        f"Text blocks created: {t.get('texts_created', 0):,}",
        f"Text blocks reused: {t.get('texts_reused', 0):,}",
        "Price rows linked to text blocks: " + ("not verified" if linked is None else f"{linked:,}"),
        f"Existing text links preserved: {t.get('links_preserved', 0):,}",
        f"Text operations skipped: {t.get('text_operations_skipped', 0):,}",
        f"Failed text operations: {t.get('text_operations_failed', 0):,}",
        "Read-back verification failures: "
        + (f"{result.get('verification_failure_count', 0):,}" if t.get("readback_verified") else "not run"),
    ]
    return lines


class PriceExportPreviewDialog(QDialog):
    """Read-only totals + row-level table for an export preview or result."""

    def __init__(self, result: dict, parent: QWidget | None = None, allow_export: bool = False) -> None:
        super().__init__(parent)
        dry = bool(result.get("dry_run"))
        self.setWindowTitle("Export preview (nothing written)" if dry else "Export result")
        self.resize(1100, 560)
        layout = QVBoxLayout(self)
        self.summary_label = QLabel("\n".join(summary_lines(result)), self)
        layout.addWidget(self.summary_label)
        if result.get("warnings"):
            warn = QLabel("\n".join(result["warnings"]), self)
            warn.setWordWrap(True)
            layout.addWidget(warn)

        rows = result.get("text_rows") or []
        self.table = QTableWidget(len(rows), len(_HEADERS), self)
        self.table.setHorizontalHeaderLabels(_HEADERS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        for r, entry in enumerate(rows):
            operation = entry.get("operation", "")
            is_global = entry.get("table") == "tCOMd_GlobalPrice"
            cells = [
                "Global price" if is_global else "Article price",
                entry.get("article_code", ""), entry.get("variant_condition", ""),
                entry.get("currency", ""),
                f"{entry.get('list', '')} (id {entry['list_id']})" if entry.get("list_id") is not None
                else entry.get("list", ""), operation,
                ACTION_LABELS.get(entry.get("action"), ""),
            ]
            record = _EntryRecord(entry)
            tid, content, _status = text_block_cells(record, entry)
            cells += [tid if is_global else "—", content]
            for c, text in enumerate(cells):
                self.table.setItem(r, c, QTableWidgetItem(str(text)))
        layout.addWidget(self.table, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.button(QDialogButtonBox.StandardButton.Close).clicked.connect(self.reject)
        self.export_button = None
        if allow_export and dry:
            self.export_button = buttons.addButton(
                "Export to MDB", QDialogButtonBox.ButtonRole.AcceptRole)
            self.export_button.setEnabled(bool(result.get("export_allowed")))
            self.export_button.clicked.connect(self.accept)
        layout.addWidget(buttons)


class _EntryRecord:
    """Adapter so a row-level result renders through ``text_block_cells``."""

    def __init__(self, entry: dict) -> None:
        self.is_global = entry.get("table") == "tCOMd_GlobalPrice"
        self.variant_condition = entry.get("variant_condition", "")
        self.product_code = ""
        self.text_id = ""
