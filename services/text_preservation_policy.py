"""Policy for translated Text values in an attached production ProductStudio workspace.

Text in an MDB attached from an existing series repository was written by people (e.g. Dalby's long
description ``Dalby Circular Coffee Table / 650mm``); the engineering value for the same text key may be
a placeholder (``NODLE100``). Incremental writers therefore, per language column:

* **preserve** an existing populated value that differs from the incoming one (reported as a conflict);
* **populate** an existing empty value;
* **create** the row when it is missing (handled by the writer);
* **replace** only through the explicit ``replace_existing_text=True`` authorization, which the normal
  export buttons never pass.

Sessions created from a template contain only rows written by this application: the incoming value wins
(earlier behaviour). Links from articles / properties / values to a text row follow the relation-link
policy (``relation_link_policy.decide``).
"""
from __future__ import annotations

from typing import Any

from services.relation_link_policy import is_attached, is_empty  # noqa: F401  (re-exported)


def decide_text(existing: Any, incoming: Any, *, attached: bool, replace_existing: bool = False) -> tuple[Any, str]:
    """``(value to write, action)``; action is same / set / filled / replaced / preserved / skipped."""
    if is_empty(incoming):
        return existing, "skipped"            # blank source never erases a populated translation
    if str(existing or "") == str(incoming):
        return existing, "same"
    if is_empty(existing):
        return incoming, "filled"
    if not attached or replace_existing:
        return incoming, "replaced"
    return existing, "preserved"


def text_conflict(type_code: str, name: str, text_id: Any, column: str, existing: Any, incoming: Any,
                  action: str) -> dict[str, Any]:
    return {"kind": "text", "entity": f"{type_code}/{name}", "text_id": text_id, "column": column,
            "action": action, "existing": str(existing or ""), "incoming": str(incoming or "")}


def text_conflict_message(entry: dict[str, Any]) -> str:
    lang = str(entry["column"]).replace("com_Text_1_", "")
    if entry["action"] == "preserved":
        return (f"{entry['entity']} [{lang}] (text id {entry['text_id']}): existing \"{entry['existing']}\" is "
                f"PRESERVED; incoming \"{entry['incoming']}\" is NOT applied.")
    return (f"{entry['entity']} [{lang}] (text id {entry['text_id']}): existing \"{entry['existing']}\" will be "
            f"REPLACED by \"{entry['incoming']}\".")
