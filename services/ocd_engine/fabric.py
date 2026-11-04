"""Fabric properties of an article: types, their colours and the default colour per type.

OCD has no dedicated fabric marker. First discover fabric-related property candidates by searching the simple
keywords "fabric" or "upholstery" (not complete phrases such as "Fabric Type" or "Fabric Colour"). The current
engine model exposes property names; translated Property-text labels must be added by the data adapter when
available. Candidate discovery is separate from deciding which candidate is the type and which is the colour.
The type/colour relationship and validity must be established from class association and OCD relations. The
default colour is chosen per configuration by the engine: first valid after relation evaluation in ``pos_pval``
order (a valid ``is_default`` value wins).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from services.ocd_engine import model as m
from services.ocd_engine import relation_parser as rp

# Discovery deliberately uses keyword hits only. Do not require "type", "colour", or
# "color" in the property name; e.g. Tun's type property is Upholstered_Base_Fabric.
_FABRIC_HINT = re.compile(r"fabric|upholstery|upholster", re.IGNORECASE)


def fabric_candidates(model: m.ArticleModel) -> list[m.PropertyDef]:
    """Properties whose names contain a fabric/upholstery keyword.

    This is candidate discovery only. Relationship analysis must establish the
    type/colour roles; a keyword hit alone must not force SKU reduction.
    """
    return [p for p in model.properties if _FABRIC_HINT.search(p.name)]


def fabric_types(model: m.ArticleModel) -> list[m.PropertyDef]:
    """Compatibility helper for legacy callers; type role is currently name-derived."""
    return [p for p in fabric_candidates(model) if re.search(r"type", p.name, re.IGNORECASE)]


def fabric_colours(model: m.ArticleModel) -> list[m.PropertyDef]:
    """Compatibility helper for legacy callers; colour role is currently name-derived."""
    return [p for p in fabric_candidates(model) if re.search(r"colou?r", p.name, re.IGNORECASE)] if fabric_types(model) else []


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
