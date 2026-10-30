"""Relation parser: grammar coverage, nesting, multi-parent, comments, error handling."""
import pytest

from services.ocd_engine import relation_parser as rp


def test_nested_and_or_parentheses_precedence():
    node = rp.parse_condition("A = '1' OR B = '2' AND C = '3'")
    assert isinstance(node, rp.Or) and isinstance(node.items[1], rp.And)       # AND binds tighter
    grouped = rp.parse_condition("(A = '1' OR B = '2') AND C = '3'")
    assert isinstance(grouped, rp.And) and isinstance(grouped.items[0], rp.Or)


def test_in_and_not_in_and_specified():
    node = rp.parse_condition("(SPECIFIED Top_Finish) AND (Top_Finish NOT IN ('A', 'B'))")
    assert isinstance(node.items[0], rp.Specified) and node.items[0].name == "TOP_FINISH"
    assert node.items[1].negated is True and len(node.items[1].values) == 2


def test_unparenthesised_specified_and_comparison():
    # real Dalby rel 19542: "SPECIFIED Access_Cutout AND Access_Cutout NOT IN (...)"
    node = rp.parse_condition("SPECIFIED Access_Cutout AND Access_Cutout NOT IN ('OFT','NC')")
    assert isinstance(node, rp.And) and isinstance(node.items[0], rp.Specified)


def test_multi_parent_relation_references_all_parents():
    node = rp.parse_condition("(A IN ('1')) AND (B = '2') OR (SPECIFIED C)")
    assert rp.referenced_properties(node) == {"A", "B", "C"}


def test_dollar_space_ban_and_case_insensitive_identifiers():
    node = rp.parse_condition("$ BAN IN ('X1', 'X1', 'X2') and top_finish = 'q75'")
    assert node.items[0].expr == rp.SysVar("$BAN")
    assert node.items[1].left == rp.PropRef("TOP_FINISH")


def test_word_comparison_operators_and_alternative_ge():
    assert rp.parse_condition("A EQ 'x'").op == "="
    assert rp.parse_condition("A NE 'x'").op == "<>"
    assert rp.parse_condition("A => 3").op == ">="


def test_string_escape_and_arithmetic_condition():
    assert rp.parse_condition("A = 'it''s'").right == rp.Const("it's")
    node = rp.parse_condition("(W + 1) * 2 > 10")
    assert isinstance(node, rp.Compare) and isinstance(node.left, rp.BinOp)


def test_assemble_drops_comment_and_empty_blocks_and_sorts():
    blocks = [(3, ""), (1, "***** header"), (4, "A = 'x'"), (2, "****** $ BAN IN ('1')")]
    assert rp.assemble_relation_text(blocks) == "A = 'x'"
    assert rp.assemble_relation_text([(2, "AND B = '1'"), (1, "A = '1'")]) == "A = '1'\nAND B = '1'"


def test_actions_trailing_commas_and_varcond_target():
    stmts = rp.parse_actions("$VARCOND = '6821=' + Access_Cutout, $VARCOND = '7030=' + Cable_leg,")
    assert [s.target for s in stmts] == ["$VARCOND", "$VARCOND"]


def test_action_if_clause_and_function_calls():
    (stmt,) = rp.parse_actions("Code = SUBSTR($BAN,0,3) + STRING(W) IF Aeron_Type IN ('A','B')")
    assert isinstance(stmt.expr, rp.BinOp) and isinstance(stmt.cond, rp.InSet)
    assert stmt.expr.left.name == "SUBSTR"


def test_unsupported_clause_is_reported_not_dropped():
    stmts = rp.parse_actions("A = 'x', USER_MESSAGE('hi') IF B = 'y', C = 'z'")
    assert isinstance(stmts[1], rp.Unsupported) and "USER_MESSAGE" in stmts[1].text
    assert isinstance(stmts[0], rp.Assign) and isinstance(stmts[2], rp.Assign)


def test_pricing_factor_statement():
    (stmt,) = rp.parse_actions("$SET_PRICING_FACTOR('ABC', WIDTH / 1000) IF WIDTH > 1000")
    assert isinstance(stmt, rp.PricingFactor) and stmt.cond is not None


def test_constraint_sections():
    c = rp.parse_constraint(
        "Objects: x IS_A cupboard where design = design_group; corpus = colour_corpus.\n"
        "Condition: x.design_group = 'A'.\n"
        "Restrictions: TABLE colours (design_group = design, colour_corpus = corpus).\n"
        "Inferences: corpus.")
    assert c.classes == (("X", "CUPBOARD"),)
    assert ("DESIGN", "DESIGN_GROUP") in c.variables and c.inferences == ("CORPUS",)
    assert isinstance(c.restrictions[0].body, rp.TableCall)


def test_restrictions_label_is_stripped_for_conditions():
    assert isinstance(rp.parse_condition("Restrictions:\r\n  $BAN IN ('X')."), rp.InSet)


@pytest.mark.parametrize("text", ["A = ", "A IN ('x'", "AND B", "A = 'x' B", "A $$ 3"])
def test_syntax_errors_are_reported_via_compile_not_raised(text):
    compiled = rp.compile_relation(1, text)
    assert compiled.error and compiled.node is None


def test_compile_cache_returns_same_object():
    assert rp.compile_relation(1, "A = 'x'") is rp.compile_relation(1, "A = 'x'")
