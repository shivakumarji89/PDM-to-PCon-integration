"""CodeScheme engine: tokenizes and encodes OCD final article numbers (spec 2.24, 4).

Two grammars exist and are *not* interchangeable:

* **Predefined** (``KeyValueList`` / ``ValueList``, spec 4.1): the final number is
  ``base + VarCodeSep + variant code``; the variant code is generated from the
  property table using fields 4-10 of the scheme row.
* **User-defined** (spec 4.2): ``[<Class>:<Property> | <TableCall> | @ | <Char>,]``,
  processed left to right. The whole final number comes from this walk -
  ``@`` is the next character of the base number, any other segment is a
  literal. There is no separate "base + separator + variant" step.

A property referenced by a user-defined scheme may be computed by a relation
action (Aeron's ``AERON_OPTIONS:Code``); the engine reads it through the same
:class:`PropertyView` as any other property.

Final-article encoding is kept apart from OBX ``ofmlvarcode`` serialization
(that lives in the OBX layer).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from services.ocd_engine import diagnostics as dg
from services.ocd_engine import relation_parser as rp
from services.ocd_engine.relation_evaluator import EvalContext, eval_expr


# ------------------------------------------------------------------ definition


@dataclass(frozen=True)
class CodeSchemeDef:
    scheme_id: str = ""
    scheme: str = ""
    varcode_sep: str = ""
    value_sep: str = ""
    visibility: str = ""        # "0" valid+visible only, "1" all configurable, "" => 1 (user-defined)
    invisible_char: str = ""    # default '-'
    unselect_char: str = ""     # default 'X'
    trim: bool = True
    mo_sep: str = ""            # default ','
    mo_bracket: str = ""

    @property
    def is_predefined(self) -> bool:
        return self.scheme.strip().upper() in {"KEYVALUELIST", "VALUELIST"}

    @classmethod
    def from_row(cls, row: dict) -> "CodeSchemeDef":
        """Build from a ``codescheme`` row (CSV field names or legacy snapshot keys)."""
        lowered = {str(k).lower(): v for k, v in row.items()}

        def pick(*keys: str) -> str:
            for key in keys:
                if key in lowered and lowered[key] is not None:
                    return str(lowered[key])
            return ""

        trim_text = pick("trim").strip().lower()
        return cls(
            scheme_id=pick("scheme_id", "schemeid", "id"),
            scheme=pick("scheme", "body"),
            varcode_sep=pick("varcode_sep", "varcodesep", "var_code_sep"),
            value_sep=pick("value_sep", "valuesep"),
            visibility=pick("visibility").strip(),
            invisible_char=pick("invisible_char", "invisiblechar"),
            unselect_char=pick("unselect_char", "unselectchar"),
            trim=trim_text in {"", "1", "true", "yes", "y"},
            mo_sep=pick("mo_sep", "mosep"),
            mo_bracket=pick("mo_bracket", "mobracket"),
        )


# ------------------------------------------------------------------ tokens


@dataclass(frozen=True)
class AtToken:
    pass


@dataclass(frozen=True)
class LiteralToken:
    text: str


@dataclass(frozen=True)
class PropToken:
    property_class: str
    property_name: str

    @property
    def key(self) -> str:
        return f"{self.property_class}:{self.property_name}"


@dataclass(frozen=True)
class MixedToken:
    """A segment holding literal text *and* ``Class:Property`` references.

    Not part of the OCD grammar; accepted because older repository data was
    written that way. Reported by :func:`tokenize` consumers as a warning.
    """
    text: str


@dataclass(frozen=True)
class TableToken:
    call: rp.TableCall


_PROP_SEGMENT = re.compile(r"^\s*([A-Za-z0-9_]+):([A-Za-z0-9_]+)\s*$")
_PROP_INLINE = re.compile(r"([A-Za-z0-9_]+):([A-Za-z0-9_]+)")


@lru_cache(maxsize=None)
def tokenize(scheme: str) -> tuple:
    """Tokenize a user-defined scheme. Literal segments (including a lone space) are kept."""
    tokens: list = []
    for segment in rp.split_top_level(scheme, ","):
        if segment == "@" or segment.strip() == "@":
            tokens.append(AtToken())
            continue
        match = _PROP_SEGMENT.match(segment)
        if match:
            tokens.append(PropToken(match.group(1), match.group(2)))
            continue
        if segment.strip().upper().startswith("TABLE") and "(" in segment:
            try:
                tokens.append(TableToken(rp.parse_condition(segment.strip())))
                continue
            except rp.RelationSyntaxError:
                pass
        if _PROP_INLINE.search(segment):
            tokens.append(MixedToken(segment))
        else:
            tokens.append(LiteralToken(segment))
    return tuple(tokens)


# ------------------------------------------------------------------ property view


@dataclass(frozen=True)
class EncodedValue:
    """What the encoder needs to know about one property in the configuration."""

    text: str = ""                      # current value ("" = no value)
    visible: bool = True                # False = currently invalid / hidden by a precondition
    optional: bool = False              # may legitimately be left unselected
    length: int = 0                     # 'digits' of the property table
    multi: tuple[str, ...] = ()         # all values of a multi-valued property


class PropertyView(Protocol):
    def get(self, property_class: str, property_name: str) -> EncodedValue | None: ...
    def ordered(self) -> list[tuple[str, str]]: ...


@dataclass
class EncodeResult:
    final_article: str
    variant_code: str
    kind: str                           # "user" | "predefined"


# ------------------------------------------------------------------ encoder


def _format_value(value: EncodedValue, scheme: CodeSchemeDef, *, force_mode: str | None = None) -> str | None:
    """Text of one property per scheme fields 5-10. ``None`` = property not included."""
    mode = force_mode if force_mode is not None else (scheme.visibility or "1")
    invisible = (scheme.invisible_char or "-")[:1]
    unselect = (scheme.unselect_char or "X")[:1]
    width = max(value.length, 0)

    if not value.visible:
        if mode == "0":
            return ""
        return invisible * max(width, 1)
    values = list(value.multi) if len(value.multi) > 1 else ([value.text] if value.text != "" else [])
    if not values:
        if value.optional:
            return unselect * max(width, 1)
        return ""
    if len(values) > 1 or value.multi:
        sep = scheme.mo_sep or ","
        joined = sep.join(values)
        bracket = scheme.mo_bracket
        if bracket and len(bracket) % 2 == 0:
            half = len(bracket) // 2
            joined = bracket[:half] + joined + bracket[half:]
        return joined
    text = values[0]
    if not scheme.trim and width:
        text = text.ljust(width)
    return text


class CodeSchemeEncoder:
    """Encodes one article's final number from a scheme row and a property view."""

    def __init__(self, scheme: CodeSchemeDef, *, base_prefix_when_no_at: bool = False,
                 tables: dict | None = None) -> None:
        self.scheme = scheme
        self.base_prefix_when_no_at = base_prefix_when_no_at
        self.tables = tables or {}
        self.tokens = () if scheme.is_predefined else tokenize(scheme.scheme)

    def referenced_properties(self) -> list[tuple[str, str]]:
        out = []
        for token in self.tokens:
            if isinstance(token, PropToken):
                out.append((token.property_class, token.property_name))
            elif isinstance(token, MixedToken):
                out.extend(_PROP_INLINE.findall(token.text))
        return out

    # -- public
    def encode(self, base_code: str, view: PropertyView, sink: dg.DiagnosticSink | None = None,
               article: str = "") -> EncodeResult | None:
        if self.scheme.is_predefined:
            return self._encode_predefined(base_code, view)
        return self._encode_user(base_code, view, sink, article)

    # -- predefined schemes (4.1)
    def _encode_predefined(self, base_code: str, view: PropertyView) -> EncodeResult:
        scheme = self.scheme
        parts: list[str] = []
        if scheme.scheme.strip().upper() == "KEYVALUELIST":
            for cls_name, prop in view.ordered():
                value = view.get(cls_name, prop)
                if value is None or not value.visible:
                    continue                                   # only currently valid properties
                text = value.text if value.text != "" else "VOID"
                if len(value.multi) > 1:
                    text = _format_value(value, scheme) or text
                parts.append(f"{cls_name}.{prop}={text}")
            variant = ";".join(parts)                          # ';' is fixed for this scheme
        else:
            mode = scheme.visibility or "1"
            for cls_name, prop in view.ordered():
                value = view.get(cls_name, prop)
                if value is None:
                    continue
                text = _format_value(value, scheme, force_mode=mode)
                if mode == "0" and not value.visible:
                    continue
                parts.append(text or "")
            variant = scheme.value_sep.join(parts)
        return EncodeResult(base_code + scheme.varcode_sep + variant, variant, "predefined")

    # -- user-defined schemes (4.2)
    def _encode_user(self, base_code: str, view: PropertyView, sink, article: str) -> EncodeResult | None:
        scheme = self.scheme
        final: list[str] = []
        variant: list[str] = []
        base_index = 0
        has_at = False
        recognised = False

        for token in self.tokens:
            if isinstance(token, AtToken):
                recognised = has_at = True
                if base_index < len(base_code):
                    final.append(base_code[base_index])
                    base_index += 1
            elif isinstance(token, PropToken):
                recognised = True
                value = view.get(token.property_class, token.property_name)
                if value is None:
                    if sink is not None:
                        sink.add(dg.MISSING_PROPERTY,
                                 f"scheme references unknown property {token.key}",
                                 article=article, property=token.key)
                    return None
                text = _format_value(value, scheme) or ""
                final.append(text)
                variant.append(text)
            elif isinstance(token, MixedToken):
                recognised = True

                def replace(match, _view=view):
                    value = _view.get(match.group(1), match.group(2))
                    return (_format_value(value, scheme) or "") if value is not None else ""

                rendered = _PROP_INLINE.sub(replace, token.text)
                final.append(rendered)
                if rendered:
                    variant.append(rendered)
            elif isinstance(token, TableToken):
                recognised = True
                text = self._table_value(token, view, base_code, sink, article)
                if text is None:
                    return None
                final.append(text)
                variant.append(text)
            else:
                final.append(token.text)
                if token.text:
                    variant.append(token.text)

        if not recognised:
            return None
        final_text, variant_text = "".join(final), "".join(variant)
        if not has_at and self.base_prefix_when_no_at:
            return EncodeResult(base_code + final_text, variant_text, "user")
        return EncodeResult(final_text, variant_text, "user")

    def _table_value(self, token: TableToken, view: PropertyView, base_code: str, sink, article: str):
        """A ``TABLE`` segment yields the unique ``$FAN`` value of the matching line (spec 4.2)."""
        table = self.tables.get(token.call.table.upper())
        if table is None:
            if sink is not None:
                sink.add(dg.MISSING_TABLE, f"scheme calls unknown table {token.call.table}",
                         article=article)
            return None
        values = {}
        for cls_name, prop in view.ordered():
            current = view.get(cls_name, prop)
            if current is not None and current.text != "":
                values[prop.upper()] = current.text
        ctx = EvalContext(values=values, ban=base_code)
        wanted = {}
        for column, expr in token.call.params:
            if column.upper() == "$FAN":
                continue
            value = eval_expr(expr, ctx)
            if value is None:
                return None
            wanted[column.upper()] = value
        found = []
        for line in table.lines:
            norm = {str(k).upper(): v for k, v in line.items()}
            if all(str(norm.get(c, "")).upper() == str(v).upper() for c, v in wanted.items()):
                if "$FAN" in norm:
                    found.append(str(norm["$FAN"]))
        if len(set(found)) != 1:
            if sink is not None:
                sink.add(dg.UNSUPPORTED_ENCODING,
                         f"table {token.call.table} gave {len(set(found))} $FAN results (undefined)",
                         article=article)
            return None
        return found[0]
