"""Baseline vs. probe-reuse equivalence for ``ConfigurationEnumerator.cs``.

The C# enumerator talks to the live pCon.planner SDK, which cannot run here and
cannot be faked without re-implementing the X3g interfaces. This module holds a
line-by-line port of ``Enumerate`` in both shapes:

* ``reuse=False`` - the original: every node inserts a probe, replays the whole
  prefix, reads the live property list, discards the probe if it is not a leaf.
* ``reuse=True``  - the optimisation: a non-leaf probe is handed to its FIRST
  child, which applies only its one new value; siblings still insert + replay.

The model is a pCon-like dependent product (Material -> Finish, Arm appears for
Metal, a relation that rewrites an earlier choice). It proves the algorithm is
output-equivalent and leak-free. It does NOT prove SDK behaviour: the one
assumption it cannot test (reads between SetValue calls do not perturb pCon's
relation evaluation) needs the real host - see the benchmark steps in
``docs/04_Reference/pCon/Enumerator_Probe_Reuse_Benchmark.md``.

Run ``python -I tests/test_pcon_enumerator_probe_reuse.py`` for the count table.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Callable

import pytest


# --------------------------------------------------------------------------- model
class Planning:
    """Entity bookkeeping: what is left in the pCon planning after a run."""

    def __init__(self) -> None:
        self.entities: dict[int, str] = {}
        self.open_instances = 0
        self.max_open_instances = 0
        self._ids = itertools.count(1)
        self.fail_insert_for: set[str] = set()
        self.fail_properties_on_call: int | None = None
        self.properties_calls = 0
        self.value_set_reads = 0

    def insert(self, article: "Spec") -> "Probe":
        if article.number in self.fail_insert_for:
            raise RuntimeError(f"pCon.planner could not insert article {article.number}")
        probe = Probe(self, next(self._ids), article)
        self.entities[probe.entity_id] = article.number
        self.open_instances += 1
        self.max_open_instances = max(self.max_open_instances, self.open_instances)
        return probe


@dataclass
class Spec:
    """Product model. ``rules`` run after every SetValue, like OFML relations."""

    number: str
    initial: dict[str, str]
    choices: Callable[[dict[str, str], str], list[str]]
    after_set: Callable[[dict[str, str], str, str], None] = lambda values, key, value: None
    final: Callable[[dict[str, str]], str] = lambda values: ""


class Probe:
    def __init__(self, planning: Planning, entity_id: int, spec: Spec) -> None:
        self.planning, self.entity_id, self.spec = planning, entity_id, spec
        self.values = dict(spec.initial)
        self.closed = False

    def keys(self) -> list[str]:
        self.planning.properties_calls += 1
        if self.planning.fail_properties_on_call == self.planning.properties_calls:
            raise RuntimeError("SDK property list unavailable")
        return list(self.values)

    def value_set(self, key: str) -> list[str]:
        self.planning.value_set_reads += 1
        return list(self.spec.choices(self.values, key))

    def set_value(self, key: str, value: str) -> bool:
        if key not in self.values or value not in self.spec.choices(self.values, key):
            return False
        self.values[key] = value
        self.spec.after_set(self.values, key, value)
        return True

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            self.planning.open_instances -= 1

    def discard(self) -> None:
        self.close()
        self.planning.entities.pop(self.entity_id, None)



# ------------------------------------------------------------------ enumerator port
@dataclass
class Result:
    rows: list[tuple[str, tuple[tuple[str, str], ...]]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    skipped: int = 0
    duplicates: int = 0
    visited: int = 0
    truncated: bool = False
    cancelled: bool = False
    probe_insertions: int = 0
    property_applications: int = 0
    replay_applications: int = 0          # SetValue calls replaying a prefix on a fresh probe
    incremental_applications: int = 0     # SetValue calls on a handed-over probe
    leaves: int = 0
    internal_nodes: int = 0
    branch_sum: int = 0
    visits_by_depth: list[int] = field(default_factory=list)
    inserts_by_depth: list[int] = field(default_factory=list)

    def _bump(self, series: list[int], depth: int) -> None:
        while len(series) <= depth:
            series.append(0)
        series[depth] += 1

    @property
    def finals(self) -> list[str]:
        return [final for final, _ in self.rows]


class Enumerator:
    def __init__(self, planning: Planning, spec: Spec, *, reuse: bool, max_configs: int = 500,
                 fixed: tuple[tuple[str, str], ...] = (), excluded: frozenset[str] = frozenset(),
                 deduplicate: bool = True, cancel: Callable[[], bool] = lambda: False,
                 legacy_reads: bool | None = None) -> None:
        """``reuse`` is MK_OBX_REUSE_PROBE, ``legacy_reads`` is MK_OBX_LEGACY_READS. By default
        ``legacy_reads`` follows ``not reuse`` (the original baseline); pass it explicitly to model the
        shipped ``MK_OBX_REUSE_PROBE=0`` build, which keeps the ValueSet-read saving."""
        self.p, self.spec, self.reuse = planning, spec, reuse
        self.legacy_reads = (not reuse) if legacy_reads is None else legacy_reads
        self.max, self.fixed, self.excluded = max_configs, fixed, excluded
        self.dedup, self.cancel_cb = deduplicate, cancel
        self.r = Result()
        self.seen: set[str] = set()

    def run(self) -> Result:
        prefix = list(self.fixed)
        assigned = {k for k, _ in prefix}
        self.enumerate(prefix, assigned, None)
        return self.r

    # -- counted SDK operations
    def _insert(self) -> Probe:
        self.r.probe_insertions += 1
        return self.p.insert(self.spec)

    def _apply(self, probe: Probe, key: str, value: str, just_read: bool = False) -> tuple[bool, str]:
        self.r.property_applications += 1
        if key not in probe.values:
            return False, f"Property {key} is not available for this configuration."
        if (not just_read or self.legacy_reads) and value not in probe.value_set(key):  # Offers(): a second ValueSet read
            return False, f"Value {value} is not offered for {key} in this configuration."
        return (True, "") if probe.set_value(key, value) else (False, f"rejected {key}={value}")

    def _cancelled(self) -> bool:
        if self.r.cancelled:
            return True
        if self.cancel_cb():
            self.r.cancelled = True
            self.r.warnings.append("Generation cancelled by the Workbench.")
        return self.r.cancelled

    def _next(self, probe: Probe, assigned: set[str]) -> tuple[str | None, list[str]]:
        for key in probe.keys():
            if key in assigned or key in self.excluded:
                continue
            values = probe.value_set(key)  # IsVariable -> ChoiceKeys
            if values:
                return key, values
        return None, []

    def enumerate(self, prefix: list[tuple[str, str]], assigned: set[str], inherited: Probe | None) -> None:
        probe, released = inherited, False
        try:
            if self._cancelled():
                return
            if len(self.r.rows) >= self.max:
                self.r.truncated = True
                return
            self.r.visited += 1
            depth = len(prefix)
            self.r._bump(self.r.visits_by_depth, depth)
            if probe is None:
                try:
                    self.r._bump(self.r.inserts_by_depth, depth)
                    probe = self._insert()
                except RuntimeError as exc:
                    self.r.skipped += 1
                    self.r.warnings.append(f"{self.spec.number}: {exc}")
                    return
                for key, value in prefix:
                    self.r.replay_applications += 1
                    ok, error = self._apply(probe, key, value)
                    if not ok:
                        self.r.skipped += 1
                        self.r.warnings.append(f"{self.spec.number} {prefix}: {error}")
                        return
            else:
                key, value = prefix[-1]
                self.r.incremental_applications += 1
                ok, error = self._apply(probe, key, value, just_read=True)
                if not ok:
                    self.r.skipped += 1
                    self.r.warnings.append(f"{self.spec.number} {prefix}: {error}")
                    return

            key, values = self._next(probe, assigned)
            if self.legacy_reads and key is not None:
                probe.value_set(key)  # original code read ChoiceKeys(next) a second time
            if key is None:
                self.r.leaves += 1
                for fkey, fvalue in self.fixed:
                    ok, error = self._apply(probe, fkey, fvalue)
                    if not ok:
                        self.r.skipped += 1
                        self.r.warnings.append(f"{self.spec.number} {prefix}: {error}")
                        return
                for akey, avalue in prefix:
                    if probe.values.get(akey) != avalue:
                        self.r.skipped += 1
                        self.r.warnings.append(f"{self.spec.number} {prefix}: {akey}={avalue} "
                                               f"changed by relations to {probe.values.get(akey)}")
                        return
                final = self.spec.final(probe.values)
                if self.dedup and final and final in self.seen:
                    self.r.duplicates += 1
                    return
                self.seen.add(final)
                probe.close()
                released = True
                self.r.rows.append((final, tuple(prefix)))
                return

            self.r.internal_nodes += 1
            self.r.branch_sum += len(values)
            carry = probe if self.reuse else None
            if not self.reuse:
                probe.discard()
            released = True
            try:
                for value in values:
                    if self._cancelled():
                        return
                    if len(self.r.rows) >= self.max:
                        self.r.truncated = True
                        return
                    prefix.append((key, value))
                    assigned.add(key)
                    handoff, carry = carry, None
                    try:
                        self.enumerate(prefix, assigned, handoff)
                    finally:
                        assigned.discard(key)
                        prefix.pop()
            finally:
                if carry is not None:
                    carry.discard()
        finally:
            if not released and probe is not None:
                probe.discard()


# ------------------------------------------------------------------------ products
def _chair_choices(values: dict[str, str], key: str) -> list[str]:
    if key == "Material":
        return ["Wood", "Metal"]
    if key == "Finish":
        return ["Silver"] if values.get("Material") == "Metal" else ["Oak", "Walnut"]
    if key == "Arm":
        return ["Fixed", "Adjustable"]
    if key == "Size":
        return ["S", "L"]
    if key == "Label":
        return ["X", "Y"]
    return []


def _chair_after(values: dict[str, str], key: str, value: str) -> None:
    if key == "Material":
        allowed = _chair_choices(values, "Finish")
        if "Finish" in values and values["Finish"] not in allowed:
            values["Finish"] = allowed[0]
        if value == "Metal":
            values.setdefault("Arm", "Fixed")  # dependent property appears
        else:
            values.pop("Arm", None)            # ...and disappears again


def _final(values: dict[str, str]) -> str:
    return "CHAIR " + "".join(v[0] for k, v in values.items() if k != "Label")


CHAIR = Spec("CHAIR", {"Material": "Wood", "Finish": "Oak", "Size": "S"}, _chair_choices, _chair_after, _final)


def _size_rewrites_material(values: dict[str, str], key: str, value: str) -> None:
    _chair_after(values, key, value)
    if key == "Size" and value == "L":          # relation changes a value chosen EARLIER
        values["Material"] = "Metal"
        _chair_after(values, "Material", "Metal")


REWRITER = Spec("REWRITE", {"Material": "Wood", "Finish": "Oak", "Size": "S"}, _chair_choices,
                _size_rewrites_material, lambda v: "REWRITE " + "".join(x[0] for x in v.values()))

DUPE = Spec("DUPE", {"Material": "Wood", "Label": "X"}, _chair_choices, _chair_after,
            lambda v: "DUPE " + v["Material"][0])  # Label never reaches the SKU

LARGE = Spec("LARGE", {"Material": "Wood", "Finish": "Oak", "Size": "S", "Label": "X"}, _chair_choices,
             _chair_after, lambda v: "LARGE " + "".join(x[0] for x in v.values()))


def run(spec: Spec, reuse: bool, **kwargs) -> tuple[Result, Planning]:
    planning = Planning()
    for attr in ("fail_insert_for", "fail_properties_on_call"):
        if attr in kwargs:
            setattr(planning, attr, kwargs.pop(attr))
    return Enumerator(planning, spec, reuse=reuse, **kwargs).run(), planning


def brute_force_skus(spec: Spec) -> set[str]:
    """Independent oracle: depth-first on fresh articles, no probe sharing at all."""
    out: set[str] = set()

    def walk(prefix: list[tuple[str, str]]) -> None:
        values = dict(spec.initial)
        for key, value in prefix:
            if key not in values or value not in spec.choices(values, key):
                return
            values[key] = value
            spec.after_set(values, key, value)
        assigned = {k for k, _ in prefix}
        for key in values:
            if key not in assigned and spec.choices(values, key):
                for value in spec.choices(values, key):
                    walk(prefix + [(key, value)])
                return
        if all(values.get(k) == v for k, v in prefix):
            out.add(spec.final(values))

    walk([])
    return out


def _same_outcome(a: Result, b: Result) -> None:
    assert a.rows == b.rows                      # identical rows, identical order
    assert a.warnings == b.warnings
    assert (a.skipped, a.duplicates, a.visited, a.truncated, a.cancelled) == \
           (b.skipped, b.duplicates, b.visited, b.truncated, b.cancelled)


# ----------------------------------------------------------------------------- tests
@pytest.mark.parametrize("spec", [CHAIR, REWRITER, DUPE, LARGE], ids=lambda s: s.number)
def test_reuse_matches_baseline_and_independent_oracle(spec):
    base, _ = run(spec, reuse=False)
    fast, planning = run(spec, reuse=True)
    _same_outcome(base, fast)
    assert set(fast.finals) == brute_force_skus(spec)
    assert len(set(fast.finals)) == len(fast.finals)              # final SKU deduplication
    assert fast.probe_insertions < base.probe_insertions
    assert fast.property_applications < base.property_applications
    assert planning.max_open_instances == 1                       # SDK allows one open instance


def test_relation_that_rewrites_an_earlier_choice_is_skipped_not_forced():
    base, _ = run(REWRITER, reuse=False)
    fast, _ = run(REWRITER, reuse=True)
    _same_outcome(base, fast)
    assert any("changed by relations" in w for w in fast.warnings)
    assert fast.skipped == base.skipped > 0
    for _, assignments in fast.rows:                              # every kept row still holds
        assert ("Size", "L") not in assignments or ("Material", "Metal") in assignments


def test_dependent_properties_appear_and_disappear():
    fast, _ = run(CHAIR, reuse=True)
    with_arm = [a for _, a in fast.rows if any(k == "Arm" for k, _ in a)]
    without_arm = [a for _, a in fast.rows if not any(k == "Arm" for k, _ in a)]
    assert with_arm and without_arm
    assert all(("Material", "Metal") in a for a in with_arm)      # Arm only after Metal
    assert all(("Finish", "Silver") in a for a in with_arm)       # Finish value set shrank
    assert all(("Material", "Wood") in a for a in without_arm)


def test_duplicate_skus_are_counted_and_never_kept():
    base, _ = run(DUPE, reuse=False)
    fast, planning = run(DUPE, reuse=True)
    _same_outcome(base, fast)
    assert fast.duplicates == base.duplicates > 0
    assert len(fast.finals) == len(set(fast.finals))
    assert set(planning.entities.values()) == {"DUPE"} and len(planning.entities) == len(fast.rows)


@pytest.mark.parametrize("limit", [1, 2, 3, 5])
def test_truncation_matches_baseline_and_leaves_no_probes(limit):
    base, bp = run(LARGE, reuse=False, max_configs=limit)
    fast, fp = run(LARGE, reuse=True, max_configs=limit)
    _same_outcome(base, fast)
    assert fast.truncated and len(fast.rows) == limit
    assert len(fp.entities) == limit and fp.open_instances == 0   # only kept leaves remain


@pytest.mark.parametrize("cancel_after_checks", [1, 2, 3, 7, 12])
def test_cancellation_matches_baseline_and_leaves_no_probes(cancel_after_checks):
    def make() -> Callable[[], bool]:
        calls = itertools.count(1)
        return lambda: next(calls) >= cancel_after_checks

    base, _ = run(LARGE, reuse=False, cancel=make())
    fast, fp = run(LARGE, reuse=True, cancel=make())
    _same_outcome(base, fast)
    assert fast.cancelled
    assert len(fp.entities) == len(fast.rows) and fp.open_instances == 0


@pytest.mark.parametrize("reuse", [False, True])
@pytest.mark.parametrize("fail_on", range(1, 15))
def test_probe_cleanup_when_the_sdk_throws_mid_run(reuse, fail_on):
    planning = Planning()
    planning.fail_properties_on_call = fail_on
    enumerator = Enumerator(planning, LARGE, reuse=reuse)
    with pytest.raises(RuntimeError, match="SDK property list unavailable"):
        enumerator.run()
    # Only already-accepted leaves may remain; the in-flight probe was removed.
    assert len(planning.entities) == len(enumerator.r.rows)
    assert planning.open_instances == 0


def test_uninsertable_article_is_skipped_in_both_modes():
    base, bp = run(CHAIR, reuse=False, fail_insert_for={"CHAIR"})
    fast, fp = run(CHAIR, reuse=True, fail_insert_for={"CHAIR"})
    _same_outcome(base, fast)
    assert fast.skipped == 1 and not fast.rows and not fp.entities


def test_fixed_and_excluded_rules_are_honoured_identically():
    kwargs = dict(fixed=(("Size", "L"),), excluded=frozenset({"Label"}))
    base, _ = run(LARGE, reuse=False, **kwargs)
    fast, _ = run(LARGE, reuse=True, **kwargs)
    _same_outcome(base, fast)
    assert fast.rows and all(("Size", "L") in a for _, a in fast.rows)


def test_deduplication_can_be_switched_off_identically():
    base, _ = run(DUPE, reuse=False, deduplicate=False)
    fast, _ = run(DUPE, reuse=True, deduplicate=False)
    _same_outcome(base, fast)
    assert fast.duplicates == 0 and len(fast.rows) > len(set(fast.finals))


def test_value_set_reads_drop():
    base, bp = run(LARGE, reuse=False)
    fast, fp = run(LARGE, reuse=True)
    assert fp.value_set_reads < bp.value_set_reads


@pytest.mark.parametrize("spec", [CHAIR, REWRITER, DUPE, LARGE], ids=lambda s: s.number)
def test_every_switch_combination_gives_the_same_output(spec):
    """MK_OBX_REUSE_PROBE x MK_OBX_LEGACY_READS: four builds of the same walk, one result."""
    runs = {(reuse, legacy): run(spec, reuse=reuse, legacy_reads=legacy)
            for reuse in (False, True) for legacy in (False, True)}
    reference, _ = runs[(False, True)]            # the original baseline
    for result, planning in runs.values():
        _same_outcome(reference, result)
        assert planning.max_open_instances == 1


def test_probe_reuse_off_still_keeps_the_value_set_saving():
    """The documented limitation: MK_OBX_REUSE_PROBE=0 alone is NOT the original baseline."""
    original, op = run(LARGE, reuse=False, legacy_reads=True)
    shipped_off, sp = run(LARGE, reuse=False, legacy_reads=False)
    assert shipped_off.probe_insertions == original.probe_insertions          # same inserts and replay
    assert shipped_off.property_applications == original.property_applications
    assert sp.value_set_reads < op.value_set_reads                            # but fewer ValueSet reads
    _, with_legacy = run(LARGE, reuse=True, legacy_reads=True)
    _, without_legacy = run(LARGE, reuse=True, legacy_reads=False)
    assert with_legacy.value_set_reads > without_legacy.value_set_reads


@pytest.mark.parametrize("reuse", [False, True])
@pytest.mark.parametrize("spec", [CHAIR, REWRITER, DUPE, LARGE], ids=lambda s: s.number)
def test_instrumentation_counters_are_consistent(spec, reuse):
    result, _ = run(spec, reuse=reuse)
    # no fixed rules here, so leaf verification adds no applications and the split is exact
    assert result.replay_applications + result.incremental_applications == result.property_applications
    assert sum(result.visits_by_depth) == result.visited
    assert sum(result.inserts_by_depth) == result.probe_insertions
    assert result.leaves + result.internal_nodes <= result.visited
    assert (result.incremental_applications > 0) == reuse


def test_replay_work_grows_with_depth_and_reuse_removes_it():
    """Replay cost is depth x nodes in the baseline; handing the probe on removes the first-child share."""
    base, _ = run(LARGE, reuse=False)
    fast, _ = run(LARGE, reuse=True)
    assert base.replay_applications == sum(depth * count for depth, count in enumerate(base.inserts_by_depth))
    assert fast.replay_applications < base.replay_applications
    assert base.visits_by_depth == fast.visits_by_depth                        # identical tree


# --------------------------------------------------------------------------- report
def benchmark_table() -> str:
    """Counts only (no timings): the three switch settings a real-host benchmark can run on one build."""
    variants = (("original (REUSE=0 LEGACY=1)", False, True),
                ("shipped REUSE=0 (LEGACY=0)", False, False),
                ("optimised (REUSE=1 LEGACY=0)", True, False))
    lines = [f"{'product':<8} {'variant':<29} {'skus':>4} {'same':>5} {'inserts':>8} {'setvalues':>10} "
             f"{'replay':>7} {'valueset-reads':>15}"]
    for spec in (CHAIR, REWRITER, DUPE, LARGE):
        reference, _ = run(spec, reuse=False, legacy_reads=True)
        for label, reuse, legacy in variants:
            result, planning = run(spec, reuse=reuse, legacy_reads=legacy)
            lines.append(f"{spec.number:<8} {label:<29} {len(result.rows):>4} {str(result.rows == reference.rows):>5} "
                         f"{result.probe_insertions:>8} {result.property_applications:>10} "
                         f"{result.replay_applications:>7} {planning.value_set_reads:>15}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(benchmark_table())
