"""Reusable application event bus.

A lightweight, generic publish/subscribe mechanism that any service can use to
publish typed events. It is intentionally domain-agnostic: it knows nothing
about activities, loading, generation, etc. Services define their own
:class:`AppEvent` subclasses and publish them here; consumers subscribe by event
type. The Activity framework is the first consumer, and future services reuse
the same bus without any redesign.

Threading: a single Qt signal marshals every published event onto the bus's
own thread, so an event published from a worker thread is dispatched to
subscribers on the bus's (typically UI) thread. Only :mod:`PySide6.QtCore` is
used - no widgets.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Type, TypeVar

from PySide6.QtCore import QObject, Signal


@dataclass(frozen=True)
class AppEvent:
    """Marker base class for all application events.

    Subclass this (as a frozen dataclass) to define a concrete event with its
    payload. Immutability keeps published events safe to share across threads
    and consumers.
    """


E = TypeVar("E", bound=AppEvent)


class EventBus(QObject):
    """Generic, thread-aware publish/subscribe hub for :class:`AppEvent`.

    Not a singleton - construct it and inject it where needed (e.g. a single
    application-wide bus provided through the application context).
    """

    # Internal marshalling channel: every published event flows through here so
    # dispatch happens on the bus's thread regardless of the publisher's thread.
    _published = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._subscribers: list[tuple[type, Callable]] = []
        self._published.connect(self._dispatch)

    def subscribe(
        self, callback: Callable[[E], None], event_type: Type[E] = AppEvent
    ) -> Callable[[E], None]:
        """Register ``callback`` for ``event_type`` (matches subclasses too).

        Subscribing with the default ``AppEvent`` receives every event. Returns
        the callback so callers can keep a reference for :meth:`unsubscribe`.
        """
        self._subscribers.append((event_type, callback))
        return callback

    def unsubscribe(self, callback: Callable) -> None:
        """Remove a previously registered ``callback`` (all its subscriptions)."""
        self._subscribers = [
            (etype, cb) for (etype, cb) in self._subscribers if cb is not callback
        ]

    def publish(self, event: AppEvent) -> None:
        """Publish ``event``; dispatched on the bus's thread (thread-safe)."""
        self._published.emit(event)

    # -- internals ---------------------------------------------------------
    def _dispatch(self, event: AppEvent) -> None:
        for event_type, callback in list(self._subscribers):
            if isinstance(event, event_type):
                callback(event)
