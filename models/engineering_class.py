"""EngineeringClass model.

A user-created *class* (the OCD ``tCOMd_Class`` / ``PropertyClass`` concept): a
named grouping of properties. It lives under
:class:`~models.engineering.Engineering` alongside families and property
definitions.

A class stores STRUCTURE, not per-article values. Each property inside a class
is a :class:`ClassPropertyAssignment` that declares:

* ``width`` - how many characters this property consumes from an article's
  *remaining* string (the Articles-workspace split). The per-article letters are
  sliced positionally by cumulative width, in list order (VARCOND-style).
* ``values`` - the property's :class:`ClassValue` list (``code`` -> ``value``),
  seeded from the linked PDM property and extendable manually. The sliced letter
  is matched against these codes to resolve the article's value.

Pure data - fields only, no methods, logic, validation or services.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ClassValue:
    """One value of a class property: the sliced ``code`` letter -> ``value``."""

    code: str = ""       # the letter that appears in the article's remaining
    value: str = ""      # the value name/meaning
    source: str = "pdm"  # "pdm" (seeded from PDM) | "manual" (gap-fill)


@dataclass
class ClassPropertyAssignment:
    """A property in a class: manual slice width + its code->value list."""

    property_id: str = ""
    property_name: str = ""
    width: int = 0      # chars consumed from the article's remaining (manual)
    type: str = ""      # C=character, L=length, N=number, T=Text
    usage: str = ""     # MDB Usage: Configuration | Graphic
    text_block: str = ""  # MDB Text-block (display key, e.g. Desk_Type)
    values: list[ClassValue] = field(default_factory=list)


@dataclass
class EngineeringClass:
    """A named class grouping properties (list order = slice order)."""

    id: str = ""
    name: str = ""
    properties: list[ClassPropertyAssignment] = field(default_factory=list)
