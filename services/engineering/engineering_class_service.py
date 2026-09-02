"""Engineering class management service.

Create, rename and delete classes and manage their property assignments,
mutating **only** ``snapshot.engineering.classes``. It never touches source/PDM
data, the UI, or signals.

A class stores STRUCTURE (ordered properties, each with a standard PDM ``code``
reference and a manual slice ``width``). The per-article letters are computed on
demand by :meth:`slice_remaining`, which slices an article's *remaining* string
positionally by cumulative width, in list order (VARCOND-style).

Business rules:
  * Class names are unique (case-insensitive, trimmed).
  * A class ``id`` never changes once created.
  * A property appears at most once per class (``assign_property`` upserts).
  * The standard ``code`` comes from PDM and is stored only for reference.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from uuid import uuid4

from models.engineering_class import (
    ClassPropertyAssignment,
    ClassValue,
    EngineeringClass,
)
from models.snapshot import Snapshot
from services.base_service import BaseService


@dataclass(frozen=True)
class ConfigCodeFinding:
    """One diagnostic about a configuration property's order codes: what the
    decoder found wrong/notable and a suggested resolution."""

    property_id: str
    property_name: str
    kind: str        # unresolved | variable_width | width_mismatch
    severity: str    # error | warning | info
    message: str
    suggestion: str


@dataclass(frozen=True)
class ClassGroup:
    """One named group the standard classes split into. ``value_ids=None`` means
    the whole property's values apply; a set scopes the class to those values.
    ``source_ranges`` are the raw ProductRange names merged into this group."""

    name: str
    prop_ids: tuple[str, ...]
    option_ids: tuple[str, ...]
    visual_ids: tuple[str, ...]
    value_ids: frozenset[str] | None
    source_ranges: tuple[str, ...] = ()



class EngineeringClassService(BaseService):
    """Create / rename / delete classes and manage their property assignments."""

    def get_classes(self, snapshot: Snapshot | None) -> list[EngineeringClass]:
        """Return the snapshot's engineering classes (empty when unavailable)."""
        if snapshot is None or snapshot.engineering is None:
            return []
        return snapshot.engineering.classes

    def create_class(
        self, snapshot: Snapshot | None, name: str
    ) -> EngineeringClass | None:
        """Append a new class and return it.

        Rejects a missing snapshot, a blank name, or a duplicate name. The new
        class gets a fresh, permanent ``id``.
        """
        if snapshot is None or snapshot.engineering is None:
            return None
        clean = (name or "").strip()
        if not clean:
            return None
        classes = snapshot.engineering.classes
        if self._find_by_name(classes, clean) is not None:
            return None
        cls = EngineeringClass(id=uuid4().hex, name=clean)
        classes.append(cls)
        return cls

    def rename_class(
        self, snapshot: Snapshot | None, class_id: str | None, new_name: str
    ) -> bool:
        """Rename a class. The ``id`` is unchanged; rejects blank/duplicate names."""
        if snapshot is None or snapshot.engineering is None or not class_id:
            return False
        classes = snapshot.engineering.classes
        target = self._find_by_id(classes, class_id)
        if target is None:
            return False
        clean = (new_name or "").strip()
        if not clean:
            return False
        existing = self._find_by_name(classes, clean)
        if existing is not None and existing is not target:
            return False
        target.name = clean
        return True

    def delete_class(self, snapshot: Snapshot | None, class_id: str | None) -> bool:
        """Remove a class and all its property assignments."""
        if snapshot is None or snapshot.engineering is None or not class_id:
            return False
        classes = snapshot.engineering.classes
        target = self._find_by_id(classes, class_id)
        if target is None:
            return False
        classes.remove(target)
        return True

    def assign_property(
        self,
        snapshot: Snapshot | None,
        class_id: str | None,
        property_id: str,
        property_name: str = "",
        width: int = 0,
        value_ids: frozenset[str] | None = None,
    ) -> ClassPropertyAssignment | None:
        """Add a property to the class (upsert by ``property_id``).

        On first add, the property's :class:`ClassValue` list is SEEDED from the
        linked PDM property's values (``code`` = ``OrderCodeValue``, ``value`` =
        value name, ``source`` = ``"pdm"``) so the codes come straight from PDM.
        On re-add the existing values are preserved (only name/width refreshed).
        ``width`` is the manual number of characters sliced from the remaining.
        ``value_ids`` (when given) scopes the seeded values to that subset - the
        group split keeps only the values a group's articles carry.
        """
        if (
            snapshot is None
            or snapshot.engineering is None
            or not class_id
            or not property_id
        ):
            return None
        target = self._find_by_id(snapshot.engineering.classes, class_id)
        if target is None:
            return None
        width = max(0, int(width or 0))
        existing = self._find_property(target, property_id)
        if existing is not None:
            if property_name:
                existing.property_name = property_name
            existing.width = width
            return existing
        assignment = ClassPropertyAssignment(
            property_id=property_id,
            property_name=property_name,
            width=width,
            values=self._seed_values(snapshot, property_id, value_ids),
        )
        target.properties.append(assignment)
        return assignment

    @staticmethod
    def _seed_values(
        snapshot: Snapshot, property_id: str,
        value_ids: frozenset[str] | None = None,
    ) -> list[ClassValue]:
        """Copy the linked PDM property's values as class values (source=pdm),
        keeping only ``value_ids`` when a scope is given."""
        prop = next(
            (p for p in snapshot.properties if p.id == property_id), None
        )
        if prop is None:
            return []
        return [
            ClassValue(code=v.code or "", value=v.value or "", source="pdm")
            for v in prop.values
            if value_ids is None or str(v.id) in value_ids
        ]

    def set_width(
        self,
        snapshot: Snapshot | None,
        class_id: str | None,
        property_id: str,
        width: int,
    ) -> bool:
        """Update only the manual slice ``width`` of an existing assignment."""
        if (
            snapshot is None
            or snapshot.engineering is None
            or not class_id
            or not property_id
        ):
            return False
        target = self._find_by_id(snapshot.engineering.classes, class_id)
        if target is None:
            return False
        assignment = self._find_property(target, property_id)
        if assignment is None:
            return False
        assignment.width = max(0, int(width or 0))
        return True

    def auto_derive_widths(
        self, snapshot: Snapshot | None, cls: EngineeringClass | None
    ) -> int:
        """Size each class-property width from its linked values' order codes.

        ``width`` = the longest ``OrderCodeValue`` length across the property's
        values, or 0 when no value carries a code (configuration attributes that
        are baked into the product code, not sliced from the order-code tail).
        Returns the number of assignments whose width changed.
        """
        if cls is None:
            return 0
        changed = 0
        for assignment in cls.properties:
            codes = [
                code
                for code, _value in self._property_values(
                    snapshot, assignment.property_id
                )
                if code
            ]
            width = max((len(code) for code in codes), default=0)
            if int(assignment.width or 0) != width:
                assignment.width = width
                changed += 1
        return changed

    def remove_property(
        self, snapshot: Snapshot | None, class_id: str | None, property_id: str
    ) -> bool:
        """Remove a property assignment from a class."""
        if (
            snapshot is None
            or snapshot.engineering is None
            or not class_id
            or not property_id
        ):
            return False
        target = self._find_by_id(snapshot.engineering.classes, class_id)
        if target is None:
            return False
        assignment = self._find_property(target, property_id)
        if assignment is None:
            return False
        target.properties.remove(assignment)
        return True

    @staticmethod
    def slice_remaining(
        cls: EngineeringClass, remaining: str
    ) -> list[tuple[str, str]]:
        """Slice an article's ``remaining`` string across the class's properties.

        Property *k* (in list order) gets ``remaining[offset : offset + width]``
        where ``offset`` is the sum of the prior widths - the same positional
        scheme VARCOND uses for parametric dimensions. Returns a list of
        ``(property_id, letters)`` in class order; letters are ``""`` past the end
        of the string.
        """
        remaining = remaining or ""
        result: list[tuple[str, str]] = []
        offset = 0
        for assignment in cls.properties:
            width = max(0, int(assignment.width or 0))
            letters = remaining[offset : offset + width] if width else ""
            result.append((assignment.property_id, letters))
            offset += width
        return result

    def resolve_remaining(
        self, cls: EngineeringClass, remaining: str
    ) -> list[dict]:
        """Slice ``remaining`` and resolve each letter to its class value.

        Returns one dict per property (class order): ``{property_id,
        property_name, letters, value, matched}`` where ``value`` is the matching
        :class:`ClassValue`'s name (or ``""``) and ``matched`` is whether a value
        with that ``code`` exists - so the UI can flag gaps.
        """
        sliced = dict(self.slice_remaining(cls, remaining))
        result: list[dict] = []
        for assignment in cls.properties:
            letters = sliced.get(assignment.property_id, "")
            match = next(
                (v for v in assignment.values if v.code == letters), None
            )
            result.append(
                {
                    "property_id": assignment.property_id,
                    "property_name": assignment.property_name,
                    "letters": letters,
                    "value": match.value if match is not None else "",
                    "matched": match is not None,
                }
            )
        return result

    # -- standard classes + attribute-sourced resolution -----------------
    #: Standard class name suffixes (``<Category>_<suffix>``).
    STANDARD_SUFFIXES = ("Attribute", "Options", "Visual")

    def ensure_standard_classes(
        self, snapshot: Snapshot | None, category: str
    ) -> list[EngineeringClass]:
        """Create/refresh the standard ``<Group>_*`` classes, one set per group.

        Idempotent and additive. When the load spans one product range the
        group is the ``category`` (the historical flat ``<Category>_Attribute`` /
        ``_Options`` / ``_Visual``). When it spans several ranges (desk / screen /
        wire management) each becomes its own ``<Group>_*`` set, scoped to the
        properties, options and values that group carries. Existing classes,
        properties and widths are left untouched.
        """
        if snapshot is None or snapshot.engineering is None:
            return []
        category = (category or "").strip() or "Class"
        engineering = snapshot.engineering
        prop_name = {str(p.id): (p.name or "") for p in snapshot.properties}
        opt_name = {str(o.id): (o.name or "") for o in snapshot.options}
        vis_name = {str(d.id): (d.name or "") for d in engineering.properties}
        groups = self.resolve_class_groups(snapshot, category)
        split = len(groups) > 1
        created: set[str] = set()
        for group in groups:
            token = self._group_token(group.name)
            members = {
                "Attribute": [(pid, prop_name.get(str(pid), "")) for pid in group.prop_ids],
                "Options": [(oid, opt_name.get(str(oid), "")) for oid in group.option_ids],
                "Visual": [(vid, vis_name.get(str(vid), "")) for vid in group.visual_ids],
            }
            for suffix in self.STANDARD_SUFFIXES:
                entries = members[suffix]
                if split and not entries:
                    continue  # a split group only gets the class kinds it has
                name = f"{token}_{suffix}"
                created.add(name)
                cls = self._find_by_name(engineering.classes, name)
                if cls is None:
                    cls = self.create_class(snapshot, name)
                if cls is None:
                    continue
                used = {a.property_id for a in cls.properties}
                for pid, pname in entries:
                    if pid and pid not in used:
                        self.assign_property(
                            snapshot, cls.id, pid, property_name=pname,
                            width=0, value_ids=group.value_ids,
                        )
                        used.add(pid)
        # Prune standard classes left over from the OTHER grouping mode so a
        # toggle never leaves both flat and split classes (which would export
        # twice). Only auto-managed ``*_Attribute/_Options/_Visual`` names.
        stale = [
            c for c in engineering.classes
            if c.name not in created
            and c.name.rsplit("_", 1)[-1] in self.STANDARD_SUFFIXES
        ]
        for c in stale:
            engineering.classes.remove(c)
        return engineering.classes

    def resolve_class_groups(
        self, snapshot: Snapshot | None, category: str
    ) -> list[ClassGroup]:
        """The named groups the standard classes split into.

        A load that spans several PDM product ranges (``attribute_range``) yields
        one group per range - the same signal Class Creation already groups the
        property tree by - scoping each group's properties/options/values to that
        range. A single-range (or un-ranged) load is one group named ``category``
        carrying everything (the historical flat behaviour). Ranges the user
        ignored on the Articles page are dropped.
        """
        if snapshot is None or snapshot.engineering is None:
            return []
        props = [p for p in snapshot.properties if p.id]
        opts = [o for o in snapshot.options if o.id]
        visuals = [d for d in snapshot.engineering.properties if d.id]
        ranges = getattr(snapshot, "attribute_range", None) or {}
        value_range = getattr(snapshot, "value_range", None) or {}
        ignored = set(getattr(snapshot, "ignored_ranges", None) or [])

        # Options carry no attribute_range; derive their range from the product
        # that links them (product_range) via each option value, the same way
        # Class Creation groups the Options tree. option value id -> ranges.
        product_range = getattr(snapshot, "product_range", None) or {}
        product_opt_vals = getattr(snapshot, "product_option_value_ids", None) or {}
        optval_ranges: dict[str, set[str]] = {}
        for pid, vids in product_opt_vals.items():
            rng = product_range.get(str(pid))
            if rng:
                for vid in vids:
                    optval_ranges.setdefault(str(vid), set()).add(rng)
        opt_values: dict[str, list[str]] = {}
        for ov in snapshot.option_values:
            opt_values.setdefault(str(ov.option_id), []).append(str(ov.id))

        def prop_ranges(pid) -> list[str]:
            return [r for r in ranges.get(str(pid), []) if r not in ignored]

        def opt_ranges(oid) -> list[str]:
            rs: set[str] = set()
            for vid in opt_values.get(str(oid), []):
                rs |= optval_ranges.get(vid, set())
            return [r for r in rs if r not in ignored]

        all_ranges = {r for p in props for r in prop_ranges(p.id)}
        all_ranges |= {r for o in opts for r in opt_ranges(o.id)}
        # Flat single group unless the user opted into the range split (keeps the
        # historical <Category>_* classes the Class Creation UI binds to).
        if not getattr(snapshot, "split_classes_by_group", False):
            return [ClassGroup(
                category,
                tuple(str(p.id) for p in props),
                tuple(str(o.id) for o in opts),
                tuple(str(d.id) for d in visuals),
                None,
            )]

        # Split basis chosen by the user: one group per article set (base
        # article) or per PDM product range (default).
        if str(getattr(snapshot, "class_group_basis", "") or "range").lower() == "article_set":
            return self._groups_by_article_set(snapshot, category, props, opts, visuals)

        if len(all_ranges) <= 1:
            return [ClassGroup(
                category,
                tuple(str(p.id) for p in props),
                tuple(str(o.id) for o in opts),
                tuple(str(d.id) for d in visuals),
                None,
            )]

        def rank(gname: str) -> int:
            for i, p in enumerate(props):
                if gname in prop_ranges(p.id):
                    return i
            return 10_000

        # Combined value -> ranges (property values + option values) for scoping.
        val_ranges: dict[str, set[str]] = {
            str(vid): set(rs) for vid, rs in value_range.items()
        }
        for vid, rs in optval_ranges.items():
            val_ranges.setdefault(vid, set()).update(rs)

        # Raw per-range group, then MERGE by the user's display name (several
        # ranges renamed to the same name become one group).
        rename = getattr(snapshot, "class_group_names", None) or {}
        raw: list[ClassGroup] = []
        for gname in sorted(all_ranges, key=rank):
            pids = tuple(str(p.id) for p in props if gname in prop_ranges(p.id))
            oids = tuple(str(o.id) for o in opts if gname in opt_ranges(o.id))
            vids = frozenset(
                str(vid) for vid, rs in val_ranges.items() if gname in rs
            )
            raw.append(ClassGroup(gname, pids, oids, tuple(), vids or None, (gname,)))

        # Entities with no kept range (and the range-less Visual defs) collect in
        # a "General" group so nothing is dropped.
        orphan_p = tuple(str(p.id) for p in props if not prop_ranges(p.id))
        orphan_o = tuple(str(o.id) for o in opts if not opt_ranges(o.id))
        if orphan_p or orphan_o or visuals:
            raw.append(ClassGroup(
                "General", orphan_p, orphan_o,
                tuple(str(d.id) for d in visuals), None, ("General",),
            ))

        merged: dict[str, ClassGroup] = {}
        order: list[str] = []
        for g in raw:
            display = (rename.get(g.name) or g.name).strip() or g.name
            if display not in merged:
                merged[display] = ClassGroup(display, (), (), (), frozenset(), ())
                order.append(display)
            cur = merged[display]
            vids = (cur.value_ids or frozenset()) | (g.value_ids or frozenset())
            merged[display] = ClassGroup(
                display,
                cur.prop_ids + g.prop_ids,
                cur.option_ids + g.option_ids,
                cur.visual_ids + g.visual_ids,
                vids or None,
                cur.source_ranges + g.source_ranges,
            )
        return [merged[name] for name in order]

    def _groups_by_article_set(
        self, snapshot: Snapshot, category: str, props: list, opts: list, visuals: list
    ) -> list[ClassGroup]:
        """One class group per article set (base article). Each group carries the
        set's own properties/options/values; the product-wide Visual defs go into
        every group (they apply to all articles). Falls back to one flat group
        when there are no article sets."""
        sets = getattr(snapshot, "article_sets", None) or []
        visual_ids = tuple(str(d.id) for d in visuals)
        if not sets:
            return [ClassGroup(
                category,
                tuple(str(p.id) for p in props),
                tuple(str(o.id) for o in opts),
                visual_ids, None,
            )]
        groups: list[ClassGroup] = []
        used: set[str] = set()
        for index, aset in enumerate(sets):
            name = (getattr(aset, "base_code", "") or "").strip() or f"{category}_{index + 1}"
            unique, k = name, 2
            while unique in used:
                unique, k = f"{name}_{k}", k + 1
            used.add(unique)
            attrs = list(aset.properties) + list(aset.options)
            vids = frozenset(
                str(v.id) for a in attrs for v in getattr(a, "values", []) if getattr(v, "id", "")
            )
            groups.append(ClassGroup(
                unique,
                tuple(str(a.id) for a in aset.properties),
                tuple(str(a.id) for a in aset.options),
                visual_ids,
                vids or None,
                (unique,),
            ))
        return groups

    @staticmethod
    def _group_token(name: str) -> str:
        """Class-name prefix from a group name: capitalised words joined, no
        spaces/special chars (``'Wire Management'`` -> ``'WireManagement'``)."""
        words = re.sub(r"[^0-9A-Za-z]+", " ", name or "").split()
        token = "".join(w[:1].upper() + w[1:] for w in words)
        return token or "Class"

    def set_group_name(
        self, snapshot: Snapshot | None, source_ranges, name: str
    ) -> None:
        """Rename (and, when the name matches another group, merge) the split
        group made of ``source_ranges`` by mapping each raw range to ``name``.
        A blank name clears the mapping (reverts to the raw range names)."""
        if snapshot is None:
            return
        clean = (name or "").strip()
        mapping = snapshot.class_group_names
        for raw in source_ranges or ():
            if clean:
                mapping[str(raw)] = clean
            else:
                mapping.pop(str(raw), None)


    def distinct_slice_codes(
        self, cls: EngineeringClass, property_id: str, remainings
    ) -> list[str]:
        """Distinct codes appearing at a property's slice across all articles.

        Slices every article ``remaining`` at the property's cumulative
        offset/width (the same positional scheme as :meth:`slice_remaining`) and
        returns the distinct non-empty codes in first-seen order. Empty when the
        property is not in the class or has width 0.
        """
        offset, width, found = 0, 0, False
        for assignment in cls.properties:
            w = max(0, int(assignment.width or 0))
            if assignment.property_id == property_id:
                width, found = w, True
                break
            offset += w
        if not found or width <= 0:
            return []
        seen: list[str] = []
        for remaining in remainings:
            code = (remaining or "")[offset : offset + width]
            if code and code not in seen:
                seen.append(code)
        return seen

    @staticmethod
    def _decode_key_for(snapshot: Snapshot | None):
        """Cheap O(n) fingerprint that changes whenever the decode would."""
        if snapshot is None:
            return None
        props = snapshot.properties
        return (
            id(snapshot),
            len(snapshot.articles),
            len(props),
            len(getattr(snapshot, "product_property_value_ids", {}) or {}),
            tuple(
                (p.id, any((v.code or "").strip() for v in p.values)) for p in props
            ),
        )

    def decode_config_codes_by_value_id(
        self, snapshot: Snapshot | None
    ) -> dict[str, dict[str, str]]:
        """Cached wrapper over :meth:`_decode_config_codes_by_value_id`."""
        key = self._decode_key_for(snapshot)
        if key is not None and getattr(self, "_valueid_key", None) == key:
            return self._valueid_cache
        result = self._decode_config_codes_by_value_id(snapshot)
        self._valueid_key = key
        self._valueid_cache = result
        return result

    def _decode_config_codes_by_value_id(
        self, snapshot: Snapshot | None
    ) -> dict[str, dict[str, str]]:
        """Slice head config codes by STORED VALUE-ID grouping - no inference.

        For each head config property, group same-length article heads by the
        value they carry (its stored AttributeValueId). A head position is that
        property's code position when it is CONSTANT within every value's group
        AND DIFFERS across the property's values; each value's code is the head
        chars there. The grouping is exact (stored ids), so codes reused across
        properties never collide (unlike value-based correlation). A property
        constant in the loaded set has no contrast and is left in the base - never
        a wrong code. Returns ``{property_id: {value_id: code}}`` and records a
        per-property layout (width, position). Read-only.
        """
        result: dict[str, dict[str, str]] = {}
        self._position_layout = {}
        self._slice_hints = {}
        if snapshot is None:
            return result
        # Every uncoded, multi-value head property is a slicing candidate - not
        # only the ones that drive dependent options. A property that is not a
        # real head code simply never owns a contiguous head run and is dropped
        # naturally; redundant duplicates are removed by the overlap pass below.
        config_props = [
            p for p in snapshot.properties
            if p.values
            and not any((v.code or "").strip() for v in p.values)
        ]
        if not config_props:
            return result
        value_to_prop = {
            str(v.id): str(p.id) for p in config_props for v in p.values
        }
        apv = snapshot.article_property_value_ids or {}
        ppv = snapshot.product_property_value_ids or {}
        product_of = {
            str(a.id): str(getattr(a, "product_id", "") or "")
            for a in snapshot.articles
        }
        head_of: dict[str, str] = {}
        assign: dict[str, dict[str, str]] = defaultdict(dict)
        for article in snapshot.articles:
            code = getattr(article, "code", "") or ""
            if not code:
                continue
            aid = str(article.id)
            head_of[aid] = code.split(".", 1)[0]
            vids = apv.get(aid) or ppv.get(product_of.get(aid, ""), [])
            for vid in vids:
                pid = value_to_prop.get(str(vid))
                if pid is not None:
                    assign[aid][pid] = str(vid)

        by_len: dict[tuple, list[str]] = defaultdict(list)
        for aid, head in head_of.items():
            # STRUCTURE = head length + the exact set of config properties the
            # article carries. Same length alone can mix different structures
            # (e.g. an accessory whose code has no tail split), which corrupts the
            # positional read; the property signature keeps like with like.
            by_len[(len(head), frozenset(assign[aid].keys()))].append(aid)

        # Phase 1: per-group ownership. Inside one (length, signature) group the
        # positions are fixed, so a property's code is the contiguous head run
        # that is constant within each value and differs across values.
        codes_seen: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        group_layout: dict[tuple, dict[str, tuple[int, int]]] = {}
        group_codes: dict[tuple, dict[str, dict[str, str]]] = {}
        minpos: dict[str, int] = {}
        minpos_src_len: dict[str, int] = {}  # group length where minpos was established
        for gkey, aids in by_len.items():
            length = gkey[0]
            if len(aids) < 2:
                continue
            gl: dict[str, tuple[int, int]] = {}
            gc: dict[str, dict[str, str]] = {}
            for prop in config_props:
                pid = str(prop.id)
                groups: dict[str, list[str]] = defaultdict(list)
                for aid in aids:
                    vid = assign[aid].get(pid)
                    if vid is not None:
                        groups[vid].append(head_of[aid])
                if len(groups) < 2:
                    continue  # no contrast in this load -> left in the base
                owned = [
                    i for i in range(length)
                    if all(len({h[i] for h in hs}) == 1 for hs in groups.values())
                    and len({hs[0][i] for hs in groups.values()}) > 1
                ]
                # a positional code is a single contiguous run
                if not owned or owned != list(range(owned[0], owned[0] + len(owned))):
                    continue
                if owned[0] < minpos.get(pid, length):
                    minpos[pid] = owned[0]
                    minpos_src_len[pid] = length
                elif pid not in minpos:
                    minpos[pid] = owned[0]
                    minpos_src_len[pid] = length
                cc: dict[str, str] = {}
                for vid, hs in groups.items():
                    code = "".join(hs[0][i] for i in owned)
                    if code:
                        codes_seen[pid][vid].add(code)
                        cc[vid] = code
                if cc:
                    gl[pid] = (owned[0], len(owned))
                    gc[pid] = cc
            if gl:
                group_layout[gkey] = gl
                group_codes[gkey] = gc

        # per-group agreement -> base result (values with one consistent code)
        for pid, vmap in codes_seen.items():
            keep = {
                vid: next(iter(codes))
                for vid, codes in vmap.items() if len(codes) == 1
            }
            if keep:
                result[pid] = keep

        # Phase 2: cross-group consolidation for VARIABLE-WIDTH values. Seed from
        # the group that decodes the most properties (the clean, usually shortest
        # layout); then for each article the single property whose value is not
        # yet known has width = head length - the other known widths, so a 2-char
        # code (Flash 'FA'/'FN') is recovered rather than a truncated 1-char code
        # that would collide with a real 1-char value. A property whose value the
        # short layout does not pin (>1 unknown at once, e.g. a symmetric bench)
        # is left as-is - never guessed.
        if group_layout:
            seed_key = max(
                group_layout, key=lambda k: (len(group_layout[k]), -k[0])
            )
            template = group_layout[seed_key]
            seed_len = seed_key[0]
            seed_sig = seed_key[1]
            order = [pid for pid, _ in sorted(
                template.items(), key=lambda kv: kv[1][0])]
            known: dict[tuple[str, str], str] = {}
            for pid, cc in group_codes[seed_key].items():
                for vid, code in cc.items():
                    known[(pid, vid)] = code
            for aid, head in head_of.items():
                # only same-structure articles: a hidden extra property (e.g.
                # Height on just some types) would otherwise leak its char into
                # the width delta and mis-size the unknown property's code.
                if frozenset(assign[aid].keys()) != seed_sig:
                    continue
                carried = [pid for pid in order if pid in assign[aid]]
                if not carried:
                    continue
                new = [pid for pid in carried
                       if (pid, assign[aid][pid]) not in known]
                delta = len(head) - seed_len
                if len(new) == 1 and delta >= 0:
                    u = new[0]
                    st, w = template[u]
                    code = head[st: st + w + delta]
                    if code:
                        known[(u, assign[aid][u])] = code
            for (pid, vid), code in known.items():
                result.setdefault(pid, {})[vid] = code

        # Phase 3: constant-value inference. A property already positioned in
        # another group (minpos known) may be constant in a different group —
        # its single value's code is the fixed character at that position.
        # Guard: only apply to groups at least as long as the group that
        # established minpos, so shorter-article groups are never mis-read.
        for gkey, aids in by_len.items():
            if len(aids) < 1:
                continue
            group_len = gkey[0]
            for prop in config_props:
                pid = str(prop.id)
                if pid not in minpos:
                    continue
                if group_len < minpos_src_len.get(pid, 0):
                    continue  # shorter than source — position unreliable here
                pos = minpos[pid]
                width = max(
                    (len(c) for c in result.get(pid, {}).values()), default=1
                )
                vids_in_group = {
                    assign[aid].get(pid) for aid in aids
                    if assign[aid].get(pid) is not None
                }
                if len(vids_in_group) != 1:
                    continue  # not constant — already handled or ambiguous
                vid = next(iter(vids_in_group))
                if vid in result.get(pid, {}):
                    continue  # already resolved
                sample = next(
                    (head_of[aid] for aid in aids if aid in head_of), None
                )
                if sample is None or pos + width > len(sample):
                    continue
                code = sample[pos: pos + width]
                if code:
                    result.setdefault(pid, {})[vid] = code

        # Overlap resolution as a SUGGESTION the user can override. A product may
        # carry a duplicate metatype property (e.g. NOALE 'Series' repeats the
        # 'Type' digit plus the line) whose head run overlaps a real property.
        # Dependency properties are never auto-ignored; a non-dependency property
        # whose run is already claimed is auto-suggested for ignoring. The user's
        # per-property decision (config_ignore_overrides) wins over the suggestion.
        pid_name = {str(p.id): (p.name or "") for p in config_props}
        hdo = {
            str(p.id): bool(getattr(p, "has_dependent_options", False))
            for p in config_props
        }
        spans = {
            pid: (
                pos,
                pos + max(
                    (len(c) for c in result.get(pid, {}).values()), default=1
                ),
            )
            for pid, pos in minpos.items() if pid in result
        }
        accepted: dict[str, tuple[int, int]] = {
            pid: sp for pid, sp in spans.items() if hdo.get(pid, False)
        }
        auto_ignore: dict[str, str] = {}
        for pid in sorted(
            (p for p in spans if not hdo.get(p, False)),
            key=lambda p: spans[p][0],
        ):
            st, en = spans[pid]
            hit = next(
                (apid for apid, (ast, aen) in accepted.items()
                 if st < aen and ast < en),
                None,
            )
            if hit is not None:
                auto_ignore[pid] = pid_name.get(hit, "")
            else:
                accepted[pid] = spans[pid]

        overrides = getattr(snapshot, "config_ignore_overrides", None) or {}
        effective_ignore = {
            pid for pid in spans
            if overrides.get(pid, pid in auto_ignore)
        }
        self._slice_hints = {
            pid: {
                "overlaps": auto_ignore.get(pid, ""),
                "auto_ignore": pid in auto_ignore,
                "ignored": pid in effective_ignore,
                "has_dependent_options": hdo.get(pid, False),
                "width": spans[pid][1] - spans[pid][0],
                "position": spans[pid][0],
            }
            for pid in spans
        }
        for pid in effective_ignore:
            result.pop(pid, None)
            minpos.pop(pid, None)

        self._position_layout = {
            pid: {
                "width": max(
                    (len(c) for c in result.get(pid, {}).values()), default=1
                ),
                "position": pos,
            }
            for pid, pos in minpos.items()
        }
        return result

    def unresolved_config_codes(self, snapshot: Snapshot | None) -> list:
        """Configuration attributes the automatic decode could NOT assign.

        A configuration attribute carries no PDM order code; the automation
        (:meth:`resolve_config_codes`) merges correlation with the per-article
        slice. Multi-value config attributes still missing ANY value after that
        are returned here so the user clarifies them before generation - the
        automation then continues. Single-value config attributes are excluded
        (their letter is constant in the base, nothing to correlate). Read-only.
        """
        if snapshot is None:
            return []
        resolved = self.resolve_config_codes(snapshot)
        unresolved = []
        for prop in snapshot.properties:
            values = getattr(prop, "values", [])
            if len(values) < 2:
                continue
            if not getattr(prop, "has_dependent_options", False):
                continue  # non-dependency (identity/metatype): not a config code
            if any((v.code or "").strip() for v in values):
                continue  # coded / partially-coded: not a pure config attribute
            rmap = resolved.get(str(prop.id), {})
            if all(str(v.id) in rmap for v in values):
                continue  # every value resolved
            unresolved.append(prop)
        return unresolved

    def article_dependent_property_ids(self, snapshot: Snapshot | None) -> set[str]:
        """Property ids that are DEPENDENT ON THE ARTICLE.

        Two-level rule (union): a property is article-dependent when PDM flags it
        (``HasDependentOptions`` > 0, the value-level code driver) OR when its
        value actually VARIES across a single product's own articles - i.e. the
        item chooses it (per-article link ``article_property_value_ids``).
        Identity/metatype attributes (constant per product, no dependent options)
        satisfy neither and are excluded. Read-only.
        """
        if snapshot is None:
            return set()
        result = {
            str(p.id)
            for p in snapshot.properties
            if p.id and getattr(p, "has_dependent_options", False)
        }
        apv = snapshot.article_property_value_ids or {}
        if not apv:
            return result
        value_to_prop = {
            str(v.id): str(p.id)
            for p in snapshot.properties for v in p.values if p.id
        }
        articles_by_product: dict[str, list[str]] = {}
        for article in snapshot.articles:
            articles_by_product.setdefault(
                str(article.product_id or ""), []
            ).append(str(article.id))
        for article_ids in articles_by_product.values():
            values_by_prop: dict[str, set[str]] = {}
            for article_id in article_ids:
                for vid in apv.get(article_id, []):
                    prop_id = value_to_prop.get(str(vid))
                    if prop_id is not None:
                        values_by_prop.setdefault(prop_id, set()).add(str(vid))
            for prop_id, value_ids in values_by_prop.items():
                if len(value_ids) > 1:
                    result.add(prop_id)
        return result

    def resolve_config_codes(
        self, snapshot: Snapshot | None
    ) -> dict[str, dict[str, str]]:
        """Authoritative HEAD config-value codes.

        Head config values carry no PDM code, so their code is read from the
        SKU by :meth:`decode_config_codes_by_value_id` (stored value-id grouping;
        exact, never collides, never guesses). Priority per value: a user
        override wins, then the stored code (committed value-id decode), then the
        live value-id decode. Nothing is inferred by correlation or abs(HDO)
        slicing - a value the value-id method cannot place (constant in the load)
        is simply left in the base, never given a wrong code. The parametric TAIL
        is separate and 100% from the stored ``OrderCodeValue`` (not handled here).

        Returns ``{property_id: {value_id: code}}``; absent values are unresolved.
        """
        if snapshot is None:
            return {}
        position = self.decode_config_codes_by_value_id(snapshot)
        overrides = getattr(snapshot, "config_code_overrides", {}) or {}
        config_props = [
            p for p in snapshot.properties
            if p.values
            and not any((v.code or "").strip() for v in p.values)
        ]
        result: dict[str, dict[str, str]] = {}
        ignore = getattr(snapshot, "config_ignore_overrides", None) or {}
        for prop in config_props:
            pid = str(prop.id)
            if ignore.get(pid) is True:
                continue  # user chose to keep this property in the base
            ov = overrides.get(pid, {})
            stored = (getattr(snapshot, "config_value_codes", None) or {}).get(pid, {})
            pos = position.get(pid, {})
            merged: dict[str, str] = {}
            for value in prop.values:
                vid = str(value.id)
                if ov.get(vid):
                    merged[vid] = ov[vid]
                elif stored.get(vid):
                    merged[vid] = stored[vid]
                elif pos.get(vid):
                    merged[vid] = pos[vid]
            if merged:
                result[pid] = merged
        return result

    def commit_config_codes(self, snapshot: Snapshot | None) -> int:
        """Persist auto-resolved config codes as the stored value->code relation
        (``snapshot.config_value_codes``) so slicing and article relations read a
        saved map instead of re-deriving it. Manual overrides are untouched.
        Returns the number of newly stored codes. Read-once at load; idempotent.
        """
        if snapshot is None:
            return 0
        resolved = self.resolve_config_codes(snapshot)
        store = snapshot.config_value_codes
        changed = 0
        for pid, mapping in resolved.items():
            bucket = store.setdefault(pid, {})
            for vid, code in mapping.items():
                if bucket.get(vid) != code:
                    bucket[vid] = code
                    changed += 1
        return changed

    def config_code_layout(self, snapshot: Snapshot | None) -> dict:
        """Per-property head layout from the position decoder: property id ->
        ``{"width": chars, "position": head index}``. Empirical evidence (each
        attribute's owned head positions) for the true code width and order.
        Read-only.
        """
        self.decode_config_codes_by_value_id(snapshot)
        return dict(getattr(self, "_position_layout", {}) or {})

    def config_slice_hints(self, snapshot: Snapshot | None) -> dict:
        """Per head-property slicing advice for the user: property id ->
        ``{overlaps, auto_ignore, ignored, has_dependent_options, width,
        position}``. ``overlaps`` names the property a redundant duplicate
        repeats; ``auto_ignore`` is the automatic suggestion; ``ignored`` is the
        effective decision after the user's ``config_ignore_overrides``. The user
        sets the final call - we only advise. Read-only."""
        self.decode_config_codes_by_value_id(snapshot)
        return dict(getattr(self, "_slice_hints", {}) or {})

    def set_config_ignore(
        self, snapshot: Snapshot | None, property_id: str, ignore: bool
    ) -> None:
        """Record the user's decision to ignore (keep in the base) or slice a
        head property, overriding the automatic suggestion. Invalidates the
        decode cache so the next read re-slices."""
        if snapshot is None or not property_id:
            return
        snapshot.config_ignore_overrides[str(property_id)] = bool(ignore)
        self._valueid_key = None

    def analyze_config_codes(
        self, snapshot: Snapshot | None
    ) -> list[ConfigCodeFinding]:
        """Diagnose the configuration-property order codes and suggest fixes.

        Surfaces the cases the correlation decoder cannot silently resolve:
        values it could not decode, mixed-width codes within one property (e.g.
        ``A`` vs ``FN``/``FA``, which shift later positions), and a declared
        width (``HasDependentOptions``) that disagrees with the real codes.
        Read-only; returns one finding per issue with a suggested resolution.
        """
        findings: list[ConfigCodeFinding] = []
        if snapshot is None:
            return findings
        decoded = self.resolve_config_codes(snapshot)
        for prop in snapshot.properties:
            values = list(getattr(prop, "values", []))
            if len(values) < 2:
                continue
            if not getattr(prop, "has_dependent_options", False):
                continue  # non-dependency (identity/metatype): not a config code
            if any((v.code or "").strip() for v in values):
                continue  # coded / partially-coded: not a pure config attribute
            codes = decoded.get(str(prop.id), {})
            resolved = [
                codes[str(v.id)] for v in values if codes.get(str(v.id))
            ]
            unresolved = [v for v in values if not codes.get(str(v.id))]
            name = prop.name or "(unnamed)"
            pid = str(prop.id or "")

            if unresolved:
                findings.append(ConfigCodeFinding(
                    property_id=pid, property_name=name, kind="unresolved",
                    severity="warning",
                    message=f"{len(unresolved)} of {len(values)} values could not be decoded from the article codes.",
                    suggestion="Load more articles so correlation has evidence, or assign the missing order codes manually.",
                ))

            widths = {len(c) for c in resolved}
            if len(widths) > 1:
                sample = ", ".join(sorted(set(resolved))[:5])
                findings.append(ConfigCodeFinding(
                    property_id=pid, property_name=name, kind="variable_width",
                    severity="info",
                    message=f"Codes have mixed widths ({sample}) - later positions shift.",
                    suggestion="Confirm the codes are correct; the width-agnostic decoder handles the shift, so do not assume a fixed width.",
                ))

            declared = int(getattr(prop, "code_width", 0) or 0)
            if resolved and declared and max(len(c) for c in resolved) != declared:
                findings.append(ConfigCodeFinding(
                    property_id=pid, property_name=name, kind="width_mismatch",
                    severity="info",
                    message=f"Declared width {declared} != actual max {max(len(c) for c in resolved)}.",
                    suggestion="HasDependentOptions is a hint, not a fixed width - trust the decoded codes.",
                ))
        return findings

    @staticmethod
    def _common_prefix(codes: list[str]) -> str:
        """Longest character prefix shared by every non-empty code."""
        codes = [c for c in codes if c]
        if not codes:
            return ""
        prefix = codes[0]
        for code in codes[1:]:
            limit = min(len(prefix), len(code))
            index = 0
            while index < limit and prefix[index] == code[index]:
                index += 1
            prefix = prefix[:index]
            if not prefix:
                break
        return prefix

    def resolve_from_attributes(
        self, snapshot: Snapshot | None, cls: EngineeringClass, remaining: str
    ) -> list[dict]:
        """Like :meth:`resolve_remaining` but resolve the sliced letter against
        the LINKED property's live values (the Attributes/Options codes), so the
        single source of truth for code->value is the source table, not a copy.
        """
        sliced = dict(self.slice_remaining(cls, remaining))
        result: list[dict] = []
        for assignment in cls.properties:
            letters = sliced.get(assignment.property_id, "")
            value, matched = "", False
            if letters:
                for code, name in self._property_values(
                    snapshot, assignment.property_id
                ):
                    if code == letters:
                        value, matched = name, True
                        break
            result.append(
                {
                    "property_id": assignment.property_id,
                    "property_name": assignment.property_name,
                    "letters": letters,
                    "value": value,
                    "matched": matched,
                }
            )
        return result

    @staticmethod
    def _property_values(snapshot: Snapshot | None, property_id: str):
        """(code, value) pairs for a linked property, from Attributes or Options."""
        if snapshot is None:
            return []
        prop = next(
            (p for p in snapshot.properties if p.id == property_id), None
        )
        if prop is not None:
            return [(v.code or "", v.value or "") for v in prop.values]
        option = next(
            (o for o in snapshot.options if o.id == property_id), None
        )
        if option is not None:
            return [(v.code or "", v.value or "") for v in option.values]
        return []

    # -- value management --------------------------------------------------
    def add_value(
        self,
        snapshot: Snapshot | None,
        class_id: str | None,
        property_id: str,
        code: str,
        value: str = "",
        source: str = "manual",
    ) -> ClassValue | None:
        """Add or update a value on a class property (upsert by ``code``)."""
        assignment = self._assignment(snapshot, class_id, property_id)
        if assignment is None:
            return None
        code = (code or "").strip()
        if not code:
            return None
        existing = next((v for v in assignment.values if v.code == code), None)
        if existing is not None:
            existing.value = value
            return existing
        cv = ClassValue(code=code, value=value, source=source)
        assignment.values.append(cv)
        return cv

    def set_value_name(
        self,
        snapshot: Snapshot | None,
        class_id: str | None,
        property_id: str,
        code: str,
        value: str,
    ) -> bool:
        """Rename the value with ``code`` on a class property."""
        assignment = self._assignment(snapshot, class_id, property_id)
        if assignment is None:
            return False
        target = next((v for v in assignment.values if v.code == code), None)
        if target is None:
            return False
        target.value = value or ""
        return True

    def set_value_code(
        self,
        snapshot: Snapshot | None,
        class_id: str | None,
        property_id: str,
        old_code: str,
        new_code: str,
    ) -> bool:
        """Change a value's ``code`` letter (rejects blank/duplicate)."""
        assignment = self._assignment(snapshot, class_id, property_id)
        if assignment is None:
            return False
        new_code = (new_code or "").strip()
        target = next((v for v in assignment.values if v.code == old_code), None)
        if target is None or not new_code:
            return False
        if new_code != old_code and any(
            v.code == new_code for v in assignment.values
        ):
            return False
        target.code = new_code
        return True

    def remove_value(
        self,
        snapshot: Snapshot | None,
        class_id: str | None,
        property_id: str,
        code: str,
    ) -> bool:
        """Remove the value with ``code`` from a class property."""
        assignment = self._assignment(snapshot, class_id, property_id)
        if assignment is None:
            return False
        target = next((v for v in assignment.values if v.code == code), None)
        if target is None:
            return False
        assignment.values.remove(target)
        return True

    def _assignment(self, snapshot, class_id, property_id):
        """Resolve a class property assignment, or ``None``."""
        if (
            snapshot is None
            or snapshot.engineering is None
            or not class_id
            or not property_id
        ):
            return None
        target = self._find_by_id(snapshot.engineering.classes, class_id)
        if target is None:
            return None
        return self._find_property(target, property_id)

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _find_by_id(classes, class_id):
        return next((c for c in classes if c.id == class_id), None)

    @staticmethod
    def _find_by_name(classes, name):
        low = name.casefold()
        return next((c for c in classes if c.name.casefold() == low), None)

    @staticmethod
    def _find_property(cls: EngineeringClass, property_id: str):
        return next(
            (a for a in cls.properties if a.property_id == property_id), None
        )
