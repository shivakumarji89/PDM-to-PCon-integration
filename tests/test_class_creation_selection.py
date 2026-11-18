from types import SimpleNamespace

from services.class_creation_selection_service import (
    build_class_creation_scope,
    classes_for_article,
)


def _snapshot():
    prop = SimpleNamespace(id="p1", values=[SimpleNamespace(id="pv1"), SimpleNamespace(id="pv2")])
    option = SimpleNamespace(id="o1", values=[SimpleNamespace(id="ov1")])
    return SimpleNamespace(
        product=SimpleNamespace(category="Desk", range_name="Desk"),
        articles=[
            SimpleNamespace(id="a1", product_id="prod1"),
            SimpleNamespace(id="a2", product_id="prod2"),
        ],
        properties=[prop],
        property_values=[
            SimpleNamespace(id="pv1", property_id="p1"),
            SimpleNamespace(id="pv2", property_id="p1"),
        ],
        options=[option],
        option_values=[SimpleNamespace(id="ov1", option_id="o1")],
        article_property_value_ids={"a1": ["pv1"], "a2": ["pv2"]},
        product_property_value_ids={},
        product_option_value_ids={"prod1": ["ov1"], "prod2": []},
        product_range={"prod1": "Desks", "prod2": "Screens"},
        attribute_range={"p1": ["Desks"]},
        article_sets=[],
        split_classes_by_group=False,
        class_group_basis="range",
    )


def test_scope_for_one_article_contains_only_its_properties_and_options():
    scope = build_class_creation_scope(_snapshot(), {"a1"})
    assert scope.article_ids == frozenset({"a1"})
    assert scope.property_ids == frozenset({"p1"})
    assert scope.property_value_ids == {"p1": frozenset({"pv1"})}
    assert scope.option_ids == frozenset({"o1"})
    assert scope.option_value_ids == {"o1": frozenset({"ov1"})}
    assert scope.product_ranges == frozenset({"Desks"})


def test_scope_for_multiple_articles_unions_their_values_and_ranges():
    scope = build_class_creation_scope(_snapshot(), {"a1", "a2"})
    assert scope.article_ids == frozenset({"a1", "a2"})
    assert scope.property_value_ids == {"p1": frozenset({"pv1", "pv2"})}
    assert scope.option_value_ids == {"o1": frozenset({"ov1"})}
    assert scope.product_ranges == frozenset({"Desks", "Screens"})


def test_classes_for_article_keeps_only_related_class_assignments():
    snapshot = _snapshot()
    attribute = SimpleNamespace(
        id="c1", name="Desk_Attribute",
        properties=[
            SimpleNamespace(property_id="p1"),
            SimpleNamespace(property_id="p2"),
        ],
    )
    options = SimpleNamespace(
        id="c2", name="Desk_Options",
        properties=[SimpleNamespace(property_id="o1")],
    )
    unrelated = SimpleNamespace(
        id="c3", name="Desk_Attribute",
        properties=[SimpleNamespace(property_id="p2")],
    )
    selected = classes_for_article(snapshot, [attribute, options, unrelated], "a1")
    assert [c.id for c in selected] == ["c1", "c2"]
    assert [a.property_id for a in selected[0].properties] == ["p1"]
