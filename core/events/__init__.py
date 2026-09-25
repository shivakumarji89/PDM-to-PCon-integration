"""Reusable application event infrastructure.

Exposes a generic :class:`~core.events.bus.EventBus` and the :class:`~core.
events.bus.AppEvent` base. Any service can publish its own ``AppEvent``
subclasses through a shared bus; the Activity framework is the first consumer.
"""
from __future__ import annotations

from core.events.bus import AppEvent, EventBus

__all__ = ["AppEvent", "EventBus"]
