"""Owner-Metatype selection: unique / multiple / none states, explicit choice, dialog and page cancel behaviour.

Synthetic fixtures only; nothing is written to a repository.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QDialog

from core.application_context import ApplicationContext
from core.config import AppConfig
from services.metatype.owner_selection import OwnerSelection, OwnerState, build_owner_choice, validate_owner_choice
from tests.test_metatype_write_contract import HEADER, K2, make_series
from ui.pages.metatype_owner_dialog import OwnerSelectionDialog

ROWS = "MT_A;hmx;test;ART1;C1;\nMT_A;hmx;test;ART2;C2;\nMT_B;hmx;test;ART3;C3;\nMT_C;hmx;test;ART4;C4;\n"
TYPES = "MT_A;GType;;T;0;\nMT_B;GType;;T;0;\nMT_B;GNew;;T;0;\n"       # MT_C owns nothing; MT_B already has GNew


@pytest.fixture
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "hmx"
    path.mkdir()
    return path


def reconcile(root):
    make_series(root, articles=HEADER + ROWS, types=TYPES)
    return ApplicationContext(AppConfig(metatype_repository_root=str(root))).metatype_article_service.reconcile(
        "demo", root=root)


def test_unique_owner_needs_no_choice(root):
    choice = build_owner_choice(reconcile(root), ["ART1", "ART2"], "GNew")
    assert choice.state is OwnerState.UNIQUE and OwnerSelection(choice).owner == "MT_A"
    assert choice.candidates[0].listed_articles == ("ART1", "ART2") and choice.candidates[0].total_articles == 2


def test_multiple_candidates_are_never_auto_selected(root):
    choice = build_owner_choice(reconcile(root), ["ART1", "ART3"], "GNew")
    selection = OwnerSelection(choice, "GNew")
    assert choice.state is OwnerState.MULTIPLE and [c.metatype_id for c in choice.candidates] == ["MT_A", "MT_B"]
    assert selection.owner is None and not selection.complete                # first candidate NOT taken
    assert "ART1" in choice.candidates[0].evidence() and "go_types" in choice.candidates[0].evidence()


def test_explicit_selection_is_validated_against_articles_and_property(root):
    selection = OwnerSelection(build_owner_choice(reconcile(root), ["ART1", "ART3"], "GNew"), "GNew")
    assert [i.code for i in selection.select("MT_C")] == ["NOT_A_CANDIDATE"] and selection.owner is None
    assert [i.code for i in selection.select("MT_B")] == ["PROPERTY_EXISTS"] and selection.owner is None
    assert not selection.select("MT_A") or selection.owner == "MT_A"
    assert selection.owner == "MT_A"
    assert [i.code for i in validate_owner_choice(selection.choice, "")] == ["NO_SELECTION"]


def test_new_articles_with_candidates_require_choice_and_warn(root):
    choice = build_owner_choice(reconcile(root), ["ART1", "BRAND_NEW"], "GNew")
    assert choice.state is OwnerState.MULTIPLE and [c.metatype_id for c in choice.candidates] == ["MT_A"]
    issues = validate_owner_choice(choice, "MT_A")
    assert [i.code for i in issues] == ["NEW_ARTICLES"] and all(i.severity == "warning" for i in issues)


def test_owner_without_go_types_rows_is_an_error(root):
    choice = build_owner_choice(reconcile(root), ["ART1", "ART4"], "GNew")
    assert [i.code for i in validate_owner_choice(choice, "MT_C")] == ["OWNER_WITHOUT_GO_TYPES"]


def test_no_valid_candidate_state(root):
    rec = reconcile(root)
    for articles in ([], ["ONLY_NEW"]):
        choice = build_owner_choice(rec, articles, "GNew")
        assert choice.state is OwnerState.NONE and choice.candidates == ()
        assert [i.code for i in validate_owner_choice(choice, "MT_A")] == ["NO_CANDIDATES"]
    assert build_owner_choice(None, ["ART1"]).state is OwnerState.NONE


def test_dialog_preselects_nothing_and_gates_ok(qapp, root):
    choice = build_owner_choice(reconcile(root), ["ART1", "ART3"], "GNew")
    dialog = OwnerSelectionDialog(choice)
    from PySide6.QtWidgets import QDialogButtonBox
    ok = dialog.buttons.button(QDialogButtonBox.StandardButton.Ok)
    assert dialog.candidates.count() == 2 and dialog.selected_id is None and not ok.isEnabled()
    assert "Several candidate" in dialog.state_label.text()
    assert dialog.select_candidate("MT_B") and not ok.isEnabled()               # PROPERTY_EXISTS blocks
    assert "PROPERTY_EXISTS" in dialog.feedback.toPlainText()
    assert dialog.select_candidate("MT_A") and ok.isEnabled() and dialog.selected_id == "MT_A"


def test_dialog_for_no_candidates_can_never_be_accepted(qapp, root):
    dialog = OwnerSelectionDialog(build_owner_choice(reconcile(root), ["ONLY_NEW"], "GNew"))
    from PySide6.QtWidgets import QDialogButtonBox
    assert "No valid candidate" in dialog.state_label.text() and dialog.candidates.count() == 0
    assert not dialog.buttons.button(QDialogButtonBox.StandardButton.Ok).isEnabled()


class _Fake:
    def __init__(self, pick):
        self.pick = pick

    def __call__(self, choice, parent):
        self.choice = choice
        return self

    def exec(self):
        return QDialog.DialogCode.Accepted if self.pick else QDialog.DialogCode.Rejected

    @property
    def selected_id(self):
        return self.pick


def test_page_cancel_preserves_pending_edits_and_selects_nothing(qapp, root, monkeypatch):
    from ui.pages.metatype_creation_page import MetatypeCreationPage
    make_series(root, articles=HEADER + ROWS, types=TYPES)
    page = MetatypeCreationPage(ApplicationContext(AppConfig(metatype_repository_root=str(root))))
    page.series_combo.setCurrentIndex(page.series_combo.findData("demo"))
    page.load_series()
    session = page.articles_session
    assert session.set_value(K2, "id", "MT_B") and session.pending_count == 1
    monkeypatch.setattr(page, "_owner_articles", lambda: ["ART1", "ART3"])
    selection = page.choose_owner(dialog_factory=_Fake(None))                    # user cancels
    assert selection.owner is None and session.pending_count == 1 and session.value(K2, "id") == "MT_B"
    assert "none selected" in page.articles_owner_label.text()
    selection = page.choose_owner(dialog_factory=_Fake("MT_A"))                  # explicit choice
    assert selection.owner == "MT_A" and "explicitly selected" in page.articles_owner_label.text()
    assert page.choose_owner(dialog_factory=_Fake(None)).owner == "MT_A"         # a later cancel keeps it
    monkeypatch.setattr(page, "_owner_articles", lambda: ["ART1", "ART2"])
    page.choose_owner(dialog_factory=_Fake(None))
    assert "unique" in page.articles_owner_label.text() and session.pending_count == 1
