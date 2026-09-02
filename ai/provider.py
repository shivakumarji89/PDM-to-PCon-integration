"""AI provider abstraction.

Defines the provider interface the assistant talks to, plus a deterministic
``MockProvider`` that answers from the engineering context. Real providers
(OpenAI, Azure OpenAI, local LLM) can be added later without changing the
assistant - it only depends on this interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from ai.context import EngineeringContext
from ai.prompts import build_prompt


class AIProvider(ABC):
    """Interface every AI provider implements."""

    @abstractmethod
    def respond(self, prompt: str, context: EngineeringContext) -> str:
        """Return a response for the given prompt and context."""


class MockProvider(AIProvider):
    """Deterministic provider that summarises the engineering context.

    Produces no invented data - every statement is derived from the context,
    which itself comes from the existing services.
    """

    name = "Mock"

    def respond(self, prompt: str, context: EngineeringContext) -> str:
        if not context.has_snapshot:
            return "No product is loaded. Load a product on the Product page to begin."

        completed, total = context.progress
        selected_total = sum(context.selected.values())
        parts = [
            f"You are working on {context.product_label}.",
            f"Current step: {context.current_step.name.title()} "
            f"({completed}/{total} steps completed).",
            f"You have selected {selected_total} item(s) in total.",
        ]
        if context.errors:
            parts.append(f"There are {len(context.errors)} blocking error(s).")
        elif context.warnings:
            parts.append(f"There are {len(context.warnings)} warning(s) to review.")
        else:
            parts.append("No warnings or errors were found.")
        parts.append(
            "Engineering readiness: "
            + ("ready to generate." if context.readiness else "not ready yet.")
        )
        return " ".join(parts)
