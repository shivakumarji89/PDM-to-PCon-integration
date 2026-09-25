"""Engineering assistant.

Orchestrates the AI layer: builds the read-only engineering context, produces
recommendations, interprets commands into safe actions, executes the non-UI
actions via existing services/manager, explains engineering state, talks to an
AI provider for free-form questions, and maintains conversation history.

It performs no engineering calculations and never writes to the database or
mutates the snapshot directly.
"""
from __future__ import annotations

from dataclasses import dataclass

from ai.actions import Action, ActionExecutor, ActionType
from ai.commands import CommandEngine
from ai.context import EngineeringContext, build_context
from ai.history import AssistantHistory
from ai.prompts import build_prompt
from ai.provider import AIProvider, MockProvider
from ai.recommendations import RecommendationEngine


@dataclass
class AssistantResponse:
    """The assistant's reply plus the (already-parsed) action to reflect in UI."""

    message: str
    action: Action


class EngineeringAssistant:
    """Reads the engineering session and helps without changing engineering logic."""

    def __init__(self, app_context, manager, provider: AIProvider | None = None) -> None:
        self._app = app_context
        self._manager = manager
        self._provider = provider or MockProvider()
        self._commands = CommandEngine()
        self._recommendations = RecommendationEngine()
        self._executor = ActionExecutor(app_context, manager)
        self.history = AssistantHistory()

    # -- context / recommendations ----------------------------------------
    def context(self) -> EngineeringContext:
        return build_context(self._app, self._manager)

    def recommendations(self) -> list[str]:
        recommendations = self._recommendations.generate(self.context())
        self.history.set_recommendations(recommendations)
        return recommendations

    # -- conversation ------------------------------------------------------
    def handle(self, text: str) -> AssistantResponse:
        """Interpret text, execute a safe action or answer, and record history."""
        context = self.context()
        action = self._commands.parse(text, context.current_step)
        self.history.add_user(text)
        self.history.add_command(text)

        if action.type == ActionType.NONE:
            message = self._answer(text, context)
        elif action.type == ActionType.SEARCH:
            message = self._executor.execute(action, context)  # UI performs the search
        else:
            message = self._executor.execute(action, context)

        self.history.add_assistant(message)
        return AssistantResponse(message, action)

    def run_action(self, action: Action) -> str:
        """Execute a pre-built action (used by quick-action buttons)."""
        message = self._executor.execute(action)
        self.history.add_assistant(message)
        return message

    # -- explanations / provider ------------------------------------------
    def _answer(self, text: str, context: EngineeringContext) -> str:
        low = text.lower()
        if "why" in low or "explain" in low:
            return self._explain(low, context)
        return self._provider.respond(build_prompt(context), context)

    def _explain(self, low: str, context: EngineeringContext) -> str:
        if "review" in low:
            if context.readiness:
                return "Review is ready: no blocking errors or missing relationships."
            issues = context.errors + context.missing_relationships
            return "Review is not ready because: " + (
                "; ".join(issues) if issues else "of validation issues"
            ) + "."
        if "warning" in low:
            return "Warnings come from validating your snapshot: " + (
                "; ".join(context.warnings) if context.warnings else "there are none"
            ) + "."
        return self._provider.respond(build_prompt(context), context)
