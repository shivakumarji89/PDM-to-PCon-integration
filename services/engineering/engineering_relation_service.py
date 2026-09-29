"""Engineering relation service.

Preserves imported OCD relations and derives configuration-domain
``A_Code_<Prop>`` encoding actions. Article coverage is used only for
generic/base ArtBase classification; it is not evidence for a validity
precondition. A validity relation is retained only when it already exists as
an explicitly authored, target-bound OCD Relation Object.

Read/derive + edit only - no database writes.
"""
from __future__ import annotations

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
        """Refresh derived actions while retaining imported OCD relations."""
        if snapshot is None:
            return []
        snapshot.relation_objects = self.build_relation_objects(snapshot)
        return snapshot.relation_objects

    def build_relation_objects(self, snapshot: Snapshot) -> list[RelationObject]:
        """Retain imported relations and derive independent code actions."""
        relations = [
            relation for relation in (snapshot.relation_objects or [])
            if getattr(relation, "rel_obj_id", "") or getattr(relation, "relation_id", "")
        ]
        seen = {relation.name for relation in relations if relation.name}

        def add(rel: RelationObject) -> None:
            if rel.name and rel.name not in seen:
                seen.add(rel.name)
                relations.append(rel)

        decoded = self.context.engineering_class_service.resolve_config_codes(snapshot)

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

            # Property-level com_RelObjID is owned by the property relation,
            # not by a value-level precondition.  In the canonical model this is
            # the action relation (A_Code_<Property>).  B_<Property>_<Value>
            # relations are bound through tCOMd_PropValue instead.
            relation_name = next(
                (
                    relation.name
                    for relation in relations
                    if str(getattr(relation, "property_id", "")) == str(prop.id or "")
                    and not str(getattr(relation, "value_id", "") or "")
                    and str(getattr(relation, "type_code", "")) == "3"
                ),
                "",
            )
            if relation_name:
                for cls in getattr(snapshot.engineering, "classes", []) or []:
                    for assignment in getattr(cls, "properties", []) or []:
                        if str(getattr(assignment, "property_id", "")) == str(prop.id or ""):
                            assignment.relation_object = relation_name

        # Option values carry the bulk of the configurable choice relations (e.g.
        # fabrics), authored identically to property value preconditions.
        for option in self._ordered_options(snapshot):
            option_name = text_block_name(option.name)
            if not option_name:
                continue

        return relations

    def _classify_article_coverage(self, snapshot: Snapshot) -> dict[str, str]:
        """Classify coverage for ArtBase only; never infer a dependency from it."""
        base_by_article = self._base_by_article(snapshot)
        all_articles = set(base_by_article)
        carriers_by_value: dict[str, set[str]] = {}
        for article_set in snapshot.article_sets:
            for attr in list(article_set.properties) + list(article_set.options):
                for value in attr.values:
                    carriers = carriers_by_value.setdefault(str(value.id), set())
                    for aid in value.article_ids:
                        if str(aid) in base_by_article:
                            carriers.add(str(aid))
        classify: dict[str, str] = {}
        for vid, carriers in carriers_by_value.items():
            classify[vid] = "generic" if carriers == all_articles else "base"
        return classify

    def classify_values(self, snapshot: Snapshot | None) -> dict[str, str]:
        """Return coverage classes used only to derive ArtBase restrictions."""
        if snapshot is None:
            return {}
        return self._classify_article_coverage(snapshot)

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
        """Value ids explicitly bound to configuration precondition relations."""
        if snapshot is None:
            return set()
        values: set[str] = set()
        for relation in snapshot.relation_objects:
            if str(getattr(relation, "domain", "")) != "C":
                continue
            if str(getattr(relation, "type_code", "")) != "1":
                continue
            values.update(
                str(value_id)
                for value_id in (getattr(relation, "value_ids", []) or [])
                if str(value_id)
            )
            value_id = str(getattr(relation, "value_id", "") or "")
            if value_id:
                values.add(value_id)
        return values

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
