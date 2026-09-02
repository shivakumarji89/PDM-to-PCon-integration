"""Relation Object workspace page.

A snapshot-driven workbench for authoring the product's OCD relation objects
(``tCOMd_RelObj`` + ``tCOMd_Relation``). Configuration-domain relations are
derived once from the snapshot (code actions + value preconditions); each
relation's OCD_4 logic body is then editable. All data lives on the in-memory
snapshot; no database queries.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.engines.filtering import text_match
from models.relation_object import (
    RELATION_DOMAIN_LABELS,
    RELATION_TYPE_LABELS,
    RelationObject,
)
from services.engineering.engineering_relation_service import validate_relation_body
from ui import theme
from ui.pages.base_page import BasePage

_COL_NAME = 0
_COL_TYPE = 1
_COL_DOMAIN = 2
_COL_BOUND = 3
_COL_ORDER = 4

_FILTER_ALL = "All types"
_GROUP_NONE = "No grouping"
_GROUP_TYPE = "Group by type"
_GROUP_PROPERTY = "Group by property"


class RelationPage(BasePage):
    """Engineering workspace for the active snapshot's relation objects."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Relation Object",
            description="Author configuration relations (preconditions and code actions).",
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._context = context
        self._all_relations: list[RelationObject] = []
        self._row_relations: list[RelationObject] = []
        self._current: RelationObject | None = None
        self._populating = False
        self._entity_names: dict[str, str] = {}
        self._value_texts: dict[str, str] = {}

        # Debounce search typing so the table rebuilds once the user pauses.
        self._filter_timer = QTimer(self)
        self._filter_timer.setSingleShot(True)
        self._filter_timer.setInterval(200)
        self._filter_timer.timeout.connect(self._apply_filter)

        self.add_content(self._build_toolbar())
        self.add_content(self._build_body())
        self.refresh()

    # -- construction ------------------------------------------------------
    def _build_toolbar(self) -> QWidget:
        box = QGroupBox("Toolbar", self)
        layout = QHBoxLayout(box)
        self._search = QLineEdit(box)
        self._search.setPlaceholderText("Search relation name or body...")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._schedule_filter)
        layout.addWidget(self._search, 1)

        layout.addWidget(QLabel("Type:", box))
        self._filter = QComboBox(box)
        self._filter.addItem(_FILTER_ALL)
        for code, label in RELATION_TYPE_LABELS.items():
            self._filter.addItem(label, code)
        self._filter.currentIndexChanged.connect(self._apply_filter)
        layout.addWidget(self._filter)

        layout.addWidget(QLabel("Group:", box))
        self._group = QComboBox(box)
        self._group.addItems([_GROUP_NONE, _GROUP_TYPE, _GROUP_PROPERTY])
        self._group.currentIndexChanged.connect(self._apply_filter)
        layout.addWidget(self._group)

        self._rebuild_btn = QPushButton("Rebuild", box)
        self._rebuild_btn.setToolTip("Re-derive relation objects from the snapshot (discards edits).")
        self._rebuild_btn.clicked.connect(self._on_rebuild)
        layout.addWidget(self._rebuild_btn)

        self._new_btn = QPushButton("New", box)
        self._new_btn.setToolTip("Add a manual relation object.")
        self._new_btn.clicked.connect(self._on_new)
        layout.addWidget(self._new_btn)
        self._delete_btn = QPushButton("Delete", box)
        self._delete_btn.setToolTip("Delete the selected relation object.")
        self._delete_btn.clicked.connect(self._on_delete)
        layout.addWidget(self._delete_btn)

        self._value_table_btn = QPushButton("Value Table", box)
        self._value_table_btn.setToolTip(
            "Preview the OCD value combination table + TABLE() constraint "
            "derived from the loaded articles."
        )
        self._value_table_btn.clicked.connect(self._on_view_value_table)
        layout.addWidget(self._value_table_btn)
        return box

    def _build_body(self) -> QWidget:
        row = QWidget(self)
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, 5, row)
        self._table.setObjectName("relationTable")
        self._table.setHorizontalHeaderLabels(["Relation", "Type", "Domain", "Bound To", "Order"])
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(28)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSortingEnabled(True)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(_COL_NAME, QHeaderView.ResizeMode.Stretch)
        for col in (_COL_TYPE, _COL_DOMAIN, _COL_BOUND, _COL_ORDER):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self._table.itemSelectionChanged.connect(self._on_row_selected)
        layout.addWidget(self._table, 2)

        layout.addWidget(self._build_editor(), 3)
        return row

    def _build_editor(self) -> QWidget:
        box = QGroupBox("Relation", self)
        layout = QVBoxLayout(box)
        form = QFormLayout()
        self._name_edit = QLineEdit(box)
        self._name_edit.editingFinished.connect(self._on_name_edited)
        form.addRow("Name:", self._name_edit)
        self._type_combo = QComboBox(box)
        for code, label in RELATION_TYPE_LABELS.items():
            self._type_combo.addItem(label, code)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow("Type:", self._type_combo)
        self._domain_combo = QComboBox(box)
        for code, label in RELATION_DOMAIN_LABELS.items():
            self._domain_combo.addItem(label, code)
        self._domain_combo.currentIndexChanged.connect(self._on_domain_changed)
        form.addRow("Domain:", self._domain_combo)
        layout.addLayout(form)

        layout.addWidget(QLabel("Body (OCD_4):", box))
        self._body_edit = QPlainTextEdit(box)
        self._body_edit.setObjectName("relationBody")
        self._body_edit.setPlaceholderText("Relation logic body...")
        self._body_edit.textChanged.connect(self._on_body_changed)
        layout.addWidget(self._body_edit, 1)
        self._body_status = QLabel("", box)
        self._body_status.setObjectName("pageSubtitle")
        layout.addWidget(self._body_status)
        return box

    # -- data --------------------------------------------------------------
    def refresh(self) -> None:
        snapshot = self._context.active_snapshot
        self._entity_names = {}
        self._value_texts = {}
        if snapshot is not None:
            for prop in snapshot.properties:
                self._entity_names[str(prop.id)] = prop.name
            for option in snapshot.options:
                self._entity_names[str(option.id)] = option.name
            for value in snapshot.property_values:
                self._value_texts[str(value.id)] = value.value
            for value in snapshot.option_values:
                self._value_texts[str(value.id)] = value.value
        self._all_relations = (
            self._context.engineering_relation_service.ensure_relation_objects(
                snapshot
            )
        )
        # Value combination tables contribute a TABLE() constraint each; ensure
        # they exist so the constraints show in the relation list.
        self._context.engineering_value_table_service.ensure_value_tables(snapshot)
        self._apply_filter()

    def _schedule_filter(self) -> None:
        """Debounce search typing so the table rebuilds once, not per keystroke."""
        self._filter_timer.start()

    def _apply_filter(self) -> None:
        query = self._search.text().strip()
        type_code = self._filter.currentData()
        rows = [
            r
            for r in self._all_relations
            if (type_code is None or r.type_code == type_code)
            and (not query or text_match(query, r.name, r.body))
        ]
        self._populate(self._grouped(rows))

    def _bound_to(self, rel: RelationObject) -> str:
        name = self._entity_names.get(rel.property_id, "")
        value = self._value_texts.get(rel.value_id, "") if rel.value_id else ""
        return f"{name} / {value}" if (name and value) else name

    def _grouped(self, rows: list[RelationObject]) -> list:
        """Return the rows, optionally sectioned by ('__header__', label) rows."""
        mode = self._group.currentText()
        if mode == _GROUP_TYPE:
            rank = {code: i for i, code in enumerate(RELATION_TYPE_LABELS)}

            def label(r):
                return RELATION_TYPE_LABELS.get(r.type_code, r.type_code)

            def sort_key(r):
                # Curated OCD type order, not alphabetical by label.
                return (rank.get(r.type_code, len(rank)), r.name)
        elif mode == _GROUP_PROPERTY:
            def label(r):
                return self._entity_names.get(r.property_id, "") or "(unbound)"

            def sort_key(r):
                return (label(r).lower(), r.name)
        else:
            return list(rows)
        items: list = []
        last = object()
        for rel in sorted(rows, key=sort_key):
            lbl = label(rel)
            if lbl != last:
                items.append(("__header__", lbl))
                last = lbl
            items.append(rel)
        return items

    def _populate(self, items: list) -> None:
        self._populating = True
        grouped = any(isinstance(e, tuple) for e in items)
        self._table.setSortingEnabled(False)
        self._table.clearSpans()
        self._table.setRowCount(0)
        self._row_relations = []
        for entry in items:
            row = self._table.rowCount()
            self._table.insertRow(row)
            if isinstance(entry, tuple):
                header = QTableWidgetItem(str(entry[1]))
                font = header.font()
                font.setBold(True)
                header.setFont(font)
                header.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self._table.setItem(row, 0, header)
                self._table.setSpan(row, 0, 1, 5)
                self._row_relations.append(None)
                continue
            rel = entry
            self._table.setItem(row, _COL_NAME, QTableWidgetItem(rel.name))
            self._table.setItem(
                row, _COL_TYPE,
                QTableWidgetItem(RELATION_TYPE_LABELS.get(rel.type_code, rel.type_code)),
            )
            self._table.setItem(
                row, _COL_DOMAIN,
                QTableWidgetItem(RELATION_DOMAIN_LABELS.get(rel.domain, rel.domain)),
            )
            self._table.setItem(row, _COL_BOUND, QTableWidgetItem(self._bound_to(rel)))
            order_item = QTableWidgetItem()
            order_item.setData(Qt.ItemDataRole.DisplayRole, rel.order)
            self._table.setItem(row, _COL_ORDER, order_item)
            self._row_relations.append(rel)
        self._table.setSortingEnabled(not grouped)
        self._populating = False
        self._show_relation(None)

    # -- selection / editing ----------------------------------------------
    def _on_row_selected(self) -> None:
        if self._populating:
            return
        row = self._table.currentRow()
        rel = self._row_relations[row] if 0 <= row < len(self._row_relations) else None
        self._show_relation(rel)

    def _show_relation(self, rel: RelationObject | None) -> None:
        self._current = None  # suppress the field handlers while loading
        enabled = rel is not None
        self._name_edit.setEnabled(enabled)
        self._type_combo.setEnabled(enabled)
        self._domain_combo.setEnabled(enabled)
        self._body_edit.setEnabled(enabled)
        if rel is None:
            self._name_edit.clear()
            self._body_edit.setPlainText("")
            self._body_status.setText("")
            return
        self._name_edit.setText(rel.name)
        self._type_combo.setCurrentIndex(max(0, self._type_combo.findData(rel.type_code)))
        self._domain_combo.setCurrentIndex(max(0, self._domain_combo.findData(rel.domain)))
        self._body_edit.setPlainText(rel.body)
        self._current = rel
        self._update_body_status(rel.body)

    def _on_name_edited(self) -> None:
        if self._current is None:
            return
        rel = self._current
        if self._context.engineering_relation_service.set_name(
            self._context.active_snapshot, self._current, self._name_edit.text().strip()
        ):
            self._context.snapshot_manager.mark_modified()
            self._apply_filter()
            self._select_relation(rel)

    def _on_type_changed(self) -> None:
        if self._current is None:
            return
        rel = self._current
        if self._context.engineering_relation_service.set_type(
            self._current, self._type_combo.currentData()
        ):
            self._context.snapshot_manager.mark_modified()
            self._apply_filter()
            self._select_relation(rel)

    def _on_domain_changed(self) -> None:
        if self._current is None:
            return
        rel = self._current
        if self._context.engineering_relation_service.set_domain(
            self._current, self._domain_combo.currentData()
        ):
            self._context.snapshot_manager.mark_modified()
            self._apply_filter()
            self._select_relation(rel)

    def _on_body_changed(self) -> None:
        if self._current is None:
            return
        text = self._body_edit.toPlainText()
        if self._context.engineering_relation_service.set_body(self._current, text):
            self._context.snapshot_manager.mark_modified()
        self._update_body_status(text)

    def _update_body_status(self, text: str) -> None:
        ok, message = validate_relation_body(text)
        self._body_status.setText("" if ok else message)
        self._body_status.setStyleSheet(
            "" if ok else f"color: {theme.COLOR_ERROR};"
        )

    def _on_new(self) -> None:
        snapshot = self._context.active_snapshot
        if snapshot is None:
            return
        service = self._context.engineering_relation_service
        existing = {r.name for r in snapshot.relation_objects}
        n = 1
        while f"B_New_{n}" in existing:
            n += 1
        created = service.add_relation(snapshot, f"B_New_{n}")
        if created is None:
            return
        self._context.snapshot_manager.mark_modified()
        self.refresh()
        self._select_relation(created)

    def _on_delete(self) -> None:
        if self._current is None:
            return
        if self._context.engineering_relation_service.remove_relation(
            self._context.active_snapshot, self._current
        ):
            self._context.snapshot_manager.mark_modified()
            self.refresh()

    def _select_relation(self, relation: RelationObject) -> None:
        for row, rel in enumerate(self._row_relations):
            if rel is relation:
                self._table.selectRow(row)
                return

    def _on_rebuild(self) -> None:
        self._context.engineering_relation_service.rebuild_relation_objects(
            self._context.active_snapshot
        )
        # Re-add the value-table TABLE() constraints dropped by the rebuild.
        self._context.engineering_value_table_service.rebuild_value_tables(
            self._context.active_snapshot
        )
        self._context.snapshot_manager.mark_modified()
        self.refresh()

    def _on_view_value_table(self) -> None:
        """Preview the OCD value combination tables + TABLE() constraints derived
        from the loaded articles (read-only, no snapshot change): the property
        config table plus the fabric/finish dependency tables."""
        snapshot = self._context.active_snapshot
        service = self._context.engineering_value_table_service
        blocks: list[str] = []

        table = service.build_property_table(snapshot)
        if table is not None:
            rows = service.to_csv_rows(table)
            blocks.append(
                "===== Config table (properties) =====\r\n"
                f"{service.constraint_body(table)}\r\n\r\n"
                f"-- {table.name}_tbl.csv ({len(table.lines)} lines) --\r\n"
                + "\r\n".join(rows)
            )

        for dep in service.build_dependency_tables(snapshot):
            rows = service.to_csv_rows(dep)
            blocks.append(
                f"===== Finish/fabric table: {dep.name} =====\r\n"
                f"{service.constraint_body(dep)}\r\n\r\n"
                f"-- {dep.name}_tbl.csv ({len(dep.lines)} lines) --\r\n"
                + "\r\n".join(rows)
            )

        text = "\r\n\r\n".join(blocks) if blocks else (
            "No value combination tables (load a family first)."
        )
        dialog = QDialog(self)
        dialog.setWindowTitle("Value Combination Tables (preview)")
        dialog.resize(600, 680)
        layout = QVBoxLayout(dialog)
        view = QPlainTextEdit(dialog)
        view.setReadOnly(True)
        view.setPlainText(text)
        layout.addWidget(view, 1)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, dialog)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()
