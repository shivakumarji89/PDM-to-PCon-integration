"""OBX *input* serialization helpers, kept apart from final-article encoding.

``ofmlvarcode`` is the OFML property assignment string pCon consumes
(``Class.Property=Value;...``). In every reference file it lists the
configurable (scope ``C``) properties that currently have a value, in
class/property order; hidden or unset properties are omitted. (Evidence:
Dalby 1,242/1,242 and Lino; ``scope C <=> flags="1"`` is a hypothesis beyond
those two programs.)
"""
from __future__ import annotations

from typing import Sequence

from services.ocd_engine import model as m


def ofml_varcode(assignments: Sequence[m.Assignment], model: m.ArticleModel | None = None) -> str:
    """``Class.Property=Value;...`` for configurable properties with a value."""
    order = {p.key: i for i, p in enumerate(model.properties)} if model is not None else {}
    chosen = [
        a for a in assignments
        if a.value is not None and not a.hidden and a.prop.scope.upper() == "C"
    ]
    chosen.sort(key=lambda a: order.get(a.prop.key, a.prop.order))
    return ";".join(f"{a.prop.class_name}.{a.prop.name}={a.value.value}" for a in chosen)
