from models.article import Article
from models.snapshot import Snapshot
from services.maintenance_alignment_service import MaintenanceAlignmentService


def _pdm(*codes: str) -> Snapshot:
    snapshot = Snapshot()
    snapshot.articles = [
        Article(id=f"pdm:{index}", code=code)
        for index, code in enumerate(codes, start=1)
    ]
    return snapshot


def _mdb(*codes: str) -> Snapshot:
    snapshot = Snapshot()
    snapshot.articles = [
        Article(id=f"mdb:article:{index}", code=code, source="MDB")
        for index, code in enumerate(codes, start=1)
    ]
    return snapshot


def test_maintenance_alignment_uses_released_mdb_base_codes_and_lengths():
    pdm = _pdm("AER1A11AF", "AER1A12AF", "ABC123X")
    mdb = _mdb("AER1A11", "ABC123")

    result = MaintenanceAlignmentService(None).align(pdm, mdb)

    assert result.status == "ALIGNED"
    assert len(result.relations) == 3
    assert pdm.article_prefix_length == {
        "pdm:1": 7,
        "pdm:2": 7,
        "pdm:3": 6,
    }
    assert pdm.base_length_overrides == {
        "AER1A11AF": 7,
        "AER1A12AF": 7,
        "ABC123X": 6,
    }
    assert pdm.maintenance_base_rules["AER1A11"]["base_length"] == 7
    assert pdm.maintenance_base_rules["ABC123"]["base_length"] == 6
    assert pdm.maintenance_article_relations["pdm:1"]["mdb_article_code"] == "AER1A11"
    assert pdm.maintenance_article_relations["pdm:2"]["base_code"] == "AER1A11"
    assert pdm.maintenance_article_relations["pdm:3"]["mdb_article_id"] == "mdb:article:2"


def test_maintenance_alignment_prefers_the_more_specific_released_base():
    pdm = _pdm("ABC12345")
    mdb = _mdb("ABC", "ABC123")

    result = MaintenanceAlignmentService(None).align(pdm, mdb)

    assert result.status == "ALIGNED"
    assert result.relations[0].base_code == "ABC123"
    assert pdm.article_prefix_length["pdm:1"] == 6


def test_maintenance_alignment_keeps_unresolved_pdm_articles_explicit():
    pdm = _pdm("AER1A11AF", "NOT_IN_RELEASED_MDB")
    mdb = _mdb("AER1A11")

    result = MaintenanceAlignmentService(None).align(pdm, mdb)

    assert result.status == "PARTIAL"
    assert result.unresolved_article_ids == ["pdm:2"]
    assert result.unresolved_article_codes == ["NOT_IN_RELEASED_MDB"]
    assert "pdm:2" not in pdm.maintenance_article_relations
