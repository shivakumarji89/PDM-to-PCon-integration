"""Front module selector for MK Product Workbench."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from core.modules import WorkbenchModule, module_title
from ui import theme


_PRIMARY_MODULES = (
    (WorkbenchModule.DEVELOPMENT, "01", "◆", "#70B52B", "Create and develop product engineering data.", "PRODUCT ENGINEERING"),
    (WorkbenchModule.MAINTENANCE, "02", "⌁", "#E83220", "Maintain and update published product packages.", "PUBLISHED DATA"),
    (WorkbenchModule.METATYPE, "03", "◇", "#70B52B", "Create and validate metatype definitions.", "HMX REPOSITORY"),
    (WorkbenchModule.OAP, "04", "◈", "#E83220", "Create and validate OAP definitions and packages.", "OAP CONFIGURATION"),
    (WorkbenchModule.QA_VALIDATION, "05", "✓", "#70B52B", "Validate product data and generated deliverables.", "QUALITY ASSURANCE"),
    (WorkbenchModule.BULK_UPDATE, "06", "⇄", "#E83220", "Run bulk maintenance operations on published packages.", "BULK OPERATIONS"),
)


class _StatusTile(QFrame):
    """Small truthful resource-status tile used in the front-page footer."""

    def __init__(self, label: str, value: str, detail: str = "") -> None:
        super().__init__()
        self.setObjectName("frontStatusTile")
        self.setStyleSheet(
            "QFrame#frontStatusTile { background:#FFFFFF; border:1px solid #E3E8EF; border-radius:9px; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)
        name = QLabel(label.upper())
        name.setStyleSheet("color:#7B8796; font-size:10px; font-weight:700;")
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("color:#17243A; font-size:12px; font-weight:700;")
        self.detail_label = QLabel(detail)
        self.detail_label.setStyleSheet("color:#7B8796; font-size:10px;")
        self.detail_label.setWordWrap(True)
        layout.addWidget(name)
        layout.addWidget(self.value_label)
        if detail:
            layout.addWidget(self.detail_label)

    def set_value(self, value: str, detail: str = "") -> None:
        self.value_label.setText(value)
        self.detail_label.setText(detail)


class ModuleHomePage(QWidget):
    """Landing screen for the six primary workbench modules."""

    module_selected = Signal(object)

    def __init__(self, context=None, parent: QWidget | None = None) -> None:
        # Backward compatibility with the former ModuleHomePage(parent) call.
        if isinstance(context, QWidget) and parent is None:
            parent, context = context, None
        super().__init__(parent)
        self._context = context
        self.setObjectName("moduleHomePage")
        self.setStyleSheet("QWidget#moduleHomePage { background:#F7F9FC; }")

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 22, 28, 18)
        root.setSpacing(14)

        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.setSpacing(3)
        eyebrow = QLabel("ENGINEERING WORKSPACE")
        eyebrow.setStyleSheet("color:#70A936; font-size:10px; font-weight:800; letter-spacing:2px;")
        title_block.addWidget(eyebrow)

        title = QLabel("MK Product Workbench")
        title.setObjectName("frontPageTitle")
        title.setFont(theme.font("workspace_title"))
        title.setStyleSheet("color:#17243A; font-size:25px; font-weight:750;")
        title_block.addWidget(title)

        subtitle = QLabel("PDM  ·  pCon Integration Suite")
        subtitle.setStyleSheet("color:#647184; font-size:13px;")
        title_block.addWidget(subtitle)

        accent = QFrame()
        accent.setFixedSize(64, 4)
        accent.setStyleSheet("background:#70B52B; border-radius:2px;")
        title_block.addWidget(accent)
        header.addLayout(title_block, 1)

        self._app_badge = QLabel("●  APPLICATION READY")
        self._app_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._app_badge.setStyleSheet(
            "QLabel { color:#4D941D; background:#EFF7E8; border:1px solid #D8EBC8; border-radius:13px; padding:8px 12px; font-size:10px; font-weight:800; }"
        )
        header.addWidget(self._app_badge, 0, Qt.AlignmentFlag.AlignTop)
        root.addLayout(header)

        hero = QFrame()
        hero.setObjectName("frontHero")
        hero.setStyleSheet("QFrame#frontHero { background:#FFFFFF; border:1px solid #E7ECF2; border-radius:14px; }")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(18, 10, 18, 10)
        hero_layout.setSpacing(16)

        hero_text = QVBoxLayout()
        hero_text.setSpacing(3)
        hero_heading = QLabel("One workspace. Every stage.")
        hero_heading.setStyleSheet("color:#17243A; font-size:15px; font-weight:700;")
        hero_text.addWidget(hero_heading)
        hero_copy = QLabel(
            "Select a module to work with product data, published packages, metatypes or validation."
        )
        hero_copy.setWordWrap(True)
        hero_copy.setStyleSheet("color:#647184; font-size:11px;")
        hero_text.addWidget(hero_copy)
        hero_layout.addLayout(hero_text, 1)

        visual = QLabel("PDM   ◈   DATA   ◈   pCon")
        visual.setAlignment(Qt.AlignmentFlag.AlignCenter)
        visual.setMinimumWidth(210)
        visual.setStyleSheet(
            "color:#4D941D; background:#F2F7ED; border:1px solid #E1EED6; border-radius:10px; padding:14px; font-size:13px; font-weight:800;"
        )
        hero_layout.addWidget(visual, 0)
        root.addWidget(hero)

        section_row = QHBoxLayout()
        section_title = QLabel("SELECT A MODULE")
        section_title.setStyleSheet("color:#647184; font-size:10px; font-weight:800; letter-spacing:1.5px;")
        section_row.addWidget(section_title)
        section_row.addStretch(1)
        hint = QLabel("Choose a workspace to continue")
        hint.setStyleSheet("color:#8A95A3; font-size:10px;")
        section_row.addWidget(hint)
        root.addLayout(section_row)

        self._cards_grid = QGridLayout()
        self._cards_grid.setContentsMargins(0, 0, 0, 0)
        self._cards_grid.setHorizontalSpacing(14)
        self._cards_grid.setVerticalSpacing(12)
        self._card_widgets: list[QFrame] = []
        for index, item in enumerate(_PRIMARY_MODULES):
            card = self._build_card(*item)
            self._card_widgets.append(card)
            self._cards_grid.addWidget(card, index // 3, index % 3)
        root.addLayout(self._cards_grid, 1)

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
        syte_line.setObjectName("syteLineModuleLink")
        syte_line.setCursor(Qt.CursorShape.PointingHandCursor)
        syte_line.setStyleSheet(
            "QPushButton#syteLineModuleLink { color:#647184; background:transparent; border:0; padding:4px 8px; font-size:11px; font-weight:700; }"
            "QPushButton#syteLineModuleLink:hover { color:#4D941D; }"
        )
        syte_line.clicked.connect(lambda: self.module_selected.emit(WorkbenchModule.SYTELINE_EXPORT))
        utility_row.addWidget(syte_line)
        utility_row.addStretch(1)
        root.addLayout(utility_row)

        self.refresh_status()

    def _build_card(self, module, number, glyph, accent, description, category) -> QFrame:
        card = QFrame(self)
        card.setObjectName("frontModuleCard")
        card.setMinimumHeight(142)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        card.setStyleSheet(
            "QFrame#frontModuleCard { background:#FFFFFF; border:1px solid #E3E8EF; border-radius:12px; }"
            f"QFrame#frontModuleCard:hover {{ border:1px solid {accent}; background:#FCFDFE; }}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 0, 14, 12)
        layout.setSpacing(6)

        accent_bar = QFrame(card)
        accent_bar.setFixedHeight(4)
        accent_bar.setStyleSheet(f"background:{accent}; border:0; border-top-left-radius:3px; border-top-right-radius:3px;")
        layout.addWidget(accent_bar)
        layout.addSpacing(7)

        accent_soft = "#EFF7E8" if accent == "#70B52B" else "#FCECE9"
        top = QHBoxLayout()
        number_label = QLabel(number)
        number_label.setStyleSheet(f"color:{accent}; background:" + accent_soft + "; border-radius:6px; padding:4px 7px; font-size:10px; font-weight:800;")
        top.addWidget(number_label)
        top.addStretch(1)
        category_label = QLabel(category)
        category_label.setStyleSheet("color:#8792A0; font-size:9px; font-weight:800; letter-spacing:0.7px;")
        top.addWidget(category_label)
        layout.addLayout(top)

        middle = QHBoxLayout()
        icon = QLabel(glyph)
        icon.setFixedSize(42, 42)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet(f"color:{accent}; background:" + accent_soft + "; border-radius:10px; font-size:23px; font-weight:700;")
        middle.addWidget(icon)

        text_block = QVBoxLayout()
        text_block.setSpacing(2)
        name = QLabel(module_title(module))
        name.setStyleSheet("color:#17243A; font-size:15px; font-weight:750;")
        text_block.addWidget(name)
        copy = QLabel(description)
        copy.setWordWrap(True)
        copy.setStyleSheet("color:#647184; font-size:10px;")
        text_block.addWidget(copy)
        middle.addLayout(text_block, 1)

        arrow = QLabel("↗")
        arrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        arrow.setFixedSize(27, 27)
        arrow.setStyleSheet(f"color:{accent}; border:1px solid {accent}; border-radius:13px; font-size:14px; font-weight:700;")
        middle.addWidget(arrow)
        layout.addLayout(middle)

        action = QPushButton("Open workspace")
        action.setCursor(Qt.CursorShape.PointingHandCursor)
        action.setStyleSheet(
            f"QPushButton {{ color:{accent}; background:#F5F8F1; border:0; border-radius:6px; padding:6px 9px; text-align:left; font-size:10px; font-weight:800; }}"
            "QPushButton:hover { background:#EAF2E2; }"
        )
        action.clicked.connect(lambda checked=False, selected=module: self.module_selected.emit(selected))
        layout.addWidget(action)
        return card

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
