"""Maintenance keeps PDM, Repository and MDB snapshots as independent objects."""
import copy

from core.application_context import ApplicationContext
from core.enums import WorkflowStep
from core.modules import WorkbenchModule, module_workflows
from models.article import Article
from models.maintenance_snapshot import (
    MaintenanceAlignment,
    MaintenanceArticleRelation,
    MaintenanceSnapshot,
)
from models.snapshot import Snapshot
from services.maintenance_alignment_service import MaintenanceAlignmentService
from services.maintenance_parity_service import MaintenanceParityService
from services.mdb_classification_service import MdbClassificationService


def _pdm() -> Snapshot:
    snapshot = Snapshot()
    snapshot.metadata.source = "PDM"
    snapshot.articles = [Article(id="pdm:1", code="AER1A11AF")]
    snapshot.article_prefix_length = {"pdm:1": 7}
    return snapshot


def _mdb(*codes: str) -> Snapshot:
    snapshot = Snapshot()
    snapshot.metadata.source = "MDB"
    snapshot.articles = [
        Article(id=f"mdb:{index}", code=code) for index, code in enumerate(codes, start=1)
    ]
    return snapshot


def _load_repository(context: ApplicationContext, imported: Snapshot) -> None:
    """Mirror RepositoryWorkspace._on_repository_extraction_finished."""
    context.register_mdb_snapshot(copy.deepcopy(imported))
    context.register_repository_snapshot(imported)
    context.activate_snapshot_source("repository")


def test_loading_mdb_does_not_replace_pdm_snapshot():
    context = ApplicationContext()
    pdm = _pdm()
    context.register_pdm_snapshot(pdm)
    assert context.active_snapshot is pdm

    context.register_mdb_snapshot(_mdb("AER1A11"))

    assert context.pdm_snapshot is pdm
    assert context.active_snapshot is pdm
    assert context.mdb_snapshot is not pdm
    assert context.repository_snapshot is None


def test_repository_load_keeps_pdm_repository_and_mdb_independent():
    context = ApplicationContext()
    pdm = _pdm()
    context.register_pdm_snapshot(pdm)

    imported = _mdb("AER1A11")
    _load_repository(context, imported)

    assert context.pdm_snapshot is pdm
    assert context.repository_snapshot is imported
    assert context.mdb_snapshot is not context.repository_snapshot
    assert context.mdb_snapshot is not context.pdm_snapshot
    # The repository source still activates the repository working snapshot.
    assert context.active_snapshot is imported

    # Editing the repository working snapshot never alters the released MDB.
    imported.articles.append(Article(id="mdb:x", code="EDITED"))
    assert [a.code for a in context.mdb_snapshot.articles] == ["AER1A11"]

    # ...and editing the released MDB never alters the repository working snapshot.
    context.mdb_snapshot.articles.append(Article(id="mdb:y", code="MDB_ONLY"))
    assert "MDB_ONLY" not in [a.code for a in context.repository_snapshot.articles]

    context.register_mdb_snapshot(None)
    assert context.pdm_snapshot is pdm
    assert context.repository_snapshot is imported


def test_maintenance_snapshot_holds_all_three_snapshots():
    pdm, repository, mdb = _pdm(), _mdb("AER1A11"), _mdb("AER1A11")
    state = MaintenanceSnapshot(
        pdm_snapshot=pdm, repository_snapshot=repository, mdb_snapshot=mdb
    )

    assert state.pdm_snapshot is pdm
    assert state.repository_snapshot is repository
    assert state.mdb_snapshot is mdb
    assert len({id(pdm), id(repository), id(mdb)}) == 3
    assert isinstance(state.alignment, MaintenanceAlignment)


def test_alignment_uses_mdb_snapshot_not_repository_snapshot():
    state = MaintenanceSnapshot(
        pdm_snapshot=_pdm(),
        repository_snapshot=_mdb("UNRELATED"),
        mdb_snapshot=_mdb("AER1A11"),
    )

    result = MaintenanceAlignmentService(None).align(state)

    assert result.status == "ALIGNED"
    assert result.relations[0].mdb_article_id == "mdb:1"
    assert result.relations[0].base_code == "AER1A11"


def test_alignment_requires_mdb_snapshot():
    state = MaintenanceSnapshot(
        pdm_snapshot=_pdm(), repository_snapshot=_mdb("AER1A11")
    )

    result = MaintenanceAlignmentService(None).align(state)

    assert not result.is_aligned
    assert result.relations == []


def test_parity_uses_mdb_snapshot_not_repository_snapshot():
    state = MaintenanceSnapshot(
        pdm_snapshot=_pdm(),
        repository_snapshot=_mdb("UNRELATED", "OTHER"),
        mdb_snapshot=_mdb("AER1A11"),
    )
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

    report = MaintenanceParityService(None).compare_loaded(state)

    assert report.passed
    articles = [d for d in report.differences if d.domain == "Articles"]
    assert [d.status for d in articles] == ["MATCH"]


def test_parity_requires_mdb_snapshot():
    state = MaintenanceSnapshot(
        pdm_snapshot=_pdm(), repository_snapshot=_mdb("AER1A11")
    )
    state.alignment = MaintenanceAlignment(status="ALIGNED")

    try:
        MaintenanceParityService(None).compare_loaded(state)
    except ValueError as error:
        assert "MDB" in str(error)
    else:
        raise AssertionError("compare_loaded must require the MDB snapshot")


def test_development_keeps_pdm_active_snapshot_behaviour():
    context = ApplicationContext()
    pdm = _pdm()
    context.register_pdm_snapshot(pdm)
    _load_repository(context, _mdb("AER1A11"))

    context.activate_snapshot_source("pdm")

    assert context.active_snapshot is pdm
    assert not MdbClassificationService.is_mdb_snapshot(context.active_snapshot)
    assert MdbClassificationService.is_mdb_snapshot(context.mdb_snapshot)


def test_bulk_update_workflow_unchanged():
    assert module_workflows(WorkbenchModule.BULK_UPDATE) == (WorkflowStep.MAINTENANCE,)


def test_development_engine_unaffected_by_loaded_mdb():
    context = ApplicationContext()
    pdm = Snapshot()
    pdm.articles = [
        Article(id="a1", product_id="p", code="ABC123-RED"),
        Article(id="a2", product_id="p", code="ABC456-GREEN"),
    ]
    pdm.article_prefix_length = {"a1": 3, "a2": 3}
    context.register_pdm_snapshot(pdm)
    _load_repository(context, _mdb("ABC123", "ABC456"))
    context.activate_snapshot_source("pdm")

    context.engineering_reduction_service.materialize_article_sets(context.active_snapshot)

    # Development keeps PDM's own prefix; the released MDB is never applied.
    assert pdm.base_length_overrides == {}
    assert {s.base_length for s in pdm.article_sets} == {3}
