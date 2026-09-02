"""OCD value combination table (see OCD 4.3 spec, section 2.21).

A :class:`ValueCombinationTable` lists all *valid* value combinations for a
defined set of properties: one logical line per combination, each line binding
each property to a value (or, for a restrictable property, a value set). It is
exported as ``<name>_tbl.csv`` (rows ``LineNr;PROPERTYNAME;VALUE``, names and
values upper case) and referenced from relationship knowledge via ``TABLE()``.

Fields only - no logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ValueCombinationTable:
    """One OCD value combination table.

    ``property_names`` is the column order (upper-case symbolic ids, ``COL_*``).
    ``access`` maps each column id to its ``TABLE()`` access parameter (the
    article property variable ``x.Prop`` or the system variable ``$BAN``).
    ``lines`` is one dict per logical line, mapping each column id to its value
    token; a value may be a single token or a list of tokens (a value set).
    ``article_class`` is the property class the ``IS_A`` constraint binds to.
    """

    name: str = ""
    article_class: str = ""
    property_names: list[str] = field(default_factory=list)
    access: dict[str, str] = field(default_factory=dict)
    lines: list[dict[str, object]] = field(default_factory=list)
