"""Single authority for standard engineering class names.

Every generated class is ``{TOKEN}_{KIND}`` where ``TOKEN`` is the base article
code (or, for the legacy single-group modes, the group token) and ``KIND`` is one
of ``ATTRIBUTE`` / ``OPTION`` / ``VISUAL``. Nothing user-editable feeds the name:
no aliases, no manufacturer abbreviations.

Legacy projects carry ``<Token>_Attribute`` / ``_Options`` / ``_Visual``; those are
still *recognised* (case-insensitively, ``Options`` == ``OPTION``) so existing
classes can be migrated in place, but they are never generated any more.
"""
from __future__ import annotations

ATTRIBUTE = "attribute"
OPTION = "option"
VISUAL = "visual"
KINDS = (ATTRIBUTE, OPTION, VISUAL)

_SUFFIX = {ATTRIBUTE: "ATTRIBUTE", OPTION: "OPTION", VISUAL: "VISUAL"}
_KIND_BY_SUFFIX = {
    "attribute": ATTRIBUTE, "attr": ATTRIBUTE,
    "option": OPTION, "options": OPTION,
    "visual": VISUAL,
}


def standard_class_name(token: str, kind: str) -> str:
    """``{TOKEN}_{KIND}`` - the only place a standard class name is composed."""
    token = str(token or "").strip()
    if not token:
        raise ValueError("A class name needs a non-empty base article code / group token.")
    return f"{token}_{_SUFFIX[kind]}"


def standard_class_names(token: str) -> dict[str, str]:
    """``{kind: class name}`` for one base article code."""
    return {kind: standard_class_name(token, kind) for kind in KINDS}


def class_kind(name: str) -> str | None:
    """``attribute`` / ``option`` / ``visual`` for a standard (or legacy) class name, else None."""
    if "_" not in str(name or ""):
        return None
    return _KIND_BY_SUFFIX.get(str(name).rsplit("_", 1)[-1].strip().casefold())


def class_token(name: str) -> str:
    """The base article code / group token a standard class name was built from."""
    return str(name or "").rsplit("_", 1)[0]


def is_attribute_class(name: str) -> bool:
    return class_kind(name) == ATTRIBUTE


def is_standard_class(name: str) -> bool:
    return class_kind(name) is not None


def casefold_collisions(tokens: list[str]) -> list[tuple[str, str]]:
    """Distinct tokens that would collide in a case-insensitive MDB (class lookups casefold)."""
    seen: dict[str, str] = {}
    clashes: list[tuple[str, str]] = []
    for token in tokens:
        key = token.casefold()
        if key in seen and seen[key] != token:
            clashes.append((seen[key], token))
        seen.setdefault(key, token)
    return clashes
