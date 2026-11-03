"""The explicit chain the generator follows for one base article.

    Base Article -> Article Encoding -> Assigned Classes -> Properties -> Property Values

``trace_article`` reads it from the OCD dataset without enumerating anything, so every step of the pCon process
can be inspected (and tested) on its own:

1. the base article row;
2. ArtBase: which properties the article restricts and to which values;
3. article encoding, from either mechanism - the code scheme of ``ocd_article.scheme_id`` and/or *code relations*
   (type-3 actions that compute a property, e.g. ``Code = $BAN + Frame + ...``, which the scheme then reads);
4. the classes assigned to the article (``ocd_propertyclass``) and their properties;
5. each property's values after the ArtBase restriction;
6. options and finishes - OCD has no separate table for them: they are the properties of assigned classes, so
   ``FINISHES`` or option classes are covered by step 4/5 and reported by class;
7. fabric types, their colours and default colour (:mod:`services.ocd_engine.fabric`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from services.ocd_engine import fabric
from services.ocd_engine import model as m
from services.ocd_engine.codescheme_engine import CodeSchemeEncoder
from services.ocd_engine.csv_loader import OcdDataset, build_article_model


@dataclass(frozen=True)
class EncodingSource:
    scheme_id: str = ""
    scheme: str = ""                          # scheme body, "" when the article has none
    scheme_properties: tuple[str, ...] = ()   # properties the (user-defined) scheme reads
    code_relation_properties: tuple[str, ...] = ()   # properties assigned by type-3 relations ("code relations")

    @property
    def mechanisms(self) -> tuple[str, ...]:
        found = []
        if self.scheme_id and self.scheme:
            found.append("article encoding (codescheme)")
        if self.code_relation_properties:
            found.append("code relation (computed property)")
        return tuple(found) or ("none",)


@dataclass(frozen=True)
class PropertyTrace:
    key: str
    name: str
    scope: str
    offered_values: int
    all_values: int
    restricted_by_artbase: bool
    has_relations: bool


@dataclass(frozen=True)
class ClassTrace:
    name: str
    relation_count: int
    properties: tuple[PropertyTrace, ...]


@dataclass(frozen=True)
class ArticleStructure:
    article_number: str
    encoding: EncodingSource
    classes: tuple[ClassTrace, ...]
    artbase: dict
    fabrics: tuple[fabric.FabricType, ...]

    def properties(self) -> list[PropertyTrace]:
        return [p for c in self.classes for p in c.properties]


_ASSIGN = re.compile(r"^\s*([A-Za-z_][\w.]*)\s*=", re.MULTILINE)


def _code_relation_targets(model: m.ArticleModel) -> tuple[str, ...]:
    """Properties a type-3 (action) relation of the article assigns a value to."""
    refs = list(model.article_relations)
    for cls in model.classes:
        refs.extend(cls.relations)
    for prop in model.properties:
        refs.extend(prop.relations)
        for value in prop.values:
            refs.extend(value.relations)
    names = {prop.name_upper: prop.name for prop in model.properties}
    found: dict[str, str] = {}
    for ref in refs:
        if ref.rel_type == m.ACTION:
            for target in _ASSIGN.findall(ref.text):
                tail = target.rsplit(".", 1)[-1]
                if tail.upper() in names:
                    found[tail.upper()] = names[tail.upper()]
    return tuple(found.values())


def trace_article(dataset: OcdDataset, article_number: str) -> ArticleStructure | None:
    dataset._index()
    model = build_article_model(dataset, article_number)
    if model is None:
        return None
    scheme = dataset.code_scheme(model.scheme_id)
    scheme_props: tuple[str, ...] = ()
    if scheme is not None and not scheme.is_predefined:
        scheme_props = tuple(f"{c}:{n}" if c else n for c, n in CodeSchemeEncoder(scheme).referenced_properties())
    encoding = EncodingSource(
        scheme_id=model.scheme_id, scheme=scheme.scheme if scheme is not None else "",
        scheme_properties=scheme_props, code_relation_properties=_code_relation_targets(model),
    )
    classes = []
    for cls in model.classes:
        traces = []
        for key in cls.property_keys:
            prop = model.property_by_key()[key]
            allowed = prop.allowed_keys
            offered = sum(1 for v in prop.values if allowed is None or v.key in allowed)
            traces.append(PropertyTrace(
                key=key, name=prop.name, scope=prop.scope, offered_values=offered, all_values=len(prop.values),
                restricted_by_artbase=allowed is not None, has_relations=bool(prop.relations),
            ))
        classes.append(ClassTrace(cls.name, len(cls.relations), tuple(traces)))
    artbase: dict[str, tuple[str, ...]] = {}
    for row in dataset.artbase.get(article_number, []):
        artbase.setdefault(f"{row['prop_class']}:{row['property']}", ())
        artbase[f"{row['prop_class']}:{row['property']}"] += (row["prop_value"],)
    return ArticleStructure(article_number, encoding, tuple(classes), artbase, tuple(fabric.fabric_structure(model)))
