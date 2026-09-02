"""Workspace host.

Owns the lifecycle of the hosted workspace pages (show/hide/activate/
deactivate/refresh/notify) on the shared stack. It performs no engineering
logic - it only drives workspace lifecycle methods and page switching.
"""
from __future__ import annotations

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
        self._stack.setCurrentWidget(page)  # triggers the page's own refresh
        page.activate()
        page.on_enter()
        self._current = step

    def is_ready(self, step: WorkflowStep) -> bool:
        return bool(self._pages[step].is_ready())

    def refresh(self, step: WorkflowStep) -> None:
        self._pages[step].refresh()

    def refresh_all(self) -> None:
        for page in self._pages.values():
            page.refresh()
