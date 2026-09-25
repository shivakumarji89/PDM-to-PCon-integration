"""Assistant history.

In-memory conversation and activity history for the current session. Holds no
engineering data - only messages, issued commands and recommendations.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Message:
    role: str  # "user" | "assistant"
    text: str


@dataclass
class AssistantHistory:
    """In-memory record of the assistant conversation and activity."""

    messages: list[Message] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    transitions: list[str] = field(default_factory=list)

    def add_user(self, text: str) -> None:
        self.messages.append(Message("user", text))

    def add_assistant(self, text: str) -> None:
        self.messages.append(Message("assistant", text))

    def add_command(self, text: str) -> None:
        self.commands.append(text)

    def set_recommendations(self, recommendations: list[str]) -> None:
        self.recommendations = list(recommendations)

    def add_transition(self, description: str) -> None:
        self.transitions.append(description)

    def clear(self) -> None:
        self.messages.clear()
        self.commands.clear()
        self.recommendations.clear()
        self.transitions.clear()
