"""Statistics engine.

Small reusable helpers for the aggregate statistics every workspace computes
(totals, averages, duplicate detection, missing-data counts). Keeps the
per-workspace statistics services thin and consistent.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Iterable


def average(total: int, count: int) -> float:
    """Safe average that returns 0.0 when there is nothing to divide by."""
    return (total / count) if count else 0.0


def count_where(items: Iterable[Any], predicate: Callable[[Any], bool]) -> int:
    """Count items matching a predicate."""
    return sum(1 for item in items if predicate(item))


def duplicate_keys(items: Iterable[Any], key: Callable[[Any], Any]) -> list[Any]:
    """Return the sorted set of keys that occur more than once.

    Falsy keys are ignored so empty codes/names do not register as duplicates.
    """
    counts = Counter(key(item) for item in items)
    return sorted(k for k, n in counts.items() if k and n > 1)


def duplicate_count(items: Iterable[Any], key: Callable[[Any], Any]) -> int:
    """Return the number of items that belong to a duplicated key group."""
    counts = Counter(key(item) for item in items)
    return sum(n for k, n in counts.items() if n > 1)
