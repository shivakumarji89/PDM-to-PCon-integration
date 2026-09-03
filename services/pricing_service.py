"""Option increment pricing report (offline, from PDM data).

Companion to :mod:`services.varcond_service`. It reports the option-increment
prices (PDM ``ItemOptionValues.IncrementalPrice``) that PDM's *Update pCon
Prices* button applies, per super product and sub-item, straight from the active
snapshot - no database access.

Base article ``$PRICE`` values run through PDM's ``PriceMatrix`` /
``PriceFormula`` / region-``BasePrice`` engine (currency- and site-specific) and
are a separate subsystem; they are NOT included here yet. This report covers the
directly portable increment prices only.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Sequence

from models.price_record import PriceRecord
from models.snapshot import Snapshot
from repositories.pdm_repository import PDMRepository
from services.base_service import BaseService
from services.varcond_service import VarCondService


@dataclass
class PricingLine:
    """One option-value increment price for a sub-item."""

    sub_item: str
    option_id: int | None
    option_name: str
    value_name: str
    code: str
    increment: float | None


@dataclass
class PricingResult:
    """Result of a pricing report run."""

    lines: list[PricingLine] = field(default_factory=list)
    text: str = ""
    warnings: list[str] = field(default_factory=list)


@dataclass
class PriceParams:
    """User inputs mirroring PDM's *Update pCon Prices* form."""

    currency: str = "GBP"           # currency_selector
    mydate: str = ""                # DateTimePicker1, PDM 'dd-MMM-yyyy'
    site_id: int = 1               # site_selector
    valid_from: str = ""            # com_PriceValidFrom
    valid_to: str = ""              # com_PriceValidTo


@dataclass
class PriceComputeResult:
    """Outcome of a price computation - the records plus what could not resolve."""

    records: list[PriceRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)


@dataclass
class PriceDiff:
    """Year-over-year comparison of two price baselines."""

    added: list[PriceRecord] = field(default_factory=list)
    changed: list[tuple[PriceRecord, PriceRecord]] = field(default_factory=list)
    removed: list[PriceRecord] = field(default_factory=list)
    unchanged: int = 0

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.changed or self.removed)


class PricingService(BaseService):
    """Report option-increment prices for super products, offline (PDM data)."""

    def generate(self, snapshot: Snapshot | None = None) -> PricingResult:
        """Build the option-increment pricing report from the active snapshot.

        Walks each super product's ``ItemComponents`` sub-items and lists the
        option-value increment prices carried by each sub-item's item prefix.
        """
        snapshot = snapshot if snapshot is not None else self.context.active_snapshot
        result = PricingResult()
        if snapshot is None:
            result.warnings.append("No active snapshot.")
            return result

        components = snapshot.article_components or {}
        increments_by_prefix = snapshot.option_increments or {}
        code_by_id = {
            str(a.id): (a.code or "")
            for a in snapshot.articles
            if a.id is not None
        }

        if not components:
            result.warnings.append(
                "No super-product BOM loaded (ItemComponents) - nothing to price."
            )
        if not increments_by_prefix:
            result.warnings.append(
                "No option increment prices loaded (ItemOptionValues)."
            )

        blocks: list[str] = []
        for article_id, comps in components.items():
            super_code = code_by_id.get(str(article_id), str(article_id))
            block_lines: list[str] = [f"# {super_code}"]
            for comp in comps:
                sub = (comp.get("sub_item") or "").strip()
                if not sub:
                    continue
                incs = increments_by_prefix.get(VarCondService._item_prefix(sub), [])
                if not incs:
                    continue
                block_lines.append(f"  {sub}")
                for inc in incs:
                    line = PricingLine(
                        sub_item=sub,
                        option_id=inc.get("option_id"),
                        option_name=inc.get("option_name", ""),
                        value_name=inc.get("value_name", ""),
                        code=inc.get("code", ""),
                        increment=inc.get("increment"),
                    )
                    result.lines.append(line)
                    inc_text = "" if line.increment is None else f"{line.increment:g}"
                    block_lines.append(
                        f"    [{line.option_id}] {line.option_name} / "
                        f"{line.value_name} ({line.code}) = {inc_text}"
                    )
            if len(block_lines) > 1:
                blocks.append("\r\n".join(block_lines))

        result.text = "\r\n\r\n".join(blocks)
        return result

    # -- price computation (PDM parity, batched) ---------------------------

    def target_currencies(
        self, snapshot: Snapshot, params: PriceParams
    ) -> list[str]:
        """Currencies to compute: the distinct currencies of the snapshot's
        defined price lists (so both EUR and GBP are pulled from PDM and aligned
        to their lists), or the single selected currency when no lists exist."""
        curs: list[str] = []
        for pl in (getattr(snapshot, "price_lists", None) or []):
            c = (pl.currency or "").upper()
            if c and c not in curs:
                curs.append(c)
        if curs:
            return curs
        sel = (params.currency or "").upper()
        return [sel] if sel else ["GBP"]

    def compute(
        self, params: PriceParams, snapshot: Snapshot | None = None
    ) -> PriceComputeResult:
        """Compute OCD price records for the active snapshot (PDM-accurate).

        Classifies every article as super (global) or plain (article) pricing,
        then pulls base and increment prices from PDM in a few batched queries -
        the values are computed by SQL Server's own ``fnGetListPrice*`` functions,
        so they are byte-identical to PDM's *Update pCon Prices* output. Runs once
        per price-list currency (EUR + GBP + ...) so every list gets its records,
        fills ``snapshot.price_records`` (the persisted baseline) and returns it.
        """
        snapshot = snapshot if snapshot is not None else self.context.active_snapshot
        result = PriceComputeResult()
        if snapshot is None:
            result.warnings.append("No active snapshot.")
            return result

        items, super_codes = self._price_plan(snapshot)
        if not items:
            result.warnings.append("No articles to price.")
            return result

        prefix_by_item = self._prefix_by_item(snapshot)
        currencies = self.target_currencies(snapshot, params)

        all_records: list[PriceRecord] = []
        unresolved: list[str] = []
        repo = PDMRepository(self.context)
        conn = repo.get_connection()
        try:
            for cur in currencies:
                cparams = replace(params, currency=cur)
                base_rows = repo.fetch_item_base_prices(
                    items,
                    cur,
                    params.mydate,
                    connection=conn,
                    site_id=params.site_id,
                )
                # Increments for every item: non-super -> article upcharge, super
                # -> global increment (both pulled from the same computed query).
                inc_rows = repo.fetch_item_option_increment_prices(
                    items, cur, params.mydate, params.site_id, conn
                )
                records, unres = self.build_records(
                    base_rows, inc_rows, super_codes, prefix_by_item, cparams
                )
                all_records.extend(records)
                unresolved.extend(unres)
        finally:
            conn.close()

        snapshot.price_records = self._accumulate_currencies(
            snapshot.price_records, all_records, currencies
        )
        result.records = all_records
        result.unresolved = unresolved
        if unresolved:
            result.warnings.append(
                f"{len(unresolved)} item(s) had no resolvable PDM list price."
            )
        return result

    def compute_streaming(
        self,
        params: PriceParams,
        snapshot: Snapshot | None = None,
        on_batch=None,
        batch_size: int = 250,
        reporter=None,
    ) -> PriceComputeResult:
        """Like :meth:`compute`, but fetch and build in item batches so the UI
        can show records as they arrive instead of waiting for the whole run.

        Each batch pulls its own base + increment prices on one shared
        connection and calls ``on_batch(records)`` with the freshly built
        records. Byte-identical to :meth:`compute` (same SQL functions, same
        classification) - only the delivery is incremental.
        """
        snapshot = snapshot if snapshot is not None else self.context.active_snapshot
        result = PriceComputeResult()
        if snapshot is None:
            result.warnings.append("No active snapshot.")
            return result

        items, super_codes = self._price_plan(snapshot)
        if not items:
            result.warnings.append("No articles to price.")
            return result

        prefix_by_item = self._prefix_by_item(snapshot)
        currencies = self.target_currencies(snapshot, params)

        # Item -> owning product, so the popup can climb a "products priced"
        # count alongside items and records.
        product_by_item = {
            a.code: str(a.product_id)
            for a in snapshot.articles
            if a.code is not None and a.product_id is not None
        }
        total_products = len({str(a.product_id) for a in snapshot.articles
                              if a.product_id is not None})
        products_seen: set[str] = set()

        all_records: list[PriceRecord] = []
        unresolved: list[str] = []
        n = len(items)
        step = max(1, batch_size)
        ncur = max(1, len(currencies))
        # Start progress BEFORE opening the connection so the popup shows a live
        # "Connecting..." step (and creeps) instead of sitting blank at 0% while
        # the potentially slow PDM connection is established.
        if reporter is not None:
            batches = (n + step - 1) // step
            reporter.begin(batches * ncur + 1, title="Computing Prices",
                           subject=" + ".join(currencies) or params.currency)
            reporter.advance("Connecting to PDM...")

        repo = PDMRepository(self.context)
        conn = repo.get_connection()
        try:
            for cur in currencies:
                cparams = replace(params, currency=cur)
                for start in range(0, n, step):
                    chunk = items[start:start + step]
                    base_rows = repo.fetch_item_base_prices(
                        chunk, cur, params.mydate, conn
                    )
                    inc_rows = repo.fetch_item_option_increment_prices(
                        chunk, cur, params.mydate, params.site_id, conn
                    )
                    recs, unres = self.build_records(
                        base_rows, inc_rows, super_codes, prefix_by_item, cparams
                    )
                    all_records.extend(recs)
                    unresolved.extend(unres)
                    if on_batch is not None and recs:
                        on_batch(recs)
                    if reporter is not None:
                        processed = min(start + step, n)
                        for code in chunk:
                            pid = product_by_item.get(code)
                            if pid:
                                products_seen.add(pid)
                        reporter.advance(f"Pricing {cur} {processed}/{n} items...")
                        reporter.set_metrics([
                            ("items", "Items Priced", processed, f" / {n}"),
                            ("records", "Price Records", len(all_records), ""),
                            ("products", "Products", len(products_seen),
                             f" / {total_products}"),
                            ("unresolved", "Unresolved", len(unresolved), ""),
                        ])
        finally:
            conn.close()

        snapshot.price_records = self._accumulate_currencies(
            snapshot.price_records, all_records, currencies
        )
        result.records = all_records
        result.unresolved = unresolved
        if unresolved:
            result.warnings.append(
                f"{len(unresolved)} item(s) had no resolvable PDM list price."
            )
        if reporter is not None:
            reporter.finish(
                True, f"Priced {n} items \u00b7 {len(all_records)} records"
            )
        return result

    @staticmethod
    def _accumulate_currencies(
        existing: Sequence[Any], new: Sequence[Any], currencies: Sequence[str]
    ) -> list[Any]:
        """Replace every computed currency in the persisted records, keeping any
        other currencies so untouched price lists stay intact."""
        curs = {(c or "").upper() for c in currencies}
        kept = [r for r in existing if (r.currency or "").upper() not in curs]
        return kept + list(new)

    @staticmethod
    def _accumulate_by_currency(
        existing: Sequence[Any], new: Sequence[Any], currency: str
    ) -> list[Any]:
        """Replace only this run's currency in the persisted records, keeping other
        currencies so multiple price lists (e.g. EUR + GBP) coexist in one snapshot."""
        cur = (currency or "").upper()
        kept = [r for r in existing if (r.currency or "").upper() != cur]
        return kept + list(new)

    @staticmethod
    def build_records(
        base_rows: Sequence[Any],
        inc_rows: Sequence[Any],
        super_codes: set[str],
        prefix_by_item: dict[str, str],
        params: PriceParams,
    ) -> tuple[list[PriceRecord], list[str]]:
        """Turn PDM price rows into OCD ``PriceRecord``s (pure, no DB access).

        Base rows become either a ``tCOMd_GlobalPrice`` row (super product,
        variant condition = the full item) or a ``tCOMd_Price`` level-``B`` base
        record. Increment rows become level-``X`` upcharges keyed to the base
        article, with PDM's ``" {OptionId}={Code}"`` variant-condition format.
        """
        records: list[PriceRecord] = []
        unresolved: list[str] = []
        for row in base_rows:
            item = str(row.Item)
            raw = row.price
            if raw is None or str(raw).strip() == "":
                unresolved.append(item)
                continue
            value = float(raw)
            if item in super_codes:
                records.append(
                    PriceRecord(
                        is_global=True,
                        article_code="",
                        variant_condition=item,
                        level="",
                        value=value,
                        currency=params.currency,
                        valid_from=params.valid_from,
                        valid_to=params.valid_to,
                    )
                )
            else:
                # Slice the article number at the set base length: the base
                # article is the prefix; the trailing dimension characters become
                # the base price variant condition (PDM: NOALE2 + "11").
                prefix = prefix_by_item.get(item) or item
                sliced = item[len(prefix):] if item.startswith(prefix) else ""
                records.append(
                    PriceRecord(
                        is_global=False,
                        article_code=prefix,
                        variant_condition=sliced,
                        level="B",
                        value=value,
                        currency=params.currency,
                        valid_from=params.valid_from,
                        valid_to=params.valid_to,
                    )
                )

        for row in inc_rows:
            item = str(row.Item)
            raw = row.IncPrice
            if raw is None or str(raw).strip() == "":
                continue
            code = str(row.Code).replace("#", "")
            if item in super_codes:
                # Super product increment -> global, full item code (no slicing),
                # matching PDM: "DTWB1E3.C 3785=CD".
                records.append(
                    PriceRecord(
                        is_global=True,
                        article_code="",
                        variant_condition=f"{item} {row.OptionId}={code}",
                        level="",
                        value=float(raw),
                        currency=params.currency,
                        valid_from=params.valid_from,
                        valid_to=params.valid_to,
                    )
                )
                continue
            prefix = prefix_by_item.get(item) or PricingService._article_prefix(
                item, None
            )
            suffix = item[len(prefix):] if item.startswith(prefix) else ""
            varcond = f"{suffix} {row.OptionId}={code}"
            records.append(
                PriceRecord(
                    is_global=False,
                    article_code=prefix,
                    variant_condition=varcond,
                    level="X",
                    value=float(raw),
                    currency=params.currency,
                    valid_from=params.valid_from,
                    valid_to=params.valid_to,
                )
            )
        return records, unresolved

    @staticmethod
    def diff(
        baseline: Sequence[PriceRecord], current: Sequence[PriceRecord]
    ) -> PriceDiff:
        """Compare two price baselines (year-over-year): what to push to OCD.

        Keys on everything but the value, so only genuinely changed cells fall
        into ``changed``; unchanged cells are counted and skipped on export.
        """
        base_by_key = {r.key(): r for r in baseline}
        cur_by_key = {r.key(): r for r in current}
        out = PriceDiff()
        for key, rec in cur_by_key.items():
            prev = base_by_key.get(key)
            if prev is None:
                out.added.append(rec)
            elif prev.value != rec.value:
                out.changed.append((prev, rec))
            else:
                out.unchanged += 1
        for key, rec in base_by_key.items():
            if key not in cur_by_key:
                out.removed.append(rec)
        return out

    # -- classification helpers --------------------------------------------

    @staticmethod
    def _article_prefix(item: str, prefix_length: int | None) -> str:
        """Base article prefix (PDM ``text3``): fixed length, else up to first ``.``."""
        item = item or ""
        if prefix_length and 0 < prefix_length <= len(item):
            return item[:prefix_length]
        dot = item.find(".")
        if -1 < dot < len(item) - 1:
            return item[: dot + 1]
        return item

    def _prefix_by_item(self, snapshot: Snapshot) -> dict[str, str]:
        """Map each article code to its base prefix (PDM ``text3``).

        The prefix length is the article set's ``base_length`` (the tool's
        authoritative slice point, equivalent to PDM's ``Item.Notes`` prefix
        length): base article = ``code[:base_length]`` and the remaining
        characters become the price variant condition (dimension codes). Falls
        back to the PDM ``article_prefix_length`` and then the ``.`` rule for any
        article not covered by a set.
        """
        out: dict[str, str] = {}
        overrides = getattr(snapshot, "base_length_overrides", None) or {}
        code_by_id = {str(a.id): a.code for a in snapshot.articles if a.code}
        for s in snapshot.article_sets:
            blen = s.base_length or 0
            for aid in s.article_ids:
                code = code_by_id.get(str(aid))
                if not code:
                    continue
                out[code] = self._sliced_base(code, overrides, blen)
        len_by_id = snapshot.article_prefix_length or {}
        for a in snapshot.articles:
            if a.code and a.code not in out:
                ov = overrides.get(a.code)
                if ov and 0 < ov < len(a.code):
                    out[a.code] = a.code[:ov]
                else:
                    out[a.code] = self._article_prefix(a.code, len_by_id.get(str(a.id)))
        return out

    @staticmethod
    def _sliced_base(code: str, overrides: dict[str, int], base_length: int) -> str:
        """Base article for a code: the registry override when present (standardise
        to CAD), else the article-set base length."""
        ov = overrides.get(code)
        if ov and 0 < ov < len(code):
            return code[:ov]
        return code[:base_length] if 0 < base_length < len(code) else code

    def _super_product_ids(self, snapshot: Snapshot) -> set[str]:
        """Ids of the snapshot's super products (drives global pricing)."""
        return {
            str(p.id)
            for p in self._snapshot_products(snapshot)
            if getattr(p, "id", None) is not None
            and getattr(p, "is_super_product", False)
        }

    def _super_item_codes(self, snapshot: Snapshot) -> set[str]:
        """Article codes whose product is a super product.

        Super pricing is decided by the PRODUCT, not the individual item; the
        per-item ``is_super_item`` flag and the ``ItemComponents`` BOM are not
        used for this decision.
        """
        super_pids = self._super_product_ids(snapshot)
        if not super_pids:
            return set()
        return {
            a.code for a in snapshot.articles
            if a.code and str(a.product_id) in super_pids
        }

    def _price_plan(self, snapshot: Snapshot) -> tuple[list[str], set[str]]:
        """Return ``(items_to_price, super_codes)`` for a compute run.

        A non-super product prices each of its articles as a sliced article
        (base + upcharge). A super product does NOT price its own super item;
        instead it prices its ``ItemComponents`` - every component article
        number is fetched and emitted as a GLOBAL price (the component code is
        the variant condition), carrying that component's option increments.
        This mirrors PDM's per-component super-product price report.

        A super item is any BOM parent (it has components) or an article of a
        super product - PDM sets IsSuperProduct iff an item has components, so
        the two are equivalent. A super item is never priced as a base article,
        and a component code is never priced as a base article (only globally),
        so the super item and its components are never both charged.
        """
        super_pids = self._super_product_ids(snapshot)
        components = snapshot.article_components or {}

        # BOM parents (super items): their own article number is never priced.
        super_item_ids = {str(k) for k in components.keys()}

        # Every component article number, in BOM order (priced globally only).
        component_codes: list[str] = []
        component_set: set[str] = set()
        for comps in components.values():
            for comp in comps:
                sub = (comp.get("sub_item") or "").strip()
                if sub and sub not in component_set:
                    component_codes.append(sub)
                    component_set.add(sub)

        items: list[str] = []
        super_codes: set[str] = set()
        seen: set[str] = set()

        # Non-super base articles: skip super items and any component code.
        for a in snapshot.articles:
            code = a.code
            if not code or code in seen:
                continue
            if str(a.id) in super_item_ids or str(a.product_id) in super_pids:
                continue  # super item -> priced via its components, not directly
            if code in component_set:
                continue  # a component -> priced globally below, never as base
            items.append(code)
            seen.add(code)

        # Components -> global (the component code is the variant condition).
        for sub in component_codes:
            if sub not in seen:
                items.append(sub)
                seen.add(sub)
            super_codes.add(sub)
        return items, super_codes

    @staticmethod
    def _snapshot_products(snapshot: Snapshot) -> list:
        """The product objects known for the snapshot (its primary product),
        read for each product's ``is_super_product`` flag."""
        primary = getattr(snapshot, "product", None)
        return [primary] if primary is not None else []
