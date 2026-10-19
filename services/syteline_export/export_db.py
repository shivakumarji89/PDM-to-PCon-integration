"""Connection factory for the SyteLine export pipeline (read-mostly PDM sessions)."""
from __future__ import annotations

from typing import Any

from repositories.pdm_repository import PDMRepository
from services.syteline_export.pipeline.db import PyodbcExportDb


def build_pdm_export_db(context: Any, trade_net_database: str = "") -> PyodbcExportDb:
    """Create the export's database sessions from the application's PDM configuration.

    Every session is a separate connection to the configured PDM database, as in the legacy
    exporter. The optional ``tradenet`` session (legacy ``sqlConnection6``) targets
    ``trade_net_database`` on the same server and is only opened if a trade-net contract is used.
    """
    repository = PDMRepository(context)
    factories = {}
    database = trade_net_database.strip()
    if database:
        if any(ch in database for ch in ";={}"):
            raise ValueError("Trade-net database name contains invalid characters.")

        def open_trade_net():
            import pyodbc

            connection_string = context.config.pdm_connection_string().replace(
                f"DATABASE={context.config.pdm_database};", f"DATABASE={database};"
            )
            return pyodbc.connect(connection_string)

        factories["tradenet"] = open_trade_net
    return PyodbcExportDb(repository.get_connection, session_factories=factories)
