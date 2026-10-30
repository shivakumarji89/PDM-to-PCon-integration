"""Front module selector for MK Product Workbench.

The page follows the approved reference design: a header with resource status,
six module launchers orbiting a central illustration (dashed ring, gears and a
seated engineer), and a status strip. The orbit is drawn in a fixed design
space and scaled uniformly, so the launchers keep their relative positions at
any window size.
"""
from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPolygonF,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QAbstractButton, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget,
)

from core.modules import WorkbenchModule, module_title

_GREEN = "#6DAE1F"
_GREEN_LIGHT = "#8CC63F"
_RED = "#E8341C"
_RED_LIGHT = "#F0553A"
_INK = "#1B2433"
_MUTED = "#5E6B7D"
_FONT_FAMILY = "Segoe UI"

# (module, number, icon, accent, description) - positions follow the reference.
_PRIMARY_MODULES = (
    (WorkbenchModule.DEVELOPMENT, "01", "code", _GREEN, "CAD & Data Workflows\nPDM – pCon Integration"),
    (WorkbenchModule.MAINTENANCE, "02", "database", _RED, "Article Update,\nPricing and Relations"),
    (WorkbenchModule.METATYPE, "03", "layers", _GREEN, "Series, Articles and\nMeta Properties"),
    (WorkbenchModule.OAP, "04", "nodes", _RED, "Options, Conditions\nand Parametric Approach"),
    (WorkbenchModule.QA_VALIDATION, "05", "check", _GREEN, "OBX Validation\nData Quality Checks"),
    (WorkbenchModule.BULK_UPDATE, "06", "cube", _RED, "Mass Updates and\nData Operations"),
)

# Design space of the orbit stage (reference image coordinates, y offset 85).
_DESIGN_W, _DESIGN_H, _DESIGN_Y0 = 1536.0, 790.0, 85.0
_TILE_RECTS = {
    WorkbenchModule.DEVELOPMENT: (166, 457, 316, 223),
    WorkbenchModule.MAINTENANCE: (217, 183, 301, 220),
    WorkbenchModule.METATYPE: (626, 106, 285, 196),
    WorkbenchModule.OAP: (1019, 183, 301, 220),
    WorkbenchModule.QA_VALIDATION: (1055, 457, 316, 223),
    WorkbenchModule.BULK_UPDATE: (619, 671, 298, 186),
}
_RING_CENTER = (768.0, 470.0)
_RING_RADIUS = 268.0
_RING_DOTS = (  # (x, y, colour, radius) on/near the ring
    (560, 292, _RED, 8), (976, 292, _RED, 8), (505, 473, _RED, 8),
    (1030, 473, _RED, 8), (546, 582, _GREEN, 7), (989, 582, _GREEN, 7),
    (538, 283, "#D9822B", 4),
)


def _font(px: float, weight: QFont.Weight = QFont.Weight.Normal) -> QFont:
    font = QFont(_FONT_FAMILY)
    font.setPixelSize(max(9, int(round(px))))
    font.setWeight(weight)
    return font


def _gear_path(cx: float, cy: float, radius: float, teeth: int = 8) -> QPainterPath:
    outer, inner = radius, radius * 0.80
    points = QPolygonF()
    step = 2 * math.pi / teeth
    for i in range(teeth):
        a = i * step
        for frac, r in ((0.0, inner), (0.18, outer), (0.50, outer), (0.68, inner)):
            ang = a + frac * step
            points.append(QPointF(cx + r * math.cos(ang), cy + r * math.sin(ang)))
    path = QPainterPath()
    path.addPolygon(points)
    path.closeSubpath()
    hole = QPainterPath()
    hole.addEllipse(QPointF(cx, cy), radius * 0.38, radius * 0.38)
    return path.subtracted(hole)


def draw_icon(p: QPainter, kind: str, rect: QRectF, color: QColor | str) -> None:
    """Draw a designed line/solid icon fitted into ``rect`` (square-ish)."""
    color = QColor(color)
    side = min(rect.width(), rect.height())
    r = QRectF(rect.center().x() - side / 2, rect.center().y() - side / 2, side, side)
    x, y, w = r.x(), r.y(), r.width()
    lw = max(1.4, w * 0.11)
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(color, lw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    if kind == "code":
        p.drawPolyline(QPolygonF([QPointF(x + .30 * w, y + .20 * w), QPointF(x + .02 * w, y + .50 * w), QPointF(x + .30 * w, y + .80 * w)]))
        p.drawPolyline(QPolygonF([QPointF(x + .70 * w, y + .20 * w), QPointF(x + .98 * w, y + .50 * w), QPointF(x + .70 * w, y + .80 * w)]))
        p.drawLine(QPointF(x + .57 * w, y + .12 * w), QPointF(x + .43 * w, y + .88 * w))
    elif kind == "database":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        ew, eh = .76 * w, .24 * w
        left = x + (w - ew) / 2
        body = QPainterPath()
        body.moveTo(left, y + .17 * w)
        body.lineTo(left, y + .83 * w)
        body.arcTo(QRectF(left, y + .83 * w - eh / 2, ew, eh), 180, 180)
        body.lineTo(left + ew, y + .17 * w)
        body.arcTo(QRectF(left, y + .17 * w - eh / 2, ew, eh), 0, -180)
        body.closeSubpath()
        body.addEllipse(QRectF(left, y + .05 * w, ew, eh))
        p.drawPath(body)
        p.setPen(QPen(QColor("#FFFFFF"), lw * .55, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for frac in (.40, .62):
            p.drawArc(QRectF(left, y + frac * w - eh / 2 + .02 * w, ew, eh), 180 * 16, 180 * 16)
    elif kind == "layers":
        def diamond(cy_frac: float) -> QPolygonF:
            return QPolygonF([QPointF(x + .5 * w, y + (cy_frac - .20) * w), QPointF(x + .98 * w, y + cy_frac * w),
                              QPointF(x + .5 * w, y + (cy_frac + .20) * w), QPointF(x + .02 * w, y + cy_frac * w)])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPolygon(diamond(.28))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(color, lw * 1.1, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        for frac in (.52, .76):
            p.drawPolyline(QPolygonF([QPointF(x + .06 * w, y + frac * w), QPointF(x + .5 * w, y + (frac + .20) * w),
                                      QPointF(x + .94 * w, y + frac * w)]))
    elif kind == "nodes":
        nodes = (QPointF(x + .50 * w, y + .17 * w), QPointF(x + .13 * w, y + .80 * w), QPointF(x + .87 * w, y + .80 * w))
        p.setPen(QPen(color, lw * .9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawPolygon(QPolygonF(list(nodes)))
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(QPen(color, lw * 1.15))
        for node in nodes:
            p.drawEllipse(node, .115 * w, .115 * w)
    elif kind == "check":
        p.setPen(QPen(color, lw, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawEllipse(r.adjusted(lw / 2, lw / 2, -lw / 2, -lw / 2))
        p.setPen(QPen(color, lw * 1.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPolyline(QPolygonF([QPointF(x + .28 * w, y + .52 * w), QPointF(x + .44 * w, y + .67 * w), QPointF(x + .73 * w, y + .35 * w)]))
    elif kind == "cube":
        top, tr, br, bot, bl, tl, mid = (QPointF(x + .5 * w, y + .06 * w), QPointF(x + .92 * w, y + .28 * w),
                                         QPointF(x + .92 * w, y + .72 * w), QPointF(x + .5 * w, y + .94 * w),
                                         QPointF(x + .08 * w, y + .72 * w), QPointF(x + .08 * w, y + .28 * w),
                                         QPointF(x + .5 * w, y + .50 * w))
        p.drawPolygon(QPolygonF([top, tr, br, bot, bl, tl]))
        p.drawPolyline(QPolygonF([tl, mid, tr]))
        p.drawLine(mid, bot)
    elif kind == "gear":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawPath(_gear_path(x + w / 2, y + w / 2, w * .5))
    elif kind == "folder":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        path = QPainterPath()
        path.addRoundedRect(QRectF(x + .04 * w, y + .22 * w, .92 * w, .66 * w), .08 * w, .08 * w)
        tab = QPainterPath()
        tab.addRoundedRect(QRectF(x + .04 * w, y + .10 * w, .40 * w, .22 * w), .06 * w, .06 * w)
        p.drawPath(path.united(tab))
    elif kind == "doc":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(QRectF(x + .16 * w, y + .04 * w, .68 * w, .92 * w), .10 * w, .10 * w)
        p.setPen(QPen(QColor("#FFFFFF"), lw * .6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        for frac in (.32, .50, .68):
            p.drawLine(QPointF(x + .30 * w, y + frac * w), QPointF(x + .70 * w, y + frac * w))
    p.restore()


class _IconWidget(QWidget):
    def __init__(self, kind: str, color: str, size: int = 34, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._kind, self._color = kind, color
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        draw_icon(p, self._kind, QRectF(self.rect()).adjusted(3, 3, -3, -3), self._color)


class _ElidedLabel(QLabel):
    """Label that shrinks (eliding with "…") instead of widening its layout."""

    _MIN_WIDTH = 48

    def minimumSizeHint(self) -> QSize:  # noqa: N802 - Qt override
        hint = super().sizeHint()
        return QSize(min(self._MIN_WIDTH, hint.width()), hint.height())

    def paintEvent(self, _event) -> None:  # noqa: N802 - Qt override
        p = QPainter(self)
        p.setFont(self.font())
        p.setPen(self.palette().color(self.foregroundRole()))
        text = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight, self.width())
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)


class _StatusItem(QWidget):
    """Icon + status dot + label + value, used in the header and the footer."""

    _GOOD = {"configured", "available", "loaded", "ready"}

    def __init__(self, icon: str, label: str, value: str, *, icon_color: str = "#4A5565", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = "ready"
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(_IconWidget(icon, icon_color, 34))
        self._dot = QLabel()
        self._dot.setFixedSize(10, 10)
        layout.addWidget(self._dot, 0, Qt.AlignmentFlag.AlignVCenter)
        text = QVBoxLayout()
        text.setSpacing(0)
        text.setContentsMargins(0, 0, 0, 0)
        self._first = QLabel()
        self._second = _ElidedLabel()
        text.addWidget(self._first)
        text.addWidget(self._second)
        layout.addLayout(text)
        self._label = label
        self.set_value(value)

    def set_value(self, value: str, detail: str = "") -> None:
        good = value.strip().lower() in self._GOOD
        self._dot.setStyleSheet(
            f"background:{'#27A032' if good else '#B7BFCA'}; border-radius:5px;"
        )
        self._first.setText(self._label)
        self._second.setText(detail or value)
        self._first.setStyleSheet(f"color:{_INK}; font-size:12px; font-weight:700; background:transparent;")
        self._second.setStyleSheet(f"color:{_MUTED}; font-size:12px; font-weight:400; background:transparent;")
        self.setToolTip(detail or value)


class _ModuleTile(QAbstractButton):
    """Clickable module launcher drawn like the reference cards."""

    _MARGIN = 10  # room for the soft shadow around the card

    def __init__(self, module: WorkbenchModule, number: str, icon: str, accent: str,
                 description: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.module = module
        self._number, self._icon, self._accent, self._description = number, icon, QColor(accent), description
        self._title = module_title(module)
        self._scale = 1.0
        self._hover = False
        self._keyboard_focus = False
        self.setObjectName("moduleOrbitButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setAccessibleName(self._title)
        self.setToolTip(f"{self._title} – {description.replace(chr(10), ' ')}")

    def set_scale(self, scale: float) -> None:
        self._scale = scale
        self.update()

    def _card(self) -> QRectF:
        m = self._MARGIN * self._scale
        return QRectF(m, m, self.width() - 2 * m, self.height() - 2 * m)

    def hitButton(self, pos) -> bool:  # noqa: N802 - Qt override
        return self._card().contains(QPointF(pos))

    def enterEvent(self, event) -> None:  # noqa: N802
        self._hover = True
        self.update()
        super().enterEvent(event)

    def focusInEvent(self, event) -> None:  # noqa: N802
        self._keyboard_focus = event.reason() in (
            Qt.FocusReason.TabFocusReason, Qt.FocusReason.BacktabFocusReason)
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:  # noqa: N802
        self._keyboard_focus = False
        super().focusOutEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        card, s = self._card(), self._scale
        radius = 22 * s
        border = max(2.0, 3.6 * s)
        light = QColor(_GREEN_LIGHT if self._accent == QColor(_GREEN) else _RED_LIGHT)
        lift = -3 * s if self._hover else 0

        # soft shadow
        for i in range(7, 0, -1):
            grow = i * 1.6 * s
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(30, 40, 50, 7 if not self._hover else 9))
            p.drawRoundedRect(card.adjusted(-grow, -grow + 6 * s, grow, grow + 6 * s), radius + grow, radius + grow)
        card = card.translated(0, lift)

        clip = QPainterPath()
        clip.addRoundedRect(card, radius, radius)
        p.save()
        p.setClipPath(clip)
        body = QColor("#FFFFFF")
        if self._hover:
            body = QColor("#F7FBEF") if self._accent == QColor(_GREEN) else QColor("#FFF5F3")
        if self.isDown():
            body = body.darker(103)
        p.fillRect(card, body)
        band_h = card.height() * 0.16
        band = QRectF(card.x(), card.y(), card.width(), band_h)
        grad = QLinearGradient(band.topLeft(), band.bottomLeft())
        grad.setColorAt(0, light)
        grad.setColorAt(1, self._accent)
        p.fillRect(band, grad)
        p.restore()

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(self._accent, border))
        p.drawRoundedRect(card.adjusted(border / 2, border / 2, -border / 2, -border / 2), radius, radius)

        p.setPen(QColor("#FFFFFF"))
        p.setFont(_font(card.height() * 0.118, QFont.Weight.Bold))
        p.drawText(band, Qt.AlignmentFlag.AlignCenter, self._number)

        icon_h = card.height() * 0.30
        icon_rect = QRectF(card.center().x() - icon_h / 2, card.y() + card.height() * 0.38 - icon_h / 2, icon_h, icon_h)
        draw_icon(p, self._icon, icon_rect, self._accent)

        p.setPen(QColor(_INK))
        p.setFont(_font(card.height() * 0.095, QFont.Weight.Bold))
        title_rect = QRectF(card.x(), card.y() + card.height() * 0.555, card.width(), card.height() * 0.15)
        p.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, self._title)

        p.setPen(QColor(_MUTED))
        p.setFont(_font(card.height() * 0.067))
        desc_rect = QRectF(card.x(), card.y() + card.height() * 0.71, card.width(), card.height() * 0.24)
        p.drawText(desc_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, self._description)

        # chevron button
        cr = card.height() * 0.088
        centre = QPointF(card.x() + card.width() * 0.89, card.y() + card.height() * 0.73)
        pale = QColor(self._accent)
        pale.setAlpha(46 if not self._hover else 80)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(pale)
        p.drawEllipse(centre, cr, cr)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(self._accent, max(1.6, cr * 0.18), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        d = cr * 0.34
        p.drawPolyline(QPolygonF([QPointF(centre.x() - d * .6, centre.y() - d), QPointF(centre.x() + d * .6, centre.y()),
                                  QPointF(centre.x() - d * .6, centre.y() + d)]))
        if self._keyboard_focus:
            p.setPen(QPen(QColor(_INK), 1.2, Qt.PenStyle.DotLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(card.adjusted(-3, -3, 3, 3), radius + 3, radius + 3)


class _OrbitStage(QWidget):
    """Central ring + illustration with the six module tiles positioned around it."""

    module_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("moduleOrbitStage")
        self.setMinimumSize(760, 400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tiles: list[_ModuleTile] = []
        for module, number, icon, accent, description in _PRIMARY_MODULES:
            tile = _ModuleTile(module, number, icon, accent, description, self)
            tile.clicked.connect(lambda checked=False, selected=module: self.module_selected.emit(selected))
            self.tiles.append(tile)

    def _scale(self) -> tuple[float, float, float]:
        s = min(self.width() / _DESIGN_W, self.height() / _DESIGN_H)
        ox = (self.width() - _DESIGN_W * s) / 2
        oy = (self.height() - _DESIGN_H * s) / 2 - _DESIGN_Y0 * s
        return s, ox, oy

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        s, ox, oy = self._scale()
        for tile in self.tiles:
            x, y, w, h = _TILE_RECTS[tile.module]
            m = _ModuleTile._MARGIN * s
            tile.setGeometry(int(ox + x * s - m), int(oy + y * s - m), int(w * s + 2 * m), int(h * s + 2 * m))
            tile.set_scale(s)

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s, ox, oy = self._scale()
        p.translate(ox, oy)
        p.scale(s, s)
        cx, cy = _RING_CENTER

        halo = QRadialGradient(QPointF(cx, cy), _RING_RADIUS)
        halo.setColorAt(0.0, QColor(255, 255, 255, 235))
        halo.setColorAt(0.72, QColor(246, 249, 246, 200))
        halo.setColorAt(1.0, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(halo)
        p.drawEllipse(QPointF(cx, cy), _RING_RADIUS, _RING_RADIUS)

        ring = QPen(QColor("#9BC77A"), 1.6, Qt.PenStyle.CustomDashLine)
        ring.setDashPattern([5, 5])
        p.setPen(ring)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), _RING_RADIUS, _RING_RADIUS)
        p.setPen(Qt.PenStyle.NoPen)
        for x, y, colour, r in _RING_DOTS:
            p.setBrush(QColor(colour))
            p.drawEllipse(QPointF(x, y), r, r)

        self._paint_illustration(p)

    @staticmethod
    def _paint_illustration(p: QPainter) -> None:
        p.setPen(Qt.PenStyle.NoPen)
        # gears behind the figure
        for gx, gy, gr, col in ((632, 412, 64, "#E1E5EA"), (940, 390, 34, "#D5DAE0"),
                                 (943, 521, 44, "#D5DAE0")):
            p.setBrush(QColor(col))
            p.drawPath(_gear_path(gx, gy, gr))
        green = QLinearGradient(740, 340, 880, 480)
        green.setColorAt(0, QColor("#9ACD4C"))
        green.setColorAt(1, QColor("#6DAE1F"))
        p.setBrush(green)
        p.drawPath(_gear_path(810, 410, 70))

        # plant
        p.setBrush(QColor("#E6E9ED"))
        pot = QPainterPath()
        pot.addRoundedRect(QRectF(602, 585, 56, 52), 6, 6)
        p.drawPath(pot)
        for angle, length, col in ((-28, 150, "#79B83A"), (-4, 175, "#5FA52A"), (22, 135, "#8CC63F"), (-50, 100, "#7DBB3E")):
            leaf = QPainterPath()
            leaf.moveTo(0, 0)
            leaf.cubicTo(-28, -length * .35, -22, -length * .8, 0, -length)
            leaf.cubicTo(24, -length * .8, 28, -length * .35, 0, 0)
            p.save()
            p.translate(630, 590)
            p.rotate(angle)
            p.setBrush(QColor(col))
            p.drawPath(leaf)
            p.restore()

        # legs and shoes
        p.setBrush(QColor("#3B4048"))
        legs = QPainterPath()
        legs.addRoundedRect(QRectF(652, 596, 238, 48), 24, 24)
        p.drawPath(legs)
        for sx in (692, 846):
            p.setBrush(QColor("#7CC242"))
            p.setPen(QPen(QColor("#FFFFFF"), 4))
            p.drawEllipse(QPointF(sx, 650), 36, 14)
            p.setPen(Qt.PenStyle.NoPen)

        # torso
        p.setBrush(QColor("#FFFFFF"))
        p.setPen(QPen(QColor("#E3E7EC"), 1.5))
        torso = QPainterPath()
        torso.moveTo(704, 482)
        torso.cubicTo(740, 462, 800, 470, 836, 492)
        torso.lineTo(844, 610)
        torso.lineTo(700, 610)
        torso.closeSubpath()
        p.drawPath(torso)
        p.setPen(Qt.PenStyle.NoPen)

        # raised arm pointing at the gear
        arm = QPen(QColor("#F2B48A"), 22, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        p.setPen(arm)
        p.drawLine(QPointF(842, 512), QPointF(918, 432))
        p.setPen(QPen(QColor("#FFFFFF"), 30, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(838, 508), QPointF(858, 488))
        p.setPen(QPen(QColor("#F2B48A"), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(918, 432), QPointF(934, 418))
        p.setPen(Qt.PenStyle.NoPen)

        # head and hair
        p.setBrush(QColor("#F2B48A"))
        p.drawEllipse(QPointF(748, 452), 34, 38)
        p.setBrush(QColor("#1C2430"))
        hair = QPainterPath()
        hair.moveTo(712, 452)
        hair.cubicTo(700, 410, 740, 396, 770, 410)
        hair.cubicTo(790, 420, 786, 438, 780, 446)
        hair.cubicTo(760, 436, 730, 436, 712, 452)
        p.drawPath(hair)

        # laptop
        p.setBrush(QColor("#2D3238"))
        screen = QPolygonF([QPointF(722, 548), QPointF(866, 544), QPointF(852, 624), QPointF(712, 628)])
        p.drawPolygon(screen)
        p.setBrush(QColor("#4A515A"))
        p.drawPolygon(QPolygonF([QPointF(706, 630), QPointF(852, 626), QPointF(862, 640), QPointF(700, 644)]))
        p.setBrush(QColor("#8A929C"))
        p.drawEllipse(QPointF(790, 586), 4, 4)
        # forearm resting on laptop
        p.setPen(QPen(QColor("#F2B48A"), 14, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawLine(QPointF(726, 540), QPointF(760, 556))


class ModuleHomePage(QWidget):
    """Landing screen with workspace actions arranged around the central visual."""

    module_selected = Signal(object)

    def __init__(self, context=None, parent: QWidget | None = None) -> None:
        # Backward compatibility with the former ModuleHomePage(parent) call.
        if isinstance(context, QWidget) and parent is None:
            parent, context = context, None
        super().__init__(parent)
        self._context = context
        self.setObjectName("moduleHomePage")

        root = QVBoxLayout(self)
        root.setContentsMargins(52, 30, 52, 18)
        root.setSpacing(6)

        # --- header -------------------------------------------------------
        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title_block.setSpacing(0)
        title = QLabel("MK Product Workbench")
        title.setStyleSheet(f"color:{_INK}; font-size:36px; font-weight:800; background:transparent;")
        subtitle = QLabel("PDM · pCon Integration Suite")
        subtitle.setStyleSheet(f"color:{_MUTED}; font-size:18px; font-weight:500; background:transparent;")
        accent = QLabel()
        accent.setFixedSize(80, 5)
        accent.setStyleSheet(f"background:{_GREEN}; border-radius:2px;")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        title_block.addSpacing(6)
        title_block.addWidget(accent)
        header.addLayout(title_block)
        header.addStretch(1)

        self._header_pdm = _StatusItem("database", "PDM", "Not checked")
        self._header_repository = _StatusItem("database", "Repository", "Not checked")
        self._header_app = _StatusItem("gear", "Application", "Ready")
        for index, item in enumerate((self._header_pdm, self._header_repository, self._header_app)):
            if index:
                sep = QLabel()
                sep.setFixedSize(1, 40)
                sep.setStyleSheet("background:#DCE2E8;")
                header.addSpacing(14)
                header.addWidget(sep)
                header.addSpacing(14)
            header.addWidget(item, 0, Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(header)

        # --- orbit ----------------------------------------------------------
        self._stage = _OrbitStage(self)
        self._stage.module_selected.connect(self.module_selected)
        self._module_buttons: list[QAbstractButton] = self._stage.tiles
        root.addWidget(self._stage, 1)

        # --- status strip ---------------------------------------------------
        strip = _StatusStrip()
        self._repository_status = _StatusItem("folder", "Active Repository", "Not checked")
        self._pdm_status = _StatusItem("database", "PDM Database", "Not checked")
        self._mdb_status = _StatusItem("doc", "MDB Snapshot", "Not loaded")
        self._application_status = _StatusItem("gear", "Application", "Ready")
        strip.set_items((self._repository_status, self._pdm_status, self._mdb_status, self._application_status))
        root.addWidget(strip)

        # --- additional tools ----------------------------------------------
        utility_row = QHBoxLayout()
        note = QLabel("Additional tools")
        note.setStyleSheet(f"color:{_MUTED}; font-size:11px; font-weight:700; background:transparent;")
        utility_row.addWidget(note)
        syte_line = QPushButton("SyteLine Export  →")
        syte_line.setObjectName("syteLineExportButton")
        syte_line.setCursor(Qt.CursorShape.PointingHandCursor)
        syte_line.setFlat(True)
        syte_line.setStyleSheet(
            f"QPushButton {{ color:{_MUTED}; background:transparent; border:0; padding:3px 8px; "
            "font-size:11px; font-weight:700; } QPushButton:hover { color:#4D941D; }"
        )
        syte_line.clicked.connect(lambda: self.module_selected.emit(WorkbenchModule.SYTELINE_EXPORT))
        utility_row.addWidget(syte_line)
        utility_row.addStretch(1)
        root.addLayout(utility_row)
        self._syteline_button = syte_line

        self.refresh_status()

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        base = QLinearGradient(0, 0, 0, h)
        base.setColorAt(0, QColor("#FFFFFF"))
        base.setColorAt(1, QColor("#F4F8F1"))
        p.fillRect(self.rect(), base)
        p.setPen(Qt.PenStyle.NoPen)

        def wave(points, colour_a: str, colour_b: str, alpha: int) -> None:
            path = QPainterPath()
            path.moveTo(*points[0])
            for c1, c2, end in points[1:]:
                path.cubicTo(QPointF(*c1), QPointF(*c2), QPointF(*end))
            path.closeSubpath()
            g = QLinearGradient(0, 0, w, 0)
            a, b = QColor(colour_a), QColor(colour_b)
            a.setAlpha(alpha)
            b.setAlpha(0)
            g.setColorAt(0, a)
            g.setColorAt(1, b)
            p.setBrush(g)
            p.drawPath(path)

        # soft red and green washes bleeding in from the page edges
        def wash(cx: float, cy: float, rx: float, ry: float, colour: str, alpha: int) -> None:
            p.save()
            p.translate(cx, cy)
            p.scale(rx, ry)
            g = QRadialGradient(QPointF(0, 0), 1.0)
            c0, c1 = QColor(colour), QColor(colour)
            c0.setAlpha(alpha)
            c1.setAlpha(0)
            g.setColorAt(0, c0)
            g.setColorAt(1, c1)
            p.setBrush(g)
            p.drawEllipse(QPointF(0, 0), 1.0, 1.0)
            p.restore()

        wash(w * .02, h * .80, w * .20, h * .26, "#F26B55", 70)
        wash(w * .08, h * .93, w * .30, h * .22, "#9BCB55", 80)
        wash(w * .94, h * .90, w * .34, h * .30, "#9BCB55", 80)
        wash(w * .30, h * .30, w * .28, h * .22, "#BFE08C", 28)

    def refresh_status(self) -> None:
        """Show configured/loaded state without claiming an untested DB connection."""
        context = self._context
        if context is None:
            return
        config = getattr(context, "config", None)
        if config is not None:
            preset = config.active_pdm_preset() or "Custom configuration"
            self._pdm_status.set_value("Configured", f"{config.pdm_server}/{config.pdm_database}")
            self._pdm_status.setToolTip(f"{preset} · {config.pdm_server}/{config.pdm_database}")
            self._header_pdm.set_value("Configured")
            roots = getattr(config, "repository_browser_roots", {}) or {}
            available = [name for name, path in roots.items() if Path(path).is_dir()]
            self._repository_status.set_value(
                "Available" if available else "Path not found",
                ", ".join(available) if available else "Configured repository folders not found",
            )
            self._header_repository.set_value("Available" if available else "Path not found")
        imported = getattr(context, "mdb_import_snapshot", None)
        self._mdb_status.set_value(
            "Loaded" if imported is not None else "Not loaded",
            "Loaded" if imported is not None else "Not loaded",
        )


class _StatusStrip(QWidget):
    """White rounded strip holding the four footer status items."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(34, 12, 34, 12)
        self._layout.setSpacing(0)
        self.setFixedHeight(76)

    def set_items(self, items) -> None:
        for index, item in enumerate(items):
            if index:
                sep = QLabel()
                sep.setFixedSize(1, 42)
                sep.setStyleSheet("background:#DCE2E8;")
                self._layout.addStretch(1)
                self._layout.addWidget(sep)
                self._layout.addStretch(1)
            self._layout.addWidget(item)

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(1, 1, -1, -3)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(30, 40, 50, 14))
        p.drawRoundedRect(rect.translated(0, 2), 16, 16)
        p.setPen(QPen(QColor("#E6EBF0"), 1))
        p.setBrush(QColor("#FFFFFF"))
        p.drawRoundedRect(rect, 16, 16)
