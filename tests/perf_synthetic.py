"""Deterministic synthetic families for the performance regression tests and benchmarks.

``build_class_creation_snapshot`` builds a Development snapshot that exercises every
branch of ``EngineeringReductionService.materialize_class_creation_article_sets``
(head-code slicing, ModelSuffix tails, manual boundary overrides, several property
structures) at any article count. ``canonical_article_sets`` turns the result into a
stable text form so an optimised implementation can be compared with the output the
original implementation produced (see ``tests/test_phase1_performance_equivalence.py``).

Nothing here touches a database, a file or the network.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from types import SimpleNamespace

from models.article import Article
from models.engineering import Engineering
from models.engineering_class import (
    ClassPropertyAssignment,
    ClassValue,
    EngineeringClass,
)
from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot

def _head_properties(width_values: int):
    """(property id, name, width, [(value id suffix, code, display value)]) for the head codes."""
    widths = (8, 9, 10, 12, 14, 16) if width_values == 6 else tuple(range(8, 8 + width_values))
    return (
        ("pt", "Type", 1, (("a", "A", "Alpha"), ("b", "B", "Beta"), ("c", "C", "Gamma"), ("d", "D", "Delta"))),
        ("pw", "Width", 2, tuple((f"{w}", f"{w:02d}", f"W{w}") for w in widths)),
        ("pd", "Depth", 2, tuple((f"{d}", f"{d:02d}", f"D{d}") for d in (5, 6, 7))),
    )


# ModelSuffix property: the value codes live in the part after the first dot.
_SUFFIX_PROPERTY = ("pf", "Finish", 2, (("s1", "", "Oak"), ("s2", "", "Ash"), ("s3", "", "Walnut")))
_SUFFIX_MARKERS = {"s1": "S1", "s2": "S2", "s3": "S3"}


def build_class_creation_snapshot(
    count: int,
    *,
    products: int = 1,
    members_per_family: int = 500,
    structures: int = 2,
    manual_boundaries: bool = False,
    width_values: int = 6,
) -> Snapshot:
    """Return a snapshot with ``count`` articles in ``structures`` property structures.

    Article ``i`` has the code ``DSK<type><width><depth><i:05d>.<finish>``; structure 0
    articles carry Type/Width/Depth/Finish, structure 1 articles lack Depth, structure 2
    lack Width, and so on, so the materialiser returns several classes. With
    ``manual_boundaries`` every 7th article gets a base-length override, which takes the
    manual-boundary branch.
    """
    head_properties = _head_properties(width_values)
    props: list[Property] = []
    class_assignments: list[ClassPropertyAssignment] = []
    value_ids_by_prop: dict[str, list[str]] = {}
    for placement, (pid, name, width, values) in enumerate(head_properties + (_SUFFIX_PROPERTY,)):
        is_suffix = pid == _SUFFIX_PROPERTY[0]
        prop_values = [
            PropertyValue(
                id=f"{pid}:{vid}", property_id=pid, value=text, code=code,
                model_suffix=_SUFFIX_MARKERS.get(vid, "") if is_suffix else "",
                display_order=index,
            )
            for index, (vid, code, text) in enumerate(values)
        ]
        props.append(Property(id=pid, name=name, values=prop_values, has_dependent_options=True))
        value_ids_by_prop[pid] = [v.id for v in prop_values]
        class_assignments.append(
            ClassPropertyAssignment(
                property_id=pid, property_name=name, width=width, placement=placement,
                values=[
                    ClassValue(
                        value_id=v.id,
                        code=(_SUFFIX_MARKERS[vid] if is_suffix else code),
                        value=text,
                    )
                    for v, (vid, code, text) in zip(prop_values, values)
                ],
            )
        )

    articles: list[Article] = []
    article_values: dict[str, list[str]] = {}
    overrides: dict[str, int] = {}
    head_defs = {pid: values for pid, _n, _w, values in head_properties}
    for i in range(count):
        t = head_defs["pt"][i % 4]
        w = head_defs["pw"][(i // 4) % width_values]
        d = head_defs["pd"][(i // (4 * width_values)) % 3]
        s = _SUFFIX_PROPERTY[3][(i // (12 * width_values)) % 3]
        structure = i % max(1, structures)
        drop = {0: set(), 1: {"pd"}, 2: {"pw"}, 3: {"pw", "pd"}}.get(structure % 4, set())
        code = f"DSK{t[1]}{w[1]}{d[1]}{i:05d}.{_SUFFIX_MARKERS[s[0]]}"
        aid = f"a{i}"
        articles.append(Article(id=aid, product_id=f"prod{i % products}", code=code))
        ids = [f"pt:{t[0]}", f"pw:{w[0]}", f"pd:{d[0]}", f"pf:{s[0]}"]
        keep = {"pt": ids[0], "pw": ids[1], "pd": ids[2], "pf": ids[3]}
        article_values[aid] = [vid for pid, vid in keep.items() if pid not in drop]
        if manual_boundaries and i % 7 == 0:
            overrides[code] = 4

    members: list[MemberArticle] = []
    families: list[EngineeringFamily] = []
    for start in range(0, count, members_per_family):
        family_id = f"f{start // members_per_family}"
        chunk = [
            MemberArticle(id=f"m{i}", article_id=f"a{i}", family_id=family_id)
            for i in range(start, min(count, start + members_per_family))
        ]
        members.extend(chunk)
        families.append(EngineeringFamily(id=family_id, name=f"Family {family_id}", members=chunk))

    all_value_ids = [vid for ids in value_ids_by_prop.values() for vid in ids]
    snapshot = Snapshot(
        id="perf-synthetic",
        articles=articles,
        properties=props,
        article_property_value_ids=article_values,
        product_property_value_ids={f"prod{p}": list(all_value_ids) for p in range(products)},
        engineering=Engineering(
            classes=[EngineeringClass(id="class1", name="Desk_Attribute", properties=class_assignments)],
            families=families,
        ),
    )
    snapshot.base_length_overrides = overrides
    return snapshot


def reduction_service():
    """An ``EngineeringReductionService`` wired the way the unit tests wire it."""
    from services.engineering.engineering_class_service import EngineeringClassService
    from services.engineering.engineering_reduction_service import EngineeringReductionService

    context = SimpleNamespace()
    context.engineering_class_service = EngineeringClassService(context)
    return EngineeringReductionService(context)


def canonical_article_sets(snapshot: Snapshot, sets) -> str:
    """Stable text form of the materialised sets plus every member's ``reduced_article``.

    Set ids are random UUIDs, so they are replaced by the set's position. Every list keeps
    its order: an optimisation must not reorder anything.
    """
    document = {
        "sets": [
            {key: value for key, value in asdict(article_set).items() if key != "id"}
            for article_set in sets
        ],
        "reduced": [
            [member.id, member.reduced_article]
            for family in snapshot.engineering.families
            for member in family.members
        ],
    }
    return json.dumps(document, sort_keys=True, separators=(",", ":"))


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
