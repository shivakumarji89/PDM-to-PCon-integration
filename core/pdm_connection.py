"""Switching and verifying the active PDM database.

Every PDM operation opens its own connection from ``context.config`` (nothing holds a connection open), so
the active database is exactly the configured server/database. A switch is therefore applied to the config and
then *verified* by connecting and asking SQL Server which database it is on; a failed switch restores the
previous configuration so the status never describes a database that is not in use.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PdmConnectionState:
    """What is actually known about the PDM connection."""

    server: str
    database: str
    verified: bool            # True only after a live connection reported ``database``
    message: str = ""         # reason when not verified

    @property
    def label(self) -> str:
        return f"{self.server}/{self.database}"


@dataclass(frozen=True)
class SwitchResult:
    ok: bool
    state: PdmConnectionState
    error: str = ""


def verify_connection(context) -> PdmConnectionState:
    """Connect with the current config and report the database SQL Server says it is connected to."""
    from repositories.pdm_repository import PDMRepository

    cfg = context.config
    server, database = cfg.pdm_server, cfg.pdm_database      # the target this check is about, fixed before connecting
    try:
        actual = PDMRepository(context).test_connection()
    except Exception as error:  # PDMConnectionError / PDMQueryError / driver failures
        state = PdmConnectionState(server, database, False, str(error))
    else:
        if actual.casefold() == database.casefold():
            state = PdmConnectionState(server, actual, True)
        else:
            state = PdmConnectionState(
                server, database, False, f"Connected to '{actual}' but '{database}' was requested.")
    # A check that finishes after the selection changed describes a database no longer selected; drop it.
    if state.label == f"{context.config.pdm_server}/{context.config.pdm_database}":
        context.pdm_connection_state = state
    return state


def switch_pdm_database(context, preset_name: str) -> SwitchResult:
    """Point the application at ``preset_name`` and verify it; restore the previous database on failure."""
    cfg = context.config
    previous = (cfg.pdm_server, cfg.pdm_database)
    previous_state = getattr(context, "pdm_connection_state", None)
    if not cfg.set_pdm_database(preset_name):
        state = previous_state or PdmConnectionState(*previous, False, "Not verified")
        return SwitchResult(False, state, f"Unknown PDM database: {preset_name}")
    state = verify_connection(context)
    if state.verified:
        _release_database_dependent_state(context)
        return SwitchResult(True, state)
    cfg.pdm_server, cfg.pdm_database = previous
    context.pdm_connection_state = previous_state or PdmConnectionState(*previous, False, "Not verified")
    return SwitchResult(False, context.pdm_connection_state, state.message)


def _release_database_dependent_state(context) -> None:
    """Release the previous database's repository handle and connected flag held by the PDM service."""
    from services.pdm_service import PDMService

    service = context._services.get(PDMService)
    if service is not None:
        service.disconnect()
        service._repository = None
