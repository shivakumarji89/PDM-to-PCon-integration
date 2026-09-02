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
        )
        snapshot.relation_objects = [
            r for r in snapshot.relation_objects if r.name != rel.name
        ]
        snapshot.relation_objects.append(rel)
        return rel

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
