"""Maintenance: the released MDB base article length is authoritative."""
from core.application_context import ApplicationContext
from models.article import Article
from models.maintenance_snapshot import MaintenanceSnapshot
from models.snapshot import Snapshot
from services.maintenance_alignment_service import MaintenanceAlignmentService


def _snapshot(*codes: str, prefix: int | None = None) -> Snapshot:
    snapshot = Snapshot()
    snapshot.articles = [
        Article(id=f"article:{index}", product_id="product", code=code)
        for index, code in enumerate(codes, start=1)
    ]
    snapshot.article_prefix_length = (
        {article.id: prefix for article in snapshot.articles} if prefix else {}
    )
    return snapshot


def _service() -> MaintenanceAlignmentService:
    return MaintenanceAlignmentService(ApplicationContext())


def _align(pdm, mdb, repository=None):
    state = MaintenanceSnapshot(
        pdm_snapshot=pdm, repository_snapshot=repository, mdb_snapshot=mdb
    )
    return MaintenanceAlignmentService(None).align(state)


def _assert_invariant(result, mdb):
    """base_code == pdm_code[:len(mdb_code)] and base_length == len(mdb_code)."""
    mdb_by_id = {a.id: a.code for a in mdb.articles}
    for relation in result.relations:
        mdb_code = mdb_by_id[relation.mdb_article_id]
        assert relation.base_length == len(mdb_code)
        assert relation.base_code == relation.pdm_article_code[: len(mdb_code)]


# 1 / 5. MDB overrides the PDM prefix length -----------------------------------

def test_mdb_overrides_pdm_prefix_length():
    pdm = _snapshot("ABC123-RED", prefix=3)
    mdb = _snapshot("ABC123")

    MaintenanceAlignmentService.apply_released_mdb_base_lengths(pdm, mdb)
    result = _align(pdm, mdb)

    assert pdm.base_length_overrides == {"ABC123-RED": 6}
    assert result.status == "ALIGNED"
    assert result.relations[0].base_length == 6
    assert result.relations[0].base_code == "ABC123"
    _assert_invariant(result, mdb)


def test_mdb_is_authoritative_over_pdm_prefix_and_earlier_override():
    pdm = _snapshot("AER1A11AF", "AER1A11AG", prefix=3)
    pdm.base_length_overrides = {"AER1A11AF": 4}
    mdb = _snapshot("AER1A11")

    MaintenanceAlignmentService.apply_released_mdb_base_lengths(pdm, mdb)
    result = _align(pdm, mdb)

    assert pdm.base_length_overrides == {"AER1A11AF": 7, "AER1A11AG": 7}
    assert [r.base_code for r in result.relations] == ["AER1A11", "AER1A11"]
    _assert_invariant(result, mdb)


def test_mdb_base_used_even_without_pdm_prefix_length():
    pdm = _snapshot("ABC123.X")
    mdb = _snapshot("ABC123")

    result = _align(pdm, mdb)

    assert result.relations[0].base_code == "ABC123"
    _assert_invariant(result, mdb)


# 2. The real engine consumes the MDB length -----------------------------------

def test_existing_engine_uses_mdb_base_length():
    pdm = _snapshot("ABC123-RED", "ABC123-BLUE", prefix=3)
    service = _service()
    engine = service.context.engineering_reduction_service
    engine.materialize_article_sets(pdm)
    assert {s.base_length for s in pdm.article_sets} == {3}  # PDM-derived

    service.prepare_pdm_scope(pdm, _snapshot("ABC123"))

    assert {s.base_length for s in pdm.article_sets} == {6}  # MDB-derived


def test_prepare_delegates_to_engine_and_skips_it_when_nothing_changes(monkeypatch):
    service = _service()
    calls = []
    monkeypatch.setattr(
        service.context.engineering_reduction_service,
        "materialize_article_sets",
        lambda snapshot: calls.append(snapshot),
    )
    pdm = _snapshot("ABC123-RED", prefix=3)

    assert service.prepare_pdm_scope(pdm, _snapshot("ABC123")) == 1
    assert service.prepare_pdm_scope(pdm, _snapshot("ABC123")) == 0
    assert service.prepare_pdm_scope(_snapshot("NOPE-1"), _snapshot("ABC123")) == 0
    assert calls == [pdm]


# 3. Multiple PDM articles share one MDB base ----------------------------------

def test_multiple_pdm_articles_share_one_mdb_base():
    pdm = _snapshot("ABC123-RED", "ABC123-BLUE", "ABC123-GREEN", prefix=3)
    mdb = _snapshot("ABC123")

    result = _align(pdm, mdb)

    assert result.status == "ALIGNED"
    assert [r.base_code for r in result.relations] == ["ABC123"] * 3
    assert {r.mdb_article_id for r in result.relations} == {"article:1"}
    _assert_invariant(result, mdb)


# 4. Different MDB bases ---------------------------------------------------------

def test_different_mdb_bases():
    pdm = _snapshot("ABC123-RED", "ABC456-GREEN", prefix=3)
    mdb = _snapshot("ABC123", "ABC456")

    result = _align(pdm, mdb)

    assert [(r.pdm_article_code, r.base_code) for r in result.relations] == [
        ("ABC123-RED", "ABC123"),
        ("ABC456-GREEN", "ABC456"),
    ]
    _assert_invariant(result, mdb)


def test_case_insensitive_match_preserves_mdb_identity():
    pdm = _snapshot("abc123xyz")
    mdb = _snapshot("ABC123")

    relation = _align(pdm, mdb).relations[0]

    assert relation.base_code == "abc123"
    assert relation.mdb_article_code == "ABC123"
    assert relation.mdb_article_id == "article:1"


# Ambiguity and missing bases are never guessed --------------------------------

def test_nested_mdb_bases_are_unresolved_even_when_pdm_prefix_length_agrees():
    pdm = _snapshot("ABC12345", prefix=6)
    mdb = _snapshot("ABC", "ABC123")

    applied = MaintenanceAlignmentService.apply_released_mdb_base_lengths(pdm, mdb)
    result = _align(pdm, mdb)

    assert applied == 0
    assert pdm.base_length_overrides == {}
    assert result.relations == []
    assert result.unresolved_article_codes == ["ABC12345"]


def test_nested_mdb_bases_without_pdm_agreement_are_unresolved():
    pdm = _snapshot("ABC12345", prefix=4)
    mdb = _snapshot("ABC", "ABC123")

    applied = MaintenanceAlignmentService.apply_released_mdb_base_lengths(pdm, mdb)
    result = _align(pdm, mdb)

    assert applied == 0
    assert pdm.base_length_overrides == {}
    assert result.relations == []
    assert result.unresolved_article_codes == ["ABC12345"]


def test_no_released_base_is_unresolved():
    pdm = _snapshot("ABC123-RED", "XYZ999-RED", prefix=6)
    mdb = _snapshot("ABC123", "ABC123456")  # longer code does not begin XYZ/ABC123-RED

    result = _align(pdm, mdb)

    assert result.status == "PARTIAL"
    assert result.unresolved_article_codes == ["XYZ999-RED"]
    assert result.relations[0].mdb_article_code == "ABC123"


def test_alignment_state_stays_off_the_shared_snapshot():
    pdm = _snapshot("ABC123-RED")
    _align(pdm, _snapshot("ABC123"))

    assert not hasattr(pdm, "maintenance_alignment_status")
    assert not hasattr(pdm, "maintenance_article_relations")


# 7. Repository snapshot is irrelevant -----------------------------------------

def test_repository_snapshot_is_not_an_mdb_base_source():
    pdm = _snapshot("ABC123-RED", prefix=3)

    result = _align(pdm, mdb=_snapshot("OTHER"), repository=_snapshot("ABC123"))

    assert result.relations == []
    assert result.unresolved_article_codes == ["ABC123-RED"]
