"""Headless validation for the engineering Class model + service.

Exercises ``EngineeringClassService`` (create/rename/delete + property
assign/upsert/remove) and the class serialization round-trip. No Qt, no
database.

Run:  $env:PYTHONPATH="."; python scripts/validate_engineering_class.py
"""
from __future__ import annotations

from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.engineering.engineering_class_service import EngineeringClassService
from services.snapshot_serialization import snapshot_from_dict, snapshot_to_dict


def _snapshot() -> Snapshot:
    """A snapshot with one PDM property (Series) carrying coded values."""
    snap = Snapshot()
    series = Property(id="p1", name="Series")
    series.values.extend(
        [
            PropertyValue(id="v1", property_id="p1", value="4-leg base", code="1"),
            PropertyValue(id="v2", property_id="p1", value="Sled Base", code="2"),
        ]
    )
    snap.properties.append(series)
    return snap


def main() -> int:
    svc = EngineeringClassService.__new__(EngineeringClassService)
    snap = _snapshot()

    # 1) Create (unique name enforced).
    fabric = svc.create_class(snap, "  Fabric  ")
    assert fabric is not None and fabric.name == "Fabric" and fabric.id
    assert svc.create_class(snap, "fabric") is None      # duplicate (casefold)
    assert svc.create_class(snap, "   ") is None          # blank
    print("OK: create class (trimmed, unique, non-blank)")

    # 2) assign_property seeds values from the linked PDM property.
    a = svc.assign_property(snap, fabric.id, "p1", property_name="Series", width=1)
    assert a is not None and a.width == 1
    assert {v.code: v.value for v in a.values} == {
        "1": "4-leg base", "2": "Sled Base",
    }, a.values
    assert all(v.source == "pdm" for v in a.values)
    print("OK: assign_property seeds code->value from PDM")

    # 3) Re-add preserves values (only name/width refreshed).
    svc.assign_property(snap, fabric.id, "p1", property_name="Series", width=1)
    assert len(a.values) == 2
    print("OK: re-add preserves values")

    # 4) Manual add / rename / recode / remove value.
    svc.add_value(snap, fabric.id, "p1", "3", "Wall mount")
    assert {v.code for v in a.values} == {"1", "2", "3"}
    assert next(v for v in a.values if v.code == "3").source == "manual"
    assert svc.set_value_name(snap, fabric.id, "p1", "3", "Wall Mounted")
    assert next(v for v in a.values if v.code == "3").value == "Wall Mounted"
    assert not svc.set_value_code(snap, fabric.id, "p1", "3", "1")   # duplicate
    assert svc.set_value_code(snap, fabric.id, "p1", "3", "4")
    assert {v.code for v in a.values} == {"1", "2", "4"}
    assert svc.remove_value(snap, fabric.id, "p1", "4")
    assert {v.code for v in a.values} == {"1", "2"}
    print("OK: add/rename/recode/remove value (manual)")

    # 5) set_width edits only the slice width (clamped >= 0).
    assert svc.set_width(snap, fabric.id, "p1", 2)
    assert a.width == 2
    assert svc.set_width(snap, fabric.id, "p1", -5) and a.width == 0
    svc.set_width(snap, fabric.id, "p1", 1)
    print("OK: set_width edits only the width (clamped)")

    # 6) resolve_remaining maps the sliced letter -> value and flags gaps.
    resolved = svc.resolve_remaining(fabric, "211")     # width 1 -> "2"
    assert resolved[0]["letters"] == "2"
    assert resolved[0]["value"] == "Sled Base" and resolved[0]["matched"]
    gap = svc.resolve_remaining(fabric, "911")          # "9" has no value
    assert gap[0]["letters"] == "9" and gap[0]["matched"] is False
    print("OK: resolve_remaining maps letter->value and flags gaps")

    # 6b) distinct_slice_codes: distinct codes at a property's slice across all
    #     articles (first-seen order, non-empty). Fabric.p1 width == 1.
    assert svc.distinct_slice_codes(fabric, "p1", ["2S", "3S", "2X"]) == ["2", "3"]
    assert svc.distinct_slice_codes(fabric, "p1", []) == []
    assert svc.distinct_slice_codes(fabric, "missing", ["2S"]) == []
    print("OK: distinct_slice_codes gathers distinct codes across articles")

    # 7) Rename (duplicate rejected) + delete class.
    trim = svc.create_class(snap, "Trim")
    assert not svc.rename_class(snap, fabric.id, "Trim")
    assert svc.rename_class(snap, fabric.id, "Fabric A")
    assert svc.delete_class(snap, trim.id)
    assert len(svc.get_classes(snap)) == 1
    print("OK: rename + delete class")

    # 8) Serialization round-trip (classes + values).
    restored = snapshot_from_dict(snapshot_to_dict(snap))
    rprop = restored.engineering.classes[0].properties[0]
    assert rprop.width == 1
    assert {v.code: v.value for v in rprop.values} == {
        "1": "4-leg base", "2": "Sled Base",
    }
    print("OK: classes + values round-trip through serialization")

    # 9) ensure_standard_classes auto-creates <Category>_* + auto-groups; and
    #    resolve_from_attributes resolves against the live Attributes codes.
    snap2 = _snapshot()
    svc.ensure_standard_classes(snap2, "Bolster")
    assert sorted(c.name for c in svc.get_classes(snap2)) == [
        "Bolster_Attribute", "Bolster_Options", "Bolster_Visual",
    ]
    attr = next(c for c in svc.get_classes(snap2) if c.name == "Bolster_Attribute")
    assert any(a.property_id == "p1" for a in attr.properties)
    svc.set_width(snap2, attr.id, "p1", 1)
    res = next(
        r for r in svc.resolve_from_attributes(snap2, attr, "21")
        if r["property_id"] == "p1"
    )
    assert res["letters"] == "2" and res["value"] == "Sled Base" and res["matched"]
    # a second call is idempotent (no duplicate classes/properties).
    svc.ensure_standard_classes(snap2, "Bolster")
    assert len(svc.get_classes(snap2)) == 3
    assert len([a for a in attr.properties if a.property_id == "p1"]) == 1
    print("OK: ensure_standard_classes (idempotent) + resolve_from_attributes")

    print("ALL ENGINEERING CLASS CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
