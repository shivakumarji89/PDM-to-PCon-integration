from types import SimpleNamespace

from services.properties_values_mdb_export_service import PropertiesValuesMdbExportService


def _snapshot_and_classes():
    p1 = SimpleNamespace(
        id="p1",
        values=[
            SimpleNamespace(id="pv1", property_id="p1", value="One", code="A"),
            SimpleNamespace(id="pv2", property_id="p1", value="Two", code="B"),
        ],
    )
    p2 = SimpleNamespace(
        id="p2",
        values=[SimpleNamespace(id="pv3", property_id="p2", value="Three", code="C")],
    )
    a1 = SimpleNamespace(
        id="a1",
        properties=[
            SimpleNamespace(property_id="p1", property_name="Type",
                            values=[SimpleNamespace(value_id="pv1", code="A", value="One")]),
        ],
    )
    a2 = SimpleNamespace(
        id="a2",
        properties=[
            SimpleNamespace(property_id="p2", property_name="Finish",
                            values=[SimpleNamespace(value_id="pv3", code="C", value="Three")]),
        ],
    )
    classes = [
        SimpleNamespace(id="class1", name="Desk_Attribute", properties=a1.properties),
        SimpleNamespace(id="class1", name="Desk_Attribute", properties=a2.properties),
    ]
    snapshot = SimpleNamespace(
        product=SimpleNamespace(category="Desk", range_name="Desk"),
        articles=[
            SimpleNamespace(id="a1", product_id="prod1"),
            SimpleNamespace(id="a2", product_id="prod2"),
        ],
        properties=[p1, p2],
        property_values=[*p1.values, *p2.values],
        options=[],
        option_values=[],
        article_property_value_ids={"a1": ["pv1"], "a2": ["pv3"]},
        product_property_value_ids={},
        product_option_value_ids={},
        product_range={},
        attribute_range={},
        article_sets=[],
        split_classes_by_group=False,
        class_group_basis="range",
    )
    return snapshot, classes


def test_assignment_union_for_one_article_keeps_only_its_related_property():
    snapshot, classes = _snapshot_and_classes()
    result = PropertiesValuesMdbExportService._assignment_union(snapshot, classes, {"a1"})
    assert list(result) == ["Desk_Attribute"]
    assert set(result["Desk_Attribute"]) == {"p1"}


def test_assignment_union_for_multiple_articles_unions_properties():
    snapshot, classes = _snapshot_and_classes()
    result = PropertiesValuesMdbExportService._assignment_union(snapshot, classes, {"a1", "a2"})
    assert list(result) == ["Desk_Attribute"]
    assert set(result["Desk_Attribute"]) == {"p1", "p2"}


def test_assignment_union_does_not_mutate_source_classes():
    snapshot, classes = _snapshot_and_classes()
    before = [
        (cls.name, [assignment.property_id for assignment in cls.properties])
        for cls in classes
    ]
    PropertiesValuesMdbExportService._assignment_union(snapshot, classes, {"a1", "a2"})
    after = [
        (cls.name, [assignment.property_id for assignment in cls.properties])
        for cls in classes
    ]
    assert after == before
