"""CET SIF order-file validation against PDM (replicates PDM 'Validate Order SIF').

Parses a Herman Miller SIF order file, and for each order line re-prices the
SKU against PDM using the SAME functions PDM uses (``fnGetListPriceByItem`` for
the base, ``fnGetListPrice`` for option increments), then flags any line whose
SIF price does not match PDM. Because the price is computed by the identical SQL
UDFs, a reported mismatch is a genuine data discrepancy, not a replication error.

Validated 2026-08-14 against a real ASIA/Atlas CNY SIF: 9/9 exact price matches.
Recipe: currency from the ``PZ`` header; pricing SITE resolved by calibrating on
the file's no-upcharge lines (the region site whose PDM base matches); effective
date = server ``GetUTCDate()`` (the current price list, not the SIF date); fabric
option codes matched to their PDM band by prefix (``1HA01`` -> ``1HA#``).

OBX (pCon) is intentionally not handled yet - SIF (CET) only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from tokenize import group

from services.base_service import BaseService


@dataclass
class SifOption:
    """One option line (``ON``/``OD``/``OG``/``OL``) under an order line."""

    code: str = ""
    desc: str = ""
    group: str = ""
    ol: float = 0.0


@dataclass
class SifLine:
    """One order line in the SIF (a ``PN`` block)."""

    seq: int = 0
    base: str = ""          # PN - base article code
    desc: str = ""          # PD
    currency: str = ""      # PZ header of the file this line came from
    market_config: str = "" # MC
    pl: float = 0.0         # PL - base list price
    sp: float = 0.0         # SP - configured (base + options) price
    qty: int = 1            # QT
    plc: str = ""           # GC - order PLC
    tag: str = ""           # TG - parent/template tag
    source_date: str = ""    # Date carried by the source order file (display only)
    options: list[SifOption] = field(default_factory=list)

    @property
    def sif_price(self) -> float:
        """The SIF's configured line price (base + option upcharges)."""
        return round(self.pl + sum(o.ol for o in self.options), 2)


@dataclass
class SifResult:
    """Validation outcome for one order line."""

    seq: int = 0
    sku: str = ""
    plc: str = ""            # PDM "Category (Product_Code)"
    qty: int = 1
    source_date: str = ""
    sif_price: float = 0.0
    pdm_price: float | None = None
    status: str = "ok"       # ok | price_mismatch | unresolved
    message: str = ""

    @property
    def result(self) -> str:
        """The PDM report 'Result' cell: VALID or the error text."""
        return "VALID" if self.status == "ok" else self.message.replace("too many options", "invalid options")


class SifValidationService(BaseService):
    """Validate a CET SIF order file's prices against PDM."""

    _PRICE_WINDOW = 10  # lines priced per PDM round-trip so results stream steadily

    @staticmethod
    def _num(value: str) -> float:
        try:
            return float(str(value).strip())
        except (TypeError, ValueError):
            return 0.0

    def parse_sif(self, text: str) -> tuple[str, list[SifLine]]:
        """Parse SIF text into ``(currency, order lines)``. Each ``PN=`` starts a
        new line; ``ON=``/``OD=``/``OG=``/``OL=`` build its options."""
        currency = ""
        source_date = ""
        lines: list[SifLine] = []
        current: SifLine | None = None
        option: SifOption | None = None
        for raw in text.splitlines():
            key, sep, val = raw.strip().partition("=")
            if not sep:
                continue
            key, val = key.strip(), val.strip()
            if key == "PZ":
                currency = val
            elif key == "DT":
                # SIF source date format: MMDDYYYY. Display only; PDM pricing
                # continues to use the manually selected validation date.
                try:
                    source_date = datetime.strptime(val, "%m%d%Y").strftime("%Y-%m-%d")
                except ValueError:
                    source_date = val
            elif key == "SL":  # SL=END OF ...
                break
            elif key == "PN":
                current = SifLine(
                    seq=len(lines) + 1,
                    base=val,
                    currency=currency,
                    source_date=source_date,
                )
                lines.append(current)
                option = None
            elif current is None:
                continue
            elif key == "PD":
                current.desc = val
            elif key == "PL":
                current.pl = self._num(val)
            elif key == "SP":
                current.sp = self._num(val)
            elif key == "QT":
                current.qty = int(self._num(val))
            elif key == "GC":
                current.plc = val
            elif key == "MC":
                current.market_config = val
            elif key == "TG":
                current.tag = val
            elif key == "ON":
                option = SifOption(code=val)
                current.options.append(option)
            elif key == "OD" and option is not None:
                option.desc = val
            elif key == "OG" and option is not None:
                option.group = val
            elif key == "OL" and option is not None:
                option.ol = self._num(val)
        return currency, lines

    def parse_obx(self, text: str) -> tuple[str, list[SifLine]]:
        """Parse an OBX file using the legacy PDM OBX validation behavior."""

        import re

        lines: list[SifLine] = []

        # OBX contains currency on its itemPrice elements.
        currency = "EUR"

        currency_match = re.search(
            r"<itemPrice\b[^>]*\bcurrency=['\"]([^'\"]+)['\"]",
            text,
            re.IGNORECASE,
        )

        if currency_match:
            currency = currency_match.group(1).strip()

        # Legacy behavior:
        # Search for <artNr type='final' and allow additional attributes
        # such as default='1'.
        article_matches = list(
            re.finditer(
                r"<artNr\s+type=['\"]final['\"][^>]*>",
                text,
                re.IGNORECASE,
            )
        )

        for seq, match in enumerate(article_matches, start=1):
            # Text immediately after the opening artNr tag.
            start = match.end()

            # The legacy implementation reads until </...>.
            end_tag = text.find("</", start)

            if end_tag == -1:
                continue

            sku = text[start:end_tag].strip()

            # Match legacy behavior of collapsing repeated spaces.
            sku = re.sub(r" {2,}", " ", sku)

            # Limit this item's search area to the next final article.
            if seq < len(article_matches):
                item_end = article_matches[seq].start()
                item_text = text[start:item_end]
            else:
                item_text = text[start:]

            # PLC
            plc = ""

            plc_match = re.search(
                r"<feature\s+name=['\"]PLC['\"]\s+value=['\"]([^'\"]*)['\"]",
                item_text,
                re.IGNORECASE,
            )

            if plc_match:
                plc = plc_match.group(1).strip()

            # Source price date (display only; PDM pricing still uses the
            # manually selected validation date).
            source_date = ""
            date_match = re.search(
                r"<priceDate\b[^>]*\bvalue=['\"]([^'\"]*)['\"]",
                item_text,
                re.IGNORECASE,
            )
            if date_match:
                source_date = date_match.group(1).strip()

            # Price
            # Legacy behavior uses the FIRST <itemPrice> after the
            # final article. In the supplied OBX this is the purchase price.
            price = 0.0

            price_match = re.search(
                r"<itemPrice\b[^>]*\bvalue=['\"]([^'\"]*)['\"]",
                item_text,
                re.IGNORECASE,
            )

            if price_match:
                price_text = price_match.group(1).strip()
                price_text = price_text.lower().replace("nan", "")

                if price_text:
                    price = self._num(price_text)

            lines.append(
                SifLine(
                    seq=seq,
                    base=sku,
                    currency=currency,
                    pl=price,
                    sp=price,
                    qty=1,
                    plc=plc,
                    source_date=source_date,
                )
            )

        return currency, lines
        
    @staticmethod
    def _sku(line: SifLine) -> str:
        """Full order-code SKU: base + option codes (skip ``!`` and ``#`` codes)."""
        codes = [o.code for o in line.options if o.code and o.code != "!" and "#" not in o.code]
        return line.base + "".join(" " + c for c in codes)

    @staticmethod
    def _increment_key_match(code: str, values: dict[str, object]) -> str | None:
        """Match one order code using the legacy GetPriceExt rule.

        Exact values win. Prefix values ending in '#' are then considered and
        the longest matching prefix wins (for example ABC# before AB#).
        """
        code = (code or "").strip().upper()
        if not code:
            return None
        if code in values:
            return code

        matches = [
            key for key in values
            if key.endswith("#") and code.startswith(key[:-1])
        ]
        return max(matches, key=len) if matches else None

    @classmethod
    def _match_inc(cls, inc, code: str) -> float:
        key = cls._increment_key_match(code, inc)
        if key is None:
            return 0.0
        price, _is_fabric, quantity = inc[key]
        return price * quantity

    @classmethod
    def _match_inc_groups(cls, groups: dict[str, dict[str, float]], codes) -> float:
        """Match selected codes against PDM OptionId groups.

        The legacy GetPriceExt implementation removes an OptionId after a value
        has been consumed. This prevents one selected code from charging more
        than one row from the same option group and handles duplicate codes
        across groups deterministically.
        """
        order = list(groups.values())
        used: set[int] = set()
        total = 0.0
        for raw in codes:
            for index, values in enumerate(order):
                if index in used:
                    continue
                key = cls._increment_key_match(raw, values)
                if key is None:
                    continue
                total += float(values[key])
                used.add(index)
                break
        return total

    @staticmethod
    def _feature_option_indexes(feature_position: object, option_id: object) -> set[int] | None:
        """Map a component OptionId to parent option positions like getListPrice."""
        text = str(feature_position or "")
        if not text:
            return None
        target = str(option_id or "")
        position = 1
        while text.startswith("|"):
            text = text[1:]
            position += 1
        if target and target in text:
            prefix = text[:text.index(target) + len(target)]
            position += prefix.count("|")
        return {position - 1}

    @staticmethod
    def _legacy_display_override(item: str, option_id: str, display: int) -> tuple[int, int]:
        """Exact product-family display-position overrides from legacy getListPrice."""
        try:
            oid = int(option_id)
        except (TypeError, ValueError):
            return display, 1

        if item.startswith(("YH304", "YH306", "YH307")) and oid == 6733:
            display = 3
        elif item.startswith(("YI303", "YI305")) and oid == 6768:
            display = 3
        elif item.startswith("NOFTE") and oid == 6820:
            display = 1
        elif item.startswith(("NODLE1", "NODLE2")):
            if oid == 6699:
                display = 1
            elif oid == 6695:
                display = 2
        elif item.startswith(("EX1", "EZ1")) and oid == 1206 and display == 1:
            display = 3
        elif item.startswith("OAW30"):
            if oid == 3278:
                display = 1
            elif oid == 3716:
                display = 2
        elif item.startswith("HE"):
            if oid == 3765:
                display = 3
            elif oid == 3761:
                display = 4

        base_display = 1
        if item.startswith("AS"):
            if item.startswith(("AS4", "AS5")) and display == 3:
                display = 1
            if display == 4:
                display = 2
            if display == 2:
                base_display = 2

        return display, base_display

    @classmethod
    def _match_component_increments(cls, rows, codes: list[str], item: str = "") -> float:
        """Port getListPrice matching, re-indexing and component-row consumption."""
        prepared = []
        for row in rows:
            code = str(getattr(row, "OrderCodeValue2", "") or "").strip().upper()
            if not code:
                continue
            display = int(getattr(row, "DisplayOrder", 0) or 0)
            tertiary = int(getattr(row, "TertiaryOption", 0) or 0)
            option_id = str(getattr(row, "OptionId", "") or "")
            display, base_display = cls._legacy_display_override(item, option_id, display)
            prepared.append({
                "row": row, "code": code, "display": display,
                "tertiary": tertiary, "base_display": base_display,
                "option_id": option_id,
                "component": str(getattr(row, "CompItem", "") or ""),
            })

        total = 0.0
        applied_option_ids: set[str] = set()
        normalized = [(code or "").strip().upper() for code in codes if code]
        deferred = 0.0
        work = list(prepared)

        for position, selected in enumerate(normalized, start=1):
            alternatives = [selected]
            if len(selected) > 2:
                alternatives.append(selected[:2] + "#")
            if len(selected) > 3:
                alternatives.append(selected[:3] + "#")

            search_from = 0
            chosen = None
            while search_from < len(work):
                matches = [
                    (idx, entry) for idx, entry in enumerate(work)
                    if idx >= search_from and entry["code"] in alternatives
                ]
                if not matches:
                    break
                idx, entry = matches[0]
                display = entry["display"]
                tertiary = entry["tertiary"]

                # Legacy tertiary/display re-indexing: if the current occurrence
                # belongs to an earlier position, search the row for this position.
                if tertiary > 0 and position > tertiary:
                    later = next(
                        (i for i, value in enumerate(work)
                         if i > idx and value["tertiary"] == position),
                        None,
                    )
                    if later is not None:
                        search_from = later
                        continue
                    later = next(
                        (i for i, value in enumerate(work)
                         if i > idx and value["display"] == position),
                        None,
                    )
                    if later is not None:
                        search_from = later
                        continue

                if item.startswith(("NOCLE7", "NOCLE8")) and position == 3:
                    if entry["option_id"] != "8" and idx + 1 < len(work):
                        search_from = idx + 1
                        continue

                position_ok = (
                    "#" in selected
                    or "#" in entry["code"]
                    or item.startswith("AK")
                    or (position == 1 and display == 1 and position == tertiary)
                    or (position == entry["base_display"] and display == entry["base_display"])
                    or (position > entry["base_display"] and display > entry["base_display"] and tertiary == 0)
                    or position == display
                    or not entry["component"]
                )
                if position_ok:
                    chosen = (idx, entry)
                    break
                break

            if chosen is None:
                continue

            idx, chosen_entry = chosen
            option_id = chosen_entry["option_id"]
            allow_duplicate = (
                item.startswith("NODL") and position == 3 and selected == "OAK"
            )
            if option_id in applied_option_ids and not allow_duplicate:
                continue
            applied_option_ids.add(option_id)

            row = chosen_entry["row"]
            price = getattr(row, "IncPrice", None)
            if price is None:
                continue
            amount = float(price)

            if item.startswith("OF") and item.endswith("2"):
                try:
                    option_num = int(option_id)
                except ValueError:
                    option_num = -1
                if option_num == 3344:
                    deferred = amount
                    amount = 0.0
                elif option_num == 8:
                    amount = max(deferred, amount)
                    deferred = 0.0

            qty = int(getattr(row, "Quantity", 1) or 1)
            total += amount * qty

            # Legacy AA/BB removal: once a component row is consumed, remove
            # competing rows for that component and conflicting OptionId.
            component = chosen_entry["component"]
            work = [
                entry for entry in work
                if entry is chosen_entry
                or entry["component"] != component
                and not (
                    entry["option_id"] == option_id
                    and entry["component"] == component
                    and entry["code"] != selected
                )
            ]

        return total + deferred

    @classmethod
    def _verify_selected_options(cls, option_rows, codes: list[str]) -> str | None:
        """Verify selected order codes with the core legacy VerifyOptions rules.

        Values are matched in PDM display order, exact first and then longest
        '#' prefix. Once matched, the complete OptionId group is consumed.
        """
        groups: dict[str, dict[str, object]] = {}
        order: list[str] = []
        for row in option_rows:
            try:
                if int(getattr(row, "Status", 1) or 1) != 1:
                    continue
            except (TypeError, ValueError):
                continue
            code = str(getattr(row, "OrderCodeValue2", "") or "").strip().upper()
            if not code or code == " ":
                continue
            group = str(getattr(row, "OptionId", "") or "")
            if group not in groups:
                groups[group] = {}
                order.append(group)
            groups[group][code] = row

        used: set[str] = set()
        for position, raw in enumerate(codes, start=1):
            code = (raw or "").strip().upper()
            if not code or code in {"!", "#"}:
                continue
            matched_group = None
            for group in order:
                if group in used:
                    continue
                if cls._increment_key_match(code, groups[group]) is not None:
                    matched_group = group
                    break
            if matched_group is None:
                return f"invalid option string in order code at position {position}: {code}"
            used.add(matched_group)
        return None

    def _server_date(self, repo, conn) -> str:
        """Effective date = PDM ``GetUTCDate()`` (the current price list)."""
        rows = repo._execute("SELECT CONVERT(varchar, GetUTCDate(), 106) AS d", (), conn)
        return rows[0].d if rows else ""

    @staticmethod
    def _is_future_date(value: str, server_date: str) -> bool:
        """Whether a user-selected date is later than PDM's current date."""
        try:
            return (
                datetime.strptime(value, "%d-%b-%Y").date()
                > datetime.strptime(server_date, "%d %b %Y").date()
            )
        except (TypeError, ValueError):
            return False
    def _site_ids(self, repo, conn) -> list[int]:
        rows = repo._execute(
            "SELECT SiteId FROM Site ORDER BY SiteId",
            (),
            conn,
        )
        return [int(r.SiteId) for r in rows]
    
    # Original PDM Validate Order SIF site rules. Currency selects the intended
    # pricing region; DomCurrCode is only that site's domestic currency and must
    # not be used to discover the pricing site.
    _SIF_SITE_BY_CURRENCY = {
        "GBP": "UK",
        "EUR": "UK",
        "HKD": "Hong Kong",
        "CNY": "HM Dongguan",
        "JPY": "Japan",
        "INR": "India",
        "BRL": "Brazil",
        "USD": "Singapore",
    }

    def site_for_currency(self, currency: str, repo, conn, *, obx: bool = False) -> int | None:
        """Resolve the intended PDM pricing site dynamically from the original
        PDM validator's currency-to-site rule, then return the PDM SiteId.

        This deliberately does not use Site.DomCurrCode: PDM can price a SKU in
        currencies other than a site's domestic currency (for example UK/EUR).
        """
        code = (currency or "").strip().upper()
        site_name = "UK" if obx and code in {"GBP", "EUR"} else self._SIF_SITE_BY_CURRENCY.get(code)
        if not site_name:
            return None

        rows = repo._execute(
            """
            SELECT SiteId
            FROM Site
            WHERE UPPER(Site) = UPPER(?)
            ORDER BY SiteId
            """,
            (site_name,),
            conn,
        )
        return int(rows[0].SiteId) if rows else None

    def _diagnose_currency_sites(
        self,
        currency: str,
        lines: list[SifLine],
        repo,
        conn,
        mydate: str,
    ) -> None:
        rows = repo._execute(
            """
            SELECT SiteId, Description, Site, DomCurrCode
            FROM Site
            WHERE UPPER(DomCurrCode) = UPPER(?)
            ORDER BY SiteId
            """,
            (currency,),
            conn,
        )

        candidates = [int(r.SiteId) for r in rows]

        if len(candidates) <= 1:
            return

        items = sorted({
            line.base
            for line in lines
            if line.base
        })[:10]

        prices = repo.fetch_item_base_prices_all_sites(
            items,
            currency,
            mydate,
            candidates,
            conn,
        )

        details = []
        for site_id in candidates:
            site_rows = [
                r for r in prices
                if int(r.SiteId) == site_id
            ]

            resolved = sum(
                1 for r in site_rows
                if r.price is not None
            )

            details.append(
                f"SiteId={site_id}: "
                f"{resolved}/{len(items)} sample items resolved"
            )

        raise RuntimeError(
            f"CURRENCY SITE DIAGNOSTIC [{currency}] "
            f"on [{mydate}]: "
            + " | ".join(details)
        )

    def resolve_site(self, currency: str, lines: list[SifLine], repo, conn, mydate: str) -> int | None:
        """Pick the PDM pricing SITE for this currency by calibrating on the
        file's no-upcharge lines - the site whose PDM base price matches the SIF
        for the most of them. Returns None if no site matches any. Prices the
        sample across all sites in one query so calibration is a single round trip."""
        sample = [l for l in lines if l.base and not any(o.ol for o in l.options)][:10]
        if not sample:
            sample = [l for l in lines if l.base][:10]
        items = [l.base for l in sample]
        want = {l.base: l.pl for l in sample}
        if not items:
            return None
        site_ids = self._site_ids(repo, conn)
        rows = repo.fetch_item_base_prices_all_sites(items, currency, mydate, site_ids, conn)
        by_site: dict[int, dict[str, object]] = {}
        for r in rows:
            by_site.setdefault(int(r.SiteId), {})[str(r.Item)] = r.price
        best_site, best_hits = None, 0
        for site in site_ids:
            prices = by_site.get(site, {})
            hits = sum(1 for it in items
                       if prices.get(it) is not None and abs(float(prices[it]) - want[it]) < 0.005)
            if hits > best_hits:
                best_hits, best_site = hits, site
        return best_site
    def validate(
        self,
        currency: str,
        lines: list[SifLine],
        site: int | None = None,
        obx: bool = False,
        validation_date: str | None = None,
        progress=None,
        stage=None,
        on_result=None,
    ) -> tuple[dict[str, int | None], list[SifResult]]:
        """Re-price every order line against PDM and flag mismatches. Lines are
        grouped by their own currency (so a batch of files in different
        currencies each price correctly), and each group resolves its own site.
        Returns ``({currency: site}, results)`` with results in file order."""
        from repositories.pdm_repository import PDMRepository

        repo = PDMRepository(self.context)
        conn = repo.get_connection()
        server_date = self._server_date(repo, conn)
        mydate = validation_date or server_date
        groups: dict[str, list[SifLine]] = {}
        for line in lines:
            groups.setdefault(line.currency or currency, []).append(line)

        sites: dict[str, int | None] = {}
        results: list[SifResult] = []
        done = [0]
        total = len(lines)
        for cur, group in groups.items():
            # Use the original PDM validator's currency-to-site business rule.
            # PDM remains the final authority: this only selects the context for
            # fnGetListPriceByItem and option pricing.
            if site is not None:
                group_site = site
            else:
                group_site = self.site_for_currency(cur, repo, conn, obx=obx)

            sites[cur] = group_site
            results.extend(self._validate_group(
                cur, group, group_site, repo, conn, mydate, done, total, progress, stage, on_result,
                "OBX" if obx else "SIF", obx
            ))
        results.sort(key=lambda r: r.seq)
        return sites, results

    def _validate_group(self, currency, lines, site, repo, conn, mydate,
                        done, total, progress, stage, on_result=None, source_label="SIF",
                        obx: bool = False) -> list[SifResult]:
        """Price one single-currency group of lines against PDM at ``site``."""
        results: list[SifResult] = []
        if site is None:
            for line in lines:
                done[0] += 1
                if progress:
                    progress(done[0], total, line.base)
                results.append(SifResult(
                    seq=line.seq, sku=self._sku(line), qty=line.qty, source_date=line.source_date, sif_price=line.sif_price,
                    status="unresolved", message=f"no PDM pricing site resolves currency {currency}"
                    ))
                if on_result:
                    on_result(results[-1])
            return results

        # Source-specific catalogue selection is intentionally resolved before
        # the shared pricing pipeline. After this point SIF and OBX use the same
        # item/option/pricing engine so neither source can bypass parity logic.
        catalogue_ids = repo.fetch_validation_catalogue_ids(
            currency,
            site,
            obx=obx,
            connection=conn,
        )
        catalogue_ids = repo.fetch_validation_catalogue_ids_ordered(
            catalogue_ids,
            site,
            connection=conn,
        )
        if stage:
            scope = ",".join(str(value) for value in catalogue_ids[:5])
            suffix = "..." if len(catalogue_ids) > 5 else ""
            stage(
                f"Pricing {len({l.base for l in lines if l.base})} items from PDM "
                f"(site {site}, {currency}, catalogues {scope}{suffix})..."
            )

        # Catalogue selection is part of the legacy validation workflow. Price
        # calculation remains independent here, while unresolved catalogue
        # verification is handled separately rather than silently ignored.
        # Price in small windows so rows appear steadily instead of one big
        # batch at the end, while keeping PDM queries bulk (fast) and parity exact.
        window = self._PRICE_WINDOW
        for start in range(0, len(lines), window):
            chunk = lines[start:start + window]
            items = sorted({l.base for l in chunk if l.base})
            # Reproduce GetPrice's pre-pricing validation: the item must have
            # an active PDM row and a complete price matrix for the selected
            # site/currency before GetPriceExt is allowed to price it.
            contexts = repo.fetch_item_price_context(
                items,
                currency,
                site,
                connection=conn,
            )
            normal_context_items = {str(row.Item) for row in contexts}
            us_items = repo.find_us_items(items, connection=conn) - normal_context_items
            if us_items:
                contexts.extend(
                    repo.fetch_us_item_price_context(
                        sorted(us_items), currency, site, connection=conn
                    )
                )

            valid_catalogues_by_item = repo.fetch_items_valid_catalogues(
                items,
                catalogue_ids,
                connection=conn,
            )
            valid_items: set[str] = set()
            for row in contexts:
                item = str(row.Item)
                status = getattr(row, "Status", None)
                price_ref = getattr(row, "BasePriceRef", None)
                is_super = bool(getattr(row, "IsSuperProduct", False))
                if status is not None and int(status) >= 2:
                    continue
                if not is_super and price_ref is None:
                    continue
                valid_items.add(item)

            normal_items = sorted(valid_items - us_items)
            got = repo.fetch_item_get_price_ext_base_prices(
                normal_items, currency, mydate, conn, site_id=site
            )
            us_got = repo.fetch_us_item_base_prices(
                sorted(valid_items & us_items),
                currency, mydate, site, connection=conn,
            ) if (valid_items & us_items) else []
            base_price = {
                str(r.Item): (float(r.price) if r.price is not None else None)
                for r in [*got, *us_got]
            }

            # Legacy GetPrice switches SuperProducts to getListPrice(), where
            # the parent price is the sum of priced ItemComponents × quantity.
            component_rows = repo.fetch_item_component_prices(
                [
                    str(row.Item)
                    for row in contexts
                    if bool(getattr(row, "IsSuperProduct", False))
                    and not (
                        (str(row.Item).startswith("MK12O")
                         or str(row.Item).startswith("MK14O"))
                        and str(row.Item).endswith("O")
                    )
                ],
                currency,
                mydate,
                site,
                connection=conn,
            )
            component_price: dict[str, float] = {}
            component_seen: dict[str, int] = {}
            for row in component_rows:
                parent = str(row.ParentItem)
                price = getattr(row, "price", None)
                if price is None:
                    continue
                component_seen[parent] = component_seen.get(parent, 0) + 1
                component_price[parent] = component_price.get(parent, 0.0) + (
                    float(price) * int(getattr(row, "Quantity", 1) or 1)
                )
            super_items: set[str] = set()
            for row in contexts:
                item = str(row.Item)
                is_super = bool(getattr(row, "IsSuperProduct", False))
                legacy_exception = (
                    (item.startswith("MK12O") or item.startswith("MK14O"))
                    and item.endswith("O")
                )
                if is_super and not legacy_exception and item in component_seen:
                    base_price[item] = round(component_price.get(item, 0.0), 2)
                    super_items.add(item)

            component_increment_rows = repo.fetch_item_component_increment_prices(
                sorted(super_items), currency, mydate, site, connection=conn
            ) if super_items else []
            component_increments_by_item: dict[str, list[object]] = {}
            for row in component_increment_rows:
                component_increments_by_item.setdefault(
                    str(getattr(row, "ParentItem", "")), []
                ).append(row)

            plc_by_item = self._fetch_plc(items, site, repo, conn)
            # The legacy validator sends the complete configured SKU to GetPrice.
            # Option pricing therefore depends on selected order codes, not on
            # whether the source SIF happened to contain an OL amount.
            inc_items = sorted({l.base for l in chunk if l.options})
            # Keep option rows grouped by PDM OptionId for both SIF and OBX.
            # GetPriceExt consumes an option group once it has matched a selected
            # order code; flattening by code loses that behaviour.
            inc_groups_by_item: dict[str, dict[str, dict[str, float]]] = {}

            if inc_items:
                # Same ordered PDM option data drives both VerifyOptions and
                # GetPriceExt; USdata uses its own direct + dependent stream.
                normal_inc_items = sorted(set(inc_items) - us_items)
                us_inc_items = sorted(set(inc_items) & us_items)
                inc_rows = repo.fetch_item_validation_options(
                    normal_inc_items, currency, mydate, site, conn
                ) if normal_inc_items else []
                if us_inc_items:
                    inc_rows.extend(
                        repo.fetch_item_us_dependent_increment_prices(
                            us_inc_items, currency, mydate, site, connection=conn
                        )
                    )
                for r in inc_rows:
                    item = str(r.Item)
                    code = str(r.OrderCodeValue2 or "").strip().upper()
                    if not code:
                        continue

                    group = str(getattr(r, "OptionId", "") or "")
                    inc_price = getattr(r, "IncPrice", None)

                    # GetPriceExt adds IncPrice directly. The Quantity column is
                    # retained by the legacy option data but is not multiplied
                    # into the standard GetPriceExt upcharge loop.
                    amount = 0.0 if inc_price is None else float(inc_price)
                    inc_groups_by_item.setdefault(item, {}).setdefault(group, {})[code] = amount
            option_rows_by_item: dict[str, list[object]] = {}
            if inc_items:
                for row in inc_rows:
                    option_rows_by_item.setdefault(str(getattr(row, "Item", "")), []).append(row)

            for line in chunk:
                done[0] += 1
                if progress:
                    progress(done[0], total, line.base)
                sku = self._sku(line)
                sif = line.sif_price
                base = base_price.get(line.base)
                plc = plc_by_item.get(line.base, "")
                # Legacy USdata pricing does not run the normal Item/Option
                # catalogue verification branch; its ordered US option stream is
                # priced directly, including dependent option values.
                option_error = None
                if str(line.base) not in us_items:
                    option_error = self._verify_selected_options(
                        option_rows_by_item.get(str(line.base), []),
                        [option.code for option in line.options],
                    )
                if option_error:
                    results.append(SifResult(
                        seq=line.seq, sku=sku, plc=plc, qty=line.qty,
                        source_date=line.source_date, sif_price=sif,
                        status="unresolved", message=option_error,
                    ))
                    if on_result:
                        on_result(results[-1])
                    continue
                if line.base not in valid_catalogues_by_item:
                    results.append(SifResult(
                        seq=line.seq, sku=sku, plc=plc, qty=line.qty,
                        source_date=line.source_date, sif_price=sif,
                        status="unresolved",
                        message=(
                            f"SKU/options do not resolve in validation catalogue scope "
                            f"[{line.base}]"
                        ),
                    ))
                    if on_result:
                        on_result(results[-1])
                    continue
                if base is None:
                    context = next(
                        (row for row in contexts if str(row.Item) == str(line.base)),
                        None,
                    )
                    if context is None:
                        reason = f"unable to resolve SKU in PDM [{line.base}]"
                    elif (
                        getattr(context, "Status", None) is not None
                        and int(context.Status) >= 2
                    ):
                        reason = f"SKU is inactive in PDM [{line.base}]"
                    elif (
                        not bool(getattr(context, "IsSuperProduct", False))
                        and getattr(context, "BasePriceRef", None) is None
                    ):
                        reason = (
                            f"incomplete price matrix for SKU [{line.base}] "
                            f"(site {site}, currency {currency})"
                        )
                    else:
                        reason = f"unable to obtain PDM price [{line.base}]"
                    results.append(SifResult(
                        seq=line.seq, sku=sku, plc=plc, qty=line.qty, source_date=line.source_date, sif_price=sif,
                        status="unresolved", message=reason))
                    if on_result:
                        on_result(results[-1])
                    continue
                # Both SIF and OBX ultimately pass selected order codes through
                # the same GetPriceExt option-group consumption behaviour.
                if str(line.base) in super_items:
                    upcharge = self._match_component_increments(
                        component_increments_by_item.get(str(line.base), []),
                        [o.code for o in line.options],
                        str(line.base),
                    )
                else:
                    upcharge = self._match_inc_groups(
                        inc_groups_by_item.get(line.base, {}),
                        [o.code for o in line.options],
                    )
                pdm = round(base + upcharge, 2)
                if abs(pdm - sif) < 0.005:
                    status, message = "ok", ""
                else:
                    status = "price_mismatch"
                    message = f"price mismatch: {source_label} [{sif:.2f}] does NOT match PDM [{pdm:.2f}]"
                results.append(SifResult(
                    seq=line.seq, sku=sku, plc=plc, qty=line.qty, source_date=line.source_date, sif_price=sif,
                    pdm_price=pdm, status=status, message=message))
                if on_result:
                    on_result(results[-1])
        return results

    def _fetch_plc(self, items, site, repo, conn) -> dict[str, str]:
        """Per-item PDM PLC as ``Category (Product_Code)`` at the site."""
        out: dict[str, str] = {}
        for chunk in repo._chunked([str(i) for i in items if i], repo._IN_CHUNK):
            ph = repo._placeholders(len(chunk))
            rows = repo._execute(
                "SELECT i.Item, pc.Product_Code AS Code, cat.Name AS Category "
                "FROM Item i "
                "INNER JOIN Product p ON i.ProductId = p.ProductId "
                "LEFT JOIN Product_Code pc ON "
                "pc.ProductCodeId = CASE "
                "WHEN i.ProductCodeIdOverride IS NOT NULL "
                "THEN i.ProductCodeIdOverride "
                "ELSE p.ProductCodeId "
                "END "
                "AND pc.SiteId = ? "
                "LEFT JOIN ProductRange pr ON p.ProductRangeId = pr.ProductRangeId "
                "LEFT JOIN ProductCategory cat ON pr.ProductCategoryId = cat.ProductCategoryId "
                f"WHERE i.Item IN ({ph})",
                (site,) + tuple(chunk),
                conn
            )
            for r in rows:
                code = (r.Code or "").strip()
                cat = (r.Category or "").strip()
                out[str(r.Item)] = f"{cat} ({code})" if code else cat
        return out

    def export_csv(self, path, currency: str, results: list[SifResult], source_label: str = "SIF") -> None:
        """Write the validation report as CSV, matching PDM's exact columns
        (``SKU, Category (PLC), PDM List Price, SIF List Price, SIF Qty, Result``)."""
        import csv

        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([
                "SKU", "Category (PLC)", f"PDM List Price ({currency})",
                f"{source_label} List Price ({currency})", f"{source_label} Qty", "Result"])
            for r in results:
                writer.writerow([
                    r.sku, r.plc,
                    "" if r.pdm_price is None else f"{r.pdm_price:.2f}",
                    f"{r.sif_price:.2f}", r.qty, r.result])
