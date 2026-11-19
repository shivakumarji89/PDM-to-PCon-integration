"""Policy for relation-object / code-scheme links on articles of an attached production workspace.

An MDB attached from an existing series repository holds production links this application did not
write (e.g. every Dalby article points at the shared price relation object ``P_PRICING_DALBY``; Lino's
``MI1E3`` at ``P_PRICING_CHAIR``). Incremental writers must not silently re-point them:

* an existing *valid* link (it points at a row that exists) is **preserved**;
* a link is created only when it is genuinely **missing** (NULL, or dangling = target row gone);
* a differing incoming link is reported as a **conflict** with both identifiers and their relation
  information, in the preview and in the result;
* replacement happens only through an explicit ``replace_existing_links=True`` operation, which is a
  separate authorization and is not offered by the normal export buttons.

Sessions created from a template contain only rows written by this application, so they keep the
earlier behaviour (the incoming link wins).
"""
from __future__ import annotations

from typing import Any, Iterable


def is_attached(session: Any) -> bool:
    return bool(getattr(session, "attached_existing", False))


def _key(value: Any) -> str:
    try:
        return str(int(float(value)))
    except (TypeError, ValueError):
        return str(value or "").strip()


def is_empty(value: Any) -> bool:
    return value is None or str(value).strip() == ""


class LinkDescriber:
    """Human-readable description of a relation object and the relations attached to it."""

    def __init__(self, objects: Iterable[dict], links: Iterable[dict] = (), relations: Iterable[dict] = ()):
        self.names = {_key(r.get("com_RelObjID")): str(r.get("com_RelObjName") or "") for r in objects}
        relation_names = {_key(r.get("com_RelationID")): str(r.get("com_RelationName") or "") for r in relations}
        self.relations: dict[str, list[dict[str, str]]] = {}
        for link in links:
            self.relations.setdefault(_key(link.get("com_RelObjID")), []).append({
                "relation": relation_names.get(_key(link.get("com_RelationID")), f"id {_key(link.get('com_RelationID'))}"),
                "type": str(link.get("com_RelObjTypeCode") or ""),
                "domain": str(link.get("com_RelObjDomainCode") or ""),
                "order": str(link.get("com_RelationOrder") if link.get("com_RelationOrder") is not None else ""),
            })

    def exists(self, object_id: Any) -> bool:
        return _key(object_id) in self.names

    def describe(self, object_id: Any) -> dict[str, Any]:
        key = _key(object_id)
        return {"id": key, "name": self.names.get(key, ""), "found": key in self.names,
                "relations": list(self.relations.get(key, []))}

    def text(self, object_id: Any) -> str:
        info = self.describe(object_id)
        if not info["found"]:
            return f"id {info['id']} (not found)"
        if not info["relations"]:
            return f"{info['name']} (id {info['id']}; no relation attached)"
        parts = "; ".join(
            f"relation {r['relation']}, type {r['type'] or '-'}, domain {r['domain'] or '-'}, order {r['order'] or '-'}"
            for r in info["relations"][:3])
        return f"{info['name']} (id {info['id']}; {parts})"


def decide(existing: Any, incoming: Any, *, attached: bool, replace_existing: bool = False,
           valid: Any = None) -> tuple[Any, str]:
    """``(value to write, action)``; action is one of same / set / repaired / replaced / preserved.

    ``valid`` is a callable ``id -> bool`` (the target row exists). ``None`` treats any non-empty link as valid.
    """
    if _key(existing) == _key(incoming) and not is_empty(existing):
        return existing, "same"
    if is_empty(incoming):
        return existing, "same"
    existing_valid = (not is_empty(existing)) and (valid is None or bool(valid(existing)))
    if not existing_valid:
        return incoming, "set" if is_empty(existing) else "repaired"
    if not attached or replace_existing:
        return incoming, "replaced"
    return existing, "preserved"


def conflict_entry(kind: str, entity: str, existing: Any, incoming: Any, action: str,
                   describer: LinkDescriber, column: str = "com_RelObjID") -> dict[str, Any]:
    return {
        "kind": kind, "entity": entity, "column": column, "action": action,
        "existing": describer.describe(existing), "incoming": describer.describe(incoming),
        "existing_text": describer.text(existing), "incoming_text": describer.text(incoming),
    }


def conflict_message(entry: dict[str, Any]) -> str:
    label = "relation object" if entry["kind"] != "code_scheme" else "code scheme"
    if entry["action"] == "preserved":
        return (f"{entry['entity']}: existing {label} link {entry['existing_text']} is PRESERVED; "
                f"incoming {entry['incoming_text']} is NOT applied.")
    return (f"{entry['entity']}: existing {label} link {entry['existing_text']} will be REPLACED by "
            f"{entry['incoming_text']}.")
