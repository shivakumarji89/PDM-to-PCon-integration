"""Non-destructive export of computed prices into an existing OCD MDB.

Unlike the full OCD exporter, this service never deletes destination rows. A
computed price whose identity already exists has only its ``com_PriceValue``
corrected; a price with no matching row is inserted. Computed prices are mapped
onto the destination's *existing* price lists (matched by currency and a
separator/case-insensitive label), preferring the list that is linked to a
distribution region - the only lists pCon actually reads. A new list is created
only when none matches, and is reported because it is unreachable until linked.
"""
from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta, timezone
import re
from typing import Any

from models.snapshot import Snapshot
from services.base_service import BaseService
from services.ocd_export_service import OcdExportService, _DATE_MAX, _DATE_MIN
from services.price_update_service import _mdb_date_literal


#: Level of every new global price row: PDM's AddMissingGlobalPricingRecords
#: hardcodes 'X', and every vendor/rolled-over ``tCOMd_GlobalPrice`` row is 'X'.
_GLOBAL_LEVEL = "X"


def _label_key(label: Any) -> str:
    """Label identity that ignores case and space/underscore/hyphen differences
    (``EURO 2026_2`` and ``EURO_2026_2`` are the same price list)."""
    return re.sub(r"[\s_\-]+", "_", str(label or "").strip().upper())


class PriceMdbExportService(BaseService):
    """Write computed price rows into an existing MDB without deleting anything."""

    @staticmethod
    def _clean_prototype(rows: list[dict[str, Any]], table: str) -> dict[str, Any]:
        """Remove generated primary keys and temporary columns from a prototype row."""
        if not rows:
            return {}
        from services.ocd_export_service import _PK
        proto = dict(rows[0])
        proto.pop(_PK.get(table, ""), None)
        for col in [name for name in proto if name.startswith("sys_tmp")]:
            proto.pop(col, None)
        return proto

    @staticmethod
    def _normalize_mdb_date(value: Any, fallback: str) -> str:
        """Normalize Access bridge dates, including JavaScript /Date(ms)/ values."""
        if value is None:
            return fallback
        if isinstance(value, datetime):
            return value.strftime("%Y%m%d")
        if hasattr(value, "strftime") and not isinstance(value, str):
            try:
                return value.strftime("%Y%m%d")
            except (TypeError, ValueError):
                pass
        text = str(value).strip()
        if not text:
            return fallback
        match = re.fullmatch(r"/Date\((-?\d+)(?:[+-]\d{4})?\)/", text)
        if match:
            try:
                instant = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(
                    milliseconds=int(match.group(1))
                )
                return instant.astimezone().strftime("%Y%m%d")
            except (ValueError, OverflowError, OSError):
                return fallback
        digits = re.sub(r"\D", "", text)
        if len(digits) >= 8:
            candidate = digits[:8]
            try:
                datetime.strptime(candidate, "%Y%m%d")
                return candidate
            except ValueError:
                return fallback
        return fallback

    @staticmethod
    def _price_text_name(variant_condition: str) -> str:
        """``tCOMd_Text.com_TextName`` of a global price's 'price' text, as PDM's
        ``AddMissingGlobalPricingRecords`` derives it: a surcharge row
        (``ITEM 8=1FD``) shares the option-id text ``8``; any other variant
        condition is its own text name."""
        vc = variant_condition or ""
        if " " in vc and "=" in vc and vc.index(" ") < vc.index("="):
            return vc[vc.index(" ") + 1:].split("=", 1)[0]
        return vc

    def export(self, snapshot: Snapshot, mdb_path: str | Path, dry_run: bool = False) -> dict[str, Any]:
        """Write ``snapshot.price_records`` into ``mdb_path`` (see module docstring).

        ``dry_run`` reads the MDB and reports exactly what would be updated,
        inserted or skipped, without executing any write.
        """
        mdb = Path(mdb_path)
        if not mdb.is_file():
            return {"ok": False, "error": "Select an existing OCD MDB file."}
        if not snapshot.price_records:
            return {"ok": False, "error": "Compute prices before exporting."}

        mdb_service = self.context.mdb_service
        if not mdb_service.is_available():
            return {"ok": False, "error": "32-bit PowerShell / ACE bridge unavailable."}

        optimized_reads = callable(getattr(mdb_service, "read_tables", None))
        # Only fetch article IDs that are referenced by the computed snapshot.
        # Large OCD files can contain far more articles than this export needs.
        relevant_article_codes = sorted({
            (record.article_code or "").strip()
            for record in snapshot.price_records
            if not record.is_global and (record.article_code or "").strip()
        })
        article_code_filter = ", ".join(
            "'" + code.replace("'", "''") + "'" for code in relevant_article_codes
        ) or "NULL"
        article_query = (
            "SELECT com_ArticleID, com_ArticleCode FROM tCOMd_Article "
            "WHERE com_ArticleCode IN (" + article_code_filter + ")"
        )
        try:
            if optimized_reads:
                initial = mdb_service.read_tables(mdb, {
                    "articles": article_query,
                    "packages": "SELECT TOP 1 com_PackageID FROM tCOMd_Package",
                    "lists": "SELECT com_PriceListID, com_PriceListLabel, sys_ISOCurrencyCode, "
                             "com_PriceValidFrom, com_PriceValidTo FROM tCOMd_PriceList2",
                    "price_proto": "SELECT TOP 1 * FROM [tCOMd_Price]",
                    "global_proto": "SELECT TOP 1 * FROM [tCOMd_GlobalPrice]",
                    "list_proto": "SELECT TOP 1 * FROM [tCOMd_PriceList2]",
                    "linked": "SELECT DISTINCT com_PriceListID FROM tCOMd_DistributionRegionPriceList",
                })
                linked_list_ids = {str(r.get("com_PriceListID")) for r in initial["linked"]}
                articles = initial["articles"]
                packages = initial["packages"]
                existing_lists = initial["lists"]
                price_proto = self._clean_prototype(initial["price_proto"], "tCOMd_Price")
                global_proto = self._clean_prototype(initial["global_proto"], "tCOMd_GlobalPrice")
                list_proto = self._clean_prototype(initial["list_proto"], "tCOMd_PriceList2")
                # Avoid serializing every existing price row from a potentially
                # large MDB. The relevant identity rows and ID maxima are fetched
                # in a second bridge session after list/article mapping is known.
                existing_prices = []
                existing_globals = []
            else:
                # Compatibility path for lightweight adapters/test doubles.
                articles = mdb_service.read_table(
                    mdb, "SELECT com_ArticleID, com_ArticleCode FROM tCOMd_Article"
                )
                packages = mdb_service.read_table(
                    mdb, "SELECT TOP 1 com_PackageID FROM tCOMd_Package"
                )
                existing_lists = mdb_service.read_table(
                    mdb, "SELECT com_PriceListID, com_PriceListLabel, sys_ISOCurrencyCode, "
                         "com_PriceValidFrom, com_PriceValidTo FROM tCOMd_PriceList2"
                )
                existing_prices = mdb_service.read_table(
                    mdb, "SELECT com_PriceID, com_ArticleID, com_PriceListID, "
                         "com_VariantCondition, com_PriceLevelCode, sys_ISOCurrencyCode, com_PriceValue "
                         "FROM tCOMd_Price"
                )
                existing_globals = mdb_service.read_table(
                    mdb, "SELECT com_GlobalPriceID, com_PackageID, com_PriceListID, "
                         "com_VariantCondition, com_PriceLevelCode, sys_ISOCurrencyCode, com_PriceValue "
                         "FROM tCOMd_GlobalPrice"
                )
                linked_list_ids = {str(r.get("com_PriceListID")) for r in mdb_service.read_table(
                    mdb, "SELECT DISTINCT com_PriceListID FROM tCOMd_DistributionRegionPriceList")}
                price_proto = OcdExportService(self.context)._prototype(mdb, "tCOMd_Price")
                global_proto = OcdExportService(self.context)._prototype(mdb, "tCOMd_GlobalPrice")
                list_proto = OcdExportService(self.context)._prototype(mdb, "tCOMd_PriceList2")
        except Exception as exc:
            return {"ok": False, "error": f"Could not read destination MDB schema/data: {exc}"}

        if not packages:
            return {"ok": False, "error": "Destination MDB has no package row."}
        article_ids = {
            str(row.get("com_ArticleCode") or "").strip(): row.get("com_ArticleID")
            for row in articles
        }
        package_id = packages[0].get("com_PackageID")

        def norm_date(value: Any, fallback: str) -> str:
            return self._normalize_mdb_date(value, fallback)

        numeric_ids = []
        for row in existing_lists:
            try:
                numeric_ids.append(int(row.get("com_PriceListID")))
            except (TypeError, ValueError):
                pass
        next_list_id = max(numeric_ids, default=0) + 1
        list_rows: list[dict[str, Any]] = []
        list_by_currency: dict[str, list[dict[str, Any]]] = {}
        used_labels = {_label_key(r.get("com_PriceListLabel")) for r in existing_lists}

        def list_rank(row, label):
            """Best list first: linked to a distribution region (the only lists
            pCon reads), then exact label, then lowest id - deterministic."""
            try:
                list_id = int(row.get("com_PriceListID"))
            except (TypeError, ValueError):
                list_id = 0
            return (
                0 if str(row.get("com_PriceListID")) in linked_list_ids else 1,
                0 if str(row.get("com_PriceListLabel") or "").strip().upper() == label else 1,
                list_id,
            )

        snapshot_list_ids: set[str] = set()
        for price_list in (snapshot.price_lists or []):
            currency = (price_list.currency or "").strip().upper()
            label = (price_list.label or price_list.id or "").strip().upper()
            if not currency or not label:
                continue
            matches = [r for r in (*existing_lists, *list_rows) if
                _label_key(r.get("com_PriceListLabel")) == _label_key(label)
                and str(r.get("sys_ISOCurrencyCode") or "").strip().upper() == currency]
            found = min(matches, key=lambda r: list_rank(r, label)) if matches else None
            if found is None and _label_key(label) not in used_labels:
                found = OcdExportService._row(list_proto, {
                    "com_PriceListID": next_list_id,
                    "com_PriceListLabel": label,
                    "sys_ISOCurrencyCode": currency,
                    "com_PriceValidFrom": _mdb_date_literal(price_list.date_from or _DATE_MIN),
                    "com_PriceValidTo": _mdb_date_literal(price_list.date_to or _DATE_MAX),
                })
                list_rows.append(found)
                next_list_id += 1
                used_labels.add(_label_key(label))
            if found is not None and str(found.get("com_PriceListID")) not in snapshot_list_ids:
                snapshot_list_ids.add(str(found.get("com_PriceListID")))
                list_by_currency.setdefault(currency, []).append({
                    "from_snapshot": True,
                    "id": found.get("com_PriceListID"),
                    "label": str(found.get("com_PriceListLabel") or label),
                    "date_from": norm_date(found.get("com_PriceValidFrom") or price_list.date_from, _DATE_MIN),
                    "date_to": norm_date(found.get("com_PriceValidTo") or price_list.date_to, _DATE_MAX),
                })

        # Include existing lists for currencies not explicitly represented in the
        # snapshot, but never invent a price list if none exists.
        for row in existing_lists:
            currency = str(row.get("sys_ISOCurrencyCode") or "").strip().upper()
            if currency and not any(str(x["id"]) == str(row.get("com_PriceListID"))
                                    for x in list_by_currency.get(currency, [])):
                list_by_currency.setdefault(currency, []).append({
                    "id": row.get("com_PriceListID"),
                    "label": str(row.get("com_PriceListLabel") or ""),
                    "date_from": norm_date(row.get("com_PriceValidFrom"), _DATE_MIN),
                    "date_to": norm_date(row.get("com_PriceValidTo"), _DATE_MAX),
                })

        ambiguous_lists: set[str] = set()

        def record_list(record):
            currency = (record.currency or "").strip().upper()
            candidates = list_by_currency.get(currency, [])
            if not candidates:
                return None
            record_from = norm_date(record.valid_from, _DATE_MIN)
            covering = [c for c in candidates
                        if c["date_from"] <= record_from <= c["date_to"]]
            # Lists the snapshot named explicitly win over unrelated lists that
            # merely cover the same date (e.g. a static NOPRICE list).
            named = [c for c in covering if c.get("from_snapshot")]
            if named:
                return named[0]
            if len(covering) == 1:
                return covering[0]
            # A single list for this currency is unambiguous even when the date
            # metadata differs in formatting between PDM and Access.
            if len(candidates) == 1:
                return candidates[0]
            if covering:
                ambiguous_lists.add(currency)  # several lists, none named: do not guess
            return None

        if optimized_reads:
            # Read only existing identities that can collide with this export,
            # plus aggregate next-ID values; this avoids moving the entire MDB
            # price tables through PowerShell JSON serialization.
            relevant_article_ids = sorted({
                str(article_ids.get((record.article_code or "").strip()))
                for record in snapshot.price_records
                if not record.is_global
                and article_ids.get((record.article_code or "").strip()) is not None
            })
            relevant_list_ids = sorted({
                str(mapped["id"])
                for record in snapshot.price_records
                for mapped in [record_list(record)]
                if mapped is not None and mapped.get("id") is not None
            })
            def sql_in(values):
                return ", ".join(v if v.lstrip("-").isdigit() else "'" + v.replace("'", "''") + "'" for v in values)
            list_filter = sql_in(relevant_list_ids) if relevant_list_ids else "NULL"
            article_filter = sql_in(relevant_article_ids) if relevant_article_ids else "NULL"
            try:
                targeted = mdb_service.read_tables(mdb, {
                    "price_keys": (
                        "SELECT com_PriceID, com_ArticleID, com_PriceListID, com_VariantCondition, "
                        "com_PriceLevelCode, sys_ISOCurrencyCode, com_PriceValue, "
                        "com_PriceValidFrom, com_PriceValidTo "
                        "FROM tCOMd_Price WHERE com_ArticleID IN (" + article_filter + ") "
                        "AND com_PriceListID IN (" + list_filter + ")"
                    ),
                    "global_keys": (
                        "SELECT com_GlobalPriceID, com_PackageID, com_PriceListID, com_VariantCondition, "
                        "com_PriceLevelCode, sys_ISOCurrencyCode, com_PriceValue "
                        "FROM tCOMd_GlobalPrice WHERE com_PackageID = " + str(package_id) + " "
                        "AND com_PriceListID IN (" + list_filter + ")"
                    ),
                    "texts": (
                        "SELECT com_TextID, com_TextName FROM tCOMd_Text WHERE "
                        "com_TextTypeCode = 'price' AND com_PackageID = " + str(package_id)
                    ),
                    "price_max": "SELECT MAX(com_PriceID) AS max_id FROM tCOMd_Price",
                    "global_max": "SELECT MAX(com_GlobalPriceID) AS max_id FROM tCOMd_GlobalPrice",
                })
                existing_prices = targeted["price_keys"]
                existing_globals = targeted["global_keys"]
                price_texts = targeted["texts"]
                price_max_rows = targeted["price_max"]
                global_max_rows = targeted["global_max"]
            except Exception as exc:
                return {"ok": False, "error": f"Could not read existing price identities: {exc}"}
        else:
            price_texts = mdb_service.read_table(
                mdb, "SELECT com_TextID, com_TextName FROM tCOMd_Text WHERE "
                     "com_TextTypeCode = 'price' AND com_PackageID = " + str(package_id))
            price_max_rows = [{"max_id": max((int(r.get("com_PriceID") or 0) for r in existing_prices), default=0)}]
            global_max_rows = [{"max_id": max((int(r.get("com_GlobalPriceID") or 0) for r in existing_globals), default=0)}]

        def key(row, global_price=False):
            # Identity as in PDM's UpdatePConItemPrice: owner (article/package) +
            # price list + variant condition, plus level B/X for article prices.
            # A global price's level is not part of it (vendor rows are all 'X'
            # while the computed record carries none) and row currency is not
            # compared (the list fixes the currency).
            return (
                str(row.get("com_PackageID" if global_price else "com_ArticleID") or ""),
                str(row.get("com_PriceListID") or ""),
                str(row.get("com_VariantCondition") or ""),
                "" if global_price else str(row.get("com_PriceLevelCode") or "B"),
            )

        # Preserve every matching row, not just the last row for an identity.
        # Some OCD files contain duplicate identities; pCon may display a zero
        # row even when another duplicate already has the computed value.
        existing_price_by_key: dict[tuple, list[dict[str, Any]]] = {}
        existing_global_by_key: dict[tuple, list[dict[str, Any]]] = {}
        for row in existing_prices:
            existing_price_by_key.setdefault(key(row), []).append(row)
        for row in existing_globals:
            existing_global_by_key.setdefault(key(row, True), []).append(row)
        existing_price_keys = set(existing_price_by_key)
        existing_global_keys = set(existing_global_by_key)
        handled_keys: set[tuple] = set()  # identities already planned this run
        text_ids = {str(t.get("com_TextName")): t.get("com_TextID") for t in price_texts}
        # Validity of a new article price: PDM copies the article's existing price
        # dates (addNewArticlePriceRecord); a new global price takes the list's.
        article_validity = {
            (str(r.get("com_ArticleID")), str(r.get("com_PriceListID"))): (
                norm_date(r.get("com_PriceValidFrom"), ""), norm_date(r.get("com_PriceValidTo"), ""))
            for r in existing_prices if r.get("com_PriceValidFrom") and r.get("com_PriceValidTo")
        }
        missing_text_names: set[str] = set()
        planned_update_detail: list[dict[str, Any]] = []
        # Lists that receive a write / records that hit several existing rows:
        # reported so the target can be checked before anything is written.
        target_lists: dict[str, dict[str, Any]] = {}
        duplicate_matches = 0

        def note_target(price_list, kind):
            entry = target_lists.setdefault(str(price_list["id"]), {
                "id": price_list["id"], "label": price_list["label"],
                "linked": str(price_list["id"]) in linked_list_ids,
                "updates": 0, "inserts": 0})
            entry[kind] += 1
        next_price_id = int((price_max_rows[0].get("max_id") if price_max_rows else 0) or 0) + 1
        next_global_id = int((global_max_rows[0].get("max_id") if global_max_rows else 0) or 0) + 1
        price_rows: list[dict[str, Any]] = []
        global_rows: list[dict[str, Any]] = []
        skipped_existing = skipped_unmapped = skipped_ambiguous = skipped_zero = 0
        value_updates: list[dict[str, Any]] = []

        for record in snapshot.price_records:
            price_list = record_list(record)
            if price_list is None:
                skipped_unmapped += 1
                if (record.currency or "").strip().upper() in ambiguous_lists:
                    skipped_ambiguous += 1
                continue
            is_global = bool(record.is_global)
            article_id = article_ids.get((record.article_code or "").strip()) if not is_global else None
            if not is_global and article_id is None:
                skipped_unmapped += 1
                continue
            row_key = (
                str(package_id if is_global else article_id),
                str(price_list["id"]),
                record.variant_condition or "",
                "" if is_global else (record.level or "B").strip() or "B",
            )
            target_keys = existing_global_keys if is_global else existing_price_keys
            existing_map = existing_global_by_key if is_global else existing_price_by_key
            try:
                price_value = float(record.value)
            except (TypeError, ValueError):
                skipped_unmapped += 1
                continue
            if not __import__("math").isfinite(price_value):
                skipped_unmapped += 1
                continue
            if price_value == 0.0:
                # PDM never writes a zero price (``if (num7 != 0.0 ...)``): an
                # unresolved/zero PDM price must not overwrite or create a row.
                skipped_zero += 1
                continue
            if (is_global, row_key) in handled_keys:
                skipped_existing += 1  # same identity computed twice: first one wins
                continue
            handled_keys.add((is_global, row_key))
            if row_key in target_keys:
                # Correct only com_PriceValue, on every row sharing this identity
                # (some OCD files carry duplicates and pCon may read any of them);
                # a row that already holds the value is left alone. Identity,
                # validity, currency and all unrelated rows remain untouched.
                primary_key = "com_GlobalPriceID" if is_global else "com_PriceID"
                table_name = "tCOMd_GlobalPrice" if is_global else "tCOMd_Price"
                stale = 0
                for existing_row in existing_map[row_key]:
                    existing_value = existing_row.get("com_PriceValue")
                    try:
                        same_value = existing_value is not None and abs(
                            float(existing_value) - price_value
                        ) < 1e-9
                    except (TypeError, ValueError):
                        same_value = False
                    if same_value:
                        continue
                    existing_id = existing_row.get(primary_key)
                    if existing_id is None:
                        return {
                            "ok": False,
                            "error": (
                                f"Cannot safely update matched price {row_key}: "
                                f"existing {primary_key} is missing."
                            ),
                        }
                    stale += 1
                    note_target(price_list, "updates")
                    planned_update_detail.append({
                        "table": table_name, "id": existing_id,
                        "variant_condition": record.variant_condition or "",
                        "list": price_list["label"], "from": existing_value, "to": price_value})
                    value_updates.append({
                        "op": "update",
                        "table": table_name,
                        "set": {"com_PriceValue": price_value},
                        "where": {primary_key: existing_id},
                    })
                if len(existing_map[row_key]) > 1:
                    duplicate_matches += 1
                if not stale:
                    skipped_existing += 1
                continue
            valid_from, valid_to = (
                article_validity.get((str(article_id), str(price_list["id"])))
                if not is_global else None
            ) or (price_list["date_from"], price_list["date_to"])
            common = {
                "com_PriceListID": price_list["id"],
                "com_VariantCondition": record.variant_condition or "",
                "com_PriceTypeCode": "S",
                # PDM hardcodes 'X' for every global row it creates.
                "com_PriceLevelCode": (
                    _GLOBAL_LEVEL if is_global else (record.level or "B").strip() or "B"
                ),
                "com_PriceRuleCode": None,
                "com_TextID": None,
                "com_PriceValue": price_value,
                "sys_ISOCurrencyCode": (record.currency or "").strip().upper(),
                "com_PriceIndex": "",
                "com_PriceValidFrom": _mdb_date_literal(valid_from),
                "com_PriceValidTo": _mdb_date_literal(valid_to),
                "com_RoundingID": None,
                "com_StatusInfoID": None,
            }
            if is_global:
                text_name = self._price_text_name(record.variant_condition)
                if text_ids.get(text_name) is None:
                    missing_text_names.add(text_name)
                common["com_TextID"] = text_ids.get(text_name)
                note_target(price_list, "inserts")
                global_rows.append(OcdExportService._row(global_proto, {
                    "com_GlobalPriceID": next_global_id,
                    "com_PackageID": package_id,
                    **common,
                }))
                next_global_id += 1
                existing_global_keys.add(row_key)
            else:
                note_target(price_list, "inserts")
                price_rows.append(OcdExportService._row(price_proto, {
                    "com_PriceID": next_price_id,
                    "com_ArticleID": article_id,
                    **common,
                }))
                next_price_id += 1
                existing_price_keys.add(row_key)

        ops = list(value_updates)
        if list_rows:
            ops.append({"op": "insert", "table": "tCOMd_PriceList2", "rows": list_rows})
        if price_rows:
            ops.append({"op": "insert", "table": "tCOMd_Price", "rows": price_rows})
        if global_rows:
            ops.append({"op": "insert", "table": "tCOMd_GlobalPrice", "rows": global_rows})
        report = {
            "mdb_path": str(mdb), "inserted_prices": 0, "inserted_global_prices": 0,
            "inserted_price_lists": 0, "updated_prices": 0, "updated_global_prices": 0,
            "skipped_existing": skipped_existing, "skipped_unmapped": skipped_unmapped,
            "skipped_ambiguous": skipped_ambiguous, "skipped_zero_price": skipped_zero,
            "failed": 0, "verified": None, "verification_failures": [], "warnings": [],
        }
        report["target_lists"] = sorted(target_lists.values(), key=lambda e: str(e["id"]))
        report["duplicate_matches"] = duplicate_matches
        for entry in report["target_lists"]:
            if not entry["linked"] and entry["id"] not in {r.get("com_PriceListID") for r in list_rows}:
                report["warnings"].append(
                    f"Target price list '{entry['label']}' (id {entry['id']}) is not linked to a "
                    "distribution region; pCon will not read prices written to it.")
        if missing_text_names:
            report["warnings"].append(
                f"{len(missing_text_names)} new global price(s) have no matching 'price' text in "
                "tCOMd_Text and were inserted without a text link (PDM would create the text).")
        if dry_run:
            # Report the plan only: nothing is executed.
            report.update({
                "dry_run": True,
                "updated_prices": sum(1 for o in value_updates if o["table"] == "tCOMd_Price"),
                "updated_global_prices": sum(1 for o in value_updates if o["table"] == "tCOMd_GlobalPrice"),
                "inserted_prices": len(price_rows), "inserted_global_prices": len(global_rows),
                "inserted_price_lists": len(list_rows),
                "plan_updates": planned_update_detail,
                "ambiguous_currencies": sorted(ambiguous_lists),
            })
            return {"ok": True, "error": None, **report}
        if not ops:
            return {"ok": True, "error": None, **report}
        batch = mdb_service.execute_batch(mdb, ops, transaction=True)
        if not batch.ok:
            # The batch runs in one transaction, so a failure leaves the MDB
            # untouched: nothing was written, whatever was planned.
            return {"ok": False, "error": batch.first_error(), **report, "failed": len(ops)}

        # Count what the bridge actually executed, not what was planned. Doubles
        # that return no per-op results fall back to the planned counts.
        results = list(getattr(batch, "results", None) or [])
        if len(results) != len(ops):
            results = [None] * len(ops)
        failed = 0
        for op, res in zip(ops, results):
            planned = len(op["rows"]) if op["op"] == "insert" else 1
            done = planned if res is None else (res.inserted if op["op"] == "insert" else res.updated)
            if done < planned:
                failed += planned - done
            if op["op"] == "insert":
                name = {"tCOMd_PriceList2": "inserted_price_lists", "tCOMd_Price": "inserted_prices",
                        "tCOMd_GlobalPrice": "inserted_global_prices"}[op["table"]]
            else:
                name = "updated_global_prices" if op["table"] == "tCOMd_GlobalPrice" else "updated_prices"
            report[name] += done
        report["failed"] = failed
        if failed:
            report["warnings"].append(
                f"{failed} planned write(s) did not change any row; verify the MDB.")
        for row in list_rows:
            report["warnings"].append(
                f"Price list '{row.get('com_PriceListLabel')}' was created but is not linked to a "
                "distribution region (tCOMd_DistributionRegionPriceList); pCon will not read it "
                "until it is linked.")

        if optimized_reads:
            failures = self._verify_writes(mdb, mdb_service, value_updates, price_rows, global_rows)
            report["verified"] = not failures
            report["verification_failures"] = failures[:10]
            if failures:
                return {
                    "ok": False, **report,
                    "error": f"Post-write verification failed for {len(failures)} row(s); "
                             "the MDB does not hold the intended values.",
                }
        return {"ok": True, "error": None, **report}

    @staticmethod
    def _verify_writes(mdb, mdb_service, value_updates, price_rows, global_rows) -> list[str]:
        """Read the written rows back and compare them with what was intended."""
        expected: dict[str, dict[Any, tuple[float, Any, Any]]] = {"tCOMd_Price": {}, "tCOMd_GlobalPrice": {}}
        pk = {"tCOMd_Price": "com_PriceID", "tCOMd_GlobalPrice": "com_GlobalPriceID"}
        for op in value_updates:
            table = op["table"]
            expected[table][op["where"][pk[table]]] = (op["set"]["com_PriceValue"], None, None)
        for table, rows in (("tCOMd_Price", price_rows), ("tCOMd_GlobalPrice", global_rows)):
            for row in rows:
                expected[table][row[pk[table]]] = (
                    row["com_PriceValue"], row["com_PriceListID"], row["com_VariantCondition"])
        queries: dict[str, str] = {}
        for table, wanted in expected.items():
            ids = sorted(wanted)
            for n in range(0, len(ids), 400):
                chunk = ", ".join(str(i) for i in ids[n:n + 400])
                queries[f"{table}:{n}"] = (
                    f"SELECT {pk[table]} AS id, com_PriceValue, com_PriceListID, com_VariantCondition "
                    f"FROM {table} WHERE {pk[table]} IN ({chunk})")
        if not queries:
            return []
        try:
            read = mdb_service.read_tables(mdb, queries)
        except Exception as exc:  # unreadable after a write is itself a failure
            return [f"read-back failed: {exc}"]
        failures: list[str] = []
        for table, wanted in expected.items():
            found = {r["id"]: r for chunk, rows in read.items() if chunk.startswith(table + ":") for r in rows}
            for row_id, (value, list_id, varcond) in wanted.items():
                row = found.get(row_id)
                if row is None:
                    failures.append(f"{table} {row_id}: row missing after write")
                    continue
                try:
                    same = abs(float(row["com_PriceValue"]) - float(value)) < 1e-9
                except (TypeError, ValueError):
                    same = False
                if not same:
                    failures.append(f"{table} {row_id}: value {row['com_PriceValue']} != {value}")
                elif list_id is not None and (
                        str(row["com_PriceListID"]) != str(list_id)
                        or str(row["com_VariantCondition"] or "") != str(varcond or "")):
                    failures.append(f"{table} {row_id}: list/variant differs from intended")
        return failures
