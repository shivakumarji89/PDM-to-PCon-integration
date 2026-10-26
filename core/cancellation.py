"""Cooperative cancellation shared by UI workers and services."""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from threading import Event, RLock
from collections.abc import Generator


class OperationCancelled(Exception):
    """The operation stopped at a safe boundary without completing."""


class CancellationToken:
    """A one-shot request; commit atomically closes the cancellation window."""

    def __init__(self) -> None:
        self._requested = Event()
        self._lock = RLock()
        self._committed = False

    def request_cancel(self) -> bool:
        with self._lock:
            if self._committed:
                return False
            self._requested.set()
            return True

    cancel = request_cancel

    def is_cancelled(self) -> bool:
        return self._requested.is_set()

    def checkpoint(self) -> None:
        if self.is_cancelled():
            raise OperationCancelled("Cancelled by user.")

    def commit(self) -> None:
        """Call immediately before an indivisible final publication/write."""
        with self._lock:
            self.checkpoint()
            self._committed = True


_current: ContextVar[CancellationToken | None] = ContextVar("cancellation", default=None)


def current_token() -> CancellationToken | None:
    return _current.get()


def checkpoint(token: CancellationToken | None = None) -> None:
    active = token if token is not None else current_token()
    if active is not None:
        active.checkpoint()


def commit() -> None:
    active = current_token()
    if active is not None:
        active.commit()


@contextmanager
def cancellation_scope(token: CancellationToken | None) -> Generator[None, None, None]:
    """Propagate a worker's token through existing synchronous service APIs."""
    reset = _current.set(token)
    try:
        checkpoint()
        yield
    finally:
        _current.reset(reset)
