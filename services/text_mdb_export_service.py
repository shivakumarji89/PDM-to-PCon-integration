"""Incremental, selected-article Text export into a ProductStudio MDB session.

Text rows are keyed by (type, name). Existing TextIDs are retained; changed
translations are updated in place and missing blocks are inserted. Article,
Property and PropValue text references are linked only where their target rows
already exist. Price text remains owned by PriceMdbExportService.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from models.mdb_export_session import MdbExportSession
from models.snapshot import Snapshot
from services.base_service import BaseService
from services.class_creation_selection_service import build_class_creation_scope
from services.engineering.engineering_text_service import text_block_name
from services.ocd_export_service import _TEXT_TYPE_OCD


class TextMdbExportService(BaseService):
    WORKFLOW = "text"

    @staticmethod
    def _key(value: Any) -> str:
        return str(value or "").strip().casefold()

    @staticmethod
    def _int(value: Any) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    @classmethod
    def _next_id(cls, rows: list[dict[str, Any]], column: str) -> int:
        return max((cls._int(row.get(column)) for row in rows), default=0) + 1

    def export_to_session(
        self, snapshot: Snapshot, session: MdbExportSession,
        selected_article_ids: set[str] | None = None, dry_run: bool = False,
    ) -> dict[str, Any]:
        if snapshot is None or snapshot.product is None:
            return {"ok": False, "error": "Load a product before exporting Text."}
        selected = {str(v) for v in (selected_article_ids or set()) if str(v)}
        if not selected:
            return {"ok": False, "error": "Select one or more articles in the Articles page Export column first."}
        sessions = self.context.mdb_export_session_service
        try:
            if sessions.product_key(snapshot) != session.product_key:
                return {"ok": False, "error": "The export session belongs to a different product."}
            if not Path(session.mdb_path).is_file():
                return {"ok": False, "error": f"The session MDB does not exist: {session.mdb_path}"}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        db = self.context.mdb_service
        if not db.is_available():
            return {"ok": False, "error": "32-bit PowerShell / ACE bridge unavailable."}
        package_id = session.package_id
        if package_id in (None, ""):
            return {"ok": False, "error": "The export session has no package ID."}

        xocd = self.context.xocd_export_service
        entries = xocd.base_code_entries(snapshot)
        selected_entries = [(str(aid), str(code)) for aid, code in entries
                            if str(aid) in selected and str(code or "").strip()]
        found = {aid for aid, _ in selected_entries}
        unknown = sorted(selected - found)
        if unknown:
            return {"ok": False, "error": "Selected articles have no generated base article: " + ", ".join(unknown[:10])}
        base_codes = list(dict.fromkeys(code for _, code in selected_entries))
        missing = [code for code in base_codes if code not in session.article_ids()]
        if missing:
            return {"ok": False, "error": "Export Articles first. Missing base article(s): " + ", ".join(missing[:10])}

        scope = build_class_creation_scope(snapshot, selected)
        blocks = self.context.engineering_text_service.ensure_text_blocks(snapshot)
        selected_names: set[tuple[str, str]] = set()
        # Article descriptions are keyed by the base article code.
        for code in base_codes:
            selected_names.add(("artshort", self._key(code)))
            selected_names.add(("artlong", self._key(code)))
        # Property and option text is restricted to the selected article scope.
        prop_by_id = {str(p.id): p for p in snapshot.properties if getattr(p, "id", None) is not None}
        option_by_id = {str(o.id): o for o in snapshot.options if getattr(o, "id", None) is not None}
        value_code_map = xocd._value_code_map(snapshot)
        for prop_id in scope.property_ids:
            prop = prop_by_id.get(str(prop_id))
            if prop is None:
                continue
            key = text_block_name(prop.name)
            selected_names.add(("property", self._key(key)))
            for value in getattr(prop, "values", []) or []:
                value_id = str(getattr(value, "id", "") or "")
                allowed = scope.property_value_ids.get(str(prop_id))
                if allowed is not None and value_id not in allowed:
                    continue
                code = (str(getattr(value, "code", "") or "").strip()
                        or str(value_code_map.get(value_id, "") or "")).replace("#", "")
                if code:
                    selected_names.add(("propvalue", self._key(f"{key}_{code}")))
        for option_id in scope.option_ids:
            option = option_by_id.get(str(option_id))
            if option is None:
                continue
            key = text_block_name(option.name)
            selected_names.add(("option", self._key(key)))
            for value in getattr(option, "values", []) or []:
                value_id = str(getattr(value, "id", "") or "")
                allowed = scope.option_value_ids.get(str(option_id))
                if allowed is not None and value_id not in allowed:
                    continue
                code = str(getattr(value, "code", "") or "").strip().replace("#", "")
                if code:
                    selected_names.add(("optionvalue", self._key(f"{key}_{code}")))

        chosen = [b for b in blocks
                  if (self._key(b.type_code), self._key(b.name)) in selected_names]
        if not chosen:
            return {"ok": False, "error": "No Text blocks are related to the selected articles."}

        proto = dict(session.prototypes.get("tCOMd_Text", {}))
        if not proto:
            return {"ok": False, "error": "The session is missing the tCOMd_Text template prototype."}
        language_columns = {
            str(col)[len("com_Text_1_"):].strip().lower(): str(col)
            for col in proto if str(col).lower().startswith("com_text_1_")
        }
        if not language_columns:
            return {"ok": False, "error": "The session MDB has no supported tCOMd_Text language columns."}
        text_columns = [
            "com_TextID", "com_TextName", "com_TextTypeCode", "com_PackageID",
            *dict.fromkeys(language_columns.values()),
        ]
        try:
            data = db.read_tables(session.mdb_path, {
                "package": f"SELECT com_PackageID FROM tCOMd_Package WHERE com_PackageID = {int(package_id)}",
                "texts": (
                    "SELECT " + ", ".join(text_columns)
                    + f" FROM tCOMd_Text WHERE com_PackageID = {int(package_id)}"
                ),
                "text_max": "SELECT MAX(com_TextID) AS max_id FROM tCOMd_Text",
                "articles": (
                    "SELECT com_ArticleID, com_ArticleCode, com_PackageID, "
                    "com_ShortTextID, com_LongTextID FROM tCOMd_Article "
                    f"WHERE com_PackageID = {int(package_id)}"
                ),
                "classes": (
                    "SELECT com_ClassID, com_ClassName FROM tCOMd_Class "
                    f"WHERE com_PackageID = {int(package_id)}"
                ),
                "properties": (
                    "SELECT com_PropertyID, com_ClassID, com_PropName, com_TextID "
                    "FROM tCOMd_Property"
                ),
                "values": (
                    "SELECT com_ValueID, com_PropertyID, com_PropValueFrom, com_TextID "
                    "FROM tCOMd_PropValue"
                ),
            })
        except Exception as exc:
            return {"ok": False, "error": f"Could not read the session MDB: {exc}"}
        if not data["package"]:
            return {"ok": False, "error": f"Session MDB no longer contains package {package_id}."}
        existing: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in data["texts"]:
            if str(row.get("com_PackageID")) != str(package_id):
                continue
            key = (self._key(row.get("com_TextTypeCode")), self._key(row.get("com_TextName")))
            existing.setdefault(key, []).append(row)
        next_id = max(self._next_id(data["texts"], "com_TextID"),\n                       self._int((data.get("text_max") or [{}])[0].get("max_id")) + 1)
        inserts: list[dict[str, Any]] = []
        updates: list[dict[str, Any]] = []
        text_id_by_key: dict[tuple[str, str], Any] = {}
        for block in chosen:
            type_code = _TEXT_TYPE_OCD.get(block.type_code, block.type_code)
            key = (self._key(type_code), self._key(block.name))
            matches = existing.get(key, [])
            if len(matches) > 1:
                return {"ok": False, "error": f"Duplicate MDB Text key: {type_code}/{block.name}."}
            values = {"com_TextName": block.name, "com_TextTypeCode": type_code,
                      "com_PackageID": package_id}
            for language, column in language_columns.items():
                values[column] = block.get_language(language) or None
            if matches:
                row = matches[0]
                text_id = row.get("com_TextID")
                text_id_by_key[(self._key(block.type_code), self._key(block.name))] = text_id
                changed = {col: val for col, val in values.items()
                           if col in row and str(row.get(col) or "") != str(val or "")}
                if changed:
                    updates.append({"op": "update", "table": "tCOMd_Text",
                                    "set": changed, "where": {"com_TextID": text_id}})
            else:
                text_id = next_id
                next_id += 1
                text_id_by_key[(self._key(block.type_code), self._key(block.name))] = text_id
                inserts.append({"op": "insert", "table": "tCOMd_Text",
                                "rows": [{"com_TextID": text_id, **proto, **values}]})

        # Link property and value text references through the selected
        # class/property natural keys; source IDs are not MDB surrogate IDs.
        classes = self.context.engineering_class_service.get_classes(snapshot)
        assignments_by_class: dict[str, dict[str, Any]] = {}
        for article_id in selected:
            for cls in __import__(
                "services.class_creation_selection_service",
                fromlist=["classes_for_article"],
            ).classes_for_article(snapshot, classes, article_id):
                bucket = assignments_by_class.setdefault(str(cls.name), {})
                for assignment in getattr(cls, "properties", []) or []:
                    bucket[str(getattr(assignment, "property_id", "") or "")] = assignment
        class_id_by_name = {
            self._key(row.get("com_ClassName")): row.get("com_ClassID")
            for row in data["classes"]
        }
        property_updates = []
        value_updates = []
        for class_name, assignments in assignments_by_class.items():
            class_id = class_id_by_name.get(self._key(class_name))
            if class_id is None:
                continue
            for source_id, assignment in assignments.items():
                source_prop = prop_by_id.get(source_id) or option_by_id.get(source_id)
                source_name = str(getattr(assignment, "property_name", "") or
                                   getattr(source_prop, "name", "") or "")
                if not source_name:
                    continue
                prop_name = self._key(xocd._prop_ident(source_name))
                prop_rows = [
                    row for row in data["properties"]
                    if str(row.get("com_ClassID")) == str(class_id)
                    and self._key(row.get("com_PropName")) == prop_name
                ]
                if len(prop_rows) != 1:
                    continue
                mdb_prop = prop_rows[0]
                text_name = self._key(str(getattr(assignment, "text_block", "") or text_block_name(source_name)))
                property_text_id = (
                    text_id_by_key.get(("property", text_name))
                    or text_id_by_key.get(("option", text_name))
                )
                if property_text_id is not None and str(mdb_prop.get("com_TextID") or "") != str(property_text_id):
                    property_updates.append({"op": "update", "table": "tCOMd_Property",
                                             "set": {"com_TextID": property_text_id},
                                             "where": {"com_PropertyID": mdb_prop.get("com_PropertyID")}})
                source_values = list(getattr(assignment, "values", []) or [])
                if not source_values and source_prop is not None:
                    source_values = list(getattr(source_prop, "values", []) or [])
                for source_value in source_values:
                    value_id = str(getattr(source_value, "value_id", "") or getattr(source_value, "id", "") or "")
                    allowed = (
                        scope.property_value_ids.get(source_id)
                        if source_id in scope.property_ids
                        else scope.option_value_ids.get(source_id)
                    )
                    if allowed is not None and value_id not in allowed:
                        continue
                    code = str(getattr(source_value, "code", "") or value_code_map.get(value_id, "")).strip().replace("#", "")
                    if not code:
                        continue
                    value_text_name = self._key(f"{text_block_name(source_name)}_{code}")
                    value_text_id = (
                        text_id_by_key.get(("propvalue", value_text_name))
                        or text_id_by_key.get(("optionvalue", value_text_name))
                    )
                    if value_text_id is None:
                        continue
                    value_rows = [
                        row for row in data["values"]
                        if str(row.get("com_PropertyID")) == str(mdb_prop.get("com_PropertyID"))
                        and self._key(row.get("com_PropValueFrom")) == self._key(code)
                    ]
                    if len(value_rows) == 1 and str(value_rows[0].get("com_TextID") or "") != str(value_text_id):
                        value_updates.append({"op": "update", "table": "tCOMd_PropValue",
                                              "set": {"com_TextID": value_text_id},
                                              "where": {"com_ValueID": value_rows[0].get("com_ValueID")}})

        # Link article short/long text references without changing article IDs.
        article_rows = [r for r in data["articles"]
                        if str(r.get("com_PackageID")) == str(package_id)
                        and self._key(r.get("com_ArticleCode")) in {self._key(c) for c in base_codes}]
        article_by_code = {self._key(r.get("com_ArticleCode")): r for r in article_rows}
        article_updates = []
        for code in base_codes:
            row = article_by_code.get(self._key(code))
            if row is None:
                return {"ok": False, "error": f"Base article '{code}' is missing from the session MDB."}
            aid = session.article_ids()[code]
            if str(row.get("com_ArticleID")) != str(aid):
                return {"ok": False, "error": f"Article ID mismatch for '{code}' in the session MDB."}
            short_id = text_id_by_key.get(("artshort", self._key(code)))
            long_id = text_id_by_key.get(("artlong", self._key(code)))
            set_values = {}
            if short_id is not None and str(row.get("com_ShortTextID") or "") != str(short_id):
                set_values["com_ShortTextID"] = short_id
            if long_id is not None and str(row.get("com_LongTextID") or "") != str(long_id):
                set_values["com_LongTextID"] = long_id
            if set_values:
                article_updates.append({"op": "update", "table": "tCOMd_Article",
                                        "set": set_values, "where": {"com_ArticleID": aid}})

        plan = inserts + updates + property_updates + value_updates + article_updates
        counts = {"selected_articles": len(selected), "base_articles": len(base_codes),
                  "text_blocks_selected": len(chosen), "texts_inserted": len(inserts),
                  "texts_updated": len(updates), "properties_linked": len(property_updates),\n                  "values_linked": len(value_updates), "articles_linked": len(article_updates)}
        result = {"ok": True, "dry_run": dry_run, "mdb_path": session.mdb_path,
                  "counts": counts, "operations": len(plan)}
        if dry_run:
            return result
        if not plan:
            sessions.record_workflow(session, self.WORKFLOW, counts)
            sessions.save(session)
            result["verified"] = True
            return result
        batch = db.execute_batch(session.mdb_path, plan, transaction=True)
        if not batch.ok:
            return {**result, "ok": False, "error": batch.first_error() or "Text MDB transaction failed."}
        try:
            verified = db.read_tables(session.mdb_path, {
                "texts": "SELECT com_TextID, com_TextName, com_TextTypeCode, com_PackageID FROM tCOMd_Text",
                "articles": "SELECT com_ArticleID, com_ShortTextID, com_LongTextID FROM tCOMd_Article",\n                "properties": "SELECT com_PropertyID, com_TextID FROM tCOMd_Property",\n                "values": "SELECT com_ValueID, com_TextID FROM tCOMd_PropValue",
            })
        except Exception as exc:
            return {**result, "ok": False, "error": f"Text was written but read-back failed: {exc}"}
        if len(verified["texts"]) < len(data["texts"]) + len(inserts):
            return {**result, "ok": False, "error": "Text read-back count verification failed."}
        sessions.record_workflow(session, self.WORKFLOW, counts)
        try:
            sessions.save(session)
        except OSError as exc:
            return {**result, "ok": False, "error": f"Text was written but workflow status could not be saved: {exc}"}
        result["verified"] = True
        return result
