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
from typing import Any
from uuid import uuid4

from models.article_set import ArticleSet, SetAttribute, SetValue
from models.member_article import MemberArticle
from models.snapshot import Snapshot
from services.base_service import BaseService
from services.engineering.engineering_repository import EngineeringRepository
from services.engineering.candidate_strategy_service import PRIMARY_STRATEGY, STRATEGY_ORDER
from services.engineering.pdm_family_reduction_service import FamilyCandidate

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
    product_range: str = ""
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


@dataclass(frozen=True)
class CandidateFamily:
    """One candidate family as presented to the legacy boundary.

    It is an :class:`ArticleSet` - the grouping this engine already derived -
    carrying the single ProductRange it belongs to, because ``ProductsList``
    is ProductRange-scoped and cannot answer a question that spans ranges.
    Sets are classified per range to begin with, so this is a label on the
    boundary's own scope, not a regrouping rule: articles are never moved
    between sets and no set is merged with another.
    """

    set_id: str = ""
    base_code: str = ""
    #: The snapshot's ProductRange NAME this candidate covers ("" when the
    #: snapshot carries no range for these products, or when the caller asked
    #: for the set unlabelled).
    product_range: str = ""
    product_ids: tuple[str, ...] = ()
    article_ids: tuple[str, ...] = ()
    #: Which rule proposed this grouping - ``"primary"`` for the property
    #: structure classes this engine derives, otherwise a strategy name from
    #: :data:`~services.engineering.candidate_strategy_service.STRATEGY_ORDER`.
    #: The primary grouping always outranks a fallback (see
    #: :meth:`EngineeringReductionService.apply_validated_reduction`).
    strategy: str = PRIMARY_STRATEGY
    #: Why a fallback proposed this grouping; empty for the primary grouping.
    strategy_reason: str = ""


@dataclass(frozen=True)
class ArticleSetValidation:
    """The legacy verdict on ONE candidate family (one :class:`ArticleSet`).

    ``status`` is the validator's own verdict, passed through unchanged:

    ``validated``
        ``ProductsList``, given the set's common functional (non-order-code)
        AttributeValueIds, returned exactly the set's ProductIds. The reduced
        base is legacy-equivalent.
    ``rejected``
        It returned a different ProductId set - see ``missing_from_filter`` /
        ``extra_in_filter``. The reduced base is NOT legacy-equivalent.
    ``unresolved``
        No verdict was possible (a single-Product set, a set spanning several
        ProductRanges, a US range, no shared functional value, or a
        ProductRange the snapshot holds only part of - ``ProductsList`` filters
        the whole range, so a partial population cannot be compared against it).
        Explicitly not a pass.
    ``error``
        The check itself failed; ``reason`` carries the exception. Never a pass.
    """

    set_id: str = ""
    base_code: str = ""
    #: The snapshot ProductRange name this verdict covers (see
    #: :class:`CandidateFamily`); "" when the set was not sliced by range.
    product_range: str = ""
    product_ids: tuple[str, ...] = ()
    #: The articles the judged candidate covers. Carried on the verdict so the
    #: apply step never has to re-derive the candidates and risk pairing a
    #: verdict with a different grouping than the one that was judged.
    article_ids: tuple[str, ...] = ()
    #: The rule that proposed the judged grouping (see
    #: :attr:`CandidateFamily.strategy`).
    strategy: str = PRIMARY_STRATEGY
    strategy_reason: str = ""
    status: str = "unresolved"
    reason: str = ""
    product_range_id: Any = None
    #: The range's ProductCategoryId - what a US range is keyed by, so a
    #: US ``unresolved`` verdict names the category it could not be proven in.
    product_category_id: Any = None
    functional_attribute_value_ids: tuple[str, ...] = ()
    filtered_product_ids: tuple[str, ...] = ()
    missing_from_filter: tuple[str, ...] = ()
    extra_in_filter: tuple[str, ...] = ()
    #: Over-matched Products the snapshot never loaded - only a live
    #: ``ProductsList`` call can reveal these, since the snapshot holds just the
    #: requested Products, not the whole ProductRange.
    extra_outside_snapshot: tuple[str, ...] = ()
    #: Whether the snapshot holds the COMPLETE legacy-eligible population of the
    #: resolved ProductRange. ``False`` means a snapshot-local emulation of
    #: ``ProductsList`` would be blind to part of the range.
    snapshot_covers_range: bool | None = None
    unloaded_range_product_count: int = 0

    @property
    def is_legacy_equivalent(self) -> bool:
        """Only an explicit ``validated`` counts; everything else does not."""
        return self.status == "validated"

    @property
    def makes_legacy_claim(self) -> bool:
        """Whether collapsing this candidate asserts anything legacy PDM can
        judge.

        Collapsing the articles of ONE Product onto one base is not a
        cross-Product family claim - there is no selector that could select a
        different Product set - so ``ProductsList`` has nothing to prove. Two
        or more Products is a family claim and must be proven.
        """
        return len(self.product_ids) >= 2

    @property
    def blocks_reduction(self) -> bool:
        """``True`` when this candidate must NOT collapse.

        A family claim that is anything other than ``validated`` - rejected,
        unresolved, or un-checkable (``error``) - is blocked. Absence of proof
        is never taken as proof.
        """
        return self.makes_legacy_claim and not self.is_legacy_equivalent


@dataclass(frozen=True)
class ReductionApplication:
    """What the enforced reduction actually did.

    ``validations`` carries every verdict, including the ones that blocked a
    collapse, so a caller never has to infer why a family stayed expanded.
    """

    validations: tuple[ArticleSetValidation, ...] = ()
    applied_article_ids: tuple[str, ...] = ()
    blocked_article_ids: tuple[str, ...] = ()
    applied_members: int = 0
    blocked_members: int = 0

    @property
    def applied_candidates(self) -> tuple[ArticleSetValidation, ...]:
        return tuple(v for v in self.validations if not v.blocks_reduction)

    @property
    def blocked_candidates(self) -> tuple[ArticleSetValidation, ...]:
        return tuple(v for v in self.validations if v.blocks_reduction)


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
        """Classify articles by the property IDs actually carried by each PDM Item.

        PDM has two levels of attribute assignment:
        ProductAttributeValues is the product-level fallback, while
        BaseAttributeValues is the concrete Item-level selection. The Item-level
        rows are authoritative for reduction because variants such as single
        versus back-to-back can carry different property sides.
        """
        if snapshot is None:
            return ()
        value_prop: dict[str, tuple[str, int]] = {}
        for prop in snapshot.properties:
            entry = (str(prop.name), int(bool(prop.has_dependent_options)))
            for value in prop.values:
                value_prop[str(value.id)] = entry

        product_values = getattr(snapshot, "product_property_value_ids", {}) or {}
        article_values = getattr(snapshot, "article_property_value_ids", {}) or {}
        range_of = getattr(snapshot, "product_range", {}) or {}

        groups: dict[tuple, list[str]] = {}
        for article in snapshot.articles:
            article_id = str(getattr(article, "id", "") or "")
            product_id = str(getattr(article, "product_id", "") or "")

            # BaseAttributeValues are the concrete PDM Item truth. When
            # Item-level rows exist, use that complete selection as the
            # signature. ProductAttributeValues are only the fallback for Items
            # for which PDM supplied no BaseAttributeValues at all.
            selected_ids = [str(v) for v in article_values.get(article_id, [])]
            product_ids = [str(v) for v in product_values.get(product_id, [])]

            selected_signature = {
                value_prop[v] for v in selected_ids if v in value_prop
            }
            product_signature = {
                value_prop[v] for v in product_ids if v in value_prop
            }
            signature = tuple(
                sorted(selected_signature if selected_ids else product_signature)
            )
            scope = str(range_of.get(product_id, "") or "")
            groups.setdefault((scope, signature), []).append(article_id)

        classes = [
            PropertyClass(
                signature=signature,
                property_names=tuple(name for name, _flag in signature),
                article_ids=tuple(ids),
                product_range=scope,
            )
            for (scope, signature), ids in groups.items()
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
        for option in getattr(snapshot, "options", []) or []:
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

        # Head config codes are needed only when PDM did NOT provide an
        # authoritative article prefix length. Do not decode the entire
        # configuration matrix up front when every loaded Item already has the
        # PDM prefix; that decoder can be expensive because it examines the
        # complete property/value vocabulary, even for a tiny article selection.
        # The decoder remains available lazily for the heuristic fallback below.
        head_layout: dict = {}
        sets: list[ArticleSet] = []
        for pc in classes:
            article_ids = [str(a) for a in pc.article_ids]
            properties = self._set_attributes(
                article_ids,
                product_of,
                product_props,
                prop_value,
                article_value_ids=getattr(snapshot, "article_property_value_ids", {}) or {},
            )
            options = self._set_attributes(
                article_ids, product_of, product_options, option_value
            )
            # Manual Class Creation values are an engineering-side overlay.
            # They are resolved only after the base length is known.
            # PDM getArticlePrefixLength is authoritative for the fixed
            # article prefix. Use the per-Item value when available; do not infer
            # the base by character heuristics when PDM already supplied it.
            pdm_prefixes = [
                int(getattr(snapshot, "article_prefix_length", {}).get(a, 0) or 0)
                for a in article_ids
                if a in getattr(snapshot, "article_prefix_length", {})
            ]
            override_lengths = [
                int(getattr(snapshot, "base_length_overrides", {}).get(code_of.get(a, ""), 0) or 0)
                for a in article_ids
                if code_of.get(a, "") in getattr(snapshot, "base_length_overrides", {})
            ]
            if override_lengths:
                base_length = min(override_lengths)
            elif pdm_prefixes:
                # PDM's getArticlePrefixLength is authoritative when it is
                # available for these Items.
                base_length = min(pdm_prefixes)
            else:
                # Only the heuristic path needs decoded head positions. Most
                # PDM loads supply article_prefix_length, so avoid doing this
                # work entirely for the normal path.
                if not head_layout:
                    try:
                        head_layout = self.context.engineering_class_service.config_code_layout(
                            snapshot
                        )
                    except Exception:
                        head_layout = {}
                ignored = getattr(snapshot, "config_ignore_overrides", {}) or {}

                # A head property is part of the base when its value is
                # constant across the set. The first NON-ignored head property
                # whose value varies is where the configurable portion starts.
                # This is data-driven: it does not assume fixed character
                # positions for a particular product family.
                varying_head_positions = [
                    int(head_layout[str(prop.id)].get("position", 0) or 0)
                    for prop in properties
                    if str(prop.id) in head_layout
                    and head_layout[str(prop.id)].get("width", 0)
                    and ignored.get(str(prop.id)) is not True
                    and any(
                        len({str(v.id) for v in attr.values}) > 1
                        for attr in properties
                        if str(attr.id) == str(prop.id)
                    )
                ]

                if varying_head_positions:
                    base_length = min(varying_head_positions)
                else:
                    ignored_end_positions = [
                        int(head_layout[str(prop.id)].get("position", 0) or 0)
                        + int(head_layout[str(prop.id)].get("width", 0) or 0)
                        for prop in properties
                        if ignored.get(str(prop.id)) is True
                        and str(prop.id) in head_layout
                        and head_layout[str(prop.id)].get("width", 0)
                    ]
                    if ignored_end_positions:
                        base_length = max(ignored_end_positions)
                    else:
                        # With no configurable head property, the complete
                        # pre-dot article number is the base. This also keeps
                        # singleton structure classes from retaining the
                        # after-dot suffix in Base Article.
                        pre_dot_lengths = [
                            len(code.split(".", 1)[0])
                            for code in (code_of.get(a, "") for a in article_ids)
                            if code
                        ]
                        if pre_dot_lengths:
                            base_length = min(pre_dot_lengths)
                        else:
                            code_len = max(
                                (len(code_of.get(a, "")) for a in article_ids),
                                default=0,
                            )
                            config_width = sum(
                                prop_width.get(str(a.id), 0) for a in properties
                            )
                            base_length = max(code_len - config_width, 0)
            properties = self._merge_manual_class_values(
                snapshot, article_ids, properties, base_length
            )
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
        article_value_ids: dict[str, list[str]] | None = None,
    ) -> list[SetAttribute]:
        """Group the set's carried values by attribute, tracking which articles
        carry each value (first-seen order, unique)."""
        # attribute id -> (name, {value id -> [article ids]})
        by_attribute: dict[str, tuple[str, dict[str, list[str]]]] = {}
        order: list[str] = []
        article_value_ids = article_value_ids or {}
        for article_id in article_ids:
            product_id = product_of.get(article_id, "")
            # PDM Item-level BaseAttributeValues are authoritative when
            # present. Product-level values are a fallback only when the Item
            # has no BaseAttributeValues rows.
            selected = [str(v) for v in article_value_ids.get(article_id, [])]
            product_values = [str(v) for v in product_value_ids.get(product_id, [])]
            value_ids = selected if selected else product_values
            for value_id in value_ids:
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
    def _merge_manual_class_values(
        snapshot: Snapshot,
        article_ids: list[str],
        attributes: list[SetAttribute],
        base_length: int,
    ) -> list[SetAttribute]:
        """Overlay manual Class Creation values onto an Article Set."""
        engineering = getattr(snapshot, "engineering", None)
        if engineering is None:
            return attributes
        article_by_id = {str(a.id): a for a in snapshot.articles}
        target_ids = {str(a) for a in article_ids}
        by_id = {str(a.id): a for a in attributes}
        prop_names = {
            str(p.id): (p.name or "")
            for p in getattr(snapshot, "properties", []) or []
        }

        for cls in getattr(engineering, "classes", []) or []:
            offset = 0
            for assignment in getattr(cls, "properties", []) or []:
                width = max(0, int(getattr(assignment, "width", 0) or 0))
                manual = [
                    v for v in getattr(assignment, "values", []) or []
                    if getattr(v, "source", "pdm") == "manual" and v.code
                ]
                if manual and width:
                    set_attr = by_id.get(str(assignment.property_id))
                    if set_attr is None:
                        set_attr = SetAttribute(
                            id=str(assignment.property_id),
                            name=getattr(assignment, "property_name", "")
                            or prop_names.get(str(assignment.property_id), ""),
                            values=[],
                        )
                        attributes.append(set_attr)
                        by_id[str(assignment.property_id)] = set_attr
                    for article_id in target_ids:
                        article = article_by_id.get(article_id)
                        if article is None:
                            continue
                        pre_dot = (article.code or "").split(".", 1)[0]
                        letters = pre_dot[base_length:][offset:offset + width]
                        match = next((v for v in manual if v.code == letters), None)
                        if match is None:
                            continue
                        existing = next(
                            (v for v in set_attr.values if v.code == match.code),
                            None,
                        )
                        if existing is None:
                            set_attr.values.append(
                                SetValue(
                                    id=f"manual:{assignment.property_id}:{match.code}",
                                    value=match.value or "",
                                    code=match.code,
                                    article_ids=[article_id],
                                )
                            )
                        elif article_id not in existing.article_ids:
                            existing.article_ids.append(article_id)
                offset += width
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

    # -- legacy PDM validation of the candidate families -------------------
    def candidate_families(
        self, snapshot: Snapshot | None, per_product_range: bool = True
    ) -> tuple[CandidateFamily, ...]:
        """The candidate families THIS engine produced, ready for the boundary.

        A candidate family is one materialised :class:`ArticleSet` - the
        articles that share a property structure and are therefore proposed to
        collapse onto one base (``ArticleSet.base_code``). The legacy boundary
        filters Products, not articles, so each set is expressed as the
        distinct ProductIds its articles belong to.

        ``ProductsList`` is ProductRange-scoped, and so is classification
        (:meth:`classify_by_properties`), so a set already belongs to exactly
        one range and each set yields exactly one candidate. The per-range
        slice below therefore only LABELS the candidate with the range the
        boundary will be asked about; it never moves an article between sets,
        merges sets, or invents a grouping. It is kept because it is the
        boundary's own scope declaration, and because it still divides
        correctly for a snapshot that carries no range for some products.
        Pass ``per_product_range=False`` to leave the label off.

        When ``context.candidate_strategy_service`` is wired, ADDITIONAL
        candidates from the fallback strategies are appended after the primary
        ones, already merged and deduplicated against them (see
        :class:`~services.engineering.candidate_strategy_service.CandidateStrategyService`).
        They are extra questions for the boundary, never a replacement: the
        primary candidates are returned unchanged and outrank every fallback
        wherever both are validated. Without that service - or with
        ``per_product_range=False``, which is the diagnostic whole-set view -
        only the primary candidates are produced.

        Materialises the sets first when the snapshot has none. Read-only.
        """
        if snapshot is None:
            return ()
        sets = list(getattr(snapshot, "article_sets", None) or ())
        if not sets:
            sets = list(self.materialize_article_sets(snapshot))
        product_of = {
            str(a.id): str(getattr(a, "product_id", "") or "") for a in snapshot.articles
        }
        code_of = {str(a.id): (a.code or "") for a in snapshot.articles}
        range_of = getattr(snapshot, "product_range", {}) or {}

        candidates: list[CandidateFamily] = []
        for article_set in sets:
            # range name -> (ProductIds, article ids), first-seen order.
            slices: dict[str, tuple[list[str], list[str]]] = {}
            for article_id in article_set.article_ids:
                product_id = product_of.get(str(article_id), "")
                if not product_id:
                    continue
                scope = str(range_of.get(product_id, "") or "") if per_product_range else ""
                product_ids, article_ids = slices.setdefault(scope, ([], []))
                if product_id not in product_ids:
                    product_ids.append(product_id)
                article_ids.append(str(article_id))
            for scope, (product_ids, article_ids) in slices.items():
                # The slice's own base, by the SAME rule the set used: the
                # shared code prefix, never longer than the set's derived base
                # length. A slice of a wide set must not inherit the whole
                # set's much shorter cross-range prefix as its base article.
                codes = [code_of.get(a, "") for a in article_ids]
                base_n = min(
                    article_set.base_length, self._common_prefix_len(codes)
                )
                candidates.append(
                    CandidateFamily(
                        set_id=article_set.id,
                        base_code=next((c for c in codes if c), "")[:base_n],
                        product_range=scope,
                        product_ids=tuple(sorted(product_ids)),
                        article_ids=tuple(article_ids),
                    )
                )
        if not per_product_range:
            return tuple(candidates)
        return tuple(candidates) + self._fallback_candidates(
            snapshot, candidates, product_of, code_of
        )

    def _fallback_candidates(
        self,
        snapshot: Snapshot,
        primary: list[CandidateFamily],
        product_of: dict[str, str],
        code_of: dict[str, str],
    ) -> tuple[CandidateFamily, ...]:
        """Turn the strategy service's proposals into candidates to be judged.

        Absent service, absent PDM or a failing strategy read leaves the
        primary candidates exactly as they were: a fallback is an extra chance
        to prove a family, so failing to produce one must never cost the
        reduction the families it could already prove.
        """
        service = getattr(self.context, "candidate_strategy_service", None)
        if service is None:
            return ()
        try:
            proposals = service.propose(
                snapshot,
                primary_product_id_sets=[c.product_ids for c in primary],
                primary_bases=[(c.base_code, c.product_range) for c in primary],
            )
        except Exception:
            # Never let a fallback source break the primary flow.
            return ()

        articles_of_product: dict[str, list[str]] = {}
        for article_id, product_id in product_of.items():
            articles_of_product.setdefault(product_id, []).append(article_id)

        candidates: list[CandidateFamily] = []
        for proposal in proposals:
            article_ids = sorted(
                article_id
                for product_id in proposal.product_ids
                for article_id in articles_of_product.get(str(product_id), ())
            )
            if not article_ids:
                continue
            # A fallback grouping is not a property-structure class, so it has
            # no derived base length to cap with. The one thing its own
            # definition guarantees is what its members' codes actually share,
            # so the base is their common prefix - which can only ever be
            # LONGER than a derived base, i.e. err towards collapsing less.
            codes = [code_of.get(a, "") for a in article_ids]
            base_n = self._common_prefix_len(codes)
            candidates.append(
                CandidateFamily(
                    set_id="",
                    base_code=next((c for c in codes if c), "")[:base_n],
                    product_range=proposal.product_range,
                    product_ids=tuple(sorted(str(p) for p in proposal.product_ids)),
                    article_ids=tuple(article_ids),
                    strategy=proposal.strategy,
                    strategy_reason=proposal.reason,
                )
            )
        return tuple(candidates)

    def validate_article_sets(
        self,
        snapshot: Snapshot | None,
        language_id: Any = 1,
        per_product_range: bool = True,
    ) -> tuple[ArticleSetValidation, ...]:
        """Prove each candidate family against the legacy ``ProductsList``.

        This does not group, re-group, or reduce anything: the grouping is the
        one :meth:`materialize_article_sets` already derived. For every
        candidate it asks the legacy boundary whether that candidate's common
        functional (non-order-code) AttributeValueIds select exactly that
        candidate's ProductIds, and returns one verdict each.

        The snapshot need not hold the whole ProductRange, so the check has to
        go to PDM; the snapshot's loaded Products are passed along so each
        verdict can state whether they covered the range
        (``snapshot_covers_range``) instead of assuming it. ``ProductsList``
        filters the COMPLETE range, so a candidate from a partly loaded range
        comes back ``unresolved`` - see
        :meth:`services.pdm_service.PDMService.complete_product_ranges` for
        closing that gap.

        Requires ``context.pdm_family_reduction_service``; its absence raises
        rather than silently skipping the check. Mutates nothing - in
        particular no ``reduced_article`` and no article code, so the
        after-dot order-code suffix is untouched.
        """
        if snapshot is None:
            return ()
        candidates = self.candidate_families(snapshot, per_product_range)
        if not candidates:
            return ()
        validator = self.context.pdm_family_reduction_service
        loaded_product_ids = sorted(
            {
                str(getattr(a, "product_id", "") or "")
                for a in snapshot.articles
                if getattr(a, "product_id", None)
            }
        )
        # Only a candidate spanning two or more Products asserts a family the
        # boundary can judge; a single-Product candidate is answered here
        # rather than costing a ProductsList round trip per Product.
        askable = [c for c in candidates if len(c.product_ids) >= 2]
        verdicts = iter(
            validator.validate_families(
                [
                    FamilyCandidate(base=c.base_code, product_ids=c.product_ids)
                    for c in askable
                ],
                language_id,
                known_product_ids=loaded_product_ids,
            )
            if askable
            else ()
        )

        results: list[ArticleSetValidation] = []
        for candidate in candidates:
            if len(candidate.product_ids) < 2:
                results.append(
                    ArticleSetValidation(
                        set_id=candidate.set_id,
                        base_code=candidate.base_code,
                        product_range=candidate.product_range,
                        product_ids=candidate.product_ids,
                        article_ids=candidate.article_ids,
                        strategy=candidate.strategy,
                        strategy_reason=candidate.strategy_reason,
                        status="unresolved",
                        reason=(
                            "Fewer than two Products: collapsing one Product's "
                            "own articles onto one base makes no cross-Product "
                            "claim, so ProductsList has nothing to prove."
                        ),
                    )
                )
                continue
            verdict = next(verdicts)
            results.append(
                ArticleSetValidation(
                    set_id=candidate.set_id,
                    base_code=candidate.base_code,
                    product_range=candidate.product_range,
                    product_ids=candidate.product_ids,
                    article_ids=candidate.article_ids,
                    strategy=candidate.strategy,
                    strategy_reason=candidate.strategy_reason,
                    status=verdict.status,
                    reason=verdict.reason,
                    product_range_id=verdict.product_range_id,
                    product_category_id=verdict.product_category_id,
                    functional_attribute_value_ids=verdict.functional_attribute_value_ids,
                    filtered_product_ids=verdict.filtered_product_ids,
                    missing_from_filter=verdict.missing_from_filter,
                    extra_in_filter=verdict.extra_in_filter,
                    extra_outside_snapshot=verdict.extra_outside_known,
                    snapshot_covers_range=verdict.range_population_complete,
                    unloaded_range_product_count=verdict.unloaded_range_product_count,
                )
            )
        return tuple(results)

    def blocked_article_ids(
        self,
        snapshot: Snapshot | None,
        validations: tuple[ArticleSetValidation, ...] | None = None,
        language_id: Any = 1,
    ) -> frozenset[str]:
        """The articles that must NOT collapse onto a reduced base.

        An article is blocked when NO candidate family covering it was
        confirmed - neither the primary one nor any fallback. A single
        confirmed candidate is enough to release it, which is the whole point
        of offering more than one grouping to the boundary. Pass
        ``validations`` to reuse verdicts already obtained instead of asking
        the boundary twice.
        """
        if snapshot is None:
            return frozenset()
        if validations is None:
            validations = self.validate_article_sets(snapshot, language_id)
        return frozenset(self._resolve(validations)[1])

    @staticmethod
    def _resolve(
        validations: tuple[ArticleSetValidation, ...],
    ) -> tuple[dict[str, ArticleSetValidation], set[str]]:
        """Pick ONE verdict per article, and collect the articles left blocked.

        Several candidates can cover the same article once fallbacks are in
        play, so the winner is chosen by a fixed, declared order - never by a
        score:

        1. a CONFIRMED family before one that merely had nothing to prove. The
           only non-blocking verdict that is not a confirmation is the
           single-Product candidate, which asserts no family at all; a proven
           cross-Product family is better evidence than that, whichever rule
           proposed it.
        2. the strategy, primary first and then
           :data:`~services.engineering.candidate_strategy_service.STRATEGY_ORDER`,
           so between two CONFIRMED answers the primary grouping always wins
           and a fallback only takes effect where the primary one was not
           confirmed;
        3. the WIDEST confirmed family. Where one confirmed family contains
           another - and it does, because a narrower selector selects a
           narrower closed set - both are equally proven, so safety cannot
           choose between them and purpose does: reduction exists to collapse,
           and splitting one proven family across two bases would leave the
           same articles with different base articles for no gain;
        4. the longer base, then the base text - pure tie-breaking, so the
           result never depends on iteration order.

        Only a verdict that does not block may win. An article covered solely
        by blocking verdicts is blocked; one no verdict covers is untouched.
        """
        rank = {PRIMARY_STRATEGY: 0}
        for index, name in enumerate(STRATEGY_ORDER):
            rank[name] = index + 1

        def order(verdict: ArticleSetValidation):
            return (
                0 if verdict.is_legacy_equivalent else 1,
                rank.get(verdict.strategy, len(rank)),
                -len(verdict.product_ids),
                -len(verdict.base_code),
                verdict.base_code,
            )

        winner: dict[str, ArticleSetValidation] = {}
        covered: set[str] = set()
        for verdict in sorted(validations, key=order):
            covered.update(verdict.article_ids)
            if verdict.blocks_reduction:
                continue
            for article_id in verdict.article_ids:
                winner.setdefault(article_id, verdict)
        return winner, covered - set(winner)

    def apply_validated_reduction(
        self, snapshot: Snapshot | None, language_id: Any = 1
    ) -> ReductionApplication:
        """Reduce - but only the families legacy PDM confirmed.

        This is the enforcing entry point of the reduction flow. The candidate
        families and their base lengths are still this engine's own
        (:meth:`materialize_article_sets`); what changes is that a family
        asserting a cross-Product base only collapses once ``ProductsList``
        returned exactly its ProductIds. Rejected, unresolved and un-checkable
        candidates are left expanded, and any base previously stamped on them
        is cleared, so an unproven collapse cannot survive in the snapshot.

        A confirmed family collapses onto the ONE base its candidate carries -
        for the primary grouping the base its set derived (the shared prefix,
        never longer than the derived base length), for a fallback the shared
        prefix of its members' codes. That is what makes it one base article
        rather than a per-article slice.

        Where several confirmed candidates cover the same article the winner
        is chosen by :meth:`_resolve`: the primary grouping first, so a
        fallback only takes effect where the primary candidate was not
        confirmed.

        Only the PRE-DOT portion is ever written: the stored base is capped at
        the ``.`` delimiter, so the order-code suffix an article carries after
        the dot is preserved byte for byte. Article codes themselves are never
        rewritten - reduction records the base, it does not regenerate the
        article.

        Mutates only ``member.reduced_article``, through the member service.
        """
        if snapshot is None or getattr(snapshot, "engineering", None) is None:
            return ReductionApplication()
        validations = self.validate_article_sets(snapshot, language_id)
        if not validations:
            return ReductionApplication()

        # article id -> the base to stamp, or "" when no candidate covering it
        # was confirmed. A blocked article is cleared rather than left as it
        # was, so an unproven collapse cannot survive in the snapshot.
        winner, blocked_ids = self._resolve(validations)
        base_by_article: dict[str, str] = {
            article_id: self._pre_dot_base(verdict.base_code)
            for article_id, verdict in winner.items()
        }
        base_by_article.update({article_id: "" for article_id in blocked_ids})
        applied = sorted(winner)
        blocked = sorted(blocked_ids)

        member_service = self.context.engineering_member_service
        applied_members = 0
        blocked_members = 0
        for family in snapshot.engineering.families:
            for member in family.members:
                article_id = str(getattr(member, "article_id", "") or "")
                if article_id not in base_by_article:
                    continue
                base = base_by_article[article_id]
                if base:
                    member_service.set_reduced_article(member, base)
                    applied_members += 1
                else:
                    member_service.set_reduced_article(member, "")
                    blocked_members += 1

        return ReductionApplication(
            validations=validations,
            applied_article_ids=tuple(applied),
            blocked_article_ids=tuple(blocked),
            applied_members=applied_members,
            blocked_members=blocked_members,
        )

    @staticmethod
    def _pre_dot_base(base: str) -> str:
        """``base`` truncated so it never reaches past the ``.`` delimiter.

        A base may end AT the dot (the established convention - see the
        Articles page dot-boundary rule) but never inside the order-code
        suffix, so an article ``BASE.SUFFIX`` always keeps ``.SUFFIX`` intact.
        """
        dot = (base or "").find(".")
        return (base or "") if dot < 0 else base[: dot + 1]


    def _repository(self) -> EngineeringRepository:
        """Reuse the context's engineering repository, else a stateless one."""
        repository = getattr(self.context, "engineering_repository", None)
        if repository is None:
            repository = EngineeringRepository(self.context)
        return repository