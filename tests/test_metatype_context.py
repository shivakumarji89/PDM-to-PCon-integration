"""Regression tests for the typed Metatype creation context."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from core.application_context import ApplicationContext
from core.config import AppConfig
from models.metatype_context import MetatypeCreationContext
from tests.test_metatype_creation_workflow import build


def make_context(root):
    return ApplicationContext(AppConfig(metatype_repository_root=str(root)))


def test_creation_session_contains_one_typed_context():
    from pathlib import Path
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        context = make_context(Path(tmp))
        service = context.metatype_creation_service
        assert service._state() is context.workflow_session("metatype.creation")["context"]
        assert set(context.workflow_session("metatype.creation")) == {"context"}
        assert isinstance(service._state(), MetatypeCreationContext)


def test_same_series_reload_preserves_answers_and_advances_revision(tmp_path):
    root = tmp_path / "hmx"
    root.mkdir()
    build(root)
    context = make_context(root)
    service = context.metatype_creation_service
    service.start("atlas")
    assert service.submit_property_identity("GATLAS_Surface", "Surface").accepted
    state = service._state()
    identity = service.identity
    revision = state.revision
    service.start("atlas")
    assert service.identity is identity
    assert state.revision > revision


def test_different_series_requires_explicit_discard(tmp_path):
    root = tmp_path / "hmx"
    root.mkdir()
    build(root, "atlas")
    build(root, "pullman")
    service = make_context(root).metatype_creation_service
    service.start("atlas")
    service.submit_property_identity("GATLAS_Surface", "Surface")
    status = service.start("pullman")
    assert status.series == "atlas"
    assert service.identity is not None
    assert service._state().pending_series == "pullman"
    service.discard_and_start("pullman")
    assert service.series == "pullman"
    assert service.identity is None


def test_repository_analysis_session_does_not_replace_creation_context(tmp_path):
    root = tmp_path / "hmx"
    root.mkdir()
    build(root)
    context = make_context(root)
    service = context.metatype_creation_service
    service.start("atlas")
    service.submit_property_identity("GATLAS_Surface", "Surface")
    state = service._state()
    context.workflow_session("metatype.series_inspection")["result"] = object()
    context.workflow_session("metatype.pattern_selection")["selection"] = object()
    assert service._state() is state
    assert service.identity.name == "GATLAS_Surface"
    assert service._pattern_selection().series == "atlas"


def test_identical_property_submission_does_not_increment_revision(tmp_path):
    root = tmp_path / "hmx"
    root.mkdir()
    build(root)
    service = make_context(root).metatype_creation_service
    service.start("atlas")
    first = service.submit_property_identity("GATLAS_Surface", "Surface")
    revision = service._state().revision
    second = service.submit_property_identity("GATLAS_Surface", "Surface")
    assert second.identity is first.identity
    assert service._state().revision == revision
