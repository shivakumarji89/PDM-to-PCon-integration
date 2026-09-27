"""Generate Article OBX permutations from repository configuration data.

In the repository/MDB model an Article is a *base article*. A permutation is a
runtime configuration built from that base article's classes/properties,
property values, relations, ArtBase restrictions and code scheme. Existing
Article rows are therefore inputs (base identities), never generated variants.
"""
from __future__ import annotations

import itertools
import re
from dataclasses import dataclass

from models.snapshot import Snapshot
from services.article_obx.article_obx_models import (
    ArticleConfigurationValue,
    ArticlePermutation,
)
from services.base_service import BaseService


@dataclass(frozen=True)
class _Dimension:
    kind: str
    entity_id: str
    name: str
    display_order: int
    values: tuple[object, ...]

@dataclass(frozen=True)
class _EvaluatedConfiguration:
    properties: tuple[ArticleConfigurationValue, ...]
    options: tuple[ArticleConfigurationValue, ...]
    computed_codes: dict[str, str]
    variant_condition: str = ""


class ArticlePermutationService(BaseService):
    """Build valid final article numbers from a repository Snapshot."""

    def build(self, snapshot: Snapshot | None = None, *, reporter=None) -> list[ArticlePermutation]:
        snapshot = snapshot or self.context.repository_snapshot
        if snapshot is None:
            if reporter is not None:
                reporter.begin(1, title="Building Article Permutations")
                reporter.finish(True, "No repository snapshot is loaded")
            return []

        results: list[ArticlePermutation] = []
        seen: set[tuple[str, str]] = set()

        relation_objects = tuple(sorted(
            getattr(snapshot, "relation_objects", []) or [],
            key=lambda r: (int(getattr(r, "order", 100) or 100), getattr(r, "name", "") or ""),
        ))

        articles = sorted(
            snapshot.articles,
            key=lambda item: ((item.code or "").strip(), str(item.id or "")),
        )
        if reporter is not None:
            reporter.begin(len(articles) or 1, title="Building Article Permutations")

        for article in articles:
            base_code = (article.code or "").strip()
            if not base_code:
                if reporter is not None:
                    reporter.advance()
                continue

            if reporter is not None:
                reporter.advance(f"Building {base_code}")

            article_permutation_count = 0

            dimensions = self._property_dimensions(snapshot, article.id, base_code)
            products = self._property_combinations(dimensions, relation_objects)

            for selected in products:
                properties = self._materialize_values(dimensions, selected)
                property_ids = {v.value_id for v in properties}

                if not self._valid_art_base(snapshot, base_code, property_ids, {v.entity_id for v in properties}):
                    continue
                if not self._valid_exclusions(snapshot, property_ids):
                    continue

                option_dimensions = self._option_dimensions(
                    snapshot, article, property_ids, base_code
                )
                option_products = (
                    itertools.product(*(d.values for d in option_dimensions))
                    if option_dimensions else [()]
                )

                for selected_options in option_products:
                    try:
                        options = self._materialize_values(option_dimensions, selected_options)
                        all_ids = {v.value_id for v in (*properties, *options)}

                        if not self._valid_art_base(snapshot, base_code, all_ids, {v.entity_id for v in (*properties, *options)}):
                            continue
                        if not self._valid_exclusions(snapshot, all_ids):
                            continue

                        evaluated = self._evaluate_configuration(
                            snapshot, base_code, properties, options,
                            relation_objects=relation_objects,
                        )
                        if evaluated is None:
                            continue

                        encoded = self._encode_article(
                            snapshot, article.id, base_code, evaluated
                        )
                        if encoded is None:
                            continue

                        final_article, variant_code = encoded
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
                        seen.add(key)

                        results.append(
                            self._make_permutation(
                                article,
                                base_code,
                                evaluated,
                                final_article,
                                variant_code,
                                self._scheme_id(snapshot, article.id),
                            )
                        )
                        article_permutation_count += 1
                        if reporter is not None:
                            reporter.note(f"Building {base_code} — {article_permutation_count} permutations")
                    except Exception as error:  # noqa: BLE001 - one bad configuration must not abort the build
                        if reporter is not None:
                            reporter.log(
                                "error",
                                f"{base_code}: skipped an invalid configuration ({error})",
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
        if reporter is not None:
            reporter.finish(True, f"Generated {len(results)} permutations")
        return results

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

    @classmethod
    def _property_combinations(cls, dimensions, relation_objects):
        """Generate property combinations while applying simple hierarchy relations."""
        if not dimensions:
            return [()]
        constraints = cls._hierarchy_constraints(relation_objects)
        ordered = cls._order_dimensions_by_dependencies(dimensions, constraints)
        results = []
        def visit(index, selected, selected_by_name):
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
        candidate_ids = (root_ids | attribute_seeds) & offered_ids

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

    @classmethod
    def _scheme_body(cls, snapshot: Snapshot, article_id: str | None) -> str:
        scheme = cls._scheme(snapshot, article_id)
        return str(
            scheme.get("body")
            or scheme.get("Scheme")
            or scheme.get("scheme")
            or ""
        )

    @classmethod
    def _evaluate_configuration(
        cls,
        snapshot: Snapshot,
        base_code: str,
        properties: tuple[ArticleConfigurationValue, ...],
        options: tuple[ArticleConfigurationValue, ...],
        *,
        relation_objects=None,
    ) -> _EvaluatedConfiguration | None:
        values = (*properties, *options)
        selected_ids = {v.value_id for v in values}
        selected = {
            cls._normalise_name(v.name): (v.value or "").upper()
            for v in values
        }
        # Raw per-value tokens available to a computed-code expression (a
        # property/option's own code, or its display value when no code is
        # recorded). Distinct from `computed_codes`, which holds relation
        # *output* and is what encoding/self-reference actually consult.
        codes_by_name = {
            cls._normalise_name(v.name): (v.code or v.value or "")
            for v in values
        }
        computed_codes = {
            cls._normalise_name(v.name): v.code
            for v in values if v.code
        }
        varconds: list[str] = []

        relations = (
            relation_objects
            if relation_objects is not None
            else tuple(sorted(
                getattr(snapshot, "relation_objects", []) or [],
                key=lambda r: (int(getattr(r, "order", 100) or 100), getattr(r, "name", "") or ""),
            ))
        )
        for relation in relations:
            domain = str(getattr(relation, "domain", "") or "")
            type_code = str(getattr(relation, "type_code", "") or "")
            body = str(getattr(relation, "body", "") or "")

            if domain == "C" and type_code in {"1", "2"}:
                value_id = str(getattr(relation, "value_id", "") or "")
                if value_id in selected_ids and not cls._relation_body_matches(
                    body, base_code, selected
                ):
                    return None

            if domain == "C" and type_code == "4":
                if not cls._constraint_matches(snapshot, body, base_code, selected):
                    return None

            if type_code == "3":
                cls._apply_action_clauses(body, base_code, selected, codes_by_name, computed_codes)
                cls._extract_varconds(body, varconds)

            if domain == "P" and type_code == "3":
                cls._extract_varconds(body, varconds)

        return _EvaluatedConfiguration(
            properties=properties,
            options=options,
            computed_codes=computed_codes,
            variant_condition=" ".join(dict.fromkeys(x for x in varconds if x)),
        )

    # -- computed-code relation actions (OCD-evidenced grammar) -------------
    #
    # Real repository action bodies (docs/02_Domain/Article_Encoding/
    # Article_Encoding.md Finding 3c, sourced from a live HM OFML repository's
    # ocd_relation.csv) are a comma-separated list of assignment clauses:
    #
    #   <Target> = <expr> [IF <condition>], <Target> = <expr> [IF <condition>], ...
    #
    # evaluated strictly left to right, each later matching clause overwriting
    # the target's prior value (self-reference: "Code = Code + ... IF ...").
    # <expr> is '+'-concatenated terms: a quoted literal, SUBSTR(<expr>,s,l),
    # $BAN (the base article number), the target's own prior value, or another
    # property/option's code. <condition> reuses the same AND/OR/IN/SPECIFIED/
    # equality grammar already used for validity relations.

    @classmethod
    def _apply_action_clauses(cls, body, base_code, selected, codes_by_name, computed_codes) -> None:
        for clause in cls._split_top_level(body, ","):
            clause = clause.strip().rstrip(".").strip()
            if not clause:
                continue
            assignment = re.match(r"^([A-Za-z0-9_]+)\s*=\s*(.*)$", clause, re.DOTALL)
            if not assignment:
                continue
            target_name, rhs = assignment.groups()

            if_match = cls._find_unquoted(rhs, r"\bIF\b")
            if if_match:
                expr_text, condition_text = rhs[:if_match.start()], rhs[if_match.end():]
            else:
                expr_text, condition_text = rhs, ""

            if condition_text.strip() and not cls._relation_body_matches(
                condition_text, base_code, selected
            ):
                continue

            try:
                value = cls._eval_expr(
                    expr_text.strip(), base_code, target_name, codes_by_name, computed_codes
                )
            except (ValueError, IndexError, TypeError):
                # A clause this evaluator cannot safely interpret must not be
                # treated as if it produced a value; skip only that clause.
                continue
            computed_codes[cls._normalise_name(target_name)] = value

    @classmethod
    def _eval_expr(cls, expr_text, base_code, target_name, codes_by_name, computed_codes) -> str:
        terms = [t for t in cls._split_top_level(expr_text, "+") if t.strip()]
        if not terms:
            raise ValueError(f"empty expression: {expr_text!r}")
        return "".join(
            cls._eval_term(term.strip(), base_code, target_name, codes_by_name, computed_codes)
            for term in terms
        )

    @classmethod
    def _eval_term(cls, term, base_code, target_name, codes_by_name, computed_codes) -> str:
        literal = re.fullmatch(r"'([^']*)'", term)
        if literal:
            return literal.group(1)

        substr = re.fullmatch(r"SUBSTR\s*\((.*)\)", term, re.IGNORECASE | re.DOTALL)
        if substr:
            args = cls._split_top_level(substr.group(1), ",")
            if len(args) != 3:
                raise ValueError(f"SUBSTR expects 3 arguments: {term!r}")
            value = cls._eval_expr(args[0].strip(), base_code, target_name, codes_by_name, computed_codes)
            start = int(args[1].strip())
            length = int(args[2].strip())
            return value[start:start + length]

        if term.upper() == "$BAN":
            return base_code

        name = cls._normalise_name(term)
        if name == cls._normalise_name(target_name):
            return computed_codes.get(name, "")
        if name in computed_codes:
            return computed_codes[name]
        return codes_by_name.get(name, "")

    @staticmethod
    def _split_top_level(text: str, sep: str) -> list[str]:
        """Split ``text`` on ``sep`` at depth 0, ignoring separators inside
        single-quoted strings or parentheses (so ``SUBSTR($BAN,0,3)`` is one
        term, not three, when splitting an expression on commas)."""
        parts: list[str] = []
        current: list[str] = []
        depth = 0
        in_quote = False
        for ch in text:
            if ch == "'":
                in_quote = not in_quote
                current.append(ch)
                continue
            if not in_quote:
                if ch in "([":
                    depth += 1
                elif ch in ")]":
                    depth = max(0, depth - 1)
                elif ch == sep and depth == 0:
                    parts.append("".join(current))
                    current = []
                    continue
            current.append(ch)
        parts.append("".join(current))
        return parts

    @staticmethod
    def _find_unquoted(text: str, pattern: str):
        """First regex match of ``pattern`` that starts outside a single-quoted
        string (so a literal like ``'IF'`` never splits as the IF keyword)."""
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if text[:match.start()].count("'") % 2 == 0:
                return match
        return None

    @staticmethod
    def _extract_varconds(body, target) -> None:
        for match in re.finditer(r"\$VARCOND\s*=\s*'([^']*)'", body, re.IGNORECASE):
            target.append(match.group(1))

    @classmethod
    def _constraint_matches(cls, snapshot, body, base_code, selected) -> bool:
        match = re.search(
            r"TABLE\s+([A-Za-z0-9_]+)\s*\((.*?)\)",
            body, re.IGNORECASE | re.DOTALL
        )
        if match:
            return cls._table_constraint_matches(
                snapshot, match.group(1), match.group(2), base_code, selected
            )
        restrictions = body.split("Restrictions:", 1)[-1].strip()
        return True if restrictions == body else cls._relation_body_matches(
            restrictions, base_code, selected
        )

    @classmethod
    def _table_constraint_matches(
        cls, snapshot, table_name, arguments, base_code, selected
    ) -> bool:
        table = next(
            (
                t for t in (getattr(snapshot, "value_tables", []) or [])
                if str(t.name or "").upper() == table_name.upper()
            ),
            None,
        )
        if table is None:
            return True

        access = {}
        for parameter in arguments.split(","):
            if "=" in parameter:
                column, expression = parameter.split("=", 1)
                access[column.strip().upper()] = expression.strip()

        for line in table.lines:
            valid = True
            for column, expected in line.items():
                expression = access.get(str(column).upper())
                if expression is None:
                    continue
                if expression.upper() == "$BAN":
                    actual = base_code
                else:
                    prop = re.search(r"x\.([A-Za-z0-9_]+)", expression, re.IGNORECASE)
                    if not prop:
                        continue
                    actual = selected.get(prop.group(1).upper())
                allowed = expected if isinstance(expected, (list, tuple)) else [expected]
                if str(actual or "").upper() not in {str(v).upper() for v in allowed}:
                    valid = False
                    break
            if valid:
                return True
        return False

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
    def _truthy(value: str) -> bool:
        return str(value or "").strip().lower() in {"1", "true", "yes", "y"}

    @staticmethod
    def _normalise_name(value: str) -> str:
        return re.sub(r"[^A-Za-z0-9_]+", "_", value or "").strip("_").upper()

    @staticmethod
    def _materialize_values(
        dimensions: tuple[_Dimension, ...],
        selected_values: tuple[object, ...],
    ) -> tuple[ArticleConfigurationValue, ...]:
        values: list[ArticleConfigurationValue] = []
        for dimension, source in zip(dimensions, selected_values):
            values.append(
                ArticleConfigurationValue(
                    kind=dimension.kind,
                    entity_id=dimension.entity_id,
                    value_id=str(source.id),
                    name=dimension.name,
                    value=source.value or "",
                    code=(getattr(source, "code", "") or getattr(source, "supplier_code", "") or "").replace("#", ""),
                    display_order=dimension.display_order,
                )
            )
        return tuple(values)

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
    def _relation_body_matches(
        body: str,
        base_code: str,
        selected: dict[str, str],
    ) -> bool:
        restrictions = body.split("Restrictions:", 1)[-1].strip()
        if not restrictions:
            return True

        branches = re.split(r"\s+OR\s+", restrictions, flags=re.IGNORECASE)
        for branch in branches:
            terms = re.split(r"\s+AND\s+", branch, flags=re.IGNORECASE)
            if all(
                ArticlePermutationService._relation_term_matches(
                    term.strip(), base_code, selected
                )
                for term in terms
                if term.strip()
            ):
                return True
        return False

    @staticmethod
    def _relation_term_matches(
        term: str,
        base_code: str,
        selected: dict[str, str],
    ) -> bool:
        term = term.strip(" ()")

        ban = re.search(
            r"\$BAN\s+IN\s*\(\s*'([^']*)'",
            term,
            re.IGNORECASE,
        )
        if ban:
            return ban.group(1).upper() == base_code.upper()

        specified = re.search(
            r"SPECIFIED\s+([A-Z0-9_]+)",
            term,
            re.IGNORECASE,
        )
        if specified and specified.group(1).upper() not in selected:
            return False

        value_match = re.search(
            r"([A-Z0-9_]+)\s+IN\s*\((.*?)\)",
            term,
            re.IGNORECASE | re.DOTALL,
        )
        if value_match:
            name = value_match.group(1).upper()
            allowed = {
                item.strip().strip("'").upper()
                for item in value_match.group(2).split(",")
            }
            return selected.get(name) in allowed

        equality = re.search(
            r"^\s*([A-Za-z0-9_]+)\s*=\s*'([^']*)'",
            term,
            re.IGNORECASE,
        )
        if equality:
            return selected.get(equality.group(1).upper()) == equality.group(2).strip().upper()

        return True

    @classmethod
    def _encode_article(
        cls,
        snapshot: Snapshot,
        article_id: str | None,
        base_code: str,
        configuration: _EvaluatedConfiguration,
    ) -> tuple[str, str] | None:
        scheme = cls._scheme(snapshot, article_id)
        body = cls._scheme_body(snapshot, article_id)

        values = {
            cls._normalise_name(v.name): v
            for v in (*configuration.properties, *configuration.options)
        }
        codes = dict(configuration.computed_codes)

        if not body:
            lowered = {str(k).lower(): str(v) for k, v in scheme.items()}
            value_sep = lowered.get("valuesep", lowered.get("value_sep", ""))
            var_sep = lowered.get("varcodesep", lowered.get("var_code_sep", ""))

            parts = []
            for value in configuration.properties:
                token = codes.get(cls._normalise_name(value.name)) or value.code or value.value
                if cls._truthy(lowered.get("trim", "")):
                    token = str(token).strip()
                parts.append(token)

            variant = value_sep.join(parts)
            return base_code + var_sep + variant, variant

        # In a user-defined scheme '@' is a final-article placeholder for the
        # base article. It is NOT part of the variant code. Other segments
        # contribute to the variant portion and are rendered after/beside the
        # base according to the scheme.
        final_parts: list[str] = []
        variant_parts: list[str] = []
        has_base_placeholder = False
        recognised = False
        base_index = 0

        for segment in body.split(","):
            token = segment

            if token == "@":
                recognised = True
                has_base_placeholder = True
                if base_index < len(base_code):
                    final_parts.append(base_code[base_index])
                    base_index += 1
                continue

            ref = re.fullmatch(
                r"\s*([A-Za-z0-9_]+):([A-Za-z0-9_]+)\s*", token
            )
            if ref:
                recognised = True
                name = cls._normalise_name(ref.group(2))
                value = values.get(name)
                code = codes.get(name)
                # A scheme may reference a purely computed property (e.g. the
                # real Aeron `AERON_OPTIONS:Code`) that is never itself a
                # selected property/option — only a relation action produces
                # it. That is valid provided some relation actually did.
                if value is None and code is None:
                    return None
                encoded = code if code is not None else (value.code or value.value)
                final_parts.append(encoded)
                variant_parts.append(encoded)
                continue

            def replace_reference(match):
                nonlocal recognised
                recognised = True
                name = cls._normalise_name(match.group(2))
                value = values.get(name)
                code = codes.get(name)
                if value is None and code is None:
                    return ""
                return code if code is not None else (value.code or value.value)

            rendered = re.sub(
                r"([A-Za-z0-9_]+):([A-Za-z0-9_]+)",
                replace_reference,
                token,
            )
            final_parts.append(rendered)
            if rendered:
                variant_parts.append(rendered)

        if not recognised:
            return None

        final_article = "".join(final_parts)
        variant = "".join(variant_parts)

        if has_base_placeholder:
            # The user-defined scheme explicitly emitted the base characters
            # through '@'. VarCodeSep is a predefined-scheme field and must
            # not be added to a user-defined scheme.
            return final_article, variant

        # No '@' means the user-defined body describes only the variant part.
        return base_code + final_article, variant


    @staticmethod
    def _make_permutation(
        article,
        base_code: str,
        configuration: _EvaluatedConfiguration,
        final_article: str,
        variant_code: str,
        scheme_id: str,
    ) -> ArticlePermutation:
        return ArticlePermutation(
            article_id=str(article.id or ""),
            product_id=str(article.product_id or ""),
            base_code=base_code,
            final_article=final_article,
            variant_code=variant_code,
            variant_condition=configuration.variant_condition,
            code_scheme_id=scheme_id,
            name=article.name or "",
            description=article.description or "",
            quantity=1,
            is_super_item=bool(getattr(article, "is_super_item", False)),
            properties=configuration.properties,
            options=configuration.options,
        )
