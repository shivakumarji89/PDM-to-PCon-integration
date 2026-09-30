from models.article import Article
from models.maintenance_snapshot import MaintenanceAlignment, MaintenanceArticleRelation, MaintenanceSnapshot
from models.snapshot import Snapshot
from services.maintenance_parity_service import MaintenanceParityService


def _state() -> MaintenanceSnapshot:
    pdm = Snapshot()
    pdm.articles = [Article(id="pdm:1", code="AER1A11AF")]
    repository = Snapshot()
    repository.articles = [Article(id="mdb:1", code="AER1A11")]
    state = MaintenanceSnapshot(pdm_snapshot=pdm, repository_snapshot=repository)
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
