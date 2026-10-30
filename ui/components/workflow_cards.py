"""Reusable card types for internal workflow pages.

All cards share one frame (padding, 1px border, 10px radius, white surface) and
differ only in content. Tone is meaningful, not decorative: ``success`` (green)
= ready/valid/complete, ``danger`` (red) = failed/blocked/attention,
``warning`` (amber) = pending, ``neutral`` = informational/inactive/unknown.

Cards are presentation-only: they hold labels and widgets that the owning page
fills in; they never read services, snapshots or the workflow.
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui import theme
from ui.components.workflow_styles import card_qss, font_qss, label, style_progress_bar

_TONE_GLYPH = {"success": "✓", "danger": "!", "warning": "●", "neutral": "i"}


class IconBadge(QLabel):
    """Round tone-coloured badge carrying a single glyph (front-page style)."""

    def __init__(self, glyph: str = "", tone: str = "neutral", size: int = 40,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._glyph = glyph
        self.set_tone(tone)

    def set_tone(self, tone: str, glyph: str | None = None) -> None:
        accent = theme.tone_colors(tone)[0]
        if glyph is not None:
            self._glyph = glyph
        self.setText(self._glyph or _TONE_GLYPH.get(tone, "i"))
        self.setStyleSheet(
            f"background: {accent}; color: #FFFFFF; border-radius: {self._size // 2}px; "
            f"font-size: {max(12, int(self._size * 0.45))}px; font-weight: 700;"
        )


class Card(QFrame):
    """Base card: shared padding, border, radius, background and tone."""

    clicked = Signal()

    def __init__(self, tone: str = "neutral", *, tinted: bool = False,
                 clickable: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("wfCard")
        self._tone = tone
        self._tinted = tinted
        self._clickable = clickable
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        if clickable:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._body = QVBoxLayout(self)
        self._body.setContentsMargins(theme.SPACE_4, theme.SPACE_3, theme.SPACE_4, theme.SPACE_3)
        self._body.setSpacing(theme.SPACE_2)
        self._restyle()

    @property
    def tone(self) -> str:
        return self._tone

    @property
    def body(self) -> QVBoxLayout:
        return self._body

    def set_tone(self, tone: str) -> None:
        if tone != self._tone:
            self._tone = tone
            self._restyle()

    def _restyle(self) -> None:
        self.setStyleSheet(card_qss(tone=self._tone, tinted=self._tinted, hover=self._clickable))

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self._clickable and event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:  # noqa: N802 - Qt override
        if self._clickable and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit()
            return
        super().keyPressEvent(event)


class KpiCard(Card):
    """Summary/KPI card: badge, big value, label and an optional caption + meter."""

    def __init__(self, label_text: str = "", value: str = "-", tone: str = "neutral", *,
                 glyph: str | None = None, caption: str = "", compact_value: bool = False,
                 parent: QWidget | None = None) -> None:
        super().__init__(tone, tinted=tone != "neutral", parent=parent)
        self.setMinimumWidth(170)
        self.body.setContentsMargins(theme.SPACE_3, 6, theme.SPACE_3, 6)
        self.body.setSpacing(2)
        row = QHBoxLayout()
        row.setSpacing(theme.SPACE_2)
        self._badge = IconBadge(glyph or "", tone, 26, self)
        row.addWidget(self._badge, 0, Qt.AlignmentFlag.AlignVCenter)
        text = QVBoxLayout()
        text.setSpacing(0)
        # compact_value: long text values (e.g. a counts summary) use the card
        # title size and wrap instead of the big KPI number size.
        self.value_label = label(value, "wf_card_title" if compact_value else "wf_kpi_value",
                                 theme.WB_NAVY, wrap=compact_value,
                                 size=None if compact_value else 22, parent=self)
        if compact_value:
            # Reserve two lines so wrapped text is never clipped by the card.
            self.value_label.setMinimumHeight(self.value_label.fontMetrics().lineSpacing() * 2 + 2)
            self.value_label.setAlignment(Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft)
        self.label_label = label(label_text, "wf_kpi_label", theme.WB_TEXT_SECONDARY, parent=self)
        text.addWidget(self.value_label)
        text.addWidget(self.label_label)
        row.addLayout(text, 1)
        self.body.addLayout(row)
        self.caption_label = label(caption, "helper", theme.WB_TEXT_SECONDARY, wrap=True, parent=self)
        self.caption_label.setVisible(bool(caption))
        self.body.addWidget(self.caption_label)
        self._meter = QProgressBar(self)
        self._meter.setRange(0, 1000)
        self._meter.setVisible(False)
        self.body.addWidget(self._meter)
        self._glyph = glyph
        self._apply_tone()

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)

    def set_caption(self, text: str) -> None:
        self.caption_label.setText(text)
        self.caption_label.setVisible(bool(text))

    def set_meter(self, fraction: float | None) -> None:
        """Thin progress meter under the value (``None`` hides it)."""
        if fraction is None:
            self._meter.setVisible(False)
            return
        self._meter.setValue(int(max(0.0, min(1.0, fraction)) * 1000))
        self._meter.setVisible(True)

    def set_tone(self, tone: str, glyph: str | None = None) -> None:
        if glyph is not None:
            self._glyph = glyph
        self._tinted = tone != "neutral"
        super().set_tone(tone)
        self._restyle()
        self._apply_tone()

    def _apply_tone(self) -> None:
        self._badge.set_tone(self._tone, self._glyph)
        style_progress_bar(self._meter, self._tone if self._tone != "neutral" else "success", height=4)


class InfoCard(Card):
    """Information card: optional title and ``label : value`` rows."""

    def __init__(self, title: str = "", *, parent: QWidget | None = None) -> None:
        super().__init__("neutral", parent=parent)
        self.title_label = label(title, "wf_card_title", theme.WB_NAVY, parent=self)
        self.title_label.setVisible(bool(title))
        self.body.addWidget(self.title_label)
        self._grid = QGridLayout()
        self._grid.setHorizontalSpacing(theme.SPACE_4)
        self._grid.setVerticalSpacing(theme.SPACE_2)
        self._grid.setColumnStretch(1, 1)
        self.body.addLayout(self._grid)

    def add_row(self, name: str, value: str | QLabel = "-") -> QLabel:
        """Append a row and return its value label so the page can update it."""
        row = self._grid.rowCount()
        key = label(name, "helper", theme.WB_TEXT_SECONDARY, parent=self)
        key.setAlignment(Qt.AlignmentFlag.AlignTop)
        if isinstance(value, QLabel):
            val = value
            val.setParent(self)
            val.setStyleSheet(f"background: transparent; color: {theme.WB_NAVY}; {font_qss('normal')}")
        else:
            val = label(value, "normal", theme.WB_NAVY, wrap=True, parent=self)
        val.setWordWrap(True)
        val.setAlignment(Qt.AlignmentFlag.AlignTop)
        val.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._grid.addWidget(key, row, 0, Qt.AlignmentFlag.AlignTop)
        self._grid.addWidget(val, row, 1)
        return val


class StatusCard(Card):
    """Status card: tone badge, a short title and an explanatory message."""

    def __init__(self, title: str = "", message: str = "", tone: str = "neutral", *,
                 parent: QWidget | None = None) -> None:
        super().__init__(tone, tinted=True, parent=parent)
        row = QHBoxLayout()
        row.setSpacing(theme.SPACE_3)
        self._badge = IconBadge("", tone, 32, self)
        row.addWidget(self._badge, 0, Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(2)
        self.title_label = label(title, "wf_card_title", theme.WB_NAVY, parent=self)
        self.message_label = label(message, "normal", theme.WB_TEXT_SECONDARY, wrap=True, parent=self)
        self.title_label.setVisible(bool(title))
        text.addWidget(self.title_label)
        text.addWidget(self.message_label)
        row.addLayout(text, 1)
        self.body.addLayout(row)

    def set_status(self, tone: str, title: str | None = None, message: str | None = None) -> None:
        if title is not None:
            self.title_label.setText(title)
            self.title_label.setVisible(bool(title))
        if message is not None:
            self.message_label.setText(message)
        super().set_tone(tone)
        self._badge.set_tone(tone)


class MessageCard(StatusCard):
    """Warning / error banner. Hidden while it has nothing to say."""

    def __init__(self, tone: str = "warning", *, parent: QWidget | None = None) -> None:
        super().__init__("", "", tone, parent=parent)
        self.setVisible(False)

    def show_message(self, text: str, tone: str | None = None, title: str | None = None) -> None:
        self.set_status(tone or self.tone, title, text)
        self.setVisible(bool(text))


class ActionCard(Card):
    """Clickable card for a workflow action: glyph, title and description."""

    def __init__(self, title: str, description: str = "", glyph: str = "→", *,
                 parent: QWidget | None = None) -> None:
        super().__init__("success", clickable=True, parent=parent)
        row = QHBoxLayout()
        row.setSpacing(theme.SPACE_3)
        row.addWidget(IconBadge(glyph, "success", 36, self), 0, Qt.AlignmentFlag.AlignTop)
        text = QVBoxLayout()
        text.setSpacing(2)
        text.addWidget(label(title, "wf_card_title", theme.WB_NAVY, parent=self))
        text.addWidget(label(description, "helper", theme.WB_TEXT_SECONDARY, wrap=True, parent=self))
        row.addLayout(text, 1)
        self.body.addLayout(row)


class DataCard(Card):
    """Data overview card: a titled surface hosting a table/tree/form/editor."""

    def __init__(self, title: str = "", subtitle: str = "", *, parent: QWidget | None = None) -> None:
        super().__init__("neutral", parent=parent)
        head = QHBoxLayout()
        head.setSpacing(theme.SPACE_2)
        titles = QVBoxLayout()
        titles.setSpacing(0)
        self.title_label = label(title, "wf_card_title", theme.WB_NAVY, parent=self)
        self.subtitle_label = label(subtitle, "helper", theme.WB_TEXT_SECONDARY, parent=self)
        self.subtitle_label.setVisible(bool(subtitle))
        titles.addWidget(self.title_label)
        titles.addWidget(self.subtitle_label)
        head.addLayout(titles, 1)
        self._actions = QHBoxLayout()
        self._actions.setSpacing(theme.SPACE_2)
        head.addLayout(self._actions)
        self._head = head
        self.body.addLayout(head)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_subtitle(self, text: str) -> None:
        self.subtitle_label.setText(text)
        self.subtitle_label.setVisible(bool(text))

    def add_header_action(self, widget: QWidget) -> None:
        self._actions.addWidget(widget)

    def set_content(self, widget: QWidget, stretch: int = 1) -> None:
        self.body.addWidget(widget, stretch)


class ProgressStatusCard(Card):
    """Progress card: title, a themed bar (new or adopted) and a caption."""

    def __init__(self, title: str = "Progress", *, bar: QProgressBar | None = None,
                 tone: str = "success", parent: QWidget | None = None) -> None:
        super().__init__("neutral", parent=parent)
        self.title_label = label(title, "wf_card_title", theme.WB_NAVY, parent=self)
        self.body.addWidget(self.title_label)
        self.bar = bar if bar is not None else QProgressBar(self)
        self.bar.setParent(self)
        style_progress_bar(self.bar, tone)
        self.body.addWidget(self.bar)
        self.caption_label = label("", "helper", theme.WB_TEXT_SECONDARY, wrap=True, parent=self)
        self.caption_label.setVisible(False)
        self.body.addWidget(self.caption_label)

    def set_caption(self, text: str) -> None:
        self.caption_label.setText(text)
        self.caption_label.setVisible(bool(text))
