from models.article import Article
from models.maintenance_snapshot import MaintenanceSnapshot
from models.snapshot import Snapshot
from services.maintenance_alignment_service import MaintenanceAlignmentService


def _snapshot(*codes: str) -> Snapshot:
    snapshot = Snapshot()
    snapshot.articles = [
        Article(id=f"article:{index}", code=code)
        for index, code in enumerate(codes, start=1)
    ]
    snapshot.article_prefix_length = {
        article.id: len(code)
        for article, code in zip(snapshot.articles, codes)
    }
    return snapshot


def test_maintenance_alignment_does_not_mutate_shared_snapshot_alignment_fields():
    pdm = _snapshot("AER1A11AF", "ABC123X")
    pdm.article_prefix_length = {"article:1": 7, "article:2": 6}
    repository = _snapshot("AER1A11", "ABC123")
    state = MaintenanceSnapshot(pdm_snapshot=pdm, repository_snapshot=repository)

    result = MaintenanceAlignmentService(None).align(state)

    assert result.status == "ALIGNED"
    assert [r.base_code for r in result.relations] == ["AER1A11", "ABC123"]
    assert not hasattr(pdm, "maintenance_alignment_status")
    assert not hasattr(pdm, "maintenance_article_relations")


def test_maintenance_alignment_prefers_longest_released_base():
    pdm = _snapshot("ABC12345")
    pdm.article_prefix_length = {"article:1": 6}
    repository = _snapshot("ABC", "ABC123")
    state = MaintenanceSnapshot(pdm_snapshot=pdm, repository_snapshot=repository)

    result = MaintenanceAlignmentService(None).align(state)

    assert result.status == "ALIGNED"
    assert result.relations[0].base_code == "ABC123"
    assert result.relations[0].base_length == 6


def test_maintenance_alignment_keeps_unresolved_articles_explicit():
    pdm = _snapshot("AER1A11AF", "NOT_IN_MDB")
    pdm.article_prefix_length = {"article:1": 7, "article:2": 3}
    repository = _snapshot("AER1A11")
    state = MaintenanceSnapshot(pdm_snapshot=pdm, repository_snapshot=repository)

    result = MaintenanceAlignmentService(None).align(state)

    assert result.status == "PARTIAL"
    assert result.unresolved_article_ids == ["article:2"]
    assert result.unresolved_article_codes == ["NOT_IN_MDB"]
