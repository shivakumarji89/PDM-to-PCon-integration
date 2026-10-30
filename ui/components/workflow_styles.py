"""Token-driven style helpers for internal workflow pages.

Every value comes from :mod:`ui.theme` (the ``WB_*`` workbench tokens), so cards,
buttons, tables and progress bars on every workflow page share one visual
language with the front page. Presentation only.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QLabel,
    QProgressBar,
    QTreeWidget,
    QWidget,
)

from ui import theme

BUTTON_ROLES = ("primary", "secondary", "danger", "ghost")


def card_qss(*, tone: str = "neutral", tinted: bool = False, hover: bool = False) -> str:
    accent, soft, border = theme.tone_colors(tone)
    # Neutral cards keep the standard hairline; tone only tints on request so a
    # page is not painted in colour without a reason.
    edge = border if (tinted or tone != "neutral") else theme.WB_BORDER
    fill = soft if tinted else theme.WB_SURFACE
    qss = (
        f"QFrame#wfCard {{ background: {fill}; border: 1px solid {edge}; "
        f"border-radius: {theme.RADIUS_LG}px; }}"
    )
    if hover:
        qss += (
            f" QFrame#wfCard:hover {{ border: 1px solid {accent}; "
            f"background: {soft if not tinted else fill}; }}"
        )
    return qss


def font_qss(role: str, size: int | None = None, weight: int | None = None) -> str:
    """Stylesheet font declaration for a typography role.

    The application stylesheet sets ``font-size`` on every ``QWidget``, which
    overrides ``setFont``; workflow typography must therefore be declared in a
    widget stylesheet to take effect.
    """
    role_size, role_weight = theme._ROLES.get(role, theme._ROLES["normal"])
    return (
        f"font-size: {size or role_size}px; "
        f"font-weight: {weight or role_weight.value};"
    )


def label(text: str = "", role: str = "normal", color: str = theme.WB_NAVY,
          *, wrap: bool = False, size: int | None = None, weight: int | None = None,
          parent: QWidget | None = None) -> QLabel:
    """A transparent label (the global QWidget rule would otherwise paint it grey)."""
    lbl = QLabel(text, parent)
    lbl.setFont(theme.font(role))
    lbl.setStyleSheet(f"background: transparent; color: {color}; {font_qss(role, size, weight)}")
    lbl.setWordWrap(wrap)
    lbl.ensurePolished()  # size hints must use the stylesheet font, not the default
    return lbl


def set_button_role(button: QAbstractButton, role: str = "secondary") -> None:
    """Give a button the shared primary / secondary / danger / ghost look."""
    if role not in BUTTON_ROLES:
        role = "secondary"
    r = theme.RADIUS_MD
    pad = "padding: 3px 10px; min-height: 18px;"
    if role == "primary":
        qss = (
            f"QPushButton {{ background: {theme.WB_GREEN}; color: #FFFFFF; border: 1px solid {theme.WB_GREEN}; "
            f"border-radius: {r}px; font-weight: 700; {pad} }} "
            f"QPushButton:hover {{ background: {theme.WB_GREEN_DARK}; border-color: {theme.WB_GREEN_DARK}; }} "
            f"QPushButton:disabled {{ background: {theme.WB_NEUTRAL_SOFT}; color: {theme.WB_NEUTRAL}; "
            f"border-color: {theme.WB_BORDER}; }}"
        )
    elif role == "danger":
        qss = (
            f"QPushButton {{ background: {theme.WB_SURFACE}; color: {theme.WB_RED}; "
            f"border: 1px solid {theme.WB_RED_BORDER}; border-radius: {r}px; font-weight: 600; {pad} }} "
            f"QPushButton:hover {{ background: {theme.WB_RED_SOFT}; border-color: {theme.WB_RED}; }} "
            f"QPushButton:disabled {{ color: {theme.WB_NEUTRAL}; background: {theme.WB_NEUTRAL_SOFT}; "
            f"border-color: {theme.WB_BORDER}; }}"
        )
    elif role == "ghost":
        qss = (
            f"QPushButton {{ background: transparent; color: {theme.WB_TEXT_SECONDARY}; border: 1px solid transparent; "
            f"border-radius: {r}px; font-weight: 600; {pad} }} "
            f"QPushButton:hover {{ background: {theme.WB_SURFACE_ALT}; color: {theme.WB_NAVY}; }} "
            f"QPushButton:disabled {{ color: {theme.WB_NEUTRAL}; }}"
        )
    else:
        qss = (
            f"QPushButton {{ background: {theme.WB_SURFACE}; color: {theme.WB_NAVY}; "
            f"border: 1px solid {theme.WB_BORDER}; border-radius: {r}px; font-weight: 600; {pad} }} "
            f"QPushButton:hover {{ background: {theme.WB_GREEN_SOFT}; border-color: {theme.WB_GREEN_BORDER}; }} "
            f"QPushButton:pressed {{ background: {theme.WB_GREEN_BORDER}; }} "
            f"QPushButton:disabled {{ color: {theme.WB_NEUTRAL}; background: {theme.WB_NEUTRAL_SOFT}; "
            f"border-color: {theme.WB_BORDER}; }}"
        )
    button.setProperty("wfRole", role)
    button.setStyleSheet(qss)


def style_progress_bar(bar: QProgressBar, tone: str = "success", *, height: int = 8) -> None:
    accent = theme.tone_colors(tone)[0]
    bar.setTextVisible(False)
    bar.setFixedHeight(height)
    bar.setStyleSheet(
        f"QProgressBar {{ background: {theme.WB_NEUTRAL_SOFT}; border: none; border-radius: {height // 2}px; }} "
        f"QProgressBar::chunk {{ background: {accent}; border-radius: {height // 2}px; }}"
    )


def style_table(view: QAbstractItemView) -> None:
    """Apply the shared compact spreadsheet treatment to a table or tree."""
    kind = "QTreeView" if isinstance(view, QTreeWidget) else "QTableView"
    view.setAlternatingRowColors(True)
    view.setStyleSheet(
        f"{kind} {{ background: #FFFFFF; alternate-background-color: #F7F9FC; "
        f"border: 1px solid #DDE4EC; border-radius: 8px; gridline-color: #E8EDF2; "
        f"color: #1B2433; selection-background-color: #E5F2D8; selection-color: #1B2433; "
        f"outline: 0; }} "
        f"{kind}::item {{ padding: 3px 7px; border: 0; border-bottom: 1px solid #EEF1F4; }} "
        f"{kind}::item:selected {{ background: #E5F2D8; color: #1B2433; }} "
        f"QHeaderView::section {{ background: #F0F3F7; color: #273449; font-weight: 650; "
        f"font-size: 12px; border: 0; border-bottom: 1px solid #DDE4EC; "
        f"border-right: 1px solid #E1E7EE; padding: 5px 8px; text-align: left; }} "
        f"QHeaderView::section:hover {{ background: #EAF2E2; color: #1B2433; }}"
    )

def divider_qss(name: str) -> str:
    return f"QFrame#{name} {{ background: {theme.WB_DIVIDER}; border: none; }}"
