"""Design-system component library.

Reusable, token-driven widgets and templates that every screen composes. No
component contains business logic; all visual values come from :mod:`ui.theme`.
"""
from __future__ import annotations

from ui.components.dialog_template import DialogTemplate
from ui.components.info_row import InfoRow
from ui.components.metric import MetricTile, StatisticsGrid
from ui.components.progress_card import ProgressCard
from ui.components.section_header import SectionHeader

__all__ = [
    "DialogTemplate",
    "InfoRow",
    "MetricTile",
    "ProgressCard",
    "SectionHeader",
    "StatisticsGrid",
]
