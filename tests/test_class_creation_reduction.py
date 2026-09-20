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


def test_development_class_creation_reduction_uses_article_specific_pdm_value():
    snapshot = _snapshot()
    service = _service(snapshot)

    sets = service.materialize_class_creation_article_sets(snapshot)

    assert len(sets) == 1
    assert sets[0].base_code == "A1100"
    assert sets[0].base_length == 5
    assert snapshot.articles[0].code == "A1X100.S1"
    assert snapshot.articles[1].code == "A1Y100.S2"
    assert snapshot.engineering.families[0].members[0].reduced_article == "A1100"
    assert snapshot.engineering.families[0].members[1].reduced_article == "A1100"

    values = {v.id: v for v in sets[0].properties[0].values}
    assert values["vx"].article_ids == ["a1"]
    assert values["vy"].article_ids == ["a2"]


def test_development_class_creation_ignore_keeps_property_in_base():
    snapshot = _snapshot()
    snapshot.config_ignore_overrides = {"p1": True}
    service = _service(snapshot)

    sets = service.materialize_class_creation_article_sets(snapshot)

    assert sets[0].base_code == "A1"
    assert sets[0].base_length == 2
    assert snapshot.engineering.families[0].members[0].reduced_article == "A1X100"
    assert snapshot.engineering.families[0].members[1].reduced_article == "A1Y100"


def test_development_class_creation_code_correction_changes_only_matching_article():
    snapshot = _snapshot()
    assignment = snapshot.engineering.classes[0].properties[0]
    assignment.values[0].code = "Q"
    service = _service(snapshot)

    service.materialize_class_creation_article_sets(snapshot)

    # Article a1 still contains the old PDM code X, so the corrected Q does not
    # remove it. Article a2 still uses the unchanged Y mapping.
    assert snapshot.engineering.families[0].members[0].reduced_article == "A1X100"
    assert snapshot.engineering.families[0].members[1].reduced_article == "A1100"
