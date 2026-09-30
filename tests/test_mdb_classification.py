from models.engineering import Engineering
from models.engineering_class import ClassPropertyAssignment, EngineeringClass
from models.snapshot import Snapshot
from services.mdb_classification_service import MdbClassificationService


def test_mdb_classification_suggests_explicit_name_tokens():
    assert MdbClassificationService.suggest("ALWAYS_ATTR_CHAIR") == "Attribute"
    assert MdbClassificationService.suggest("ALWAYS_ATTRIBUTE_LOUNGE") == "Attribute"
    assert MdbClassificationService.suggest("ALWAYS_OPT") == "Option"
    assert MdbClassificationService.suggest("ALWAYS_OPTION_STOOL") == "Option"
    assert MdbClassificationService.suggest("GRAPHIC_LABELS") == "Misc"
    assert MdbClassificationService.suggest("SOMETHING_UNKNOWN") == "Unclassified"


def test_mdb_classification_is_token_based_not_substring_based():
    assert MdbClassificationService.suggest("OPTIONAL_FEATURE") == "Unclassified"
    assert MdbClassificationService.suggest("ATTRIBUTELESS") == "Unclassified"


def test_mdb_classification_returns_property_ids_for_class_type():
    snapshot = Snapshot()
    snapshot.metadata.source = "MDB"
    attr = EngineeringClass(id="mdb:class:1", name="ALWAYS_ATTR")
    attr.properties.append(
        ClassPropertyAssignment(property_id="mdb:property:1")
    )
    option = EngineeringClass(id="mdb:class:2", name="ALWAYS_OPT")
    option.properties.append(
        ClassPropertyAssignment(property_id="mdb:property:2")
    )
    snapshot.engineering = Engineering(classes=[attr, option])
    snapshot.mdb_class_types = {
        "mdb:class:1": "Attribute",
        "mdb:class:2": "Option",
    }

    assert MdbClassificationService.property_ids_for_type(snapshot, "Attribute") == {
        "mdb:property:1"
    }
    assert MdbClassificationService.property_ids_for_type(snapshot, "Option") == {
        "mdb:property:2"
    }
