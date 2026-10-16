"""Append-only export of computed prices into an existing OCD MDB.

Unlike the full OCD exporter, this service never deletes or updates destination
rows. It adds missing price lists when necessary and inserts only price records
whose identity is not already present.
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


class PriceMdbExportService(BaseService):
    """Append computed price rows to an existing MDB without destructive writes."""

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

    def export(self, snapshot: Snapshot, mdb_path: str | Path) -> dict[str, Any]:
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
                })
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
        used_labels = {str(r.get("com_PriceListLabel") or "").strip().upper() for r in existing_lists}

        for price_list in (snapshot.price_lists or []):
            currency = (price_list.currency or "").strip().upper()
            label = (price_list.label or price_list.id or "").strip().upper()
            if not currency or not label:
                continue
            found = next((r for r in existing_lists if
                str(r.get("com_PriceListLabel") or "").strip().upper() == label
                and str(r.get("sys_ISOCurrencyCode") or "").strip().upper() == currency), None)
            if found is None:
                found = next((r for r in list_rows if
                    str(r.get("com_PriceListLabel") or "").strip().upper() == label
                    and str(r.get("sys_ISOCurrencyCode") or "").strip().upper() == currency), None)
            if found is None and label not in used_labels:
                found = OcdExportService._row(list_proto, {
                    "com_PriceListID": next_list_id,
                    "com_PriceListLabel": label,
                    "sys_ISOCurrencyCode": currency,
                    "com_PriceValidFrom": _mdb_date_literal(price_list.date_from or _DATE_MIN),
                    "com_PriceValidTo": _mdb_date_literal(price_list.date_to or _DATE_MAX),
                })
                list_rows.append(found)
                next_list_id += 1
                used_labels.add(label)
            if found is not None:
                list_by_currency.setdefault(currency, []).append({
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

        def record_list(record):
            currency = (record.currency or "").strip().upper()
            candidates = list_by_currency.get(currency, [])
            if not candidates:
                return None
            record_from = norm_date(record.valid_from, _DATE_MIN)
            for candidate in candidates:
                if candidate["date_from"] <= record_from <= candidate["date_to"]:
                    return candidate
            # A single list for this currency is unambiguous even when the date
            # metadata differs in formatting between PDM and Access.
            return candidates[0] if len(candidates) == 1 else None

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
                        "com_PriceLevelCode, sys_ISOCurrencyCode, com_PriceValue "
                        "FROM tCOMd_Price WHERE com_ArticleID IN (" + article_filter + ") "
                        "AND com_PriceListID IN (" + list_filter + ")"
                    ),
                    "global_keys": (
                        "SELECT com_GlobalPriceID, com_PackageID, com_PriceListID, com_VariantCondition, "
                        "com_PriceLevelCode, sys_ISOCurrencyCode, com_PriceValue "
                        "FROM tCOMd_GlobalPrice WHERE com_PackageID = " + str(package_id) + " "
                        "AND com_PriceListID IN (" + list_filter + ")"
                    ),
                    "price_max": "SELECT MAX(com_PriceID) AS max_id FROM tCOMd_Price",
                    "global_max": "SELECT MAX(com_GlobalPriceID) AS max_id FROM tCOMd_GlobalPrice",
                })
                existing_prices = targeted["price_keys"]
                existing_globals = targeted["global_keys"]
                price_max_rows = targeted["price_max"]
                global_max_rows = targeted["global_max"]
            except Exception as exc:
                return {"ok": False, "error": f"Could not read existing price identities: {exc}"}
        else:
            price_max_rows = [{"max_id": max((int(r.get("com_PriceID") or 0) for r in existing_prices), default=0)}]
            global_max_rows = [{"max_id": max((int(r.get("com_GlobalPriceID") or 0) for r in existing_globals), default=0)}]

        def key(row, global_price=False):
            return (
                str(row.get("com_PackageID" if global_price else "com_ArticleID") or ""),
                str(row.get("com_PriceListID") or ""),
                str(row.get("com_VariantCondition") or ""),
                str(row.get("com_PriceLevelCode") or "B"),
                str(row.get("sys_ISOCurrencyCode") or "").strip().upper(),
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
        next_price_id = int((price_max_rows[0].get("max_id") if price_max_rows else 0) or 0) + 1
        next_global_id = int((global_max_rows[0].get("max_id") if global_max_rows else 0) or 0) + 1
        price_rows: list[dict[str, Any]] = []
        global_rows: list[dict[str, Any]] = []
        skipped_existing = skipped_unmapped = 0
        value_updates: list[dict[str, Any]] = []

        for record in snapshot.price_records:
            price_list = record_list(record)
            if price_list is None:
                skipped_unmapped += 1
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
                (record.level or "B").strip() or "B",
                (record.currency or "").strip().upper(),
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
            if row_key in target_keys:
                # Update only the value in the exact matched row. Identity,
                # validity, currency and all unrelated rows remain untouched.
                matching_rows = existing_map[row_key]
                primary_key = "com_GlobalPriceID" if is_global else "com_PriceID"
                table_name = "tCOMd_GlobalPrice" if is_global else "tCOMd_Price"
                for existing_row in matching_rows:
                    existing_value = existing_row.get("com_PriceValue")
                    try:
                        same_value = existing_value is not None and abs(
                            float(existing_value) - price_value
                        ) < 1e-9
                    except (TypeError, ValueError):
                        same_value = False
                    if same_value:
                        skipped_existing += 1
                        continue
                    existing_id = existing_row.get(primary_key)
                    if existing_id is None:
                        return {
                            "ok": False,
                            "error": (
                                f"Cannot safely update mismatched price {row_key}: "
                                f"existing {primary_key} is missing."
                            ),
                        }
                    value_updates.append({
                        "op": "update",
                        "table": table_name,
                        "set": {"com_PriceValue": price_value},
                        "where": {primary_key: existing_id},
                    })
                continue
            common = {
                "com_PriceListID": price_list["id"],
                "com_VariantCondition": record.variant_condition or "",
                "com_PriceTypeCode": "S",
                "com_PriceLevelCode": (record.level or "B").strip() or "B",
                "com_PriceRuleCode": None,
                "com_TextID": None,
                "com_PriceValue": price_value,
                "sys_ISOCurrencyCode": (record.currency or "").strip().upper(),
                "com_PriceIndex": "",
                "com_PriceValidFrom": _mdb_date_literal(record.valid_from or price_list["date_from"]),
                "com_PriceValidTo": _mdb_date_literal(record.valid_to or price_list["date_to"]),
                "com_RoundingID": None,
                "com_StatusInfoID": None,
            }
            if is_global:
                global_rows.append(OcdExportService._row(global_proto, {
                    "com_GlobalPriceID": next_global_id,
                    "com_PackageID": package_id,
                    **common,
                }))
                next_global_id += 1
                existing_global_keys.add(row_key)
            else:
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
        if not ops:
            return {
                "ok": True, "mdb_path": str(mdb), "inserted_prices": 0,
                "inserted_global_prices": 0, "inserted_price_lists": 0,
                "skipped_existing": skipped_existing, "skipped_unmapped": skipped_unmapped,
            }
        batch = mdb_service.execute_batch(mdb, ops, transaction=True)
        return {
            "ok": batch.ok, "error": batch.first_error(), "mdb_path": str(mdb),
            "inserted_prices": len(price_rows), "inserted_global_prices": len(global_rows),
            "inserted_price_lists": len(list_rows),
            "updated_prices": sum(1 for op in value_updates if op["table"] == "tCOMd_Price"),
            "updated_global_prices": sum(1 for op in value_updates if op["table"] == "tCOMd_GlobalPrice"),
            "skipped_existing": skipped_existing,
            "skipped_unmapped": skipped_unmapped,
        }
