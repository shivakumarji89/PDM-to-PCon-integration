"""Engine-neutral configuration model.

The configuration engine runs on :class:`ArticleModel`. Two producers build it:
``csv_loader.build_article_model`` (OCD CSV folders) and the Snapshot adapter in
``services/article_obx`` (repository/MDB data). The engine itself imports
neither.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# relation types (OCD 2.15)
PRECONDITION = 1
SELECTION = 2
ACTION = 3
CONSTRAINT = 4
REACTION = 5
POST_REACTION = 6


@dataclass(frozen=True)
class RelationRef:
    """One relation of a relational object, bound to an entity."""

    name: str
    rel_type: int
    domain: str = "C"
    order: int = 0
    text: str = ""


@dataclass(frozen=True)
class ValueDef:
    key: str                         # unique id within the model (value id / "class:prop:value")
    value: str                       # the value relations see (OCD ``value_from``)
    code: str = ""                   # token used when encoding (defaults to ``value``)
    display: str = ""
    order: int = 0
    relations: tuple[RelationRef, ...] = ()

    @property
    def encoded(self) -> str:
        return self.code or self.value


@dataclass(frozen=True)
class PropertyDef:
    key: str                         # unique id (property id / "class:prop")
    name: str                        # the name relations use
    class_name: str = ""
    order: int = 0
    values: tuple[ValueDef, ...] = ()
    relations: tuple[RelationRef, ...] = ()
    length: int = 0
    optional: bool = False
    restrictable: bool = False
    multi_option: bool = False
    kind: str = "property"           # "property" | "option" (repository model)
    scope: str = ""                  # OCD scope: C configurable; R/RG/RV derived or read-only
    allowed_keys: frozenset[str] | None = None   # ArtBase restriction (None = unrestricted)

    @property
    def name_upper(self) -> str:
        return self.name.upper()


@dataclass(frozen=True)
class ClassDef:
    name: str
    order: int = 0
    relations: tuple[RelationRef, ...] = ()
    property_keys: tuple[str, ...] = ()


@dataclass
class ArticleModel:
    base_code: str
    article_key: str = ""
    properties: tuple[PropertyDef, ...] = ()
    classes: tuple[ClassDef, ...] = ()
    article_relations: tuple[RelationRef, ...] = ()
    tables: dict = field(default_factory=dict)       # upper-case name -> object with ``.lines``
    scheme_id: str = ""

    def property_by_key(self) -> dict[str, PropertyDef]:
        return {prop.key: prop for prop in self.properties}

    def class_by_name(self) -> dict[str, ClassDef]:
        return {cls.name.upper(): cls for cls in self.classes}


@dataclass(frozen=True)
class Assignment:
    """The state of one property in a configuration."""

    prop: PropertyDef
    value: ValueDef | None = None     # None = no value
    hidden: bool = False              # invalid / invisible because a precondition is FALSE
