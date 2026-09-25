"""MDB -> XOCD reconciliation records.

The reconciliation engine treats the exported **XOCD** package as the source of
truth and the imported **MDB** as a disposable, possibly hand-edited artifact.
It diffs the two per entity (name-keyed) and classifies each delta so the user
can choose which changes to fold back into XOCD. Fields only - no logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field

#: A change's fold-back verdict.
VERDICT_SAFE = "safe"        # representable + consistent -> safe to apply
VERDICT_REVIEW = "review"    # representable but needs a human decision
VERDICT_BLOCKED = "blocked"  # not representable in XOCD / unsafe -> cannot fold

#: A change's kind.
KIND_ADDED = "added"
KIND_REMOVED = "removed"
KIND_MODIFIED = "modified"


@dataclass
class ReconFieldChange:
    """One changed column of a modified entity."""

    field: str = ""
    old: str = ""
    new: str = ""


@dataclass
class ReconChange:
    """One classified MDB-vs-XOCD delta for a single entity."""

    table: str = ""                 # logical table (e.g. "price", "propertyvalue")
    entity: str = ""                # human name-key (e.g. "NOALE211 / STD")
    kind: str = KIND_MODIFIED       # added / removed / modified
    fields: list[ReconFieldChange] = field(default_factory=list)
    summary: str = ""               # human-readable intent
    verdict: str = VERDICT_REVIEW   # safe / review / blocked
    reason: str = ""                # why this verdict
    new_row: dict = field(default_factory=dict)  # source (repo/MDB) row, for apply
    source_ref: str = ""            # link back to the XOCD line, e.g. "xocd_price.csv:42"


@dataclass
class ReconReport:
    """The full reconciliation result for one MDB against its XOCD baseline."""

    program: str = ""
    changes: list[ReconChange] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def blocked(self) -> list[ReconChange]:
        return [c for c in self.changes if c.verdict == VERDICT_BLOCKED]

    def summary(self) -> str:
        by = {KIND_ADDED: 0, KIND_REMOVED: 0, KIND_MODIFIED: 0}
        for change in self.changes:
            by[change.kind] = by.get(change.kind, 0) + 1
        return (
            f"{by[KIND_ADDED]} added, {by[KIND_MODIFIED]} modified, "
            f"{by[KIND_REMOVED]} removed"
        )
