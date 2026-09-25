"""Engineering value combination table service (OCD 4.3 spec, section 2.21).

Builds an OCD *value combination table* over the family's configurable
properties: every loaded article is one valid combination, so the table's
logical lines are the DISTINCT value-combinations the article set actually
carries. A ``TABLE()`` constraint (relation type 4, domain C) then binds the
table to the article, enforcing configuration consistency.

The value combinations come only from the snapshot's own article set - no
external data. Derive/preview only; feeds the OCD ``<name>_tbl.csv`` export and
the relationship-knowledge ``TABLE()`` call.
"""
from __future__ import annotations

from collections import defaultdict

from models.property import Property
from models.relation_object import RelationObject
from models.snapshot import Snapshot
from models.value_table import ValueCombinationTable
from services.base_service import BaseService
from services.engineering.engineering_text_service import text_block_name


class EngineeringValueTableService(BaseService):
    """Build and edit the active snapshot's value combination tables."""

    def ensure_value_tables(
        self, snapshot: Snapshot | None
    ) -> list[ValueCombinationTable]:
        """Return the snapshot's value tables, building them once if empty, and
        keep a matching ``TABLE()`` constraint relation object for each."""
        if snapshot is None:
            return []
        if not snapshot.value_tables:
            snapshot.value_tables = self._build_all(snapshot)
        self._sync_constraint_relations(snapshot)
        return snapshot.value_tables

    def rebuild_value_tables(
        self, snapshot: Snapshot | None
    ) -> list[ValueCombinationTable]:
        """Force a fresh derivation (property config + fabric/finish tables) and
        refresh their constraint relation objects."""
        if snapshot is None:
            return []
        snapshot.value_tables = self._build_all(snapshot)
        self._sync_constraint_relations(snapshot)
        return snapshot.value_tables

    def _build_all(self, snapshot: Snapshot) -> list[ValueCombinationTable]:
        tables: list[ValueCombinationTable] = []
        prop_table = self.build_property_table(snapshot)
        if prop_table is not None and prop_table.lines:
            tables.append(prop_table)
        tables.extend(self.build_dependency_tables(snapshot))
        return tables

    def _sync_constraint_relations(self, snapshot: Snapshot) -> None:
        """Ensure one ``C_<table>`` constraint relation object (type 4, domain C)
        per value table, without disturbing other relations. Idempotent."""
        wanted = {
            f"C_{t.name.upper()}": self.constraint_body(t)
            for t in snapshot.value_tables
        }
        by_name = {r.name: r for r in snapshot.relation_objects}
        for name, body in wanted.items():
            existing = by_name.get(name)
            if existing is None:
                snapshot.relation_objects.append(RelationObject(
                    name=name, type_code="4", domain="C", order=100, body=body,
                ))
            else:
                existing.body = body

    def build_property_table(
        self, snapshot: Snapshot | None, name: str = "config"
    ) -> ValueCombinationTable | None:
        """Value combination table over the family's DISCRETE configurable
        properties: one distinct value-combination per logical line, scoped by
        the base article (``COL_BAN``).

        Per the OCD manual a combination table must be complete and is only
        useful for discrete properties, so parametric/continuous dimensions
        (all-numeric values, e.g. Width/Depth) are excluded. Every discrete
        property is a column (partial-coverage columns kept - absent on a row =
        undefined access); lines are the distinct real per-article combinations,
        ordered deterministically. Returns None if there is nothing to tabulate.
        """
        if snapshot is None or not snapshot.article_sets:
            return None
        decoded = self.context.engineering_class_service.resolve_config_codes(snapshot)
        parametric = self._parametric_property_ids(snapshot)
        base_by_article = self._base_by_article(snapshot)

        # article id -> {COL_id: token}; access + display order per column.
        per_article: dict[str, dict[str, str]] = defaultdict(dict)
        access: dict[str, str] = {}
        order_of: dict[str, tuple] = {}
        for prop in self._ordered_properties(snapshot):
            if str(prop.id) in parametric:
                continue
            prop_var = text_block_name(prop.name)
            if not prop_var:
                continue
            col = f"COL_{prop_var.upper()}"
            order_of.setdefault(col, (prop.display_order or 0, prop.name or ""))
            access.setdefault(col, f"x.{prop_var}")
        for article_set in snapshot.article_sets:
            for attr in article_set.properties:
                if str(attr.id) in parametric:
                    continue
                prop_var = text_block_name(attr.name)
                if not prop_var:
                    continue
                col = f"COL_{prop_var.upper()}"
                dec = decoded.get(str(attr.id), {})
                for value in attr.values:
                    token = self._config_token(value, dec.get(str(value.id), ""))
                    if not token:
                        continue
                    for aid in value.article_ids:
                        per_article[str(aid)][col] = token

        if not per_article:
            return None

        # Base scope column (COL_BAN = $BAN), first in order when present.
        for aid, base in base_by_article.items():
            if aid in per_article and base:
                per_article[aid]["COL_BAN"] = base
        if any("COL_BAN" in per_article[a] for a in per_article):
            access["COL_BAN"] = "$BAN"
            order_of["COL_BAN"] = (-1, "")

        # Keep only columns every article carries -> uniform, valid lines.
        # Every discrete column present on at least one article (COL_BAN first).
        # Keeping partial-coverage columns makes the attribute table COMPLETE;
        # a property absent on an article is simply omitted from that row (its
        # TABLE() access parameter is then undefined, per the OCD manual).
        columns = [
            col for col in sorted(order_of, key=lambda c: order_of[c])
            if any(col in per_article[a] for a in per_article)
        ]
        if not columns:
            return None

        # Distinct REAL per-article combinations - correlation between columns is
        # preserved (each line is an article that exists), so the table never
        # over-permits.
        seen: set[tuple] = set()
        rows: list[dict[str, str]] = []
        for aid in per_article:
            row = {c: per_article[aid][c] for c in columns if c in per_article[aid]}
            key = tuple(sorted(row.items()))
            if key in seen:
                continue
            seen.add(key)
            rows.append(row)
        rows.sort(key=lambda r: tuple(r.get(c, "") for c in columns))
        lines: list[dict[str, object]] = [dict(r) for r in rows]

        return ValueCombinationTable(
            name=name,
            article_class=self._article_class(snapshot),
            property_names=columns,
            access={c: access[c] for c in columns},
            lines=lines,
        )

    def build_dependency_tables(
        self, snapshot: Snapshot | None
    ) -> list[ValueCombinationTable]:
        """Fabric/finish value combination tables from the option dependency
        graph (``DependentOptionValues``): one table per PARENT option, with a
        logical row per parent value and a value SET per dependent (child)
        option - the compact form the OCD manual describes.

        This is the maintenance surface: a fabric/finish change in PDM changes
        the edges, so the tables regenerate. Returns one table per parent option
        that has dependents (chains yield one table per parent level).
        """
        if snapshot is None:
            return []
        edges = getattr(snapshot, "option_option_dependencies", None) or {}
        if not edges:
            return []
        opt_of_value = self._option_of_value(snapshot)
        opt_name = {str(o.id): text_block_name(o.name) for o in snapshot.options}
        value_token = self._value_tokens(snapshot)
        # Which option values each base article offers -> scopes finish rules by
        # base (COL_BAN). Empty until the family is reduced; then the tables omit
        # COL_BAN and apply family-wide.
        base_offered = self._offered_values_by_base(snapshot)
        use_base = bool(base_offered)

        # parent option -> base -> child option -> parent token -> set(child token)
        graph: dict[str, dict[str, dict[str, dict[str, set]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
        )
        for src, dsts in edges.items():
            po = opt_of_value.get(str(src))
            ptok = value_token.get(str(src))
            if not po or not ptok:
                continue
            for dst in dsts:
                co = opt_of_value.get(str(dst))
                ctok = value_token.get(str(dst))
                if not co or not ctok or co == po:
                    continue
                if use_base:
                    for base, offered in base_offered.items():
                        if str(src) in offered and str(dst) in offered:
                            graph[po][base][co][ptok].add(ctok)
                else:
                    graph[po][""][co][ptok].add(ctok)

        tables: list[ValueCombinationTable] = []
        for po in sorted(graph, key=lambda o: opt_name.get(o, o)):
            parent = opt_name.get(po) or ""
            per_base = graph[po]
            if not parent or not per_base:
                continue
            parent_col = f"COL_{parent.upper()}"
            child_opts = {
                co for base in per_base for co in per_base[base] if opt_name.get(co)
            }
            child_cols = {co: f"COL_{opt_name[co].upper()}" for co in child_opts}
            ordered_children = sorted(child_cols, key=lambda c: opt_name.get(c, c))
            columns = (["COL_BAN"] if use_base else []) + [parent_col] + [
                child_cols[co] for co in ordered_children
            ]
            access = {parent_col: f"x.{parent}"}
            if use_base:
                access["COL_BAN"] = "$BAN"
            for co in ordered_children:
                access[child_cols[co]] = f"x.{opt_name[co]}"

            # One logical row per (base, parent value); children carry value sets.
            lines: list[dict[str, object]] = []
            for base in sorted(per_base):
                children = per_base[base]
                parent_values = sorted(
                    {pv for co in children for pv in children[co]}
                )
                for pv in parent_values:
                    line: dict[str, object] = {}
                    if use_base:
                        line["COL_BAN"] = base
                    line[parent_col] = pv
                    for co in ordered_children:
                        cvs = sorted(children.get(co, {}).get(pv, set()))
                        if cvs:
                            line[child_cols[co]] = cvs if len(cvs) > 1 else cvs[0]
                    lines.append(line)

            tables.append(ValueCombinationTable(
                name=f"{parent.lower()}",
                article_class=self._article_class(snapshot),
                property_names=columns,
                access=access,
                lines=lines,
            ))
        return tables

    def _offered_values_by_base(self, snapshot: Snapshot) -> dict[str, set]:
        """base article -> the option value ids its products offer (from
        ``product_option_value_ids`` + each product's reduced base). Empty when
        the family is not yet reduced."""
        base_of_article = self._base_by_article(snapshot)
        base_of_product: dict[str, set] = defaultdict(set)
        for article in snapshot.articles:
            base = base_of_article.get(str(article.id))
            if base:
                base_of_product[str(getattr(article, "product_id", ""))].add(base)
        result: dict[str, set] = defaultdict(set)
        offered = getattr(snapshot, "product_option_value_ids", None) or {}
        for pid, vids in offered.items():
            for base in base_of_product.get(str(pid), ()):
                for vid in vids:
                    result[base].add(str(vid))
        return result

    @staticmethod
    def _option_of_value(snapshot: Snapshot) -> dict[str, str]:
        result: dict[str, str] = {}
        for option in snapshot.options:
            for value in option.values:
                result[str(value.id)] = str(option.id)
        return result

    def _value_tokens(self, snapshot: Snapshot) -> dict[str, str]:
        """option value id -> config token (order code, else value)."""
        result: dict[str, str] = {}
        for option in snapshot.options:
            for value in option.values:
                token = self._config_token(value)
                if token:
                    result[str(value.id)] = token
        return result

    @staticmethod
    def to_csv_rows(table: ValueCombinationTable | None) -> list[str]:
        """The OCD ``<name>_tbl.csv`` rows: ``LineNr;PROPERTYNAME;VALUE`` (a
        restrictable value set yields one row per value). Upper case, in column
        order, line numbers 1-based."""
        if table is None:
            return []
        rows: list[str] = []
        for line_nr, line in enumerate(table.lines, start=1):
            for pname in table.property_names:
                if pname not in line:
                    continue
                value = line[pname]
                values = value if isinstance(value, (list, tuple)) else [value]
                for token in values:
                    rows.append(f"{line_nr};{pname};{token}")
        return rows

    @staticmethod
    def constraint_body(table: ValueCombinationTable | None) -> str:
        """The OCD constraint that binds the table as a consistency check:
        ``Objects: x IS_A <class>. Restrictions: TABLE <name> ( COL = x.Prop,
        ... ).`` Each column maps to its access parameter (``x.Prop`` / ``$BAN``).
        """
        if table is None or not table.property_names:
            return ""
        params = ", ".join(
            f"{col} = {table.access.get(col, col)}" for col in table.property_names
        )
        cls = (table.article_class or "ARTICLE").strip()
        return (
            f"Objects:\r\n  x IS_A {cls}.\r\n"
            f"Restrictions:\r\n  TABLE {table.name.upper()} ( {params} )."
        )

    @staticmethod
    def _parametric_property_ids(snapshot: Snapshot) -> set[str]:
        """Property ids that are parametric/continuous dimensions (every value is
        numeric, e.g. Width 600/800). The OCD manual restricts combination tables
        to discrete properties, so these are excluded."""
        result: set[str] = set()
        for prop in snapshot.properties:
            texts = [(v.value or "").strip() for v in prop.values]
            texts = [t for t in texts if t]
            if texts and all(t.isdigit() for t in texts):
                result.add(str(prop.id))
        return result

    @staticmethod
    def _base_by_article(snapshot: Snapshot) -> dict[str, str]:
        """article id -> its BASE article number (reduced code); un-reduced
        articles omitted."""
        result: dict[str, str] = {}
        if snapshot.engineering is None:
            return result
        for family in snapshot.engineering.families:
            for member in family.members:
                base = (member.reduced_article or "").strip()
                if base:
                    result[str(member.article_id)] = base
        return result

    @staticmethod
    def _article_class(snapshot: Snapshot) -> str:
        """The property class the constraint binds to (``<Category>_Attribute``),
        mirroring the Class Creation page's class naming, sanitised to a valid
        OFML identifier (no spaces)."""
        product = getattr(snapshot, "product", None)
        label = ""
        if product is not None:
            label = (
                getattr(product, "category", "") or getattr(product, "range_name", "")
            ).strip()
        if not label and snapshot.metadata is not None:
            label = (snapshot.metadata.product_code or "").strip()
        safe = "".join(c if c.isalnum() else "_" for c in label).strip("_")
        while "__" in safe:
            safe = safe.replace("__", "_")
        return f"{safe or 'Class'}_Attribute"

    @staticmethod
    def _ordered_properties(snapshot: Snapshot) -> list[Property]:
        return sorted(
            snapshot.properties,
            key=lambda p: (p.display_order is None, p.display_order or 0, p.name or ""),
        )

    @staticmethod
    def _config_token(value, decoded_code: str = "") -> str:
        """The value's configuration token: numeric value itself, else order
        code, else the decoded/sliced code; empty for pure display-text values.
        Mirrors the relation service's token rule so both agree."""
        text = (value.value or "").strip()
        if text.isdigit():
            return text
        code = (value.code or "").strip() or (decoded_code or "").strip()
        return code.replace("#", "")
