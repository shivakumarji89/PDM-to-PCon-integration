"""Adapter between repository Snapshots and the standalone OCD engine.

``services/ocd_engine`` knows nothing about Snapshots. This module converts the
Snapshot's relation objects, property/option values, value tables and code
schemes into the engine's neutral model, so ``ArticlePermutationService`` can
delegate relation evaluation and CodeScheme encoding without changing its
public interface.

Binding rules (mirroring the repository data model):

* a relation bound to value ids attaches to those values;
* a relation bound to property ids only attaches to those properties;
* a relation bound to nothing is article-level (actions, constraints);
* ``article_codes`` / ``article_classes`` restrict a relation to those articles.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Iterable, Sequence

from services.ocd_engine import model as m
from services.ocd_engine.codescheme_engine import CodeSchemeDef


def normalise_name(value: str) -> str:
    """Identifier form relations and schemes use: ``Seat Depth`` -> ``SEAT_DEPTH``."""
    return re.sub(r"[^A-Za-z0-9_]+", "_", value or "").strip("_").upper()


def _ids(relation, many: str, one: str) -> list[str]:
    found = {str(v) for v in (getattr(relation, many, []) or []) if str(v)}
    single = str(getattr(relation, one, "") or "")
    if single:
        found.add(single)
    return sorted(found)


class SnapshotRelationIndex:
    """Relation objects of a Snapshot, indexed by what they are bound to."""

    def __init__(self, relations: Iterable) -> None:
        self.by_value: dict[str, list[tuple[object, m.RelationRef]]] = defaultdict(list)
        self.by_property: dict[str, list[tuple[object, m.RelationRef]]] = defaultdict(list)
        self.unbound: list[tuple[object, m.RelationRef]] = []
        ordered = sorted(
            relations or [],
            key=lambda r: (int(getattr(r, "order", 100) or 100), getattr(r, "name", "") or ""),
        )
        for relation in ordered:
            type_code = str(getattr(relation, "type_code", "") or "")
            if not type_code.isdigit():
                continue
            rel_type = int(type_code)
            value_ids = _ids(relation, "value_ids", "value_id")
            property_ids = _ids(relation, "property_ids", "property_id")
            name = (getattr(relation, "name", "") or getattr(relation, "relation_name", "") or "relation")
            if value_ids and rel_type == m.SELECTION:
                # Repository data binds hierarchy conditions to values with the
                # selection-condition code; they gate the value like a precondition.
                rel_type = m.PRECONDITION
            ref = m.RelationRef(
                name=str(name), rel_type=rel_type,
                domain=str(getattr(relation, "domain", "") or "C"),
                order=int(getattr(relation, "order", 100) or 100),
                text=str(getattr(relation, "body", "") or ""),
            )
            if value_ids:
                for value_id in value_ids:
                    self.by_value[value_id].append((relation, ref))
            elif property_ids:
                for property_id in property_ids:
                    self.by_property[property_id].append((relation, ref))
            else:
                self.unbound.append((relation, ref))

    @staticmethod
    def _applies(relation, base_code: str) -> bool:
        codes = list(getattr(relation, "article_codes", []) or [])
        return not codes or base_code in codes

    def for_value(self, value_id: str, base_code: str) -> tuple[m.RelationRef, ...]:
        return tuple(ref for rel, ref in self.by_value.get(str(value_id), ())
                     if self._applies(rel, base_code))

    def for_property(self, property_id: str, base_code: str) -> tuple[m.RelationRef, ...]:
        return tuple(ref for rel, ref in self.by_property.get(str(property_id), ())
                     if self._applies(rel, base_code))

    def article_level(self, base_code: str) -> tuple[m.RelationRef, ...]:
        # Unbound preconditions/selection conditions have no entity to gate, so
        # only actions, constraints and reactions are article-level.
        return tuple(
            ref for rel, ref in self.unbound
            if ref.rel_type >= m.ACTION and self._applies(rel, base_code)
        )


def value_def(source, dimension_kind: str) -> m.ValueDef:
    """Engine value for a Snapshot property/option value.

    Relations see the display ``value``; encoding uses the code (``#`` marks
    stripped) or, failing that, the display value - exactly as the generator
    always did.
    """
    code = (getattr(source, "code", "") or getattr(source, "supplier_code", "") or "").replace("#", "")
    return m.ValueDef(
        key=str(source.id), value=source.value or "", code=code, display=source.value or "",
        order=int(getattr(source, "display_order", 0) or 0),
    )


def property_def(dimension, index: dict | SnapshotRelationIndex, base_code: str,
                 *, order: int = 0, allowed_ids: set[str] | None = None) -> m.PropertyDef:
    """Engine property for a ``_Dimension`` of the permutation service."""
    relation_index: SnapshotRelationIndex = index  # type: ignore[assignment]
    values = tuple(
        m.ValueDef(
            key=str(v.id), value=v.value or "",
            code=(getattr(v, "code", "") or getattr(v, "supplier_code", "") or "").replace("#", ""),
            display=v.value or "", order=int(getattr(v, "display_order", 0) or 0),
            relations=relation_index.for_value(str(v.id), base_code),
        )
        for v in dimension.values
    )
    return m.PropertyDef(
        key=f"{dimension.kind}:{dimension.entity_id}", name=normalise_name(dimension.name),
        class_name="", order=order, values=values,
        relations=relation_index.for_property(dimension.entity_id, base_code),
        kind=dimension.kind, scope="C",
        allowed_keys=frozenset(allowed_ids) if allowed_ids is not None else None,
    )


def value_tables(snapshot) -> dict[str, object]:
    return {
        str(t.name or "").upper(): t
        for t in (getattr(snapshot, "value_tables", []) or [])
        if getattr(t, "name", "")
    }


def scheme_definition(scheme_row: dict) -> CodeSchemeDef:
    """Scheme definition from a Snapshot ``code_schemes`` row.

    A row with no scheme text is a predefined ``ValueList`` described only by
    its separator fields (the repository's compact representation).

    The MDB import currently keeps only ``name`` and ``body`` of a code scheme,
    not its visibility/replacement-character/trim fields. When the row carries
    no ``visibility`` field the scheme is evaluated in mode ``0`` (a property
    hidden by a precondition contributes nothing) - the value every sampled real
    scheme carries and the legacy behaviour - rather than the spec's "empty =
    mode 1", which would invent ``-`` placeholders the real number never has.
    """
    row = scheme_row or {}
    definition = CodeSchemeDef.from_row(row)
    has_visibility = any(str(k).lower() == "visibility" for k in row)
    visibility = definition.visibility if has_visibility else "0"
    scheme_text = definition.scheme if definition.scheme.strip() else "ValueList"
    return CodeSchemeDef(
        scheme_id=definition.scheme_id, scheme=scheme_text,
        varcode_sep=definition.varcode_sep, value_sep=definition.value_sep,
        visibility=visibility, invisible_char=definition.invisible_char,
        unselect_char=definition.unselect_char, trim=definition.trim,
        mo_sep=definition.mo_sep, mo_bracket=definition.mo_bracket,
    )


def codes_by_name(assignments: Sequence[m.Assignment]) -> dict[str, str]:
    """Right-hand-side operand values: the encoded token of each selected value."""
    return {
        a.prop.name_upper: (a.value.code or a.value.value or "")
        for a in assignments if a.value is not None and not a.hidden
    }
