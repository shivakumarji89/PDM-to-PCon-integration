"""Price-relation result cache (``VarcondEngine(cache=True)``): equal inputs reuse, any dependency change misses,
nothing is shared between contexts, results cannot be mutated through the cache, diagnostics and cancellation
behave as without it, and cached and uncached runs produce identical output."""
import pytest

from core.cancellation import CancellationToken, OperationCancelled, cancellation_scope
from services.ocd_engine import diagnostics as dg
from services.ocd_engine import model as m
from services.ocd_engine import relation_parser as rp
from services.ocd_engine import varcond_engine as ve
from services.ocd_engine.configuration_engine import ConfigurationEngine
from services.ocd_engine.generator import OcdArticleGenerator
from services.ocd_engine.relation_evaluator import EvalContext
from services.ocd_engine.varcond_engine import VarcondEngine
from ocd_helpers import model, prop, rel, val
from ocd_repo_fixture import write_demo_range


T = {}      # one shared tables object, as a real engine always passes


def price(text, **kw):
    return rel(text, rel_type=3, domain="P", **kw)


def results(mdl, **kwargs):
    engine = ConfigurationEngine(mdl, **kwargs)
    out = [(tuple((a.prop.name, a.value.value if a.value else None, a.hidden) for a in c.assignments),
            r.varconds, dict(r.pricing_factors), dict(r.computed))
           for c, r in engine.generate()]
    return out, engine


def both(mdl):
    plain, plain_engine = results(mdl)
    cached, cached_engine = results(mdl, price_relation_cache=True, price_cache_verify_every=1)
    assert cached == plain                                   # same rows, same order, same varconds/factors/computed
    assert len(cached_engine.sink) == len(plain_engine.sink)  # same diagnostics count
    return cached_engine.price_relation_stats, plain_engine.price_relation_stats


# ------------------------------------------------------------------ reuse and invalidation
def test_identical_relation_inputs_reuse_the_result():
    mdl = model("B", [prop("A", ["1", "2", "3"]), prop("Other", ["x", "y"])],
                article_relations=[price("$VARCOND = 'A=' + A")])
    cached, plain = both(mdl)
    assert (plain["runs"], plain["relationEvaluations"], plain["cacheHits"]) == (6, 6, 0)
    assert (cached["runs"], cached["cacheMisses"], cached["cacheHits"]) == (6, 3, 3)
    assert cached["relationEvaluations"] == 3 and cached["cacheVerified"] == 3


def test_a_change_in_any_read_property_is_a_miss():
    mdl = model("B", [prop("A", ["1", "2"]), prop("B2", ["x", "y"])],
                article_relations=[price("$VARCOND = A + B2")])
    cached, _ = both(mdl)
    assert (cached["cacheHits"], cached["cacheMisses"]) == (0, 4)


def test_conditions_and_specified_reads_are_dependencies():
    mdl = model("B", [prop("A", ["1", "2"]), prop("Opt", ["on", "off"]), prop("Z", ["q", "r"])],
                article_relations=[price("$VARCOND = 'S', $VARCOND = 'ON' IF Opt = 'on', $VARCOND = 'SET' IF SPECIFIED Opt")])
    cached, _ = both(mdl)
    assert cached["cacheMisses"] == 2 and cached["cacheHits"] == 6    # only Opt matters: 2 distinct inputs of 8



def test_computed_inputs_are_part_of_the_key():
    """The price relation reads only Aux; Aux is computed from B2 by a configuration-domain relation."""
    mdl = model("B", [prop("A", ["1", "2"]), prop("B2", ["x", "y"])],
                article_relations=[rel("Aux = B2", rel_type=3, domain="C"), price("$VARCOND = 'K=' + Aux")])
    out, _ = results(mdl, price_relation_cache=True)
    assert {tuple(v) for _, v, _, _ in out} == {("K=X",), ("K=Y",)}
    cached, _ = both(mdl)
    assert cached["cacheMisses"] == 2 and cached["cacheHits"] == 2


def test_computed_values_no_relation_reads_do_not_defeat_sharing():
    """A computed property unique to every configuration (like PEP100's Code) must not stop equal inputs sharing."""
    mdl = model("B", [prop("A", ["1", "2"]), prop("B2", ["x", "y", "z"])],
                article_relations=[rel("Tag = A + B2", rel_type=3, domain="C"), price("$VARCOND = 'A=' + A")])
    out, _ = results(mdl, price_relation_cache=True)
    assert len({c["TAG"] for _, _, _, c in out}) == 6                      # one computed value per configuration
    cached, _ = both(mdl)
    assert cached["cacheMisses"] == 2 and cached["cacheHits"] == 4


def test_selected_values_and_visible_properties_change_the_relation_scope():
    """Value/property relations are only in scope when selected/visible, so the same read values can still differ."""
    vr = price("$VARCOND = 'VAL'")
    pr = price("$VARCOND = 'PROP'")
    mdl = model("B", [prop("A", [val("x", rels=[vr]), val("y")], rels=[pr]), prop("C", ["1", "2"])],
                article_relations=[price("$VARCOND = 'ART'")])
    out, _ = results(mdl, price_relation_cache=True)
    by_a = {dict((n, v) for n, v, _ in cfg)["A"]: list(varconds) for cfg, varconds, _, _ in out}
    assert by_a == {"x": ["ART", "PROP", "VAL"], "y": ["ART", "PROP"]}
    both(mdl)


def test_pricing_factors_are_cached_and_equal():
    mdl = model("B", [prop("A", ["1", "2"]), prop("Other", ["x", "y"])],
                article_relations=[price("$SET_PRICING_FACTOR('F', 1.5) IF A = '2', $VARCOND = 'A=' + A")])
    both(mdl)
    out, _ = results(mdl, price_relation_cache=True)
    assert [f for _, _, f, _ in out if f] == [{"F": 1.5}, {"F": 1.5}]



# ------------------------------------------------------------------ contexts are never shared
def _engine(text, base="B", cache=True):
    return VarcondEngine(model(base, [prop("A", ["1"])], article_relations=[price(text)]), cache=cache)


def test_ban_and_tables_are_part_of_the_key():
    engine = _engine("$VARCOND = $BAN")
    tables = {}
    a = engine.run([], EvalContext(values={}, ban="ART1", tables=tables))
    b = engine.run([], EvalContext(values={}, ban="ART2", tables=tables))
    assert (a.keys, b.keys) == (["ART1"], ["ART2"])
    assert engine.cache_hits == 0 and engine.cache_misses == 2


def test_two_articles_with_the_same_property_names_never_share_results():
    first = ConfigurationEngine(model("ONE", [prop("A", ["1"])], article_relations=[price("$VARCOND = 'X' + A")]),
                                price_relation_cache=True)
    second = ConfigurationEngine(model("TWO", [prop("A", ["1"])], article_relations=[price("$VARCOND = 'Y' + A")]),
                                 price_relation_cache=True)
    (a,) = [r.varconds for _, r in first.generate()]
    (b,) = [r.varconds for _, r in second.generate()]
    assert (a, b) == (["X1"], ["Y1"])
    assert first.price_relation_stats["cacheHits"] == second.price_relation_stats["cacheHits"] == 0


def test_aliases_are_part_of_the_key():
    engine = _engine("$VARCOND = 'V=' + P")
    one = engine.run([], EvalContext(tables=T, values={"A": "1", "B": "2"}, aliases={"P": "A"}))
    two = engine.run([], EvalContext(tables=T, values={"A": "1", "B": "2"}, aliases={"P": "B"}))
    assert (one.keys, two.keys) == (["V=1"], ["V=2"])
    assert engine.cache_bypassed == 0


def test_qualified_names_resolve_through_their_tail():
    engine = _engine("$VARCOND = 'V=' + S.Size")
    one = engine.run([], EvalContext(tables=T, values={"SIZE": "L"}))
    two = engine.run([], EvalContext(tables=T, values={"SIZE": "S"}))
    assert (one.keys, two.keys) == (["V=L"], ["V=S"]) and engine.cache_hits == 0
    assert engine.cache_bypassed == 0


def test_absent_and_empty_values_are_different_inputs():
    engine = _engine("$VARCOND = 'SET' IF SPECIFIED A")
    absent = engine.run([], EvalContext(tables=T, values={}))
    empty = engine.run([], EvalContext(tables=T, values={"A": ""}))
    present = engine.run([], EvalContext(tables=T, values={"A": "1"}))
    assert (absent.keys, empty.keys, present.keys) == ([], [], ["SET"]) and engine.cache_hits == 0
    assert engine.cache_bypassed == 0


def test_equal_looking_values_of_different_type_do_not_share_a_key():
    reading = _engine("$VARCOND = 'V=' + STRING(A)")
    tables = {}
    keys = {reading._key(engine_scope(reading), EvalContext(values={"A": v}, tables=tables))
            for v in (1, 1.0, True, "1")}
    assert len(keys) == 4


def engine_scope(engine):
    return [(r, "article") for r in engine.model.article_relations]


# ------------------------------------------------------------------ immutability
def test_mutating_a_returned_result_does_not_change_later_hits():
    engine = _engine("$VARCOND = 'K', $SET_PRICING_FACTOR('F', 2)")
    assert engine.run([], EvalContext(values={"A": "1"})).factors == {"F": 2.0}      # the statement is valid
    engine = _engine("$VARCOND = 'K', $SET_PRICING_FACTOR('F', 2)")
    tables = {}
    ctx = lambda: EvalContext(values={"A": "1"}, tables=tables)                     # noqa: E731
    first = engine.run([], ctx())
    first.keys.append("POISON")
    first.factors["POISON"] = 9.0
    second = engine.run([], ctx())
    third = engine.run([], ctx())
    assert engine.cache_hits == 2 and engine.cache_misses == 1
    assert second.keys == third.keys == ["K"] and "POISON" not in second.factors
    assert second.keys is not third.keys and second.factors is not third.factors


# ------------------------------------------------------------------ diagnostics, errors, bypass
@pytest.mark.parametrize("text", [
    "$VARCOND = STRING('x')",                 # EvalError at run time -> skipped clause
    "$VARCOND = 'a' +",                       # parse error
    "IF A = 1 THEN FROBNICATE(A)",            # unsupported statement
])
def test_relations_that_report_are_never_cached_and_keep_their_diagnostics(text):
    mdl = model("B", [prop("A", ["1", "2", "3"])], article_relations=[price(text), price("$VARCOND = 'OK'")])
    plain, plain_engine = results(mdl)
    cached, cached_engine = results(mdl, price_relation_cache=True)
    assert cached == plain
    assert len(cached_engine.sink) == len(plain_engine.sink) > 0          # one report per configuration, as before
    stats = cached_engine.price_relation_stats
    assert stats["cacheHits"] == 0 and stats["cacheMisses"] == 0 and stats["cacheUnclean"] + stats["cacheBypassed"] == 3


def test_unanalysable_relation_bypasses_the_cache(monkeypatch):
    real = rp.compile_relation

    def compile_with_unknown_node(rel_type, text):
        compiled = real(rel_type, text)
        return rp.CompiledRelation(compiled.rel_type, [object()], compiled.refs) if text == "$VARCOND = 'W'" else compiled

    monkeypatch.setattr(ve.rp, "compile_relation", compile_with_unknown_node)
    engine = _engine("$VARCOND = 'W'")
    engine.run([], EvalContext(values={}))
    engine.run([], EvalContext(values={}))
    assert (engine.cache_bypassed, engine.cache_hits, engine.cache_misses) == (2, 0, 0)
    assert engine.relation_evaluations == 2


def test_a_different_tables_object_bypasses_the_cache():
    engine = _engine("$VARCOND = 'V'")
    engine.run([], EvalContext(values={}, tables={}))
    engine.run([], EvalContext(values={}, tables={"T": object()}))
    assert (engine.cache_misses, engine.cache_bypassed) == (1, 1)


def test_unhashable_state_bypasses_the_cache():
    engine = _engine("$VARCOND = 'V' IF SPECIFIED X")
    engine.run([], EvalContext(values={}, computed={"X": [1]}))       # X is read and cannot be hashed
    assert engine.cache_bypassed == 1


def test_verify_mode_detects_a_corrupt_entry():
    mdl = model("B", [prop("A", ["1", "2"]), prop("Other", ["x", "y"])],
                article_relations=[price("$VARCOND = 'A=' + A")])
    engine = ConfigurationEngine(mdl, price_relation_cache=True, price_cache_verify_every=1)
    cache = engine._varcond_engine._cache
    gen = engine.generate()
    next(gen)
    for key in cache:
        cache[key] = (("WRONG",), ())
    with pytest.raises(RuntimeError, match="cache mismatch"):
        list(gen)


def test_cache_cap_stops_storing_but_keeps_results_correct(monkeypatch):
    monkeypatch.setattr(ve, "MAX_CACHE_ENTRIES", 2)
    mdl = model("B", [prop("A", [str(i) for i in range(5)])], article_relations=[price("$VARCOND = 'A=' + A")])
    plain, _ = results(mdl)
    cached, engine = results(mdl, price_relation_cache=True)
    assert cached == plain and engine.price_relation_stats["cacheFull"] == 3


# ------------------------------------------------------------------ cancellation and cache-off parity
def test_cancellation_is_honoured_with_the_cache_on():
    token = CancellationToken()
    mdl = model("B", [prop("A", [str(i) for i in range(50)]), prop("B2", [str(i) for i in range(50)])],
                article_relations=[price("$VARCOND = 'A=' + A")])
    engine = ConfigurationEngine(mdl, price_relation_cache=True)
    seen = 0
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        for _ in engine.generate():
            seen += 1
            if seen == 10:
                token.request_cancel()
    assert seen < 2500


def test_cache_is_off_by_default():
    engine = ConfigurationEngine(model("B", [prop("A", ["1", "2"])], article_relations=[price("$VARCOND = 'K'")]))
    list(engine.generate())
    stats = engine.price_relation_stats
    assert stats["relationEvaluations"] == 2 and stats["cacheHits"] == stats["cacheMisses"] == 0


# ------------------------------------------------------------------ generator level
def test_generator_output_is_identical_with_and_without_the_cache(tmp_path):
    generator = OcdArticleGenerator(write_demo_range(tmp_path))
    plain = generator.generate(["CHAIR1"], currency="EUR", price_date="2026-01-15", price_relation_cache=False)
    cached = generator.generate(["CHAIR1"], currency="EUR", price_date="2026-01-15", price_cache_verify_every=1)
    assert cached.skus == plain.skus                                         # every field, order included
    assert (cached.warnings, cached.invalid, cached.duplicates, cached.configurations, cached.nodes, cached.pruned) \
        == (plain.warnings, plain.invalid, plain.duplicates, plain.configurations, plain.nodes, plain.pruned)
    assert plain.price_relation_stats["cacheHits"] == 0
    assert cached.price_relation_stats["runs"] == plain.price_relation_stats["runs"] == cached.configurations
