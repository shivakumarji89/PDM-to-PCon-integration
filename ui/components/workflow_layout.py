"""Shared layout foundation for internal workflow pages.

``WorkflowPageLayout`` offers five optional regions - header, toolbar, summary
cards, main working area and footer - built from Qt layouts only (no absolute
positioning). Regions with no content stay hidden, so a page uses just what it
needs. Presentation only.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui import theme
from ui.components.workflow_styles import divider_qss, label, set_button_role


class StatusPill(QLabel):
    """Small rounded status indicator (``Ready``, ``Blocked`` ...)."""

    def __init__(self, text: str = "", tone: str = "neutral", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_status(text, tone)

    def set_status(self, text: str, tone: str = "neutral") -> None:
        accent, soft, border = theme.tone_colors(tone)
        self.setText(text)
        self.setVisible(bool(text))
        self.setStyleSheet(
            f"background: {soft}; color: {accent}; border: 1px solid {border}; "
            f"border-radius: 11px; padding: 3px 12px; font-size: 13px; font-weight: 600;"
        )


# A distinct symbol for each named workflow; text glyphs remain crisp at any DPI.
_WORKFLOW_GLYPHS = {
    # Core product workflows
    "product": "⬡",
    "articles": "▤",
    "class creation": "▦",
    "text": "T",
    "relation object": "⛓",
    "pricing": "＄",
    "pricing relation": "⇄",
    "pricing relations": "⇄",
    "review": "✓",
    "generate": "⚙",
    "engineering": "⌘",
    # Maintenance and data operations
    "maintenance": "✎",
    "pdm / mdb comparison": "↔",
    "pdm ↔ mdb comparison": "↔",
    "comparison": "↔",
    "bulk update": "▥",
    # QA and generated deliverables
    "obx validation": "✔",
    "cet sif validation": "⊙",
    "article obx generator": "◇",
    "article obx generator (pcon sdk)": "◈",
    "pcon article obx generator": "◈",
    "export pdm data": "↗",
    "syteline export": "⇧",
    # Metatype workflows
    "create metatype": "⌗",
    "repository analysis": "⌕",
    "metatype articles": "▣",
    "metatype properties": "▧",
    "metatype values": "◆",
    "property values": "◆",
    "metatype texts": "¶",
    "texts": "¶",
    "metatype setup": "⚒",
    "setup": "⚒",
    "metatype relations": "∞",
    "relations / ordering": "∞",
    "metatype review": "☑",
    "final review": "☑",
    # OAP and supporting workspaces
    "oap": "◎",
    "oap setup": "⚑",
}
def workflow_glyph(title: str) -> str:
    """Return the dedicated visual symbol for a workflow/page title."""
    key = " ".join(title.casefold().replace("&", " ").split())
    return _WORKFLOW_GLYPHS.get(key, "◇")

class WorkflowHeader(QWidget):
    """Title, green accent rule, description, optional status pill and actions."""

    def __init__(self, title: str = "", description: str = "", parent: QWidget | None = None,
                 glyph: str = "") -> None:
        super().__init__(parent)
        self.setObjectName("wfHeader")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            f"QWidget#wfHeader {{ background: #FFFFFF; border: 1px solid {theme.WB_BORDER}; "
            f"border-radius: 12px; }}"
        )
        outer = QHBoxLayout(self)
        outer.setContentsMargins(theme.SPACE_3, 8, theme.SPACE_3, 8)
        outer.setSpacing(theme.SPACE_3)
        glyph = glyph or workflow_glyph(title)
        if glyph:
            from ui.components.workflow_cards import IconBadge

            self.icon = IconBadge(glyph, "success", 42, self)
            outer.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignVCenter)

        text = QVBoxLayout()
        text.setSpacing(0)
        self.title_label = label(title, "wf_title", theme.WB_NAVY, size=21, parent=self)
        self.title_label.setObjectName("pageTitle")
        text.addWidget(self.title_label)
        self.description_label = label(description, "subtitle", theme.WB_TEXT_SECONDARY, wrap=True, parent=self)
        self.description_label.setObjectName("pageSubtitle")
        self.description_label.setVisible(bool(description))
        text.addWidget(self.description_label)
        outer.addLayout(text, 1)

        self.status_pill = StatusPill("", "neutral", self)
        outer.addWidget(self.status_pill, 0, Qt.AlignmentFlag.AlignTop)
        self._actions = QHBoxLayout()
        self._actions.setSpacing(theme.SPACE_2)
        outer.addLayout(self._actions)

    def set_status(self, text: str, tone: str = "neutral") -> None:
        self.status_pill.set_status(text, tone)

    def add_action(self, widget: QWidget, role: str | None = "secondary") -> None:
        """Place a real page action in the headline action group.

        Existing callbacks and enabled/disabled state remain owned by the page.
        Use ``role="primary"`` for the forward/commit action.
        """
        if role is not None and hasattr(widget, "setStyleSheet"):
            set_button_role(widget, role)  # type: ignore[arg-type]
        self._actions.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)


class ActionBar(QFrame):
    """Toolbar surface: groups of related actions separated by thin dividers."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("wfActionBar")
        self.setStyleSheet(
            f"QFrame#wfActionBar {{ background: {theme.WB_SURFACE}; border: 1px solid {theme.WB_BORDER}; "
            f"border-radius: {theme.RADIUS_LG}px; }}"
        )
        self._row = QHBoxLayout(self)
        self._row.setContentsMargins(theme.SPACE_3, theme.SPACE_2, theme.SPACE_3, theme.SPACE_2)
        self._row.setSpacing(theme.SPACE_2)
        self._groups = 0

    def add_group(self, *widgets: QWidget, role: str | None = None) -> None:
        """Add related actions. ``role`` styles buttons (primary/secondary/danger/ghost)."""
        if self._groups:
            sep = QFrame(self)
            sep.setObjectName(f"wfActionSep{self._groups}")
            sep.setFixedWidth(1)
            sep.setStyleSheet(divider_qss(sep.objectName()))
            self._row.addWidget(sep)
        for w in widgets:
            if role is not None:
                set_button_role(w, role)  # type: ignore[arg-type]
            self._row.addWidget(w)
        self._groups += 1

    def add_stretch(self) -> None:
        self._row.addStretch(1)


class CardRow(QWidget):
    """Responsive row of cards: reflows to fewer columns as the width shrinks."""

    def __init__(self, min_card_width: int = 200, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._min = max(120, min_card_width)
        self._cards: list[QWidget] = []
        self._cols = 0
        self._grid = QGridLayout(self)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(theme.SPACE_3)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

    def add_card(self, card: QWidget) -> None:
        self._cards.append(card)
        self._reflow(force=True)

    def columns(self) -> int:
        return self._cols

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        self._reflow()

    def _reflow(self, force: bool = False) -> None:
        if not self._cards:
            return
        usable = max(self.width(), 1)
        cols = max(1, min(len(self._cards), (usable + self._grid.spacing()) // (self._min + self._grid.spacing())))
        if self.width() <= 1:  # before first layout: assume everything fits one row
            cols = len(self._cards)
        if cols == self._cols and not force:
            return
        self._cols = cols
        for card in self._cards:
            self._grid.removeWidget(card)
        for i, card in enumerate(self._cards):
            self._grid.addWidget(card, i // cols, i % cols)
        for c in range(len(self._cards)):
            self._grid.setColumnStretch(c, 1 if c < cols else 0)

    def minimumSizeHint(self):  # noqa: N802 - Qt override
        # Never force the page wider than one card: the row reflows instead.
        hint = super().minimumSizeHint()
        hint.setWidth(self._min)
        return hint


class _Region(QWidget):
    """A page region that hides itself while empty."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)
        self.layout_.setSpacing(theme.SPACE_3)
        self.setVisible(False)

    def add(self, widget: QWidget, stretch: int = 0) -> None:
        self.layout_.addWidget(widget, stretch)
        self.setVisible(True)


class WorkflowPageLayout(QWidget):
    """Header / toolbar / summary / main / footer composition for a workflow page."""

    def __init__(self, title: str = "", description: str = "", parent: QWidget | None = None,
                 glyph: str = "") -> None:
        super().__init__(parent)
        self.setObjectName("wfPage")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(theme.SPACE_3)

        self.header = WorkflowHeader(title, description, self, glyph)
        self._toolbar = _Region(self)
        self._summary = _Region(self)
        self._main = _Region(self)
        self._footer = _Region(self)
        self._main.setVisible(True)
        root.addWidget(self.header)
        root.addWidget(self._toolbar)
        root.addWidget(self._summary)
        root.addWidget(self._main, 1)
        root.addWidget(self._footer)

    @property
    def main_layout(self) -> QVBoxLayout:
        return self._main.layout_

    def add_toolbar(self, widget: QWidget) -> None:
        self._toolbar.add(widget)

    def add_summary(self, widget: QWidget) -> None:
        self._summary.add(widget)

    def add_main(self, widget: QWidget, stretch: int = 0) -> None:
        self._main.add(widget, stretch)

    def add_footer(self, widget: QWidget) -> None:
        self._footer.add(widget)
