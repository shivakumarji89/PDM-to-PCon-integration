"""Engineering relation service.

Derives and maintains the snapshot's OCD relation objects (``tCOMd_RelObj`` +
``tCOMd_Relation``) to ONE canonical standard, applied identically to every
product (no per-product editorial variance). For the configuration domain it
authors, per property in display order:

  * an **Action** ``A_Code_<Prop>`` mapping each value to its order code
    (``Code<Prop> = '<code>' IF <Prop> = <value>``) - only when a value's code
    actually differs from the value (i.e. numeric/parametric properties), and
  * a **Precondition** ``B_<Prop>_<Value>`` ONLY for a value confined to a
    proper subset of the family's base articles - body ``$BAN IN (...)``. A
    generic value (present on every base article) is unrestricted and gets no
    relation.

Naming and body grammar are fixed by the standard: ``<Prop>`` is the property's
name in the shared underscore convention (:func:`text_block_name`), the suffix
and body operand are the value's configuration token, and ordering is
deterministic - so the same snapshot yields byte-identical output for any user.

Read/derive + edit only - no database writes.
"""
from __future__ import annotations

from collections import defaultdict

from models.property import Property
from models.relation_object import RelationObject
from models.snapshot import Snapshot
from services.base_service import BaseService
from services.engineering.engineering_text_service import text_block_name


def validate_relation_body(body: str) -> tuple[bool, str]:
    """Lightweight OCD_4 body sanity check used by the editor: balanced
    parentheses and quotes. Returns (ok, message); an empty body is valid."""
    text = body or ""
    if text.count("(") != text.count(")"):
        return False, "Unbalanced parentheses."
    if text.count("'") % 2 != 0:
        return False, "Unbalanced quotes."
    return True, ""


class EngineeringRelationService(BaseService):
    """Build and edit the active snapshot's relation objects."""

    def ensure_relation_objects(
        self, snapshot: Snapshot | None
    ) -> list[RelationObject]:
        """Return the snapshot's relation objects, deriving them once if empty so
        later edits survive refreshes."""
        if snapshot is None:
            return []
        if not snapshot.relation_objects:
            snapshot.relation_objects = self.build_relation_objects(snapshot)
        return snapshot.relation_objects

    def rebuild_relation_objects(
        self, snapshot: Snapshot | None
    ) -> list[RelationObject]:
        """Force a fresh derivation, discarding any prior objects (and edits)."""
        if snapshot is None:
            return []
        snapshot.relation_objects = self.build_relation_objects(snapshot)
        return snapshot.relation_objects

    def build_relation_objects(self, snapshot: Snapshot) -> list[RelationObject]:
        """Derive configuration-domain relation objects (code actions +
        value preconditions) to the canonical standard. Deterministic and
        de-duplicated: same snapshot -> identical output for any user."""
        relations: list[RelationObject] = []
        seen: set[str] = set()

        def add(rel: RelationObject) -> None:
            if rel.name and rel.name not in seen:
                seen.add(rel.name)
                relations.append(rel)

        decoded = self.context.engineering_class_service.resolve_config_codes(snapshot)
        classify, bodies = self._classify_and_bodies(snapshot, decoded)

        for prop in self._ordered_properties(snapshot):
            prop_name = text_block_name(prop.name)
            if not prop_name:
                continue
            prop_decoded = decoded.get(str(prop.id), {})
            values = self._ordered_values(prop.values)

            # Action: only value->code mappings where the code differs from the
            # value token (numeric/parametric properties; choice values ARE their
            # own code, so they need no action).
            action_lines: list[str] = []
            for value in values:
                token = self._config_token(value)
                code = ((value.code or "").strip() or prop_decoded.get(
                    str(value.id), ""
                )).replace("#", "")
                if code and code != token:
                    rhs = token if self._is_numeric(value) else f"'{token}'"
                    action_lines.append(
                        f"Code{prop_name} = '{code}' IF {prop_name} = {rhs}"
                    )
            if action_lines:
                add(RelationObject(
                    name=f"A_Code_{prop_name}",
                    type_code="3",
                    domain="C",
                    order=100,
                    body=",\r\n".join(action_lines),
                    property_id=str(prop.id or ""),
                ))

            self._add_value_preconditions(
                add, prop_name, str(prop.id or ""), values, classify, bodies,
            )

        # Option values carry the bulk of the configurable choice relations (e.g.
        # fabrics), authored identically to property value preconditions.
        for option in self._ordered_options(snapshot):
            option_name = text_block_name(option.name)
            if not option_name:
                continue
            self._add_value_preconditions(
                add, option_name, str(option.id or ""),
                self._ordered_values(option.values), classify, bodies,
            )

        return relations

    def _add_value_preconditions(
        self, add, attr_name, entity_id, values, classify, bodies,
    ) -> None:
        """Emit ``B_<Attr>_<Value>`` ONLY for a COMBINATION value (availability
        gated by a head/code property, not just the base) - the combined body is
        precomputed. Generic and pure base-scoped (ArtBase) values get no
        relation; display-text identity values are skipped."""
        for value in values:
            vid = str(value.id)
            if classify.get(vid) != "combination":
                continue
            token = self._config_token(value)
            body = bodies.get(vid)
            if not token or not body:
                continue
            add(RelationObject(
                name=f"B_{attr_name}_{token}",
                type_code="1",
                domain="C",
                order=100,
                body=body,
                property_id=entity_id,
                value_id=vid,
            ))

    @staticmethod
    def _head_property_ids(snapshot: Snapshot) -> set[str]:
        """Head/code (config) properties = those whose values carry no order code
        (positional in the base article code). Only these may gate a combination
        precondition."""
        return {
            str(p.id) for p in snapshot.properties
            if p.values and not any((v.code or "").strip() for v in p.values)
        }

    @staticmethod
    def _articles_by_base(base_by_article: dict[str, str]) -> dict[str, set]:
        result: dict[str, set] = defaultdict(set)
        for aid, base in base_by_article.items():
            result[base].add(aid)
        return result

    def _article_tokens(
        self, snapshot: Snapshot, decoded: dict
    ) -> dict[str, dict[str, str]]:
        """article id -> {attribute id -> config token}. Head values use the
        decoded position code, coded values their order code."""
        result: dict[str, dict[str, str]] = defaultdict(dict)
        for article_set in snapshot.article_sets:
            for attr in list(article_set.properties) + list(article_set.options):
                aid_attr = str(attr.id)
                dec = decoded.get(aid_attr, {})
                for value in attr.values:
                    token = self._config_token(value, dec.get(str(value.id), ""))
                    if not token:
                        continue
                    for aid in value.article_ids:
                        result[str(aid)][aid_attr] = token
        return result

    def _attr_names(self, snapshot: Snapshot) -> dict[str, str]:
        names: dict[str, str] = {}
        for prop in snapshot.properties:
            names[str(prop.id)] = text_block_name(prop.name)
        for option in snapshot.options:
            names[str(option.id)] = text_block_name(option.name)
        return names

    @staticmethod
    def _value_attr(snapshot: Snapshot) -> dict[str, str]:
        result: dict[str, str] = {}
        for article_set in snapshot.article_sets:
            for attr in list(article_set.properties) + list(article_set.options):
                for value in attr.values:
                    result[str(value.id)] = str(attr.id)
        return result

    def _classify_and_bodies(
        self, snapshot: Snapshot, decoded: dict
    ) -> tuple[dict[str, str], dict[str, str]]:
        """value id -> 'generic' | 'base' | 'combination', plus the combined body
        for combination values.
          generic     - on every article (unrestricted) -> no relation.
          base        - restricted by base only -> ArtBase.
          combination - gated by a head/code property -> relation.
        """
        base_by_article = self._base_by_article(snapshot)
        articles_by_base = self._articles_by_base(base_by_article)
        all_articles = set(base_by_article)
        head_ids = self._head_property_ids(snapshot)
        article_tokens = self._article_tokens(snapshot, decoded)
        attr_names = self._attr_names(snapshot)
        value_attr = self._value_attr(snapshot)
        carriers_by_value: dict[str, set] = defaultdict(set)
        for article_set in snapshot.article_sets:
            for attr in list(article_set.properties) + list(article_set.options):
                for value in attr.values:
                    for aid in value.article_ids:
                        if str(aid) in base_by_article:
                            carriers_by_value[str(value.id)].add(str(aid))
        classify: dict[str, str] = {}
        bodies: dict[str, str] = {}
        for vid, carriers in carriers_by_value.items():
            if carriers == all_articles:
                classify[vid] = "generic"
                continue
            aid_attr = value_attr.get(vid, "")
            if aid_attr not in head_ids:
                body = self._combination_body(
                    carriers, aid_attr, base_by_article, articles_by_base,
                    article_tokens, attr_names, head_ids,
                )
                if "(SPECIFIED" in body:
                    classify[vid] = "combination"
                    bodies[vid] = body
                    continue
            classify[vid] = "base"
        return classify, bodies

    def classify_values(self, snapshot: Snapshot | None) -> dict[str, str]:
        """value id -> 'generic' | 'base' | 'combination' (see rule). Used by the
        ArtBase service to skip combination values."""
        if snapshot is None:
            return {}
        decoded = self.context.engineering_class_service.resolve_config_codes(snapshot)
        return self._classify_and_bodies(snapshot, decoded)[0]

    def _combination_body(
        self, carriers, attr_id, base_by_article, articles_by_base,
        article_tokens, attr_names, head_ids,
    ) -> str:
        """OR of per-base branches. A base carried whole -> ``$BAN IN ('base')``;
        a base carried in part -> the HEAD-property conditions that select
        exactly its carriers plus the base gate. Conditions are verified; a base
        no head property can characterise falls back to the gate alone."""
        branches: list[str] = []
        for base in sorted({base_by_article[a] for a in carriers}):
            arts = articles_by_base[base]
            here = carriers & arts
            if here == arts:
                branches.append(f"$BAN IN ('{base}')")
                continue
            keep: dict[str, set] = {}
            for qid in head_ids:
                if qid == attr_id or not attr_names.get(qid):
                    continue
                cvals = {article_tokens.get(a, {}).get(qid) for a in here}
                cvals.discard(None)
                avals = {article_tokens.get(a, {}).get(qid) for a in arts}
                avals.discard(None)
                if cvals and cvals != avals:
                    keep[qid] = cvals
            selected = {
                a for a in arts
                if all(
                    article_tokens.get(a, {}).get(qid) in vals
                    for qid, vals in keep.items()
                )
            }
            if keep and selected == here:
                conds = []
                for qid in sorted(keep, key=lambda q: attr_names[q]):
                    qname = attr_names[qid]
                    vals = ", ".join(f"'{x}'" for x in sorted(keep[qid]))
                    conds.append(f"(SPECIFIED {qname}) AND ({qname} IN ({vals}))")
                branches.append(" AND ".join(conds + [f"$BAN IN ('{base}')"]))
            else:
                branches.append(f"$BAN IN ('{base}')")
        return " OR ".join(branches)

    @staticmethod
    def _ordered_properties(snapshot: Snapshot) -> list[Property]:
        """Properties in canonical order: display order, then name."""
        return sorted(
            snapshot.properties,
            key=lambda p: (p.display_order is None, p.display_order or 0, p.name or ""),
        )

    @staticmethod
    def _ordered_options(snapshot: Snapshot) -> list:
        """Options in canonical order: display order, then name."""
        return sorted(
            snapshot.options,
            key=lambda o: (o.display_order is None, o.display_order or 0, o.name or ""),
        )

    @staticmethod
    def _ordered_values(values: list) -> list:
        """Values in canonical order: display order, then value."""
        return sorted(
            values,
            key=lambda v: (v.display_order is None, v.display_order or 0, v.value or ""),
        )

    @staticmethod
    def _config_token(value, decoded_code: str = "") -> str:
        """The value's configuration token: the numeric value itself, else the
        order code, else the sliced/decoded code. Empty for pure display-text
        values (which are identity attributes, not configurable choices)."""
        text = (value.value or "").strip()
        if text.isdigit():
            return text
        code = (value.code or "").strip() or (decoded_code or "").strip()
        # '#' marks a deprecated non-standard fabric flag; drop only that char.
        return code.replace("#", "")

    @staticmethod
    def _is_numeric(value) -> bool:
        return (value.value or "").strip().isdigit()


    def _base_by_article(self, snapshot: Snapshot) -> dict[str, str]:
        """article id -> its BASE article number (the reduced code).

        Articles not yet reduced are OMITTED, so $BAN never contains a full
        article number - the MDB holds only base article numbers.
        """
        result: dict[str, str] = {}
        for family in snapshot.engineering.families:
            for member in family.members:
                base = (member.reduced_article or "").strip()
                if base:
                    result[str(member.article_id)] = base
        return result

    @staticmethod
    def _value_base_codes(
        snapshot: Snapshot, base_by_article: dict[str, str]
    ) -> dict[str, list[str]]:
        """value id -> sorted distinct base article numbers carrying that value,
        taken from the article-set co-occurrence."""
        result: dict[str, set[str]] = {}
        for article_set in snapshot.article_sets:
            for attribute in list(article_set.properties) + list(article_set.options):
                for value in attribute.values:
                    bucket = result.setdefault(str(value.id), set())
                    for aid in value.article_ids:
                        base = base_by_article.get(str(aid))
                        if base:
                            bucket.add(base)
        return {vid: sorted(bases) for vid, bases in result.items()}

    def related_value_ids(self, snapshot: Snapshot | None) -> set[str]:
        """Value ids that get a relation (COMBINATION values, gated by a head
        property). Generic and pure base-scoped (ArtBase) values are excluded -
        lets Class Creation blank the Relation cell for them."""
        if snapshot is None:
            return set()
        return {
            vid for vid, kind in self.classify_values(snapshot).items()
            if kind == "combination"
        }

    def set_body(self, relation: RelationObject | None, body: str) -> bool:
        """Set a relation object's logic body. Returns True on change."""
        if relation is None:
            return False
        relation.body = "" if body is None else body
        return True

    # -- manual curation (additive; does not affect the derivation) --------
    def add_relation(
        self,
        snapshot: Snapshot | None,
        name: str,
        type_code: str = "1",
        domain: str = "C",
        body: str = "",
    ) -> RelationObject | None:
        """Add a manual relation object. Returns it, or None if the snapshot is
        missing or the name is blank/already used."""
        if snapshot is None or not name:
            return None
        if any(r.name == name for r in snapshot.relation_objects):
            return None
        relation = RelationObject(
            name=name, type_code=type_code, domain=domain, order=100, body=body
        )
        snapshot.relation_objects.append(relation)
        return relation

    def remove_relation(
        self, snapshot: Snapshot | None, relation: RelationObject | None
    ) -> bool:
        """Remove a relation object from the snapshot. Returns True on removal."""
        if snapshot is None or relation is None:
            return False
        try:
            snapshot.relation_objects.remove(relation)
        except ValueError:
            return False
        return True

    def set_name(
        self,
        snapshot: Snapshot | None,
        relation: RelationObject | None,
        name: str,
    ) -> bool:
        """Rename a relation object. Returns True on change; rejects a blank or
        duplicate name."""
        if relation is None or not name or name == relation.name:
            return False
        others = snapshot.relation_objects if snapshot is not None else []
        if any(r is not relation and r.name == name for r in others):
            return False
        relation.name = name
        return True

    @staticmethod
    def set_type(relation: RelationObject | None, type_code: str) -> bool:
        """Set a relation object's type code. Returns True on change."""
        if relation is None or not type_code:
            return False
        relation.type_code = type_code
        return True

    @staticmethod
    def set_domain(relation: RelationObject | None, domain: str) -> bool:
        """Set a relation object's domain code. Returns True on change."""
        if relation is None or not domain:
            return False
        relation.domain = domain
        return True
