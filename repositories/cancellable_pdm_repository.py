from __future__ import annotations

from threading import RLock
from typing import Any, Sequence

from core.errors import PDMConnectionError, PDMQueryError
from repositories.pdm_repository import PDMRepository


class _TrackedCursor:
    """Proxy a pyodbc cursor so the active statement can be cancelled safely."""

    def __init__(self, cursor, owner: "CancellablePDMRepository", connection) -> None:
        self._cursor = cursor
        self._owner = owner
        self._connection = connection

    def execute(self, *args, **kwargs):
        self._owner._control.checkpoint()
        self._owner._set_active(self._cursor, self._connection)
        try:
            self._cursor.execute(*args, **kwargs)
            return self
        except Exception:
            self._owner._clear_active(self._cursor)
            raise

    def executemany(self, *args, **kwargs):
        self._owner._control.checkpoint()
        self._owner._set_active(self._cursor, self._connection)
        try:
            return self._cursor.executemany(*args, **kwargs)
        except Exception:
            self._owner._clear_active(self._cursor)
            raise

    def close(self) -> None:
        try:
            self._cursor.close()
        finally:
            self._owner._clear_active(self._cursor)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class _TrackedConnection:
    """Proxy a pyodbc connection and return tracked cursors."""

    def __init__(self, connection, owner: "CancellablePDMRepository") -> None:
        self._connection = connection
        self._owner = owner

    def cursor(self, *args, **kwargs):
        return _TrackedCursor(
            self._connection.cursor(*args, **kwargs),
            self._owner,
            self._connection,
        )

    def close(self) -> None:
        self._connection.close()

    def __getattr__(self, name):
        return getattr(self._connection, name)


class CancellablePDMRepository(PDMRepository):
    """PDMRepository variant used only by OBX validation.

    It keeps the existing PDM SQL and pricing implementation intact while
    adding a validation-control checkpoint before every SQL execute and a
    pyodbc Cursor.cancel hook for user cancellation.
    """

    def __init__(self, context, operation_control) -> None:
        super().__init__(context)
        self._control = operation_control
        self._active_lock = RLock()
        self._active_cursor = None
        self._active_connection = None
        self._control.register_cancel_handler(self.cancel_active_operation)

    def get_connection(self):
        connection = super().get_connection()
        return _TrackedConnection(connection, self)

    def _execute(
        self, query: str, params: Sequence[Any], connection: Any = None
    ) -> list[Any]:
        """Run a query with validation checkpoints and active-cursor tracking."""
        self._control.checkpoint()
        owns_connection = connection is None
        conn = self.get_connection() if owns_connection else connection
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except self._driver().Error as error:
            raise PDMQueryError(f"PDM query failed: {error}") from error
        except (PDMConnectionError, PDMQueryError):
            raise
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception:
                    pass
            if owns_connection:
                try:
                    conn.close()
                except Exception:
                    pass

    def _set_active(self, cursor, connection) -> None:
        with self._active_lock:
            self._active_cursor = cursor
            self._active_connection = connection

    def _clear_active(self, cursor) -> None:
        with self._active_lock:
            if cursor is self._active_cursor:
                self._active_cursor = None
                self._active_connection = None

    def cancel_active_operation(self) -> None:
        """Ask ODBC to cancel the currently executing statement.

        pyodbc exposes Cursor.cancel specifically for cancellation from a
        separate thread. If the driver rejects that request, close the active
        connection as a last-resort cleanup path.
        """
        with self._active_lock:
            cursor = self._active_cursor
            connection = self._active_connection

        if cursor is None:
            return

        try:
            cursor.cancel()
            return
        except Exception:
            pass

        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
