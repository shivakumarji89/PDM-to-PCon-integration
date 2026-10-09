"""Pricing-relation workspace page.

Generates and displays the OCD ``PA_PRICING`` relation body for the active
snapshot - the single "merging" relation that ties the configuration selections
to the price variant conditions computed on the Pricing page. Non-super products
get the property-concatenation body; super products delegate to the VARCOND
generator. No database access.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from services.pricing_relation_service import PricingRelationService
from ui.pages.base_page import BasePage
from ui.widgets.maintenance_source_tabs import (
    MDB_NOT_LOADED_TEXT,
    MaintenanceSourceMixin,
    read_only_in_mdb,
)


def _v(parent: QWidget) -> QVBoxLayout:
    """A zero-margin vertical layout."""
    layout = QVBoxLayout(parent)
    layout.setContentsMargins(0, 0, 0, 0)
    return layout


@read_only_in_mdb("_on_generate", "_render_components")
class PricingRelationPage(MaintenanceSourceMixin, BasePage):
    """Generate the PA_PRICING relation for the active snapshot."""

    def __init__(self, context, parent: QWidget | None = None) -> None:
        super().__init__(
            title="Pricing Relation",
            description="Generate the PA_PRICING relation that merges config to price varconds.",
            parent=parent,
            show_placeholder=False,
            content_stretch=True,
        )
        self._init_source_tabs(context)
        self.add_content(self._build_toolbar())
        self.add_content(self._build_view())

    def _build_toolbar(self) -> QWidget:
        box = QGroupBox("Generate", self)
        layout = QHBoxLayout(box)
        self._name_label = QLabel("", box)
        layout.addWidget(self._name_label, 1)
        self._copy_btn = QPushButton("Copy", box)
        self._copy_btn.clicked.connect(self._on_copy)
        layout.addWidget(self._copy_btn)
        return box

    def _build_view(self) -> QWidget:
        box = QGroupBox("PA_PRICING relation body", self)
        layout = _v(box)
        self._count_label = QLabel("", box)
        layout.addWidget(self._count_label)
        self._editor = QPlainTextEdit(box)
        self._editor.setReadOnly(True)
        self._editor.setPlaceholderText(
            "Click Generate to build the PA_PRICING relation from the active snapshot."
        )
        layout.addWidget(self._editor)
        return box

    def on_enter(self) -> None:
        """Generate PA_PRICING relations automatically when entering."""
        self._sync_source()
        if self.is_mdb_view():
            self.refresh()
            return
        self._on_generate()

    def refresh(self) -> None:
        """Maintenance MDB view only; PDM keeps its enter-time generation."""
        if self._begin_refresh():
            return
        if self.is_mdb_view():
            self._render_mdb()

    def _on_source_changed(self, _source: str) -> None:
        if self._begin_refresh():
            return
        if self.is_mdb_view():
            self._render_mdb()
        else:
            self._on_generate()

    def _render_mdb(self) -> None:
        """Show the imported PA_* relation objects. Never generates or stores."""
        snapshot = self._context.active_snapshot
        self._count_label.setStyleSheet("")
        if snapshot is None:
            self._name_label.setText(MDB_NOT_LOADED_TEXT)
            self._count_label.setText("")
            self._editor.setPlainText("")
            return
        relations = [
            r for r in snapshot.relation_objects if (r.name or "").startswith("PA_")
        ]
        self._name_label.setText(
            f"{len(relations)} imported PA_* relation(s) (MDB, read-only)"
        )
        self._count_label.setText(
            f"{sum(len(r.body or '') for r in relations):,} chars"
        )
        blocks = [f"* {r.name}" + "\r\n" + (r.body or "") for r in relations]
        self._editor.setPlainText(
            "\r\n\r\n".join(blocks) or "(no PA_* relations in the imported MDB)"
        )

    def _on_generate(self) -> None:
        service = PricingRelationService(self._context)
        snapshot = self._context.active_snapshot
        # Super products -> de-duplicated PA_<component> relations (each shared
        # component stored once, aligned to its articles via the BOM); non-super
        # stays a single PA_PRICING body.
        if snapshot is not None and snapshot.article_components:
            self._render_components(
                service, snapshot,
                service.generate_component_relations(snapshot),
                service.component_alignment(snapshot),
            )
            return
        result = service.generate()
        service.commit(snapshot, result)
        header = f"* {result.relation_name}"
        self._name_label.setText(result.relation_name)
        over = result.char_count_total > PricingRelationService.PCON_RELATION_CHAR_LIMIT
        self._count_label.setText(
            f"Total: {result.char_count_total:,} chars   |   "
            f"Components: {result.char_count_components:,} chars "
            f"({result.definition_count:,} definitions)"
            + ("   ⚠ exceeds 64000 limit" if over else "")
        )
        self._count_label.setStyleSheet(
            "color: #b00020; font-weight: bold;" if over else ""
        )
        body = result.body or "(nothing generated)"
        if result.warnings:
            body = body + "\r\n\r\n* Warnings:\r\n" + "\r\n".join(
                "*   " + w for w in result.warnings
            )
        self._editor.setPlainText(header + "\r\n\r\n" + body)

    def _render_components(self, service, snapshot, results, alignment) -> None:
        """Render + persist the de-duplicated PA_<component> relations, with a
        size summary and the BOM-driven article->relation alignment."""
        service.commit_split(snapshot, results)
        limit = PricingRelationService.PCON_RELATION_CHAR_LIMIT
        total = sum(r.char_count_total for r in results)
        largest = max((r.char_count_total for r in results), default=0)
        over = [r for r in results if r.char_count_total > limit]
        bases = {r.component_base for r in results}
        self._name_label.setText(
            f"{len(results)} PA_<component> relations ({len(bases)} components)"
        )
        self._count_label.setText(
            f"{len(results)} relations   |   {len(alignment):,} articles   |   "
            f"total {total:,} chars   |   largest {largest:,} chars"
            + (f"   ⚠ {len(over)} over 64000" if over else "   ✓ all under 64000")
        )
        self._count_label.setStyleSheet(
            "color: #b00020; font-weight: bold;" if over else ""
        )
        blocks: list[str] = []
        # Alignment first (which relations each article references), then bodies.
        blocks.append("* Article -> component relations (BOM alignment)")
        for art in sorted(alignment)[:200]:
            blocks.append(f"*   {art} : {', '.join(alignment[art])}")
        for r in results:
            flag = "  ⚠ OVER 64000" if r.char_count_total > limit else ""
            blocks.append(
                f"* {r.relation_name}  (RelObj {r.relobj_name}, "
                f"{r.char_count_total:,} chars, {r.definition_count:,} defs){flag}"
                "\r\n" + (r.body or "")
            )
        self._editor.setPlainText("\r\n\r\n".join(blocks) or "(nothing generated)")

    def _on_copy(self) -> None:
        QApplication.clipboard().setText(self._editor.toPlainText())

    def showEvent(self, event) -> None:  # noqa: N802 (Qt override)
        super().showEvent(event)
        self._sync_source()
        if not self.is_mdb_view():
            self._name_label.setText("")

    def is_ready(self) -> bool:
        snapshot = self._context.active_snapshot
        return snapshot is not None and snapshot.product is not None
