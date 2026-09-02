"""Unified design system tokens for the Engineering Workbench.

Single source of truth for typography, spacing, colours and status presentation
used across every workspace. Widgets and the stylesheet share these values so
the application looks and behaves like one mature desktop product rather than a
set of independently styled pages.

This module is presentation-only: it defines constants and small helpers and
never touches business logic, services or the workflow.
"""
from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor, QFont

# --------------------------------------------------------------------------
# Palette (kept in sync with resources/styles.qss)
# --------------------------------------------------------------------------
INK = "#1f2733"          # primary text
INK_SOFT = "#33404f"     # secondary text
MUTED = "#63707e"        # helper / disabled text
LINE = "#e1e6ec"         # borders / dividers
SURFACE = "#ffffff"      # panels / inputs
CANVAS = "#f4f6f8"       # window background
ACCENT = "#2f6fed"       # primary / current
ACCENT_DARK = "#2a63d4"

COLOR_OK = "#1f9d55"
COLOR_WARNING = "#c77f0a"
COLOR_ERROR = "#c0392b"
COLOR_INFO = "#2f6fed"
COLOR_MUTED = "#63707e"

# Additive V1 surfaces / soft tints (design system).
SURFACE_ALT = "#fafbfc"   # zebra rows / card body
LINE_STRONG = "#cfd6de"   # active borders
ACCENT_SOFT = "#eaf1fe"   # selection / accent fill
OK_SOFT = "#e7f5ee"
WARNING_SOFT = "#fdf3e2"
ERROR_SOFT = "#fbecea"
INFO_SOFT = "#eaf1fe"

# --------------------------------------------------------------------------
# Spacing (pixels) - use these instead of ad-hoc numbers
# --------------------------------------------------------------------------
PAGE_MARGIN = 16         # outer margin of a workspace page
SECTION_SPACING = 8      # gap between sections in a page
GROUP_PADDING = 8        # inner padding of a group box
CONTROL_SPACING = 6      # gap between related controls
LABEL_SPACING = 6        # gap between a label and its value
TABLE_PADDING = 4        # cell padding
TREE_PADDING = 3         # tree row padding

# Formal spacing scale (4/8/12/16/24/32) - prefer these in new components.
SPACE_1 = 4
SPACE_2 = 8
SPACE_3 = 12
SPACE_4 = 16
SPACE_5 = 24
SPACE_6 = 32

# Application shell layout - one source of truth for the 3-panel gaps/insets.
# Used by the Python layouts AND (via @token@ substitution in main.load_stylesheet)
# by the stylesheet, so panels never drift apart again.
PANEL_INSET = SPACE_2     # content padding inside every top-level panel (8)
PANEL_GUTTER = SPACE_2    # gap between panels: splitter handles + dock separators (8)

# Corner radius.
RADIUS_SM = 4
RADIUS_MD = 6
RADIUS_LG = 10

# Component metrics.
CONTROL_H = 30
PROGRESS_H = 10

# --------------------------------------------------------------------------
# Typography (pixel sizes + weights)
# --------------------------------------------------------------------------
FONT_FAMILY = "Segoe UI"

WEIGHT_NORMAL = QFont.Weight.Normal
WEIGHT_SEMIBOLD = QFont.Weight.DemiBold
WEIGHT_BOLD = QFont.Weight.Bold

# role -> (pixel size, weight)
_ROLES: dict[str, tuple[int, QFont.Weight]] = {
    "app_title": (15, WEIGHT_BOLD),
    "workspace_title": (18, WEIGHT_BOLD),
    "section_header": (13, WEIGHT_BOLD),
    "tab_header": (13, WEIGHT_SEMIBOLD),
    "normal": (13, WEIGHT_NORMAL),
    "table_header": (13, WEIGHT_SEMIBOLD),
    "table_cell": (13, WEIGHT_NORMAL),
    "status": (13, WEIGHT_SEMIBOLD),
    "helper": (12, WEIGHT_NORMAL),
    "button": (13, WEIGHT_SEMIBOLD),
    # Additive V1 roles (cards, metrics, dialogs).
    "dialog_title": (18, WEIGHT_BOLD),
    "subtitle": (13, WEIGHT_NORMAL),
    "card_title": (13, WEIGHT_SEMIBOLD),
    "metric_value": (20, WEIGHT_BOLD),
    "metric_label": (11, WEIGHT_SEMIBOLD),
    "percent": (20, WEIGHT_BOLD),
}


def font(role: str = "normal") -> QFont:
    """Return the :class:`QFont` for a typography role from the design system."""
    size, weight = _ROLES.get(role, _ROLES["normal"])
    f = QFont(FONT_FAMILY)
    f.setPixelSize(size)
    f.setWeight(weight)
    return f


# --------------------------------------------------------------------------
# Status presentation (colour + glyph + label). One vocabulary everywhere.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class StatusStyle:
    label: str
    color: str
    glyph: str


STATUS: dict[str, StatusStyle] = {
    "ready": StatusStyle("Ready", COLOR_OK, "\u25CF"),          # ●
    "current": StatusStyle("Current", ACCENT, "\u25B6"),        # ▶
    "completed": StatusStyle("Completed", COLOR_OK, "\u2714"),  # ✔
    "blocked": StatusStyle("Blocked", MUTED, "\U0001F512"),     # 🔒
    "not_started": StatusStyle("Not started", MUTED, "\u25CB"), # ○
    "warning": StatusStyle("Warning", COLOR_WARNING, "\u26A0"), # ⚠
    "error": StatusStyle("Error", COLOR_ERROR, "\u2716"),       # ✖
    "invalid": StatusStyle("Invalid", COLOR_ERROR, "\u26A0"),   # ⚠
    "information": StatusStyle("Information", COLOR_INFO, "\u2139"),  # ℹ
    "success": StatusStyle("Success", COLOR_OK, "\u2714"),      # ✔
}


def status_style(name: str) -> StatusStyle:
    """Return the :class:`StatusStyle` for a status name (defaults to info)."""
    return STATUS.get(name, STATUS["information"])


def status_color(name: str) -> QColor:
    return QColor(status_style(name).color)
