"""Evaluator for parsed OCD relations: three-valued logic, verdicts, actions.

The OCD language is three-valued (appendix A): a condition is TRUE, FALSE or
UNDEFINED (it reads a property the article lacks or that has no value). How an
UNDEFINED result counts depends on the relation type, so this module returns
the raw :class:`Tri` and exposes the per-type verdict helpers separately:

* precondition   - violated only if definitely FALSE
* selection cond - met only if definitely TRUE
* action ``IF``  - fires only if definitely TRUE
* constraint     - restriction violated unless TRUE (undefined violates)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import IntEnum

from services.ocd_engine import relation_parser as rp


class Tri(IntEnum):
    FALSE = 0
    UNDEFINED = 1
    TRUE = 2

    @staticmethod
    def of(flag: bool) -> "Tri":
        return Tri.TRUE if flag else Tri.FALSE


def tri_and(values) -> Tri:
    result = Tri.TRUE
    for value in values:
        if value is Tri.FALSE:
            return Tri.FALSE
        if value is Tri.UNDEFINED:
            result = Tri.UNDEFINED
    return result


def tri_or(values) -> Tri:
    result = Tri.FALSE
    for value in values:
        if value is Tri.TRUE:
            return Tri.TRUE
        if value is Tri.UNDEFINED:
            result = Tri.UNDEFINED
    return result


def tri_not(value: Tri) -> Tri:
    # NOT(UNDEFINED) = UNDEFINED. The spec states the AND/OR rules only; this
    # is the standard extension and is documented as an assumption.
    if value is Tri.UNDEFINED:
        return Tri.UNDEFINED
    return Tri.FALSE if value is Tri.TRUE else Tri.TRUE


# ---- verdicts per relation type (spec appendix A)

def precondition_violated(result: Tri) -> bool:
    return result is Tri.FALSE


def selection_condition_met(result: Tri) -> bool:
    return result is Tri.TRUE


def action_fires(result: Tri) -> bool:
    return result is Tri.TRUE


class EvalError(ValueError):
    """A relation that parsed but cannot be evaluated (type error, bad call)."""


@dataclass
class EvalContext:
    """Configuration state a relation is evaluated against."""

    values: dict[str, object]
    ban: str = ""
    tables: dict[str, object] = field(default_factory=dict)
    aliases: dict[str, str] = field(default_factory=dict)   # constraint variable -> property
    computed: dict[str, object] = field(default_factory=dict)
    varconds: list[str] = field(default_factory=list)
    pricing_factors: dict[str, float] = field(default_factory=dict)
    # Optional alternative values for property references on the *right side of
    # an assignment*. Repository (MDB) data keeps a display value and a code per
    # property value: conditions test the value, assignments concatenate codes.
    # OCD CSV data has one value, so this stays ``None`` there.
    rhs_values: dict[str, object] | None = None

    def resolve(self, name: str) -> str:
        """Property key for ``name``: constraint variables and ``VAR.PROP`` qualifiers resolved."""
        name = name.upper()
        if name in self.values or name in self.computed:
            return name
        if name in self.aliases:
            return self.aliases[name]
        if "." in name:
            tail = name.rsplit(".", 1)[1]
            return self.aliases.get(tail, tail)
        return name

    def lookup(self, name: str):
        key = self.resolve(name)
        if key in self.computed:
            return self.computed[key]
        return self.values.get(key)

    def assign(self, name: str, value) -> None:
        self.computed[self.resolve(name)] = value


# ------------------------------------------------------------------ expressions


def _number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _format_number(value: float) -> str:
    text = repr(float(value))
    return text[:-2] if text.endswith(".0") else text


def eval_expr(node, ctx: EvalContext):
    """Value of an expression: ``str``, ``float``, ``bool`` or ``None`` (undefined)."""
    if isinstance(node, rp.Const):
        return node.value
    if isinstance(node, rp.PropRef):
        return ctx.lookup(node.name)
    if isinstance(node, rp.SysVar):
        if node.name == "$BAN":
            return ctx.ban
        return ctx.lookup(node.name)
    if isinstance(node, rp.Neg):
        operand = eval_expr(node.operand, ctx)
        number = _number(operand)
        return None if number is None else -number
    if isinstance(node, rp.BinOp):
        left, right = eval_expr(node.left, ctx), eval_expr(node.right, ctx)
        if left is None or right is None:
            return None
        if node.op == "+" and (isinstance(left, str) or isinstance(right, str)):
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            raise EvalError("cannot mix string and number with '+'")
        a, b = _number(left), _number(right)
        if a is None or b is None:
            raise EvalError(f"non-numeric operand for '{node.op}'")
        if node.op == "+":
            return a + b
        if node.op == "-":
            return a - b
        if node.op == "*":
            return a * b
        if b == 0:
            return None
        return a / b
    if isinstance(node, rp.Func):
        return _eval_func(node, ctx)
    if isinstance(node, (rp.Compare, rp.InSet, rp.Specified, rp.And, rp.Or, rp.Not, rp.TableCall)):
        result = eval_cond(node, ctx)
        return None if result is Tri.UNDEFINED else result is Tri.TRUE
    raise EvalError(f"cannot evaluate {type(node).__name__}")


def _eval_func(node: rp.Func, ctx: EvalContext):
    args = [eval_expr(arg, ctx) for arg in node.args]
    name = node.name
    if name == "SUBSTR":
        if len(args) not in (2, 3):
            raise EvalError("SUBSTR expects 2 or 3 arguments")
        if args[0] is None:
            return None
        text = args[0]
        if not isinstance(text, str):
            return ""
        start = _number(args[1])
        length = _number(args[2]) if len(args) == 3 else None
        if start is None or start != int(start) or start < 0 or start > len(text):
            return ""
        if length is not None and (length != int(length) or length < 0):
            return ""
        start = int(start)
        return text[start:] if length is None else text[start:start + int(length)]
    if any(arg is None for arg in args):
        return None
    if name == "STRING":
        number = _number(args[0])
        if number is None:
            raise EvalError("STRING expects a number")
        return _format_number(number)
    if name == "SIZE":
        return float(len(str(args[0])))
    if name in {"TOUPPER", "TOLOWER", "TRIM", "RTRIM", "LTRIM"}:
        text = str(args[0])
        return {"TOUPPER": text.upper, "TOLOWER": text.lower, "TRIM": lambda: text.strip(" "),
                "RTRIM": lambda: text.rstrip(" "), "LTRIM": lambda: text.lstrip(" ")}[name]()
    numbers = [_number(arg) for arg in args]
    if any(n is None for n in numbers):
        raise EvalError(f"{name} expects numbers")
    try:
        if name == "POW":
            return math.pow(numbers[0], numbers[1])
        unary = {"SQRT": math.sqrt, "FABS": math.fabs, "CEIL": math.ceil, "FLOOR": math.floor,
                 "SIGN": lambda x: -1.0 if x < 0 else 1.0, "TRUNC": math.trunc,
                 "FRAC": lambda x: x - math.trunc(x)}
        return float(unary[name](numbers[0]))
    except (ValueError, KeyError, IndexError, OverflowError) as error:
        raise EvalError(f"{name} failed: {error}") from error


# ------------------------------------------------------------------ conditions


def _equal(a, b, mode: str = "auto") -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if mode == "str" or (mode == "auto" and isinstance(a, str) and isinstance(b, str)
                         and (_number(a) is None or _number(b) is None)):
        return str(a).upper() == str(b).upper()
    na, nb = _number(a), _number(b)
    if na is None or nb is None:
        if isinstance(a, str) and isinstance(b, str):
            return a.upper() == b.upper()
        raise EvalError(f"cannot compare {a!r} with {b!r}")
    return na == nb


def _operand_mode(left_node, right_node) -> str:
    """Comparison type from the *syntax* (spec A: operands must be the same type).

    A string literal makes it a string comparison (so ``'900' > '1000'``), a
    numeric literal or arithmetic makes it numeric; two property references are
    compared numerically when both values are numbers, else as strings.
    """
    for node in (left_node, right_node):
        if isinstance(node, rp.Const) and isinstance(node.value, str):
            return "str"
    for node in (left_node, right_node):
        if isinstance(node, (rp.BinOp, rp.Neg, rp.Func)) or (
                isinstance(node, rp.Const) and isinstance(node.value, float)):
            return "num"
    return "auto"


def _compare(op: str, a, b, mode: str = "auto") -> bool:
    if op == "=":
        return _equal(a, b, mode)
    if op == "<>":
        return not _equal(a, b, mode)
    numeric = mode == "num" or (mode == "auto" and _number(a) is not None and _number(b) is not None)
    if not numeric:
        a, b = str(a), str(b)
        ordering = (a > b) - (a < b)          # lexicographic, code-point order (Latin-1)
    else:
        na, nb = _number(a), _number(b)
        if na is None or nb is None:
            raise EvalError(f"cannot order {a!r} and {b!r}")
        ordering = (na > nb) - (na < nb)
    return {"<": ordering < 0, "<=": ordering <= 0, ">": ordering > 0, ">=": ordering >= 0}[op]


def eval_cond(node, ctx: EvalContext) -> Tri:
    if isinstance(node, rp.Const):
        return Tri.of(bool(node.value))
    if isinstance(node, rp.And):
        return tri_and(eval_cond(item, ctx) for item in node.items)
    if isinstance(node, rp.Or):
        return tri_or(eval_cond(item, ctx) for item in node.items)
    if isinstance(node, rp.Not):
        return tri_not(eval_cond(node.item, ctx))
    if isinstance(node, rp.Specified):
        value = ctx.lookup(node.name)
        return Tri.of(value is not None and value != "")
    if isinstance(node, rp.Compare):
        left, right = eval_expr(node.left, ctx), eval_expr(node.right, ctx)
        if left is None or right is None:
            return Tri.UNDEFINED
        return Tri.of(_compare(node.op, left, right, _operand_mode(node.left, node.right)))
    if isinstance(node, rp.InSet):
        left = eval_expr(node.expr, ctx)
        if left is None:
            return Tri.UNDEFINED
        found = False
        for value_node in node.values:
            value = eval_expr(value_node, ctx)
            if value is not None and _equal(left, value, _operand_mode(node.expr, value_node)):
                found = True
                break
        return Tri.of(found != node.negated)
    if isinstance(node, rp.TableCall):
        return _eval_table(node, ctx, exactly_one=True)
    if isinstance(node, (rp.PropRef, rp.SysVar, rp.Func, rp.BinOp)):
        value = eval_expr(node, ctx)
        if value is None:
            return Tri.UNDEFINED
        if isinstance(value, bool):
            return Tri.of(value)
        raise EvalError("expression is not a condition")
    raise EvalError(f"cannot evaluate {type(node).__name__} as a condition")


def _eval_table(node: rp.TableCall, ctx: EvalContext, *, exactly_one: bool) -> Tri:
    table = ctx.tables.get(node.table.upper())
    if table is None:
        raise EvalError(f"value combination table {node.table} is not loaded")
    actual: dict[str, object] = {}
    for column, expr in node.params:
        value = eval_expr(expr, ctx)
        if value is None:
            return Tri.UNDEFINED                  # B.2.1: undefined parameter => undefined
        actual[column.upper()] = value
    matches = 0
    for line in table.lines:
        normalised = {str(k).upper(): v for k, v in line.items()}
        ok = True
        for column, value in actual.items():
            expected = normalised.get(column)
            if expected is None:
                continue
            allowed = expected if isinstance(expected, (list, tuple, set, frozenset)) else [expected]
            if not any(_equal(value, item) for item in allowed):
                ok = False
                break
        matches += ok
    return Tri.of(matches == 1 if exactly_one else matches >= 1)


# ------------------------------------------------------------------ actions


@dataclass
class ActionReport:
    assigned: list[tuple[str, object]] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)      # (clause text, reason)


def run_actions(statements, ctx: EvalContext) -> ActionReport:
    """Execute action statements in order; later assignments overwrite earlier ones.

    An assignment takes effect only if its ``IF`` condition is definitely TRUE
    and its right side is defined (appendix A). ``$VARCOND`` is multivalued:
    every assignment appends (price table keys are upper case, spec 3.2).
    """
    report = ActionReport()
    for statement in statements:
        if isinstance(statement, rp.Unsupported):
            report.skipped.append((statement.text, statement.reason))
            continue
        try:
            if isinstance(statement, rp.Assign):
                if statement.cond is not None and not action_fires(eval_cond(statement.cond, ctx)):
                    continue
                rhs_ctx = ctx
                if ctx.rhs_values is not None:
                    rhs_ctx = EvalContext(values={**ctx.values, **ctx.rhs_values}, ban=ctx.ban,
                                          tables=ctx.tables, aliases=ctx.aliases, computed=ctx.computed)
                value = eval_expr(statement.expr, rhs_ctx)
                if value is None:
                    continue
                if statement.target == "$VARCOND":
                    ctx.varconds.append(str(value).upper())
                else:
                    ctx.assign(statement.target, value)
                report.assigned.append((statement.target, value))
            elif isinstance(statement, rp.PricingFactor):
                if statement.cond is not None and not action_fires(eval_cond(statement.cond, ctx)):
                    continue
                variant, factor = eval_expr(statement.variant, ctx), eval_expr(statement.factor, ctx)
                if variant is not None and _number(factor) is not None:
                    ctx.pricing_factors[str(variant).upper()] = _number(factor)    # last call wins
        except EvalError as error:
            report.skipped.append((repr(statement), str(error)))
    return report


# ------------------------------------------------------------------ constraints


@dataclass
class ConstraintResult:
    evaluated: bool
    satisfied: bool
    reason: str = ""


def run_constraint(constraint: rp.Constraint, ctx: EvalContext) -> ConstraintResult:
    """Check one constraint (appendix B.1) and apply its inferred assignments.

    The ``Condition`` section gates evaluation (undefined => not evaluated).
    Each restriction must be TRUE; FALSE or UNDEFINED violates the constraint.
    Value assignment via ``prop = expr`` for a property listed under
    ``Inferences:`` is supported; restriction of value *sets* is not.
    """
    ctx.aliases.update(dict(constraint.variables))
    if constraint.condition is not None and eval_cond(constraint.condition, ctx) is not Tri.TRUE:
        return ConstraintResult(evaluated=False, satisfied=True)
    inferred = set(constraint.inferences) | {
        alias for alias, _ in constraint.variables if alias in constraint.inferences
    }
    for restriction in constraint.restrictions:
        if isinstance(restriction, rp.Unsupported):
            return ConstraintResult(True, True, f"unsupported clause skipped: {restriction.text}")
        if restriction.cond is not None and eval_cond(restriction.cond, ctx) is not Tri.TRUE:
            continue
        body = restriction.body
        if isinstance(body, rp.Compare) and body.op == "=" and isinstance(body.left, rp.PropRef) \
                and body.left.name in inferred and ctx.lookup(body.left.name) is None:
            value = eval_expr(body.right, ctx)
            if value is not None:
                ctx.assign(body.left.name, value)
                continue
        if isinstance(body, rp.InSet) and isinstance(body.expr, rp.PropRef) \
                and body.expr.name in inferred and ctx.lookup(body.expr.name) is None:
            continue     # would restrict the value set; not modelled, never fails
        if isinstance(body, rp.TableCall):
            result = _eval_table(body, ctx, exactly_one=False)
        else:
            result = eval_cond(body, ctx)
        if result is not Tri.TRUE:
            return ConstraintResult(True, False, f"restriction {result.name}: {_describe(body)}")
    return ConstraintResult(True, True)


def _describe(node) -> str:
    names = sorted(rp.referenced_properties(node))
    return f"{type(node).__name__} on {', '.join(names) or 'constants'}"
