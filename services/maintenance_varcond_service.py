"""Maintenance → Pricing Relation → Article VARCOND Relations generation.

Maintenance-only counterpart of :meth:`VarCondService.generate_live`. The
Development workflow keeps using ``generate_live`` untouched.

Incremental (option-suffix) rules follow the legacy
``PriceMaintenance.getOptionIncrementSuffixes`` exactly as read from the
compiled ``PDMMaintenance.exe`` (1.0.9686.24988) IL, not the prefix query used
by ``fetch_item_option_increments`` (which drops every option value whose code
ends in ``#``, i.e. all Fabric type values - the reason
``$VARCOND = '<component> 8=' + Fabric_Type`` rules went missing):

* the item is resolved first - a dotless code that neither ends in ``F`` nor
  starts with ``MET`` becomes ``SELECT TOP 1 Item ... LIKE '<code>%F' AND
  Status = 1 ORDER BY Item``; a code containing ``-`` becomes the (last) parent
  super-item that holds it;
* ``EXEC PDMOptionDataReportWithIncBase @item, @siteId = 1,
  @excludeFabricColours = 1`` - both values are hard-coded constants in the
  legacy method (``ldc.i4.1``), so there is no site selection;
* every returned row with a non-empty ``IncPriceBase`` contributes its
  ``(OptionId, Option2)``; the rows are *not* filtered by component;
* ``execThread`` turns ``Option2`` into a property via
  ``CADMaintenance.ParsePConPropertyName``, applies the HZ13/HZ14 fabric rename,
  de-duplicates by property name and emits ``'<component> <optionId>=' + <name>``.

Cache: the raw PDM rows for each parent article (and each resolved component)
are loaded once and kept in memory. Prefix, exclusion and substitution edits are
applied locally to the cached rows; PDM is read again only for a parent not yet
loaded, after :meth:`clear_cache`, or on an explicit ``refresh``.

Not ported: the family-specific fallbacks ``execThread`` runs when the first
lookup returns nothing (RYMPSH/RYT/RY3VNN...HW/RY2U). They do not apply to the
families verified here and remain only in ``VarCondService``'s opt-in
``legacy_exact`` mode.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

from services.base_service import BaseService
from services.varcond_service import VarCondResult, VarCondRule, VarCondService

INCREMENT_PROCEDURE = "PDMOptionDataReportWithIncBase"
#: Hard-coded by the legacy ``getOptionIncrementSuffixes`` (``ldc.i4.1`` boxed
#: for both ``@siteId`` and ``@excludeFabricColours``).
LEGACY_SITE_ID = 1
LEGACY_EXCLUDE_FABRIC_COLOURS = 1


@dataclass
class ParentSource:
    """Raw PDM rows for one parent article (never mutated after loading)."""

    parent: str
    found: bool = True
    prefix_length: int = 0
    # (SQL-capitalised attribute name, OrderCodeValue) in DisplayOrder.
    attributes: list[tuple[str, str]] = field(default_factory=list)
    # (sub item, quantity, component sequence, FeaturePositionString).
    components: list[tuple[str, int, str, str]] = field(default_factory=list)
    # sub item -> [(option id, Option2)] for every procedure row that carries an
    # increment, in procedure order (before name de-duplication).
    increments: dict[str, list[tuple[int, str]]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


SourceLoader = Callable[[Sequence[str]], "dict[str, ParentSource]"]


class MaintenanceVarCondService(BaseService):
    """Generate Maintenance VARCOND relations from cached legacy source rows."""

    def __init__(self, context=None, loader: SourceLoader | None = None) -> None:
        self.context = context
        self._uses_live_loader = loader is None
        self._loader = loader or self._load_live
        self._cache: dict[str, ParentSource] = {}
        self._increment_cache: dict[str, list[tuple[int, str]]] = {}
        self.load_count = 0          # number of loader invocations (PDM reads)

    # -- cache -------------------------------------------------------------
    def clear_cache(self) -> None:
        self._cache.clear()
        self._increment_cache.clear()

    def has_sources(self, article_codes: Sequence[str]) -> bool:
        """Return whether every requested parent has cached source data."""
        return all(
            (code or "").strip() in self._cache
            for code in article_codes if (code or "").strip()
        )

    def invalidate(self, article_codes: Sequence[str]) -> None:
        """Drop the cached rows of the given parents (and shared components)."""
        for code in article_codes:
            src = self._cache.pop(code, None)
            if src is not None:
                for sub, _q, _s, _f in src.components:
                    self._increment_cache.pop(sub, None)

    def sources_for(
        self, article_codes: Sequence[str], refresh: bool = False,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> list[ParentSource]:
        """Cached sources; optionally report progress for live PDM reads."""
        codes = list(dict.fromkeys(
            (c or "").strip() for c in article_codes if (c or "").strip()
        ))
        if refresh:
            self.invalidate(codes)
        missing = [c for c in codes if c not in self._cache]
        if progress_callback:
            progress_callback(0, len(missing), "")
        if missing:
            self.load_count += 1
            if self._uses_live_loader:
                loaded = self._load_live(missing, progress_callback)
            else:
                loaded = self._loader(missing)
                if progress_callback:
                    progress_callback(len(missing), len(missing), "")
            for code in missing:
                self._cache[code] = loaded.get(code) or ParentSource(
                    parent=code, found=False
                )
        return [self._cache[c] for c in codes]

    # -- generation (local; no PDM access) ---------------------------------
    def generate(
        self,
        article_codes: Sequence[str],
        prefix: str = "",
        property_exclusions: str = "",
        property_substitutions: str = "",
        refresh: bool = False,
    ) -> VarCondResult:
        result = VarCondResult()
        codes = [c for c in article_codes if (c or "").strip()]
        if not codes:
            result.warnings.append("No parent article codes selected.")
            return result
        vc = VarCondService.__new__(VarCondService)
        vc.context = self.context
        for src in self.sources_for(codes, refresh=refresh):
            result.warnings.extend(src.warnings)
            if src.found:
                self._emit_parent(
                    vc, src, result, prefix, property_exclusions, property_substitutions
                )
        # Legacy emits repeated definitions and preserves order.
        if result.rules:
            result.text = ",\r\n".join(rule.rule for rule in result.rules) + "\r\n"
        return result

    @staticmethod
    def _suffix_entries(
        parent_sub: str, rows: list[tuple[int, str]], substitutions: str
    ) -> list[tuple[int, str]]:
        """``execThread``: ParsePConPropertyName, HZ13/HZ14 fabric rename,
        de-duplicate by name, then plain-replace substitutions."""
        entries: list[tuple[int, str]] = []
        names: list[str] = []
        for option_id, option_name in rows:
            name = VarCondService._parse_pcon_property_name(option_name)
            if "fabric" in name.lower() and parent_sub.startswith(("HZ13", "HZ14")):
                name = (
                    "Upper_Front_Fabric_Type" if parent_sub.startswith("HZ13")
                    else "Lower_Front_Fabric_Type"
                )
            if name in names:
                continue
            names.append(name)
            entries.append((int(option_id), name))
        for token in (substitutions or "").split(","):
            if not token or "=" not in token:
                continue
            old, new = token.split("=", 1)
            if old == "":
                continue
            entries = [
                (oid, name.replace(old, new) if old in name else name)
                for oid, name in entries
            ]
        return entries

    @classmethod
    def _emit_parent(
        cls, vc: VarCondService, src: ParentSource, result: VarCondResult,
        prefix: str, exclusions: str, substitutions: str,
    ) -> None:
        if not src.components:
            return
        parts: list[str] = []
        for raw_prop, order_code in src.attributes:
            prop = vc._pcon_property_name(raw_prop, src.parent)
            if exclusions and prop in exclusions:
                if prop not in result.excluded:
                    result.excluded.append(prop)
                continue
            prop = vc._apply_substitutions(prop, substitutions)
            value = (order_code or "").replace(".", "")
            parts.append(f"{(prefix.strip() + '.') if prefix.strip() else ''}{prop} = '{value}'")
        body = "IF" + ((" " + " AND ".join(parts)) if parts else "")

        for sub, qty, _seq, _fps in src.components:
            if not sub:
                continue
            result.rules.append(
                VarCondRule(article=sub, body=body, rule=f"$VARCOND = '{sub}' {body}")
            )
            if qty > 1:
                result.rules.append(VarCondRule(
                    article=sub, body=body,
                    rule=f"$SET_PRICING_FACTOR('{sub}', {qty}) {body}",
                ))
            for option_id, name in cls._suffix_entries(
                sub, src.increments.get(sub, []), substitutions
            ):
                suffix = f"'{sub} {option_id}=' + {name}"
                result.rules.append(VarCondRule(
                    article=sub, body=body, rule=f"$VARCOND = {suffix} {body}"
                ))
                if qty > 1:
                    result.rules.append(VarCondRule(
                        article=sub, body=body,
                        rule=f"$SET_PRICING_FACTOR({suffix}, {qty}) {body}",
                    ))

    # -- live PDM access (read-only) ---------------------------------------
    _ATTR_SQL = (
        "SELECT DISTINCT Product.Product, "
        "CASE WHEN ABS(attr.HasDependentOptions) > 0 THEN "
        "SUBSTRING(Item.Item, ? + 1 + (SELECT COALESCE((SELECT SUM(ABS(attr2.HasDependentOptions)) "
        "FROM Item i2 INNER JOIN BaseAttributeValues bav2 ON i2.ItemId = bav2.ItemId "
        "INNER JOIN AttributeValue atval2 ON bav2.AttributeValueId = atval2.AttributeValueId "
        "INNER JOIN Attribute attr2 ON atval2.AttributeId = attr2.AttributeId "
        "WHERE i2.Item = ? AND (atval2.OrderCodeValue IS NOT NULL OR ABS(attr2.HasDependentOptions) <> 0) "
        "AND attr2.DisplayOrder < attr.DisplayOrder), 0)), ABS(attr.HasDependentOptions)) "
        "ELSE atval.OrderCodeValue END AS OrderCodeValue, attr.DisplayOrder, "
        "CASE WHEN CHARINDEX(' ', attr.Name) > 0 THEN "
        "SUBSTRING(attr.Name, 1, CHARINDEX(' ', attr.Name)) + "
        "UPPER(SUBSTRING(attr.Name, CHARINDEX(' ', attr.Name) + 1, 1)) + "
        "SUBSTRING(attr.Name, CHARINDEX(' ', attr.Name) + 2, 99) ELSE attr.Name END AS prop "
        "FROM Product INNER JOIN Item ON Product.ProductId = Item.ProductId "
        "INNER JOIN BaseAttributeValues bav ON Item.ItemId = bav.ItemId "
        "INNER JOIN AttributeValue atval ON bav.AttributeValueId = atval.AttributeValueId "
        "INNER JOIN Attribute attr ON atval.AttributeId = attr.AttributeId "
        "WHERE Item.Item = ? AND (atval.OrderCodeValue IS NOT NULL OR ABS(attr.HasDependentOptions) > 0) "
        "ORDER BY attr.DisplayOrder"
    )

    def _load_live(
        self, codes: Sequence[str],
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> dict[str, ParentSource]:
        """Read live PDM sources with batched parent and BOM queries.

        Parent metadata, BOM rows and category master notes are fetched in
        bounded batches. Attribute rows and the legacy increment procedure
        remain per-parent/per-unique-component to preserve their exact SQL and
        stored-procedure semantics.
        """
        from repositories.pdm_repository import PDMRepository

        repo = PDMRepository(self.context)
        conn = repo.get_connection()
        out: dict[str, ParentSource] = {}
        try:
            total = len(codes)
            # SQL Server's parameter limit is 2,100; use 500-code chunks to
            # leave ample room for future query parameters.
            chunk_size = min(getattr(repo, "_IN_CHUNK", 500), 500)
            for offset in range(0, total, chunk_size):
                chunk = list(codes[offset:offset + chunk_size])
                placeholders = repo._placeholders(len(chunk))
                item_rows = repo._execute(
                    "SELECT i.ItemId, i.Item, i.Notes, pr.ProductCategoryId "
                    "FROM Item i INNER JOIN Product p ON i.ProductId = p.ProductId "
                    "INNER JOIN ProductRange pr ON p.ProductRangeId = pr.ProductRangeId "
                    f"WHERE i.Item IN ({placeholders})",
                    tuple(chunk), connection=conn,
                )
                by_code = {str(row.Item): row for row in item_rows}
                sources = {code: ParentSource(parent=code) for code in chunk}
                for code, src in sources.items():
                    if code not in by_code:
                        src.found = False
                        src.warnings.append(f"{code}: article was not found in live PDM.")

                item_id_to_code = {
                    row.ItemId: str(row.Item) for row in item_rows
                }
                item_ids = list(item_id_to_code)
                if item_ids:
                    for id_chunk in repo._chunked(item_ids, chunk_size):
                        id_placeholders = repo._placeholders(len(id_chunk))
                        component_rows = repo._execute(
                            "SELECT itco.ItemId AS ParentItemId, sub.Item AS SubItem, "
                            "itco.Quantity, itco.ComponentSequence, "
                            "itco.FeaturePositionString "
                            "FROM ItemComponents itco "
                            "INNER JOIN Item sub ON itco.SubItemId = sub.ItemId "
                            f"WHERE itco.ItemId IN ({id_placeholders}) "
                            "ORDER BY itco.ItemId, CONVERT(INT, itco.ComponentSequence)",
                            tuple(id_chunk), connection=conn,
                        )
                        for comp in component_rows:
                            parent = item_id_to_code.get(comp.ParentItemId)
                            if parent is None:
                                continue
                            try:
                                qty = int(getattr(comp, "Quantity", 1) or 1)
                            except (TypeError, ValueError):
                                qty = 1
                            sources[parent].components.append((
                                str(comp.SubItem or "").strip(), qty,
                                str(comp.ComponentSequence or ""),
                                str(comp.FeaturePositionString or ""),
                            ))

                # Resolve category fallback notes once for the whole batch.
                category_ids = list(dict.fromkeys(
                    getattr(row, "ProductCategoryId", None)
                    for row in item_rows
                    if getattr(row, "ProductCategoryId", None) is not None
                ))
                master_notes: dict[object, str] = {}
                if category_ids:
                    for master in repo.fetch_category_master_notes(
                        category_ids, connection=conn
                    ):
                        category_id = getattr(master, "ProductCategoryId", None)
                        if category_id not in master_notes:
                            master_notes[category_id] = str(
                                getattr(master, "Notes", "") or ""
                            )

                # Resolve per-parent prefix lengths before loading attributes
                # in a single bounded query per batch.
                for code in chunk:
                    src = sources[code]
                    item = by_code.get(code)
                    if item is None or not src.components:
                        continue
                    notes = str(getattr(item, "Notes", "") or "").split(",")[0].strip()
                    if notes.isdigit():
                        src.prefix_length = int(notes)
                    if src.prefix_length <= 0:
                        category_id = getattr(item, "ProductCategoryId", None)
                        token = master_notes.get(category_id, "").split(",")[0].strip()
                        if token.isdigit():
                            src.prefix_length = int(token)
                    if src.prefix_length <= 0:
                        src.warnings.append(
                            f"{code}: article prefix length is undefined; "
                            "parametric codes may be incorrect."
                        )

                self._load_attributes_batch(repo, conn, sources)

                # Increment pricing suffixes come from a legacy stored procedure
                # that is called once per unique component and cannot be safely
                # replaced by the snapshot's differently-filtered increment query.
                for code in chunk:
                    src = sources[code]
                    if src.found and src.components:
                        for sub, _qty, _seq, _fps in src.components:
                            if sub and sub not in src.increments:
                                if sub not in self._increment_cache:
                                    self._increment_cache[sub] = self._fetch_increments(
                                        repo, conn, sub
                                    )
                                src.increments[sub] = self._increment_cache[sub]
                    out[code] = src
                    if progress_callback:
                        progress_callback(len(out), total, code)
        finally:
            conn.close()
        return out

    def _load_attributes_batch(self, repo, conn, sources: dict[str, ParentSource]) -> None:
        """Load the existing attribute projection for many parents per query.

        The legacy attribute SQL is retained; only its item-specific prefix
        length and item predicates are supplied through a VALUES input table.
        """
        codes = [
            code for code, src in sources.items()
            if src.found and src.components
        ]
        if not codes:
            return
        chunk_size = min(getattr(repo, "_IN_CHUNK", 500) // 2, 250)
        for code_chunk in repo._chunked(codes, chunk_size):
            values_sql = ", ".join("(?, ?)" for _ in code_chunk)
            params = []
            for code in code_chunk:
                params.extend((code, sources[code].prefix_length))
            query = self._ATTR_SQL
            query = query.replace(
                "SELECT DISTINCT Product.Product, ",
                "SELECT DISTINCT Item.Item AS ParentArticle, ",
                1,
            )
            query = query.replace(
                "SUBSTRING(Item.Item, ? + 1 +",
                "SUBSTRING(Item.Item, src.PrefixLength + 1 +",
                1,
            )
            query = query.replace(
                "WHERE i2.Item = ? AND",
                "WHERE i2.Item = Item.Item AND",
                1,
            )
            query = query.replace(
                "FROM Product INNER JOIN Item ON Product.ProductId = Item.ProductId ",
                "FROM Product INNER JOIN Item ON Product.ProductId = Item.ProductId "
                f"INNER JOIN (VALUES {values_sql}) "
                "AS src(ItemCode, PrefixLength) ON src.ItemCode = Item.Item ",
                1,
            )
            query = query.replace(
                "WHERE Item.Item = ? AND",
                "WHERE Item.Item = src.ItemCode AND",
                1,
            )
            rows = repo._execute(query, tuple(params), connection=conn)
            for row in rows:
                parent = str(getattr(row, "ParentArticle", "") or "")
                src = sources.get(parent)
                if src is not None:
                    src.attributes.append((
                        str(getattr(row, "prop", "") or ""),
                        str(getattr(row, "OrderCodeValue", "") or ""),
                    ))

    def _load_parent(self, repo, conn, parent: str) -> ParentSource:
        src = ParentSource(parent=parent)
        rows = repo._execute(
            "SELECT i.ItemId, i.Notes, pr.ProductCategoryId "
            "FROM Item i INNER JOIN Product p ON i.ProductId = p.ProductId "
            "INNER JOIN ProductRange pr ON p.ProductRangeId = pr.ProductRangeId "
            "WHERE i.Item = ?", (parent,), connection=conn,
        )
        if not rows:
            src.found = False
            src.warnings.append(f"{parent}: article was not found in live PDM.")
            return src
        item = rows[0]
        comp_rows = repo._execute(
            "SELECT sub.Item AS SubItem, itco.Quantity, itco.ComponentSequence, "
            "itco.FeaturePositionString "
            "FROM ItemComponents itco INNER JOIN Item sub ON itco.SubItemId = sub.ItemId "
            "WHERE itco.ItemId = ? ORDER BY CONVERT(INT, itco.ComponentSequence)",
            (item.ItemId,), connection=conn,
        )
        if not comp_rows:
            return src                      # no BOM -> no rules (as generate_live)
        for comp in comp_rows:
            try:
                qty = int(getattr(comp, "Quantity", 1) or 1)
            except (TypeError, ValueError):
                qty = 1
            src.components.append((
                str(comp.SubItem or "").strip(), qty,
                str(comp.ComponentSequence or ""),
                str(comp.FeaturePositionString or ""),
            ))

        # CADMaintenance.getArticlePrefixLength (same as generate_live).
        notes = str(getattr(item, "Notes", "") or "").split(",")[0].strip()
        if notes.isdigit():
            src.prefix_length = int(notes)
        category_id = getattr(item, "ProductCategoryId", None)
        if src.prefix_length <= 0 and category_id is not None:
            for master in repo.fetch_category_master_notes([category_id], connection=conn):
                token = str(getattr(master, "Notes", "") or "").split(",")[0].strip()
                if token.isdigit():
                    src.prefix_length = int(token)
                    break
        if src.prefix_length <= 0:
            src.warnings.append(
                f"{parent}: article prefix length is undefined; parametric codes may be incorrect."
            )

        for attr in repo._execute(
            self._ATTR_SQL, (src.prefix_length, parent, parent), connection=conn
        ):
            src.attributes.append((
                str(getattr(attr, "prop", "") or ""),
                str(getattr(attr, "OrderCodeValue", "") or ""),
            ))
        for sub, _qty, _seq, _fps in src.components:
            if sub and sub not in src.increments:
                if sub not in self._increment_cache:
                    self._increment_cache[sub] = self._fetch_increments(repo, conn, sub)
                src.increments[sub] = self._increment_cache[sub]
        return src

    @staticmethod
    def _resolve_item(repo, conn, my: str) -> str:
        """Legacy ``getOptionIncrementSuffixes`` item resolution (IL offsets 24-278)."""
        if "." not in my.strip(".") and not my.endswith("F") and not my.startswith("MET"):
            for row in repo._execute(
                "SELECT TOP 1 Item FROM Item WHERE Item LIKE ? AND Status = 1 ORDER BY Item",
                (my + "%F",), connection=conn,
            ):
                my = str(row.Item)
        if "-" in my:
            for row in repo._execute(
                "SELECT Item.Item FROM Item INNER JOIN ItemComponents itco "
                "ON Item.ItemId = itco.ItemId INNER JOIN Item sub_item "
                "ON itco.SubItemId = sub_item.ItemId WHERE sub_item.Item = ?",
                (my,), connection=conn,
            ):
                my = str(row.Item)           # legacy keeps the last row
        return my

    def _fetch_increments(self, repo, conn, sub: str) -> list[tuple[int, str]]:
        """``(OptionId, Option2)`` of every procedure row with a non-empty
        ``IncPriceBase`` for the legacy-resolved item (site/exclusion constants
        from the legacy IL; no component filter, as in legacy)."""
        item = self._resolve_item(repo, conn, sub)
        cursor = conn.cursor()
        try:
            cursor.execute(
                f"EXEC dbo.{INCREMENT_PROCEDURE} @item = ?, @siteId = ?, "
                "@excludeFabricColours = ?",
                (item, LEGACY_SITE_ID, LEGACY_EXCLUDE_FABRIC_COLOURS),
            )
            # The procedure emits several result sets (temp-table inserts);
            # advance to the one carrying IncPriceBase.
            while True:
                if cursor.description is not None:
                    names = [c[0] for c in cursor.description]
                    if "IncPriceBase" in names:
                        break
                if not cursor.nextset():
                    return []
            ix = {n.lower(): i for i, n in enumerate(names)}
            out: list[tuple[int, str]] = []
            for row in cursor.fetchall():
                option_id = row[ix["optionid"]]
                inc = row[ix["incpricebase"]]
                if option_id is None or inc is None or str(inc) == "":
                    continue
                out.append((int(option_id), str(row[ix["option2"]] or "")))
            return out
        finally:
            cursor.close()
