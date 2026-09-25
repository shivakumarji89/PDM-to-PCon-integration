"""Command engine.

Deterministically interprets natural-language / command text into a safe
:class:`~ai.actions.Action`. It only maps intent - it never executes anything
or performs engineering calculations.
"""
from __future__ import annotations

from ai.actions import Action, ActionType
from ai.context import COLLECTIONS
from core.enums import WorkflowStep
from core.workflow import WORKFLOW_ITEMS

_STEP_TITLES = sorted(
    ((item.title.lower(), item.step) for item in WORKFLOW_ITEMS),
    key=lambda pair: len(pair[0]),
    reverse=True,
)

_LABELS = {key: label for key, label, _step, _svc in COLLECTIONS}
_STEP_FOR = {key: step for key, _label, step, _svc in COLLECTIONS}

_STOPWORDS = {
    "find", "search", "list", "show", "all", "the", "me", "with", "containing",
    "for", "that", "have", "a", "an", "of", "in", "any",
    "article", "articles", "property", "properties", "propertyvalue",
    "value", "values", "option", "options", "code", "codes",
}


class CommandEngine:
    """Parses text into a safe action intent."""

    def parse(self, text: str, current_step: WorkflowStep | None = None) -> Action:
        raw = (text or "").strip()
        low = raw.lower()
        if not low:
            return Action(ActionType.NONE, message="Please enter a command.")

        # Navigation
        if any(v in low for v in ("go to", "open", "navigate")):
            step = self._detect_step(low)
            if step is not None:
                return Action(ActionType.NAVIGATE, step=step)

        if "refresh" in low:
            return Action(ActionType.REFRESH)

        if "readiness" in low or "am i ready" in low or "can i generate" in low:
            return Action(ActionType.SHOW_READINESS)

        if "warning" in low or "error" in low:
            return Action(ActionType.SHOW_WARNINGS)

        if "select all" in low or ("select" in low and "all" in low):
            collection = self._detect_collection(low) or self._current_collection(current_step)
            return Action(ActionType.SELECT_ALL, collection=collection)

        if "clear" in low and ("select" in low or "selection" in low):
            collection = self._detect_collection(low) or self._current_collection(current_step)
            return Action(ActionType.CLEAR_SELECTION, collection=collection)

        if "invalid" in low or "missing" in low:
            collection = self._detect_collection(low)
            if collection is None and "code" in low:
                collection = "property_values"
            return Action(ActionType.SHOW_INVALID, collection=collection)

        if any(v in low for v in ("find", "search", "list", "containing", "show")):
            collection = self._detect_collection(low)
            if collection is not None:
                return Action(
                    ActionType.SEARCH,
                    step=_STEP_FOR[collection],
                    collection=collection,
                    query=self._extract_query(raw),
                )

        return Action(ActionType.NONE, message="")

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _detect_step(low: str) -> WorkflowStep | None:
        for title, step in _STEP_TITLES:
            if title in low:
                return step
        return None

    @staticmethod
    def _detect_collection(low: str) -> str | None:
        if "option value" in low:
            return "option_values"
        if "option" in low:
            return "options"
        if "property value" in low:
            return "property_values"
        if "propert" in low:
            return "properties"
        if "article" in low:
            return "articles"
        return None

    @staticmethod
    def _current_collection(current_step: WorkflowStep | None) -> str:
        for key, _label, step, _svc in COLLECTIONS:
            if step == current_step:
                return key
        return "articles"

    @staticmethod
    def _extract_query(raw: str) -> str:
        low = raw.lower()
        if "containing" in low:
            return raw[low.index("containing") + len("containing"):].strip()
        tokens = [tok for tok in raw.split() if tok.lower() not in _STOPWORDS]
        return " ".join(tokens).strip()
