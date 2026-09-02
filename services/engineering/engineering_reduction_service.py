"""Engineering reduction engine.

Reads the Engineering Property Management data (property definitions, members
and their assignments) and identifies members that share an identical
engineering signature, grouping them into reduction groups.

As part of processing it builds an **internal** normalized matrix (one row per
member, one column per property, ordered by ``PropertyDefinition.order``). That
matrix is an implementation detail - it is a local structure only and is never
exposed as a domain model.

The engine is strictly read-only: it never mutates Engineering, members, or
assignments. It performs no validation, generation, or synchronization.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from uuid import uuid4

from models.article_set import ArticleSet, SetAttribute, SetValue
from models.member_article import MemberArticle
from models.snapshot import Snapshot
from services.base_service import BaseService
from services.engineering.engineering_repository import EngineeringRepository

#: Separator used between property values when building a signature. It is a
#: control character (unit separator) that does not occur in engineering values.
SIGNATURE_SEPARATOR = "\x1f"


@dataclass(frozen=True)
class ReductionGroup:
    """A set of members that share one identical engineering signature.

    Each group carries a stable ``id`` (a fresh UUID generated on creation);
    consumers should identify a group by its ``id`` rather than its signature.
    The signature remains the internal grouping key.
    """

    signature: str
    members: tuple[MemberArticle, ...] = ()
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass(frozen=True)
class ReductionResult:
    """Read-only result of a reduction: the complete set of reduction groups."""

    groups: tuple[ReductionGroup, ...] = ()


@dataclass(frozen=True)
class BaseArticleGroup:
    """Members sharing one Base Article (the ``reduced_article`` prefix).

    The base is an aggregation node, not a lossy collapse: it holds every member
    line item plus the UNION of their property-value links (from
    ``snapshot.article_property_value_ids``) and the per-value member coverage
    (value id -> how many members carry it), so downstream class generation
    keeps full fidelity.
    """

    base: str
    members: tuple[MemberArticle, ...] = ()
    property_value_ids: tuple[str, ...] = ()
    value_coverage: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass(frozen=True)
class PropertyClass:
    """Articles that share an identical PROPERTY SIGNATURE.

    The signature is the set of attributes each article carries, with each
    attribute's dependency flag (PDM ``HasDependentOptions``). Articles whose
    property set differs - e.g. a back-to-back desk (both A and B sides) versus a
    single desk (A side only) - form separate classes. Read-only aggregation.
    """

    signature: tuple[tuple[str, int], ...] = ()
    property_names: tuple[str, ...] = ()
    article_ids: tuple[str, ...] = ()
    id: str = field(default_factory=lambda: uuid4().hex)


@dataclass(frozen=True)
class BaseMasterSet:
    """Articles that share ONE base article number, merged across property
    structures.

    Two property-structure classes that reduce to the SAME base (same base
    length + same prefix) are one master article; the properties only some of
    them carry become ``optional_property_names`` (relation-gated, e.g. an
    Always Chair's optional ``Height adjustable``). Read-only aggregation.
    """

    base: str = ""
    base_length: int = 0
    article_ids: tuple[str, ...] = ()
    property_names: tuple[str, ...] = ()        # union across variants
    optional_property_names: tuple[str, ...] = ()  # not carried by every variant
    id: str = field(default_factory=lambda: uuid4().hex)


def collapse_duplicate_values(values, code_of):
    """Drop redundant same-name value rows, keeping the coded one.

    PDM defines some attribute values once per product sub-series, so the
    family-wide union carries the same value under several ``AttributeValueId``s.
    The names may match exactly (``Sled Base`` twice on ``Type``) or differ only
    in case/spacing (``Sled Base`` vs ``Sled base`` on ``Series``); both are
    treated as one value via a case- and punctuation-insensitive key. Only the id
    whose article position resolves gets a code; its twin is noise. Rule per name
    (input order preserved): keep one row for every distinct non-empty code; if
    any coded row exists, drop the name's code-less rows; if none is coded, keep
    the first row. Genuinely distinct codes on one name (e.g. two ``4 Star Swivel
    Base`` mapping to 5 and 6) are all kept.

    ``code_of(value) -> str`` yields a value's effective code (stored or decoded).
    """
    coded_names: dict[str, set] = {}
    for value in values:
        code = (code_of(value) or "").strip()
        if code:
            coded_names.setdefault(normalize_value_name(value.value), set()).add(code)
    kept = []
    seen: set = set()
    for value in values:
        name = normalize_value_name(value.value)
        code = (code_of(value) or "").strip()
        if code:
            key = (name, code)
        elif name in coded_names:
            continue  # code-less twin of a resolved value
        else:
            key = (name, "")
        if key in seen:
            continue  # same name+code already shown
        seen.add(key)
        kept.append(value)
    return kept


_VALUE_NAME_NOISE = re.compile(r"[^0-9a-z]+")


def normalize_value_name(text: str) -> str:
    """Case- and punctuation-insensitive key so ``Sled Base`` == ``Sled base``."""
    return _VALUE_NAME_NOISE.sub(" ", (text or "").casefold()).strip()


class EngineeringReductionService(BaseService):
    """Group members by identical engineering signature (read-only)."""

    def reduce(self, snapshot: Snapshot | None) -> ReductionResult:
        """Build the internal matrix and return the reduction groups.

        Columns are the property definitions ordered by ``order`` (then id);
        rows are the members. A missing assignment contributes an empty value.
        Members whose ordered values are identical share a signature and land in
        the same group. Group and member order follow member traversal order.
        """
        repository = self._repository()
        columns = sorted(
            repository.get_properties(snapshot), key=lambda p: (p.order, p.id)
        )
        column_ids = [definition.id for definition in columns]

        groups: dict[str, list[MemberArticle]] = {}
        for member in repository.get_members(snapshot):
            # One row of the internal matrix: the member's value per column, in
            # column order, with missing assignments as empty values.
            values = []
            for property_id in column_ids:
                assignment = repository.find_assignment(member, property_id)
                values.append(assignment.value if assignment is not None else "")
            signature = SIGNATURE_SEPARATOR.join(values)
            groups.setdefault(signature, []).append(member)

        return ReductionResult(
            groups=tuple(
                ReductionGroup(signature=signature, members=tuple(members))
                for signature, members in groups.items()
            )
        )

    def group_by_base(self, snapshot: Snapshot | None) -> tuple[BaseArticleGroup, ...]:
        """Group members by Base Article (``reduced_article``), aggregating the
        UNION of each member's property-value links with per-value coverage.

        Read-only. Members not yet reduced (empty ``reduced_article``) are
        skipped. Group and member order follow member traversal order.
        """
        if snapshot is None:
            return ()
        apv = getattr(snapshot, "article_property_value_ids", {}) or {}
        order: list[str] = []
        members_by_base: dict[str, list[MemberArticle]] = {}
        coverage_by_base: dict[str, dict[str, int]] = {}
        for member in self._repository().get_members(snapshot):
            base = (getattr(member, "reduced_article", "") or "").strip()
            if not base:
                continue
            if base not in members_by_base:
                members_by_base[base] = []
                coverage_by_base[base] = {}
                order.append(base)
            members_by_base[base].append(member)
            coverage = coverage_by_base[base]
            for value_id in apv.get(str(getattr(member, "article_id", "")), []):
                coverage[value_id] = coverage.get(value_id, 0) + 1
        return tuple(
            BaseArticleGroup(
                base=base,
                members=tuple(members_by_base[base]),
                property_value_ids=tuple(coverage_by_base[base].keys()),
                value_coverage=dict(coverage_by_base[base]),
            )
            for base in order
        )

    def classify_by_properties(
        self, snapshot: Snapshot | None
    ) -> tuple[PropertyClass, ...]:
        """Classify articles by the SET of properties (attributes) they carry.

        Each article inherits its product's property set: the signature is the
        set of ``(attribute name, dependency flag)`` on the article's product
        (from PDM ``ProductAttributeValues`` via
        ``snapshot.product_property_value_ids``). Articles whose products share
        an identical property set land in the same :class:`PropertyClass`; a
        different set (more, fewer or different attributes) forms a separate
        class - so a back-to-back desk and a single desk are classified apart.
        Read-only; largest first.
        """
        if snapshot is None:
            return ()
        value_prop: dict[str, tuple[str, int]] = {}
        for prop in snapshot.properties:
            entry = (str(prop.name), int(bool(prop.has_dependent_options)))
            for value in prop.values:
                value_prop[str(value.id)] = entry
        product_values = getattr(snapshot, "product_property_value_ids", {}) or {}
        signature_by_product: dict[str, tuple] = {}
        for product_id, value_ids in product_values.items():
            signature_by_product[str(product_id)] = tuple(
                sorted({value_prop[str(vid)] for vid in value_ids if str(vid) in value_prop})
            )
        groups: dict[tuple, list[str]] = {}
        for article in snapshot.articles:
            article_id = str(getattr(article, "id", "") or "")
            product_id = str(getattr(article, "product_id", "") or "")
            signature = signature_by_product.get(product_id, ())
            groups.setdefault(signature, []).append(article_id)
        classes = [
            PropertyClass(
                signature=signature,
                property_names=tuple(name for name, _flag in signature),
                article_ids=tuple(ids),
            )
            for signature, ids in groups.items()
        ]
        return tuple(sorted(classes, key=lambda c: len(c.article_ids), reverse=True))

    def merge_sets_by_base(
        self, snapshot: Snapshot | None
    ) -> tuple[BaseMasterSet, ...]:
        """Merge property-structure classes that share the SAME base article
        number into one master per base.

        Groups every article by its base (``code[:base_length]``, base length
        from the materialised ``article_sets``). Classes that reduce to the same
        base become one :class:`BaseMasterSet`; a property carried by only some
        of that base's variants is reported in ``optional_property_names``.
        Bases with a genuinely different reduced number stay separate (matching
        the rule: merge only when the base article number is identical). Ordered
        largest first. Read-only.
        """
        if snapshot is None:
            return ()
        code_of = {str(a.id): (a.code or "") for a in snapshot.articles}
        set_len = {
            frozenset(str(a) for a in s.article_ids): s.base_length
            for s in (getattr(snapshot, "article_sets", None) or [])
        }
        classes = self.classify_by_properties(snapshot)

        # base -> {"ids": set, "len": int, "props": list[frozenset]}
        by_base: dict[str, dict] = {}
        for cls in classes:
            ids = frozenset(str(a) for a in cls.article_ids)
            base_len = set_len.get(ids)
            if base_len is None:  # not materialised: fall back to full length
                base_len = max(
                    (len(code_of.get(str(a), "")) for a in cls.article_ids),
                    default=0,
                )
            props = frozenset(cls.property_names)
            for aid in cls.article_ids:
                base = code_of.get(str(aid), "")[:base_len]
                entry = by_base.setdefault(
                    base, {"ids": [], "len": base_len, "props": []}
                )
                entry["ids"].append(str(aid))
                if props not in entry["props"]:
                    entry["props"].append(props)

        masters: list[BaseMasterSet] = []
        for base, entry in by_base.items():
            variant_propsets = entry["props"]
            union: set[str] = set().union(*variant_propsets) if variant_propsets else set()
            common: set[str] = (
                set.intersection(*[set(p) for p in variant_propsets])
                if variant_propsets else set()
            )
            masters.append(
                BaseMasterSet(
                    base=base,
                    base_length=entry["len"],
                    article_ids=tuple(entry["ids"]),
                    property_names=tuple(sorted(union)),
                    optional_property_names=tuple(sorted(union - common)),
                )
            )
        masters.sort(key=lambda m: len(m.article_ids), reverse=True)
        return tuple(masters)

    def materialize_article_sets(
        self, snapshot: Snapshot | None
    ) -> list[ArticleSet]:
        """Build and store ``snapshot.article_sets`` from the product links.

        For every property class (see :meth:`classify_by_properties`) records
        the set's articles, its base length (the article code length minus the
        sum of the applicable properties' widths - coded value codes AND
        dependency counts) and, for each property and option the set carries,
        that attribute's values with the exact articles that carry each value (a
        value may apply to only part of the set). Read of source links only;
        writes just ``snapshot.article_sets``.
        """
        if snapshot is None:
            return []
        classes = self.classify_by_properties(snapshot)
        # value id -> (attribute id, attribute name, value name, code)
        prop_value: dict[str, tuple[str, str, str, str]] = {}
        for prop in snapshot.properties:
            for value in prop.values:
                prop_value[str(value.id)] = (
                    str(prop.id), prop.name or "", value.value or "", value.code or ""
                )
        option_value: dict[str, tuple[str, str, str, str]] = {}
        for option in snapshot.options:
            for value in option.values:
                option_value[str(value.id)] = (
                    str(option.id), option.name or "",
                    value.value or "", value.code or ""
                )
        product_props = getattr(snapshot, "product_property_value_ids", {}) or {}
        product_options = getattr(snapshot, "product_option_value_ids", {}) or {}
        product_of = {
            str(a.id): str(getattr(a, "product_id", "") or "") for a in snapshot.articles
        }
        code_of = {str(a.id): (a.code or "") for a in snapshot.articles}

        # Per-property slice width = the STORED code length (OrderCodeValue) - the
        # only consistent, 100% definition for the parametric TAIL. Head config
        # properties have no stored code; their width/position come from the
        # value-id head decoder instead (see head_layout below).
        prop_width: dict[str, int] = {}
        for prop in snapshot.properties:
            codes = [(v.code or "").strip() for v in prop.values]
            if any(codes):
                prop_width[str(prop.id)] = max(
                    (len(c) for c in codes if c), default=0
                )
            else:
                prop_width[str(prop.id)] = 0  # head config: no stored code

        # Head config codes (Type/Fabrics/... no stored code) are appended to the
        # base article number $BAN (PDM A_CODE: Code = $BAN + head codes + '.' +
        # tail codes). The value-id decoder reports each head config property's
        # head position; $BAN ends at the earliest such position, so slicing them
        # off leaves the short base line.
        try:
            head_layout = self.context.engineering_class_service.config_code_layout(
                snapshot
            )
        except Exception:
            head_layout = {}

        sets: list[ArticleSet] = []
        for pc in classes:
            article_ids = [str(a) for a in pc.article_ids]
            properties = self._set_attributes(
                article_ids, product_of, product_props, prop_value
            )
            options = self._set_attributes(
                article_ids, product_of, product_options, option_value
            )
            # Base length: if any head config property has a decoded head
            # position, $BAN ends at the earliest one (head codes + tail are
            # stripped together). Otherwise fall back to the tail-only rule
            # (full code length minus the coded tail widths).
            head_positions = [
                head_layout[str(a.id)]["position"]
                for a in properties
                if str(a.id) in head_layout
                and head_layout[str(a.id)].get("width", 0)
            ]
            if head_positions:
                base_length = max(min(head_positions), 0)
            else:
                code_len = max(
                    (len(code_of.get(a, "")) for a in article_ids), default=0
                )
                config_width = sum(
                    prop_width.get(str(a.id), 0) for a in properties
                )
                base_length = max(code_len - config_width, 0)
            # Base code = the article number shown only as far as the group's
            # codes are the SAME value (common prefix), never beyond the derived
            # base length. This is the shared "base article" for the set.
            codes = [code_of.get(a, "") for a in article_ids]
            base_n = min(base_length, self._common_prefix_len(codes))
            base_code = next((c for c in codes if c), "")[:base_n]
            sets.append(
                ArticleSet(
                    id=pc.id,
                    base_length=base_length,
                    base_code=base_code,
                    article_ids=article_ids,
                    properties=properties,
                    options=options,
                )
            )
        snapshot.article_sets = sets
        return sets

    @staticmethod
    def _set_attributes(
        article_ids: list[str],
        product_of: dict[str, str],
        product_value_ids: dict[str, list[str]],
        value_lookup: dict[str, tuple[str, str, str, str]],
    ) -> list[SetAttribute]:
        """Group the set's carried values by attribute, tracking which articles
        carry each value (first-seen order, unique)."""
        # attribute id -> (name, {value id -> [article ids]})
        by_attribute: dict[str, tuple[str, dict[str, list[str]]]] = {}
        order: list[str] = []
        for article_id in article_ids:
            product_id = product_of.get(article_id, "")
            for value_id in product_value_ids.get(product_id, []):
                info = value_lookup.get(str(value_id))
                if info is None:
                    continue
                attribute_id, attribute_name, _value_name, _code = info
                if attribute_id not in by_attribute:
                    by_attribute[attribute_id] = (attribute_name, {})
                    order.append(attribute_id)
                values = by_attribute[attribute_id][1]
                carriers = values.setdefault(str(value_id), [])
                if article_id not in carriers:
                    carriers.append(article_id)
        attributes: list[SetAttribute] = []
        for attribute_id in order:
            attribute_name, values = by_attribute[attribute_id]
            set_values = [
                SetValue(
                    id=value_id,
                    value=value_lookup[value_id][2],
                    code=value_lookup[value_id][3],
                    article_ids=carriers,
                )
                for value_id, carriers in values.items()
            ]
            attributes.append(
                SetAttribute(id=attribute_id, name=attribute_name, values=set_values)
            )
        return attributes

    @staticmethod
    def _common_prefix_len(codes: list[str]) -> int:
        """Longest common prefix length across non-empty codes (the shared base)."""
        codes = [c for c in codes if c]
        if not codes:
            return 0
        prefix = codes[0]
        for code in codes[1:]:
            limit = min(len(prefix), len(code))
            index = 0
            while index < limit and prefix[index] == code[index]:
                index += 1
            prefix = prefix[:index]
            if not prefix:
                return 0
        return len(prefix)

    def _repository(self) -> EngineeringRepository:
        """Reuse the context's engineering repository, else a stateless one."""
        repository = getattr(self.context, "engineering_repository", None)
        if repository is None:
            repository = EngineeringRepository(self.context)
        return repository
