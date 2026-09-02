"""Snapper service - bulk OBX permutation generation for the Builder.

Turns selected articles and property-value selections into every meaningful
configuration (cartesian product + hierarchy resolution) and renders them as a
pCon ``.obx`` basket. Each generated article carries the :data:`~services.
obx_service.OBX_SENTINEL` in its ``final`` number so a pCon-updated file can be
cleaned back to only the valid configurations (see :meth:`OBXService.clean_obx`).

Concept ported from the MK_OFML_Testsuite snapper generator, but driven from the
in-memory snapshot (articles / properties / values) instead of OCD CSVs.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.engines.permutations import (
    build_varcode,
    compute_permutations,
    expand_with_children,
)
from services.base_service import BaseService
from services.obx_service import OBX_SENTINEL, OBXArticle, OBXFeature, OBXService
from services.xocd_export_service import XocdExportService


@dataclass
class SnapperResult:
    """Outcome of a snapper generation run."""

    permutations: list[dict[str, Any]] = field(default_factory=list)
    xml: str = ""
    count: int = 0
    warnings: list[str] = field(default_factory=list)


class SnapperService(BaseService):
    """Generate bulk OBX permutations from snapshot selections."""

    @staticmethod
    def _pcon_name(prop_name: str) -> str:
        name = prop_name
        paren = name.find(" (")
        if paren > -1:
            name = name[:paren]
        return name.replace(" ", "_")

    def available_dimensions(self, snapshot=None) -> dict[str, list[dict[str, str]]]:
        """Selectable properties -> their value ``{code, label}`` list (for the UI)."""
        snapshot = snapshot if snapshot is not None else self.context.active_snapshot
        out: dict[str, list[dict[str, str]]] = {}
        if snapshot is None:
            return out
        prop_name_by_id = {p.id: p.name for p in snapshot.properties if p.id}
        for pv in snapshot.property_values:
            pname = prop_name_by_id.get(pv.property_id or "")
            if not pname:
                continue
            key = self._pcon_name(pname)
            out.setdefault(key, []).append(
                {"code": pv.code or pv.value, "label": pv.value}
            )
        return out

    def derive_child_resolutions(
        self, snapshot=None
    ) -> tuple[dict[str, dict[str, Any]], set[str]]:
        """Build hierarchy ``child_resolutions`` from snapshot dependency edges.

        A property is a *child* when its values are enabled by another property's
        values (fabric Type -> Colour). Returns ``({child_prop: {"parent":
        parent_prop, "map": {parent_code: [child_codes]}}}, child_prop_names)`` so
        the caller can exclude child properties from the cartesian dimensions and
        resolve them per parent instead. Uses ``attribute_option_dependencies`` +
        ``option_option_dependencies`` (value-id -> enabled value-ids).
        """
        snapshot = snapshot if snapshot is not None else self.context.active_snapshot
        if snapshot is None:
            return {}, set()

        prop_name_by_id = {p.id: p.name for p in snapshot.properties if p.id}
        opt_name_by_id = {o.id: o.name for o in snapshot.options if o.id}
        info: dict[str, tuple[str, str]] = {}
        for pv in snapshot.property_values:
            pname = prop_name_by_id.get(pv.property_id or "")
            if pname:
                info[str(pv.id)] = (self._pcon_name(pname), (pv.code or "").strip())
        for ov in snapshot.option_values:
            oname = opt_name_by_id.get(ov.option_id or "")
            if oname:
                info[str(ov.id)] = (self._pcon_name(oname), (ov.code or "").strip())

        edges: dict[str, list[str]] = {}
        for src_map in (
            snapshot.attribute_option_dependencies or {},
            snapshot.option_option_dependencies or {},
        ):
            for src, targets in src_map.items():
                bucket = edges.setdefault(str(src), [])
                for target in targets:
                    if str(target) not in bucket:
                        bucket.append(str(target))

        child_res: dict[str, dict[str, Any]] = {}
        for parent_id, child_ids in edges.items():
            parent = info.get(parent_id)
            if parent is None or not parent[1]:
                continue
            p_prop, p_code = parent
            for cid in child_ids:
                child = info.get(cid)
                if child is None or not child[1]:
                    continue
                c_prop, c_code = child
                if c_prop == p_prop:
                    continue
                entry = child_res.setdefault(c_prop, {"parent": p_prop, "map": {}})
                if entry["parent"] != p_prop:  # keep first parent (single-parent)
                    continue
                codes = entry["map"].setdefault(p_code, [])
                if c_code not in codes:
                    codes.append(c_code)
        return child_res, set(child_res.keys())

    def generate(
        self,
        article_codes: list[str],
        selections: dict[str, list[str]],
        child_resolutions: dict[str, dict[str, Any]] | None = None,
        distribute: bool = False,
        manufacturer_id: str = "HM",
        series_id: str | None = None,
        ofml_class_suffix: str = "_OPT",
        use_sentinel: bool = True,
        snapshot=None,
    ) -> SnapperResult:
        """Build the OBX for ``article_codes`` x ``selections`` permutations."""
        result = SnapperResult()
        snapshot = snapshot if snapshot is not None else self.context.active_snapshot
        if snapshot is None or snapshot.product is None:
            result.warnings.append("No active snapshot.")
            return result
        if not article_codes:
            result.warnings.append("No articles selected.")
            return result

        sid = series_id or XocdExportService.series_id(snapshot.product)
        ofml_class = sid + ofml_class_suffix

        dims = {k: list(v) for k, v in (selections or {}).items() if v}
        perms = compute_permutations(list(article_codes), dims)
        perms = expand_with_children(perms, child_resolutions or {}, distribute)
        result.permutations = perms

        obx_articles: list[OBXArticle] = []
        for perm in perms:
            props: dict[str, str] = perm["properties"]
            varcode = build_varcode(ofml_class, props)
            final = (
                OBX_SENTINEL
                if use_sentinel
                else (perm["article"] + " " + varcode).strip()
            )
            features = [
                OBXFeature(name=k, value=v, flags="1", descr_field0=k, descr_field1=v)
                for k, v in props.items()
            ]
            obx_articles.append(
                OBXArticle(
                    base_code=perm["article"],
                    final_code=final,
                    ofml_varcode=varcode,
                    manufacturer_id=manufacturer_id,
                    series_id=sid,
                    description="",
                    features=features,
                )
            )

        result.count = len(obx_articles)
        result.xml = OBXService(self.context)._render_xml(obx_articles)
        if not obx_articles:
            result.warnings.append("No permutations generated.")
        return result
