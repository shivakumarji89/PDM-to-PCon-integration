"""Pricing-relation (PA_PRICING) generation.

Builds the OCD ``PA_PRICING`` relation body that merges a configuration to its
price variant conditions - the single "merging" method that ties the config
selections to the price records the Pricing workflow computed.

Two styles, both from the same source data (``article_varcond_terms`` +
``option_increments``):

* **Non-super** (article pricing) - property-concatenation, matching PDM's
  hand-authored ``PA_PRICING_*`` bodies::

      $VARCOND = Type + Number_Of_Fabrics,
      $VARCOND = Type + Number_Of_Fabrics + ' 6530=' + Base_Finish,

  The article-price line reconstructs the sliced dimension varcond from the
  config property codes; each incremental line appends ``' <optId>=' + <opt>``.

* **Super** (global pricing) - delegated to :class:`~services.varcond_service.
  VarCondService`, the offline port of PDM's *Generate VARCOND for PA_PRICING*
  (``$VARCOND = '<sub_item>' IF <config>`` per BOM sub-item).

No database access - everything comes from the active snapshot.
"""
from __future__ import annotations

import copy
from collections import defaultdict
from dataclasses import dataclass, field

from core.export_readiness import relation_object_key, resolve_entity_bindings
from models.snapshot import Snapshot
from models.relation_object import RelationObject
from services.base_service import BaseService
from services.varcond_service import VarCondService


@dataclass
class PricingRelationResult:
    """Result of a PA_PRICING relation generation run."""

    relation_name: str = ""
    body: str = ""
    is_super: bool = False
    relobj_name: str = ""           # OCD RelObj name (P_<prefix>); relation = PA_<prefix>
    component_base: str = ""        # component grouping key (for chunked PA_<base>_N)
    article_price_lines: list[str] = field(default_factory=list)
    incremental_lines: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # Character-count stamp (pCon Creator caps a single relation at 64000).
    char_count_total: int = 0        # whole relation body
    char_count_components: int = 0   # the per-component ($VARCOND = '<code>') lines
    definition_count: int = 0        # number of component definition lines


class PricingRelationService(BaseService):
    """Generate the PA_PRICING relation body offline (PDM parity)."""

    def generate(self, snapshot: Snapshot | None = None) -> PricingRelationResult:
        """Build the PA_PRICING relation body for the active snapshot."""
        snapshot = snapshot if snapshot is not None else self.context.active_snapshot
        result = PricingRelationResult()
        if snapshot is None:
            result.warnings.append("No active snapshot.")
            return result

        result.relation_name = self._relation_name(snapshot)

        # Super product -> reuse the VARCOND generator (PDM's own export).
        if snapshot.article_components:
            var = self._varcond_service().generate(snapshot=snapshot)
            result.is_super = True
            result.body = var.text
            result.warnings.extend(var.warnings)
            self._stamp_char_counts(result)
            return result

        # Non-super -> property-concatenation PA_PRICING.
        self._build_non_super(snapshot, result)
        self._stamp_char_counts(result)
        return result

    # -- character-count stamp --------------------------------------------
    PCON_RELATION_CHAR_LIMIT = 64000

    @classmethod
    def _stamp_char_counts(cls, result: "PricingRelationResult") -> None:
        """Stamp the relation body's character counts (total + the per-component
        lines) and warn when the body exceeds the pCon Creator 64000 limit."""
        body = result.body or ""
        result.char_count_total = len(body)
        comp_lines = [
            ln for ln in body.splitlines() if ln.startswith("$VARCOND = '")
        ]
        result.char_count_components = sum(len(ln) for ln in comp_lines)
        result.definition_count = len(comp_lines)
        if result.char_count_total > cls.PCON_RELATION_CHAR_LIMIT:
            result.warnings.append(
                f"Relation body is {result.char_count_total} characters - exceeds "
                f"the pCon Creator limit of {cls.PCON_RELATION_CHAR_LIMIT}. "
                "Increase the relation prefix length or split the relation."
            )

    def commit(
        self, snapshot: Snapshot, result: PricingRelationResult
    ) -> RelationObject | None:
        """Persist the generated PA_PRICING relation onto the snapshot.

        Upserts by name into ``relation_objects`` (Price-domain Action) so it
        travels with the project and exports. Returns the stored relation, or
        ``None`` when there is nothing to store.
        """
        if not result.body.strip():
            return None
        rel = RelationObject(
            name=result.relation_name,
            type_code="3",   # Action
            domain="P",      # Price
            order=100,
            body=result.body,
            # The one non-super price relation is generated over every article
            # of the snapshot, so each exported base article carries it
            # (tCOMd_Article.com_RelObjID, as legacy PDM bound each article to
            # its price relation). An imported article binding takes precedence.
            article_codes=self._base_article_codes(snapshot),
        )
        snapshot.relation_objects = [
            r for r in snapshot.relation_objects if r.name != rel.name
        ]
        snapshot.relation_objects.append(rel)
        return rel

    def _base_article_codes(self, snapshot: Snapshot) -> list[str]:
        """Base article codes exactly as the exporters write them."""
        xocd = getattr(getattr(self, "context", None), "xocd_export_service", None)
        return list(xocd._base_codes(snapshot)) if xocd is not None else []

    def _varcond_service(self) -> VarCondService:
        """A VarCondService that works even without a bound context, since its
        parsing helpers and ``generate(snapshot=...)`` never touch the DB."""
        vc = VarCondService.__new__(VarCondService)
        vc.context = getattr(self, "context", None)
        return vc

    # -- split generation (PA_<article-prefix> per group) -----------------
    def generate_split(
        self, snapshot: Snapshot | None = None, prefix_length: int = 6
    ) -> list[PricingRelationResult]:
        """Split a super product's PA_PRICING into ``PA_<article-prefix>`` relations.

        Groups the super items (``article_components`` parents) by their first
        ``prefix_length`` code characters and generates one relation per group,
        named ``PA_<prefix>`` (RelObj ``P_<prefix>``, domain P / type 3) - the
        golden OCD structure where an article is matched to its price relation by
        code prefix. A longer prefix yields more, smaller relations; a group
        whose body still exceeds the pCon 64000 limit is flagged (raise the
        prefix length). Deduplication runs within each group.
        """
        snapshot = snapshot if snapshot is not None else self.context.active_snapshot
        results: list[PricingRelationResult] = []
        if snapshot is None or not snapshot.article_components:
            return results
        n = max(1, int(prefix_length))
        code_by_id = {
            str(a.id): (a.code or "") for a in snapshot.articles if a.id is not None
        }
        groups: dict[str, list[str]] = defaultdict(list)
        for pid in snapshot.article_components:
            code = code_by_id.get(str(pid), str(pid))
            prefix = code[:n] if 0 < n < len(code) else code
            groups[prefix].append(str(pid))
        for prefix in sorted(groups):
            sub = copy.copy(snapshot)   # share all maps; narrow the BOM parents
            sub.article_components = {
                pid: snapshot.article_components[pid] for pid in groups[prefix]
            }
            var = self._varcond_service().generate(snapshot=sub)
            res = PricingRelationResult(
                relation_name=f"PA_{prefix}",
                relobj_name=f"P_{prefix}",
                body=var.text,
                is_super=True,
            )
            res.warnings.extend(var.warnings)
            self._stamp_char_counts(res)
            results.append(res)
        return results

    def commit_split(
        self, snapshot: Snapshot, results: list[PricingRelationResult]
    ) -> list[RelationObject]:
        """Persist the split ``PA_<prefix>`` relations onto the snapshot,
        replacing any prior ``PA_`` price relations. Returns the stored list."""
        if snapshot is None:
            return []
        kept = [
            r for r in snapshot.relation_objects
            if not (r.name or "").startswith("PA_")
        ]
        rels: list[RelationObject] = []
        for i, res in enumerate(results):
            if not res.body.strip():
                continue
            rels.append(RelationObject(
                name=res.relation_name, type_code="3", domain="P",
                order=100 + i, body=res.body,
            ))
        snapshot.relation_objects = kept + rels
        return rels

    # -- component-relation model (de-dup shared components) ---------------
    @staticmethod
    def _component_key(sub: str) -> str:
        """Component grouping key: the code BASE before the dimension suffix
        (e.g. 'DWE3TADAAL.0812S4M' -> 'DWE3TADAAL'), so every dimension variant
        of a component collapses into one PA_<base> relation."""
        sub = (sub or "").strip()
        dot = sub.find(".")
        return sub[:dot] if dot > 0 else sub

    def generate_component_relations(
        self, snapshot: Snapshot | None = None
    ) -> list[PricingRelationResult]:
        """De-duplicated, component-grouped price relations.

        Groups the globally de-duplicated VARCOND rules by the COMPONENT BASE
        they target - each component family's rules are stored ONCE in a
        ``PA_<base>`` relation (RelObj ``P_<base>``) instead of PDM's per-article
        copies. A base whose body would exceed the pCon 64000 limit is chunked
        into ordered ``PA_<base>_1/_2/...`` parts (all under one ``P_<base>``
        RelObj). The article->relation alignment comes from the BOM
        (:meth:`component_alignment`).
        """
        snapshot = snapshot if snapshot is not None else self.context.active_snapshot
        results: list[PricingRelationResult] = []
        if snapshot is None or not snapshot.article_components:
            return results
        var = self._varcond_service().generate(snapshot=snapshot)  # globally deduped
        groups: dict[str, list[str]] = defaultdict(list)
        for r in var.rules:
            groups[self._component_key(r.article)].append(r.rule)
        limit = self.PCON_RELATION_CHAR_LIMIT
        for key in sorted(groups):
            chunks = self._chunk_rules(groups[key], limit)
            multi = len(chunks) > 1
            for i, chunk in enumerate(chunks, start=1):
                body = ",\r\n".join(chunk) + "\r\n"
                res = PricingRelationResult(
                    relation_name=f"PA_{key}_{i}" if multi else f"PA_{key}",
                    relobj_name=f"P_{key}",   # one RelObj aggregates the base's parts
                    body=body, is_super=True, component_base=key,
                )
                self._stamp_char_counts(res)
                results.append(res)
        return results

    @staticmethod
    def _chunk_rules(rules: list[str], limit: int) -> list[list[str]]:
        """Pack rules into ordered chunks whose joined body stays under ``limit``
        (each rule + a ',\\r\\n' separator). A single rule bigger than the limit
        gets its own chunk."""
        chunks: list[list[str]] = []
        cur: list[str] = []
        cur_len = 0
        for rule in rules:
            add = len(rule) + 3
            if cur and cur_len + add > limit:
                chunks.append(cur)
                cur, cur_len = [], 0
            cur.append(rule)
            cur_len += add
        if cur:
            chunks.append(cur)
        return chunks or [[]]

    def component_alignment(
        self, snapshot: Snapshot
    ) -> dict[str, list[str]]:
        """Article code -> the ``PA_<base>`` relation names it references.

        Derived from the BOM (``article_components``): each super article links to
        the component relations for the sub-items it carries - the OCD RelObjRel
        alignment, where a shared component body is referenced, not copied.
        """
        code_by_id = {
            str(a.id): (a.code or "") for a in snapshot.articles if a.id is not None
        }
        out: dict[str, set] = defaultdict(set)
        for pid, comps in (snapshot.article_components or {}).items():
            art = code_by_id.get(str(pid), str(pid))
            for comp in comps:
                sub = (comp.get("sub_item") or "").strip()
                if not sub:
                    continue
                out[art].add(f"PA_{self._component_key(sub)}")
        return {art: sorted(names) for art, names in out.items()}

    # -- non-super generation ---------------------------------------------
    def _build_non_super(
        self, snapshot: Snapshot, result: PricingRelationResult
    ) -> None:
        vc = self._varcond_service()
        terms_by_article = snapshot.article_varcond_terms or {}
        increments_by_prefix = snapshot.option_increments or {}
        code_by_id = {
            str(a.id): (a.code or "") for a in snapshot.articles if a.id is not None
        }

        rep_id = next((aid for aid, t in terms_by_article.items() if t), None)
        if rep_id is None:
            result.warnings.append(
                "No config attributes loaded (article_varcond_terms) - "
                "cannot build the article-price VARCOND."
            )
            return
        item = code_by_id.get(str(rep_id), "")

        # Config property names in DisplayOrder (those that contribute a code).
        props: list[str] = []
        for term in terms_by_article[rep_id]:
            base_code = str(term.get("order_code", "") or "")
            hdo = int(term.get("has_dependent_options", 0) or 0)
            if not base_code and hdo == 0:
                continue
            props.append(vc._pcon_property_name(term.get("name", ""), item))
        if not props:
            result.warnings.append("No config properties carry an order code.")
            return

        concat = " + ".join(props)
        result.article_price_lines.append(f"$VARCOND = {concat}")

        # One incremental line per option that carries an increment anywhere.
        seen: set = set()
        for incs in increments_by_prefix.values():
            for inc in incs:
                option_id = inc.get("option_id")
                if option_id is None or option_id in seen:
                    continue
                seen.add(option_id)
                opt = vc._pcon_option_name(inc.get("option_name", ""))
                result.incremental_lines.append(
                    f"$VARCOND = {concat} + ' {option_id}=' + {opt}"
                )

        result.body = self._format_body(
            result.article_price_lines, result.incremental_lines
        )

    @staticmethod
    def _format_body(article_lines: list[str], inc_lines: list[str]) -> str:
        """Assemble the PA_PRICING body with PDM's section headers."""
        out: list[str] = [
            "*****************",
            "* Article prices",
            "*****************",
            "",
        ]
        out += [ln + "," for ln in article_lines]
        out += [
            "",
            "********************",
            "* Incremental prices",
            "********************",
            "",
        ]
        out += [ln + "," for ln in inc_lines]
        return "\r\n".join(out)

    @staticmethod
    def _relation_name(snapshot: Snapshot) -> str:
        product = snapshot.product
        code = (product.code if product else "") or "PRODUCT"
        return f"PA_PRICING_{code}"


# ---------------------------------------------------------------------------
# Generated price relations in the full MDB export
# ---------------------------------------------------------------------------
class PriceRelationExportError(RuntimeError):
    """The generated price relations cannot be exported safely; the message names the cause."""


_BLOCKED = "Price relation export blocked:\n"


def price_relation_names(prefix: str) -> tuple[str, str]:
    """``(relation object name, relation name)`` of a price relation: ``P_<prefix>`` / ``PA_<prefix>``.

    ``OcdExportService`` derives the relation name from the object name by inserting an ``A`` after
    the domain letter, so ``P_x`` yields ``PA_x`` (the legacy PDM and golden-MDB convention).
    """
    return f"P_{prefix}", f"PA_{prefix}"


def remove_superseded_price_relations(
    existing: list[RelationObject], generated: list[RelationObject]
) -> list[RelationObject]:
    """``existing`` without the price relations ``generated`` supersedes.

    Removed: a price-domain Action that collides by object or relation name with a generated one, and
    a price-domain Action without MDB ids named ``PA_*`` (the old generated naming). Everything else -
    B_/A_ relations, imported price containers that are not regenerated, manual relations - is kept.
    """
    object_names = {rel.name for rel in generated}
    relation_names = {rel.relation_name for rel in generated if rel.relation_name}

    def superseded(rel: RelationObject) -> bool:
        if str(rel.domain or "").upper() != "P" or str(rel.type_code or "") != "3":
            return False
        if rel.name in object_names or (rel.relation_name and rel.relation_name in relation_names):
            return True
        imported = bool(str(rel.rel_obj_id or "").strip() or str(rel.relation_id or "").strip())
        return not imported and (rel.name or "").startswith("PA_")

    return [rel for rel in existing if not superseded(rel)]


def merge_generated_price_relations(
    existing: list[RelationObject], generated: list[RelationObject]
) -> list[RelationObject]:
    """:func:`remove_superseded_price_relations` followed by ``generated``."""
    return remove_superseded_price_relations(existing, generated) + list(generated)


def validate_price_relation_bindings(
    generated: list[RelationObject], merged: list[RelationObject],
    valid_codes: set[str] | None = None,
) -> None:
    """Raise :class:`PriceRelationExportError` unless every generated relation binds real articles.

    Checks, per relation: it names at least one article; each article is one the export contains
    (``valid_codes``, when given); and across ``merged``: no article is claimed by two different
    relation objects and every generated relation keeps at least one article after imported bindings
    take precedence. Nothing is repaired or guessed.
    """
    problems: list[str] = []
    for rel in generated:
        label = rel.relation_name or rel.name
        codes = [str(code).strip() for code in rel.article_codes if str(code).strip()]
        if not codes:
            problems.append(f"{label}: no articles to bind (no engineering article maps to this prefix)")
        elif valid_codes is not None:
            unknown = sorted(code for code in codes if code not in valid_codes)
            if unknown:
                problems.append(f"{label}: article(s) not in the export: {', '.join(unknown[:5])}"
                                + (" ..." if len(unknown) > 5 else ""))
    if problems:
        raise PriceRelationExportError(_BLOCKED + "\n".join(problems))

    articles, _classes, conflicts = resolve_entity_bindings(merged)
    if conflicts:
        raise PriceRelationExportError(_BLOCKED + "\n".join(message for _entity, message in conflicts[:10]))
    for rel in generated:
        key = relation_object_key(rel)
        if not any(articles.get(str(code)) == key for code in rel.article_codes):
            problems.append(f"{rel.relation_name or rel.name}: every article is already bound to another "
                            "relation object, so this relation would be unreachable")
    if problems:
        raise PriceRelationExportError(_BLOCKED + "\n".join(problems))


def prepare_price_relation_export(context, export_snapshot: Snapshot, generated: list[RelationObject]) -> None:
    """Put ``generated`` onto the isolated ``export_snapshot`` and validate it (never the live snapshot).

    Superseded price relations are removed first; if no other relation object remains they are
    derived (B_/A_), so the export keeps the same configuration relations as the plain export.
    """
    export_snapshot.relation_objects = remove_superseded_price_relations(
        export_snapshot.relation_objects or [], generated)
    context.engineering_relation_service.ensure_relation_objects(export_snapshot)
    export_snapshot.relation_objects = list(export_snapshot.relation_objects) + list(generated)

    valid_codes = None
    xocd = getattr(context, "xocd_export_service", None)
    if xocd is not None and hasattr(xocd, "_base_codes"):
        valid_codes = set(xocd._base_codes(export_snapshot))
    validate_price_relation_bindings(generated, export_snapshot.relation_objects, valid_codes)
