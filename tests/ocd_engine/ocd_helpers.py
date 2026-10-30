"""Tiny builders shared by the OCD engine tests (no application imports)."""
from __future__ import annotations

import dataclasses

from services.ocd_engine import model as m
from services.ocd_engine.configuration_engine import ConfigurationEngine

REAL_OCD_ROOT = "C:/HermanMillerOFMLSVN/Staging/HermanMiller/_repository/hmx"
OBX_REFERENCE_DIR = "C:/Users/siaoca/Downloads/Dalby_OBX_Files"


def rel(text, rel_type=1, domain="C", name=None, order=0):
    return m.RelationRef(name=name or f"R{abs(hash((text, rel_type, domain))) % 10000}",
                         rel_type=rel_type, domain=domain, order=order, text=text)


def val(value, code=None, rels=()):
    return m.ValueDef(key=f"v:{value}", value=value, code=code if code is not None else value,
                      relations=tuple(rels))


def prop(name, values=(), *, cls="CLS", rels=(), scope="C", optional=False, length=0, allowed=None):
    vals = tuple(v if isinstance(v, m.ValueDef) else val(v) for v in values)
    return m.PropertyDef(key=f"{cls}:{name}", name=name, class_name=cls, values=vals,
                         relations=tuple(rels), scope=scope, optional=optional, length=length,
                         allowed_keys=frozenset(f"v:{a}" for a in allowed) if allowed is not None else None)


def model(base, props, article_relations=(), classes=(), tables=None):
    ordered = tuple(dataclasses.replace(p, order=i) for i, p in enumerate(props))
    return m.ArticleModel(base_code=base, properties=ordered, classes=tuple(classes),
                          article_relations=tuple(article_relations), tables=tables or {})


def run(mdl, **kwargs):
    """All valid configurations as ``[(Configuration, FinalResult)]`` plus the engine."""
    engine = ConfigurationEngine(mdl, **kwargs)
    return list(engine.generate()), engine


def chosen(config):
    """``{property: value}``; hidden properties map to ``'<hidden>'``, unset to ``None``."""
    return {a.prop.name: ("<hidden>" if a.hidden else (a.value.value if a.value else None))
            for a in config.assignments}
