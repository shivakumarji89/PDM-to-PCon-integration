"""Validate Engineering JSON persistence (Phase A).

Headless, PDM-free check that a fully populated Snapshot - source data plus the
Engineering graph - survives a value round-trip through
:mod:`services.snapshot_serialization` and a save/load cycle through
:class:`services.snapshot_store.SnapshotStore`.

Run:  python -m scripts.validate_snapshot_serialization
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from core.enums import SnapshotStatus
from models.article import Article
from models.article_set import ArticleSet, SetAttribute, SetValue
from models.engineering import Engineering
from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.option import Option
from models.option_value import OptionValue
from models.product import Product
from models.property import Property
from models.property_assignment import PropertyAssignment
from models.property_definition import PropertyDataType, PropertyDefinition
from models.property_value import PropertyValue
from models.snapshot import Snapshot, SnapshotMetadata
from services.snapshot_serialization import snapshot_from_dict, snapshot_to_dict
from services.snapshot_store import SnapshotStore


def _build_sample_snapshot() -> Snapshot:
    """A representative snapshot exercising every serialized field."""
    width_values = [
        PropertyValue(id="pv1", property_id="p1", value="1200", code="12"),
        PropertyValue(id="pv2", property_id="p1", value="1400", code="14"),
    ]
    finish_values = [
        PropertyValue(id="pv3", property_id="p2", value="Black", code="BL"),
        PropertyValue(id="pv4", property_id="p2", value="White", code="WH"),
    ]
    width = Property(
        id="p1", code="{WID}", name="Width", data_type="number",
        display_order=1, attribute_type=2, has_dependent_options=False,
        selected=True, values=list(width_values),
    )
    finish = Property(
        id="p2", code="{FIN}", name="Finish", values=list(finish_values),
    )
    option = Option(
        id="o1", code="{FAB}", name="Fabric", is_fabric=True,
        values=[OptionValue(id="ov1", option_id="o1", value="Wool", code="WL")],
    )
    article = Article(
        id="a1", product_id="prod1", code="AR001", name="Desk",
        quantity=1, description="A desk", status="Active", selected=True,
        weight_kg=12.5, height=720, width=1200, depth=800,
        properties=[width],
    )
    product = Product(
        id="prod1", code="DSK", name="Desk Range", category="Desks",
        catalogue_id="381", status="Active",
        articles=[article], options=[option],
    )
    engineering = Engineering(
        families=[
            EngineeringFamily(
                id="default", name="Default Family",
                members=[
                    MemberArticle(
                        id="m1", article_id="a1",
                        reduced_article="AR001-R", long_description="Reduced desk",
                        property_values=[
                            PropertyAssignment(property_id="d1", value="1200"),
                        ],
                    )
                ],
            )
        ],
        properties=[
            PropertyDefinition(
                id="d1", name="Width", order=1,
                data_type=PropertyDataType.NUMBER,
            )
        ],
    )
    return Snapshot(
        id="prod1", status=SnapshotStatus.MODIFIED, product=product,
        articles=[article], properties=[width, finish],
        property_values=[*width_values, *finish_values],
        options=[option], option_values=list(option.values),
        product_property_value_ids={"prod1": ["pv1", "pv3"]},
        product_option_value_ids={"prod1": ["ov1"]},
        article_sets=[
            ArticleSet(
                id="set1", base_length=3, article_ids=["a1"],
                properties=[
                    SetAttribute(
                        id="p1", name="Width",
                        values=[SetValue(id="pv1", value="1200", code="12",
                                         article_ids=["a1"])],
                    )
                ],
                options=[
                    SetAttribute(
                        id="o1", name="Fabric",
                        values=[SetValue(id="ov1", value="Wool", code="WL",
                                         article_ids=["a1"])],
                    )
                ],
            )
        ],
        metadata=SnapshotMetadata(source="test", product_code="DSK"),
        engineering=engineering,
    )


def main() -> int:
    snapshot = _build_sample_snapshot()

    # 1) Pure dict round-trip preserves equality.
    restored = snapshot_from_dict(snapshot_to_dict(snapshot))
    assert restored == snapshot, "dict round-trip changed the snapshot"

    # 1b) The derived article-set table survives with its value coverage.
    assert len(restored.article_sets) == 1
    aset = restored.article_sets[0]
    assert aset.base_length == 3 and aset.article_ids == ["a1"]
    assert aset.properties[0].values[0].article_ids == ["a1"]
    assert aset.options[0].values[0].code == "WL"
    assert restored.product_option_value_ids == {"prod1": ["ov1"]}
    print("OK: article_sets table + product_option_value_ids round-trip")

    # 2) File save/load round-trip preserves equality (no PDM).
    with tempfile.TemporaryDirectory() as tmp:
        store = SnapshotStore(directory=tmp)
        path = store.save(snapshot)
        assert path.exists(), "save did not write a file"
        loaded = store.load(path)
        assert loaded == snapshot, "file round-trip changed the snapshot"
        by_id = store.load_by_id("prod1")
        assert by_id == snapshot, "load_by_id changed the snapshot"

    # 3) Engineering graph specifically survives.
    fam = restored.engineering.families[0]
    assert fam.members[0].property_values[0].value == "1200"
    assert restored.engineering.properties[0].data_type is PropertyDataType.NUMBER

    print("PASS: snapshot serialization + store round-trip (dict, file, by-id)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
