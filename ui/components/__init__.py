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

from ui.components.workflow_cards import (
    ActionCard,
    Card,
    DataCard,
    IconBadge,
    InfoCard,
    KpiCard,
    MessageCard,
    ProgressStatusCard,
    StatusCard,
)
from ui.components.workflow_layout import (
    ActionBar,
    CardRow,
    StatusPill,
    WorkflowHeader,
    WorkflowPageLayout,
)
from ui.components.workflow_shell import (
    AppHeaderBar,
    DetailTabs,
    ModuleIdentityPanel,
    StatusIndicator,
    WorkflowSidebar,
    WorkflowStepNav,
    WorkflowTipsCard,
)
from ui.components.workflow_styles import set_button_role, style_progress_bar, style_table

__all__ = [
    "AppHeaderBar",
    "DetailTabs",
    "ModuleIdentityPanel",
    "StatusIndicator",
    "WorkflowSidebar",
    "WorkflowStepNav",
    "WorkflowTipsCard",
    "ActionBar",
    "ActionCard",
    "Card",
    "CardRow",
    "DataCard",
    "IconBadge",
    "InfoCard",
    "KpiCard",
    "MessageCard",
    "ProgressStatusCard",
    "StatusCard",
    "StatusPill",
    "WorkflowHeader",
    "WorkflowPageLayout",
    "set_button_role",
    "style_progress_bar",
    "style_table",
    "DialogTemplate",
    "InfoRow",
    "MetricTile",
    "ProgressCard",
    "SectionHeader",
    "StatisticsGrid",
]
