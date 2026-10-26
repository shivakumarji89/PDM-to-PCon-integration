"""Database boundary for the SyteLine export pipeline.

The legacy exporter holds five SqlConnections open for the whole run
(``sqlConnection``..``sqlConnection5``) and executes concatenated SQL on them.
The port keeps the *connection names* (SQL such as ``SELECT ... INTO #temptable``
is session scoped) but binds every value as a parameter.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Protocol, Sequence
from threading import RLock

from core.cancellation import checkpoint


class ExportDb(Protocol):
    """What the pipeline needs from the database. Rows are dicts keyed by column name."""

    def query(
        self, conn: str, sql: str, params: Sequence[Any] = (), *, stage: str = ""
    ) -> list[dict[str, Any]]:
        """Run a SELECT/EXEC on the named session and return all rows ([] for an empty result set).

        Raises RuntimeError if the statement yields no result set (a missing result set is an
        error, an empty one is not).
        """

    def execute(self, conn: str, sql: str, params: Sequence[Any] = (), *, stage: str = "") -> int:
        """Run a non-query statement and return the affected row count."""

    def close(self) -> None:
        """Close every session."""


class PyodbcExportDb:
    """pyodbc implementation. Sessions are opened lazily per name and closed together."""

    def __init__(
        self,
        connection_factory: Callable[[], Any],
        *,
        timeout_seconds: int = 900,
        session_factories: Mapping[str, Callable[[], Any]] | None = None,
    ) -> None:
        self._factory = connection_factory
        self._session_factories = dict(session_factories or {})
        self._timeout = timeout_seconds
        self._sessions: dict[str, Any] = {}
        self._active_lock = RLock()
        self._active_cursor = None

    def cancel_active_operation(self) -> None:
        """Best-effort Cursor.cancel; unsupported drivers finish cooperatively."""
        with self._active_lock:
            if self._active_cursor is not None:
                try:
                    self._active_cursor.cancel()
                except Exception:
                    pass

    def _activate(self, cursor) -> None:
        with self._active_lock:
            checkpoint()
            self._active_cursor = cursor

    def _close_cursor(self, cursor) -> None:
        with self._active_lock:
            if self._active_cursor is cursor:
                self._active_cursor = None
            cursor.close()

    def _session(self, name: str):
        checkpoint()
        connection = self._sessions.get(name)
        if connection is None:
            connection = self._session_factories.get(name, self._factory)()
            # The legacy SqlConnections run in autocommit mode; keeping the same avoids holding
            # an implicit transaction (and its locks) open for the whole export.
            try:
                connection.autocommit = True
            except Exception:  # driver without autocommit support: fall back to explicit commit
                pass
            self._sessions[name] = connection
        checkpoint()
        return connection

    def query(self, conn, sql, params=(), *, stage=""):
        checkpoint()
        cursor = self._session(conn).cursor()
        try:
            cursor.timeout = self._timeout
            self._activate(cursor)
            checkpoint()
            cursor.execute(sql, *params)
            checkpoint()
            # A procedure without SET NOCOUNT ON yields row-count results before its SELECT;
            # ADO.NET ExecuteReader skips them, so advance to the first real result set.
            while cursor.description is None and cursor.nextset():
                checkpoint()
            if cursor.description is None:
                raise RuntimeError(f"[stage {stage}] statement returned no result set")
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            checkpoint()
            result = []
            for row in rows:
                checkpoint()
                result.append(dict(zip(columns, row)))
            return result
        except Exception:
            checkpoint()
            raise
        finally:
            try:
                self._close_cursor(cursor)
            except Exception:  # cursor already invalid; the session is closed in close()
                pass

    def execute(self, conn, sql, params=(), *, stage=""):
        checkpoint()
        connection = self._session(conn)
        cursor = connection.cursor()
        try:
            cursor.timeout = self._timeout
            self._activate(cursor)
            checkpoint()
            cursor.execute(sql, *params)
            count = cursor.rowcount
            connection.commit()
            return count
        except Exception:
            checkpoint()
            raise
        finally:
            try:
                self._close_cursor(cursor)
            except Exception:
                pass

    def close(self) -> None:
        sessions, self._sessions = self._sessions, {}
        for connection in sessions.values():
            try:
                connection.close()
            except Exception:
                pass


class ScriptedExportDb:
    """Deterministic test double. ``script`` maps a SQL substring to rows (or a callable)."""

    def __init__(self, script: Mapping[str, Any] | None = None) -> None:
        self.script = dict(script or {})
        self.calls: list[tuple[str, str, tuple, str]] = []
        self.closed = False

    def _lookup(self, conn: str, sql: str, params: tuple):
        for needle, result in self.script.items():
            if needle in sql:
                return result(conn, sql, params) if callable(result) else result
        raise AssertionError(f"Unscripted SQL: {sql[:200]!r}")

    def query(self, conn, sql, params=(), *, stage=""):
        self.calls.append((conn, sql, tuple(params), stage))
        result = self._lookup(conn, sql, tuple(params))
        if result is None:
            raise RuntimeError(f"[stage {stage}] statement returned no result set")
        return [dict(row) for row in result]

    def execute(self, conn, sql, params=(), *, stage=""):
        self.calls.append((conn, sql, tuple(params), stage))
        result = self._lookup(conn, sql, tuple(params))
        return result if isinstance(result, int) and not isinstance(result, bool) else 0

    def close(self) -> None:
        self.closed = True
