from __future__ import annotations

from collections.abc import Callable
from threading import Event, RLock

from core.cancellation import CancellationToken, OperationCancelled, current_token

class ValidationPaused(Exception):
    """Raised when validation was paused before the next PDM operation."""


class ValidationCancelled(OperationCancelled):
    """Raised when validation was cancelled by the user."""


class ValidationControl:
    """Thread-safe pause/cancel state shared by an OBX validation run."""

    def __init__(self, cancellation_token: CancellationToken | None = None) -> None:
        self._paused = Event()
        self.cancellation_token = cancellation_token or current_token() or CancellationToken()
        self._lock = RLock()
        self._cancel_handlers: list[Callable[[], None]] = []
        self._cancel_dispatched = False

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    def cancel(self) -> None:
        with self._lock:
            if self._cancel_dispatched or not self.cancellation_token.request_cancel():
                return
            self._cancel_dispatched = True
            handlers = list(self._cancel_handlers)
        for handler in handlers:
            try:
                handler()
            except Exception:
                pass

    def is_paused(self) -> bool:
        return self._paused.is_set()

    def is_cancelled(self) -> bool:
        return self.cancellation_token.is_cancelled()

    def register_cancel_handler(self, handler: Callable[[], None]) -> None:
        with self._lock:
            if self.is_cancelled():
                handler()
                return
            if handler not in self._cancel_handlers:
                self._cancel_handlers.append(handler)

    def unregister_cancel_handler(self, handler: Callable[[], None]) -> None:
        with self._lock:
            if handler in self._cancel_handlers:
                self._cancel_handlers.remove(handler)

    def checkpoint(self) -> None:
        if self.is_cancelled():
            raise ValidationCancelled("Validation cancelled by user.")
        if self.is_paused():
            raise ValidationPaused("Validation paused by user.")
