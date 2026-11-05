"""Configuration engine: dependency-aware enumeration and verification.

``enumerate`` walks the properties depth-first in dependency order and offers,
at each node, only the values whose preconditions are not violated by what is
already chosen - the unrestricted Cartesian product is never built. A property
whose own precondition is definitely FALSE is *hidden* (no value, as pCon
omits it). ``finalize`` then verifies a complete configuration against the
full relation set (computed properties may have changed what is visible),
evaluates computed properties, constraints and price relations.

Every rejection is counted and, within the sink's bounds, explained.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Iterator, Mapping, Sequence

from core.cancellation import checkpoint
from services.ocd_engine import diagnostics as dg
from services.ocd_engine import fabric
from services.ocd_engine import fabric_resolver as fr
from services.ocd_engine import model as m
from services.ocd_engine import relation_parser as rp
from services.ocd_engine.codescheme_engine import EncodedValue
from services.ocd_engine.computed_property_engine import ComputedPropertyEngine
from services.ocd_engine.relation_evaluator import (
    EvalContext, EvalError, Tri, eval_cond, precondition_violated, run_constraint,
    selection_condition_met,
)
from services.ocd_engine.varcond_engine import VarcondEngine


@dataclass
class EnumerationLimits:
    """Safeguards against permutation explosion; ``None`` = unlimited."""

    max_configurations: int | None = None
    max_nodes: int | None = None


@dataclass
class EnumerationStats:
    nodes: int = 0
    emitted: int = 0
    pruned: int = 0
    truncated: bool = False
    reason: str = ""
    inert: tuple[str, ...] = ()      # read-only properties offered one value only (see ``inert_properties``)


#: OCD scopes of properties the user cannot configure: ``R`` read-only, ``RG`` read-only group,
#: ``RV`` read-only value. Configurable (``C``) properties are never collapsed.
READ_ONLY_SCOPES = frozenset({"R", "RG", "RV"})


@dataclass(frozen=True)
class Configuration:
    assignments: tuple[m.Assignment, ...]

    def values(self) -> dict[str, str]:
        return {a.prop.name_upper: a.value.value for a in self.assignments
                if a.value is not None and not a.hidden}


@dataclass
class FinalResult:
    valid: bool
    reason: str = ""
    relation: str = ""
    computed: dict = field(default_factory=dict)
    varconds: list[str] = field(default_factory=list)
    pricing_factors: dict = field(default_factory=dict)
    uncertain: bool = False          # a relation could not be parsed/evaluated for this configuration
    context: EvalContext | None = None


class ConfigView:
    """:class:`PropertyView` over one configuration plus its computed properties."""

    def __init__(self, model: m.ArticleModel, assignments, computed: Mapping[str, object]) -> None:
        self._by_class: dict[tuple[str, str], m.Assignment] = {}
        self._by_name: dict[str, m.Assignment] = {}
        for item in assignments:
            self._by_class[(item.prop.class_name.upper(), item.prop.name_upper)] = item
            self._by_name.setdefault(item.prop.name_upper, item)
        self._computed = {str(k).upper(): v for k, v in computed.items()}
        self._ordered = [(p.class_name, p.name) for p in model.properties]
        self._known = {(p.class_name.upper(), p.name_upper) for p in model.properties} | \
                      {p.name_upper for p in model.properties}

    def get(self, property_class: str, property_name: str) -> EncodedValue | None:
        name = property_name.upper()
        item = self._by_class.get((property_class.upper(), name)) or self._by_name.get(name)
        if name in self._computed and (item is None or not item.hidden):
            computed = self._computed[name]
            return EncodedValue(text="" if computed is None else str(computed), visible=True)
        if item is None:
            # known to the model but not part of this configuration => invisible
            return EncodedValue(visible=False) if name in self._known else None
        return EncodedValue(
            text=item.value.encoded if item.value is not None else "",
            visible=not item.hidden,
            optional=item.prop.optional,
            length=item.prop.length,
        )

    def ordered(self) -> list[tuple[str, str]]:
        return list(self._ordered)


@dataclass(frozen=True)
class _Follower:
    colour_upper: str
    type_upper: str
    primary_type_upper: str


def _tail(name: str) -> str:
    return name.rsplit(".", 1)[-1]


class ConfigurationEngine:
    def __init__(self, model: m.ArticleModel, *, sink: dg.DiagnosticSink | None = None,
                 limits: EnumerationLimits | None = None,
                 progress: Callable[[EnumerationStats], None] | None = None,
                 rhs_values_factory: Callable[[Mapping[str, str], Sequence[m.Assignment]], dict] | None = None,
                 progress_every: int = 5000,
                 identity_texts: Sequence[str] | None = None,
                 fabric_default_only: bool = True, fabric_property: str = "",
                 shared_fabric: bool = False, fabric_ties: Sequence[fabric.FabricTie] | None = None) -> None:
        """``shared_fabric`` (opt-in): fabric positions that offer the same fabric types (``fabric.shared_fabric_ties``, e.g.
        a Back/Arms and a Seat position) are one choice. The later position's type and colour are restricted, at its
        own node and by the same precondition filtering, to what the first position selected - the independent
        product of the positions is never enumerated. ``fabric_ties`` supplies ties derived from an unrestricted
        model (a pinned model may offer fewer types); ``None`` derives them from ``model``.

        ``fabric_default_only``: every fabric colour property the data shows (``fabric.discover_schemes``) is
        resolved by :class:`~services.ocd_engine.fabric_resolver.FabricColourResolver` to ONE colour per
        configuration - a valid flagged ``is_default`` colour, else the first valid colour in source order - at the
        colour's own node, so the other colours are never expanded. ``False`` keeps every valid colour.

        ``fabric_property``: the one optional manual choice - the property that holds the fabric information. It
        is an input to the same discovery/resolver (roles are still read from the data); when it cannot be
        resolved, :meth:`enumerate` raises :class:`~services.ocd_engine.fabric_resolver.FabricOverrideError`
        instead of offering every colour.

        ``identity_texts``: every text outside the model's relations that reads property values to build the
        final article (the code scheme body). ``None`` disables the inert-property optimisation because the
        engine cannot know what else reads the configuration."""
        self.model = model
        self.sink = sink if sink is not None else dg.DiagnosticSink()
        self.limits = limits or EnumerationLimits()
        self.progress = progress
        self.progress_every = progress_every
        self.stats = EnumerationStats()
        self._rhs_values_factory = rhs_values_factory
        self._bad: set[str] = set()                   # relations already reported as unusable
        self._leaf_uncertain = False
        self._no_value_reported: set[str] = set()
        self._classes = model.class_by_name()
        self._computed_engine = ComputedPropertyEngine(model, self.sink)
        self._varcond_engine = VarcondEngine(model, self.sink)
        self._constraints = self._collect_constraints()
        self._candidate_refs: dict[str, tuple[str, ...]] = {}     # dimension key -> properties its value filter reads
        self._candidate_cache: dict[tuple, list[m.ValueDef]] = {}
        # One resolver for every fabric (type, colour) pair the data shows; off -> every valid colour stays.
        self._fabric = (fr.FabricColourResolver(model, self._tri_checked, fabric_property=fabric_property)
                        if fabric_default_only else None)
        self._fabric_colours = self._fabric.colour_properties if self._fabric else frozenset()
        self.fabric_resolutions: dict[tuple, fr.FabricResolution] = {}     # first resolution per (colour, type, pick)
        if not shared_fabric:
            ties: tuple[fabric.FabricTie, ...] = ()
        elif fabric_ties is not None:
            ties = tuple(fabric_ties)
        else:
            ties = fabric.shared_fabric_ties(model, fabric.discover(model, fabric_property).schemes)
        self.fabric_ties = ties
        # follower property (upper) -> the property (upper) whose selected value it must take
        self._tie_source: dict[str, str] = {}
        for tie in ties:
            self._tie_source[tie.follower_type.upper()] = tie.primary_type.upper()
            self._tie_source[tie.follower_colour.upper()] = tie.primary_colour.upper()
        self._props_by_name = {p.name_upper: p for p in model.properties}
        # primary colour property (upper) -> the ties whose follower must accept the colour it picks
        self._followers: dict[str, list[_Follower]] = {}
        for tie in ties:
            self._followers.setdefault(tie.primary_colour.upper(), []).append(
                _Follower(tie.follower_colour.upper(), tie.follower_type.upper(), tie.primary_type.upper()))
        if self._fabric is not None and self._fabric.override_error:
            self.sink.add(dg.FABRIC_OVERRIDE_UNRESOLVED, f"fabric property {self._fabric.override or fabric_property}: "
                          f"{self._fabric.override_error}",
                          dg.Severity.WARNING if self._fabric.override_missing else dg.Severity.ERROR,
                          article=model.base_code, property=self._fabric.override or fabric_property)
        for pair in (self._fabric.unconfirmed if self._fabric else ()):
            self.sink.add(dg.FABRIC_PAIR_UNCONFIRMED,
                          f"{pair.type_property} -> {pair.colour_property} has the structure of a fabric type/colour "
                          f"pair ({pair.mechanism}) but no fabric name; it is not reduced to one colour",
                          dg.Severity.INFO, article=model.base_code, property=pair.colour_property)
        for colour_name, types in (self._fabric.ambiguous if self._fabric else ()):
            self.sink.add(dg.FABRIC_PAIR_AMBIGUOUS,
                          f"{colour_name} fits several fabric types equally well ({', '.join(types)}); the data does "
                          f"not say which one it follows, so it is not paired and not reduced to one colour",
                          dg.Severity.WARNING, article=model.base_code, property=colour_name)
        self._inert = self.inert_properties(model, identity_texts) if identity_texts is not None else frozenset()

    @property
    def fabric_override_error(self) -> str:
        """Why the manual fabric property cannot be used (empty when none was chosen, it applies, or the article
        merely lacks it - that case only warns and falls back to automatic discovery)."""
        fab = self._fabric
        return fab.override_error if fab is not None and not fab.override_missing else ""

    # ------------------------------------------------------------ inert properties
    @staticmethod
    def inert_properties(model: m.ArticleModel, identity_texts: Sequence[str]) -> frozenset[str]:
        """Upper-case names of read-only properties whose value cannot change anything.

        A property is inert when it is read-only (scope R/RG/RV, so it is not in the OBX ``ofmlvarcode``,
        which lists configurable properties only), no relation of the article - precondition, selection,
        action, constraint, reaction, any domain, on the article, its classes, properties or values - and no
        identity text (the code scheme) mentions it, and none of its values carries an action or constraint.
        Offering it more than one value then yields configurations that differ only in that value: the same
        validity, final article, variant conditions and price. Only its first offered value is enumerated;
        the first value is the one the full enumeration reached first, so the result is unchanged.
        An unparsable relation does not disable the check: the scan is textual, so it over- rather than
        under-reports references.
        """
        texts = [ref.text for ref in model.article_relations]
        for cls in model.classes:
            texts.extend(ref.text for ref in cls.relations)
        for prop in model.properties:
            texts.extend(ref.text for ref in prop.relations)
            for value in prop.values:
                texts.extend(ref.text for ref in value.relations)
        texts.extend(identity_texts)
        haystack = chr(10).join(texts)
        found = set()
        for prop in model.properties:
            if prop.scope.upper() not in READ_ONLY_SCOPES or len(prop.values) < 2:
                continue
            if any(r.rel_type in (m.ACTION, m.CONSTRAINT) for v in prop.values for r in v.relations):
                continue
            if re.search(rf"(?<![A-Za-z0-9_]){re.escape(prop.name)}(?![A-Za-z0-9_])", haystack, re.IGNORECASE):
                continue
            found.add(prop.name_upper)
        return frozenset(found)

    # ------------------------------------------------------------ relation helpers
    def _tri_checked(self, ref: m.RelationRef, ctx: EvalContext, owner: str) -> tuple[Tri, str | None]:
        """The relation's result and, when it could not be parsed or evaluated, why (the result is then UNDEFINED)."""
        compiled = rp.compile_relation(m.PRECONDITION if ref.rel_type in (1, 2) else ref.rel_type, ref.text)
        if compiled.error:
            self._report_bad(ref, compiled.error, owner, dg.RELATION_PARSE_ERROR)
            return Tri.UNDEFINED, compiled.error
        try:
            return eval_cond(compiled.node, ctx), None
        except EvalError as error:
            self._report_bad(ref, str(error), owner, dg.RELATION_EVAL_ERROR)
            return Tri.UNDEFINED, str(error)

    def _tri(self, ref: m.RelationRef, ctx: EvalContext, owner: str) -> Tri:
        return self._tri_checked(ref, ctx, owner)[0]

    def _report_bad(self, ref: m.RelationRef, message: str, owner: str, code: str) -> None:
        self._leaf_uncertain = True
        if ref.name in self._bad:
            return
        self._bad.add(ref.name)
        self.sink.add(code, message, article=self.model.base_code, relation=ref.name, source=owner)

    @staticmethod
    def _of_type(relations, rel_type: int):
        return [r for r in relations if r.rel_type == rel_type and r.domain.upper() == "C"]

    def _collect_constraints(self):
        """Article/class-level constraints (type 4, domain C), parsed once."""
        found = []
        owners = [(r, "article") for r in self.model.article_relations]
        for cls in self.model.classes:
            owners.extend((r, f"class {cls.name}") for r in cls.relations)
        for ref, owner in sorted(owners, key=lambda item: (item[0].order, item[0].name)):
            if ref.rel_type == m.CONSTRAINT and ref.domain.upper() == "C":
                compiled = rp.compile_relation(m.CONSTRAINT, ref.text)
                if compiled.error:
                    self.sink.add(dg.RELATION_PARSE_ERROR, compiled.error,
                                  article=self.model.base_code, relation=ref.name, source=owner)
                    continue
                found.append((ref, owner, compiled))
        return found

    def _relation_refs(self, dim: m.PropertyDef) -> tuple[set[str], bool]:
        """Properties the relations that decide ``dim``'s visibility and values read, and whether all were readable."""
        refs: set[str] = set()
        readable = True
        relations = list(self._of_type(dim.relations, m.PRECONDITION)) +             list(self._of_type(dim.relations, m.SELECTION))
        cls = self._classes.get(dim.class_name.upper())
        if cls is not None:
            relations += self._of_type(cls.relations, m.PRECONDITION)
        for value in dim.values:
            relations += self._of_type(value.relations, m.PRECONDITION)
            relations += self._of_type(value.relations, m.SELECTION)
        for ref in relations:
            compiled = rp.compile_relation(m.PRECONDITION, ref.text)
            refs |= {_tail(r) for r in compiled.refs}
            readable = readable and not compiled.error
        return refs, readable

    # ------------------------------------------------------------ ordering
    def _prepare(self, dimensions: Sequence[m.PropertyDef]):
        names = {d.name_upper: i for i, d in enumerate(dimensions)}
        deps: list[set[str]] = []
        self._candidate_refs, self._candidate_cache = {}, {}
        by_name = {d.name_upper: d for d in dimensions}
        for dim in dimensions:
            refs, readable = self._relation_refs(dim)
            for follower in self._followers.get(dim.name_upper, ()):
                # The colour this position picks is also checked against its follower (``_accept``), so the choice
                # depends on what the follower's relations read, and is ordered after it.
                follower_dim = by_name.get(follower.colour_upper)
                if follower_dim is not None:
                    more, more_readable = self._relation_refs(follower_dim)
                    refs |= more | {follower.type_upper}
                    readable = readable and more_readable
            if readable:
                # What this dimension's value filter (``_candidates``) can depend on; see there.
                self._candidate_refs[dim.key] = tuple(sorted(refs))
            scheme = self._fabric.scheme_of(dim.name_upper) if self._fabric else None
            if scheme is not None:
                # The colour list is a function of the selected type even when no relation reads it (value-text
                # fallback): order the type first and key the candidate cache on it.
                refs.add(scheme.type_upper)
                if dim.key in self._candidate_refs:
                    self._candidate_refs[dim.key] = tuple(sorted(set(self._candidate_refs[dim.key]) | {scheme.type_upper}))
            source = self._tie_source.get(dim.name_upper)
            if source is not None:
                # A tied position is chosen after the position it follows, and its list is keyed on that choice.
                refs.add(source)
                if dim.key in self._candidate_refs:
                    self._candidate_refs[dim.key] = tuple(sorted(set(self._candidate_refs[dim.key]) | {source}))
            refs.discard(dim.name_upper)
            deps.append({r for r in refs if r in names})
        order: list[int] = []
        placed: set[str] = set()
        remaining = list(range(len(dimensions)))
        while remaining:
            pick = next((i for i in remaining if deps[i] <= placed), None)
            if pick is None:
                pick = remaining[0]
                self.sink.add(dg.CYCLIC_DEPENDENCY,
                              f"cyclic property dependency near {dimensions[pick].name}; original order used",
                              dg.Severity.WARNING, article=self.model.base_code,
                              property=dimensions[pick].name)
            order.append(pick)
            placed.add(dimensions[pick].name_upper)
            remaining.remove(pick)
        return [dimensions[i] for i in order]

    def _constraint_schedule(self, ordered: Sequence[m.PropertyDef]):
        """Depth at which each constraint can first be decided (all inputs chosen)."""
        index = {d.name_upper: i for i, d in enumerate(ordered)}
        schedule: dict[int, list] = {}
        for ref, owner, compiled in self._constraints:
            aliases = dict(compiled.node.variables)
            depth = -1
            ready = True
            for raw in compiled.refs:
                name = _tail(raw)
                name = aliases.get(name, name)
                if name in index:
                    depth = max(depth, index[name])
                else:
                    ready = False
                    break
            if ready and depth >= 0:
                schedule.setdefault(depth, []).append((ref, owner, compiled))
        return schedule

    # ------------------------------------------------------------ enumeration
    def enumerate(self, dimensions: Sequence[m.PropertyDef] | None = None,
                  *, base_values: Mapping[str, object] | None = None) -> Iterator[Configuration]:
        """Yield every configuration of ``dimensions`` that survives early pruning.

        ``base_values`` seeds the evaluation state (fixed values, e.g. ArtBase
        singletons). Output order is deterministic: dependency order, values by
        their display order.
        """
        if self.fabric_override_error:
            raise fr.FabricOverrideError(self.fabric_override_error)
        dims = [d for d in (dimensions if dimensions is not None else self.model.properties) if d.values]
        ordered = self._prepare(dims)
        schedule = self._constraint_schedule(ordered)
        self.stats = EnumerationStats(inert=tuple(sorted(d.name for d in ordered if d.name_upper in self._inert)))
        values: dict[str, object] = {str(k).upper(): v for k, v in (base_values or {}).items()}
        ctx = EvalContext(values=values, ban=self.model.base_code, tables=self.model.tables)
        chosen: list[m.Assignment] = []
        limits = self.limits

        def stop() -> bool:
            if limits.max_nodes is not None and self.stats.nodes >= limits.max_nodes:
                self.stats.truncated, self.stats.reason = True, f"node limit {limits.max_nodes} reached"
                return True
            return self.stats.truncated

        def visit(depth: int):
            self.stats.nodes += 1
            if self.stats.nodes % 256 == 0:
                checkpoint()
            if self.progress is not None and self.stats.nodes % self.progress_every == 0:
                self.progress(self.stats)
            if stop():
                return
            if depth == len(ordered):
                if limits.max_configurations is not None and self.stats.emitted >= limits.max_configurations:
                    # flagged only when one more configuration actually exists
                    self.stats.truncated = True
                    self.stats.reason = f"configuration limit {limits.max_configurations} reached"
                    return
                self.stats.emitted += 1
                yield Configuration(tuple(chosen))
                return
            dim = ordered[depth]
            if self._is_hidden(dim, ctx):
                chosen.append(m.Assignment(dim, None, True))
                yield from visit(depth + 1)
                chosen.pop()
                return
            candidates = self._candidates(dim, ctx)
            shared = self._shared_value(dim, ctx)
            if not candidates and shared is not None:
                # The position this one follows chose a value that is not valid here: the two positions cannot
                # agree, so this is not a configuration (never an unassigned position).
                self.stats.pruned += 1
                if dim.name_upper not in self._no_value_reported:
                    self._no_value_reported.add(dim.name_upper)
                    self.sink.add(dg.SHARED_FABRIC_UNAVAILABLE,
                                  f"{dim.name} cannot take the value {shared!r} chosen for "
                                  f"{self._tie_source[dim.name_upper]} under some selections; those configurations "
                                  f"are rejected", dg.Severity.INFO, article=self.model.base_code, property=dim.name)
                return
            if not candidates and dim.name_upper in self._fabric_colours and self._fabric_type_selected(dim, ctx):
                # A fabric is chosen but none of its colours is valid here: not a configuration.
                self.stats.pruned += 1
                if dim.name_upper not in self._no_value_reported:
                    self._no_value_reported.add(dim.name_upper)
                    why = self._fabric.resolve(dim, ctx, self._shared_value(dim, ctx))[0].describe()
                    self.sink.add(dg.NO_FABRIC_COLOUR,
                                  f"no colour of {dim.name} is valid for the selected fabric type under some "
                                  f"selections; those configurations are rejected ({why})", dg.Severity.WARNING,
                                  article=self.model.base_code, property=dim.name)
                return
            if not candidates:
                self._note_no_value(dim)
                chosen.append(m.Assignment(dim, None, False))
                yield from visit(depth + 1)
                chosen.pop()
                return
            name = dim.name_upper
            if name in self._inert:
                candidates = candidates[:1]
            for value in candidates:
                values[name] = value.value
                chosen.append(m.Assignment(dim, value, False))
                if self._early_constraints_ok(schedule.get(depth, ()), ctx, dim, value):
                    yield from visit(depth + 1)
                chosen.pop()
                values.pop(name, None)
                if self.stats.truncated:
                    return

        yield from visit(0)
        if self.stats.truncated:
            self.sink.add(dg.ENUMERATION_TRUNCATED,
                          f"{self.stats.reason}; {self.stats.emitted} configuration(s) emitted, result is incomplete",
                          dg.Severity.ERROR, article=self.model.base_code)
        if self.progress is not None:
            self.progress(self.stats)

    def _fabric_type_selected(self, dim: m.PropertyDef, ctx: EvalContext) -> bool:
        return self._fabric.type_selected(dim.name_upper, ctx.values)

    def _is_hidden(self, dim: m.PropertyDef, ctx: EvalContext) -> bool:
        cls = self._classes.get(dim.class_name.upper())
        if cls is not None:
            for ref in self._of_type(cls.relations, m.PRECONDITION):
                if precondition_violated(self._tri(ref, ctx, f"class {cls.name}")):
                    return True
        for ref in self._of_type(dim.relations, m.PRECONDITION):
            if precondition_violated(self._tri(ref, ctx, f"property {dim.name}")):
                return True
        return False

    def _candidates(self, dim: m.PropertyDef, ctx: EvalContext) -> list[m.ValueDef]:
        """The values of ``dim`` whose preconditions hold now.

        The result is a function of the properties those preconditions read, so it is computed once per
        distinct state of just those properties instead of once per node (a colour list of hundreds of
        values depends on the fabric type alone, not on every finish chosen before it).
        """
        refs = self._candidate_refs.get(dim.key)
        if refs is None:
            return self._filter_values(dim, ctx)
        key = (dim.key, tuple(ctx.values.get(name) for name in refs))
        found = self._candidate_cache.get(key)
        if found is None:
            found = self._candidate_cache[key] = self._filter_values(dim, ctx)
        return found

    def _shared_value(self, dim: m.PropertyDef, ctx: EvalContext) -> str | None:
        """The value ``dim`` must take because it follows another fabric position (``None`` = not tied, or that
        position has no value in this configuration)."""
        source = self._tie_source.get(dim.name_upper)
        found = ctx.values.get(source) if source is not None else None
        return None if found is None else str(found)

    def _accepted(self, dim: m.PropertyDef, ctx: EvalContext) -> frozenset[str] | None:
        """For a colour that a later fabric position must share: the colour codes that position accepts, so the pick
        is valid in both (``None`` = no follower, or nothing to check)."""
        followers = self._followers.get(dim.name_upper)
        if not followers:
            return None
        accepted: frozenset[str] | None = None
        for follower in followers:
            follower_dim, shared_type = self._props_by_name.get(follower.colour_upper), ctx.values.get(follower.primary_type_upper)
            if follower_dim is None or shared_type is None:
                continue
            probe = EvalContext(values={**ctx.values, follower.type_upper: shared_type}, ban=ctx.ban, tables=ctx.tables)
            if self._is_hidden(follower_dim, probe):
                continue
            valid = frozenset(self._fabric.resolve(follower_dim, probe)[0].valid)
            accepted = valid if accepted is None else accepted & valid
        return accepted

    def _resolve_fabric(self, dim: m.PropertyDef, ctx: EvalContext) -> list[m.ValueDef]:
        """The one fabric colour of ``dim`` for this configuration (none if no colour is valid), explanation recorded."""
        resolution, chosen = self._fabric.resolve(dim, ctx, self._shared_value(dim, ctx), self._accepted(dim, ctx))
        self.stats.pruned += dict(resolution.rejected_counts).get(fr.REASON_PRECONDITION, 0)
        key = (dim.name_upper, resolution.type_value, resolution.selected, resolution.mechanism)
        if key not in self.fabric_resolutions and len(self.fabric_resolutions) < 5000:
            self.fabric_resolutions[key] = resolution
            if chosen:
                self.sink.add(dg.FABRIC_COLOUR_RESOLVED, resolution.describe(), dg.Severity.INFO,
                              article=self.model.base_code, property=dim.name)
            if resolution.uncertain:
                bad = next(r for r in resolution.rejected if r.reason in (fr.REASON_UNUSABLE, fr.REASON_UNSUPPORTED))
                self.sink.add(dg.FABRIC_COLOUR_UNCERTAIN,
                              f"{dim.name}: a colour relation cannot be interpreted safely, so the colour is not "
                              f"offered ({bad.value}: {bad.detail})", dg.Severity.WARNING,
                              article=self.model.base_code, property=dim.name)
        return chosen

    def _filter_values(self, dim: m.PropertyDef, ctx: EvalContext) -> list[m.ValueDef]:
        if dim.name_upper in self._fabric_colours:
            return self._resolve_fabric(dim, ctx)
        out = []
        shared = self._shared_value(dim, ctx)
        for value in dim.values:
            if dim.allowed_keys is not None and value.key not in dim.allowed_keys:
                continue
            if shared is not None and value.value != shared:
                self.stats.pruned += 1
                continue
            ok = True
            for ref in self._of_type(value.relations, m.PRECONDITION):
                if precondition_violated(self._tri(ref, ctx, f"value {dim.name}={value.value}")):
                    ok = False
                    self.stats.pruned += 1
                    break
            if ok:
                out.append(value)
        return out

    def _note_no_value(self, dim: m.PropertyDef) -> None:
        if dim.name_upper in self._no_value_reported:
            return
        self._no_value_reported.add(dim.name_upper)
        self.sink.add(dg.NO_VALID_VALUE,
                      f"no value of {dim.name} is valid under some selections; it is left unassigned there",
                      dg.Severity.INFO, article=self.model.base_code, property=dim.name)

    def _early_constraints_ok(self, constraints, ctx: EvalContext, dim, value) -> bool:
        for ref, owner, compiled in constraints:
            probe = EvalContext(values=ctx.values, ban=ctx.ban, tables=ctx.tables)
            result = run_constraint(compiled.node, probe)
            if result.evaluated and not result.satisfied:
                self.stats.pruned += 1
                if self.stats.pruned <= 50:
                    self.sink.add(dg.INVALID_CONFIGURATION, result.reason, dg.Severity.INFO,
                                  article=self.model.base_code, property=dim.name,
                                  value=value.value, relation=ref.name, source=owner)
                return False
        return True

    # ------------------------------------------------------------ verification
    def finalize(self, assignments: Sequence[m.Assignment], *,
                 extra_values: Mapping[str, object] | None = None) -> FinalResult:
        """Verify a complete configuration and compute actions, constraints, VARCONDs."""
        self._leaf_uncertain = False
        values: dict[str, object] = {str(k).upper(): v for k, v in (extra_values or {}).items()}
        for item in assignments:
            if item.value is not None and not item.hidden:
                values[item.prop.name_upper] = item.value.value
        rhs = self._rhs_values_factory(values, assignments) if self._rhs_values_factory else None
        ctx = EvalContext(values=values, ban=self.model.base_code, tables=self.model.tables, rhs_values=rhs)

        # Properties without enumerable values (e.g. a computed ``Code``) are still
        # part of the article: their actions run unless a precondition hides them.
        present = {a.prop.key for a in assignments}
        assignments = list(assignments) + [
            m.Assignment(prop, None, self._is_hidden(prop, ctx))
            for prop in self.model.properties if not prop.values and prop.key not in present
        ]

        self._computed_engine.run(assignments, ctx)

        failure = self._verify(assignments, ctx)
        if failure is not None:
            reason, relation = failure
            self.sink.add(dg.INVALID_CONFIGURATION, reason, dg.Severity.INFO,
                          article=self.model.base_code, relation=relation)
            return FinalResult(False, reason, relation, uncertain=self._leaf_uncertain)

        varconds = self._varcond_engine.run(assignments, ctx)
        return FinalResult(
            True, computed=dict(ctx.computed),
            varconds=list(ctx.varconds) + varconds.keys,
            pricing_factors=varconds.factors, uncertain=self._leaf_uncertain, context=ctx,
        )

    def _verify(self, assignments, ctx: EvalContext) -> tuple[str, str] | None:
        for item in assignments:
            prop, value = item.prop, item.value
            cls = self._classes.get(prop.class_name.upper())
            if not item.hidden and value is not None:
                if cls is not None:
                    for ref in self._of_type(cls.relations, m.PRECONDITION):
                        if precondition_violated(self._tri(ref, ctx, f"class {cls.name}")):
                            return (f"class precondition of {cls.name} is FALSE with {prop.name}={value.value}", ref.name)
                for ref in self._of_type(prop.relations, m.PRECONDITION):
                    if precondition_violated(self._tri(ref, ctx, f"property {prop.name}")):
                        return (f"precondition of property {prop.name} is FALSE", ref.name)
                for ref in self._of_type(value.relations, m.PRECONDITION):
                    if precondition_violated(self._tri(ref, ctx, f"value {prop.name}={value.value}")):
                        return (f"precondition of value {prop.name}={value.value} is FALSE", ref.name)
            if not item.hidden and value is None:
                for ref in self._of_type(prop.relations, m.SELECTION):
                    if selection_condition_met(self._tri(ref, ctx, f"property {prop.name}")):
                        return (f"selection condition of {prop.name} is met but the property has no value", ref.name)
        for ref, owner, compiled in self._constraints:
            try:
                result = run_constraint(compiled.node, ctx)
            except EvalError as error:
                self._report_bad(ref, str(error), owner, dg.RELATION_EVAL_ERROR)
                continue
            if result.evaluated and not result.satisfied:
                return (f"constraint violated: {result.reason}", ref.name)
        return None

    # ------------------------------------------------------------ convenience
    def view(self, assignments, computed: Mapping[str, object] | None = None) -> ConfigView:
        return ConfigView(self.model, assignments, computed or {})

    def generate(self, dimensions: Sequence[m.PropertyDef] | None = None, *,
                 base_values: Mapping[str, object] | None = None):
        """Yield ``(Configuration, FinalResult)`` for every valid configuration."""
        for config in self.enumerate(dimensions, base_values=base_values):
            result = self.finalize(config.assignments, extra_values=base_values)
            if result.valid:
                yield config, result
