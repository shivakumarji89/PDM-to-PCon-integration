"""Variant conditions (``$VARCOND``) from price-domain relations (spec 3.2).

Price relations are actions in domain ``P``. ``$VARCOND`` is multivalued: every
assignment contributes one key, so the result is a list, never one overwritten
string. Keys are upper-cased because the price table is matched in upper case.
An assignment whose operands are undefined (e.g. a hidden property) assigns
nothing - which is exactly how Dalby omits the 6821/7030 keys on articles
that lack Access_Cutout / Cable_leg.

Optional result cache (``cache=True``, off by default)
-------------------------------------------------------
Evaluating every price relation for every configuration dominates generation time, yet the result is a
pure function of what the relations can read. ``run`` is memoised on exactly that:

* the ordered list of relations in scope (article/class relations are fixed, property and value relations
  depend on which properties are visible and which values are selected),
* the values of every name those relations mention, expanded the way ``EvalContext.resolve`` can reach them
  (the name, its alias target, its qualifier tail and that tail's alias) - absent and ``None`` are told apart,
* the entries of ``computed`` under those same names (computed properties are produced by other relations and
  constraints, so a relation reading one is keyed on its value; entries under names no relation can look up -
  e.g. a ``Code`` that is unique per configuration - cannot influence the result and are left out) and the
  ``aliases``,
* ``$BAN``; the value-combination tables are pinned by identity (the first ``tables`` object seen is kept, and a
  context carrying a different one bypasses the cache).

``rhs_values`` is not part of the key because the price context never receives it. A run is only stored
when it was clean (no parse error, no skipped clause), because the sink counts every diagnostic and a hit
would silently drop them; a relation whose AST cannot be walked bypasses the cache. The cache belongs to one
engine instance (one article model, one generation run) and holds immutable values only.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

from services.ocd_engine import diagnostics as dg
from services.ocd_engine import model as m
from services.ocd_engine import relation_parser as rp
from services.ocd_engine.computed_property_engine import execute_relations, relations_in_scope
from services.ocd_engine.relation_evaluator import EvalContext

#: Stops the cache growing without bound on a pathological article; beyond it results are simply not stored.
MAX_CACHE_ENTRIES = 250_000
_ABSENT = object()


@dataclass
class VarcondResult:
    keys: list[str] = field(default_factory=list)
    factors: dict[str, float] = field(default_factory=dict)


class _Uncacheable(Exception):
    """An AST node the dependency walk does not understand: its reads cannot be enumerated."""


def _read_names(node, into: set[str]) -> None:
    """Every name an AST can look up (properties, ``SPECIFIED`` targets, ``$`` variables), by construction.

    Walks all dataclass fields so a node type added to the parser later is covered; anything that is not a
    plain value, container or AST dataclass raises :class:`_Uncacheable`.
    """
    if isinstance(node, (rp.PropRef, rp.Specified, rp.SysVar)):
        into.add(node.name.upper())
    elif dataclasses.is_dataclass(node) and not isinstance(node, type):
        for item in dataclasses.fields(node):
            _read_names(getattr(node, item.name), into)
    elif isinstance(node, (tuple, list)):
        for item in node:
            _read_names(item, into)
    elif node is None or isinstance(node, (str, int, float, bool)):
        return
    else:
        raise _Uncacheable(type(node).__name__)


class VarcondEngine:
    def __init__(self, model: m.ArticleModel, sink: dg.DiagnosticSink | None = None, *,
                 cache: bool = False, verify_every: int = 0) -> None:
        """``verify_every=N`` (with ``cache``): re-evaluate every Nth hit and raise if the cached result differs."""
        self.model = model
        self.sink = sink
        self._cache_enabled = cache
        self._verify_every = verify_every
        self._cache: dict[tuple, tuple[tuple[str, ...], tuple[tuple[str, float], ...]]] = {}
        self._reads: dict[int, tuple[object, frozenset[str] | None]] = {}   # id(relation) -> (relation, names)
        self._names: dict[tuple, tuple[str, ...]] = {}
        self._tables: object = None            # the value-combination tables the cached results were computed with
        # counters, always kept: they are what the benchmark reads
        self.runs = 0                    # configurations evaluated
        self.relation_evaluations = 0    # relations actually executed (misses, bypasses, uncached engine)
        self.cache_hits = 0
        self.cache_misses = 0            # evaluated and stored
        self.cache_bypassed = 0          # not cacheable (unanalysable relation, unhashable state)
        self.cache_unclean = 0           # evaluated but produced diagnostics, so never stored
        self.cache_full = 0              # clean results not stored because the cache is at its cap
        self.cache_verified = 0

    # ------------------------------------------------------------------ evaluation
    @staticmethod
    def _price_context(ctx: EvalContext) -> EvalContext:
        # Price relations may only touch auxiliary properties (spec 2.15), so
        # they run on a copy: nothing they assign may leak into the configuration.
        return EvalContext(
            values=ctx.values, ban=ctx.ban, tables=ctx.tables,
            aliases=dict(ctx.aliases), computed=dict(ctx.computed),
        )

    def _execute(self, scoped, ctx: EvalContext, *, count: bool = True) -> tuple[VarcondResult, bool]:
        price_ctx = self._price_context(ctx)
        if count:
            self.relation_evaluations += len(scoped)
        clean = execute_relations(scoped, price_ctx, self.sink, self.model.base_code)
        # de-duplicate, keep first-seen order: "not defined whether applied once or per relation" (3.2)
        return VarcondResult(list(dict.fromkeys(price_ctx.varconds)), dict(price_ctx.pricing_factors)), clean

    def run(self, assignments, ctx: EvalContext) -> VarcondResult:
        scoped = relations_in_scope(self.model, assignments, m.ACTION, "P")
        self.runs += 1
        if not self._cache_enabled:
            return self._execute(scoped, ctx)[0]
        key = self._key(scoped, ctx)
        if key is None:
            self.cache_bypassed += 1
            return self._execute(scoped, ctx)[0]
        found = self._cache.get(key)
        if found is not None:
            self.cache_hits += 1
            result = VarcondResult(list(found[0]), dict(found[1]))
            if self._verify_every and self.cache_hits % self._verify_every == 0:
                self.cache_verified += 1
                fresh = self._execute(scoped, ctx, count=False)[0]
                if fresh.keys != result.keys or fresh.factors != result.factors:
                    raise RuntimeError(
                        f"price relation cache mismatch for {self.model.base_code}: cached "
                        f"{result.keys}/{result.factors}, evaluated {fresh.keys}/{fresh.factors}")
            return result
        result, clean = self._execute(scoped, ctx)
        if not clean:
            self.cache_unclean += 1
        elif len(self._cache) >= MAX_CACHE_ENTRIES:
            self.cache_full += 1
        else:
            self.cache_misses += 1
            self._cache[key] = (tuple(result.keys), tuple(result.factors.items()))
        return result

    # ------------------------------------------------------------------ cache key
    def _relation_reads(self, relation) -> frozenset[str] | None:
        entry = self._reads.get(id(relation))
        if entry is None:
            compiled = rp.compile_relation(relation.rel_type, relation.text)
            names: frozenset[str] | None = None
            if not compiled.error:
                try:
                    found: set[str] = set()
                    _read_names(compiled.node, found)
                    names = frozenset(found)
                except _Uncacheable:
                    names = None
            # the relation object is kept alongside so its id() cannot be reused while cached
            entry = self._reads[id(relation)] = (relation, names)
        return entry[1]

    def _key(self, scoped, ctx: EvalContext) -> tuple | None:
        if self._tables is None:
            self._tables = ctx.tables
        elif ctx.tables is not self._tables:
            return None
        reads = []
        for relation, _owner in scoped:
            names = self._relation_reads(relation)
            if names is None:
                return None
            reads.append(names)
        scope = tuple(id(relation) for relation, _ in scoped)
        aliases = tuple(sorted(ctx.aliases.items()))
        names_key = (scope, aliases)
        lookup_names = self._names.get(names_key)
        if lookup_names is None:
            alias_map = dict(aliases)
            wanted: set[str] = set()
            for names in reads:
                for name in names:
                    wanted.add(name)
                    wanted.add(alias_map.get(name, name))
                    if "." in name:
                        tail = name.rsplit(".", 1)[1]
                        wanted.add(tail)
                        wanted.add(alias_map.get(tail, tail))
            lookup_names = self._names[names_key] = tuple(sorted(wanted))
        values, computed = ctx.values, ctx.computed
        # Every read is lookup(name) for a name in ``lookup_names``, answered from ``computed`` first, else ``values``.
        # Type-tagged so that 1, 1.0 and True (equal as dict keys, different to the evaluator) never share a key.
        deps = tuple(v if v is _ABSENT or isinstance(v, str) else (type(v), v)
                     for v in (values.get(name, _ABSENT) for name in lookup_names))
        derived = tuple(v if v is _ABSENT or isinstance(v, str) else (type(v), v)
                        for v in (computed.get(name, _ABSENT) for name in lookup_names))
        key = (scope, aliases, ctx.ban, deps, derived)
        try:
            hash(key)
        except TypeError:
            return None
        return key

    # ------------------------------------------------------------------ reporting
    def stats(self) -> dict[str, int]:
        return {
            "runs": self.runs, "relationEvaluations": self.relation_evaluations,
            "cacheHits": self.cache_hits, "cacheMisses": self.cache_misses,
            "cacheBypassed": self.cache_bypassed, "cacheUnclean": self.cache_unclean,
            "cacheFull": self.cache_full, "cacheVerified": self.cache_verified,
            "cacheEntries": len(self._cache),
        }
