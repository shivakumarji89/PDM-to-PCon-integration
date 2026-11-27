"""Incremental article-scoped Properties and Values export to a ProductStudio MDB.

Writes only tCOMd_Property and tCOMd_PropValue. Class IDs must already exist
(from Class Creation); Article and CodeScheme IDs are never modified. Text and
relation-object references are reused when present and otherwise remain NULL
for their respective workflows.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from models.mdb_export_session import MdbExportSession
from models.snapshot import Snapshot
from services.relation_link_policy import legacy_session_error
from services.base_service import BaseService
from services.class_creation_selection_service import (
    build_class_creation_scope,
    classes_for_article,
)
from services.engineering.engineering_text_service import text_block_name


class PropertiesValuesMdbExportService(BaseService):
    WORKFLOW = "properties_values"

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

    @staticmethod
    def _allowed_value_ids(scope, source_id: str):
        """Value ids an in-scope property/option may export; ``None`` = not a scoped source.

        A property/option that IS in scope but has no value mapping exports zero values - the
        missing mapping must never widen to every PDM value.
        """
        if source_id in scope.property_ids:
            return scope.property_value_ids.get(source_id, frozenset())
        if source_id in scope.option_ids:
            return scope.option_value_ids.get(source_id, frozenset())
        return None

    @staticmethod
    def _assignment_union(snapshot: Snapshot, classes: list, selected_ids: set[str], base_of=None):
        """Union selected articles' class assignments without mutating source classes."""
        by_name: dict[str, dict[str, Any]] = {}
        for article_id in sorted(selected_ids):
            for cls in classes_for_article(snapshot, classes, article_id, base_of=base_of):
                name = str(getattr(cls, "name", "") or "").strip()
                if not name:
                    continue
                target = by_name.setdefault(name, {})
                for assignment in getattr(cls, "properties", []) or []:
                    pid = str(getattr(assignment, "property_id", "") or "")
                    if not pid:
                        continue
                    old = target.get(pid)
                    if old is None:
                        target[pid] = assignment
                    else:
                        # Same class/property can be reached through multiple
                        # selected articles. Merge its class values by value ID/code.
                        values = list(getattr(old, "values", []) or [])
                        seen = {
                            (str(getattr(v, "value_id", "") or ""),
                             str(getattr(v, "code", "") or "").strip())
                            for v in values
                        }
                        for value in getattr(assignment, "values", []) or []:
                            key = (str(getattr(value, "value_id", "") or ""),
                                   str(getattr(value, "code", "") or "").strip())
                            if key not in seen:
                                values.append(value)
                                seen.add(key)
                        try:
                            import copy
                            merged = copy.copy(old)
                            merged.values = values
                            target[pid] = merged
                        except Exception:
                            pass
        return by_name

    def export_to_session(
        self,
        snapshot: Snapshot,
        session: MdbExportSession,
        selected_article_ids: set[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        if snapshot is None or snapshot.product is None:
            return {"ok": False, "error": "Load a product before exporting Properties and Values."}
        legacy = legacy_session_error(session)
        if legacy:
            return {"ok": False, "error": legacy, "legacy_session": True}
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
        # Canonical base of every article from the context-aware resolver (price tier
        # included), resolved once and handed to the class selection below.
        base_of = {str(_aid): str(_base or "") for _aid, _base in entries}
        selected_entries = [
            (str(article_id), str(base_code))
            for article_id, base_code in entries
            if str(article_id) in selected and str(base_code or "")
        ]
        found = {article_id for article_id, _ in selected_entries}
        unknown = sorted(selected - found)
        if unknown:
            return {"ok": False, "error": (
                "Some selected articles have no generated base article: "
                + ", ".join(unknown[:10])
                + ". Check their base-length / reduction mapping first."
            )}
        selected_base_codes = list(dict.fromkeys(base for _, base in selected_entries))
        article_map = session.article_ids()
        missing_articles = [code for code in selected_base_codes if code not in article_map]
        if missing_articles:
            return {"ok": False, "error": (
                "Export the selected Articles first. Missing base article(s): "
                + ", ".join(missing_articles[:10])
            )}

        classes = self.context.engineering_class_service.get_classes(snapshot)
        assignments_by_class = self._assignment_union(snapshot, classes, selected, base_of=base_of)
        if not assignments_by_class:
            return {"ok": False, "error": "No Class Creation properties are related to the selected article(s)."}

        scope = build_class_creation_scope(snapshot, selected)
        try:
            data = db.read_tables(session.mdb_path, {
                "package": (
                    "SELECT com_PackageID FROM tCOMd_Package "
                    f"WHERE com_PackageID = {int(package_id)}"
                ),
                "classes": "SELECT com_ClassID, com_ClassName, com_PackageID FROM tCOMd_Class",
                "articles": "SELECT com_ArticleID, com_ArticleCode, com_PackageID FROM tCOMd_Article",
                "properties": (
                    "SELECT com_PropertyID, com_ClassID, com_PropName "
                    "FROM tCOMd_Property"
                ),
                "values": (
                    "SELECT com_ValueID, com_PropertyID, com_PropValueFrom "
                    "FROM tCOMd_PropValue"
                ),
                "texts": (
                    "SELECT com_TextID, com_TextName, com_TextTypeCode, com_PackageID "
                    "FROM tCOMd_Text"
                ),
                "relobjs": (
                    "SELECT com_RelObjID, com_RelObjName, com_PackageID FROM tCOMd_RelObj"
                ),
            })
        except Exception as exc:
            return {"ok": False, "error": f"Could not read the session MDB: {exc}"}
        if not data["package"]:
            return {"ok": False, "error": f"Session MDB no longer contains package {package_id}."}
        package_articles = [row for row in data["articles"] if str(row.get("com_PackageID")) == str(package_id)]
        actual_article_keys = {(str(row.get("com_ArticleID")), self._key(row.get("com_ArticleCode"))) for row in package_articles}
        invalid_articles = [code for code in selected_base_codes if (str(article_map[code]), self._key(code)) not in actual_article_keys]
        if invalid_articles:
            return {"ok": False, "error": "Selected Articles no longer match the session MDB: " + ", ".join(invalid_articles[:10]) + ". Re-export Articles first."}

        package_classes = [
            row for row in data["classes"]
            if str(row.get("com_PackageID")) == str(package_id)
        ]
        class_by_name: dict[str, list[dict[str, Any]]] = {}
        for row in package_classes:
            class_by_name.setdefault(self._key(row.get("com_ClassName")), []).append(row)

        property_ids: dict[tuple[str, str], int] = {}
        package_properties = [
            row for row in data["properties"]
            if any(str(row.get("com_ClassID")) == str(c.get("com_ClassID")) for c in package_classes)
        ]
        for row in package_properties:
            key = (str(row.get("com_ClassID")), self._key(row.get("com_PropName")))
            if key in property_ids:
                return {"ok": False, "error": f"Duplicate MDB Property mapping for class/property {key}."}
            property_ids[key] = self._int(row.get("com_PropertyID"))

        text_by_key: dict[tuple[str, str], list[Any]] = {}
        for row in data["texts"]:
            if str(row.get("com_PackageID")) == str(package_id):
                key = (self._key(row.get("com_TextTypeCode")), self._key(row.get("com_TextName")))
                text_by_key.setdefault(key, []).append(row.get("com_TextID"))
        relobj_by_name: dict[str, list[Any]] = {}
        for row in data["relobjs"]:
            if str(row.get("com_PackageID")) == str(package_id):
                relobj_by_name.setdefault(self._key(row.get("com_RelObjName")), []).append(row.get("com_RelObjID"))

        next_property_id = self._next_id(data["properties"], "com_PropertyID")
        next_value_id = self._next_id(data["values"], "com_ValueID")
        property_inserts: list[dict[str, Any]] = []
        value_inserts: list[dict[str, Any]] = []
        warnings: list[str] = []
        properties_reused = 0
        value_keys = {
            (str(row.get("com_PropertyID")), self._key(row.get("com_PropValueFrom")))
            for row in data["values"]
        }

        prop_by_id = {str(p.id): p for p in (getattr(snapshot, "properties", []) or []) if getattr(p, "id", None) is not None}
        option_by_id = {str(o.id): o for o in (getattr(snapshot, "options", []) or []) if getattr(o, "id", None) is not None}
        code_map = xocd._value_code_map(snapshot)
        value_digits = xocd._value_lengths(snapshot)
        property_proto = dict(session.prototypes.get("tCOMd_Property", {}))
        value_proto = dict(session.prototypes.get("tCOMd_PropValue", {}))
        if not property_proto or not value_proto:
            return {"ok": False, "error": "The session is missing tCOMd_Property or tCOMd_PropValue template prototypes."}

        for class_name, by_property in assignments_by_class.items():
            class_matches = class_by_name.get(self._key(class_name), [])
            if len(class_matches) != 1:
                return {"ok": False, "error": (
                    f"Expected one existing Class '{class_name}' in the session MDB. "
                    "Run Class Creation first or repair duplicate class rows."
                )}
            class_id = self._int(class_matches[0].get("com_ClassID"))
            for source_id, assignment in by_property.items():
                source_prop = prop_by_id.get(source_id)
                source_option = option_by_id.get(source_id)
                source_name = (
                    str(getattr(assignment, "property_name", "") or "")
                    or str(getattr(source_prop or source_option, "name", "") or "")
                )
                if not source_name:
                    warnings.append(f"Skipped unnamed property ID {source_id} in class '{class_name}'.")
                    continue
                prop_name = xocd._prop_ident(source_name)
                text_name = str(getattr(assignment, "text_block", "") or text_block_name(source_name))
                if not prop_name:
                    warnings.append(f"Skipped property '{source_name}' because its normalized name is empty.")
                    continue
                natural_key = (str(class_id), self._key(prop_name))
                existing_property_id = property_ids.get(natural_key)
                if existing_property_id is None:
                    property_id = next_property_id
                    next_property_id += 1
                    usage = str(getattr(assignment, "usage", "") or "")
                    ptype = (str(getattr(assignment, "type", "") or
                                 getattr(source_prop, "data_type", "") or "C").strip().upper()[:1] or "C")
                    text_matches = (
                        text_by_key.get(("property", self._key(text_name)), [])
                        or text_by_key.get(("option", self._key(text_name)), [])
                    )
                    text_id = text_matches[0] if len(text_matches) == 1 else None
                    relation_name = str(getattr(assignment, "relation_object", "") or "")
                    relation_matches = relobj_by_name.get(self._key(relation_name), []) if relation_name else []
                    relobj_id = relation_matches[0] if len(relation_matches) == 1 else None
                    if relation_name and len(relation_matches) > 1:
                        warnings.append(f"Relation Object '{relation_name}' is ambiguous; property link left empty.")
                    # com_PropInfoPicPrefix is a REQUIRED text column in the real OCD schema: it must be a
                    # string (empty when no @PropInfoPicPrefix applies), never NULL - exactly what the full
                    # export writes, including for properties that originate from an option.
                    try:
                        prop_info_prefix = self.context.material_picking_service.prop_info_pic_prefix(
                            snapshot, source_name, str(getattr(source_prop, "code", "") or "")
                        )
                    except Exception:
                        prop_info_prefix = ""
                    prop_info_prefix = "" if prop_info_prefix is None else str(prop_info_prefix)
                    property_inserts.append({
                        "op": "insert", "table": "tCOMd_Property", "rows": [{
                            "com_PropertyID": property_id, **property_proto,
                            "com_ClassID": class_id, "com_PropName": prop_name,
                            "com_PropTypeCode": ptype,
                            "com_PropScopeCode": "RG" if usage.lower().startswith("g") else "C",
                            "com_PropPosition": 100 + max(0, self._int(getattr(assignment, "placement", 0))) * 10,
                            "com_TextID": text_id, "com_RelObjID": relobj_id,
                            "com_HintTextID": None,
                            "com_PropDigits": value_digits.get(source_id, 0) or max(1, len(prop_name)),
                            "com_PropDecDigits": 0,
                            "com_PropInfoPicPrefix": prop_info_prefix,
                        }]})
                    property_ids[natural_key] = property_id
                else:
                    property_id = existing_property_id
                    properties_reused += 1

                # ClassValue is the authoritative code->value list for this
                # assignment. Scope it to values carried by selected articles.
                class_values = list(getattr(assignment, "values", []) or [])
                if not class_values:
                    if source_prop is not None:
                        source_values = list(getattr(source_prop, "values", []) or []) or [
                            value for value in (getattr(snapshot, "property_values", []) or [])
                            if str(getattr(value, "property_id", "") or "") == source_id
                        ]
                    elif source_option is not None:
                        source_values = list(getattr(source_option, "values", []) or []) or [
                            value for value in (getattr(snapshot, "option_values", []) or [])
                            if str(getattr(value, "option_id", "") or "") == source_id
                        ]
                    else:
                        source_values = []
                    class_values = [
                        type("ExportValue", (), {
                            "value_id": str(getattr(value, "id", "") or ""),
                            "code": str(getattr(value, "code", "") or code_map.get(str(getattr(value, "id", "") or ""), "")),
                            "value": str(getattr(value, "value", "") or ""),
                        })()
                        for value in source_values
                    ]
                allowed_ids = self._allowed_value_ids(scope, source_id)
                if allowed_ids is not None:
                    class_values = [
                        value for value in class_values
                        if str(getattr(value, "value_id", "") or "") in allowed_ids
                    ]
                seen_codes: set[str] = set()
                position = 0
                for value in class_values:
                    code = str(getattr(value, "code", "") or "").strip()
                    value_id = str(getattr(value, "value_id", "") or "")
                    if not code and value_id:
                        code = str(code_map.get(value_id, "") or "").strip()
                    if not code or self._key(code) in seen_codes:
                        continue
                    seen_codes.add(self._key(code))
                    key = (str(property_id), self._key(code))
                    if key not in value_keys:
                        value_text_name = f"{text_block_name(source_name)}_{code}"
                        value_text_matches = (
                            text_by_key.get(("propvalue", self._key(value_text_name)), [])
                            or text_by_key.get(("optionvalue", self._key(value_text_name)), [])
                        )
                        text_id = value_text_matches[0] if len(value_text_matches) == 1 else None
                        value_inserts.append({
                            "op": "insert", "table": "tCOMd_PropValue", "rows": [{
                                "com_ValueID": next_value_id, **value_proto,
                                "com_PropertyID": property_id,
                                "com_PropValPosition": 100 + position * 10,
                                "com_PropValOpCodeFrom": "EQ",
                                "com_PropValueFrom": code,
                                "com_TextID": text_id,
                                "com_RelObjID": None,
                                "com_PropValIsDefault": False,
                            }]})
                        value_keys.add(key)
                        next_value_id += 1
                    position += 1

        plan = property_inserts + value_inserts
        counts = {
            "selected_articles": len(selected),
            "base_articles": len(selected_base_codes),
            "properties_inserted": len(property_inserts),
            "properties_reused": properties_reused,
            "values_inserted": len(value_inserts),
        }
        result = {
            "ok": True, "dry_run": dry_run, "mdb_path": session.mdb_path,
            "counts": counts, "warnings": warnings, "operations": len(plan),
        }
        if dry_run:
            return result
        if not plan:
            sessions.record_workflow(session, self.WORKFLOW, counts)
            try:
                sessions.save(session)
            except OSError as exc:
                return {**result, "ok": False, "error": f"Could not save Properties and Values workflow status: {exc}"}
            result["verified"] = True
            return result

        batch = db.execute_batch(session.mdb_path, plan, transaction=True)
        if not batch.ok:
            return {**result, "ok": False, "error": batch.first_error() or "Properties and Values MDB transaction failed."}
        try:
            verified = db.read_tables(session.mdb_path, {
                "properties": "SELECT com_PropertyID FROM tCOMd_Property",
                "values": "SELECT com_ValueID FROM tCOMd_PropValue",
            })
        except Exception as exc:
            return {**result, "ok": False, "error": f"Properties and Values wrote data but read-back failed: {exc}"}
        expected_properties = len(data["properties"]) + len(property_inserts)
        expected_values = len(data["values"]) + len(value_inserts)
        if (len(verified["properties"]) < expected_properties
                or len(verified["values"]) < expected_values):
            return {**result, "ok": False, "error": (
                "Properties and Values read-back validation failed: "
                f"properties {len(verified['properties'])}/{expected_properties}, "
                f"values {len(verified['values'])}/{expected_values}."
            )}
        sessions.record_workflow(session, self.WORKFLOW, counts)
        try:
            sessions.save(session)
        except OSError as exc:
            return {**result, "ok": False, "error": f"Properties and Values were written but session save failed: {exc}"}
        result["verified"] = True
        return result
