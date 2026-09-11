from __future__ import annotations

from threading import Event, RLock

from core.errors import PDMValidationCancelled, PDMValidationPaused


class ValidationControl:
    """Thread-safe pause/cancel state shared by an OBX validation run."""

    def __init__(self) -> None:
        self._paused = Event()
        self._cancelled = Event()
        self._lock = RLock()
        self._cancel_handlers: list[callable] = []

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    def cancel(self) -> None:
        self._cancelled.set()
        with self._lock:
            handlers = list(self._cancel_handlers)
        for handler in handlers:
            try:
                handler()
            except Exception:
                pass

    def is_paused(self) -> bool:
        return self._paused.is_set()

    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    def register_cancel_handler(self, handler) -> None:
        with self._lock:
            if handler not in self._cancel_handlers:
                self._cancel_handlers.append(handler)

    def unregister_cancel_handler(self, handler) -> None:
        with self._lock:
            if handler in self._cancel_handlers:
                self._cancel_handlers.remove(handler)

    def checkpoint(self) -> None:
        if self.is_cancelled():
            raise PDMValidationCancelled("Validation cancelled by user.")
        if self.is_paused():
            raise PDMValidationPaused("Validation paused by user.")
