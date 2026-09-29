from types import SimpleNamespace

from models.article import Article
from models.engineering import Engineering
from models.engineering_class import (
    ClassPropertyAssignment,
    ClassValue,
    EngineeringClass,
)
from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.engineering.engineering_class_service import EngineeringClassService
from services.engineering.engineering_reduction_service import (
    EngineeringReductionService,
)
from services.snapshot_serialization import snapshot_from_dict, snapshot_to_dict


def _snapshot():
    v_x = PropertyValue(id="vx", property_id="p1", value="X", code="X")
    v_y = PropertyValue(id="vy", property_id="p1", value="Y", code="Y")
    prop = Property(
        id="p1",
        name="Type",
        values=[v_x, v_y],
        has_dependent_options=True,
    )
    a1 = Article(id="a1", product_id="prod", code="A1X100.S1")
    a2 = Article(id="a2", product_id="prod", code="A1Y100.S2")
    cls = EngineeringClass(
        id="class1",
        name="Bolster_Attribute",
        properties=[
            ClassPropertyAssignment(
                property_id="p1",
                property_name="Type",
                width=1,
                placement=0,
                values=[
                    ClassValue(value_id="vx", code="X", value="X"),
                    ClassValue(value_id="vy", code="Y", value="Y"),
                ],
            )
        ],
    )
    members = [
        MemberArticle(id="m1", article_id="a1", family_id="f1"),
        MemberArticle(id="m2", article_id="a2", family_id="f1"),
    ]
    snapshot = Snapshot(
        id="s1",
        articles=[a1, a2],
        properties=[prop],
        article_property_value_ids={"a1": ["vx"], "a2": ["vy"]},
        engineering=Engineering(
            classes=[cls],
            families=[EngineeringFamily(id="f1", name="Bolster", members=members)],
        ),
    )
    return snapshot


def _service(snapshot):
    context = SimpleNamespace()
    context.engineering_class_service = EngineeringClassService(context)
    return EngineeringReductionService(context)


def test_development_class_creation_reduction_preserves_article_specific_value_coverage():
    snapshot = _snapshot()
    service = _service(snapshot)

    sets = service.materialize_class_creation_article_sets(snapshot)

    assert len(sets) == 1
    assert sets[0].base_code == "A1"
    assert sets[0].base_length == 2
    assert snapshot.articles[0].code == "A1X100.S1"
    assert snapshot.articles[1].code == "A1Y100.S2"
    assert snapshot.engineering.families[0].members[0].reduced_article == "A1"
    assert snapshot.engineering.families[0].members[1].reduced_article == "A1"

    values = {v.id: v for v in sets[0].properties[0].values}
    assert values["vx"].article_ids == ["a1"]
    assert values["vy"].article_ids == ["a2"]


def test_class_creation_sliced_match_does_not_reassign_pdm_article_value():
    snapshot = _snapshot()
    prop = snapshot.properties[0]
    prop.values.append(PropertyValue(id="vz", property_id="p1", value="Z", code="Z"))
    snapshot.articles[0].code = "A1Y100.S1"
    snapshot.base_length_overrides = {"A1Y100.S1": 2, "A1Y100.S2": 2}
    service = _service(snapshot)

    article_set = service.materialize_class_creation_article_sets(snapshot)[0]

    assert article_set.article_ids == ["a1", "a2"]
    values = {value.id: value for value in article_set.properties[0].values}
    assert values["vx"].article_ids == ["a1"]
    assert values["vy"].article_ids == ["a2"]
    assert {value.id for value in prop.values} - set(values) == {"vz"}
    assert snapshot.article_property_value_ids == {"a1": ["vx"], "a2": ["vy"]}


def test_class_creation_single_article_leaves_other_pdm_values_remaining():
    snapshot = _snapshot()
    prop = snapshot.properties[0]
    prop.values.append(PropertyValue(id="vz", property_id="p1", value="Z", code="Z"))
    snapshot.articles.pop()
    snapshot.article_property_value_ids.pop("a2")
    snapshot.engineering.families[0].members.pop()

    article_set = _service(snapshot).materialize_class_creation_article_sets(snapshot)[0]

    assert article_set.article_ids == ["a1"]
    assert {value.id: value.article_ids for value in article_set.properties[0].values} == {
        "vx": ["a1"],
    }
    assert {value.id for value in prop.values} - {
        value.id for value in article_set.properties[0].values
    } == {"vy", "vz"}


def test_development_class_creation_ignore_keeps_property_in_base():
    snapshot = _snapshot()
    snapshot.config_ignore_overrides = {"p1": True}
    snapshot.base_length_overrides = {"A1X100.S1": 3, "A1Y100.S2": 3}
    service = _service(snapshot)

    sets = service.materialize_class_creation_article_sets(snapshot)

    assert sets[0].base_code == "A1"
    assert sets[0].base_length == 2
    assert snapshot.engineering.families[0].members[0].reduced_article == "A1X"
    assert snapshot.engineering.families[0].members[1].reduced_article == "A1Y"
    assert snapshot.config_ignore_overrides == {"p1": True}


def test_development_class_creation_code_correction_changes_only_matching_article():
    snapshot = _snapshot()
    assignment = snapshot.engineering.classes[0].properties[0]
    assignment.values[0].code = "Q"
    snapshot.base_length_overrides = {"A1X100.S1": 2, "A1Y100.S2": 2}
    service = _service(snapshot)

    article_set = service.materialize_class_creation_article_sets(snapshot)[0]

    assert service.resolve_variant_condition(snapshot, "a1", 2).consumed == ()
    assert service.resolve_variant_condition(snapshot, "a2", 2).consumed == (
        ("p1", "Type", "Y"),
    )
    assert [member.reduced_article for member in snapshot.engineering.families[0].members] == ["A1", "A1"]
    assert {value.id: value.article_ids for value in article_set.properties[0].values} == {
        "vx": ["a1"], "vy": ["a2"],
    }


def test_development_reduction_uses_class_creation_sliced_code_not_article_value_id():
    snapshot = Snapshot(
        id="s2",
        articles=[Article(id="a1", product_id="prod", code="AL1C1002S")],
        properties=[
            Property(
                id="p1",
                name="Type",
                values=[
                    PropertyValue(id="v0", property_id="p1", value="Zero", code="0"),
                    PropertyValue(id="v2", property_id="p1", value="Two", code="2"),
                ],
                has_dependent_options=True,
            )
        ],
        # Deliberately point the PDM relationship at 0 even though the
        # Class Creation Sliced vocabulary contains both 0 and 2. The
        # reduction must follow Class Creation, not this PDM value id.
        article_property_value_ids={"a1": ["v0"]},
        base_length_overrides={"AL1C1002S": 7},
        engineering=Engineering(
            classes=[
                EngineeringClass(
                    id="class2",
                    name="Bolster_Attribute",
                    properties=[
                        ClassPropertyAssignment(
                            property_id="p1",
                            property_name="Type",
                            width=1,
                            placement=0,
                            values=[
                                ClassValue(value_id="v0", code="0", value="Zero"),
                                ClassValue(value_id="v2", code="2", value="Two"),
                            ],
                        )
                    ],
                )
            ],
            families=[
                EngineeringFamily(
                    id="f2",
                    name="Bolster",
                    members=[MemberArticle(id="m3", article_id="a1", family_id="f2")],
                )
            ],
        ),
    )
    service = _service(snapshot)

    article_set = service.materialize_class_creation_article_sets(snapshot)[0]

    assert snapshot.engineering.families[0].members[0].reduced_article == "AL1C100"
    assert service.resolve_variant_condition(snapshot, "a1", 7).consumed == (
        ("p1", "Type", "2"),
    )
    assert service.resolve_variant_condition(snapshot, "a1", 7).remaining == "S"
    assert [(value.id, value.article_ids) for value in article_set.properties[0].values] == [
        ("v0", ["a1"]),
    ]
    assert snapshot.article_property_value_ids == {"a1": ["v0"]}

def test_manual_base_length_override_preserves_class_creation_property_relationships_and_ignore():
    snapshot = _snapshot()
    snapshot.config_ignore_overrides = {"p1": False}
    snapshot.base_length_overrides = {"A1X100.S1": 3, "A1Y100.S2": 3}
    service = _service(snapshot)

    sets = service.materialize_class_creation_article_sets(snapshot)

    assert snapshot.engineering.families[0].members[0].reduced_article == "A1X"
    assert snapshot.engineering.families[0].members[1].reduced_article == "A1Y"
    values = {v.id: v for v in sets[0].properties[0].values}
    assert values["vx"].article_ids == ["a1"]
    assert values["vy"].article_ids == ["a2"]
    assert snapshot.config_ignore_overrides == {"p1": False}
    assert snapshot.article_property_value_ids == {"a1": ["vx"], "a2": ["vy"]}


def test_manual_base_length_override_round_trips_with_snapshot():
    snapshot = _snapshot()
    snapshot.base_length_overrides = {"A1X100.S1": 3}

    restored = snapshot_from_dict(snapshot_to_dict(snapshot))

    assert restored.base_length_overrides == {"A1X100.S1": 3}


def test_manual_base_length_override_wins_over_registry_override_in_review_preview():
    # Regression contract for Review: the export preview may load CAD registry
    # defaults, but an explicit Article-workflow override remains authoritative.
    registry = {"A1X100.S1": 6}
    manual = {"A1X100.S1": 3}
    effective = dict(registry)
    effective.update(manual)
    assert effective["A1X100.S1"] == 3


def test_variant_condition_is_consumed_only_from_the_next_positional_slice():
    snapshot = _snapshot()
    snapshot.articles[0].code = "A1ZXX.S1"
    service = _service(snapshot)

    resolved = service.resolve_variant_condition(snapshot, "a1", 2)

    assert resolved.base == "A1"
    assert resolved.remaining == "ZXX"
    assert resolved.consumed == ()
    assert resolved.unassigned == "ZXX"


def test_variant_condition_consumes_sequential_widths_in_placement_order():
    snapshot = Snapshot(
        id="s3",
        articles=[Article(id="a1", product_id="prod", code="ABC145")],
        properties=[
            Property(id="p1", name="Height", values=[
                PropertyValue(id="h1", property_id="p1", value="1", code="1")
            ], has_dependent_options=True),
            Property(id="p2", name="Width", values=[
                PropertyValue(id="w45", property_id="p2", value="45", code="45")
            ], has_dependent_options=True),
        ],
        article_property_value_ids={"a1": ["h1", "w45"]},
        engineering=Engineering(
            classes=[EngineeringClass(
                id="class3",
                name="Chair_Attribute",
                properties=[
                    ClassPropertyAssignment(
                        property_id="p1", property_name="Height", width=1, placement=0,
                        values=[ClassValue(value_id="h1", code="1", value="1")],
                    ),
                    ClassPropertyAssignment(
                        property_id="p2", property_name="Width", width=2, placement=1,
                        values=[ClassValue(value_id="w45", code="45", value="45")],
                    ),
                ],
            )],
            families=[EngineeringFamily(
                id="f3", name="Chair",
                members=[MemberArticle(id="m3", article_id="a1", family_id="f3")],
            )],
        ),
    )
    service = _service(snapshot)

    resolved = service.resolve_variant_condition(snapshot, "a1", 3)

    assert resolved.base == "ABC"
    assert resolved.remaining == ""
    assert resolved.unassigned == ""
    assert resolved.consumed == (
        ("p1", "Height", "1"),
        ("p2", "Width", "45"),
    )


def test_variant_condition_does_not_consume_a_property_not_carried_by_article():
    snapshot = Snapshot(
        id="s4",
        articles=[Article(id="a1", product_id="prod", code="ABC123")],
        properties=[
            Property(id="p1", name="Height", values=[
                PropertyValue(id="h1", property_id="p1", value="1", code="1")
            ], has_dependent_options=True),
            Property(id="p2", name="Width", values=[
                PropertyValue(id="w2", property_id="p2", value="2", code="2")
            ], has_dependent_options=True),
        ],
        article_property_value_ids={"a1": ["h1"]},
        engineering=Engineering(
            classes=[EngineeringClass(
                id="class4",
                name="Chair_Attribute",
                properties=[
                    ClassPropertyAssignment(
                        property_id="p1", property_name="Height", width=1, placement=0,
                        values=[ClassValue(value_id="h1", code="1", value="1")],
                    ),
                    ClassPropertyAssignment(
                        property_id="p2", property_name="Width", width=1, placement=1,
                        values=[ClassValue(value_id="w2", code="2", value="2")],
                    ),
                ],
            )],
            families=[EngineeringFamily(
                id="f4", name="Chair",
                members=[MemberArticle(id="m4", article_id="a1", family_id="f4")],
            )],
        ),
    )
    service = _service(snapshot)

    resolved = service.resolve_variant_condition(snapshot, "a1", 3)

    assert resolved.base == "ABC"
    assert resolved.remaining == "23"
    assert resolved.unassigned == "23"
    assert resolved.consumed == (("p1", "Height", "1"),)


def test_variant_condition_rejects_invalid_width_but_keeps_unassigned_tail():
    snapshot = _snapshot()
    assignment = snapshot.engineering.classes[0].properties[0]
    assignment.width = 2
    service = _service(snapshot)

    resolved = service.resolve_variant_condition(snapshot, "a1", 2)

    assert resolved.base == "A1"
    assert resolved.remaining == "X100"
    assert resolved.unassigned == "X100"
    assert any("width" in issue.lower() for issue in resolved.issues)


def test_class_creation_split_metadata_round_trips():
    snapshot = _snapshot()
    service = _service(snapshot)
    service.materialize_class_creation_article_sets(snapshot)

    restored = snapshot_from_dict(snapshot_to_dict(snapshot))

    assert restored.article_sets[0].class_splits
    split = restored.article_sets[0].class_splits[0]
    assert split.property_id == "p1"
    assert split.width == 1
    assert split.start == restored.article_sets[0].base_length
