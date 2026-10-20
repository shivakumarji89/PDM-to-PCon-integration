"""Evidence-backed rules for a new polymorphic property (decisions D2, D4, D6). Pure, writes nothing.

Verified against the real repository (read-only survey, 50 series, 1,893 go_types rows):

* Bit 4 ("controls the variant code") is set on 0 rows and is therefore always refused.
* Bit 2048 is documented for ``na``/``fn`` only; it is refused for ``ch`` (unresolved in Metatype.md section 6).
* Bits 128 (sort order, ``go_proporder``) and 8192 (validity, ``go_propvalues``) are *not* consistently paired
  with their tables in practice (134 of 180 ``ch`` properties with bit 128 have no ``go_proporder`` row for any
  of their values), so pairing is a policy, not a data fact.
* Every polymorphic selector (a property with more than one distinct value) is format ``ch``.
* A selector's ``default`` is one of its values in 139 of 174 cases, and its ``filter`` is empty in 118 of 174
  (the rest list parent property names, comma separated). Neither is a rule, so neither is invented: the default
  must be chosen explicitly and checked to be a value, the filter is optional.

The mode *policy* (base 3, +128 with sort-order rows, +8192 with validity rows) is the documented recommendation
(decision D4) and is **not confirmed**: ``ModePolicy.confirmed`` defaults to False and a writer must refuse an
unconfirmed policy. Passing a confirmed policy is the owner's decision, never made here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

BIT_EDITABLE = 1
BIT_GLOBAL_MODIFICATION = 2
BIT_VARIANT_CODE = 4          # never set in the real data
BIT_SORT_ORDER = 128
BIT_NA_FN_ONLY = 2048
BIT_VALIDITY = 8192
MODE_MAX = 0xFFFF             # go_types.mode is uint16
PROPERTY_FORMAT = "ch"
_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FIELD_FORBIDDEN = (";", '"', "\r", "\n")


@dataclass(frozen=True)
class ModePolicy:
    base: int = BIT_EDITABLE | BIT_GLOBAL_MODIFICATION      # 3: editable + global modification
    sort_bit: int = BIT_SORT_ORDER
    validity_bit: int = BIT_VALIDITY
    confirmed: bool = False                                 # owner decision D4; never assumed


@dataclass(frozen=True)
class ModeDecision:
    mode: int | None            # None when the policy breaks a verified invariant
    confirmed: bool
    problems: tuple[str, ...] = ()

    @property
    def usable(self) -> bool:
        return self.mode is not None and self.confirmed and not self.problems


def encode_mode(policy: ModePolicy, has_sort_order: bool, has_validity: bool) -> ModeDecision:
    """Compute the mode for a ``ch`` selector; a verified-invariant violation yields ``mode=None``."""
    problems: list[str] = []
    mode = policy.base
    if has_sort_order:
        mode |= policy.sort_bit
    if has_validity:
        mode |= policy.validity_bit
    invalid = False
    if mode & BIT_VARIANT_CODE:
        problems.append("Bit 4 is set on 0 of 1,893 real go_types rows and is refused.")
        invalid = True
    if mode & BIT_NA_FN_ONLY:
        problems.append("Bit 2048 is documented for na/fn properties only and is refused for ch.")
        invalid = True
    if not 0 <= mode <= MODE_MAX:
        problems.append(f"Mode {mode} does not fit the uint16 schema field.")
        invalid = True
    if not policy.confirmed:
        problems.append("The mode policy is a recommendation the owner has not confirmed (decision D4).")
    return ModeDecision(None if invalid else mode, policy.confirmed, tuple(problems))


@dataclass(frozen=True)
class PropertyFormat:
    format: str
    default: str
    filter: str
    problems: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return not self.problems


def build_property_format(values: list[str], default: str | None, filter_names: str = "") -> PropertyFormat:
    """Format ``ch`` with an explicit default that is one of the values and an optional filter."""
    problems: list[str] = []
    clean = [v.strip(" \t") for v in values if v and v.strip(" \t")]
    if len(set(clean)) < 2:
        problems.append("A polymorphic selector needs at least two distinct values.")
    for value in clean:
        if any(c in value for c in _FIELD_FORBIDDEN) or value.startswith("#"):
            problems.append(f"Value {value!r} contains the delimiter, a quote, a line break or starts with '#'.")
    chosen = (default or "").strip(" \t")
    if not chosen:
        problems.append("Choose the default value explicitly; it is not assumed to be the first value.")
    elif chosen not in clean:
        problems.append(f"The default {chosen!r} is not one of the property's values.")
    names = [n.strip(" \t") for n in filter_names.split(",") if n.strip(" \t")]
    for name in names:
        if not _NAME.match(name):
            problems.append(f"Filter name {name!r} is not a property name.")
    return PropertyFormat(PROPERTY_FORMAT, chosen, ",".join(names), tuple(problems))


@dataclass
class ArticleValueTable:
    """Explicit per-article value assignment (decision D2). Never filled in or defaulted.

    ``articles`` are the listed articles (identity = article number); ``allowed_values`` the property's values;
    ``config_ids`` the article's existing ConfigID (go_articles.prm_key), which keys the go_properties row and is
    never inferred, so an article without one cannot take a value.
    """
    articles: list[str]
    allowed_values: list[str]
    config_ids: dict[str, str] = field(default_factory=dict)
    assigned: dict[str, str] = field(default_factory=dict)

    def set_value(self, article: str, value: str) -> bool:
        if article not in self.articles:
            return False
        value = value.strip(" \t")
        if value:
            self.assigned[article] = value
        else:
            self.assigned.pop(article, None)
        return True

    def problems(self) -> list[str]:
        out: list[str] = []
        if not self.articles:
            out.append("No articles are listed, so no per-article values can be assigned.")
        for stray in sorted(set(self.assigned) - set(self.articles)):
            out.append(f"{stray} is not a listed article.")
        for article in self.articles:
            value = self.assigned.get(article)
            if not value:
                out.append(f"{article}: no value assigned.")
            elif value not in self.allowed_values:
                out.append(f"{article}: {value!r} is not one of the property's values.")
            if not self.config_ids.get(article, "").strip(" \t"):
                out.append(f"{article}: no ConfigID (prm_key) exists; it is never inferred, so no go_properties row "
                           "can be keyed for it.")
        pairs: dict[str, set[str]] = {}
        for article in self.articles:
            config = self.config_ids.get(article, "").strip(" \t")
            if config and article in self.assigned:
                pairs.setdefault(config, set()).add(self.assigned[article])
        for config, vals in sorted(pairs.items()):
            if len(vals) > 1:
                out.append(f"ConfigID {config} is shared by articles with different values "
                           f"({', '.join(sorted(vals))}); one go_properties row cannot hold both.")
        return out

    def article_problems(self, article: str) -> list[str]:
        """The problems that concern one article (its own value/ConfigID and any ConfigID conflict it is part of)."""
        config = self.config_ids.get(article, "").strip(" 	")
        mine = []
        for problem in self.problems():
            if problem.startswith(f"{article}: ") or (config and problem.startswith(f"ConfigID {config} is shared")):
                mine.append(problem)
        return mine

    def rebuild(self, articles: list[str], allowed_values: list[str], config_ids: dict[str, str]) -> None:
        """Adopt a new article/value/ConfigID context, keeping the values already entered for articles still listed."""
        self.assigned = {a: v for a, v in self.assigned.items() if a in articles}
        self.articles, self.allowed_values, self.config_ids = list(articles), list(allowed_values), dict(config_ids)

    @property
    def complete(self) -> bool:
        return not self.problems()


def config_ids_for(result, articles: list[str]) -> dict[str, str]:
    """Existing ConfigID (prm_key) per listed article from a reconciliation; articles without one are absent."""
    column = result.roles.get("configid") if result is not None else None
    out: dict[str, str] = {}
    if column is None:
        return out
    for row in result.rows:
        if row.identity is not None and row.identity[2] in articles:
            value = row.values.get(column, "").strip(" \t")
            if value:
                out[row.identity[2]] = value
    return out
