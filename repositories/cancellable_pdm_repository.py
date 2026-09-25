from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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

    def __init__(self, context, operation_control, lookup_cache=None) -> None:
        super().__init__(context)
        self._control = operation_control
        self._lookup_cache = lookup_cache if lookup_cache is not None else {}
        self._active_lock = RLock()
        self._active_cursor = None
        self._active_connection = None
        self.last_skipped_option_items: list[str] = []
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

    def fetch_item_base_prices(
        self, items, currency, mydate, connection=None, site_id=1
    ) -> list[Any]:
        """Reuse completed OBX base-price lookups and query only missing items."""
        cache = self._lookup_cache.setdefault("base_price", {})
        vals = [str(i) for i in items if i]
        missing = []
        for item in vals:
            key = (item, (currency or "").strip().upper(), mydate or "", int(site_id) if site_id is not None else None)
            if key not in cache:
                missing.append(item)
        if missing:
            rows = super().fetch_item_base_prices(
                missing, currency, mydate, connection=connection, site_id=site_id
            )
            by_item = {}
            for row in rows:
                by_item.setdefault(str(row.Item), []).append(row)
            for item in missing:
                key = (item, (currency or "").strip().upper(), mydate or "", int(site_id) if site_id is not None else None)
                cache[key] = by_item.get(item, [])
        out = []
        for item in vals:
            key = (item, (currency or "").strip().upper(), mydate or "", int(site_id) if site_id is not None else None)
            out.extend(cache.get(key, []))
        return out

    def fetch_item_option_increment_prices(
        self, items, currency, mydate, site_id, connection=None
    ) -> list[Any]:
        """Reuse completed per-item option-price procedure results for OBX."""
        cache = self._lookup_cache.setdefault("option_increment", {})
        vals = [str(i) for i in items if i]
        missing = []
        for item in vals:
            key = (item, (currency or "").strip().upper(), mydate or "", int(site_id) if site_id is not None else None)
            if key not in cache:
                missing.append(item)
        self.last_skipped_option_items = []
        if missing:
            # Keep the existing PDM stored-procedure call and result semantics.
            # Each worker processes its assigned items independently so one
            # failed article can be recorded and retried without discarding the
            # other articles in that worker.
            worker_count = min(2, len(missing))
            chunks = [
                missing[index::worker_count]
                for index in range(worker_count)
                if missing[index::worker_count]
            ]

            def fetch_chunk(chunk):
                worker_repo = CancellablePDMRepository(
                    self.context,
                    self._control,
                    self._lookup_cache,
                )
                worker_conn = worker_repo.get_connection()
                successful_rows = []
                skipped_items = []
                try:
                    for item in chunk:
                        try:
                            item_rows = PDMRepository.fetch_item_option_increment_prices(
                                worker_repo,
                                [item],
                                currency,
                                mydate,
                                site_id,
                                connection=worker_conn,
                            )
                            successful_rows.extend(item_rows)
                        except Exception:
                            skipped_items.append(item)
                    return successful_rows, skipped_items
                finally:
                    worker_conn.close()
                    self._control.unregister_cancel_handler(
                        worker_repo.cancel_active_operation
                    )

            rows = []
            if worker_count > 1:
                with ThreadPoolExecutor(
                    max_workers=worker_count,
                    thread_name_prefix="obx-pdm-option",
                ) as executor:
                    for chunk_rows, chunk_skipped in executor.map(fetch_chunk, chunks):
                        rows.extend(chunk_rows)
                        self.last_skipped_option_items.extend(chunk_skipped)
            else:
                rows, self.last_skipped_option_items = fetch_chunk(missing)

            by_item = {}
            for row in rows:
                by_item.setdefault(str(row.Item), []).append(row)
            for item in missing:
                key = (item, (currency or "").strip().upper(), mydate or "", int(site_id) if site_id is not None else None)
                cache[key] = by_item.get(item, [])
        out = []
        for item in vals:
            key = (item, (currency or "").strip().upper(), mydate or "", int(site_id) if site_id is not None else None)
            out.extend(cache.get(key, []))
        return out

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
