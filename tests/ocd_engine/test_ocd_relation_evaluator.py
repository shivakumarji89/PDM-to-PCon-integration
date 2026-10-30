"""Relation evaluator: three-valued logic and the per-type verdicts."""
import itertools

import pytest

from services.ocd_engine import relation_parser as rp
from services.ocd_engine.relation_evaluator import (
    EvalContext, EvalError, Tri, eval_cond, eval_expr, precondition_violated,
    run_actions, run_constraint, selection_condition_met, tri_and, tri_not, tri_or,
)

T, F, U = Tri.TRUE, Tri.FALSE, Tri.UNDEFINED


def cond(text, **values):
    ctx = EvalContext({k.upper(): v for k, v in values.items()}, ban="BAN1")
    return eval_cond(rp.parse_condition(text), ctx)


@pytest.mark.parametrize("a,b", list(itertools.product([T, F, U], repeat=2)))
def test_and_or_truth_tables_follow_spec(a, b):
    # spec A: AND is undefined only if both undefined or one undefined and the other true
    expected_and = F if F in (a, b) else (U if U in (a, b) else T)
    expected_or = T if T in (a, b) else (U if U in (a, b) else F)
    assert tri_and([a, b]) is expected_and
    assert tri_or([a, b]) is expected_or


def test_not_of_undefined_is_undefined():
    assert tri_not(U) is U and tri_not(T) is F and tri_not(F) is T


def test_undefined_property_makes_comparison_undefined_not_false():
    assert cond("Color = 'red'") is U
    assert cond("Color IN ('red')") is U
    assert cond("Color NOT IN ('red')") is U


def test_specified_never_undefined_and_guards_comparisons():
    assert cond("SPECIFIED Color") is F
    assert cond("SPECIFIED Color", color="red") is T
    assert cond("(SPECIFIED Color) AND (Color IN ('red'))") is F           # FALSE beats UNDEFINED in AND
    assert cond("(SPECIFIED Color) AND (Color IN ('red'))", color="red") is T


def test_or_true_branch_beats_undefined():
    assert cond("Color = 'red' OR $BAN IN ('BAN1')") is T
    assert cond("Color = 'red' OR $BAN IN ('NOPE')") is U


def test_string_equality_is_case_insensitive_ordering_is_lexicographic():
    assert cond("Color = 'RED'", color="red") is T
    assert cond("Code < 'b'", code="a") is T
    assert cond("Code < 'B'", code="a") is F                               # 'a' (97) > 'B' (66)


def test_numeric_comparison_vs_string_digits():
    assert cond("W > 1000", w="900") is F                                  # numeric, not lexicographic
    assert cond("W > '1000'", w="900") is T                                # both strings: '900' > '1000'


def test_precondition_semantics_undefined_is_not_violated():
    assert precondition_violated(F) and not precondition_violated(U) and not precondition_violated(T)


def test_selection_condition_semantics_only_true_is_met():
    assert selection_condition_met(T) and not selection_condition_met(U) and not selection_condition_met(F)


def test_action_if_requires_definite_true():
    ctx = EvalContext({}, ban="B")
    run_actions(rp.parse_actions("X = 'a' IF Missing = 'x'"), ctx)
    assert "X" not in ctx.computed                                         # UNDEFINED condition: no effect
    run_actions(rp.parse_actions("X = 'a' IF $BAN = 'B'"), ctx)
    assert ctx.computed["X"] == "a"


def test_assignment_with_undefined_right_side_has_no_effect():
    ctx = EvalContext({"A": "1"}, ban="B")
    report = run_actions(rp.parse_actions("X = A + Missing, Y = A + '!'"), ctx)
    assert "X" not in ctx.computed and ctx.computed["Y"] == "1!"
    assert len(report.assigned) == 1


def test_actions_overwrite_in_order_and_self_reference():
    ctx = EvalContext({"A": "1"}, ban="BASE")
    run_actions(rp.parse_actions("C = SUBSTR($BAN,0,2), C = C + A, C = C + '-' + A"), ctx)
    assert ctx.computed["C"] == "BA1-1"


def test_substr_edge_cases_follow_spec():
    ctx = EvalContext({}, ban="ABCDEF")

    def ev(text):
        return eval_expr(rp.parse_actions(f"X = {text}")[0].expr, ctx)

    assert ev("SUBSTR($BAN, 2)") == "CDEF"
    assert ev("SUBSTR($BAN, 4, 10)") == "EF"                               # length past end: to end
    assert ev("SUBSTR($BAN, 9, 1)") == ""                                  # position past end: empty
    assert ev("SUBSTR($BAN, 1, 2)") == "BC"


def test_type_error_is_an_eval_error():
    with pytest.raises(EvalError):
        eval_expr(rp.parse_actions("X = 'a' + 1")[0].expr, EvalContext({}))


def test_varcond_collects_every_assignment_uppercased():
    ctx = EvalContext({"A": "x"}, ban="B")
    run_actions(rp.parse_actions("$VARCOND = '6821=' + A, $VARCOND = 'k2'"), ctx)
    assert ctx.varconds == ["6821=X", "K2"]


def test_pricing_factor_last_call_wins():
    ctx = EvalContext({"W": "2000"}, ban="B")
    run_actions(rp.parse_actions("$SET_PRICING_FACTOR('K', 1.5), $SET_PRICING_FACTOR('K', W / 1000)"), ctx)
    assert ctx.pricing_factors == {"K": 2.0}


# ---- constraints
def constraint(text, **values):
    ctx = EvalContext({k.upper(): v for k, v in values.items()}, ban="B")
    return run_constraint(rp.parse_constraint(text), ctx), ctx


def test_constraint_condition_gates_evaluation():
    result, _ = constraint("Objects: x IS_A c. Condition: A = 'on'. Restrictions: B = 'y'.", a="off", b="n")
    assert not result.evaluated and result.satisfied
    result, _ = constraint("Objects: x IS_A c. Condition: A = 'on'. Restrictions: B = 'y'.", a="on", b="n")
    assert result.evaluated and not result.satisfied


def test_constraint_undefined_restriction_violates():
    result, _ = constraint("Objects: x IS_A c. Restrictions: B = 'y'.")
    assert result.evaluated and not result.satisfied


def test_constraint_inference_assigns_value():
    result, ctx = constraint("Objects: x IS_A c. Restrictions: B = A. Inferences: B.", a="v")
    assert result.satisfied and ctx.computed["B"] == "v"


def test_constraint_restriction_with_if_condition():
    text = "Objects: x IS_A c. Restrictions: B = 'y' IF A = 'on'."
    assert constraint(text, a="off")[0].satisfied
    assert not constraint(text, a="on", b="n")[0].satisfied


def test_constraint_table_call_requires_matching_line():
    class Table:
        lines = [{"A": "1", "B": ["x", "y"]}, {"A": "2", "B": "z"}]

    text = "Objects: o IS_A c. Restrictions: TABLE t (A = pa, B = pb)."
    ctx = EvalContext({"PA": "1", "PB": "y"}, ban="B", tables={"T": Table()})
    assert run_constraint(rp.parse_constraint(text), ctx).satisfied
    ctx = EvalContext({"PA": "2", "PB": "y"}, ban="B", tables={"T": Table()})
    assert not run_constraint(rp.parse_constraint(text), ctx).satisfied
    ctx = EvalContext({"PA": "1"}, ban="B", tables={"T": Table()})            # undefined parameter
    assert not run_constraint(rp.parse_constraint(text), ctx).satisfied
