"""Generate Article OBX permutations from repository configuration data.

In the repository/MDB model an Article is a *base article*. A permutation is a
runtime configuration built from that base article's classes/properties,
property values, relations, ArtBase restrictions and code scheme. Existing
Article rows are therefore inputs (base identities), never generated variants.

Relation evaluation, computed properties, VARCOND collection and CodeScheme
encoding are delegated to the standalone engine in ``services/ocd_engine``
through ``ocd_engine_adapter``; this service keeps the repository-specific
parts (dimension discovery, options, exclusions, ArtBase).
"""
from __future__ import annotations
from core.cancellation import checkpoint, OperationCancelled

import itertools
import re
from dataclasses import dataclass

from models.snapshot import Snapshot
from services.article_obx import ocd_engine_adapter as adapter
from services.article_obx.article_obx_models import (
    ArticleConfigurationValue,
    ArticlePermutation,
)
from services.base_service import BaseService
from services.ocd_engine import diagnostics as dg
from services.ocd_engine import model as ocd_model
from services.ocd_engine.codescheme_engine import CodeSchemeEncoder
from services.ocd_engine.configuration_engine import ConfigurationEngine, EnumerationLimits


@dataclass(frozen=True)
class _Dimension:
    kind: str
    entity_id: str
    name: str
    display_order: int
    values: tuple[object, ...]


class ArticlePermutationService(BaseService):
    """Build valid final article numbers from a repository Snapshot."""

    #: Safeguard against permutation explosion. When an article would exceed
    #: this many configurations the build stops for that article and records an
    #: ``ENUMERATION_TRUNCATED`` error in ``last_diagnostics`` (never silent).
    #: ``None`` disables the limit.
    max_permutations_per_article: int | None = 250_000

    #: When a user-defined scheme has no ``@``, the legacy generator prefixed the
    #: base article. OCD 4.2 says the scheme alone produces the whole number, so
    #: the standalone engine defaults to ``False``; the repository generator
    #: keeps ``True`` until the owner decides (see docs/02_Domain/OBX).
    legacy_base_prefix_without_at: bool = True

    #: Diagnostics of the most recent ``build`` (rejections, unsupported syntax, truncation).
    last_diagnostics: dg.DiagnosticSink | None = None

    def build(self, snapshot: Snapshot | None = None, *, reporter=None) -> list[ArticlePermutation]:
        checkpoint()
        snapshot = snapshot or self.context.qa_snapshot
        sink = dg.DiagnosticSink()
        self.last_diagnostics = sink
        if snapshot is None:
            if reporter is not None:
                reporter.begin(1, title="Building Article Permutations")
                reporter.finish(True, "No repository snapshot is loaded")
            return []

        results: list[ArticlePermutation] = []
        seen: set[tuple] = set()

        relation_index = adapter.SnapshotRelationIndex(getattr(snapshot, "relation_objects", []) or [])
        tables = adapter.value_tables(snapshot)

        articles = sorted(
            snapshot.articles,
            key=lambda item: ((item.code or "").strip(), str(item.id or "")),
        )
        if reporter is not None:
            reporter.begin(len(articles) or 1, title="Building Article Permutations")

        for article in articles:
            checkpoint()
            base_code = (article.code or "").strip()
            if not base_code:
                if reporter is not None:
                    reporter.advance()
                continue

            if reporter is not None:
                reporter.advance(f"Building {base_code}")

            self._build_article(
                snapshot, article, base_code, relation_index, tables, results, seen, sink, reporter,
            )

            if reporter is not None:
                reporter.advance(
                    f"Completed {base_code} — {len(results)} permutation(s)"
                )

        results.sort(
            key=lambda item: (
                item.base_code,
                item.final_article,
                tuple(v.value_id for v in item.properties),
                tuple(v.value_id for v in item.options),
            )
        )
        checkpoint()
        return results

    def _build_article(self, snapshot, article, base_code, relation_index, tables,
                       results, seen, sink, reporter) -> None:
        limit = self.max_permutations_per_article
        dimensions = self._property_dimensions(snapshot, article.id, base_code)
        property_defs = tuple(
            adapter.property_def(d, relation_index, base_code, order=index)
            for index, d in enumerate(dimensions)
        )
        dimension_by_key = {pdef.key: dim for pdef, dim in zip(property_defs, dimensions)}
        scheme_id = self._scheme_id(snapshot, article.id)
        scheme = adapter.scheme_definition(self._scheme(snapshot, article.id))
        model = ocd_model.ArticleModel(
            base_code=base_code, article_key=str(article.id or ""),
            properties=property_defs,
            article_relations=relation_index.article_level(base_code),
            tables=tables, scheme_id=scheme_id,
        )
        engine = ConfigurationEngine(
            model, sink=sink,
            limits=EnumerationLimits(max_configurations=limit),
            rhs_values_factory=lambda values, assignments: adapter.codes_by_name(assignments),
        )
        encoder = CodeSchemeEncoder(
            scheme, base_prefix_when_no_at=self.legacy_base_prefix_without_at, tables=tables,
        )
        option_cache: dict[tuple, tuple[ocd_model.PropertyDef, ...]] = {}
        count = 0

        for config in engine.enumerate(property_defs):
            checkpoint()
            by_key = {a.prop.key: a for a in config.assignments}
            ordered = tuple(by_key[pdef.key] for pdef in property_defs)
            properties = tuple(
                self._configuration_value(dimension_by_key[a.prop.key], a)
                for a in ordered if a.value is not None and not a.hidden
            )
            property_ids = {v.value_id for v in properties}

            if not self._valid_art_base(snapshot, base_code, property_ids, {v.entity_id for v in properties}):
                continue
            if not self._valid_exclusions(snapshot, property_ids):
                continue

            option_dimensions = self._option_dimensions(snapshot, article, property_ids, base_code)
            option_defs = self._option_defs(option_dimensions, relation_index, base_code, option_cache)
            option_dimension_by_key = {
                pdef.key: dim for pdef, dim in zip(option_defs, option_dimensions)
            }
            option_products = (
                itertools.product(*(d.values for d in option_defs)) if option_defs else [()]
            )

            for selected_options in option_products:
                checkpoint()
                try:
                    option_assignments = tuple(
                        ocd_model.Assignment(d, v) for d, v in zip(option_defs, selected_options)
                    )
                    options = tuple(
                        self._configuration_value(option_dimension_by_key[a.prop.key], a)
                        for a in option_assignments
                    )
                    all_ids = {v.value_id for v in (*properties, *options)}

                    if not self._valid_art_base(snapshot, base_code, all_ids, {v.entity_id for v in (*properties, *options)}):
                        continue
                    if not self._valid_exclusions(snapshot, all_ids):
                        continue

                    assignments = ordered + option_assignments
                    final = engine.finalize(assignments)
                    if not final.valid:
                        continue

                    encoded = encoder.encode(
                        base_code, engine.view(assignments, final.computed), sink, base_code,
                    )
                    if encoded is None:
                        continue

                    # Semantic identity, not the encoded text: two distinct
                    # configurations (different selected value IDs) may
                    # legitimately encode to the same visible final article
                    # (e.g. a property that does not feed the CodeScheme at
                    # all) and must both be kept, not silently merged.
                    key = (
                        str(article.id or ""),
                        tuple(v.value_id for v in properties),
                        tuple(v.value_id for v in options),
                    )
                    if key in seen:
                        continue
                    if limit is not None and count >= limit:
                        self._truncated(sink, base_code, limit, count, reporter)
                        return
                    seen.add(key)

                    varconds = tuple(dict.fromkeys(x for x in final.varconds if x))
                    results.append(
                        self._make_permutation(
                            article, base_code, properties, options, varconds,
                            encoded.final_article, encoded.variant_code, scheme_id,
                            tuple(final.pricing_factors.items()),
                        )
                    )
                    count += 1
                    if reporter is not None:
                        reporter.note(f"Building {base_code} — {count} permutations")
                except OperationCancelled:
                    raise
                except Exception as error:  # noqa: BLE001 - one bad configuration must not abort the build
                    sink.add(dg.RELATION_EVAL_ERROR, f"skipped an invalid configuration ({error})",
                             article=base_code)
                    if reporter is not None:
                        reporter.log(
                            "error",
                            f"{base_code}: skipped an invalid configuration ({error})",
                        )
        if engine.stats.truncated:
            self._truncated(sink, base_code, limit, count, reporter, already_recorded=True)

    @staticmethod
    def _truncated(sink, base_code, limit, count, reporter, already_recorded=False) -> None:
        if not already_recorded:
            sink.add(dg.ENUMERATION_TRUNCATED,
                     f"permutation limit {limit} reached after {count} configuration(s); "
                     f"the result for this article is incomplete",
                     dg.Severity.ERROR, article=base_code)
        if reporter is not None:
            reporter.log("error", f"{base_code}: permutation limit reached; result incomplete")

    @staticmethod
    def _configuration_value(dimension: _Dimension, assignment) -> ArticleConfigurationValue:
        value = assignment.value
        return ArticleConfigurationValue(
            kind=dimension.kind,
            entity_id=dimension.entity_id,
            value_id=value.key,
            name=dimension.name,
            value=value.value,
            code=value.code,
            display_order=dimension.display_order,
        )

    @staticmethod
    def _option_defs(option_dimensions, relation_index, base_code, cache):
        signature = tuple((d.entity_id, tuple(str(v.id) for v in d.values)) for d in option_dimensions)
        if signature not in cache:
            cache[signature] = tuple(
                adapter.property_def(d, relation_index, base_code, order=1000 + index)
                for index, d in enumerate(option_dimensions)
            )
        return cache[signature]

    def _property_dimensions(
        self,
        snapshot: Snapshot,
        article_id: str | None,
        base_code: str,
    ) -> tuple[_Dimension, ...]:
        property_ids = self._article_property_ids(snapshot, article_id)
        if not property_ids:
            property_ids = {
                str(prop.id)
                for prop in snapshot.properties
                if prop.id is not None
            }

        restrictions = (getattr(snapshot, "art_base", {}) or {}).get(base_code, {})
        scheme_order = self._scheme_property_order(snapshot, article_id)
        dimensions: list[_Dimension] = []

        for prop in snapshot.properties:
            prop_id = str(prop.id or "")
            if not prop_id or prop_id not in property_ids:
                continue
            # CodeScheme controls encoding/order; it does not define the
            # configurable dimension set. Article -> Class -> Property is
            # authoritative for that.
            allowed_ids = {
                str(value_id)
                for value_id in restrictions.get(prop_id, [])
            }
            source_values = [
                value
                for value in prop.values
                if not allowed_ids or str(value.id) in allowed_ids
            ]
            source_values.sort(
                key=lambda value: (
                    value.display_order is None,
                    value.display_order or 0,
                    value.value or "",
                    str(value.id or ""),
                )
            )
            if not source_values:
                continue

            dimensions.append(
                _Dimension(
                    kind="property",
                    entity_id=prop_id,
                    name=prop.name or prop.code or prop_id,
                    display_order=(
                        int(prop.display_order)
                        if prop.display_order is not None
                        else 10**9
                    ),
                    values=tuple(source_values),
                )
            )

        if scheme_order:
            rank = {name: index for index, name in enumerate(scheme_order)}
            dimensions.sort(
                key=lambda item: (
                    rank.get(self._normalise_name(item.name), 10**6),
                    item.display_order,
                    item.name,
                )
            )
        else:
            dimensions.sort(
                key=lambda item: (
                    item.display_order,
                    item.name,
                    item.entity_id,
                )
            )

        return tuple(dimensions)

    # -- legacy single-parent hierarchy pruning ------------------------------
    #
    # No longer used by ``build()``: the engine evaluates the full relation
    # grammar (multi-parent, OR, NOT IN, three-valued logic). Retained because
    # tests/test_cancellation_workflow_surfaces.py exercises the cancellation
    # checkpoint inside ``_property_combinations``; removable once that test is
    # retargeted at the engine.

    @classmethod
    def _property_combinations(cls, dimensions, relation_objects):
        """Generate property combinations while applying simple hierarchy relations."""
        if not dimensions:
            return [()]
        constraints = cls._hierarchy_constraints(relation_objects)
        ordered = cls._order_dimensions_by_dependencies(dimensions, constraints)
        results = []
        def visit(index, selected, selected_by_name):
            checkpoint()
            if index >= len(ordered):
                results.append(tuple(selected)); return
            dimension = ordered[index]
            name = cls._normalise_name(dimension.name)
            for value in dimension.values:
                value_id = str(getattr(value, "id", ""))
                if not cls._value_satisfies_hierarchy(value_id, constraints, selected_by_name):
                    continue
                selected.append(value)
                selected_by_name[name] = str(getattr(value, "value", "") or "").upper()
                visit(index + 1, selected, selected_by_name)
                selected_by_name.pop(name, None); selected.pop()
        visit(0, [], {})
        index_by_id = {d.entity_id: i for i, d in enumerate(dimensions)}
        return [tuple(combo[index_by_id[d.entity_id]] for d in dimensions) for combo in results]

    @classmethod
    def _hierarchy_constraints(cls, relation_objects):
        constraints = {}
        for relation in relation_objects:
            domain = str(getattr(relation, "domain", "") or "")
            type_code = str(getattr(relation, "type_code", "") or "")
            value_id = str(getattr(relation, "value_id", "") or "")
            body = str(getattr(relation, "body", "") or "")
            if domain != "C" or type_code not in {"1", "2"} or not value_id:
                continue
            parsed = cls._single_parent_condition(body)
            if parsed is not None:
                parent, allowed = parsed
                constraints.setdefault(value_id, []).append((parent, frozenset(x.upper() for x in allowed)))
        return constraints

    @staticmethod
    def _single_parent_condition(body):
        text = body.split("Restrictions:", 1)[-1].strip()
        if not text or re.search(r"\bOR\b", text, re.IGNORECASE):
            return None
        specified = re.search(r"SPECIFIED\s+([A-Za-z0-9_]+)", text, re.IGNORECASE)
        value_match = re.search(r"([A-Za-z0-9_]+)\s+IN\s*\(\s*([^)]*)\)", text, re.IGNORECASE | re.DOTALL)
        if specified and value_match and specified.group(1).upper() == value_match.group(1).upper():
            values = [x.strip().strip("'").strip('"') for x in value_match.group(2).split(',') if x.strip()]
            return specified.group(1), values
        equality = re.fullmatch(r"\(?\s*([A-Za-z0-9_]+)\s*=\s*['\"]([^'\"]+)['\"]\s*\)?", text, re.IGNORECASE)
        return (equality.group(1), [equality.group(2)]) if equality else None

    @classmethod
    def _order_dimensions_by_dependencies(cls, dimensions, constraints):
        by_name = {cls._normalise_name(d.name): d for d in dimensions}
        dependencies = {}
        for dimension in dimensions:
            parents = set()
            for value in dimension.values:
                for parent, _allowed in constraints.get(str(getattr(value, "id", "")), ()):
                    parent = cls._normalise_name(parent)
                    if parent in by_name and parent != cls._normalise_name(dimension.name):
                        parents.add(parent)
            dependencies[cls._normalise_name(dimension.name)] = parents
        ordered, remaining, placed = [], list(dimensions), set()
        while remaining:
            progress = False
            for dimension in list(remaining):
                name = cls._normalise_name(dimension.name)
                if dependencies.get(name, set()).issubset(placed):
                    ordered.append(dimension); remaining.remove(dimension); placed.add(name); progress = True
            if not progress:
                ordered.extend(remaining); break
        return tuple(ordered)

    @classmethod
    def _value_satisfies_hierarchy(cls, value_id, constraints, selected_by_name):
        for parent, allowed in constraints.get(value_id, ()):
            selected = selected_by_name.get(cls._normalise_name(parent))
            if selected is not None and selected not in allowed:
                return False
        return True

    def _option_dimensions(
        self, snapshot: Snapshot, article, selected_property_ids: set[str], base_code: str
    ) -> tuple[_Dimension, ...]:
        product_id = str(article.product_id or "")
        offered_ids = {
            str(v) for v in (snapshot.product_option_value_ids or {}).get(product_id, [])
        }
        if not offered_ids:
            return ()

        attribute_seeds: set[str] = set()
        for value_id in selected_property_ids:
            attribute_seeds.update(
                str(v)
                for v in (snapshot.attribute_option_dependencies or {}).get(value_id, [])
            )

        # An option can be independently offered by the product or enabled by
        # another selected value.  Do not let one dependency edge (for example
        # FR -> FR_Option) hide an independent option such as Fabric_Colour.
        #
        # Values which are targets of option->option dependencies are children;
        # values with no incoming edge are root options and remain available.
        # From those roots, and from attribute-enabled seeds, walk the option
        # dependency graph so every reachable child is retained.
        option_dependencies = snapshot.option_option_dependencies or {}
        dependent_child_ids = {
            str(child)
            for children in option_dependencies.values()
            for child in children
        }
        root_ids = offered_ids - dependent_child_ids
        attribute_gated_ids = {
            str(child)
            for children in (snapshot.attribute_option_dependencies or {}).values()
            for child in children
        }
        independent_root_ids = root_ids - attribute_gated_ids
        candidate_ids = (
            independent_root_ids
            | attribute_seeds
        ) & offered_ids

        pending = list(candidate_ids)
        while pending:
            current = pending.pop()
            for child in option_dependencies.get(current, []):
                child = str(child)
                if child in offered_ids and child not in candidate_ids:
                    candidate_ids.add(child)
                    pending.append(child)
        restrictions = (snapshot.art_base or {}).get(base_code, {})
        dimensions: list[_Dimension] = []

        for option in snapshot.options:
            oid = str(option.id or "")
            allowed = {str(v) for v in restrictions.get(oid, [])}
            values = [
                v for v in option.values
                if str(v.id) in candidate_ids
                and (not allowed or str(v.id) in allowed)
            ]
            values.sort(
                key=lambda value: (
                    value.display_order is None,
                    value.display_order or 0,
                    value.value or "",
                    str(value.id or ""),
                )
            )
            if values:
                dimensions.append(
                    _Dimension(
                        kind="option",
                        entity_id=oid,
                        name=option.name or option.code or oid,
                        display_order=int(option.display_order or 10**9),
                        values=tuple(values),
                    )
                )

        dimensions.sort(key=lambda d: (d.display_order, d.name, d.entity_id))
        return tuple(dimensions)

    @classmethod
    def _scheme_id(cls, snapshot: Snapshot, article_id: str | None) -> str:
        return str((snapshot.article_code_scheme_ids or {}).get(str(article_id or "")) or "")

    @classmethod
    def _scheme(cls, snapshot: Snapshot, article_id: str | None) -> dict:
        sid = cls._scheme_id(snapshot, article_id)
        return (snapshot.code_schemes or {}).get(sid, {}) if sid else {}

    @staticmethod
    def _article_property_ids(snapshot: Snapshot, article_id: str | None) -> set[str]:
        article_key = str(article_id or "")
        property_ids: set[str] = set()

        # ArticleClass is the repository class definition, but PDM snapshots
        # can also carry article-specific attribute/value links.  Preserve
        # those links when present so a property such as Fabric_Colour is not
        # lost merely because it is not repeated on the generated class.
        links = (getattr(snapshot, "article_class_ids", {}) or {}).get(
            article_key, []
        )
        class_ids = {str(value) for value in links}
        for engineering_class in getattr(snapshot.engineering, "classes", []) or []:
            if str(engineering_class.id) not in class_ids:
                continue
            for assignment in engineering_class.properties:
                if assignment.property_id:
                    property_ids.add(str(assignment.property_id))

        article_value_ids = {
            str(value_id)
            for value_id in (getattr(snapshot, "article_property_value_ids", {}) or {}).get(
                article_key, []
            )
        }
        if article_value_ids:
            for value in getattr(snapshot, "property_values", []) or []:
                if str(value.id or "") in article_value_ids and value.property_id:
                    property_ids.add(str(value.property_id))

        return property_ids

    @classmethod
    def _scheme_property_order(
        cls, snapshot: Snapshot, article_id: str | None
    ) -> list[str]:
        scheme_id = (
            getattr(snapshot, "article_code_scheme_ids", {}) or {}
        ).get(str(article_id or ""))
        if not scheme_id:
            return []

        scheme = (getattr(snapshot, "code_schemes", {}) or {}).get(str(scheme_id), {})
        body = str(
            scheme.get("body")
            or scheme.get("Scheme")
            or scheme.get("scheme")
            or ""
        )
        if not body:
            return []

        # Current MK Workbench code-scheme rows use a compact body:
        # @,@,...,Class:Property Class:Property ...
        # The @ characters represent the base portion; the property tokens
        # define the deterministic variant-code property order.
        tokens = re.findall(r"([A-Za-z0-9_]+):([A-Za-z0-9_]+)", body)
        return [cls._normalise_name(prop) for _class_name, prop in tokens]

    @staticmethod
    def _normalise_name(value: str) -> str:
        return adapter.normalise_name(value)

    @staticmethod
    def _valid_art_base(
        snapshot: Snapshot,
        base_code: str,
        selected_ids: set[str],
        selected_property_ids: set[str] | None = None,
    ) -> bool:
        restrictions = (getattr(snapshot, "art_base", {}) or {}).get(base_code, {})
        if not restrictions:
            return True

        selected_property_ids = selected_property_ids or set()
        for property_id, allowed_values in restrictions.items():
            if selected_property_ids and str(property_id) not in selected_property_ids:
                continue
            allowed = {str(value_id) for value_id in allowed_values or ()}
            if allowed and not (selected_ids & allowed):
                return False
        return True

    @staticmethod
    def _valid_exclusions(snapshot: Snapshot, selected_ids: set[str]) -> bool:
        exclusions = getattr(snapshot, "attribute_value_exclusions", {}) or {}
        for value_id in selected_ids:
            if any(
                str(other) in selected_ids
                for other in exclusions.get(str(value_id), ())
            ):
                return False
        return True

    @staticmethod
    def _make_permutation(
        article,
        base_code: str,
        properties: tuple[ArticleConfigurationValue, ...],
        options: tuple[ArticleConfigurationValue, ...],
        variant_conditions: tuple[str, ...],
        final_article: str,
        variant_code: str,
        scheme_id: str,
        pricing_factors: tuple[tuple[str, float], ...] = (),
    ) -> ArticlePermutation:
        return ArticlePermutation(
            article_id=str(article.id or ""),
            product_id=str(article.product_id or ""),
            base_code=base_code,
            final_article=final_article,
            variant_code=variant_code,
            variant_condition=" ".join(variant_conditions),
            variant_conditions=variant_conditions,
            pricing_factors=pricing_factors,
            code_scheme_id=scheme_id,
            name=article.name or "",
            description=article.description or "",
            quantity=1,
            is_super_item=bool(getattr(article, "is_super_item", False)),
            properties=properties,
            options=options,
        )
