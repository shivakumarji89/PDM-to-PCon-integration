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
import hashlib
import json
import re
from typing import Any

from models.snapshot import Snapshot
from services.base_service import BaseService
from services.ocd_export_service import OcdExportService, _DATE_MAX, _DATE_MIN
from services.price_update_service import _mdb_date_literal
from services.price_list_targets import (
    computation_date, normalize_mdb_date, resolve_targets,
)
from services.price_text_blocks import (
    ACTION_CREATE, ACTION_LINK_NEW, ACTION_NONE, ACTION_PRESERVE, ACTION_REUSE,
    ACTION_SKIP, ACTION_UNLINKED, language_columns, name_key, price_text_labels,
)


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
        return normalize_mdb_date(value, fallback)

    def read_price_lists(self, mdb_path: str | Path) -> dict[str, Any]:
        """Existing price lists and the region-linked list ids (read-only), for the
        target-list dialog. ``{"lists": [...], "linked": {...}}`` or ``{"error": ...}``."""
        mdb_service = self.context.mdb_service
        try:
            read = mdb_service.read_tables(Path(mdb_path), {
                "lists": "SELECT com_PriceListID, com_PriceListLabel, sys_ISOCurrencyCode, "
                         "com_PriceValidFrom, com_PriceValidTo FROM tCOMd_PriceList2",
                "linked": "SELECT DISTINCT com_PriceListID FROM tCOMd_DistributionRegionPriceList",
            })
        except Exception as exc:
            return {"error": f"Could not read price lists: {exc}"}
        return {"lists": read["lists"], "linked": {str(r.get("com_PriceListID")) for r in read["linked"]}}

    def export(self, snapshot: Snapshot, mdb_path: str | Path, dry_run: bool = False,
               list_targets: dict[str, str] | None = None,
               expected_plan: str | None = None) -> dict[str, Any]:
        """Write ``snapshot.price_records`` into ``mdb_path`` (see module docstring).

        ``dry_run`` reads the MDB and reports exactly what would be updated,
        inserted or skipped, without executing any write.

        ``list_targets`` ({currency: chosen list name}) selects strict routing: each
        currency goes only to its validated target list, which must cover the
        computation date; any invalid target blocks the whole export. Without it the
        legacy automatic list selection is used. ``expected_plan`` is the
        ``plan_digest`` of an approved preview: if the MDB or inputs changed since,
        nothing is written.
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
                    "text_proto": "SELECT TOP 1 * FROM [tCOMd_Text]",
                    "linked": "SELECT DISTINCT com_PriceListID FROM tCOMd_DistributionRegionPriceList",
                })
                linked_list_ids = {str(r.get("com_PriceListID")) for r in initial["linked"]}
                articles = initial["articles"]
                packages = initial["packages"]
                existing_lists = initial["lists"]
                price_proto = self._clean_prototype(initial["price_proto"], "tCOMd_Price")
                global_proto = self._clean_prototype(initial["global_proto"], "tCOMd_GlobalPrice")
                list_proto = self._clean_prototype(initial["list_proto"], "tCOMd_PriceList2")
                text_columns = list(initial["text_proto"][0]) if initial["text_proto"] else []
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
                text_rows = mdb_service.read_table(mdb, "SELECT TOP 1 * FROM [tCOMd_Text]")
                text_columns = list(text_rows[0]) if text_rows else []
        except Exception as exc:
            if re.search(r"already in use|could not lock|exclusive", str(exc), re.IGNORECASE):
                return {"ok": False, "error": "The MDB is open exclusively by another process and cannot be "
                                              "read; nothing was written. Close it and retry."}
            return {"ok": False, "error": f"Could not read destination MDB schema/data: {exc}"}

        if not packages:
            return {"ok": False, "error": "Destination MDB has no package row."}
        article_ids = {
            str(row.get("com_ArticleCode") or "").strip(): row.get("com_ArticleID")
            for row in articles
        }
        package_id = packages[0].get("com_PackageID")
        text_lang_cols = language_columns(text_columns)
        en_col = next((c for c in text_lang_cols if c.endswith("_en")), "")

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

        comp_date = computation_date(snapshot.price_records)
        strict = list_targets is not None
        list_plans: dict[str, Any] = {}
        blocking_errors: list[str] = []
        block_reasons: dict[str, int] = {}
        blocked_detail: list[dict[str, Any]] = []
        why: dict[str, str] = {}
        if strict:
            wanted = {str(k).strip().upper(): v for k, v in (list_targets or {}).items()}
            record_currencies = sorted({(r.currency or "").strip().upper()
                                        for r in snapshot.price_records if (r.currency or "").strip()})
            list_plans = resolve_targets(
                {c: wanted.get(c, "") for c in record_currencies},
                existing_lists, linked_list_ids, comp_date)
            for ccy, plan in list_plans.items():
                blocking_errors += [f"{ccy}: {e}" for e in plan.errors]
                if not plan.ok:
                    continue
                if plan.action == "create":
                    list_rows.append(OcdExportService._row(list_proto, {
                        "com_PriceListID": next_list_id,
                        "com_PriceListLabel": plan.name,
                        "sys_ISOCurrencyCode": ccy,
                        "com_PriceValidFrom": _mdb_date_literal(plan.date_from),
                        "com_PriceValidTo": _mdb_date_literal(plan.date_to),
                    }))
                    plan.list_id = next_list_id
                    next_list_id += 1
                    plan.label = plan.name
                else:
                    plan.label = next((str(r.get("com_PriceListLabel") or plan.name) for r in existing_lists
                                       if str(r.get("com_PriceListID")) == str(plan.list_id)), plan.name)
                list_by_currency[ccy] = [{
                    "from_snapshot": True, "id": plan.list_id, "label": plan.label, "currency": ccy,
                    "date_from": plan.date_from, "date_to": plan.date_to,
                }]
        else:
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
            why.clear()
            if strict:
                if not candidates:
                    why["reason"] = "no valid target list for " + (currency or "blank currency")
                    return None
                chosen = candidates[0]
                day = norm_date(record.valid_from, "")
                if not day:
                    why["reason"] = "record has no computation date"
                    return None
                if not chosen["date_from"] <= day <= chosen["date_to"]:
                    why["reason"] = (f"computation date {day} outside list "
                                     f"'{chosen['label']}' ({chosen['date_from']}-{chosen['date_to']})")
                    return None
                return chosen
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
                        "com_PriceLevelCode, sys_ISOCurrencyCode, com_PriceValue, com_TextID "
                        "FROM tCOMd_GlobalPrice WHERE com_PackageID = " + str(package_id) + " "
                        "AND com_PriceListID IN (" + list_filter + ")"
                    ),
                    "texts": (
                        "SELECT com_TextID, com_TextName" + (", " + en_col if en_col else "")
                        + " FROM tCOMd_Text WHERE "
                        "com_TextTypeCode = 'price' AND com_PackageID = " + str(package_id)
                    ),
                    "text_max": "SELECT MAX(com_TextID) AS max_id FROM tCOMd_Text",
                    "price_max": "SELECT MAX(com_PriceID) AS max_id FROM tCOMd_Price",
                    "global_max": "SELECT MAX(com_GlobalPriceID) AS max_id FROM tCOMd_GlobalPrice",
                })
                existing_prices = targeted["price_keys"]
                existing_globals = targeted["global_keys"]
                price_texts = targeted["texts"]
                text_max_rows = targeted["text_max"]
                price_max_rows = targeted["price_max"]
                global_max_rows = targeted["global_max"]
            except Exception as exc:
                return {"ok": False, "error": f"Could not read existing price identities: {exc}"}
        else:
            price_texts = mdb_service.read_table(
                mdb, "SELECT com_TextID, com_TextName FROM tCOMd_Text WHERE "
                     "com_TextTypeCode = 'price' AND com_PackageID = " + str(package_id))
            text_max_rows = mdb_service.read_table(mdb, "SELECT MAX(com_TextID) AS max_id FROM tCOMd_Text")
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
        # Existing price texts by case-insensitive name (Jet's `=`, as PDM's lookup);
        # several ids under one name is ambiguous and is never guessed.
        text_ids_by_name: dict[str, list[Any]] = {}
        for t in price_texts:
            text_ids_by_name.setdefault(name_key(t.get("com_TextName")), []).append(t.get("com_TextID"))
        next_text_id = int((text_max_rows[0].get("max_id") if text_max_rows else 0) or 0) + 1
        text_rows_new: list[dict[str, Any]] = []   # tCOMd_Text rows to create
        new_text_ids: dict[str, Any] = {}          # name key -> id allocated this run
        text_plan: list[dict[str, Any]] = []       # one entry per priced row
        blocked_rows = 0
        # Validity of a new article price: PDM copies the article's existing price
        # dates (addNewArticlePriceRecord); a new global price takes the list's.
        article_validity = {
            (str(r.get("com_ArticleID")), str(r.get("com_PriceListID"))): (
                norm_date(r.get("com_PriceValidFrom"), ""), norm_date(r.get("com_PriceValidTo"), ""))
            for r in existing_prices if r.get("com_PriceValidFrom") and r.get("com_PriceValidTo")
            if norm_date(r.get("com_PriceValidFrom"), "") and norm_date(r.get("com_PriceValidTo"), "")
        }
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

        text_name_by_id = {str(t.get("com_TextID")): str(t.get("com_TextName") or "") for t in price_texts}
        text_content_by_id = {str(t.get("com_TextID")): str(t.get(en_col) or "") for t in price_texts} if en_col else {}

        def text_entry(record, price_list, operation):
            """Row-level text plan; ``text_id`` is only ever an id already in the MDB."""
            return {
                "table": "tCOMd_GlobalPrice" if record.is_global else "tCOMd_Price",
                "article_code": record.article_code or "",
                "variant_condition": record.variant_condition or "",
                "level": record.level,
                "currency": (record.currency or "").strip().upper(),
                "list": price_list["label"], "list_id": price_list["id"], "operation": operation,
                "action": ACTION_NONE, "text_name": "", "text_id": None,
                "text_status": "n/a" if not record.is_global else "", "text_content": "",
                "reason": "",
            }

        def base_key(article_id, list_id, variant):
            # variant compared case-insensitively, as Jet compares it
            return (str(article_id), str(list_id), (variant or "").split(" ")[0].casefold(), "B")

        existing_base_keys = {(a, l, v.casefold(), lv) for a, l, v, lv in existing_price_keys}
        existing_global_base_keys = {(a, l, v.casefold(), lv) for a, l, v, lv in existing_global_keys}

        # An article upcharge (level X, "<suffix> <option>=<value>") is only meaningful on top of
        # its base price row (same article, list and suffix). Every real upcharge row has one and
        # PDM never writes one for an item it could not price, so a new upcharge is inserted only
        # when its base row exists or is written by this same export.
        planned_bases: set[tuple] = set()
        planned_global_bases: set[tuple] = set()

        def is_surcharge(record):
            if record.source_item and record.pdm_lookup_code:
                return record.pdm_lookup_code != record.source_item
            vc = record.variant_condition
            vc = vc or ""
            return " " in vc and "=" in vc and vc.index(" ") < vc.index("=")

        for record in snapshot.price_records:
            if record.is_global:
                mapped = record_list(record)
                try:
                    priced = float(record.value) != 0.0 and __import__("math").isfinite(float(record.value))
                except (TypeError, ValueError):
                    priced = False
                if mapped is not None and priced and not is_surcharge(record):
                    planned_global_bases.add(
                        (str(package_id), str(mapped["id"]), (record.variant_condition or "").casefold(), ""))
                continue
            if (record.level or "B").strip() != "B":
                continue
            mapped = record_list(record)
            article = article_ids.get((record.article_code or "").strip())
            try:
                finite = float(record.value) != 0.0 and __import__("math").isfinite(float(record.value))
            except (TypeError, ValueError):
                finite = False
            if mapped is not None and article is not None and finite and not (record.variant_condition or "").count(" "):
                planned_bases.add(base_key(article, mapped["id"], record.variant_condition))
        skipped_no_base = 0

        for record in snapshot.price_records:
            price_list = record_list(record)
            if price_list is None:
                skipped_unmapped += 1
                if strict:
                    reason = why.get("reason", "no target list")
                    block_reasons[reason] = block_reasons.get(reason, 0) + 1
                    if len(blocked_detail) < 200:
                        blocked_detail.append({
                            "article_code": record.article_code or "",
                            "variant_condition": record.variant_condition or "",
                            "currency": (record.currency or "").strip().upper(), "reason": reason})
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
            match_keys = [row_key]
            if is_global and is_surcharge(record) and record.pdm_lookup_code:
                # The worker can identify a row whose stored condition differs
                # from AddMissingGlobalPricingRecords' insertion condition.
                # Prefer that identity; canonical fallback makes inserts repeatable.
                worker_keys = [
                    (row_key[0], row_key[1], condition, row_key[3])
                    for condition in dict.fromkeys((
                        record.pdm_lookup_code, record.pdm_lookup_code.replace("#", ""),
                    ))
                ]
                match_keys = [k for k in worker_keys if k in existing_map] or match_keys
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
            if any((is_global, k) in handled_keys for k in [row_key, *match_keys]):
                skipped_existing += 1  # same identity computed twice: first one wins
                continue
            handled_keys.add((is_global, row_key))
            handled_keys.update((is_global, k) for k in match_keys)
            if match_keys[0] in target_keys:
                # Correct only com_PriceValue; a row already holding the value
                # is left alone. Identity, validity, currency and unrelated rows
                # remain untouched.
                primary_key = "com_GlobalPriceID" if is_global else "com_PriceID"
                table_name = "tCOMd_GlobalPrice" if is_global else "tCOMd_Price"
                stale = 0
                all_matches = [r for k in match_keys for r in existing_map[k]]
                matched_rows = all_matches
                if not is_global or not is_surcharge(record):
                    # PDM's Article base/surcharge and Global base lookups retain
                    # only the last matching ID; its Global surcharge loop
                    # processes each existing row.
                    matched_rows = matched_rows[-1:]
                for existing_row in matched_rows:
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
                        "variant_condition": existing_row.get("com_VariantCondition") or "",
                        "list": price_list["label"], "from": existing_value, "to": price_value})
                    value_updates.append({
                        "op": "update",
                        "table": table_name,
                        "set": {"com_PriceValue": price_value},
                        "where": {primary_key: existing_id},
                    })
                if len(all_matches) > 1:
                    duplicate_matches += 1
                if not stale:
                    skipped_existing += 1
                # Text links of matched rows are never rewritten (PDM's value update
                # does not touch com_TextID); the plan only reports them.
                linked_id = next((r.get("com_TextID") for r in all_matches
                                  if r.get("com_TextID") not in (None, "")), None)
                entry = text_entry(record, price_list, "update" if stale else "unchanged")
                entry["variant_condition"] = match_keys[0][2]
                if is_global:
                    entry["row_ids"] = [r.get(primary_key) for r in all_matches]
                    entry.update(
                        action=ACTION_PRESERVE if linked_id is not None else ACTION_UNLINKED,
                        text_id=linked_id,
                        text_name=text_name_by_id.get(str(linked_id), ""),
                        text_content=text_content_by_id.get(str(linked_id), ""),
                        text_status="existing" if linked_id is not None else "missing")
                text_plan.append(entry)
                continue
            no_base = False
            if not is_global and (record.level or "B").strip() == "X":
                bk = base_key(article_id, price_list["id"], record.variant_condition)
                no_base = bk not in planned_bases and bk not in existing_base_keys
            elif is_global and is_surcharge(record):
                source_item = record.source_item or record.variant_condition.split(" ")[0]
                gk = (str(package_id), str(price_list["id"]), source_item.casefold(), "")
                no_base = gk not in planned_global_bases and gk not in existing_global_base_keys
            if no_base:
                skipped_no_base += 1
                reason = "upcharge has no base price row (item unpriced)"
                block_reasons[reason] = block_reasons.get(reason, 0) + 1
                if len(blocked_detail) < 200:
                    blocked_detail.append({
                        "article_code": record.article_code or "", "variant_condition": record.variant_condition or "",
                        "currency": (record.currency or "").strip().upper(), "reason": reason})
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
                text_name, display = price_text_labels(record.variant_condition, record.product_code)
                tkey = name_key(text_name)
                known = text_ids_by_name.get(tkey, [])
                entry = text_entry(record, price_list, "insert")
                entry["text_name"] = text_name
                if len(known) > 1:
                    entry.update(action=ACTION_SKIP, text_status="ambiguous",
                                 reason=f"{len(known)} price texts are named '{text_name}'")
                elif len(known) == 1:
                    entry.update(action=ACTION_REUSE, text_id=known[0], text_status="existing",
                                 text_content=text_content_by_id.get(str(known[0]), ""))
                elif tkey in new_text_ids:
                    entry.update(action=ACTION_LINK_NEW, text_status="new")
                elif not text_lang_cols:
                    entry.update(action=ACTION_SKIP, text_status="missing",
                                 reason="tCOMd_Text has no language columns to create the text in")
                elif display == (record.variant_condition or "") and "_" not in display and not record.product_code:
                    # PDM always labels such a text "<item>  (<Product_Code>)"; a label
                    # without it never occurs in the real MDB, so do not create one.
                    entry.update(action=ACTION_SKIP, text_status="missing",
                                 reason=f"Product_Code unknown for '{text_name}'; recompute prices")
                else:
                    entry.update(action=ACTION_CREATE, text_status="new", text_content=display)
                    new_text_ids[tkey] = next_text_id
                    text_rows_new.append({
                        "com_TextID": next_text_id, "com_PackageID": package_id,
                        "com_TextTypeCode": "price", "com_TextName": text_name,
                        **{col: display for col in text_lang_cols},
                    })
                    next_text_id += 1
                text_plan.append(entry)
                if entry["action"] == ACTION_SKIP:
                    blocked_rows += 1
                    continue
                common["com_TextID"] = entry["text_id"] if entry["text_id"] is not None else new_text_ids[tkey]
                note_target(price_list, "inserts")
                entry["row_ids"] = [next_global_id]
                global_rows.append(OcdExportService._row(global_proto, {
                    "com_GlobalPriceID": next_global_id,
                    "com_PackageID": package_id,
                    **common,
                }))
                next_global_id += 1
                existing_global_keys.add(row_key)
            else:
                text_plan.append(text_entry(record, price_list, "insert"))
                note_target(price_list, "inserts")
                price_rows.append(OcdExportService._row(price_proto, {
                    "com_PriceID": next_price_id,
                    "com_ArticleID": article_id,
                    **common,
                }))
                next_price_id += 1
                existing_price_keys.add(row_key)

        ops = []
        if text_rows_new:
            # Texts first: the global rows that follow reference their ids.
            ops.append({"op": "insert", "table": "tCOMd_Text", "rows": text_rows_new})
        ops.extend(value_updates)
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
            "skipped_text_blocked": blocked_rows, "skipped_no_base_price": skipped_no_base,
            "failed": 0, "verified": None, "verification_failures": [], "warnings": [],
        }
        report["target_lists"] = sorted(target_lists.values(), key=lambda e: str(e["id"]))
        report["duplicate_matches"] = duplicate_matches
        report["text_rows"] = text_plan
        report["computation_date"] = comp_date
        report["strict_lists"] = strict
        report["list_plan"] = [{**p.as_dict(), "label": getattr(p, "label", p.name)}
                               for p in list_plans.values()]
        report["blocking_errors"] = blocking_errors
        report["blocked_reasons"] = block_reasons
        report["blocked_rows"] = blocked_detail
        report["export_allowed"] = not blocking_errors
        report["plan_digest"] = hashlib.sha256(json.dumps(
            {"ops": ops, "lists": report["list_plan"]}, sort_keys=True, default=str).encode()).hexdigest()

        def count_action(*actions):
            return sum(1 for e in text_plan if e["action"] in actions)

        text_summary = {
            "price_rows_to_update": len(value_updates),
            "price_rows_to_insert": len(price_rows) + len(global_rows),
            "text_reuse": count_action(ACTION_REUSE),
            "text_create": count_action(ACTION_CREATE),
            "text_link_new": count_action(ACTION_LINK_NEW),
            "text_preserve": count_action(ACTION_PRESERVE),
            "text_unlinked_existing": count_action(ACTION_UNLINKED),
            "text_missing_or_ambiguous": count_action(ACTION_SKIP),
            "rows_blocked": blocked_rows,
        }
        report["text_summary"] = text_summary
        for entry in report["target_lists"]:
            if not entry["linked"] and entry["id"] not in {r.get("com_PriceListID") for r in list_rows}:
                report["warnings"].append(
                    f"Target price list '{entry['label']}' (id {entry['id']}) is not linked to a "
                    "distribution region; pCon will not read prices written to it.")
        if blocked_rows:
            reasons = sorted({e["reason"] for e in text_plan if e["action"] == ACTION_SKIP})
            report["warnings"].append(
                f"{blocked_rows} new global price row(s) were not inserted because their text "
                "block is missing or ambiguous: " + "; ".join(reasons[:3]))
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
        if blocking_errors:
            return {"ok": False, "error": "Target price list validation failed: " + "; ".join(blocking_errors),
                    **report}
        if expected_plan is not None and expected_plan != report["plan_digest"]:
            return {"ok": False, "error": "The MDB or the export inputs changed since the preview; "
                                          "run Preview Export again.", **report}
        if not ops:
            report["text_result"] = self._text_result(text_summary, 0, None)
            return {"ok": True, "error": None, **report}
        batch = mdb_service.execute_batch(mdb, ops, transaction=True)
        if not batch.ok:
            # The batch runs in one transaction, so a failure leaves the MDB
            # untouched: nothing was written, whatever was planned.
            report["text_result"] = self._text_result(text_summary, 0, None, failed=len(text_rows_new))
            error = batch.first_error() or "unknown error"
            if re.search(r"already in use|could not lock|locked|exclusive|sharing violation|cannot open",
                         error, re.IGNORECASE):
                error = ("The MDB is locked or in use by another process (e.g. pCon Creator or PDM) "
                         f"and could not be written; nothing was written. Close it and retry. ({error})")
            return {"ok": False, "error": error, **report, "failed": len(ops)}

        # Count what the bridge actually executed, not what was planned. Doubles
        # that return no per-op results fall back to the planned counts.
        results = list(getattr(batch, "results", None) or [])
        if len(results) != len(ops):
            results = [None] * len(ops)
        failed = 0
        texts_created = 0
        for op, res in zip(ops, results):
            planned = len(op["rows"]) if op["op"] == "insert" else 1
            done = planned if res is None else (res.inserted if op["op"] == "insert" else res.updated)
            if done < planned:
                failed += planned - done
            if op["op"] == "insert":
                if op["table"] == "tCOMd_Text":
                    texts_created += done
                    continue
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

        stats = None
        if optimized_reads:
            failures, stats = self._verify_writes(
                mdb, mdb_service, value_updates, price_rows, global_rows,
                text_rows_new, text_plan, text_lang_cols, package_id, list_rows)
            report["verified"] = not failures
            report["verification_failures"] = failures[:10]
            report["verification_failure_count"] = len(failures)
        # Row-level results: only a verified id is shown as written.
        for entry in text_plan:
            if entry["action"] in (ACTION_CREATE, ACTION_LINK_NEW):
                tid = new_text_ids.get(name_key(entry["text_name"]))
                ok = stats is None or tid in stats["texts_ok"]
                entry["text_id"] = tid if ok else None
                entry["text_status"] = "created" if ok else "unverified"
            elif entry["action"] == ACTION_REUSE:
                entry["text_status"] = "existing"
        report["text_result"] = self._text_result(text_summary, texts_created, stats)
        if report["verified"] is False:
            return {
                "ok": False, **report,
                "error": f"Post-write verification failed for {report['verification_failure_count']} row(s); "
                         "the MDB does not hold the intended values.",
            }
        return {"ok": True, "error": None, **report}

    @staticmethod
    def _text_result(summary, created, stats, failed=0) -> dict[str, Any]:
        """Actual (executed, and where verified read back) text-block results."""
        verified = stats is not None
        return {
            "texts_created": created,
            "texts_reused": stats["reused_ok"] if verified else summary["text_reuse"],
            "rows_linked": stats["rows_linked_ok"] if verified else None,
            "links_preserved": stats["preserved_ok"] if verified else summary["text_preserve"],
            "text_operations_skipped": summary["text_missing_or_ambiguous"],
            "text_operations_failed": failed + (len(stats["failures"]) if verified else 0),
            "readback_verified": verified,
        }

    @staticmethod
    def _verify_writes(mdb, mdb_service, value_updates, price_rows, global_rows,
                       text_rows_new=(), text_plan=(), text_lang_cols=(), package_id=None, list_rows=()):
        """Read the written rows back and compare them with what was intended.

        Returns ``(failures, stats)``: ``failures`` lists every mismatch (price
        values, list/variant identity, text links, text content, duplicate texts,
        dangling references); ``stats`` holds the verified text-block counts.
        """
        expected: dict[str, dict[Any, tuple[float, Any, Any, Any]]] = {"tCOMd_Price": {}, "tCOMd_GlobalPrice": {}}
        pk = {"tCOMd_Price": "com_PriceID", "tCOMd_GlobalPrice": "com_GlobalPriceID"}
        for op in value_updates:
            table = op["table"]
            expected[table][op["where"][pk[table]]] = (op["set"]["com_PriceValue"], None, None, None)
        for table, rows in (("tCOMd_Price", price_rows), ("tCOMd_GlobalPrice", global_rows)):
            for row in rows:
                expected[table][row[pk[table]]] = (
                    row["com_PriceValue"], row["com_PriceListID"], row["com_VariantCondition"],
                    row.get("sys_ISOCurrencyCode"))
        # Text links expected on global rows: inserted rows carry the planned id,
        # preserved/unlinked rows must still hold what they held before.
        expected_text_link: dict[Any, Any] = {r["com_GlobalPriceID"]: r.get("com_TextID") for r in global_rows}
        for entry in text_plan:
            if entry["action"] in (ACTION_PRESERVE, ACTION_UNLINKED):
                for row_id in entry.get("row_ids") or []:
                    expected_text_link[row_id] = entry["text_id"]
        created = {r["com_TextID"]: r for r in text_rows_new}
        referenced = {v for v in expected_text_link.values() if v is not None} | set(created)

        queries: dict[str, str] = {}
        for table, wanted in expected.items():
            ids = sorted(wanted)
            for n in range(0, len(ids), 400):
                chunk = ", ".join(str(i) for i in ids[n:n + 400])
                extra = ", com_TextID" if table == "tCOMd_GlobalPrice" else ""
                queries[f"{table}:{n}"] = (
                    f"SELECT {pk[table]} AS id, com_PriceValue, com_PriceListID, com_VariantCondition, "
                    f"sys_ISOCurrencyCode{extra} "
                    f"FROM {table} WHERE {pk[table]} IN ({chunk})")
        # Every list a written row points at, plus every list this export created:
        # their currency and (for new lists) label / validity are read back too.
        row_currency_by_list: dict[Any, set] = {}
        for wanted in expected.values():
            for _v, list_id, _vc, ccy in wanted.values():
                if list_id is not None:
                    row_currency_by_list.setdefault(list_id, set()).add(str(ccy or "").upper())
        created_lists = {r["com_PriceListID"]: r for r in list_rows}
        list_ids = sorted(set(row_currency_by_list) | set(created_lists), key=str)
        if list_ids:
            queries["lists:0"] = (
                "SELECT com_PriceListID AS id, com_PriceListLabel, sys_ISOCurrencyCode, com_PriceValidFrom, "
                "com_PriceValidTo FROM tCOMd_PriceList2 WHERE com_PriceListID IN ("
                + ", ".join(str(i) for i in list_ids) + ")")
        unchanged_ids = sorted(i for i in expected_text_link if i not in expected["tCOMd_GlobalPrice"])
        for n in range(0, len(unchanged_ids), 400):
            chunk = ", ".join(str(i) for i in unchanged_ids[n:n + 400])
            queries[f"links:{n}"] = (
                f"SELECT com_GlobalPriceID AS id, com_TextID FROM tCOMd_GlobalPrice "
                f"WHERE com_GlobalPriceID IN ({chunk})")
        text_ids = sorted(referenced)
        lang = ", ".join(text_lang_cols)
        for n in range(0, len(text_ids), 400):
            chunk = ", ".join(str(i) for i in text_ids[n:n + 400])
            queries[f"texts:{n}"] = (
                "SELECT com_TextID AS id, com_PackageID, com_TextTypeCode, com_TextName"
                + (", " + lang if lang else "") + f" FROM tCOMd_Text WHERE com_TextID IN ({chunk})")
        names = sorted({r["com_TextName"] for r in text_rows_new})
        for n in range(0, len(names), 100):
            in_list = ", ".join("'" + x.replace("'", "''") + "'" for x in names[n:n + 100])
            queries[f"textdup:{n}"] = (
                "SELECT com_TextName, COUNT(*) AS n FROM tCOMd_Text WHERE com_TextTypeCode = 'price' "
                f"AND com_PackageID = {package_id} AND com_TextName IN ({in_list}) GROUP BY com_TextName")
        stats = {"texts_ok": set(), "reused_ok": 0, "rows_linked_ok": 0, "preserved_ok": 0, "failures": []}
        if not queries:
            return [], stats
        try:
            read = mdb_service.read_tables(mdb, queries)
        except Exception as exc:  # unreadable after a write is itself a failure
            stats["failures"] = [f"read-back failed: {exc}"]
            return [f"read-back failed: {exc}"], stats

        def rows_of(prefix):
            return [r for chunk, rows in read.items() if chunk.startswith(prefix + ":") for r in rows]

        failures: list[str] = []
        text_failures: list[str] = []
        for table, wanted in expected.items():
            found = {r["id"]: r for r in rows_of(table)}
            for row_id, (value, list_id, varcond, want_ccy) in wanted.items():
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
                elif want_ccy and str(row.get("sys_ISOCurrencyCode") or "").upper() != str(want_ccy).upper():
                    failures.append(f"{table} {row_id}: currency {row.get('sys_ISOCurrencyCode')} != {want_ccy}")
                elif list_id is not None and (
                        str(row["com_PriceListID"]) != str(list_id)
                        or str(row["com_VariantCondition"] or "") != str(varcond or "")):
                    failures.append(f"{table} {row_id}: list/variant differs from intended")

        lists_read = {r["id"]: r for r in rows_of("lists")}
        for list_id, currencies in row_currency_by_list.items():
            actual = lists_read.get(list_id)
            if actual is None:
                failures.append(f"tCOMd_PriceList2 {list_id}: list missing after write")
                continue
            list_ccy = str(actual.get("sys_ISOCurrencyCode") or "").upper()
            if currencies - {list_ccy}:
                failures.append(
                    f"currency routing: rows for {sorted(currencies)} point at {list_ccy} list {list_id}")
        for list_id, want in created_lists.items():
            actual = lists_read.get(list_id)
            if actual is None:
                continue
            bad = []
            if str(actual.get("com_PriceListLabel") or "") != str(want["com_PriceListLabel"]):
                bad.append("label")
            if str(actual.get("sys_ISOCurrencyCode") or "") != str(want["sys_ISOCurrencyCode"]):
                bad.append("currency")
            for col in ("com_PriceValidFrom", "com_PriceValidTo"):
                if normalize_mdb_date(actual.get(col), "") != re.sub(r"\D", "", str(want[col]))[:8]:
                    bad.append(col)
            if bad:
                failures.append(f"tCOMd_PriceList2 {list_id}: {', '.join(bad)} differ from intended")

        link_rows = {r["id"]: r for r in rows_of("tCOMd_GlobalPrice")}
        link_rows.update({r["id"]: r for r in rows_of("links")})
        texts = {r["id"]: r for r in rows_of("texts")}
        link_ok: dict[Any, bool] = {}
        for row_id, want in expected_text_link.items():
            row = link_rows.get(row_id)
            if row is None:
                continue  # already reported as a missing price row
            got = row.get("com_TextID")
            if str(got if got is not None else "") != str(want if want is not None else ""):
                text_failures.append(f"tCOMd_GlobalPrice {row_id}: text link {got} != {want}")
            elif want is not None and want not in texts:
                text_failures.append(f"tCOMd_GlobalPrice {row_id}: text {want} does not exist (dangling)")
            else:
                link_ok[row_id] = True
        for text_id, want in created.items():
            row = texts.get(text_id)
            if row is None:
                text_failures.append(f"tCOMd_Text {text_id}: row missing after write")
                continue
            bad = [c for c in ("com_TextTypeCode", "com_TextName", *text_lang_cols)
                   if str(row.get(c) or "") != str(want.get(c) or "")]
            if str(row.get("com_PackageID")) != str(want["com_PackageID"]):
                bad.append("com_PackageID")
            if bad:
                text_failures.append(f"tCOMd_Text {text_id}: {', '.join(bad)} differ from intended")
            else:
                stats["texts_ok"].add(text_id)
        for row in rows_of("textdup"):
            if int(row.get("n") or 0) != 1:
                text_failures.append(f"tCOMd_Text '{row.get('com_TextName')}': {row.get('n')} duplicate texts")

        inserted_global_ids = {r["com_GlobalPriceID"] for r in global_rows}
        for entry in text_plan:
            ids = entry.get("row_ids") or []
            if entry["action"] == ACTION_REUSE and ids and all(link_ok.get(i) for i in ids):
                stats["reused_ok"] += 1
            if entry["action"] in (ACTION_REUSE, ACTION_CREATE, ACTION_LINK_NEW):
                stats["rows_linked_ok"] += sum(1 for i in ids if i in inserted_global_ids and link_ok.get(i))
            if entry["action"] == ACTION_PRESERVE and ids and all(link_ok.get(i) for i in ids):
                stats["preserved_ok"] += 1
        stats["failures"] = text_failures
        return failures + text_failures, stats
