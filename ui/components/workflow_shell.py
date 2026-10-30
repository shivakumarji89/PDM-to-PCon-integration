"""Shared workflow shell: application header, module sidebar and detail tabs.

Presentation-only building blocks that reproduce the MK Product Workbench
internal-workflow chrome: a top status header, a left panel with the module
identity, vertical workflow steps (with a progress connector) and a tips card,
and styled bottom detail tabs. The sidebar reads step state from the existing
:class:`~workflow.manager.WorkflowManager` and navigates through its existing
``jump_to`` rule - it owns no workflow state of its own.
"""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFontMetrics,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ui import theme
from ui.components.workflow_cards import Card
from ui.components.workflow_styles import label, set_button_role
from workflow.state import WorkflowState

_STATE_NAME = {
    WorkflowState.COMPLETED: "completed",
    WorkflowState.IN_PROGRESS: "current",
    WorkflowState.READY: "ready",
    WorkflowState.BLOCKED: "blocked",
    WorkflowState.NOT_STARTED: "not_started",
    WorkflowState.INVALID: "invalid",
}


# --------------------------------------------------------------------------
# Application header
# --------------------------------------------------------------------------
class _HeaderIcon(QWidget):
    """Small flat glyph (database / folder / document) for a header indicator."""

    def __init__(self, kind: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._kind = kind
        self.setFixedSize(22, 22)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink, cut = QColor("#4A5568"), QColor(theme.WB_SURFACE)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(ink)
        if self._kind == "folder":
            p.drawRoundedRect(QRectF(2, 4, 9, 5), 1.5, 1.5)
            p.drawRoundedRect(QRectF(2, 6, 18, 12), 2, 2)
        elif self._kind == "doc":
            path = QPainterPath()
            path.moveTo(5, 2); path.lineTo(14, 2); path.lineTo(18, 6)
            path.lineTo(18, 20); path.lineTo(5, 20); path.closeSubpath()
            p.drawPath(path)
            p.setPen(QPen(cut, 1.5))
            for y in (11, 14.5, 18):
                p.drawLine(QPointF(8, y), QPointF(15, y))
        else:  # database cylinder
            p.drawRect(QRectF(3, 5, 16, 12))
            p.drawEllipse(QRectF(3, 2, 16, 6))
            p.drawEllipse(QRectF(3, 14, 16, 6))
            p.setPen(QPen(cut, 1.2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            for y in (8.5, 13):
                p.drawArc(QRectF(3, y - 3, 16, 6), 180 * 16, 180 * 16)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(ink)
            p.drawRect(QRectF(3, 5, 16, 1))


class StatusIndicator(QWidget):
    """Icon + (dot, name) over state text (``PDM`` / ``Loaded``) for the header."""

    def __init__(self, name: str, parent: QWidget | None = None, icon: str = "db") -> None:
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(theme.SPACE_3, 0, theme.SPACE_3, 0)
        row.setSpacing(theme.SPACE_2)
        row.addWidget(_HeaderIcon(icon, self), 0, Qt.AlignmentFlag.AlignVCenter)
        col = QVBoxLayout()
        col.setSpacing(0)
        top = QHBoxLayout()
        top.setSpacing(5)
        self._dot = QFrame(self)
        self._dot.setFixedSize(8, 8)
        self.name_label = label(name, "helper", theme.WB_NAVY, weight=700, parent=self)
        top.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)
        top.addWidget(self.name_label)
        top.addStretch(1)
        self.state_label = label("-", "helper", theme.WB_TEXT_SECONDARY, parent=self)
        col.addLayout(top)
        col.addWidget(self.state_label)
        row.addLayout(col)
        self.set_state("-", "neutral")

    def set_state(self, text: str, tone: str, tooltip: str = "") -> None:
        accent = theme.tone_colors(tone)[0]
        self._dot.setStyleSheet(f"background: {accent}; border-radius: 4px;")
        self.state_label.setText(text)
        self.state_label.setMinimumWidth(self.state_label.fontMetrics().horizontalAdvance(text) + 4)
        self.updateGeometry()
        self.setToolTip(tooltip or f"{self.name_label.text()}: {text}")


class AppHeaderBar(QFrame):
    """Brand, subtitle, connection/data status indicators and Settings access."""

    settings_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("wfAppHeader")
        self.setStyleSheet(
            f"QFrame#wfAppHeader {{ background: {theme.WB_SURFACE}; "
            f"border-bottom: 1px solid {theme.WB_BORDER}; }}"
        )
        row = QHBoxLayout(self)
        row.setContentsMargins(theme.SPACE_4, 6, theme.SPACE_4, 6)
        row.setSpacing(theme.SPACE_3)

        brand = QVBoxLayout()
        brand.setSpacing(1)
        title = label("MK Product Workbench", "app_title", theme.WB_NAVY, size=19, parent=self)
        rule = QFrame(self)
        rule.setObjectName("wfBrandRule")
        rule.setFixedSize(34, 3)
        rule.setStyleSheet(f"QFrame#wfBrandRule {{ background: {theme.WB_GREEN}; border: none; border-radius: 1px; }}")
        brand.addWidget(title)
        brand.addWidget(rule)
        row.addLayout(brand)

        row.addWidget(self._sep("wfHeaderSepA", 22))
        row.addWidget(label("PDM · pCon Integration Suite", "subtitle", theme.WB_TEXT_SECONDARY, parent=self))
        row.addStretch(1)

        self._indicators: dict[str, StatusIndicator] = {}
        for key, name, icon in (("pdm", "PDM", "db"), ("repository", "Repository", "folder"), ("mdb", "MDB", "doc")):
            ind = StatusIndicator(name, self, icon)
            self._indicators[key] = ind
            row.addWidget(ind)
            row.addWidget(self._sep(f"wfHeaderSep_{key}"))

        self.settings_button = QPushButton("⚙  Settings", self)
        self.settings_button.setToolTip("Open the Settings menu")
        set_button_role(self.settings_button, "ghost")
        self.settings_button.clicked.connect(self.settings_clicked)
        row.addWidget(self.settings_button)

    def _sep(self, name: str, height: int = 30) -> QFrame:
        sep = QFrame(self)
        sep.setObjectName(name)
        sep.setFixedSize(1, height)
        sep.setStyleSheet(f"QFrame#{name} {{ background: {theme.WB_DIVIDER}; border: none; }}")
        return sep

    def set_indicator(self, key: str, text: str, tone: str, tooltip: str = "") -> None:
        ind = self._indicators.get(key)
        if ind is not None:
            ind.set_state(text, tone, tooltip)

    def indicator(self, key: str) -> StatusIndicator:
        return self._indicators[key]


# --------------------------------------------------------------------------
# Sidebar: module identity, vertical steps, tips
# --------------------------------------------------------------------------
class ModuleIdentityPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("wfIdentity")
        self.setStyleSheet("QWidget#wfIdentity { background: transparent; }")
        col = QVBoxLayout(self)
        col.setContentsMargins(theme.SPACE_3, theme.SPACE_3, theme.SPACE_3, theme.SPACE_2)
        col.setSpacing(theme.SPACE_1)
        self.title_label = label("", "wf_title", theme.WB_NAVY, size=24, parent=self)
        self.description_label = label("", "subtitle", theme.WB_TEXT_SECONDARY, wrap=True, parent=self)
        col.addWidget(self.title_label)
        col.addWidget(self.description_label)

    def set_module(self, title: str, description: str) -> None:
        self.title_label.setText(title)
        self.description_label.setText(description)


def _wrap_lines(fm: QFontMetrics, text: str, width: int, max_lines: int) -> list[str]:
    """Greedy word wrap into at most ``max_lines`` lines; the last one is elided."""
    words, lines, cur = text.split(), [], ""
    for i, word in enumerate(words):
        trial = f"{cur} {word}".strip()
        if fm.horizontalAdvance(trial) <= width or not cur:
            cur = trial
            continue
        lines.append(cur)
        cur = word
        if len(lines) == max_lines - 1:
            cur = " ".join(words[i:])
            break
    if cur:
        lines.append(fm.elidedText(cur, Qt.TextElideMode.ElideRight, width))
    return lines[:max_lines]


class _StepRow(QWidget):
    """One workflow step: connector, status circle, title and wrapped description."""

    clicked = Signal(object)

    _TEXT_X = 54
    _MAX_DESC_LINES = 2

    def __init__(self, step, index: int, title: str, description: str,
                 first: bool, last: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.step = step
        self._index = index
        self._title = title
        self._description = description
        self._first = first
        self._last = last
        self._state = "not_started"
        self._prev_done = False
        self._hover = False
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(self._height_for(230))  # rows never compress; the list scrolls instead
        self.setAccessibleName(title)

    @property
    def state(self) -> str:
        return self._state

    @property
    def enabled_for_click(self) -> bool:
        return self._state != "blocked"

    def set_prev_done(self, done: bool) -> None:
        if done != self._prev_done:
            self._prev_done = done
            self.update()

    def set_state(self, state: str) -> None:
        if state != self._state:
            self._state = state
            self.setCursor(Qt.CursorShape.PointingHandCursor if self.enabled_for_click
                           else Qt.CursorShape.ArrowCursor)
            self.update()
        self.setToolTip(f"{self._title} — {theme.status_style(self._state_status()).label}\n{self._description}")

    def _state_status(self) -> str:
        return {"completed": "completed", "current": "current", "ready": "ready",
                "blocked": "blocked", "not_started": "not_started", "invalid": "invalid"}[self._state]

    # -- geometry -----------------------------------------------------------
    def _text_width(self, width: int) -> int:
        return max(40, width - self._TEXT_X - 14)

    def _desc_lines(self, width: int) -> list[str]:
        return _wrap_lines(QFontMetrics(theme.font("helper")), self._description,
                           self._text_width(width), self._MAX_DESC_LINES)

    def _title_lines(self, width: int) -> list[str]:
        return _wrap_lines(QFontMetrics(theme.font("wf_card_title")), self._title,
                           self._text_width(width), 2)

    def _height_for(self, width: int) -> int:
        lines = max(1, len(self._desc_lines(width)))
        titles = max(1, len(self._title_lines(width)))
        return (8 + titles * QFontMetrics(theme.font("wf_card_title")).height() + 1
                + lines * QFontMetrics(theme.font("helper")).lineSpacing() + 8)

    def sizeHint(self) -> QSize:  # noqa: N802 - Qt override
        return QSize(220, self.height())

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override
        super().resizeEvent(event)
        needed = self._height_for(self.width())
        if needed != self.height():
            self.setFixedHeight(needed)

    def enterEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._hover = True
        self.update()

    def leaveEvent(self, event) -> None:  # noqa: N802 - Qt override
        self._hover = False
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self._activate()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self._activate()
            return
        super().keyPressEvent(event)

    def _activate(self) -> None:
        if self.enabled_for_click:
            self.clicked.emit(self.step)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy, r = 30.0, h / 2.0, 14.0
        state = self._state
        current = state == "current"
        panel = QRectF(2, 3, w - 4, h - 6)

        # Connected progress line: green between two finished steps, grey otherwise.
        p.setPen(QPen(QColor(theme.WB_GREEN if self._prev_done else theme.WB_DIVIDER), 2))
        if not self._first:
            p.drawLine(QPointF(cx, 0), QPointF(cx, cy - r))
        p.setPen(QPen(QColor(theme.WB_GREEN if state == "completed" else theme.WB_DIVIDER), 2))
        if not self._last:
            p.drawLine(QPointF(cx, cy + r), QPointF(cx, h))

        # Current step: prominent green selection panel with a chevron.
        if current:
            grad = QLinearGradient(panel.topLeft(), panel.topRight())
            grad.setColorAt(0, QColor(theme.WB_GREEN))
            grad.setColorAt(1, QColor(theme.WB_GREEN_DARK))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(grad)
            p.drawRoundedRect(panel, theme.RADIUS_LG, theme.RADIUS_LG)
            p.setPen(QPen(QColor("#FFFFFF"), 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                          Qt.PenJoinStyle.RoundJoin))
            p.drawPolyline(QPolygonF([QPointF(w - 20, cy - 5), QPointF(w - 14, cy), QPointF(w - 20, cy + 5)]))
        elif self._hover and self.enabled_for_click:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(theme.WB_GREEN_SOFT))
            p.drawRoundedRect(panel, theme.RADIUS_LG, theme.RADIUS_LG)

        # Status circle: tick when completed, otherwise the step number.
        if state == "completed":
            fill, edge, glyph_color = theme.WB_GREEN, theme.WB_GREEN, "#FFFFFF"
        elif current:
            fill, edge, glyph_color = "#FFFFFF", "#FFFFFF", theme.WB_GREEN_DARK
        elif state == "invalid":
            fill, edge, glyph_color = theme.WB_RED, theme.WB_RED, "#FFFFFF"
        elif state == "blocked":
            fill, edge, glyph_color = theme.WB_SURFACE, theme.WB_DIVIDER, theme.WB_NEUTRAL
        else:
            fill, edge, glyph_color = theme.WB_NEUTRAL_SOFT, theme.WB_DIVIDER, theme.WB_TEXT_SECONDARY
        p.setPen(QPen(QColor(edge), 1.5, Qt.PenStyle.DashLine if state == "blocked" else Qt.PenStyle.SolidLine))
        p.setBrush(QColor(fill))
        circle = QRectF(cx - r, cy - r, 2 * r, 2 * r)
        p.drawEllipse(circle)
        if state == "completed":
            p.setPen(QPen(QColor("#FFFFFF"), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                          Qt.PenJoinStyle.RoundJoin))
            p.drawPolyline(QPolygonF([QPointF(cx - 5.5, cy + 0.5), QPointF(cx - 1.5, cy + 4.5), QPointF(cx + 6, cy - 4)]))
        else:
            gf = theme.font("wf_card_title")
            gf.setPixelSize(14)
            p.setFont(gf)
            p.setPen(QColor(glyph_color))
            p.drawText(circle, Qt.AlignmentFlag.AlignCenter, "!" if state == "invalid" else str(self._index))

        # Title + wrapped description (never clipped mid-glyph).
        x = self._TEXT_X
        avail = self._text_width(w)
        tf, df = theme.font("wf_card_title"), theme.font("helper")
        tfm, dfm = QFontMetrics(tf), QFontMetrics(df)
        title_color = "#FFFFFF" if current else (theme.WB_NAVY if state != "blocked" else theme.WB_NEUTRAL)
        desc_color = "#EAF5DA" if current else (theme.WB_NEUTRAL if state == "blocked" else theme.WB_TEXT_SECONDARY)
        lines = self._desc_lines(w)
        title_lines = self._title_lines(w)
        block_h = len(title_lines) * tfm.height() + 1 + max(1, len(lines)) * dfm.lineSpacing()
        y = cy - block_h / 2.0
        p.setFont(tf)
        p.setPen(QColor(title_color))
        for line in title_lines:
            p.drawText(QRectF(x, y, avail, tfm.height()), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, line)
            y += tfm.height()
        y += 1
        p.setFont(df)
        p.setPen(QColor(desc_color))
        for line in lines:
            p.drawText(QRectF(x, y, avail, dfm.lineSpacing()), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, line)
            y += dfm.lineSpacing()

        if self.hasFocus():
            p.setPen(QPen(QColor(theme.WB_GREEN_DARK), 1, Qt.PenStyle.DotLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(panel.adjusted(0.5, 0.5, -0.5, -0.5), theme.RADIUS_LG, theme.RADIUS_LG)


class WorkflowStepNav(QWidget):
    """Vertical list of :class:`_StepRow`s. Emits ``step_clicked(step)``."""

    step_clicked = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._col = QVBoxLayout(self)
        self._col.setContentsMargins(theme.SPACE_2, 0, theme.SPACE_2, 0)
        self._col.setSpacing(0)
        self._rows: dict = {}

    def set_steps(self, items) -> None:
        """``items``: iterable of objects with ``step``, ``title``, ``description``."""
        for row in self._rows.values():
            self._col.removeWidget(row)
            row.deleteLater()
        self._rows = {}
        items = list(items)
        for i, item in enumerate(items, start=1):
            row = _StepRow(item.step, i, item.title, item.description,
                           first=i == 1, last=i == len(items), parent=self)
            row.clicked.connect(self.step_clicked)
            self._rows[item.step] = row
            self._col.addWidget(row)

    def set_state(self, step, state: str) -> None:
        row = self._rows.get(step)
        if row is not None:
            row.set_state(state)
        previous_done = False
        for current in self._rows.values():
            current.set_prev_done(previous_done)
            previous_done = current.state == "completed"

    def rows(self) -> dict:
        return dict(self._rows)


class _BulbIcon(QWidget):
    """Light-bulb glyph on a soft green disc for the tips card."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(30, 30)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(theme.WB_GREEN_BORDER))
        p.drawEllipse(QRectF(0, 0, 30, 30))
        p.setPen(QPen(QColor(theme.WB_GREEN_DARK), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(9.5, 6, 11, 11))
        p.drawLine(QPointF(12, 20.5), QPointF(18, 20.5))
        p.drawLine(QPointF(13, 23), QPointF(17, 23))


class WorkflowTipsCard(Card):
    """Workflow Tips card for the bottom of the sidebar: soft green, bulb icon."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("success", tinted=True, parent=parent)
        row = QHBoxLayout()
        row.setSpacing(theme.SPACE_3)
        row.addWidget(_BulbIcon(self), 0, Qt.AlignmentFlag.AlignTop)
        col = QVBoxLayout()
        col.setSpacing(2)
        col.addWidget(label("Workflow Tips", "wf_card_title", theme.WB_NAVY, parent=self))
        self.text_label = label("", "helper", theme.WB_TEXT_SECONDARY, wrap=True, parent=self)
        col.addWidget(self.text_label)
        row.addLayout(col, 1)
        self.body.addLayout(row)
        self.setVisible(False)

    def set_tip(self, text: str) -> None:
        self.text_label.setText(text)
        self.setVisible(bool(text))


class WorkflowSidebar(QWidget):
    """Module identity + vertical workflow steps + tips, bound to the manager.

    Painted as one white rounded card with a faint corner tint (no images)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("wfSidebar")
        self.setStyleSheet("QWidget#wfSidebar { background: transparent; }")
        col = QVBoxLayout(self)
        col.setContentsMargins(theme.SPACE_2, theme.SPACE_2, theme.SPACE_2, theme.SPACE_3)
        col.setSpacing(theme.SPACE_2)
        self.identity = ModuleIdentityPanel(self)
        self.nav = WorkflowStepNav(self)
        self.tips = WorkflowTipsCard(self)
        col.addWidget(self.identity)
        # Steps scroll when the panel is short (small window / high DPI) so
        # rows keep their height and the tips card stays visible.
        scroll = QScrollArea(self)
        scroll.setObjectName("wfSidebarScroll")
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # No scrollbar track eating row width; the wheel / touch still scrolls.
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea#wfSidebarScroll { background: transparent; border: 0; }")
        scroll.viewport().setAutoFillBackground(False)
        self.nav.setObjectName("wfStepNav")
        self.nav.setStyleSheet("QWidget#wfStepNav { background: transparent; }")
        scroll.setWidget(self.nav)
        col.addWidget(scroll, 1)
        col.addWidget(self.tips)
        self._manager = None
        self._items: dict = {}
        self.nav.step_clicked.connect(self._on_step_clicked)

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        p.fillPath(path, QColor(theme.WB_SURFACE))
        p.setClipPath(path)
        warm = QRadialGradient(rect.right() - 6, rect.top() + 6, 150)
        warm.setColorAt(0, QColor(232, 52, 28, 38))
        warm.setColorAt(1, QColor(232, 52, 28, 0))
        p.fillRect(rect, warm)
        leaf = QRadialGradient(rect.left() - 8, rect.bottom() - 70, 200)
        leaf.setColorAt(0, QColor(109, 174, 31, 46))
        leaf.setColorAt(1, QColor(109, 174, 31, 0))
        p.fillRect(rect, leaf)
        p.setClipping(False)
        p.setPen(QPen(QColor(theme.WB_BORDER), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)

    def bind_manager(self, manager) -> None:
        self._manager = manager
        manager.state_changed.connect(self.render)
        manager.step_changed.connect(lambda *_: self.render())

    def set_module(self, title: str, description: str, items) -> None:
        items = list(items)
        self._items = {item.step: item for item in items}
        self.identity.set_module(title, description)
        self.nav.set_steps(items)
        self.render()

    def _on_step_clicked(self, step) -> None:
        # Navigation and readiness rules stay entirely in the manager.
        if self._manager is not None:
            self._manager.jump_to(step)

    def render(self) -> None:
        if self._manager is None or not self._items:
            return
        current = self._manager.current_step()
        for step in self._items:
            state = _STATE_NAME[self._manager.step_state(step)]
            if step == current and state != "invalid":
                state = "current"  # the open step is always the highlighted one
            self.nav.set_state(step, state)
        item = self._items.get(current)
        self.tips.set_tip(item.description if item is not None else "")


# --------------------------------------------------------------------------
# Bottom detail tabs
# --------------------------------------------------------------------------
class DetailTabs(QTabWidget):
    """Flat tab strip with a green underline on the active tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("wfDetailTabs")
        self.setDocumentMode(True)
        self.setStyleSheet(
            f"QTabWidget#wfDetailTabs::pane {{ border: none; border-top: 1px solid {theme.WB_BORDER}; "
            f"background: {theme.WB_SURFACE}; top: -1px; }} "
            f"QTabBar::tab {{ background: transparent; color: {theme.WB_TEXT_SECONDARY}; padding: 7px 16px; "
            f"border: none; border-bottom: 2px solid transparent; font-weight: 600; font-size: 13px; }} "
            f"QTabBar::tab:selected {{ color: {theme.WB_GREEN_DARK}; border-bottom: 2px solid {theme.WB_GREEN}; }} "
            f"QTabBar::tab:hover:!selected {{ color: {theme.WB_NAVY}; }}"
        )
