"""Computed properties and relation actions (spec 2.15, appendix A).

Actions assign property values (a computed ``Code`` property, an auxiliary
property, ``$VARCOND``). They run in relation-object order within an entity,
and entities run article -> property classes -> properties (not hidden) ->
values (currently set), per spec 3.2.
"""
from __future__ import annotations

from services.ocd_engine import diagnostics as dg
from services.ocd_engine import model as m
from services.ocd_engine import relation_parser as rp
from services.ocd_engine.relation_evaluator import EvalContext, run_actions


def _ordered(relations, rel_type: int, domain: str):
    chosen = [r for r in relations if r.rel_type == rel_type and r.domain.upper() == domain]
    return sorted(chosen, key=lambda r: (r.order, r.name))


def relations_in_scope(model: m.ArticleModel, assignments, rel_type: int, domain: str):
    """``[(RelationRef, owner label)]`` in evaluation order for one configuration."""
    scoped = [(rel, "article") for rel in _ordered(model.article_relations, rel_type, domain)]
    for cls in sorted(model.classes, key=lambda c: (c.order, c.name)):
        scoped.extend((rel, f"class {cls.name}") for rel in _ordered(cls.relations, rel_type, domain))
    for item in sorted(assignments, key=lambda a: (a.prop.order, a.prop.name)):
        if item.hidden:
            continue
        scoped.extend((rel, f"property {item.prop.name}") for rel in _ordered(item.prop.relations, rel_type, domain))
    for item in sorted(assignments, key=lambda a: (a.prop.order, a.prop.name)):
        if item.hidden or item.value is None:
            continue
        scoped.extend(
            (rel, f"value {item.prop.name}={item.value.value}")
            for rel in _ordered(item.value.relations, rel_type, domain)
        )
    return scoped


def execute_relations(scoped, ctx: EvalContext, sink: dg.DiagnosticSink | None, article: str = "") -> None:
    for rel, owner in scoped:
        compiled = rp.compile_relation(rel.rel_type, rel.text)
        if compiled.error:
            if sink is not None:
                sink.add(dg.RELATION_PARSE_ERROR, compiled.error, article=article,
                         relation=rel.name, source=owner)
            continue
        report = run_actions(compiled.node, ctx)
        if sink is not None:
            for clause, reason in report.skipped:
                code = dg.UNSUPPORTED_SYNTAX if "not an assignment" in reason or "expected" in reason \
                    or "unexpected" in reason else dg.RELATION_EVAL_ERROR
                sink.add(code, f"clause skipped: {clause} ({reason})", article=article,
                         relation=rel.name, source=owner)


class ComputedPropertyEngine:
    """Runs configuration-domain (``C``) actions; results land in ``ctx.computed``."""

    def __init__(self, model: m.ArticleModel, sink: dg.DiagnosticSink | None = None) -> None:
        self.model = model
        self.sink = sink

    def run(self, assignments, ctx: EvalContext) -> dict[str, object]:
        scoped = relations_in_scope(self.model, assignments, m.ACTION, "C")
        execute_relations(scoped, ctx, self.sink, self.model.base_code)
        return ctx.computed
