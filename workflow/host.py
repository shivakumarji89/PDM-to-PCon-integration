"""Workspace host.

Owns the lifecycle of the hosted workspace pages (show/hide/activate/
deactivate/refresh/notify) on the shared stack. It performs no engineering
logic - it only drives workspace lifecycle methods and page switching.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer

from core.enums import WorkflowStep


class WorkspaceHost:
    """Drives workspace lifecycle on a QStackedWidget."""

    def __init__(self, stack, pages: dict[WorkflowStep, object]) -> None:
        self._stack = stack
        self._pages = pages
        self._current: WorkflowStep | None = None

    def get(self, step: WorkflowStep):
        return self._pages[step]

    def current(self) -> WorkflowStep | None:
        return self._current

    def activate(self, step: WorkflowStep) -> None:
        """Show and activate a workspace, deactivating the previous one."""
        if self._current is not None and self._current != step:
            previous = self._pages.get(self._current)
            if previous is not None:
                previous.on_leave()
                previous.deactivate()

        page = self._pages[step]
        self._stack.setCurrentWidget(page)
        # QStackedWidget does not call the workspace's refresh hook when the
        # page becomes current. Refresh on activation so workflows always
        # reflect the latest shared ApplicationContext snapshot.
        page.refresh()
        page.activate()
        page.on_enter()

        # Fit every visible table after refresh and layout have completed.
        if hasattr(page, "auto_fit_tables"):
            QTimer.singleShot(0, page.auto_fit_tables)

        self._current = step

    def is_ready(self, step: WorkflowStep) -> bool:
        page = self._pages[step]
        # A single page can host multiple workflow stages (Metatype). Let it
        # calculate readiness for the requested stage instead of applying the
        # page-wide readiness to every navigator entry.
        stage_readiness = getattr(page, "is_ready_for_step", None)
        if callable(stage_readiness):
            return bool(stage_readiness(step))
        return bool(page.is_ready())

    def refresh(self, step: WorkflowStep) -> None:
        self._pages[step].refresh()

    def refresh_all(self) -> None:
        for page in self._pages.values():
            page.refresh()
