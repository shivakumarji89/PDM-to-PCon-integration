"""Explicit confirmation of the MDB workspace type for a legacy export session.

A session file saved before ``attached_existing`` existed does not say whether its MDB is an existing
production workspace or a freshly initialized template copy. That is never guessed: every incremental
export entry point calls :func:`ensure_workspace_type_known` before it may read-preview or write, so the
user's answer is recorded once through ``MdbExportSessionService.declare_attachment`` and reused by
every later stage (and after a restart, because it lives in the session file).
"""
from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QMessageBox, QWidget

TITLE = "Confirm MDB Workspace Type"
MESSAGE = (
    "This export session was created by an earlier version of MK Product Workbench. "
    "The application cannot determine whether its MDB is an existing production workspace "
    "or a newly initialized template workspace.\n\n"
    "Please confirm the correct workspace type before continuing."
)
EXISTING_LABEL = "Existing Production Workspace"
TEMPLATE_LABEL = "Newly Initialized Template Workspace"
CANCEL_LABEL = "Cancel"


def is_legacy_session(session: Any) -> bool:
    """True when the session does not record whether its MDB is attached (unknown, never guessed)."""
    return session is not None and not bool(getattr(session, "attached_flag_known", True))


def ask_workspace_type(parent: QWidget | None) -> bool | None:
    """Show the dialog. ``True`` = existing production, ``False`` = template, ``None`` = cancelled.

    Neither answer is the default: Enter and Escape both map to Cancel.
    """
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(TITLE)
    box.setText(MESSAGE)
    existing = box.addButton(EXISTING_LABEL, QMessageBox.ButtonRole.AcceptRole)
    template = box.addButton(TEMPLATE_LABEL, QMessageBox.ButtonRole.AcceptRole)
    cancel = box.addButton(CANCEL_LABEL, QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel)
    box.setEscapeButton(cancel)
    box.exec()
    clicked = box.clickedButton()
    if clicked is existing:
        return True
    if clicked is template:
        return False
    return None


def ensure_workspace_type_known(
    parent: QWidget | None, sessions: Any, session: Any, title: str = TITLE,
) -> bool:
    """True when the export may continue (flag already known, or the user just declared it).

    Cancel records nothing and returns False; a failed save is reported and returns False. A known
    session is returned untouched and never re-asked.
    """
    if not is_legacy_session(session):
        return True
    answer = ask_workspace_type(parent)
    if answer is None:
        return False
    try:
        sessions.declare_attachment(session, answer)
    except Exception as exc:
        QMessageBox.critical(
            parent, title,
            f"The workspace type could not be saved, so the export was stopped:\n\n{exc}",
        )
        return False
    return True
