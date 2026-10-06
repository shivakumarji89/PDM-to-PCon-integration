"""PDM, MDB Import, and MDB Export snapshot ownership tests."""

from core.application_context import ApplicationContext
from core.enums import WorkflowStep
from core.modules import WorkbenchModule, module_workflows, snapshot_source_for_module
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


def _load_mdb_import(context: ApplicationContext, imported: Snapshot) -> None:
    """Mirror the single-snapshot MDB import registration."""
    context.register_mdb_import_snapshot(imported)


def test_application_context_exposes_independent_snapshot_roles():
    context = ApplicationContext()

    assert context.pdm_snapshot is None
    assert context.mdb_import_snapshot is None
    assert context.mdb_export_snapshot is None
    assert context.qa_snapshot is None
    assert not hasattr(context, "repository_snapshot")
    assert not hasattr(context, "mdb_snapshot")


def test_loading_mdb_does_not_replace_pdm_snapshot():
    context = ApplicationContext()
    pdm = _pdm()
    context.register_pdm_snapshot(pdm)
    assert context.active_snapshot is pdm

    imported = _mdb("AER1A11")
    context.register_mdb_import_snapshot(imported)

    assert context.pdm_snapshot is pdm
    assert context.active_snapshot is pdm
    assert context.mdb_import_snapshot is imported
    assert context.mdb_import_snapshot is not pdm


def test_bulk_and_qa_can_activate_mdb_import_without_replacing_pdm():
    context = ApplicationContext()
    pdm = _pdm()
    context.register_pdm_snapshot(pdm)
    imported = _mdb("AER1A11")
    context.register_mdb_import_snapshot(imported)
    context.activate_snapshot_source("mdb_import")

    assert context.active_snapshot is imported
    assert context.pdm_snapshot is pdm


def test_maintenance_class_creation_uses_pdm_as_active_source():
    context = ApplicationContext()
    pdm = _pdm()
    imported = _mdb("AER1A11")
    context.register_pdm_snapshot(pdm)
    context.register_mdb_import_snapshot(imported)

    context.activate_snapshot_source(snapshot_source_for_module(WorkbenchModule.MAINTENANCE))

    assert context.active_snapshot is pdm
    assert context.mdb_import_snapshot is imported
    assert not MdbClassificationService.is_mdb_snapshot(context.active_snapshot)


def test_mdb_export_snapshot_is_a_copy_of_development_output():
    context = ApplicationContext()
    pdm = _pdm()
    imported = _mdb("AER1A11")
    context.register_pdm_snapshot(pdm)
    context.register_mdb_import_snapshot(imported)

    export = context.prepare_mdb_export_snapshot(pdm)

    assert context.mdb_export_snapshot is export
    assert export is not pdm
    assert export is not imported
    assert export.id != pdm.id
    assert [article.code for article in export.articles] == ["AER1A11AF"]
    export.articles[0].code = "EDITED"
    assert pdm.articles[0].code == "AER1A11AF"
    assert imported.articles[0].code == "AER1A11"

    context.register_pdm_snapshot(_pdm())
    assert context.mdb_export_snapshot is None


def test_qa_snapshot_is_an_independent_copy_of_mdb_import():
    context = ApplicationContext()
    pdm = _pdm()
    imported = _mdb("AER1A11")
    context.register_pdm_snapshot(pdm)
    context.register_mdb_import_snapshot(imported)
    qa = context.prepare_qa_snapshot()

    assert qa is context.qa_snapshot
    assert qa is not imported
    assert qa.id != imported.id
    assert qa.metadata.source == "QA"
    assert not MdbClassificationService.is_mdb_snapshot(qa)

    context.prepare_mdb_export_snapshot(pdm)
    qa.articles[0].code = "QA-EDITED"
    assert pdm.articles[0].code == "AER1A11AF"
    assert imported.articles[0].code == "AER1A11"
    assert context.mdb_export_snapshot.articles[0].code == "AER1A11AF"


def test_qa_snapshot_can_be_reset_and_reprepared_independently():
    context = ApplicationContext()
    context.register_mdb_import_snapshot(_mdb("AER1A11"))
    original = context.prepare_qa_snapshot()

    context.register_qa_snapshot(None)
    assert context.qa_snapshot is None

    replacement = context.prepare_qa_snapshot(_mdb("AER2B22"))
    assert replacement is context.qa_snapshot
    assert replacement is not original
    assert replacement.id != original.id
    assert [article.code for article in replacement.articles] == ["AER2B22"]
    assert [article.code for article in context.mdb_import_snapshot.articles] == ["AER1A11"]


def test_replacing_mdb_import_does_not_replace_qa_snapshot():
    context = ApplicationContext()
    context.register_mdb_import_snapshot(_mdb("AER1A11"))
    qa = context.prepare_qa_snapshot()

    context.register_mdb_import_snapshot(_mdb("AER2B22"))

    assert context.qa_snapshot is qa
    assert [article.code for article in qa.articles] == ["AER1A11"]


def test_replacing_mdb_export_does_not_replace_qa_snapshot():
    context = ApplicationContext()
    context.register_mdb_import_snapshot(_mdb("AER1A11"))
    qa = context.prepare_qa_snapshot()

    context.prepare_mdb_export_snapshot(_pdm())
    first_export = context.mdb_export_snapshot
    context.prepare_mdb_export_snapshot(_pdm())

    assert context.qa_snapshot is qa
    assert context.mdb_export_snapshot is not first_export


def test_replacing_pdm_does_not_replace_qa_snapshot():
    context = ApplicationContext()
    context.register_mdb_import_snapshot(_mdb("AER1A11"))
    qa = context.prepare_qa_snapshot()

    context.register_pdm_snapshot(_pdm())

    assert context.qa_snapshot is qa
    assert [article.code for article in qa.articles] == ["AER1A11"]


def test_maintenance_snapshot_holds_pdm_and_mdb_import_references():
    pdm, mdb_import = _pdm(), _mdb("AER1A11")
    state = MaintenanceSnapshot(
        pdm_snapshot=pdm, mdb_import_snapshot=mdb_import
    )

    assert state.pdm_snapshot is pdm
    assert state.mdb_import_snapshot is mdb_import
    assert not hasattr(state, "repository_snapshot")
    assert isinstance(state.alignment, MaintenanceAlignment)


def test_alignment_uses_mdb_import_snapshot():
    state = MaintenanceSnapshot(
        pdm_snapshot=_pdm(),
        mdb_import_snapshot=_mdb("AER1A11"),
    )

    result = MaintenanceAlignmentService(None).align(state)

    assert result.status == "ALIGNED"
    assert result.relations[0].mdb_article_id == "mdb:1"
    assert result.relations[0].base_code == "AER1A11"


def test_alignment_requires_mdb_import_snapshot():
    state = MaintenanceSnapshot(pdm_snapshot=_pdm())

    result = MaintenanceAlignmentService(None).align(state)

    assert not result.is_aligned
    assert result.relations == []


def test_parity_uses_mdb_import_snapshot():
    state = MaintenanceSnapshot(
        pdm_snapshot=_pdm(),
        mdb_import_snapshot=_mdb("AER1A11"),
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


def test_parity_requires_mdb_import_snapshot():
    state = MaintenanceSnapshot(pdm_snapshot=_pdm())
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
    _load_mdb_import(context, _mdb("AER1A11"))

    context.activate_snapshot_source("pdm")

    assert context.active_snapshot is pdm
    assert not MdbClassificationService.is_mdb_snapshot(context.active_snapshot)
    assert MdbClassificationService.is_mdb_snapshot(context.mdb_import_snapshot)


def test_bulk_update_workflow_unchanged():
    assert module_workflows(WorkbenchModule.BULK_UPDATE) == (WorkflowStep.MAINTENANCE,)


def test_development_and_maintenance_use_pdm_while_repository_modules_use_import():
    assert snapshot_source_for_module(WorkbenchModule.DEVELOPMENT) == "pdm"
    assert snapshot_source_for_module(WorkbenchModule.MAINTENANCE) == "pdm"
    assert snapshot_source_for_module(WorkbenchModule.BULK_UPDATE) == "mdb_import"
    assert snapshot_source_for_module(WorkbenchModule.QA_VALIDATION) == "mdb_import"


def test_development_engine_unaffected_by_loaded_mdb():
    context = ApplicationContext()
    pdm = Snapshot()
    pdm.articles = [
        Article(id="a1", product_id="p", code="ABC123-RED"),
        Article(id="a2", product_id="p", code="ABC456-GREEN"),
    ]
    pdm.article_prefix_length = {"a1": 3, "a2": 3}
    context.register_pdm_snapshot(pdm)
    _load_mdb_import(context, _mdb("ABC123", "ABC456"))
    context.activate_snapshot_source("pdm")

    context.engineering_reduction_service.materialize_article_sets(context.active_snapshot)

    # Development keeps PDM's own prefix; the released MDB is never applied.
    assert pdm.base_length_overrides == {}
    assert {s.base_length for s in pdm.article_sets} == {3}
