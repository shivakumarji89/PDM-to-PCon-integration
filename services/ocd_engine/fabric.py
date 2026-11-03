"""Fabric properties of an article: types, their colours and the default colour per type.

OCD has no fabric marker. A fabric *type* property and a fabric *colour* property are recognised by name
(``*Fabric*Type``, ``*Fabric*Colo(u)r``) and the colour is only treated as a fabric colour when the article also
has a fabric type, so a plain ``Colour`` property is never touched. Which colours belong to which type is not a
table either: each colour value carries a precondition on the type (``Seat_Fabric_Type = 'VZ'``), so it is read
from the relations. The default colour is chosen per configuration by the engine, not here: the first colour valid after
relation evaluation, in ``pos_pval`` order (a value flagged ``is_default`` wins when it is valid). The
``default_colour`` of :func:`fabric_structure` is only the static preview: flagged, else first by source order,
ignoring relations on properties other than the type.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from services.ocd_engine import model as m
from services.ocd_engine import relation_parser as rp

_TYPE = re.compile(r"fabric.*type", re.IGNORECASE)
_COLOUR = re.compile(r"fabric.*colou?r", re.IGNORECASE)


def fabric_types(model: m.ArticleModel) -> list[m.PropertyDef]:
    return [p for p in model.properties if _TYPE.search(p.name)]


def fabric_colours(model: m.ArticleModel) -> list[m.PropertyDef]:
    """Fabric colour properties; empty unless the article has a fabric type property."""
    return [p for p in model.properties if _COLOUR.search(p.name)] if fabric_types(model) else []


@dataclass(frozen=True)
class FabricType:
    type_property: str
    colour_property: str
    type_value: str
    colours: tuple[str, ...]
    default_colour: str | None


def _types_of_colour(value: m.ValueDef, type_name: str) -> list[str]:
    """Type values a colour's precondition admits: the literals compared with the type property."""
    found: list[str] = []
    for ref in value.relations:
        if ref.rel_type != m.PRECONDITION:
            continue
        compiled = rp.compile_relation(m.PRECONDITION, ref.text)
        if compiled.error:
            continue
        found.extend(re.findall(rf"{re.escape(type_name)}\s*=\s*'([^']*)'", ref.text, re.IGNORECASE))
        for group in re.findall(rf"{re.escape(type_name)}\s+IN\s*\(([^)]*)\)", ref.text, re.IGNORECASE):
            found.extend(re.findall(r"'([^']*)'", group))
    return found


def fabric_structure(model: m.ArticleModel) -> list[FabricType]:
    """Every fabric type value with its colours and default colour, per type/colour property pair."""
    out: list[FabricType] = []
    types = fabric_types(model)
    for colour in fabric_colours(model):
        prefix = re.split(r"fabric", colour.name, flags=re.IGNORECASE)[0].lower()
        owner = next((t for t in types if t.name.lower().startswith(prefix)), types[0])
        allowed = colour.allowed_keys
        values = [v for v in colour.values if allowed is None or v.key in allowed]
        for type_value in owner.values:
            members = [v for v in values if type_value.value in _types_of_colour(v, owner.name)]
            default = next((v.value for v in members if v.is_default), members[0].value if members else None)
            out.append(FabricType(owner.name, colour.name, type_value.value,
                                  tuple(v.value for v in members), default))
    return out


def constrained_to_default(candidates: Sequence[m.ValueDef]) -> list[m.ValueDef]:
    """The default colour among relation-valid ``candidates``: the flagged ``is_default`` one if any, else the first.

    ``candidates`` are already filtered by the colours' relations and are in OCD source order
    (``pos_pval``), so "first" is the first colour valid for the current configuration.
    """
    flagged = next((v for v in candidates if v.is_default), None)
    return [flagged if flagged is not None else candidates[0]] if candidates else []
