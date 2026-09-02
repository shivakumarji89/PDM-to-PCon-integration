"""Validate collapse_duplicate_values against the real Always 'Type' shape.

PDM lists the same display name under several AttributeValueIds (one per product
sub-series). Only the id whose article position resolves gets a code; the
code-less twin must be dropped, while genuinely distinct codes on one name are
kept.
"""
from dataclasses import dataclass

from services.engineering.engineering_reduction_service import (
    collapse_duplicate_values,
)


@dataclass
class V:
    id: str
    value: str
    code: str = ""


def main() -> int:
    # Real Always 'Type' values (display order) + decoded codes by id.
    decoded = {"83224": "1", "83230": "2", "89799": "6", "89983": "5",
               "93300": "8", "93301": "9"}
    values = [
        V("83224", "4 Leg Base"),
        V("83225", "Sled Base"),
        V("83226", "Wood Base"),
        V("83230", "Sled Base"),
        V("83232", "Wood Base"),
        V("89799", "4 Star Swivel Base"),
        V("89800", "5 Star Swivel Base"),
        V("89983", "4 Star Swivel Base"),
        V("93300", "Counter height stool 4 leg"),
        V("93301", "Bar stool 4 leg"),
    ]
    code_of = lambda v: v.code or decoded.get(v.id, "")
    kept = collapse_duplicate_values(values, code_of)
    kept_ids = [v.id for v in kept]

    # Code-less twins of a resolved value are dropped.
    assert "83225" not in kept_ids, "code-less Sled Base twin should be dropped"
    # Both distinct 4 Star codes (5 and 6) are preserved.
    assert "89799" in kept_ids and "89983" in kept_ids, "distinct codes must stay"
    # An all-blank name (Wood Base) collapses to exactly one row.
    wood = [v for v in kept if v.value == "Wood Base"]
    assert len(wood) == 1, f"Wood Base should collapse to one, got {len(wood)}"
    # Unique resolved/unresolved singletons remain.
    for keep_id in ("83224", "83230", "89800", "93300", "93301"):
        assert keep_id in kept_ids, f"{keep_id} should be kept"
    # Net: 10 -> 8 rows.
    assert len(kept) == 8, f"expected 8 rows, got {len(kept)}"

    # Idempotent: collapsing again changes nothing.
    again = collapse_duplicate_values(kept, code_of)
    assert [v.id for v in again] == kept_ids, "collapse must be idempotent"

    print(f"OK collapse_duplicate_values: 10 -> {len(kept)} rows {kept_ids}")

    # Real Always 'Series' shape: same concepts, inconsistent case/spacing, all
    # code-less. Case/punctuation-insensitive key collapses the twins (11 -> 8).
    series = [
        V("99434", "4 leg base"),
        V("83223", "4-leg base"),
        V("99438", "4 star base"),
        V("98041", "4 Star Swivel Base"),
        V("99439", "5 star base"),
        V("99443", "Bar Stool"),
        V("99442", "Counter Stool"),
        V("98039", "Sled Base"),
        V("99435", "Sled base"),
        V("98040", "Wood Base"),
        V("99436", "Wood base"),
    ]
    skept = collapse_duplicate_values(series, lambda v: v.code)
    snames = [v.value for v in skept]
    # Case-only twins collapse to one each.
    assert snames.count("Sled Base") + snames.count("Sled base") == 1, snames
    assert snames.count("Wood Base") + snames.count("Wood base") == 1, snames
    # Hyphen-vs-space twin collapses.
    assert snames.count("4 leg base") + snames.count("4-leg base") == 1, snames
    # Genuinely different names stay ('4 star base' != '4 Star Swivel Base').
    assert "4 star base" in snames and "4 Star Swivel Base" in snames, snames
    assert len(skept) == 8, f"Series expected 8 rows, got {len(skept)}: {snames}"

    print(f"OK Series case/spacing collapse: 11 -> {len(skept)} rows {snames}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
