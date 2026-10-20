"""Regression tests for XOCD relation-object bindings on properties and values."""

from models.engineering_class import ClassPropertyAssignment, EngineeringClass
from models.property import Property, PropertyValue
from models.relation_object import RelationObject
from models.snapshot import Snapshot
from services.xocd_export_service import XocdExportService


class _RelationService:
    @staticmethod
    def build_relation_objects(snapshot):
        return snapshot.relation_objects


class _ClassService:
    @staticmethod
    def resolve_config_codes(snapshot):
        return {}


class _Context:
    engineering_relation_service = _RelationService()
    engineering_class_service = _ClassService()


def test_xocd_exports_property_and_value_relation_bindings_to_correct_rows():
    snapshot = Snapshot(
        properties=[
            Property(id="parent", name="Parent"),
            Property(
                id="child",
                name="Child",
                values=[
                    PropertyValue(
                        id="child-x", property_id="child", value="X", code="X"
                    )
                ],
            ),
        ],
        property_values=[
            PropertyValue(
                id="child-x", property_id="child", value="X", code="X"
            )
        ],
        relation_objects=[
            RelationObject(
                name="A_Code_Parent",
                type_code="3",
                domain="C",
                body="CodeParent = 'A'",
                property_id="parent",
            ),
            RelationObject(
                name="B_Child_X",
                type_code="1",
                domain="C",
                body="(SPECIFIED Parent) AND (Parent IN ('A'))",
                property_id="child",
                value_id="child-x",
            ),
        ],
    )
    service = XocdExportService(_Context())

    relation_rows, body_rows, value_relobj, property_relobj = service._relations(
        snapshot, {"program": "TEST"}
    )

    assert len(relation_rows) == 2
    assert body_rows
    assert property_relobj == {"parent": 1}
    assert value_relobj == {"child-x": 2}

    classes = [
        EngineeringClass(
            id="class-1",
            name="Chair",
            properties=[
                ClassPropertyAssignment(
                    property_id="parent", property_name="Parent", type="C"
                ),
                ClassPropertyAssignment(
                    property_id="child", property_name="Child", type="C"
                ),
            ],
        )
    ]
    property_rows = service._properties(
        snapshot, {"program": "TEST"}, classes, property_relobj
    )

    # xocd_property.csv field 6 (zero-based index 5) is RelObjID.
    assert property_rows[0][5] == 1
    assert property_rows[1][5] == 0

    value_rows = service._property_values(
        snapshot, {"program": "TEST"}, classes, value_relobj
    )
    assert any(row[6] == 2 for row in value_rows)
