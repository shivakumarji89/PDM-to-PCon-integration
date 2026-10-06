from models.article import Article
from models.maintenance_snapshot import MaintenanceAlignment, MaintenanceArticleRelation, MaintenanceSnapshot
from models.property import Property
from models.relation_object import RelationObject
from models.snapshot import Snapshot
from services.maintenance_parity_service import MaintenanceParityService


def _state() -> MaintenanceSnapshot:
    pdm = Snapshot()
    pdm.articles = [Article(id="pdm:1", code="AER1A11AF")]
    mdb = Snapshot()
    mdb.articles = [Article(id="mdb:1", code="AER1A11")]
    state = MaintenanceSnapshot(pdm_snapshot=pdm, mdb_import_snapshot=mdb)
    state.alignment = MaintenanceAlignment(
        status="ALIGNED",
        relations=[
            MaintenanceArticleRelation(
                pdm_article_id="pdm:1",
                pdm_article_code="AER1A11AF",
                mdb_article_id="mdb:1",
                mdb_article_code="AER1A11",
                base_code="AER1A11",
                base_length=7,
            )
        ],
    )
    return state


def test_maintenance_parity_article_identity_uses_released_base():
    service = MaintenanceParityService(None)
    assert service._maintenance_article_keys(_state()) == {"aer1a11": ""}

def test_loaded_maintenance_comparison_uses_mdb_import_snapshot():
    service = MaintenanceParityService(None)
    report = service.compare_loaded(_state())

    assert report.passed
    assert report.match_count == 1
    assert report.differences[0].domain == "Articles"
    assert report.differences[0].status == "MATCH"


def test_loaded_maintenance_reports_pdm_properties_and_relations_missing_from_mdb():
    state = _state()
    state.pdm_snapshot.properties = [
        Property(id="pdm:property", code="P1", name="Property X")
    ]
    state.pdm_snapshot.relation_objects = [
        RelationObject(name="Relation Z", body="P1 == 1")
    ]

    report = MaintenanceParityService(None).compare_loaded(state)

    missing = {
        (item.domain, item.key)
        for item in report.differences
        if item.status == "MISSING"
    }
    assert ("Properties", "p1") in missing
    assert ("Relation Objects", "relation z||1|c") in missing
