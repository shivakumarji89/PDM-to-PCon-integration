"""Filtering engine.

Standardises the search / filter execution shared by the selectable
workspaces. A workspace supplies the values to search and its own extra
predicates; the engine runs the common pipeline (text match + predicates) so
each page stops re-implementing it.
"""
from __future__ import annotations

from typing import Any, Callable, Iterable


def text_match(term: str, *values: str) -> bool:
    """Return True when ``term`` is empty or contained in any value.

    Matching is case-insensitive and substring-based, mirroring the behaviour
    used by every workspace search box.
    """
    term = (term or "").strip().lower()
    if not term:
        return True
    return any(term in (value or "").lower() for value in values)


def filter_items(
    items: Iterable[Any],
    term: str,
    text_fields: Callable[[Any], tuple[str, ...]],
    predicates: Iterable[Callable[[Any], bool]] = (),
) -> list[Any]:
    """Filter items by a search term plus optional extra predicates.

    ``text_fields`` maps an item to the strings its search should match.
    ``predicates`` are additional include-tests (all must pass).
    """
    predicate_list = list(predicates)
    result: list[Any] = []
    for item in items:
        if not text_match(term, *text_fields(item)):
            continue
        if all(predicate(item) for predicate in predicate_list):
            result.append(item)
    return result
