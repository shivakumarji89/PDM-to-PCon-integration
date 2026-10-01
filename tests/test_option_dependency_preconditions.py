"""Tests for value-bound 1/C preconditions derived from DependentOptionValues."""

import unittest

from models.option import Option
from models.option_value import OptionValue
from models.property import Property, PropertyValue
from models.relation_object import RelationObject
from models.snapshot import Snapshot
from services.engineering.engineering_relation_service import EngineeringRelationService


class _RelationContext:
    class _EngineeringClassService:
        @staticmethod
        def resolve_config_codes(snapshot):
            return {}

    engineering_class_service = _EngineeringClassService()


def _option(oid: str, name: str, codes: list[str], order: int) -> Option:
    return Option(
        id=oid,
        name=name,
        display_order=order,
        values=[
            OptionValue(id=code, option_id=oid, value=code, code=code, display_order=i)
            for i, code in enumerate(codes)
        ],
    )


def _snapshot(grades: dict[str, list[str]], edges: dict[str, list[str]]) -> Snapshot:
    fabric = _option("fabric", "Fabric", list(grades), 1)
    colours = [code for codes in grades.values() for code in codes]
    colour = _option("colour", "Fabric colour", colours, 2)
    return Snapshot(
        options=[fabric, colour],
        option_values=fabric.values + colour.values,
        option_option_dependencies=edges,
    )


def _preconditions(snapshot: Snapshot) -> list[RelationObject]:
    service = EngineeringRelationService(_RelationContext())
    return [r for r in service.build_relation_objects(snapshot) if r.name.startswith("B_")]


class OptionDependencyPreconditionTests(unittest.TestCase):
    def test_one_parent_one_child(self):
        snapshot = _snapshot({"V26": ["V2601"]}, {"V26": ["V2601"]})

        [rel] = _preconditions(snapshot)

        self.assertEqual(rel.name, "B_FABRIC_COLOUR_V26")
        self.assertEqual(rel.relation_name, "BA_FABRIC_COLOUR_V26")
        self.assertEqual((rel.type_code, rel.domain, rel.order), ("1", "C", 100))
        self.assertEqual(rel.body, "(SPECIFIED Fabric) AND (Fabric IN ('V26'))")
        self.assertEqual(rel.value_ids, ["V2601"])
        self.assertEqual((rel.value_id, rel.property_id, rel.property_ids), ("", "", []))

    def test_one_parent_many_children_share_one_relation_object(self):
        snapshot = _snapshot(
            {"V26": ["V2601", "V2602", "V2603"]},
            {"V26": ["V2603", "V2601", "V2602"]},
        )

        [rel] = _preconditions(snapshot)

        self.assertEqual(rel.value_ids, ["V2601", "V2602", "V2603"])

    def test_each_parent_value_gets_its_own_relation_object(self):
        snapshot = _snapshot(
            {"V26": ["V2601", "V2602"], "V27": ["V2701", "V2702"]},
            {"V26": ["V2601", "V2602"], "V27": ["V2701", "V2702"]},
        )

        rels = _preconditions(snapshot)

        self.assertEqual(
            [(r.name, r.value_ids) for r in rels],
            [
                ("B_FABRIC_COLOUR_V26", ["V2601", "V2602"]),
                ("B_FABRIC_COLOUR_V27", ["V2701", "V2702"]),
            ],
        )
        self.assertEqual(rels[1].body, "(SPECIFIED Fabric) AND (Fabric IN ('V27'))")

    def test_duplicate_dependency_rows_do_not_duplicate_bindings_or_objects(self):
        snapshot = _snapshot(
            {"V26": ["V2601", "V2602"]},
            {"V26": ["V2601", "V2601", "V2602", "V2602"]},
        )

        rels = _preconditions(snapshot)

        self.assertEqual([r.name for r in rels], ["B_FABRIC_COLOUR_V26"])
        self.assertEqual(rels[0].value_ids, ["V2601", "V2602"])

    def test_no_dependency_rows_generate_no_preconditions(self):
        snapshot = _snapshot({"V26": ["V2601"]}, {})

        self.assertEqual(_preconditions(snapshot), [])

    def test_edges_to_values_outside_the_snapshot_are_ignored(self):
        snapshot = _snapshot({"V26": ["V2601"]}, {"V26": ["V2601", "GONE"], "MISSING": ["V2601"]})

        [rel] = _preconditions(snapshot)

        self.assertEqual(rel.value_ids, ["V2601"])

    def test_parent_code_hash_flag_is_dropped_as_in_existing_tokens(self):
        snapshot = _snapshot({"1HA#": ["1HA01"]}, {"1HA#": ["1HA01"]})

        [rel] = _preconditions(snapshot)

        self.assertEqual(rel.name, "B_FABRIC_COLOUR_1HA")
        self.assertEqual(rel.body, "(SPECIFIED Fabric) AND (Fabric IN ('1HA'))")

    def test_secondary_fabric_options_stay_distinct(self):
        primary = _option("fabric", "Fabric type", ["V26"], 1)
        primary_colour = _option("colour", "Fabric colour", ["V2601"], 2)
        secondary = Option(id="fabric2", name="Fabric type (Secondary)", display_order=3, values=[
            OptionValue(id="V26S", option_id="fabric2", value="V26", code="V26"),
        ])
        secondary_colour = Option(id="colour2", name="Fabric colour (Secondary)", display_order=4, values=[
            OptionValue(id="V2601S", option_id="colour2", value="V2601", code="V2601"),
        ])
        snapshot = Snapshot(
            options=[primary, primary_colour, secondary, secondary_colour],
            option_option_dependencies={"V26": ["V2601"], "V26S": ["V2601S"]},
        )

        rels = _preconditions(snapshot)

        self.assertEqual(
            [(r.name, r.body, r.value_ids) for r in rels],
            [
                ("B_FABRIC_COLOUR_V26",
                 "(SPECIFIED Fabric_Type) AND (Fabric_Type IN ('V26'))", ["V2601"]),
                ("B_FABRIC_COLOUR_SECONDARY_V26",
                 "(SPECIFIED Fabric_Type_Secondary) AND (Fabric_Type_Secondary IN ('V26'))",
                 ["V2601S"]),
            ],
        )

    def test_child_enabled_by_several_parent_values_gets_one_shared_object(self):
        frame = _option("frame", "Frame finish", ["G1", "BK", "CRB"], 1)
        chassis = _option("chassis", "Chassis finish", ["G1C", "BLX", "SNC"], 2)
        snapshot = Snapshot(
            options=[frame, chassis],
            # G1C reachable from G1 only; BLX from G1 and BK (Aeron-style multi
            # parent); SNC from BK and CRB, listed twice to mimic duplicate rows.
            option_option_dependencies={
                "G1": ["G1C", "BLX"],
                "BK": ["BLX", "SNC"],
                "CRB": ["SNC", "SNC"],
            },
        )

        rels = _preconditions(snapshot)

        self.assertEqual(
            [(r.name, r.relation_name, r.body, r.value_ids) for r in rels],
            [
                ("B_CHASSIS_FINISH_G1", "BA_CHASSIS_FINISH_G1",
                 "(SPECIFIED Frame_Finish) AND (Frame_Finish IN ('G1'))", ["G1C"]),
                ("B_CHASSIS_FINISH_G1_BK", "BA_CHASSIS_FINISH_G1_BK",
                 "(SPECIFIED Frame_Finish) AND (Frame_Finish IN ('G1', 'BK'))", ["BLX"]),
                ("B_CHASSIS_FINISH_BK_CRB", "BA_CHASSIS_FINISH_BK_CRB",
                 "(SPECIFIED Frame_Finish) AND (Frame_Finish IN ('BK', 'CRB'))", ["SNC"]),
            ],
        )
        bound = [v for r in rels for v in r.value_ids]
        self.assertEqual(len(bound), len(set(bound)))  # one RelObjID per PropValue
        self.assertEqual(rels, _preconditions(snapshot))  # deterministic

    def test_generated_preconditions_feed_related_value_ids(self):
        snapshot = _snapshot({"V26": ["V2601", "V2602"]}, {"V26": ["V2601", "V2602"]})
        service = EngineeringRelationService(_RelationContext())
        snapshot.relation_objects = service.build_relation_objects(snapshot)

        self.assertEqual(service.related_value_ids(snapshot), {"V2601", "V2602"})

    def test_imported_relation_with_same_name_wins_and_code_action_is_kept(self):
        snapshot = _snapshot({"V26": ["V2601"]}, {"V26": ["V2601"]})
        snapshot.properties = [
            Property(
                id="width",
                name="Width",
                values=[PropertyValue(id="w1", property_id="width", value="600", code="06")],
            )
        ]
        imported = RelationObject(
            name="B_FABRIC_COLOUR_V26", type_code="1", domain="C",
            body="(SPECIFIED Fabric) AND (Fabric IN ('V26')) AND $BAN IN ('X')",
            value_ids=["V2601"], rel_obj_id="885", relation_id="900",
        )
        snapshot.relation_objects = [imported]
        service = EngineeringRelationService(_RelationContext())

        relations = service.build_relation_objects(snapshot)

        self.assertEqual([r.name for r in relations], ["B_FABRIC_COLOUR_V26", "A_Code_Width"])
        self.assertIs(relations[0], imported)


if __name__ == "__main__":
    unittest.main()
