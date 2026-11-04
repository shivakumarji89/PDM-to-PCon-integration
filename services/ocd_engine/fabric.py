"""Fabric properties of an article, discovered from the repository data (never from property names alone).

OCD has no fabric marker, so a *(type, colour)* property pair is recognised by the structure it carries:

``relation``      the colour values' own preconditions compare another property (the *type*) with literals
                  (``Seat_Fabric_Type = '7O'``, ``(SPECIFIED T) AND (T IN ('Z3'))``), those literals are the leading
                  characters of the colour codes (type ``7O`` -> colours ``7O005``, ``7O009``), and at least one type
                  owns several colours. A plain finish/graphic that merely depends on another property does not
                  have the code-prefix shape, so it is not taken for a fabric.
``prefix_text``   fallback for data without such relations: the colour codes extend the type codes *and* the value
                  texts (``ocd_propvaluetext``, any language) follow the ``<description> - <code>`` pattern for both
                  properties. Code prefixes alone are never enough, and a colour whose code extends more than one type
                  code is *ambiguous* - it is excluded, not guessed.

Structure is necessary but, on its own, not sufficient: an edge/material pair can have the same shape. A pair is
only *confirmed* as fabric when a property name also carries a fabric word (corroboration; the name alone never
creates a scheme). Structural pairs without that corroboration are reported by :func:`discover_schemes`
(``confirmed_only=False``) and left unreduced. The colours a configuration
may use are resolved per configuration by :mod:`services.ocd_engine.fabric_resolver`; ``default_colour`` of
:func:`fabric_structure` is only the static preview (flagged, else first in source order, ignoring relations on
properties other than the type).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from services.ocd_engine import model as m
from services.ocd_engine import relation_parser as rp

MECH_RELATION = "relation"
MECH_PREFIX_TEXT = "prefix_text"

#: Share of a colour property's values that must be tied to a type by a relation literal.
MIN_MAPPED = 0.5
#: Share of those literal-tied values whose code must start with, and be longer than, the literal.
MIN_EXTENDING = 0.9
#: Share of values of both properties whose text must end with ``- <code>`` (fallback only).
MIN_TEXT_CONFIRMED = 0.9

_NAME_HINT = re.compile(r"fabric|upholster|textile", re.IGNORECASE)
_LABEL_CODE = re.compile(r"\s-\s*(\S+)\s*$")


@dataclass(frozen=True)
class FabricEvidence:
    total: int                      # colour values considered
    mapped: int                     # tied to a type by a relation literal
    extending: int                  # ... whose code extends that literal
    prefix_only: int = 0            # fallback: values with exactly one type code as prefix
    ambiguous: int = 0              # fallback: values whose code extends several type codes
    text_confirmed: float = 0.0     # share of values (both properties) whose text ends with ``- <code>``
    name_hint: bool = False         # a property name carries a fabric word (corroboration, never sufficient)


@dataclass(frozen=True)
class FabricScheme:
    type_property: str
    colour_property: str
    mechanism: str
    evidence: FabricEvidence

    @property
    def type_upper(self) -> str:
        return self.type_property.upper()

    @property
    def colour_upper(self) -> str:
        return self.colour_property.upper()


def type_literals(value: m.ValueDef, type_name: str) -> list[str]:
    """Type values the precondition(s) of ``value`` compare ``type_name`` with (positive ``=`` / ``IN`` only)."""
    found: list[str] = []
    name = rf"(?<![A-Za-z0-9_]){re.escape(type_name)}"
    for ref in value.relations:
        if ref.rel_type != m.PRECONDITION or ref.domain.upper() != "C":
            continue
        if rp.compile_relation(m.PRECONDITION, ref.text).error:
            continue
        found.extend(re.findall(rf"{name}\s*=\s*'([^']*)'", ref.text, re.IGNORECASE))
        for group in re.findall(rf"{name}\s+IN\s*\(([^)]*)\)", ref.text, re.IGNORECASE):
            found.extend(re.findall(r"'([^']*)'", group))
    return found


def _offered(prop: m.PropertyDef) -> list[m.ValueDef]:
    allowed = prop.allowed_keys
    return [v for v in prop.values if allowed is None or v.key in allowed]


def labelled_with_code(value: m.ValueDef) -> bool:
    """A language text of ``value`` follows ``<description> - <code>`` with the value's own code."""
    return any((hit := _LABEL_CODE.search(text)) is not None and hit.group(1).lower() == value.value.lower()
               for _, text in value.labels)


def _text_share(types: m.PropertyDef, colours: list[m.ValueDef]) -> float:
    both = _offered(types) + colours
    return sum(labelled_with_code(v) for v in both) / len(both) if both else 0.0


def _hint(types: m.PropertyDef, colour: m.PropertyDef) -> bool:
    return bool(_NAME_HINT.search(types.name) or _NAME_HINT.search(colour.name))


def _relation_evidence(types: m.PropertyDef, colour: m.PropertyDef,
                       values: list[m.ValueDef]) -> tuple[FabricEvidence, bool]:
    mapped = extending = 0
    per_literal: dict[str, int] = {}
    for value in values:
        literals = set(type_literals(value, types.name))
        if not literals:
            continue
        mapped += 1
        hits = [lit for lit in literals if lit and value.value.startswith(lit) and len(value.value) > len(lit)]
        if hits:
            extending += 1
            for lit in hits:
                per_literal[lit] = per_literal.get(lit, 0) + 1
    evidence = FabricEvidence(len(values), mapped, extending, text_confirmed=_text_share(types, values),
                              name_hint=_hint(types, colour))
    return evidence, any(n >= 2 for n in per_literal.values())


def prefix_members(type_value: str, colours: Sequence[m.ValueDef], type_values: Sequence[str]) -> tuple[list, list]:
    """``(members, ambiguous)`` of ``colours`` for ``type_value`` by code prefix.

    A colour is a member when its code extends ``type_value`` and no *other* type code is also a prefix of it;
    when another is, the colour is ambiguous (``7O576`` under types ``7O`` and ``7O5``) and belongs to neither."""
    members, ambiguous = [], []
    for colour in colours:
        code = colour.value
        owners = [t for t in type_values if t and code.startswith(t) and len(code) > len(t)]
        if type_value in owners:
            (members if len(owners) == 1 else ambiguous).append(colour)
    return members, ambiguous


def _fallback_evidence(types: m.PropertyDef, colour: m.PropertyDef,
                       values: list[m.ValueDef]) -> tuple[FabricEvidence, bool]:
    codes = [t.value for t in _offered(types)]
    unique = ambiguous = 0
    per_type: dict[str, int] = {}
    for value in values:
        owners = [t for t in codes if t and value.value.startswith(t) and len(value.value) > len(t)]
        if len(owners) == 1:
            unique += 1
            per_type[owners[0]] = per_type.get(owners[0], 0) + 1
        elif owners:
            ambiguous += 1
    evidence = FabricEvidence(len(values), 0, 0, unique, ambiguous, _text_share(types, values), _hint(types, colour))
    return evidence, any(n >= 2 for n in per_type.values())


def discover_schemes(model: m.ArticleModel, *, confirmed_only: bool = True) -> tuple[FabricScheme, ...]:
    """Every fabric (type, colour) pair of the article, one per colour property, by the evidence above.

    ``confirmed_only=False`` also returns structural pairs without a fabric word in either property name."""
    props = [p for p in model.properties if p.values]
    schemes: list[FabricScheme] = []
    for colour in props:
        values = _offered(colour)
        if len(values) < 2:
            continue
        best: tuple[tuple, FabricScheme] | None = None
        for types in props:
            if types is colour or not _offered(types):
                continue
            evidence, many = _relation_evidence(types, colour, values)
            if (evidence.mapped >= MIN_MAPPED * evidence.total and evidence.mapped
                    and evidence.extending >= MIN_EXTENDING * evidence.mapped and many):
                scheme, rank = FabricScheme(types.name, colour.name, MECH_RELATION, evidence), (2, evidence.mapped)
            else:
                evidence, many = _fallback_evidence(types, colour, values)
                if not (evidence.prefix_only >= MIN_MAPPED * evidence.total and many
                        and evidence.text_confirmed >= MIN_TEXT_CONFIRMED):
                    continue
                scheme, rank = FabricScheme(types.name, colour.name, MECH_PREFIX_TEXT, evidence), (1, evidence.prefix_only)
            if best is None or rank > best[0]:
                best = (rank, scheme)
        if best is not None and (best[1].evidence.name_hint or not confirmed_only):
            schemes.append(best[1])
    return tuple(schemes)


def fabric_types(model: m.ArticleModel) -> list[m.PropertyDef]:
    names = {s.type_upper for s in discover_schemes(model)}
    return [p for p in model.properties if p.name_upper in names]


def fabric_colours(model: m.ArticleModel) -> list[m.PropertyDef]:
    names = {s.colour_upper for s in discover_schemes(model)}
    return [p for p in model.properties if p.name_upper in names]


@dataclass(frozen=True)
class FabricType:
    type_property: str
    colour_property: str
    type_value: str
    colours: tuple[str, ...]
    default_colour: str | None
    mechanism: str = MECH_RELATION


def fabric_structure(model: m.ArticleModel) -> list[FabricType]:
    """Every fabric type value with its colours and default colour, per discovered type/colour pair."""
    by_name = {p.name_upper: p for p in model.properties}
    out: list[FabricType] = []
    for scheme in discover_schemes(model):
        owner, colour = by_name[scheme.type_upper], by_name[scheme.colour_upper]
        values = _offered(colour)
        type_values = [t.value for t in _offered(owner)]
        for type_value in _offered(owner):
            if scheme.mechanism == MECH_RELATION:
                members = [v for v in values if type_value.value in type_literals(v, owner.name)]
            else:
                members, _ = prefix_members(type_value.value, values, type_values)
            default = next((v.value for v in members if v.is_default), members[0].value if members else None)
            out.append(FabricType(owner.name, colour.name, type_value.value,
                                  tuple(v.value for v in members), default, scheme.mechanism))
    return out


def constrained_to_default(candidates: Sequence[m.ValueDef]) -> list[m.ValueDef]:
    """The default colour among relation-valid ``candidates``: the flagged ``is_default`` one if any, else the first.

    ``candidates`` are already filtered by the colours' relations and are in OCD source order
    (``pos_pval``), so "first" is the first colour valid for the current configuration.
    """
    flagged = next((v for v in candidates if v.is_default), None)
    return [flagged if flagged is not None else candidates[0]] if candidates else []
