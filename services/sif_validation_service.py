"""CET SIF order-file validation against PDM (replicates PDM 'Validate Order SIF').

Parses a Herman Miller SIF order file, and for each order line re-prices the
SKU against PDM using the SAME functions PDM uses (legacy ``fnGetListPrice``
semantics for the base, ``fnGetListPrice`` for option increments), then flags
any line whose SIF price does not match PDM. Because the price is computed by
the identical SQL UDFs, a reported mismatch is a genuine data discrepancy,
not a replication error.

Validated 2026-08-14 against a real ASIA/Atlas CNY SIF: 9/9 exact price matches.
Recipe: currency from the ``PZ`` header; pricing SITE resolved by calibrating on
the file's no-upcharge lines (the region site whose PDM base matches); effective
date = server ``GetUTCDate()`` (the current price list, not the SIF date); fabric
option codes matched to their PDM band by prefix (``1HA01`` -> ``1HA#``).

OBX (pCon) uses a dedicated parser and shares the PDM repricing engine; this service remains the shared pricing implementation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
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
    currency: str = ""
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

    _PRICE_WINDOW = 16  # normal PDM query window; one validation connection is reused

    @classmethod
    def _adaptive_price_window(cls, line_count: int) -> int:
        """Keep PDM query batches small as an OBX/SIF workload grows.

        The window is deliberately conservative: it changes query size, not
        connection concurrency. The existing validation call still owns one
        PDM connection and reuses it across all windows, while the connection
        recovery logic in the caller remains unchanged.
        """
        base = max(1, int(cls._PRICE_WINDOW))
        count = max(0, int(line_count))
        if count <= 128:
            return base
        if count <= 512:
            return min(base, 8)
        if count <= 2000:
            return min(base, 4)
        return min(base, 2)

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
    def _match_inc(inc, code: str) -> float:
        code = (code or "").strip().upper()

        # Exact match
        if code in inc:
            price, _is_fabric, quantity = inc[code]
            return price * quantity

        # Prefix fallback: prefer the most specific PDM band. For example,
        # 1HA01 must resolve to 1HA# before a broader 1H# band when both exist.
        candidates = []
        if len(code) >= 3:
            candidates.append(code[:3] + "#")
        if len(code) >= 2:
            candidates.append(code[:2] + "#")
        for key in candidates:
            if key in inc:
                price, _is_fabric, quantity = inc[key]
                return price * quantity

        return 0.0

    @staticmethod
    def _increment_key_match(code: str, values: dict[str, object]) -> str | None:
        """Match exact option codes first, then the most-specific PDM '#' band."""
        code = (code or "").strip().upper()
        if not code:
            return None
        if code in values:
            return code
        matches = [
            key for key in values
            if key.endswith("#") and key != "#" and code.startswith(key[:-1])
        ]
        return max(matches, key=len) if matches else None

    @classmethod
    def _verify_selected_options(cls, option_rows, codes: list[str]) -> str | None:
        """Validate selected order codes against active PDM option groups."""
        groups: dict[str, dict[str, object]] = {}
        order: list[str] = []
        for row in option_rows:
            try:
                if int(getattr(row, "Status", None)) != 1:
                    continue
                if int(getattr(row, "IsFabric", 0) or 0) == 2:
                    continue
            except (TypeError, ValueError):
                continue
            code = str(getattr(row, "OrderCodeValue2", "") or "").strip().upper()
            if not code or code in {"!", "#"}:
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
            matched_group = next(
                (
                    group for group in order
                    if group not in used
                    and cls._increment_key_match(code, groups[group]) is not None
                ),
                None,
            )
            if matched_group is None:
                return f"invalid option string in order code at position {position}: {code}"
            used.add(matched_group)
        return None

    @staticmethod
    def _match_inc_groups(
        groups: dict[str, dict[str, tuple[float, int]]],
        codes,
        fabric_groups: dict[str, dict[str, float]] | None = None,
        fabric_targets: dict[str, list[str]] | None = None,
    ) -> float:
        """OBX upcharge with legacy PDM fabric-band resolution."""
        order = list(groups.items())
        used: set[str] = set()
        total = 0.0
        fabric_occurrence: dict[str, int] = {}

        for raw in codes:
            code = (raw or "").strip().upper()
            if not code:
                continue
            is_fabric_colour = bool(fabric_targets and code in fabric_targets)
            if not is_fabric_colour:
                for group_id, values in order:
                    if group_id in used or code not in values:
                        continue
                    price, quantity = values[code]
                    total += price * quantity
                    used.add(group_id)
                    break
                continue
            if not fabric_groups:
                continue
            targets = fabric_targets.get(code, [])
            occurrence = fabric_occurrence.get(code, 0)
            target_group = targets[occurrence] if occurrence < len(targets) else None
            if target_group is None:
                continue
            band_values = fabric_groups.get(str(target_group), {})
            candidates = [
                (band_code, price) for band_code, price in band_values.items()
                if band_code.endswith("#") and code.startswith(band_code[:-1])
            ]
            fabric_occurrence[code] = occurrence + 1
            used.add(str(target_group))
            if candidates:
                _, price = max(candidates, key=lambda pair: len(pair[0]))
                total += price
        return total

    @staticmethod
    def _feature_option_indexes(feature_position: object, option_id: object) -> set[int] | None:
        """Return zero-based parent option slots mapped to a component OptionId."""
        text = str(feature_position or "")
        target = str(option_id or "")
        if not text or not target:
            return None
        positions = {
            index for index, value in enumerate(text.split("|"))
            if value == target
        }
        return positions or None

    @staticmethod
    def _legacy_component_display_override(
        item: str, option_id: str, display: int
    ) -> tuple[int, int]:
        """Apply source-audited GetPrice family position overrides to SuperProducts."""
        item = (item or "").upper()
        try:
            option_number = int(option_id)
        except (TypeError, ValueError):
            return display, 1

        if item.startswith(("YH304", "YH306", "YH307")) and option_number == 6733:
            display = 3
        elif item.startswith(("YI303", "YI305")) and option_number == 6768:
            display = 3
        elif item.startswith("NOFTE") and option_number == 6820:
            display = 1
        elif item.startswith(("NODLE1", "NODLE2")):
            if option_number == 6699:
                display = 1
            elif option_number == 6695:
                display = 2
        elif item.startswith(("EX1", "EZ1")) and option_number == 1206 and display == 1:
            display = 3
        elif item.startswith("OAW30"):
            if option_number == 3278:
                display = 1
            elif option_number == 3716:
                display = 2
        elif item.startswith("HE"):
            if option_number == 3765:
                display = 3
            elif option_number == 3761:
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
    def _match_component_increments(
        cls, rows, codes: list[str], item: str = ""
    ) -> float:
        """Allocate component increments by GetPrice position and option group."""
        normalized_item = (item or "").upper()
        prepared = []
        for row in rows:
            code = str(getattr(row, "OrderCodeValue2", "") or "").strip().upper()
            if not code:
                continue
            option_id = str(getattr(row, "OptionId", "") or "")
            display = int(getattr(row, "DisplayOrder", 0) or 0)
            display, base_display = cls._legacy_component_display_override(
                normalized_item, option_id, display
            )
            prepared.append({
                "row": row,
                "code": code,
                "display": display,
                "tertiary": int(getattr(row, "TertiaryOption", 0) or 0),
                "feature_positions": cls._feature_option_indexes(
                    getattr(row, "FeaturePositionString", None), option_id
                ),
                "base_display": base_display,
                "option_id": option_id,
                "component": str(getattr(row, "CompItem", "") or ""),
            })

        total = 0.0
        deferred = 0.0
        applied_option_ids: set[str] = set()
        work = list(prepared)
        for position, raw in enumerate(codes, start=1):
            selected = (raw or "").strip().upper()
            if not selected:
                continue
            search_from = 0
            chosen = None
            while search_from < len(work):
                match = next(
                    (
                        (index, entry) for index, entry in enumerate(work)
                        if index >= search_from
                        and entry["option_id"] not in applied_option_ids
                        and cls._increment_key_match(selected, {entry["code"]: entry})
                    ),
                    None,
                )
                if match is None:
                    break
                index, entry = match
                tertiary = entry["tertiary"]
                if tertiary > 0 and position > tertiary:
                    later = next(
                        (
                            candidate for candidate in range(index + 1, len(work))
                            if work[candidate]["tertiary"] == position
                        ),
                        None,
                    )
                    if later is None:
                        later = next(
                            (
                                candidate for candidate in range(index + 1, len(work))
                                if work[candidate]["display"] == position
                            ),
                            None,
                        )
                    if later is not None:
                        search_from = later
                        continue

                feature_positions = entry["feature_positions"]
                position_matches_feature = (
                    feature_positions is not None and position - 1 in feature_positions
                )
                position_ok = (
                    "#" in selected
                    or "#" in entry["code"]
                    or normalized_item.startswith("AK")
                    or (position == 1 and entry["display"] == 1 and position == tertiary)
                    or (
                        position == entry["base_display"]
                        and entry["display"] == entry["base_display"]
                    )
                    or (
                        position > entry["base_display"]
                        and entry["display"] > entry["base_display"]
                        and tertiary == 0
                    )
                    or position == entry["display"]
                    or position_matches_feature
                    or not entry["component"]
                )
                if position_ok:
                    chosen = (index, entry)
                break

            if chosen is None:
                continue
            _, chosen_entry = chosen
            option_id = chosen_entry["option_id"]
            if option_id in applied_option_ids:
                continue
            applied_option_ids.add(option_id)

            row = chosen_entry["row"]
            price = getattr(row, "IncPrice", None)
            if price is not None:
                amount = float(price)
                if normalized_item.startswith("OF") and normalized_item.endswith("2"):
                    try:
                        option_number = int(option_id)
                    except ValueError:
                        option_number = -1
                    if option_number == 3344:
                        deferred = amount
                        amount = 0.0
                    elif option_number == 8:
                        amount = max(deferred, amount)
                        deferred = 0.0
                total += amount * int(getattr(row, "Quantity", 1) or 1)

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

    def _server_date(self, repo, conn) -> str:
        """Effective date = PDM ``GetUTCDate()`` (the current price list)."""
        rows = repo._execute("SELECT CONVERT(varchar, GetUTCDate(), 106) AS d", (), conn)
        return rows[0].d if rows else ""

    @staticmethod
    def _normalise_pricing_date(value: date | datetime | str) -> str:
        """Normalize supported validation dates without locale-dependent guessing."""
        if isinstance(value, datetime):
            if value.utcoffset() is not None:
                raise ValueError(
                    "invalid validation date: timezone-aware values are not supported"
                )
            timespec = "microseconds" if value.microsecond else "seconds"
            return value.isoformat(sep=" ", timespec=timespec)
        if isinstance(value, date):
            return value.isoformat()

        text = str(value or "").strip()
        formats = ("%Y-%m-%d", "%d-%b-%Y", "%d %b %Y", "%d/%m/%Y")
        for date_format in formats:
            try:
                return datetime.strptime(text, date_format).strftime("%Y-%m-%d")
            except ValueError:
                continue

        # ISO datetime strings preserve their time component; localized or
        # timezone-bearing values are rejected rather than interpreted by SQL.
        if len(text) >= 19 and text[4:5] == "-" and text[7:8] == "-":
            try:
                parsed = datetime.fromisoformat(text)
            except ValueError:
                parsed = None
            if parsed is not None and parsed.tzinfo is None:
                timespec = "microseconds" if parsed.microsecond else "seconds"
                return parsed.isoformat(sep=" ", timespec=timespec)

        raise ValueError(
            f"invalid validation date {text!r}; expected YYYY-MM-DD, DD-Mon-YYYY, "
            "DD Mon YYYY, DD/MM/YYYY, or an ISO datetime"
        )

    @classmethod
    def _is_future_date(
        cls, value: date | datetime | str, server_date: date | datetime | str
    ) -> bool:
        """Compare validation dates using the same accepted formats as pricing."""
        selected = datetime.fromisoformat(cls._normalise_pricing_date(value)).date()
        current = datetime.fromisoformat(cls._normalise_pricing_date(server_date)).date()
        return selected > current
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
        "HKD": "HK",
        "CNY": "DG",
        "JPY": "JP",
        "INR": "IN",
        "BRL": "BR",
        "USD": "SG",
    }

    _SITE_DESCRIPTION_BY_CODE = {
        "UK": "UK",
        "HK": "Hong Kong",
        "DG": "HM Dongguan",
        "JP": "Japan",
        "IN": "India",
        "BR": "Brazil",
        "SG": "Singapore",
    }

    def site_for_currency(self, currency: str, repo, conn, *, obx: bool = False) -> int | None:
        """Resolve the intended PDM pricing site dynamically from the original
        PDM validator's currency-to-site rule, then return the PDM SiteId.

        This deliberately does not use Site.DomCurrCode: PDM can price a SKU in
        currencies other than a site's domestic currency (for example UK/EUR).
        """
        code = (currency or "").strip().upper()
        site_code = "UK" if obx and code in {"GBP", "EUR"} else self._SIF_SITE_BY_CURRENCY.get(code)
        if not site_code:
            return None

        rows = repo._execute(
            """
            SELECT SiteId
            FROM Site
            WHERE UPPER(Site) = UPPER(?) OR UPPER(Description) = UPPER(?)
            ORDER BY CASE WHEN UPPER(Site) = UPPER(?) THEN 0 ELSE 1 END, SiteId
            """,
            (
                site_code,
                self._SITE_DESCRIPTION_BY_CODE.get(site_code, site_code),
                site_code,
            ),
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
        mydate = self._normalise_pricing_date(validation_date or server_date)
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
                    seq=line.seq, sku=self._sku(line), currency=currency, qty=line.qty, source_date=line.source_date, sif_price=line.sif_price,
                    status="unresolved", message=f"no PDM pricing site resolves currency {currency}"
                    ))
                if on_result:
                    on_result(results[-1])
            return results

        all_items = sorted({line.base for line in lines if line.base})
        normal_domain_items = repo.find_normal_items(all_items, connection=conn)
        us_items = repo.find_us_items(all_items, connection=conn) - normal_domain_items
        normal_scope_items = set(all_items) - us_items
        catalogue_ids = (
            repo.fetch_validation_catalogue_ids(site, connection=conn)
            if normal_scope_items
            else []
        )
        if stage:
            stage(f"Pricing {len({l.base for l in lines if l.base})} items from PDM (site {site}, {currency})...")

        # Price in small windows so rows appear steadily while keeping PDM queries bulk and parity exact.
        # For large workloads, shrink the query window rather than increasing
        # connection concurrency. The same validation connection is reused.
        window = self._adaptive_price_window(len(lines))
        if stage and window < self._PRICE_WINDOW:
            stage(f"Large validation workload: using PDM query window {window} (connection reuse protected).")
        for start in range(0, len(lines), window):
            chunk = lines[start:start + window]
            items = sorted({l.base for l in chunk if l.base})
            normal_items = [item for item in items if item not in us_items]
            us_domain_items = [item for item in items if item in us_items]
            contexts = (
                repo.fetch_item_validation_price_context(
                    normal_items, currency, site, connection=conn
                )
                if normal_items
                else []
            )
            us_contexts = (
                repo.fetch_us_item_price_context(
                    us_domain_items, currency, site, connection=conn
                )
                if us_domain_items
                else []
            )
            contexts.extend(us_contexts)
            context_by_item = {str(row.Item): row for row in contexts}
            valid_catalogues_by_item = (
                repo.fetch_items_valid_catalogues(
                    normal_items, catalogue_ids, connection=conn
                )
                if normal_items and catalogue_ids
                else {}
            )
            eligible_base_items: set[str] = set()
            context_errors: dict[str, str] = {}
            for item in items:
                context = context_by_item.get(item)
                if item in us_items:
                    if context is None:
                        context_errors[item] = f"unable to resolve USItem pricing context [{item}]"
                        continue
                    status = getattr(context, "Status", None)
                    if status is None or int(status) >= 2:
                        context_errors[item] = f"inactive or unresolved USItem [{item}]"
                        continue
                    us_price_fields = (
                        "ProductCodeId", "PriceCode", "BasePriceRef", "Rounding",
                        "MatchedCurrency", "BasePrice",
                    )
                    if any(getattr(context, field, None) is None for field in us_price_fields):
                        context_errors[item] = (
                            f"incomplete USItem price context for [{item}] "
                            f"(site {site}, currency {currency})"
                        )
                        continue
                    eligible_base_items.add(item)
                    continue

                if item not in valid_catalogues_by_item:
                    context_errors[item] = (
                        f"SKU/options do not resolve in validation catalogue scope [{item}]"
                    )
                    continue
                if context is None:
                    context_errors[item] = f"unable to resolve SKU in PDM [{item}]"
                    continue
                status = getattr(context, "Status", None)
                if status is not None and int(status) >= 2:
                    context_errors[item] = f"SKU is inactive in PDM [{item}]"
                    continue
                if status is None:
                    context_errors[item] = f"unable to determine PDM item status [{item}]"
                    continue
                is_super_product = bool(getattr(context, "IsSuperProduct", False))
                required_matrix_fields = (
                    "ProductCodeId", "PriceCode", "BasePriceRef", "Rounding",
                    "MatchedCurrency",
                )
                if not is_super_product and any(
                    getattr(context, field, None) is None
                    for field in required_matrix_fields
                ):
                    context_errors[item] = (
                        f"incomplete price matrix for SKU [{item}] "
                        f"(site {site}, currency {currency})"
                    )
                    continue
                eligible_base_items.add(item)

            super_candidate_items = {
                item for item in eligible_base_items
                if bool(getattr(context_by_item[item], "IsSuperProduct", False))
            }
            if obx:
                inc_items = sorted({
                    line.base for line in chunk
                    if line.options and line.base in eligible_base_items
                    and line.base not in super_candidate_items
                    and line.base not in us_items
                })
            else:
                inc_items = sorted({
                    line.base for line in chunk
                    if line.base in eligible_base_items and any(option.ol for option in line.options)
                    and line.base not in super_candidate_items
                    and line.base not in us_items
                })
            option_items = sorted({
                line.base for line in chunk
                if line.options and line.base in eligible_base_items
                and line.base not in us_items
            })
            option_data_items = sorted(set(option_items) | set(inc_items))
            skipped_option_items: set[str] = set()
            option_rows = (
                repo.fetch_item_validation_options(
                    option_data_items, currency, mydate, site, conn
                )
                if option_data_items
                else []
            )
            if option_data_items:
                skipped_option_items = set(
                    getattr(repo, "last_skipped_option_items", [])
                )
            if obx:
                us_increment_items = sorted({
                    line.base for line in chunk
                    if line.options and line.base in eligible_base_items
                    and line.base in us_items
                })
            else:
                us_increment_items = sorted({
                    line.base for line in chunk
                    if line.base in eligible_base_items and line.base in us_items
                    and any(option.ol for option in line.options)
                })
            us_option_rows = (
                repo.fetch_item_us_option_increment_prices(
                    us_increment_items, currency, mydate, site, connection=conn
                )
                if us_increment_items
                else []
            )
            all_increment_rows = [*option_rows, *us_option_rows]
            option_rows_by_item: dict[str, list[Any]] = {}
            for row in option_rows:
                option_rows_by_item.setdefault(str(getattr(row, "Item", "")), []).append(row)

            option_errors_by_seq: dict[int, str] = {}
            valid_pricing_items: set[str] = set()
            for line in chunk:
                if line.base not in eligible_base_items:
                    continue
                if line.base in us_items:
                    valid_pricing_items.add(line.base)
                    continue
                option_error = self._verify_selected_options(
                    option_rows_by_item.get(str(line.base), []),
                    [option.code for option in line.options],
                )
                if option_error:
                    option_errors_by_seq[line.seq] = option_error
                else:
                    valid_pricing_items.add(line.base)

            super_product_items = valid_pricing_items & super_candidate_items
            us_price_items = valid_pricing_items & us_items
            standard_price_items = valid_pricing_items - super_product_items - us_price_items
            got = (
                repo.fetch_validation_get_price_ext_base_prices(
                    sorted(standard_price_items), currency, mydate, conn, site_id=site
                )
                if standard_price_items
                else []
            )
            us_got = (
                repo.fetch_us_item_base_prices(
                    sorted(us_price_items), currency, mydate, site, connection=conn
                )
                if us_price_items
                else []
            )
            base_price = {
                str(row.Item): (float(row.price) if row.price is not None else None)
                for row in [*got, *us_got]
            }

            if super_product_items:
                parent_ids = {
                    item: getattr(context_by_item[item], "ItemId", None)
                    for item in super_product_items
                }
                item_by_parent_id = {
                    str(parent_id): item for item, parent_id in parent_ids.items()
                    if parent_id is not None
                }
                expected_components: dict[str, list[tuple[str, str, int]]] = {
                    item: [] for item in super_product_items
                }
                if item_by_parent_id:
                    bom_rows = repo.fetch_item_components(
                        [parent_ids[item] for item in item_by_parent_id.values()],
                        connection=conn,
                    )
                    for row in bom_rows:
                        parent = item_by_parent_id.get(str(row.ParentItemId))
                        if parent is not None:
                            expected_components[parent].append((
                                str(row.ComponentSequence),
                                str(row.SubItem),
                                int(row.Quantity or 1),
                            ))

                    component_price_rows = repo.fetch_item_component_prices(
                        sorted(item_by_parent_id.values()),
                        currency,
                        mydate,
                        site,
                        connection=conn,
                    )
                else:
                    component_price_rows = []

                priced_components: dict[str, list[Any]] = {}
                for row in component_price_rows:
                    priced_components.setdefault(str(row.ParentItem), []).append(row)
                for item in super_product_items:
                    expected = expected_components[item]
                    actual = priced_components.get(item, [])
                    actual_signature = sorted((
                        str(row.ComponentSequence),
                        str(row.ComponentItem),
                        int(row.Quantity or 1),
                    ) for row in actual)
                    if not expected:
                        context_errors[item] = (
                            f"SuperProduct has no resolvable components [{item}]"
                        )
                    elif sorted(expected) != actual_signature:
                        context_errors[item] = (
                            f"unable to resolve all SuperProduct components [{item}]"
                        )
                    elif any(getattr(row, "price", None) is None for row in actual):
                        context_errors[item] = (
                            f"unable to resolve a SuperProduct component price [{item}]"
                        )
                    else:
                        base_price[item] = round(sum(
                            float(row.price) * int(row.Quantity or 1)
                            for row in actual
                        ), 2)
                    if item in context_errors:
                        eligible_base_items.discard(item)

            plc_by_item = self._fetch_plc(items, site, repo, conn)
            inc_by_item: dict[str, dict[str, tuple[float, int, int]]] = {}
            # OBX order codes repeat across option groups, so OBX also keeps the
            # rows grouped by PDM OptionId (in PDM row order).
            inc_groups_by_item: dict[str, dict[str, dict[str, tuple[float, int]]]] = {}
            fabric_groups_by_item: dict[str, dict[str, dict[str, float]]] = {}
            fabric_targets_by_item: dict[str, dict[str, list[str]]] = {}

            for r in all_increment_rows:
                item = str(r.Item)
                if item not in inc_items and item not in us_increment_items:
                    continue
                if item not in us_items:
                    try:
                        if int(getattr(r, "Status", None)) != 1:
                            continue
                    except (TypeError, ValueError):
                        continue
                inc_price = getattr(r, "IncPrice", None)
                code = str(r.OrderCodeValue2 or "").strip().upper()

                if obx or item in us_items:
                    group = str(getattr(r, "OptionId", "") or "")
                    is_fabric = int(r.IsFabric or 0)
                    inc_groups_by_item.setdefault(item, {}).setdefault(group, {})[code] = (
                        0.0 if inc_price is None else float(inc_price),
                        int(r.Quantity or 1) if is_fabric == 0 else 1,
                    )
                    if is_fabric == 1 and code.endswith("#") and inc_price is not None:
                        fabric_groups_by_item.setdefault(item, {}).setdefault(group, {})[code] = float(inc_price)
                    elif is_fabric == 2:
                        parent_group = str(getattr(r, "ParentOptId", "") or "")
                        if parent_group and code:
                            fabric_targets_by_item.setdefault(item, {}).setdefault(code, []).append(parent_group)

                if inc_price is None:
                    continue

                is_fabric = int(r.IsFabric or 0)
                quantity = int(r.Quantity or 1)
                inc_by_item.setdefault(item, {})[code] = (
                    float(inc_price),
                    is_fabric,
                    quantity,
                )

            component_increment_items = sorted({
                line.base for line in chunk
                if line.base in super_product_items
                and line.base in eligible_base_items
                and line.base in base_price
                and line.options
                and line.seq not in option_errors_by_seq
            })
            component_increment_rows = (
                repo.fetch_item_component_increment_prices(
                    component_increment_items, currency, mydate, site, connection=conn
                )
                if component_increment_items
                else []
            )
            component_increments_by_item: dict[str, list[Any]] = {}
            for row in component_increment_rows:
                component_increments_by_item.setdefault(
                    str(getattr(row, "ParentItem", "")), []
                ).append(row)

            for line in chunk:
                # A worker can report an individual option lookup as skipped.
                # Do not manufacture a pricing result for it; the OBX worker
                # will retain that line as pending so it can be retried alone.
                if line.base in skipped_option_items:
                    continue
                done[0] += 1
                if progress:
                    progress(done[0], total, line.base)
                sku = self._sku(line)
                sif = line.sif_price
                plc = plc_by_item.get(line.base, "")
                if line.base not in eligible_base_items:
                    results.append(SifResult(
                        seq=line.seq, sku=sku, currency=currency, plc=plc,
                        qty=line.qty, source_date=line.source_date, sif_price=sif,
                        status="unresolved", message=context_errors.get(
                            line.base, f"unable to resolve SKU in PDM [{line.base}]"
                        ),
                    ))
                    if on_result:
                        on_result(results[-1])
                    continue
                option_error = option_errors_by_seq.get(line.seq)
                if option_error:
                    results.append(SifResult(
                        seq=line.seq, sku=sku, currency=currency, plc=plc,
                        qty=line.qty, source_date=line.source_date, sif_price=sif,
                        status="unresolved", message=option_error,
                    ))
                    if on_result:
                        on_result(results[-1])
                    continue
                base = base_price.get(line.base)
                if base is None:
                    results.append(SifResult(
                        seq=line.seq, sku=sku, currency=currency, plc=plc, qty=line.qty, source_date=line.source_date, sif_price=sif,
                        status="unresolved", message=context_errors.get(
                            line.base, f"unable to resolve SKU in PDM [{line.base}]"
                        )))
                    if on_result:
                        on_result(results[-1])
                    continue
                if line.base in super_product_items:
                    upcharge = self._match_component_increments(
                        component_increments_by_item.get(line.base, []),
                        [option.code for option in line.options],
                        line.base,
                    )
                elif obx or line.base in us_items:
                    upcharge = self._match_inc_groups(
                        inc_groups_by_item.get(line.base, {}),
                        [o.code for o in line.options],
                        fabric_groups_by_item.get(line.base, {}),
                        fabric_targets_by_item.get(line.base, {}),
                    )
                else:
                    inc = inc_by_item.get(line.base, {})
                    upcharge = sum(self._match_inc(inc, o.code) for o in line.options)
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
