"""Explicit owner-Metatype selection when ``resolve_owner_metatype`` cannot name a unique owner.

Three distinct states (never merged):

* ``UNIQUE``   - every listed article names one Metatype; nothing to choose, the owner is that id.
* ``MULTIPLE`` - several candidate Metatypes (the listed articles name different ones, or some listed
  articles are new while the existing ones name candidates). The user must choose; the first candidate is
  **never** selected automatically.
* ``NONE``     - no candidate Metatype can be derived (no articles, no metatypeid role, only new articles).
  Nothing can be chosen; the owner decision is reported as blocked.

A choice is validated against the articles and the property being created: it must be one of the
candidates, must own go_types rows when go_types was read (warning when it was not), and must not already
define the property (documented uniqueness of (Metatype, property); error). Pure and read-only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from models.metatype_articles import ArticleReconciliation
from services.metatype.owner_resolution import OwnerResolution, resolve_owner_metatype


class OwnerState(str, Enum):
    UNIQUE = "unique"
    MULTIPLE = "multiple"
    NONE = "none"


@dataclass(frozen=True)
class Candidate:
    metatype_id: str
    listed_articles: tuple[str, ...]      # listed articles that name this Metatype
    total_articles: int                   # all go_articles rows naming it
    has_go_types_rows: bool | None        # None = go_types not read
    defines_property: bool | None         # None = go_types not read / no property given

    def evidence(self) -> str:
        parts = [f"named by listed article(s): {', '.join(self.listed_articles) or '(none)'}",
                 f"{self.total_articles} go_articles row(s) use it"]
        if self.has_go_types_rows is not None:
            parts.append("owns go_types rows" if self.has_go_types_rows else "has NO go_types rows")
        if self.defines_property:
            parts.append("ALREADY defines the property")
        return "; ".join(parts)


@dataclass(frozen=True)
class OwnerChoice:
    state: OwnerState
    resolution: OwnerResolution
    candidates: tuple[Candidate, ...] = ()
    explanation: str = ""


@dataclass(frozen=True)
class OwnerIssue:
    severity: str    # "error" | "warning"
    code: str
    message: str


@dataclass
class OwnerSelection:
    """Holds the state; ``selected`` is only ever set by an explicit :meth:`select`."""
    choice: OwnerChoice
    property_name: str = ""
    selected: str | None = None
    issues: list[OwnerIssue] = field(default_factory=list)

    @property
    def owner(self) -> str | None:
        """The owner to use: the unique one, or the validated explicit selection, else ``None``."""
        if self.choice.state is OwnerState.UNIQUE:
            return self.choice.resolution.metatype_id
        return self.selected

    @property
    def complete(self) -> bool:
        return self.owner is not None

    def select(self, metatype_id: str) -> list[OwnerIssue]:
        """Validate and record an explicit selection. An invalid one leaves ``selected`` unchanged."""
        self.issues = validate_owner_choice(self.choice, metatype_id)
        if not any(i.severity == "error" for i in self.issues):
            self.selected = metatype_id
        return self.issues

    def clear(self) -> None:
        self.selected = None
        self.issues = []


def build_owner_choice(result: ArticleReconciliation | None, articles, property_name: str = "") -> OwnerChoice:
    resolution = resolve_owner_metatype(result, articles)
    wanted = [a.strip(" \t") for a in articles if a.strip(" \t")]
    if resolution.resolved:
        return OwnerChoice(OwnerState.UNIQUE, resolution,
                           (_candidate(result, resolution.metatype_id, wanted, property_name),),
                           f"All listed articles belong to {resolution.metatype_id}.")
    if not resolution.candidates:
        return OwnerChoice(OwnerState.NONE, resolution, (), resolution.reason + " No candidate Metatype exists.")
    candidates = tuple(_candidate(result, m, wanted, property_name) for m in resolution.candidates)
    return OwnerChoice(OwnerState.MULTIPLE, resolution, candidates, resolution.reason)


def validate_owner_choice(choice: OwnerChoice, metatype_id: str) -> list[OwnerIssue]:
    if choice.state is OwnerState.NONE:
        return [OwnerIssue("error", "NO_CANDIDATES", "No valid candidate Metatype exists; nothing can be selected.")]
    if not metatype_id:
        return [OwnerIssue("error", "NO_SELECTION", "Select one Metatype explicitly.")]
    found = next((c for c in choice.candidates if c.metatype_id == metatype_id), None)
    if found is None:
        return [OwnerIssue("error", "NOT_A_CANDIDATE",
                           f"{metatype_id} is not a candidate derived from the listed articles "
                           f"({', '.join(c.metatype_id for c in choice.candidates)}).")]
    issues: list[OwnerIssue] = []
    if found.has_go_types_rows is False:
        issues.append(OwnerIssue("error", "OWNER_WITHOUT_GO_TYPES",
                                 f"{metatype_id} owns no go_types rows; a property cannot be added to it."))
    elif found.has_go_types_rows is None:
        issues.append(OwnerIssue("warning", "GO_TYPES_UNVERIFIED", "go_types was not read; the owner is unverified."))
    if found.defines_property:
        issues.append(OwnerIssue("error", "PROPERTY_EXISTS",
                                 f"{metatype_id} already defines the property (one go_types row per Metatype and property)."))
    missing = choice.resolution.missing
    if missing:
        issues.append(OwnerIssue("warning", "NEW_ARTICLES",
                                 f"New article(s) {', '.join(missing)} will take {metatype_id} as their Metatype."))
    return issues


def _candidate(result: ArticleReconciliation | None, metatype_id: str, wanted: list[str], prop: str) -> Candidate:
    column = result.roles.get("metatypeid") if result is not None else None
    listed: list[str] = []
    total = 0
    if result is not None and column is not None:
        for row in result.rows:
            if row.values.get(column, "").strip(" \t") == metatype_id:
                total += 1
                if row.identity is not None and row.identity[2] in wanted and row.identity[2] not in listed:
                    listed.append(row.identity[2])
    table = result.loader_result.table("go_types") if result is not None and result.loader_result else None
    if table is None or table.state.value not in ("valid", "empty", "no_data") or not table.columns:
        return Candidate(metatype_id, tuple(listed), total, None, None)
    records = table.records()
    owned = [r for r in records if r.get("id", "").strip(" \t") == metatype_id]
    defines = any(r.get("name", "").strip(" \t") == prop for r in owned) if prop else None
    return Candidate(metatype_id, tuple(listed), total, bool(owned), defines)
