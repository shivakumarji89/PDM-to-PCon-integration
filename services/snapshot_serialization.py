"""Snapshot serialization.

Pure, dependency-free conversion between the in-memory :class:`~models.snapshot.
Snapshot` object graph and plain JSON-compatible dictionaries. This is the
foundation of Engineering JSON persistence: it lets a fully loaded,
engineering-enriched Snapshot be written to and restored from disk with no PDM
access whatsoever.

Design notes:
  * **Pure functions only** - the domain models stay "fields only" (no methods),
    so all serialization knowledge lives here.
  * Every collection is serialized **by value**. Identity between the flat
    Snapshot indexes (``articles`` / ``options`` / ...) and the product object
    graph is intentionally not preserved, because the Engineering layer
    references source articles by ``article_id`` *string*, never by object
    identity - so a value round-trip is sufficient for correctness.
  * Enums are stored by their ``.value`` and restored **defensively**: an
    unknown value falls back to a safe default instead of raising.
  * ``*_from_dict`` tolerates missing keys, so documents written by an earlier
    version keep loading.
"""
from __future__ import annotations

from typing import Any

from core.enums import SnapshotStatus
from models.article import Article
from models.article_set import ArticleSet, SetAttribute, SetValue
from models.engineering import Engineering
from models.engineering_class import (
    ClassPropertyAssignment,
    ClassValue,
    EngineeringClass,
)
from models.engineering_family import EngineeringFamily
from models.engineering_relationships import EngineeringRelationships
from models.member_article import MemberArticle
from models.option import Option
from models.option_value import OptionValue
from models.price_list import PriceList
from models.price_record import PriceRecord
from models.product import Product
from models.property import Property
from models.property_assignment import PropertyAssignment
from models.property_definition import PropertyDataType, PropertyDefinition
from models.property_value import PropertyValue
from models.product_profile import ProductProfile, VariantGroup
from models.snapshot import Snapshot, SnapshotMetadata
from models.text_block import TextBlock
from models.relation_object import RelationObject
from models.value_table import ValueCombinationTable


# -- enum helpers ---------------------------------------------------------

def _snapshot_status_from(value: Any) -> SnapshotStatus:
    """Restore a :class:`SnapshotStatus`, defaulting to ``READY`` if unknown."""
    try:
        return SnapshotStatus(value)
    except ValueError:
        return SnapshotStatus.READY


def _property_data_type_from(value: Any) -> PropertyDataType:
    """Restore a :class:`PropertyDataType`, defaulting to ``TEXT`` if unknown."""
    try:
        return PropertyDataType(value)
    except ValueError:
        return PropertyDataType.TEXT


# -- source leaf records --------------------------------------------------

def property_value_to_dict(value: PropertyValue) -> dict[str, Any]:
    return {
        "id": value.id,
        "property_id": value.property_id,
        "value": value.value,
        "code": value.code,
        "model_suffix": value.model_suffix,
        "display_order": value.display_order,
        "selected": value.selected,
    }


def property_value_from_dict(data: dict[str, Any]) -> PropertyValue:
    return PropertyValue(
        id=data.get("id"),
        property_id=data.get("property_id"),
        value=data.get("value", ""),
        code=data.get("code", ""),
        model_suffix=data.get("model_suffix", ""),
        display_order=data.get("display_order"),
        selected=bool(data.get("selected", False)),
    )


def option_value_to_dict(value: OptionValue) -> dict[str, Any]:
    return {
        "id": value.id,
        "option_id": value.option_id,
        "value": value.value,
        "code": value.code,
        "supplier_code": value.supplier_code,
        "display_order": value.display_order,
        "selected": value.selected,
    }


def option_value_from_dict(data: dict[str, Any]) -> OptionValue:
    return OptionValue(
        id=data.get("id"),
        option_id=data.get("option_id"),
        value=data.get("value", ""),
        code=data.get("code", ""),
        supplier_code=data.get("supplier_code", ""),
        display_order=data.get("display_order"),
        selected=bool(data.get("selected", False)),
    )


# -- source mid-level records ---------------------------------------------

def property_to_dict(prop: Property) -> dict[str, Any]:
    return {
        "id": prop.id,
        "code": prop.code,
        "name": prop.name,
        "data_type": prop.data_type,
        "display_order": prop.display_order,
        "attribute_type": prop.attribute_type,
        "has_dependent_options": prop.has_dependent_options,
        "code_width": prop.code_width,
        "selected": prop.selected,
        "values": [property_value_to_dict(v) for v in prop.values],
    }


def property_from_dict(data: dict[str, Any]) -> Property:
    return Property(
        id=data.get("id"),
        code=data.get("code", ""),
        name=data.get("name", ""),
        data_type=data.get("data_type", ""),
        display_order=data.get("display_order"),
        attribute_type=data.get("attribute_type"),
        has_dependent_options=bool(data.get("has_dependent_options", False)),
        code_width=int(data.get("code_width", 0) or 0),
        selected=bool(data.get("selected", False)),
        values=[property_value_from_dict(v) for v in data.get("values", [])],
    )


def option_to_dict(option: Option) -> dict[str, Any]:
    return {
        "id": option.id,
        "code": option.code,
        "name": option.name,
        "display_order": option.display_order,
        "is_fabric": option.is_fabric,
        "selected": option.selected,
        "values": [option_value_to_dict(v) for v in option.values],
    }


def option_from_dict(data: dict[str, Any]) -> Option:
    return Option(
        id=data.get("id"),
        code=data.get("code", ""),
        name=data.get("name", ""),
        display_order=data.get("display_order"),
        is_fabric=bool(data.get("is_fabric", False)),
        selected=bool(data.get("selected", False)),
        values=[option_value_from_dict(v) for v in data.get("values", [])],
    )


def article_to_dict(article: Article) -> dict[str, Any]:
    return {
        "id": article.id,
        "product_id": article.product_id,
        "code": article.code,
        "name": article.name,
        "quantity": article.quantity,
        "description": article.description,
        "status": article.status,
        "source": article.source,
        "notes": article.notes,
        "is_super_item": article.is_super_item,
        "weight_kg": article.weight_kg,
        "volume_l": article.volume_l,
        "height": article.height,
        "width": article.width,
        "depth": article.depth,
        "selected": article.selected,
        "properties": [property_to_dict(p) for p in article.properties],
    }


def article_from_dict(data: dict[str, Any]) -> Article:
    return Article(
        id=data.get("id"),
        product_id=data.get("product_id"),
        code=data.get("code", ""),
        name=data.get("name", ""),
        quantity=data.get("quantity", 0),
        description=data.get("description", ""),
        status=data.get("status", ""),
        source=data.get("source", ""),
        notes=data.get("notes", ""),
        is_super_item=bool(data.get("is_super_item", False)),
        weight_kg=data.get("weight_kg"),
        volume_l=data.get("volume_l"),
        height=data.get("height"),
        width=data.get("width"),
        depth=data.get("depth"),
        selected=bool(data.get("selected", False)),
        properties=[property_from_dict(p) for p in data.get("properties", [])],
    )


def _exclusion_delta_to_dict(snapshot, base: dict[str, Any]) -> dict[str, Any]:
    """Serialize only the EXCLUDED slice of the held baseline (the parts pruned
    from the working snapshot), so a project file stays lean - the kept data is
    already serialized once as the working snapshot. The full baseline is
    reconstructed on load as ``working + this delta``.
    """
    work_articles = {str(a.id) for a in snapshot.articles}
    work_pvs = {str(v.id) for v in snapshot.property_values}
    work_props = {str(p.id) for p in snapshot.properties}
    work_ovs = {str(v.id) for v in snapshot.option_values}
    work_opts = {str(o.id) for o in snapshot.options}

    # Fully-excluded properties/options carry their full values; the excluded
    # values of PARTIALLY-excluded (still-kept) props ride in property_values.
    props = []
    for p in base.get("properties", []):
        if str(p.id) not in work_props:
            d = property_to_dict(p)
            d["values"] = [
                property_value_to_dict(v)
                for v in base.get("prop_values", {}).get(str(p.id), [])
            ]
            props.append(d)
    opts = []
    for o in base.get("options", []):
        if str(o.id) not in work_opts:
            d = option_to_dict(o)
            d["values"] = [
                option_value_to_dict(v)
                for v in base.get("opt_values", {}).get(str(o.id), [])
            ]
            opts.append(d)

    def _excl_map(name: str, work: dict) -> dict:
        return {k: v for k, v in base.get(name, {}).items() if k not in work}

    return {
        "articles": [
            article_to_dict(a) for a in base.get("articles", [])
            if str(a.id) not in work_articles
        ],
        "property_values": [
            property_value_to_dict(v) for v in base.get("property_values", [])
            if str(v.id) not in work_pvs
        ],
        "properties": props,
        "option_values": [
            option_value_to_dict(v) for v in base.get("option_values", [])
            if str(v.id) not in work_ovs
        ],
        "options": opts,
        "product_property_value_ids": _excl_map(
            "product_property_value_ids", snapshot.product_property_value_ids),
        "product_option_value_ids": _excl_map(
            "product_option_value_ids", snapshot.product_option_value_ids),
        "product_range": _excl_map("product_range", snapshot.product_range or {}),
        "article_property_value_ids": _excl_map(
            "article_property_value_ids", snapshot.article_property_value_ids),
        "article_varcond_terms": _excl_map(
            "article_varcond_terms", snapshot.article_varcond_terms),
        "article_components": _excl_map(
            "article_components", snapshot.article_components),
        "article_prefix_length": _excl_map(
            "article_prefix_length", snapshot.article_prefix_length),
        "attribute_range": _excl_map("attribute_range", snapshot.attribute_range),
        "value_range": _excl_map("value_range", snapshot.value_range),
    }


def _reconstruct_exclusion_baseline(snap, delta: dict[str, Any]) -> dict[str, Any]:
    """Rebuild the full held baseline from the working snapshot + the excluded
    delta, so unticking a range still restores it after a project reload."""
    excl_props = [property_from_dict(p) for p in delta.get("properties", [])]
    excl_opts = [option_from_dict(o) for o in delta.get("options", [])]
    excl_articles = [article_from_dict(a) for a in delta.get("articles", [])]
    excl_pvs = [
        property_value_from_dict(v) for v in delta.get("property_values", [])
    ]
    excl_ovs = [
        option_value_from_dict(v) for v in delta.get("option_values", [])
    ]

    # Excluded values of partially-excluded props/options, re-attached by parent.
    pv_by_prop: dict[str, list] = {}
    for v in excl_pvs:
        pv_by_prop.setdefault(str(v.property_id), []).append(v)
    ov_by_opt: dict[str, list] = {}
    for v in excl_ovs:
        ov_by_opt.setdefault(str(v.option_id), []).append(v)

    def _sorted(values):
        return sorted(
            values, key=lambda v: (v.display_order is None, v.display_order or 0)
        )

    prop_values = {
        str(p.id): _sorted(list(p.values) + pv_by_prop.get(str(p.id), []))
        for p in snap.properties
    }
    for p in excl_props:
        prop_values[str(p.id)] = list(p.values)
    opt_values = {
        str(o.id): _sorted(list(o.values) + ov_by_opt.get(str(o.id), []))
        for o in snap.options
    }
    for o in excl_opts:
        opt_values[str(o.id)] = list(o.values)

    def _merge(work: dict, name: str) -> dict:
        return {**dict(work), **(delta.get(name) or {})}

    return {
        "articles": list(snap.articles) + excl_articles,
        "properties": list(snap.properties) + excl_props,
        "prop_values": prop_values,
        "property_values": list(snap.property_values) + excl_pvs,
        "options": list(snap.options) + excl_opts,
        "opt_values": opt_values,
        "option_values": list(snap.option_values) + excl_ovs,
        "product_property_value_ids": _merge(
            snap.product_property_value_ids, "product_property_value_ids"),
        "product_option_value_ids": _merge(
            snap.product_option_value_ids, "product_option_value_ids"),
        "product_range": _merge(snap.product_range, "product_range"),
        "article_property_value_ids": _merge(
            snap.article_property_value_ids, "article_property_value_ids"),
        "article_varcond_terms": _merge(
            snap.article_varcond_terms, "article_varcond_terms"),
        "article_components": _merge(
            snap.article_components, "article_components"),
        "article_prefix_length": _merge(
            snap.article_prefix_length, "article_prefix_length"),
        "attribute_range": _merge(snap.attribute_range, "attribute_range"),
        "value_range": _merge(snap.value_range, "value_range"),
    }


def product_to_dict(product: Product) -> dict[str, Any]:
    return {
        "id": product.id,
        "code": product.code,
        "name": product.name,
        "description": product.description,
        "category": product.category,
        "catalogue_id": product.catalogue_id,
        "range_name": product.range_name,
        "status": product.status,
        "is_super_product": product.is_super_product,
        "new_product": product.new_product,
        "articles": [article_to_dict(a) for a in product.articles],
        "options": [option_to_dict(o) for o in product.options],
    }


def product_from_dict(data: dict[str, Any]) -> Product:
    return Product(
        id=data.get("id"),
        code=data.get("code", ""),
        name=data.get("name", ""),
        description=data.get("description", ""),
        category=data.get("category", ""),
        catalogue_id=data.get("catalogue_id"),
        range_name=data.get("range_name", ""),
        status=data.get("status", ""),
        is_super_product=bool(data.get("is_super_product", False)),
        new_product=bool(data.get("new_product", False)),
        articles=[article_from_dict(a) for a in data.get("articles", [])],
        options=[option_from_dict(o) for o in data.get("options", [])],
    )


# -- engineering records --------------------------------------------------

def property_assignment_to_dict(assignment: PropertyAssignment) -> dict[str, Any]:
    return {
        "property_id": assignment.property_id,
        "value": assignment.value,
    }


def property_assignment_from_dict(data: dict[str, Any]) -> PropertyAssignment:
    return PropertyAssignment(
        property_id=data.get("property_id", ""),
        value=data.get("value", ""),
    )


def property_definition_to_dict(definition: PropertyDefinition) -> dict[str, Any]:
    return {
        "id": definition.id,
        "name": definition.name,
        "order": definition.order,
        "data_type": definition.data_type.value,
    }


def property_definition_from_dict(data: dict[str, Any]) -> PropertyDefinition:
    return PropertyDefinition(
        id=data.get("id", ""),
        name=data.get("name", ""),
        order=data.get("order", 0),
        data_type=_property_data_type_from(data.get("data_type")),
    )


def member_article_to_dict(member: MemberArticle) -> dict[str, Any]:
    return {
        "id": member.id,
        "article_id": member.article_id,
        "family_id": member.family_id,
        "reduced_article": member.reduced_article,
        "short_description": member.short_description,
        "long_description": member.long_description,
        "relation_object": member.relation_object,
        "code_scheme": member.code_scheme,
        "property_values": [
            property_assignment_to_dict(a) for a in member.property_values
        ],
    }


def member_article_from_dict(data: dict[str, Any]) -> MemberArticle:
    return MemberArticle(
        id=data.get("id", ""),
        article_id=data.get("article_id", ""),
        family_id=data.get("family_id", ""),
        reduced_article=data.get("reduced_article", ""),
        short_description=data.get("short_description", ""),
        long_description=data.get("long_description", ""),
        relation_object=data.get("relation_object", ""),
        code_scheme=data.get("code_scheme", ""),
        property_values=[
            property_assignment_from_dict(a)
            for a in data.get("property_values", [])
        ],
    )


def engineering_family_to_dict(family: EngineeringFamily) -> dict[str, Any]:
    return {
        "id": family.id,
        "name": family.name,
        "members": [member_article_to_dict(m) for m in family.members],
    }


def engineering_family_from_dict(data: dict[str, Any]) -> EngineeringFamily:
    return EngineeringFamily(
        id=data.get("id", ""),
        name=data.get("name", ""),
        members=[member_article_from_dict(m) for m in data.get("members", [])],
    )


def engineering_relationships_to_dict(
    relationships: EngineeringRelationships,
) -> dict[str, Any]:
    return {
        "article_to_properties": {
            article_id: list(property_ids)
            for article_id, property_ids in relationships.article_to_properties.items()
        },
        "property_to_values": {
            property_id: list(values)
            for property_id, values in relationships.property_to_values.items()
        },
        "article_property_values": {
            article_id: dict(values)
            for article_id, values in relationships.article_property_values.items()
        },
    }


def engineering_relationships_from_dict(
    data: dict[str, Any],
) -> EngineeringRelationships:
    return EngineeringRelationships(
        article_to_properties={
            str(article_id): [str(p) for p in property_ids]
            for article_id, property_ids in data.get(
                "article_to_properties", {}
            ).items()
        },
        property_to_values={
            str(property_id): [str(v) for v in values]
            for property_id, values in data.get("property_to_values", {}).items()
        },
        article_property_values={
            str(article_id): {str(p): str(v) for p, v in values.items()}
            for article_id, values in data.get(
                "article_property_values", {}
            ).items()
        },
    )


def class_property_assignment_to_dict(
    assignment: ClassPropertyAssignment,
) -> dict[str, Any]:
    return {
        "property_id": assignment.property_id,
        "property_name": assignment.property_name,
        "width": assignment.width,
        "type": assignment.type,
        "usage": assignment.usage,
        "text_block": assignment.text_block,
        "values": [class_value_to_dict(v) for v in assignment.values],
    }


def class_property_assignment_from_dict(
    data: dict[str, Any],
) -> ClassPropertyAssignment:
    return ClassPropertyAssignment(
        property_id=data.get("property_id", ""),
        property_name=data.get("property_name", ""),
        width=int(data.get("width", 0) or 0),
        type=data.get("type", ""),
        usage=data.get("usage", ""),
        text_block=data.get("text_block", ""),
        values=[
            class_value_from_dict(v) for v in data.get("values", [])
        ],
    )


def class_value_to_dict(value: ClassValue) -> dict[str, Any]:
    return {"code": value.code, "value": value.value, "source": value.source}


def class_value_from_dict(data: dict[str, Any]) -> ClassValue:
    return ClassValue(
        code=data.get("code", ""),
        value=data.get("value", ""),
        source=data.get("source", "pdm"),
    )


def engineering_class_to_dict(cls: EngineeringClass) -> dict[str, Any]:
    return {
        "id": cls.id,
        "name": cls.name,
        "properties": [
            class_property_assignment_to_dict(a) for a in cls.properties
        ],
    }


def engineering_class_from_dict(data: dict[str, Any]) -> EngineeringClass:
    return EngineeringClass(
        id=data.get("id", ""),
        name=data.get("name", ""),
        properties=[
            class_property_assignment_from_dict(a)
            for a in data.get("properties", [])
        ],
    )


def engineering_to_dict(engineering: Engineering) -> dict[str, Any]:
    return {
        "families": [
            engineering_family_to_dict(f) for f in engineering.families
        ],
        "properties": [
            property_definition_to_dict(p) for p in engineering.properties
        ],
        "classes": [
            engineering_class_to_dict(c) for c in engineering.classes
        ],
        "relationships": engineering_relationships_to_dict(
            engineering.relationships
        ),
    }


def engineering_from_dict(data: dict[str, Any]) -> Engineering:
    relationships_data = data.get("relationships")
    return Engineering(
        families=[
            engineering_family_from_dict(f) for f in data.get("families", [])
        ],
        properties=[
            property_definition_from_dict(p) for p in data.get("properties", [])
        ],
        classes=[
            engineering_class_from_dict(c) for c in data.get("classes", [])
        ],
        relationships=(
            engineering_relationships_from_dict(relationships_data)
            if relationships_data is not None
            else EngineeringRelationships()
        ),
    )


# -- metadata + snapshot --------------------------------------------------

def snapshot_metadata_to_dict(metadata: SnapshotMetadata) -> dict[str, Any]:
    return {
        "source": metadata.source,
        "product_code": metadata.product_code,
        "created_at": metadata.created_at,
        "created_by": metadata.created_by,
        "notes": metadata.notes,
    }


def snapshot_metadata_from_dict(data: dict[str, Any]) -> SnapshotMetadata:
    return SnapshotMetadata(
        source=data.get("source", ""),
        product_code=data.get("product_code", ""),
        created_at=data.get("created_at"),
        created_by=data.get("created_by", ""),
        notes=data.get("notes", ""),
    )


def product_profile_to_dict(profile: ProductProfile) -> dict[str, Any]:
    return {
        "super_product": profile.super_product,
        "component_bucket": profile.component_bucket,
        "total_properties": profile.total_properties,
        "coded_properties": profile.coded_properties,
        "uncoded_properties": profile.uncoded_properties,
        "dependent_option_properties": profile.dependent_option_properties,
        "model_suffix_properties": profile.model_suffix_properties,
        "instance_variant_groups": [
            {"base": g.base, "variants": list(g.variants)}
            for g in profile.instance_variant_groups
        ],
        "traits": list(profile.traits),
    }


def product_profile_from_dict(data: dict[str, Any]) -> ProductProfile:
    return ProductProfile(
        super_product=bool(data.get("super_product", False)),
        component_bucket=bool(data.get("component_bucket", False)),
        total_properties=int(data.get("total_properties", 0)),
        coded_properties=int(data.get("coded_properties", 0)),
        uncoded_properties=int(data.get("uncoded_properties", 0)),
        dependent_option_properties=int(data.get("dependent_option_properties", 0)),
        model_suffix_properties=int(data.get("model_suffix_properties", 0)),
        instance_variant_groups=[
            VariantGroup(
                base=g.get("base", ""),
                variants=[str(v) for v in g.get("variants", [])],
            )
            for g in data.get("instance_variant_groups", [])
        ],
        traits=[str(t) for t in data.get("traits", [])],
    )


def article_set_to_dict(article_set: ArticleSet) -> dict[str, Any]:
    return {
        "id": article_set.id,
        "base_length": article_set.base_length,
        "base_code": article_set.base_code,
        "article_ids": list(article_set.article_ids),
        "properties": [_set_attribute_to_dict(a) for a in article_set.properties],
        "options": [_set_attribute_to_dict(a) for a in article_set.options],
    }


def _set_attribute_to_dict(attribute: SetAttribute) -> dict[str, Any]:
    return {
        "id": attribute.id,
        "name": attribute.name,
        "values": [
            {
                "id": v.id,
                "value": v.value,
                "code": v.code,
                "article_ids": list(v.article_ids),
            }
            for v in attribute.values
        ],
    }


def article_set_from_dict(data: dict[str, Any]) -> ArticleSet:
    return ArticleSet(
        id=str(data.get("id", "")),
        base_length=int(data.get("base_length", 0)),
        base_code=str(data.get("base_code", "")),
        article_ids=[str(a) for a in data.get("article_ids", [])],
        properties=[_set_attribute_from_dict(a) for a in data.get("properties", [])],
        options=[_set_attribute_from_dict(a) for a in data.get("options", [])],
    )


def _set_attribute_from_dict(data: dict[str, Any]) -> SetAttribute:
    return SetAttribute(
        id=str(data.get("id", "")),
        name=str(data.get("name", "")),
        values=[
            SetValue(
                id=str(v.get("id", "")),
                value=str(v.get("value", "")),
                code=str(v.get("code", "")),
                article_ids=[str(a) for a in v.get("article_ids", [])],
            )
            for v in data.get("values", [])
        ],
    )


def text_block_to_dict(block: TextBlock) -> dict[str, Any]:
    return {
        "name": block.name,
        "type_code": block.type_code,
        "de": block.de,
        "en": block.en,
        "fr": block.fr,
        "nl": block.nl,
    }


def text_block_from_dict(data: dict[str, Any]) -> TextBlock:
    return TextBlock(
        name=str(data.get("name", "")),
        type_code=str(data.get("type_code", "")),
        de=str(data.get("de", "")),
        en=str(data.get("en", "")),
        fr=str(data.get("fr", "")),
        nl=str(data.get("nl", "")),
    )


def price_record_to_dict(record: PriceRecord) -> dict[str, Any]:
    return {
        "is_global": record.is_global,
        "article_code": record.article_code,
        "variant_condition": record.variant_condition,
        "level": record.level,
        "value": record.value,
        "currency": record.currency,
        "valid_from": record.valid_from,
        "valid_to": record.valid_to,
    }


def price_record_from_dict(data: dict[str, Any]) -> PriceRecord:
    return PriceRecord(
        is_global=bool(data.get("is_global", False)),
        article_code=str(data.get("article_code", "")),
        variant_condition=str(data.get("variant_condition", "")),
        level=str(data.get("level", "B")),
        value=float(data.get("value", 0.0) or 0.0),
        currency=str(data.get("currency", "")),
        valid_from=str(data.get("valid_from", "")),
        valid_to=str(data.get("valid_to", "")),
    )


def price_list_to_dict(price_list: PriceList) -> dict[str, Any]:
    return {
        "id": price_list.id,
        "label": price_list.label,
        "currency": price_list.currency,
        "date_from": price_list.date_from,
        "date_to": price_list.date_to,
    }


def price_list_from_dict(data: dict[str, Any]) -> PriceList:
    return PriceList(
        id=str(data.get("id", "")),
        label=str(data.get("label", "")),
        currency=str(data.get("currency", "")),
        date_from=str(data.get("date_from", "")),
        date_to=str(data.get("date_to", "")),
    )


def relation_object_to_dict(relation: RelationObject) -> dict[str, Any]:
    return {
        "name": relation.name,
        "type_code": relation.type_code,
        "domain": relation.domain,
        "order": relation.order,
        "body": relation.body,
        "class_name": relation.class_name,
        "property_id": relation.property_id,
        "value_id": relation.value_id,
    }


def relation_object_from_dict(data: dict[str, Any]) -> RelationObject:
    return RelationObject(
        name=str(data.get("name", "")),
        type_code=str(data.get("type_code", "1")),
        domain=str(data.get("domain", "C")),
        order=int(data.get("order", 100)),
        body=str(data.get("body", "")),
        class_name=str(data.get("class_name", "")),
        property_id=str(data.get("property_id", "")),
        value_id=str(data.get("value_id", "")),
    )


def value_table_to_dict(table: ValueCombinationTable) -> dict[str, Any]:
    return {
        "name": table.name,
        "article_class": table.article_class,
        "property_names": list(table.property_names),
        "access": dict(table.access),
        "lines": [dict(line) for line in table.lines],
    }


def value_table_from_dict(data: dict[str, Any]) -> ValueCombinationTable:
    return ValueCombinationTable(
        name=str(data.get("name", "")),
        article_class=str(data.get("article_class", "")),
        property_names=[str(c) for c in data.get("property_names", [])],
        access={
            str(k): str(v) for k, v in (data.get("access") or {}).items()
        },
        lines=[
            {
                str(k): ([str(x) for x in v] if isinstance(v, list) else str(v))
                for k, v in (line or {}).items()
            }
            for line in data.get("lines", [])
        ],
    )


def snapshot_to_dict(snapshot: Snapshot) -> dict[str, Any]:
    """Serialize a whole Snapshot (source + engineering) to a JSON-ready dict."""
    return {
        "id": snapshot.id,
        "status": snapshot.status.value,
        "product": (
            product_to_dict(snapshot.product)
            if snapshot.product is not None
            else None
        ),
        "articles": [article_to_dict(a) for a in snapshot.articles],
        "properties": [property_to_dict(p) for p in snapshot.properties],
        "property_values": [
            property_value_to_dict(v) for v in snapshot.property_values
        ],
        "options": [option_to_dict(o) for o in snapshot.options],
        "option_values": [
            option_value_to_dict(v) for v in snapshot.option_values
        ],
        "article_property_value_ids": snapshot.article_property_value_ids,
        "product_property_value_ids": snapshot.product_property_value_ids,
        "product_option_value_ids": snapshot.product_option_value_ids,
        "article_components": snapshot.article_components,
        "component_head_attrs": snapshot.component_head_attrs,
        "article_varcond_terms": snapshot.article_varcond_terms,
        "article_prefix_length": snapshot.article_prefix_length,
        "base_length_overrides": snapshot.base_length_overrides,
        "base_article_overrides": snapshot.base_article_overrides,
        "option_increments": snapshot.option_increments,
        "attribute_value_exclusions": snapshot.attribute_value_exclusions,
        "attribute_option_dependencies": snapshot.attribute_option_dependencies,
        "option_option_dependencies": snapshot.option_option_dependencies,
        "metadata": snapshot_metadata_to_dict(snapshot.metadata),
        "product_profile": product_profile_to_dict(snapshot.product_profile),
        "article_sets": [article_set_to_dict(s) for s in snapshot.article_sets],
        "text_blocks": [text_block_to_dict(b) for b in snapshot.text_blocks],
        "relation_objects": [
            relation_object_to_dict(r) for r in snapshot.relation_objects
        ],
        "price_records": [
            price_record_to_dict(p) for p in snapshot.price_records
        ],
        "price_lists": [
            price_list_to_dict(p) for p in snapshot.price_lists
        ],
        "value_tables": [
            value_table_to_dict(t) for t in snapshot.value_tables
        ],
        "art_base": snapshot.art_base,
        "config_code_overrides": snapshot.config_code_overrides,
        "config_value_codes": snapshot.config_value_codes,
        "config_ignore_overrides": snapshot.config_ignore_overrides,
        "split_classes_by_group": snapshot.split_classes_by_group,
        "class_group_basis": snapshot.class_group_basis,
        "class_group_names": snapshot.class_group_names,
        "attribute_category": snapshot.attribute_category,
        "attribute_range": snapshot.attribute_range,
        "value_range": snapshot.value_range,
        "product_range": snapshot.product_range,
        "ignored_ranges": snapshot.ignored_ranges,
        "exclusion_delta": (
            _exclusion_delta_to_dict(snapshot, snapshot.exclusion_baseline)
            if snapshot.exclusion_baseline else None
        ),
        "engineering": engineering_to_dict(snapshot.engineering),
    }


def snapshot_from_dict(data: dict[str, Any]) -> Snapshot:
    """Restore a whole Snapshot (source + engineering) from a dict."""
    product_data = data.get("product")
    engineering_data = data.get("engineering")
    metadata_data = data.get("metadata")
    profile_data = data.get("product_profile")
    snap = Snapshot(
        id=data.get("id"),
        status=_snapshot_status_from(data.get("status")),
        product=(
            product_from_dict(product_data)
            if product_data is not None
            else None
        ),
        articles=[article_from_dict(a) for a in data.get("articles", [])],
        properties=[property_from_dict(p) for p in data.get("properties", [])],
        property_values=[
            property_value_from_dict(v)
            for v in data.get("property_values", [])
        ],
        options=[option_from_dict(o) for o in data.get("options", [])],
        option_values=[
            option_value_from_dict(v) for v in data.get("option_values", [])
        ],
        article_property_value_ids={
            str(k): [str(v) for v in vals]
            for k, vals in (data.get("article_property_value_ids") or {}).items()
        },
        product_property_value_ids={
            str(k): [str(v) for v in vals]
            for k, vals in (data.get("product_property_value_ids") or {}).items()
        },
        product_option_value_ids={
            str(k): [str(v) for v in vals]
            for k, vals in (data.get("product_option_value_ids") or {}).items()
        },
        article_components={
            str(k): list(v or [])
            for k, v in (data.get("article_components") or {}).items()
        },
        component_head_attrs={
            str(k): [str(n) for n in (v or [])]
            for k, v in (data.get("component_head_attrs") or {}).items()
        },
        article_varcond_terms={
            str(k): list(v or [])
            for k, v in (data.get("article_varcond_terms") or {}).items()
        },
        article_prefix_length={
            str(k): int(v)
            for k, v in (data.get("article_prefix_length") or {}).items()
            if v is not None
        },
        base_length_overrides={
            str(k): int(v)
            for k, v in (data.get("base_length_overrides") or {}).items()
            if v is not None
        },
        base_article_overrides={
            str(k): str(v)
            for k, v in (data.get("base_article_overrides") or {}).items()
            if v is not None
        },
        option_increments={
            str(k): list(v or [])
            for k, v in (data.get("option_increments") or {}).items()
        },
        attribute_value_exclusions={
            str(k): [str(v) for v in vals]
            for k, vals in (data.get("attribute_value_exclusions") or {}).items()
        },
        attribute_option_dependencies={
            str(k): [str(v) for v in vals]
            for k, vals in (data.get("attribute_option_dependencies") or {}).items()
        },
        option_option_dependencies={
            str(k): [str(v) for v in vals]
            for k, vals in (data.get("option_option_dependencies") or {}).items()
        },
        metadata=(
            snapshot_metadata_from_dict(metadata_data)
            if metadata_data is not None
            else SnapshotMetadata()
        ),
        product_profile=(
            product_profile_from_dict(profile_data)
            if profile_data is not None
            else ProductProfile()
        ),
        article_sets=[
            article_set_from_dict(s) for s in data.get("article_sets", [])
        ],
        text_blocks=[
            text_block_from_dict(b) for b in data.get("text_blocks", [])
        ],
        relation_objects=[
            relation_object_from_dict(r) for r in data.get("relation_objects", [])
        ],
        price_records=[
            price_record_from_dict(p) for p in data.get("price_records", [])
        ],
        price_lists=[
            price_list_from_dict(p) for p in data.get("price_lists", [])
        ],
        value_tables=[
            value_table_from_dict(t) for t in data.get("value_tables", [])
        ],
        art_base={
            str(k): {
                str(ek): [str(v) for v in vals]
                for ek, vals in (m or {}).items()
            }
            for k, m in (data.get("art_base") or {}).items()
        },
        config_code_overrides={
            str(k): {str(vk): str(vv) for vk, vv in (m or {}).items()}
            for k, m in (data.get("config_code_overrides") or {}).items()
        },
        config_value_codes={
            str(k): {str(vk): str(vv) for vk, vv in (m or {}).items()}
            for k, m in (data.get("config_value_codes") or {}).items()
        },
        config_ignore_overrides={
            str(k): bool(v)
            for k, v in (data.get("config_ignore_overrides") or {}).items()
        },
        split_classes_by_group=bool(data.get("split_classes_by_group", False)),
        class_group_basis=str(data.get("class_group_basis", "") or "range"),
        class_group_names={
            str(k): str(v)
            for k, v in (data.get("class_group_names") or {}).items()
        },
        attribute_category={
            str(k): str(v)
            for k, v in (data.get("attribute_category") or {}).items()
        },
        attribute_range={
            str(k): [str(v) for v in vals]
            for k, vals in (data.get("attribute_range") or {}).items()
        },
        value_range={
            str(k): [str(v) for v in vals]
            for k, vals in (data.get("value_range") or {}).items()
        },
        product_range={
            str(k): str(v)
            for k, v in (data.get("product_range") or {}).items()
        },
        ignored_ranges=[str(v) for v in (data.get("ignored_ranges") or [])],
        engineering=(
            engineering_from_dict(engineering_data)
            if engineering_data is not None
            else Engineering()
        ),
    )
    # Rebuild the held exclusion baseline (full = working + excluded delta) so a
    # reloaded project can still restore an excluded range with no PDM reload.
    delta = data.get("exclusion_delta")
    if delta:
        snap.exclusion_baseline = _reconstruct_exclusion_baseline(snap, delta)
    return snap
