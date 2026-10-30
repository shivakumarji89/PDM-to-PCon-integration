"""Front module selector for MK Product Workbench."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from core.modules import WorkbenchModule, module_title
from ui import theme


# Six workspaces arranged around the central PDM -> DATA -> pCon hub.
_PRIMARY_MODULES = (
    (WorkbenchModule.DEVELOPMENT, "01", "◆", "#70B52B", "Product engineering", "Create and develop product data."),
    (WorkbenchModule.MAINTENANCE, "02", "⌁", "#E83220", "Published data", "Maintain existing product packages."),
    (WorkbenchModule.METATYPE, "03", "◇", "#70B52B", "HMX repository", "Create and validate metatypes."),
    (WorkbenchModule.OAP, "04", "◈", "#E83220", "OAP configuration", "Create and validate OAP packages."),
    (WorkbenchModule.QA_VALIDATION, "05", "✓", "#70B52B", "Quality assurance", "Validate data and deliverables."),
    (WorkbenchModule.BULK_UPDATE, "06", "⇄", "#E83220", "Bulk operations", "Run maintenance across packages."),
)


class _StatusTile(QFrame):
    """Small truthful resource-status tile used in the front-page footer."""

    def __init__(self, label: str, value: str, detail: str = "") -> None:
        super().__init__()
        self.setObjectName("frontStatusTile")
        self.setStyleSheet(
            "QFrame#frontStatusTile { background:#FFFFFF; border:1px solid #E3E8EF; border-radius:8px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(11, 7, 11, 7)
        layout.setSpacing(2)
        name = QLabel(label.upper())
        name.setStyleSheet("color:#7B8796; font-size:9px; font-weight:700;")
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("color:#17243A; font-size:11px; font-weight:700;")
        self.detail_label = QLabel(detail)
        self.detail_label.setStyleSheet("color:#7B8796; font-size:9px;")
        self.detail_label.setWordWrap(True)
        layout.addWidget(name)
        layout.addWidget(self.value_label)
        if detail:
            layout.addWidget(self.detail_label)

    def set_value(self, value: str, detail: str = "") -> None:
        self.value_label.setText(value)
        self.detail_label.setText(detail)


class ModuleHomePage(QWidget):
    """Landing screen with workspace actions arranged around the PDM/data/pCon hub."""

    module_selected = Signal(object)

    def __init__(self, context=None, parent: QWidget | None = None) -> None:
        # Backward compatibility with the former ModuleHomePage(parent) call.
        if isinstance(context, QWidget) and parent is None:
            parent, context = context, None
        super().__init__(parent)
        self._context = context
        self.setObjectName("moduleHomePage")
        self.setStyleSheet("QWidget#moduleHomePage { background:#F5F7FA; }")

        root = QVBoxLayout(self)
        root.setContentsMargins(26, 18, 26, 14)
        root.setSpacing(11)

        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        eyebrow = QLabel("ENGINEERING WORKSPACE")
        eyebrow.setStyleSheet("color:#70A936; font-size:9px; font-weight:800; letter-spacing:2px;")
        title_block.addWidget(eyebrow)
        title = QLabel("MK Product Workbench")
        title.setFont(theme.font("workspace_title"))
        title.setStyleSheet("color:#17243A; font-size:23px; font-weight:750;")
        title_block.addWidget(title)
        subtitle = QLabel("PDM  ·  pCon Integration Suite")
        subtitle.setStyleSheet("color:#647184; font-size:12px;")
        title_block.addWidget(subtitle)
        header.addLayout(title_block, 1)

        self._app_badge = QLabel("●  APPLICATION READY")
        self._app_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._app_badge.setStyleSheet(
            "color:#4D941D; background:#EFF7E8; border:1px solid #D8EBC8; "
            "border-radius:11px; padding:7px 12px; font-size:9px; font-weight:800;"
        )
        header.addWidget(self._app_badge, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header)

        section = QHBoxLayout()
        section_title = QLabel("CHOOSE A WORKSPACE")
        section_title.setStyleSheet("color:#647184; font-size:10px; font-weight:800; letter-spacing:1.4px;")
        section.addWidget(section_title)
        section.addStretch(1)
        section_hint = QLabel("Select any module to open its workflow")
        section_hint.setStyleSheet("color:#8994A2; font-size:10px;")
        section.addWidget(section_hint)
        root.addLayout(section)

        # The central hub remains the visual anchor; module launchers surround it.
        stage = QFrame()
        stage.setObjectName("moduleOrbitStage")
        stage.setStyleSheet(
            "QFrame#moduleOrbitStage { background:#FFFFFF; border:1px solid #E4EAF0; border-radius:15px; }"
        )
        orbit = QGridLayout(stage)
        orbit.setContentsMargins(22, 18, 22, 18)
        orbit.setHorizontalSpacing(18)
        orbit.setVerticalSpacing(14)
        orbit.setColumnStretch(0, 1)
        orbit.setColumnStretch(1, 1)
        orbit.setColumnStretch(2, 1)
        orbit.setRowStretch(0, 1)
        orbit.setRowStretch(1, 1)
        orbit.setRowStretch(2, 1)

        placements = ((0, 0), (2, 0), (0, 2), (2, 2), (1, 0), (1, 2))
        self._module_buttons: list[QPushButton] = []
        for item, (row, col) in zip(_PRIMARY_MODULES, placements):
            button = self._build_module_button(*item)
            self._module_buttons.append(button)
            orbit.addWidget(button, row, col)

        hub = self._build_hub()
        orbit.addWidget(hub, 0, 1, 3, 1)
        root.addWidget(stage, 1)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        self._pdm_status = _StatusTile("PDM Database", "Not checked", "Connection not tested")
        self._repository_status = _StatusTile("Repository", "Not checked", "Local path not verified")
        self._mdb_status = _StatusTile("MDB Snapshot", "Not loaded", "No imported MDB snapshot")
        self._application_status = _StatusTile("Application", "Ready", "Module selector initialized")
        for tile in (self._pdm_status, self._repository_status, self._mdb_status, self._application_status):
            bottom.addWidget(tile, 1)
        root.addLayout(bottom)

        utility_row = QHBoxLayout()
        note = QLabel("Additional tools")
        note.setStyleSheet("color:#8792A0; font-size:10px; font-weight:700;")
        utility_row.addWidget(note)
        syte_line = QPushButton("SyteLine Export  →")
        syte_line.setCursor(Qt.CursorShape.PointingHandCursor)
        syte_line.setStyleSheet(
            "QPushButton { color:#647184; background:transparent; border:0; padding:3px 8px; "
            "font-size:10px; font-weight:700; } QPushButton:hover { color:#4D941D; }"
        )
        syte_line.clicked.connect(lambda: self.module_selected.emit(WorkbenchModule.SYTELINE_EXPORT))
        utility_row.addWidget(syte_line)
        utility_row.addStretch(1)
        root.addLayout(utility_row)

        self.refresh_status()

    def _build_hub(self) -> QFrame:
        hub = QFrame()
        hub.setObjectName("moduleHub")
        hub.setMinimumWidth(250)
        hub.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        hub.setStyleSheet(
            "QFrame#moduleHub { background:#F1F7EB; border:1px solid #DDEBD2; border-radius:16px; }"
        )
        layout = QVBoxLayout(hub)
        layout.setContentsMargins(18, 22, 18, 22)
        layout.setSpacing(12)
        layout.addStretch(1)

        eyebrow = QLabel("PRODUCT DATA FLOW")
        eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        eyebrow.setStyleSheet("color:#6C9D43; font-size:9px; font-weight:800; letter-spacing:1.8px;")
        layout.addWidget(eyebrow)

        flow = QHBoxLayout()
        flow.setSpacing(5)
        for index, label in enumerate(("PDM", "DATA", "pCon")):
            node = QLabel(label)
            node.setAlignment(Qt.AlignmentFlag.AlignCenter)
            node.setMinimumHeight(48)
            node.setStyleSheet(
                "color:#315D20; background:#FFFFFF; border:1px solid #D9E8CE; "
                "border-radius:9px; padding:5px 8px; font-size:13px; font-weight:800;"
            )
            flow.addWidget(node, 1)
            if index < 2:
                arrow = QLabel("›")
                arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
                arrow.setStyleSheet("color:#79A85A; font-size:20px; font-weight:700;")
                flow.addWidget(arrow)
        layout.addLayout(flow)

        divider = QFrame()
        divider.setFixedHeight(2)
        divider.setStyleSheet("background:#DCE9D2; border:0;")
        layout.addWidget(divider)

        heading = QLabel("One connected workspace")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        heading.setStyleSheet("color:#17243A; font-size:15px; font-weight:750;")
        layout.addWidget(heading)
        copy = QLabel("Choose a module around the hub to work with product engineering, published packages, repository data or validation.")
        copy.setWordWrap(True)
        copy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        copy.setStyleSheet("color:#647184; font-size:10px;")
        layout.addWidget(copy)
        layout.addStretch(1)
        return hub

    def _build_module_button(self, module, number, glyph, accent, category, description) -> QPushButton:
        button = QPushButton(f"{number}   {glyph}   {module_title(module)}\n{category.upper()}\n{description}")
        button.setObjectName("moduleOrbitButton")
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setMinimumHeight(104)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        soft = "#EFF7E8" if accent == "#70B52B" else "#FCECE9"
        button.setStyleSheet(
            "QPushButton#moduleOrbitButton {"
            f" color:#17243A; background:#FFFFFF; border:1px solid #E2E8EF; border-left:4px solid {accent};"
            " border-radius:10px; padding:12px; text-align:left; font-size:12px; font-weight:700;"
            "}"
            "QPushButton#moduleOrbitButton:hover {"
            f" background:{soft}; border:1px solid {accent};"
            "}"
            "QPushButton#moduleOrbitButton:pressed { background:#EAF0E6; }"
        )
        button.clicked.connect(lambda checked=False, selected=module: self.module_selected.emit(selected))
        return button

    def refresh_status(self) -> None:
        """Show configured/loaded state without claiming an untested DB connection."""
        context = self._context
        if context is None:
            return
        config = getattr(context, "config", None)
        if config is not None:
            preset = config.active_pdm_preset() or "Custom configuration"
            self._pdm_status.set_value(
                "Configured", f"{preset} · {config.pdm_server}/{config.pdm_database}"
            )
            roots = getattr(config, "repository_browser_roots", {}) or {}
            available = [name for name, path in roots.items() if Path(path).is_dir()]
            self._repository_status.set_value(
                "Available" if available else "Path not found",
                ", ".join(available) if available else "Configured repository folders not found",
            )
        imported = getattr(context, "mdb_import_snapshot", None)
        self._mdb_status.set_value(
            "Loaded" if imported is not None else "Not loaded",
            "Imported MDB snapshot is available" if imported is not None else "No imported MDB snapshot",
        )
