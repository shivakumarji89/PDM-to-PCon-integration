"""One resolver for the fabric colours a configuration may use.

For a colour property of a discovered :class:`~services.ocd_engine.fabric.FabricScheme` it runs, per configuration:

1. read the selected fabric type from the configuration state;
2. take the colour candidates in repository source order, de-duplicated by code (first occurrence wins). With the
   ``relation`` mechanism every offered colour is a candidate and its own relations decide; with the ``prefix_text``
   fallback only colours whose code unambiguously extends the selected type code are candidates;
3. evaluate *every* applicable relation of each candidate with the engine's own evaluator (``evaluate``) - there is no
   second relation evaluator here. Property- and class-level preconditions are applied by the engine before the colour
   property is offered at all;
4. drop colours whose precondition is FALSE, whose relation cannot be parsed/evaluated, or that carry a relation type
   OCD does not define on a value (a selection condition is legal on a property only);
5. pick one colour: the first valid colour flagged ``is_default``, else the first valid colour in source order.

An unreadable relation is never read as "valid": the colour is rejected and the reason is recorded, so a relation the
engine cannot interpret cannot silently turn into "offer every colour". When the type is selected and no colour
survives, the engine rejects the configuration (``NO_FABRIC_COLOUR``).

AND/OR semantics are not decided here: a colour's relations are evaluated one by one by the evaluator (three-valued,
a precondition is violated only when definitely FALSE) and a colour must pass all of them, exactly as for any other
property value.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from services.ocd_engine import fabric
from services.ocd_engine import model as m
from services.ocd_engine.relation_evaluator import EvalContext, Tri, precondition_violated

#: ``evaluate(relation, context, owner) -> (result, error)``; ``error`` is set when the relation could not be used.
Evaluate = Callable[[m.RelationRef, EvalContext, str], "tuple[Tri, str | None]"]

SELECTED_EXPLICIT = "explicit-default"
SELECTED_FIRST = "first-valid"
SELECTED_NONE = "none"

#: Rejections kept individually per resolution; the counts per reason are always exact.
MAX_LISTED = 25

REASON_PRECONDITION = "precondition FALSE"
REASON_UNUSABLE = "relation unusable"
REASON_UNSUPPORTED = "unsupported relation type"
REASON_UNMAPPED = "not mapped to the selected type"
REASON_AMBIGUOUS = "ambiguous type prefix"


class FabricOverrideError(ValueError):
    """The manually selected fabric property cannot be resolved; nothing is enumerated."""


@dataclass(frozen=True)
class Rejection:
    value: str
    reason: str
    detail: str = ""


@dataclass(frozen=True)
class FabricResolution:
    colour_property: str
    type_property: str
    type_value: str | None
    mechanism: str
    candidates: tuple[str, ...]              # in source order, de-duplicated, before relation evaluation
    valid: tuple[str, ...]                   # candidates that passed every relation, in source order
    rejected: tuple[Rejection, ...]          # the first MAX_LISTED rejections
    rejected_counts: tuple[tuple[str, int], ...]
    selected: str | None
    selection: str                           # SELECTED_EXPLICIT / SELECTED_FIRST / SELECTED_NONE
    duplicates: int = 0

    @property
    def rejected_total(self) -> int:
        return sum(n for _, n in self.rejected_counts)

    @property
    def uncertain(self) -> bool:
        return any(reason in (REASON_UNUSABLE, REASON_UNSUPPORTED) for reason, _ in self.rejected_counts)

    def describe(self) -> str:
        counts = ", ".join(f"{n} {reason}" for reason, n in self.rejected_counts) or "none"
        chosen = (f"{self.selected} ({self.selection})" if self.selected is not None else "no valid colour")
        return (f"{self.colour_property} for {self.type_property}={self.type_value!r}: mechanism {self.mechanism}; "
                f"{len(self.candidates)} candidate(s), {len(self.valid)} valid, rejected: {counts}; selected {chosen}")


class FabricColourResolver:
    def __init__(self, model: m.ArticleModel, evaluate: Evaluate,
                 schemes: Sequence[fabric.FabricScheme] | None = None, fabric_property: str = "") -> None:
        self.model = model
        self._evaluate = evaluate
        if schemes is None:
            found = fabric.discover(model, fabric_property)
            self.schemes, self.unconfirmed = found.schemes, found.unconfirmed
            self.override, self.override_error, self.override_missing = (
                found.override, found.override_error, found.override_missing)
        else:
            self.schemes, self.unconfirmed = tuple(schemes), ()
            self.override = self.override_error = ""
            self.override_missing = False
        self._by_colour: dict[str, fabric.FabricScheme] = {s.colour_upper: s for s in self.schemes}
        self._type_values: dict[str, list[str]] = {}
        props = model.property_by_key()
        for prop in props.values():
            if prop.name_upper in {s.type_upper for s in self.schemes}:
                allowed = prop.allowed_keys
                self._type_values[prop.name_upper] = [v.value for v in prop.values
                                                      if allowed is None or v.key in allowed]

    @property
    def colour_properties(self) -> frozenset[str]:
        return frozenset(self._by_colour)

    @property
    def type_properties(self) -> frozenset[str]:
        return frozenset(s.type_upper for s in self.schemes)

    def scheme_of(self, colour_upper: str) -> fabric.FabricScheme | None:
        return self._by_colour.get(colour_upper)

    def type_selected(self, colour_upper: str, values: Mapping[str, object]) -> bool:
        scheme = self._by_colour.get(colour_upper)
        return scheme is not None and scheme.type_upper in values

    # ------------------------------------------------------------------ resolution
    def resolve(self, dim: m.PropertyDef, ctx: EvalContext) -> tuple[FabricResolution, list[m.ValueDef]]:
        """``(explanation, [the selected colour])``; the list is empty when no colour is valid."""
        scheme = self._by_colour[dim.name_upper]
        type_value = ctx.values.get(scheme.type_upper)
        type_text = None if type_value is None else str(type_value)
        allowed = dim.allowed_keys
        offered, seen, duplicates = [], set(), 0
        for value in dim.values:
            if allowed is not None and value.key not in allowed:
                continue
            if value.value in seen:
                duplicates += 1
                continue
            seen.add(value.value)
            offered.append(value)

        rejected: list[Rejection] = []
        counts: dict[str, int] = {}

        def reject(value: m.ValueDef, reason: str, detail: str = "") -> None:
            counts[reason] = counts.get(reason, 0) + 1
            if len(rejected) < MAX_LISTED:
                rejected.append(Rejection(value.value, reason, detail))

        if scheme.mechanism == fabric.MECH_PREFIX_TEXT and type_text is not None:
            members, ambiguous = fabric.prefix_members(type_text, offered, self._type_values[scheme.type_upper])
            member_codes = {v.value for v in members}
            for value in ambiguous:
                reject(value, REASON_AMBIGUOUS, "code extends several type codes")
            ambiguous_codes = {v.value for v in ambiguous}
            candidates = [v for v in offered if v.value in member_codes]
            unmapped = len(offered) - len(candidates) - len(ambiguous_codes)
            if unmapped:
                counts[REASON_UNMAPPED] = unmapped
        else:
            candidates = offered

        valid: list[m.ValueDef] = []
        for value in candidates:
            verdict = self._check(dim, value, ctx)
            if verdict is None:
                valid.append(value)
            else:
                reject(value, *verdict)

        selected = next((v for v in valid if v.is_default), None)
        selection = SELECTED_EXPLICIT if selected is not None else SELECTED_NONE
        if selected is None and valid:
            selected, selection = valid[0], SELECTED_FIRST
        return FabricResolution(
            colour_property=dim.name, type_property=scheme.type_property, type_value=type_text,
            mechanism=scheme.mechanism, candidates=tuple(v.value for v in candidates),
            valid=tuple(v.value for v in valid), rejected=tuple(rejected),
            rejected_counts=tuple(counts.items()), selected=selected.value if selected is not None else None,
            selection=selection, duplicates=duplicates,
        ), ([selected] if selected is not None else [])

    def _check(self, dim: m.PropertyDef, value: m.ValueDef, ctx: EvalContext) -> tuple[str, str] | None:
        """``None`` when every relation of ``value`` allows it, else ``(reason, detail)``."""
        for ref in value.relations:
            if ref.rel_type == m.SELECTION:
                return REASON_UNSUPPORTED, f"{ref.name}: a selection condition is not defined on a property value"
            if ref.rel_type != m.PRECONDITION or ref.domain.upper() != "C":
                continue
            result, error = self._evaluate(ref, ctx, f"value {dim.name}={value.value}")
            if error is not None:
                return REASON_UNUSABLE, f"{ref.name}: {error}"
            if precondition_violated(result):
                return REASON_PRECONDITION, ref.name
        return None
