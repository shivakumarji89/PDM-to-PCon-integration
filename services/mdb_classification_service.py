"""Classification helpers for imported MDB engineering classes.

The classifier is intentionally conservative: it only suggests a type when a
class name contains an explicit Attribute/Option/Misc token. The user can
always override the suggestion in the repository classification dialog.
"""
from __future__ import annotations

import re


class MdbClassificationService:
    TYPES = ("Attribute", "Option", "Misc", "Unclassified")

    _TOKENS = {
        "ATTRIBUTE": "Attribute",
        "ATTR": "Attribute",
        "OPTION": "Option",
        "OPTIONS": "Option",
        "OPT": "Option",
        "MISC": "Misc",
        "VISUAL": "Misc",
        "GRAPHIC": "Misc",
    }

    @classmethod
    def suggest(cls, class_name: str) -> str:
        tokens = {
            token.upper()
            for token in re.split(r"[^A-Za-z0-9]+", str(class_name or ""))
            if token
        }
        for token in ("ATTRIBUTE", "ATTR", "OPTION", "OPTIONS", "OPT", "MISC", "VISUAL", "GRAPHIC"):
            if token in tokens:
                return cls._TOKENS[token]
        return "Unclassified"

    @classmethod
    def type_for_class(cls, snapshot, class_id: str) -> str:
        mapping = getattr(snapshot, "mdb_class_types", {}) or {}
        value = mapping.get(str(class_id), "Unclassified")
        return value if value in cls.TYPES else "Unclassified"

    @classmethod
    def class_ids_for_type(cls, snapshot, class_type: str) -> set[str]:
        if snapshot is None:
            return set()
        return {
            str(class_id)
            for class_id, value in (getattr(snapshot, "mdb_class_types", {}) or {}).items()
            if value == class_type
        }

    @classmethod
    def property_ids_for_type(cls, snapshot, class_type: str) -> set[str]:
        """Return source property IDs assigned to MDB classes of the given type."""
        if snapshot is None or not getattr(snapshot, "engineering", None):
            return set()
        class_ids = cls.class_ids_for_type(snapshot, class_type)
        property_ids: set[str] = set()
        for engineering_class in snapshot.engineering.classes:
            if str(engineering_class.id) not in class_ids:
                continue
            property_ids.update(
                str(assignment.property_id)
                for assignment in engineering_class.properties
                if assignment.property_id
            )
        return property_ids

    @classmethod
    def is_mdb_snapshot(cls, snapshot) -> bool:
        return bool(
            snapshot is not None
            and getattr(getattr(snapshot, "metadata", None), "source", "") == "MDB"
        )
