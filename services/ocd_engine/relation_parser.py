"""Parser for the OCD relation languages (OCD_1 / OCD_2, spec appendix A-B).

Produces an immutable AST. Nothing here evaluates; see ``relation_evaluator``.

Supported (evidenced in real OCD data or specified by OCD 4.3):

* conditions: ``AND``/``OR``/``NOT``, parentheses, ``= <> < <= > >= EQ NE LT LE
  GT GE =>``, ``IN (..)``/``NOT IN (..)``, ``SPECIFIED prop``, ``TRUE``/``FALSE``,
  ``TABLE name(col = x, ..)``;
* expressions: string/number constants, property references, ``$BAN``,
  ``+ - * /`` (``+`` also concatenates strings), parentheses, the functions
  ``SUBSTR STRING SIZE TOUPPER TOLOWER TRIM RTRIM LTRIM`` and the arithmetic
  functions of appendix F;
* actions: ``target = expr [IF cond]`` statements separated by commas
  (``target`` may be ``$VARCOND``), ``$SET_PRICING_FACTOR(..)``;
* constraints: ``Objects: / Condition: / Restrictions: / Inferences:``.

Anything else is returned as an :class:`Unsupported` node carrying the source
text, never silently dropped and never guessed at.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache


class RelationSyntaxError(ValueError):
    def __init__(self, message: str, position: int = -1) -> None:
        super().__init__(message if position < 0 else f"{message} (at offset {position})")
        self.position = position


# --------------------------------------------------------------------------- AST


@dataclass(frozen=True)
class Const:
    value: object                    # str | float | bool


@dataclass(frozen=True)
class PropRef:
    name: str                        # upper-case; may be qualified "VAR.PROP"


@dataclass(frozen=True)
class SysVar:
    name: str                        # "$BAN", "$VARCOND", "$SELF.X" (upper-case)


@dataclass(frozen=True)
class Func:
    name: str
    args: tuple


@dataclass(frozen=True)
class BinOp:
    op: str                          # + - * /
    left: object
    right: object


@dataclass(frozen=True)
class Neg:
    operand: object


@dataclass(frozen=True)
class Compare:
    op: str                          # = <> < <= > >=
    left: object
    right: object


@dataclass(frozen=True)
class InSet:
    expr: object
    values: tuple
    negated: bool = False


@dataclass(frozen=True)
class Specified:
    name: str


@dataclass(frozen=True)
class And:
    items: tuple


@dataclass(frozen=True)
class Or:
    items: tuple


@dataclass(frozen=True)
class Not:
    item: object


@dataclass(frozen=True)
class TableCall:
    table: str
    params: tuple                    # ((column, expr), ...)


@dataclass(frozen=True)
class Assign:
    target: str                      # upper-case property name or "$VARCOND"
    expr: object
    cond: object | None = None


@dataclass(frozen=True)
class PricingFactor:
    variant: object
    factor: object
    cond: object | None = None


@dataclass(frozen=True)
class Unsupported:
    text: str
    reason: str


@dataclass(frozen=True)
class ConstraintRelation:
    """One comma-separated relation of a ``Restrictions:`` section."""
    body: object                     # Compare | InSet | TableCall | other condition
    cond: object | None = None


@dataclass(frozen=True)
class Constraint:
    classes: tuple                   # ((var, property_class), ...)
    variables: tuple                 # ((var, property_name), ...)
    condition: object | None
    restrictions: tuple              # ConstraintRelation | Unsupported
    inferences: tuple                # upper-case property names / "VAR.PROP"


# --------------------------------------------------------------------------- lexer

_TOKEN_RE = re.compile(
    r"""
    (?P<ws>\s+)
  | (?P<string>'(?:[^']|'')*')
  | (?P<number>\d+(?:\.\d+)?)
  | (?P<sysvar>\$\s*[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)
  | (?P<ident>[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)
  | (?P<op><>|<=|>=|=>|=<|[=<>+\-*/(),.:])
    """,
    re.VERBOSE,
)

_KEYWORDS = {
    "AND", "OR", "NOT", "IN", "SPECIFIED", "IF", "TRUE", "FALSE", "TABLE",
    "EQ", "NE", "LT", "LE", "GT", "GE",
}
_WORD_OPS = {"EQ": "=", "NE": "<>", "LT": "<", "LE": "<=", "GT": ">", "GE": ">="}
_CMP_OPS = {"=", "<>", "<", "<=", ">", ">=", "=>", "=<"}


@dataclass(frozen=True)
class Token:
    kind: str       # string number sysvar ident keyword op end
    text: str
    pos: int


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    pos = 0
    while pos < len(text):
        match = _TOKEN_RE.match(text, pos)
        if not match:
            raise RelationSyntaxError(f"unexpected character {text[pos]!r}", pos)
        kind = match.lastgroup
        raw = match.group()
        if kind == "ws":
            pass
        elif kind == "string":
            tokens.append(Token("string", raw[1:-1].replace("''", "'"), pos))
        elif kind == "sysvar":
            tokens.append(Token("sysvar", re.sub(r"\s+", "", raw).upper(), pos))
        elif kind == "ident":
            upper = raw.upper()
            tokens.append(Token("keyword" if upper in _KEYWORDS else "ident", upper, pos))
        else:
            tokens.append(Token(kind, raw, pos))
        pos = match.end()
    tokens.append(Token("end", "", len(text)))
    return tokens


def assemble_relation_text(blocks: list[tuple[int, str]] | list[str]) -> str:
    """Join relation code blocks (spec 2.16) and drop comment/empty lines.

    ``blocks`` is ``[(block_nr, text), ...]`` (sorted here) or plain strings
    already in order. Real data uses lines starting with ``*`` as comments and
    empty blocks as spacing (both confirmed in Dalby ``ocd_relation.csv``).
    """
    if blocks and isinstance(blocks[0], tuple):
        blocks = [text for _nr, text in sorted(blocks, key=lambda item: item[0])]
    lines: list[str] = []
    for block in blocks:
        for line in str(block).splitlines() or [""]:
            stripped = line.strip()
            if stripped and not stripped.startswith("*"):
                lines.append(stripped)
    return "\n".join(lines)


# --------------------------------------------------------------------------- parser

_FUNCS = {
    "SUBSTR", "STRING", "SIZE", "TOUPPER", "TOLOWER", "TRIM", "RTRIM", "LTRIM",
    "POW", "SQRT", "FABS", "CEIL", "FLOOR", "SIGN", "TRUNC", "FRAC",
}


class _Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.tokens = tokenize(text)
        self.i = 0

    # -- token helpers
    @property
    def tok(self) -> Token:
        return self.tokens[self.i]

    def peek(self, offset: int = 1) -> Token:
        return self.tokens[min(self.i + offset, len(self.tokens) - 1)]

    def next(self) -> Token:
        token = self.tokens[self.i]
        self.i = min(self.i + 1, len(self.tokens) - 1)
        return token

    def at(self, kind: str, text: str | None = None) -> bool:
        return self.tok.kind == kind and (text is None or self.tok.text == text)

    def accept(self, kind: str, text: str | None = None) -> Token | None:
        if self.at(kind, text):
            return self.next()
        return None

    def expect(self, kind: str, text: str | None = None) -> Token:
        if not self.at(kind, text):
            want = text or kind
            raise RelationSyntaxError(f"expected {want!r}, found {self.tok.text or 'end'!r}", self.tok.pos)
        return self.next()

    def finish(self) -> None:
        if not self.at("end"):
            raise RelationSyntaxError(f"unexpected {self.tok.text!r}", self.tok.pos)

    # -- conditions
    def condition(self):
        items = [self.and_cond()]
        while self.accept("keyword", "OR"):
            items.append(self.and_cond())
        return items[0] if len(items) == 1 else Or(tuple(items))

    def and_cond(self):
        items = [self.not_cond()]
        while self.accept("keyword", "AND"):
            items.append(self.not_cond())
        return items[0] if len(items) == 1 else And(tuple(items))

    def not_cond(self):
        if self.accept("keyword", "NOT"):
            return Not(self.not_cond())
        return self.primary_cond()

    def primary_cond(self):
        if self.at("op", "("):
            # A '(' may open a grouped condition or an arithmetic operand of a
            # comparison, e.g. "(A + 1) > 2". Try the condition reading first.
            start = self.i
            try:
                self.next()
                inner = self.condition()
                self.expect("op", ")")
                if not (self.tok.kind == "op" and self.tok.text in _CMP_OPS | {"+", "-", "*", "/"}) \
                        and not (self.tok.kind == "keyword" and self.tok.text in {"IN", "NOT", *_WORD_OPS}):
                    return inner
            except RelationSyntaxError:
                pass
            self.i = start
        if self.accept("keyword", "SPECIFIED"):
            name = self.next()
            if name.kind not in {"ident", "sysvar"}:
                raise RelationSyntaxError("SPECIFIED needs a property name", name.pos)
            return Specified(name.text)
        if self.at("keyword", "TRUE") or self.at("keyword", "FALSE"):
            return Const(self.next().text == "TRUE")
        if self.at("keyword", "TABLE"):
            return self.table_call()
        return self.comparison()

    def comparison(self):
        left = self.expr()
        negated = False
        if self.at("keyword", "NOT") and self.peek().kind == "keyword" and self.peek().text == "IN":
            self.next()
            negated = True
        if self.accept("keyword", "IN"):
            self.expect("op", "(")
            values = [self.expr()]
            while self.accept("op", ","):
                values.append(self.expr())
            self.expect("op", ")")
            return InSet(left, tuple(values), negated)
        if self.tok.kind == "op" and self.tok.text in _CMP_OPS:
            op = self.next().text
            op = {"=>": ">=", "=<": "<="}.get(op, op)
        elif self.tok.kind == "keyword" and self.tok.text in _WORD_OPS:
            op = _WORD_OPS[self.next().text]
        else:
            raise RelationSyntaxError(f"expected a comparison, found {self.tok.text or 'end'!r}", self.tok.pos)
        return Compare(op, left, self.expr())

    def table_call(self):
        self.expect("keyword", "TABLE")
        name = self.expect("ident").text
        self.expect("op", "(")
        params = []
        while not self.at("op", ")"):
            column = self.expect("ident").text
            self.expect("op", "=")
            params.append((column, self.expr()))
            if not self.accept("op", ","):
                break
        self.expect("op", ")")
        return TableCall(name, tuple(params))

    # -- expressions
    def expr(self):
        node = self.term()
        while self.tok.kind == "op" and self.tok.text in {"+", "-"}:
            op = self.next().text
            node = BinOp(op, node, self.term())
        return node

    def term(self):
        node = self.factor()
        while self.tok.kind == "op" and self.tok.text in {"*", "/"}:
            op = self.next().text
            node = BinOp(op, node, self.factor())
        return node

    def factor(self):
        token = self.tok
        if token.kind == "string":
            self.next()
            return Const(token.text)
        if token.kind == "number":
            self.next()
            return Const(float(token.text))
        if token.kind == "op" and token.text == "-":
            self.next()
            return Neg(self.factor())
        if token.kind == "op" and token.text == "(":
            self.next()
            node = self.expr()
            self.expect("op", ")")
            return node
        if token.kind == "keyword" and token.text in {"TRUE", "FALSE"}:
            self.next()
            return Const(token.text == "TRUE")
        if token.kind == "sysvar":
            self.next()
            if self.at("op", "("):          # $SET_PRICING_FACTOR(...) style call
                return self.call(token.text)
            return SysVar(token.text)
        if token.kind == "ident":
            self.next()
            if self.at("op", "(") and token.text in _FUNCS:
                return self.call(token.text)
            return PropRef(token.text)
        raise RelationSyntaxError(f"unexpected {token.text or 'end'!r} in expression", token.pos)

    def call(self, name: str):
        self.expect("op", "(")
        args = []
        if not self.at("op", ")"):
            args.append(self.expr())
            while self.accept("op", ","):
                args.append(self.expr())
        self.expect("op", ")")
        return Func(name, tuple(args))

    # -- statements
    def statement(self):
        if self.tok.kind in {"ident", "sysvar"} and self.peek().kind == "op" and self.peek().text == "=":
            target = self.next().text
            self.next()
            expr = self.expr()
            cond = self.condition() if self.accept("keyword", "IF") else None
            self.finish()
            return Assign(target, expr, cond)
        if self.tok.kind == "sysvar" and self.tok.text.replace("_", "").replace("$", "") == "SETPRICINGFACTOR" \
                or (self.tok.kind == "sysvar" and self.tok.text.startswith("$SET")):
            call = self.factor()
            cond = self.condition() if self.accept("keyword", "IF") else None
            self.finish()
            if isinstance(call, Func) and len(call.args) == 2:
                return PricingFactor(call.args[0], call.args[1], cond)
            raise RelationSyntaxError("$SET_PRICING_FACTOR needs (variant condition, factor)", self.tok.pos)
        raise RelationSyntaxError(f"not an assignment: {self.tok.text!r}", self.tok.pos)


def split_top_level(text: str, separator: str = ",") -> list[str]:
    """Split on ``separator`` outside quotes and parentheses."""
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    quoted = False
    for ch in text:
        if ch == "'":
            quoted = not quoted
        elif not quoted:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
            elif ch == separator and depth == 0:
                parts.append("".join(current))
                current = []
                continue
        current.append(ch)
    parts.append("".join(current))
    return parts


_LABEL_RE = re.compile(r"^\s*Restrictions\s*:\s*", re.IGNORECASE)


@lru_cache(maxsize=None)
def parse_condition(text: str):
    """Parse a precondition / selection-condition body into a condition AST."""
    cleaned = _LABEL_RE.sub("", text.strip())
    cleaned = cleaned.rstrip().rstrip(".").strip()
    parser = _Parser(cleaned)
    node = parser.condition()
    parser.finish()
    return node


@lru_cache(maxsize=None)
def parse_actions(text: str) -> tuple:
    """Parse an action/reaction body; unparsable clauses become :class:`Unsupported`."""
    statements = []
    for clause in split_top_level(text, ","):
        clause = clause.strip().rstrip(".").strip()
        if not clause:
            continue
        try:
            statements.append(_Parser(clause).statement())
        except RelationSyntaxError as error:
            statements.append(Unsupported(clause, str(error)))
    return tuple(statements)


_SECTION_RE = re.compile(r"\b(Objects|Condition|Restrictions|Inferences)\s*:", re.IGNORECASE)


@lru_cache(maxsize=None)
def parse_constraint(text: str) -> Constraint:
    sections: dict[str, str] = {}
    matches = list(_SECTION_RE.finditer(text))
    if not matches:
        raise RelationSyntaxError("constraint has no Objects/Condition/Restrictions section")
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).lower()] = text[match.end():end].strip().rstrip(".").strip()

    classes: list[tuple[str, str]] = []
    variables: list[tuple[str, str]] = []
    objects = sections.get("objects", "")
    for declaration in split_top_level(objects, ","):
        declaration = declaration.strip()
        if not declaration:
            continue
        head, _, where = re.split(r"\b(WHERE)\b", declaration, maxsplit=1, flags=re.IGNORECASE)[0:3] \
            if re.search(r"\bWHERE\b", declaration, re.IGNORECASE) else (declaration, "", "")
        match = re.match(r"^\s*(\w+)\s+IS_A\s+(\w+)\s*$", head, re.IGNORECASE)
        if match:
            classes.append((match.group(1).upper(), match.group(2).upper()))
        for declared in split_top_level(where, ";"):
            pair = re.match(r"^\s*(\w+)\s*=\s*(\w+)\s*$", declared)
            if pair:
                variables.append((pair.group(1).upper(), pair.group(2).upper()))

    condition = None
    if sections.get("condition"):
        condition = parse_condition(sections["condition"])

    restrictions = []
    for clause in split_top_level(sections.get("restrictions", ""), ","):
        clause = clause.strip().rstrip(".").strip()
        if not clause:
            continue
        try:
            parser = _Parser(clause)
            body = parser.condition()
            cond = parser.condition() if parser.accept("keyword", "IF") else None
            parser.finish()
            restrictions.append(ConstraintRelation(body, cond))
        except RelationSyntaxError as error:
            restrictions.append(Unsupported(clause, str(error)))

    inferences = tuple(
        name.strip().upper()
        for name in split_top_level(sections.get("inferences", ""), ",")
        if name.strip()
    )
    return Constraint(tuple(classes), tuple(variables), condition, tuple(restrictions), inferences)


# --------------------------------------------------------------------------- analysis


def referenced_properties(node, into: set[str] | None = None) -> set[str]:
    """Upper-case property names an AST reads (qualified names keep their prefix)."""
    names = into if into is not None else set()
    if node is None or isinstance(node, (Const, Unsupported)):
        return names
    if isinstance(node, PropRef):
        names.add(node.name)
    elif isinstance(node, Specified):
        names.add(node.name)
    elif isinstance(node, SysVar):
        pass
    elif isinstance(node, (And, Or)):
        for item in node.items:
            referenced_properties(item, names)
    elif isinstance(node, Not):
        referenced_properties(node.item, names)
    elif isinstance(node, (Compare, BinOp)):
        referenced_properties(node.left, names)
        referenced_properties(node.right, names)
    elif isinstance(node, Neg):
        referenced_properties(node.operand, names)
    elif isinstance(node, InSet):
        referenced_properties(node.expr, names)
        for value in node.values:
            referenced_properties(value, names)
    elif isinstance(node, Func):
        for arg in node.args:
            referenced_properties(arg, names)
    elif isinstance(node, TableCall):
        for _column, expr in node.params:
            referenced_properties(expr, names)
    elif isinstance(node, Assign):
        referenced_properties(node.expr, names)
        referenced_properties(node.cond, names)
    elif isinstance(node, PricingFactor):
        referenced_properties(node.variant, names)
        referenced_properties(node.factor, names)
        referenced_properties(node.cond, names)
    elif isinstance(node, ConstraintRelation):
        referenced_properties(node.body, names)
        referenced_properties(node.cond, names)
    elif isinstance(node, Constraint):
        referenced_properties(node.condition, names)
        for item in node.restrictions:
            referenced_properties(item, names)
    elif isinstance(node, (tuple, list)):
        for item in node:
            referenced_properties(item, names)
    return names


# --------------------------------------------------------------------------- compile cache


@dataclass(frozen=True)
class CompiledRelation:
    """A relation parsed once: AST, the properties it reads, or the parse error."""

    rel_type: int
    node: object = None
    refs: frozenset = frozenset()
    error: str = ""


_COMPILED: dict[tuple[int, str], CompiledRelation] = {}


def compile_relation(rel_type: int, text: str) -> CompiledRelation:
    """Parse ``text`` according to its relation type; cached by ``(type, text)``.

    Types 1 and 2 are conditions, 3/5/6 action lists, 4 a constraint. Parse
    failures are returned (``error`` set), never raised.
    """
    key = (rel_type, text)
    cached = _COMPILED.get(key)
    if cached is not None:
        return cached
    try:
        if rel_type in (1, 2):
            node = parse_condition(text)
        elif rel_type == 4:
            node = parse_constraint(text)
        else:
            node = parse_actions(text)
        refs = frozenset(referenced_properties(node))
        compiled = CompiledRelation(rel_type, node, refs)
    except RelationSyntaxError as error:
        compiled = CompiledRelation(rel_type, error=str(error))
    _COMPILED[key] = compiled
    return compiled
