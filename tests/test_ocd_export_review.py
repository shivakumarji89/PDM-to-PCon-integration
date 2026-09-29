"""Regression test for the Review-specific export path in OcdExportService.

Review intentionally builds property/value rows without Text or Relation
Object data (those are owned by the Text and Relation workflows). This test
covers the ``_build_review`` call chain to guard against the
``_properties()`` call-arity regression where the Review path dropped the
``property_relobj`` argument and raised:

    TypeError: OcdExportService._properties() missing 1 required
    positional argument: 'proto'
"""
import unittest

from models.engineering import Engineering
from models.engineering_class import ClassPropertyAssignment, EngineeringClass
from models.property import Property, PropertyValue
from models.snapshot import Snapshot
from services.ocd_export_service import OcdExportResult, OcdExportService


class _EngineeringClassService:
    @staticmethod
    def get_classes(snapshot):
        return snapshot.engineering.classes


class _XocdExportService:
    @staticmethod
    def _value_code_map(snapshot):
        return {"oak": "A"}

    @staticmethod
    def _value_lengths(snapshot):
        return {"finish": 1}

    @staticmethod
    def _base_codes(snapshot):
        return []

    @staticmethod
    def _group_token_by_base(snapshot, classes):
        return {}


class _MaterialPickingService:
    @staticmethod
    def prop_info_pic_prefix(snapshot, name, code):
        return ""


class _EngineeringArtbaseService:
    @staticmethod
    def build_art_base(snapshot):
        return {}


class _ReviewContext:
    engineering_class_service = _EngineeringClassService()
    xocd_export_service = _XocdExportService()
    material_picking_service = _MaterialPickingService()
    engineering_artbase_service = _EngineeringArtbaseService()


def _review_snapshot() -> Snapshot:
    finish = Property(id="finish", name="Finish")
    finish.values = [PropertyValue(id="oak", property_id="finish", value="Oak", code="A")]

    engineering_class = EngineeringClass(id="cls-1", name="Article")
    engineering_class.properties = [
        ClassPropertyAssignment(property_id="finish", property_name="Finish"),
    ]

    return Snapshot(
        properties=[finish],
        property_values=list(finish.values),
        engineering=Engineering(classes=[engineering_class]),
    )


class ReviewExportPathTests(unittest.TestCase):
    def test_build_review_generates_property_rows_without_relobj_argument(self):
        snapshot = _review_snapshot()
        service = OcdExportService(_ReviewContext())
        protos = {
            table: {}
            for table in (
                "tCOMd_CodeScheme", "tCOMd_Class", "tCOMd_Property",
                "tCOMd_PropValue", "tCOMd_Article", "tCOMd_ArticleClass",
                "tCOMd_ArtBase",
            )
        }
        result = OcdExportResult()

        sequence = service._build_review(
            snapshot, package_id=1, comgroup_id=1, series_id="S1",
            protos=protos, result=result,
        )

        tables = dict(sequence)
        self.assertEqual(len(tables["tCOMd_Property"]), 1)
        self.assertEqual(tables["tCOMd_Property"][0]["com_PropName"], "Finish")
        self.assertIsNone(tables["tCOMd_Property"][0]["com_RelObjID"])


if __name__ == "__main__":
    unittest.main()
