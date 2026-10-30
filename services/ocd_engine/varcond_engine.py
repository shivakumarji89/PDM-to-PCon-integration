"""Variant conditions (``$VARCOND``) from price-domain relations (spec 3.2).

Price relations are actions in domain ``P``. ``$VARCOND`` is multivalued: every
assignment contributes one key, so the result is a list, never one overwritten
string. Keys are upper-cased because the price table is matched in upper case.
An assignment whose operands are undefined (e.g. a hidden property) assigns
nothing - which is exactly how Dalby omits the 6821/7030 keys on articles
that lack Access_Cutout / Cable_leg.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from services.ocd_engine import diagnostics as dg
from services.ocd_engine import model as m
from services.ocd_engine.computed_property_engine import execute_relations, relations_in_scope
from services.ocd_engine.relation_evaluator import EvalContext


@dataclass
class VarcondResult:
    keys: list[str] = field(default_factory=list)
    factors: dict[str, float] = field(default_factory=dict)


class VarcondEngine:
    def __init__(self, model: m.ArticleModel, sink: dg.DiagnosticSink | None = None) -> None:
        self.model = model
        self.sink = sink

    def run(self, assignments, ctx: EvalContext) -> VarcondResult:
        # Price relations may only touch auxiliary properties (spec 2.15), so
        # they run on a copy: nothing they assign may leak into the configuration.
        price_ctx = EvalContext(
            values=ctx.values, ban=ctx.ban, tables=ctx.tables,
            aliases=dict(ctx.aliases), computed=dict(ctx.computed),
        )
        scoped = relations_in_scope(self.model, assignments, m.ACTION, "P")
        execute_relations(scoped, price_ctx, self.sink, self.model.base_code)
        # de-duplicate, keep first-seen order: "not defined whether applied once or per relation" (3.2)
        return VarcondResult(list(dict.fromkeys(price_ctx.varconds)), dict(price_ctx.pricing_factors))
