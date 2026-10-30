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

from dataclasses import dataclass, field
from typing import Callable, Iterator, Mapping, Sequence

from core.cancellation import checkpoint
from services.ocd_engine import diagnostics as dg
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


def _tail(name: str) -> str:
    return name.rsplit(".", 1)[-1]


class ConfigurationEngine:
    def __init__(self, model: m.ArticleModel, *, sink: dg.DiagnosticSink | None = None,
                 limits: EnumerationLimits | None = None,
                 progress: Callable[[EnumerationStats], None] | None = None,
                 rhs_values_factory: Callable[[Mapping[str, str], Sequence[m.Assignment]], dict] | None = None,
                 progress_every: int = 5000) -> None:
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

    # ------------------------------------------------------------ relation helpers
    def _tri(self, ref: m.RelationRef, ctx: EvalContext, owner: str) -> Tri:
        compiled = rp.compile_relation(m.PRECONDITION if ref.rel_type in (1, 2) else ref.rel_type, ref.text)
        if compiled.error:
            self._report_bad(ref, compiled.error, owner, dg.RELATION_PARSE_ERROR)
            return Tri.UNDEFINED
        try:
            return eval_cond(compiled.node, ctx)
        except EvalError as error:
            self._report_bad(ref, str(error), owner, dg.RELATION_EVAL_ERROR)
            return Tri.UNDEFINED

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

    # ------------------------------------------------------------ ordering
    def _prepare(self, dimensions: Sequence[m.PropertyDef]):
        names = {d.name_upper: i for i, d in enumerate(dimensions)}
        deps: list[set[str]] = []
        for dim in dimensions:
            refs: set[str] = set()
            relations = list(self._of_type(dim.relations, m.PRECONDITION)) + \
                list(self._of_type(dim.relations, m.SELECTION))
            cls = self._classes.get(dim.class_name.upper())
            if cls is not None:
                relations += self._of_type(cls.relations, m.PRECONDITION)
            for value in dim.values:
                relations += self._of_type(value.relations, m.PRECONDITION)
                relations += self._of_type(value.relations, m.SELECTION)
            for ref in relations:
                compiled = rp.compile_relation(m.PRECONDITION, ref.text)
                refs |= {_tail(r) for r in compiled.refs}
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
        dims = [d for d in (dimensions if dimensions is not None else self.model.properties) if d.values]
        ordered = self._prepare(dims)
        schedule = self._constraint_schedule(ordered)
        self.stats = EnumerationStats()
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
            if not candidates:
                self._note_no_value(dim)
                chosen.append(m.Assignment(dim, None, False))
                yield from visit(depth + 1)
                chosen.pop()
                return
            name = dim.name_upper
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
        out = []
        for value in dim.values:
            if dim.allowed_keys is not None and value.key not in dim.allowed_keys:
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
