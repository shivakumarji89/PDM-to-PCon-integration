"""Engineering actions.

Defines the safe action vocabulary the assistant may perform and an executor
that carries out the non-UI actions by invoking existing services and the
workflow manager. It never writes to the database, mutates the snapshot
directly, or performs engineering calculations.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from ai.context import COLLECTIONS
from core.enums import WorkflowStep


class ActionType(Enum):
    NONE = "none"
    NAVIGATE = "navigate"
    SELECT_ALL = "select_all"
    CLEAR_SELECTION = "clear_selection"
    REFRESH = "refresh"
    SEARCH = "search"
    SHOW_WARNINGS = "show_warnings"
    SHOW_INVALID = "show_invalid"
    SHOW_READINESS = "show_readiness"


@dataclass
class Action:
    """A parsed, safe action request."""

    type: ActionType = ActionType.NONE
    step: WorkflowStep | None = None
    collection: str | None = None
    query: str = ""
    message: str = ""

    @property
    def requires_ui(self) -> bool:
        # Actions that change what a workspace shows and need a UI refresh.
        return self.type in (
            ActionType.NAVIGATE,
            ActionType.SELECT_ALL,
            ActionType.CLEAR_SELECTION,
            ActionType.REFRESH,
            ActionType.SEARCH,
        )


def _collection(key: str | None):
    for entry in COLLECTIONS:
        if entry[0] == key:
            return entry
    return None


class ActionExecutor:
    """Executes non-UI actions via existing services and the workflow manager."""

    def __init__(self, app_context, manager) -> None:
        self._app = app_context
        self._manager = manager

    def execute(self, action: Action, context=None) -> str:
        # Readiness/warnings reuse an EngineeringContext already built this
        # request (from build_context) instead of recomputing review() again.
        if action.type == ActionType.SHOW_READINESS:
            return self._show_readiness(action, context)
        if action.type == ActionType.SHOW_WARNINGS:
            return self._show_warnings(action, context)
        handler = {
            ActionType.NAVIGATE: self._navigate,
            ActionType.SELECT_ALL: self._select_all,
            ActionType.CLEAR_SELECTION: self._clear_selection,
            ActionType.REFRESH: self._refresh,
            ActionType.SHOW_INVALID: self._show_invalid,
            ActionType.SEARCH: self._search_hint,
        }.get(action.type)
        if handler is None:
            return action.message or "I could not perform that action."
        return handler(action)

    # -- handlers ----------------------------------------------------------
    def _navigate(self, action: Action) -> str:
        if action.step is None:
            return "No workflow step was specified."
        if self._manager.jump_to(action.step):
            return f"Opened the {self._manager.title(action.step)} workspace."
        return (
            f"The {self._manager.title(action.step)} workspace is not available yet "
            "(load a product first)."
        )

    def _select_all(self, action: Action) -> str:
        entry = _collection(action.collection)
        if entry is None:
            return "Which collection should I select?"
        _key, label, _step, service_attr = entry
        service = getattr(self._app, service_attr)
        service.select_all()
        return f"Selected all {label} ({service.selected_count()})."

    def _clear_selection(self, action: Action) -> str:
        entry = _collection(action.collection)
        if entry is None:
            return "Which collection's selection should I clear?"
        _key, label, _step, service_attr = entry
        service = getattr(self._app, service_attr)
        service.clear_selection()
        return f"Cleared the {label} selection."

    def _refresh(self, _action: Action) -> str:
        self._manager.refresh()
        return "Refreshed the workspace state."

    def _show_warnings(self, _action: Action, context=None) -> str:
        if context is not None:
            errors, warnings = context.errors, context.warnings
        else:
            review = self._app.validation_service.review()
            errors, warnings = review.errors, review.warnings
        if errors:
            return "Errors:\n" + "\n".join(f"- {e}" for e in errors) + (
                "\nWarnings:\n" + "\n".join(f"- {w}" for w in warnings)
                if warnings else ""
            )
        if warnings:
            return "Warnings:\n" + "\n".join(f"- {w}" for w in warnings)
        return "There are no warnings or errors."

    def _show_invalid(self, action: Action) -> str:
        entry = _collection(action.collection)
        if entry is None:
            return "Which collection's invalid items should I show?"
        _key, label, _step, service_attr = entry
        service = getattr(self._app, service_attr)
        validation = service.validate()
        invalid = [
            item for item in service.items() if validation.issues_for(item)
        ]
        if not invalid:
            return f"All {label} are valid."
        lines = []
        for item in invalid[:20]:
            name = getattr(item, "name", None) or getattr(item, "value", None) or getattr(item, "code", "")
            lines.append(f"- {name}: {', '.join(validation.issues_for(item))}")
        more = "" if len(invalid) <= 20 else f"\n(+{len(invalid) - 20} more)"
        return f"Invalid {label}:\n" + "\n".join(lines) + more

    def _show_readiness(self, _action: Action, context=None) -> str:
        if context is not None:
            ready = context.readiness
        else:
            ready = self._app.validation_service.review().ready
        return f"Engineering readiness: {'READY' if ready else 'NOT READY'}."

    def _search_hint(self, action: Action) -> str:
        entry = _collection(action.collection)
        label = entry[1] if entry else "items"
        return f"Searching {label} for '{action.query}'."
