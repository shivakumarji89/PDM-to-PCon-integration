"""Incremental Class Creation export into a ProductStudio session MDB.

The Development/full OCD builder remains the mapping authority. This service
writes only class-owned tables and extends the mandatory code schemes created
by the Articles workflow. Existing MDB primary keys and unrelated rows are
preserved; all writes use MDBService transactions.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from models.mdb_export_session import MdbExportSession
from models.snapshot import Snapshot
from services.base_service import BaseService
from services.engineering.engineering_reduction_service import collapse_duplicate_values
from services.engineering.engineering_text_service import text_block_name
from services.ocd_export_service import OcdExportService
from services.xocd_export_service import XocdExportService


class ClassCreationMdbExportService(BaseService):
    WORKFLOW = "class_creation"

    @staticmethod
    def _key(value: Any) -> str:
        return str(value or "").strip().casefold()

    @staticmethod
    def _int(value: Any) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _next_id(rows: list[dict[str, Any]], column: str) -> int:
        return max((ClassCreationMdbExportService._int(r.get(column)) for r in rows), default=0) + 1

    def export_to_session(
        self, snapshot: Snapshot, session: MdbExportSession, dry_run: bool = False,
    ) -> dict[str, Any]:
        """Export all Development engineering classes into the existing product MDB."""
        if snapshot is None or snapshot.product is None:
            return {"ok": False, "error": "Load a product before exporting Class Creation."}
        if not session.article_ids():
            return {"ok": False, "error": "Export Articles first so Class Creation can link to retained article IDs."}
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

        ocd = self.context.ocd_export_service
        xocd = self.context.xocd_export_service
        classes = self.context.engineering_class_service.get_classes(snapshot)
        if not classes:
            return {"ok": False, "error": "No engineering classes are available to export."}
        article_ids = session.article_ids()
        base_codes = list(article_ids)
        codes = xocd._value_code_map(snapshot)
        digits = xocd._value_lengths(snapshot)

        try:
            data = db.read_tables(session.mdb_path, {
                "package": f"SELECT com_PackageID FROM tCOMd_Package WHERE com_PackageID = {int(package_id)}",
                "classes": "SELECT * FROM tCOMd_Class",
                "properties": "SELECT * FROM tCOMd_Property",
                "values": "SELECT * FROM tCOMd_PropValue",
                "schemes": "SELECT * FROM tCOMd_CodeScheme",
                "articles": "SELECT com_ArticleID, com_ArticleCode, com_PackageID FROM tCOMd_Article",
                "article_classes": "SELECT * FROM tCOMd_ArticleClass",
                "artbase": "SELECT * FROM tCOMd_ArtBase",
                "texts": "SELECT com_TextID, com_TextName, com_TextTypeCode, com_PackageID FROM tCOMd_Text",
                "relobjs": "SELECT com_RelObjID, com_RelObjName, com_PackageID FROM tCOMd_RelObj",
            })
        except Exception as exc:
            return {"ok": False, "error": f"Could not read the session MDB: {exc}"}
        if not data["package"]:
            return {"ok": False, "error": f"Session MDB no longer contains package {package_id}."}

        for table in ("tCOMd_Class", "tCOMd_Property", "tCOMd_PropValue",
                      "tCOMd_CodeScheme", "tCOMd_ArticleClass", "tCOMd_ArtBase"):
            if table not in session.prototypes:
                return {"ok": False, "error": f"Session has no template prototype for {table}; no data was written."}

        # Restrict every lookup to this product package.
        package_rows = {
            "classes": [r for r in data["classes"] if str(r.get("com_PackageID")) == str(package_id)],
            "schemes": [r for r in data["schemes"] if str(r.get("com_PackageID")) == str(package_id)],
            "articles": [r for r in data["articles"] if str(r.get("com_PackageID")) == str(package_id)],
            "texts": [r for r in data["texts"] if str(r.get("com_PackageID")) == str(package_id)],
            "relobjs": [r for r in data["relobjs"] if str(r.get("com_PackageID")) == str(package_id)],
        }
        existing_classes = package_rows["classes"]
        existing_properties = data["properties"]
        existing_values = data["values"]
        existing_schemes = package_rows["schemes"]
        existing_article_classes = data["article_classes"]
        existing_artbase = data["artbase"]

        class_by_name: dict[str, list[dict[str, Any]]] = {}
        for row in existing_classes:
            class_by_name.setdefault(self._key(row.get("com_ClassName")), []).append(row)
        class_ids: dict[str, int] = {}
        class_inserts: list[dict[str, Any]] = []
        class_updates: list[dict[str, Any]] = []
        next_class = self._next_id(data["classes"], "com_ClassID")
        warnings: list[str] = []
        for cls in classes:
            matches = class_by_name.get(self._key(cls.name), [])
            if len(matches) > 1:
                warnings.append(f"Class '{cls.name}' is duplicated in the MDB; skipped rather than guessing.")
                continue
            if matches:
                row_id = self._int(matches[0].get("com_ClassID"))
                class_ids[str(cls.id)] = row_id
                if matches[0].get("com_PackageID") != package_id:
                    class_updates.append({"op": "update", "table": "tCOMd_Class",
                        "set": {"com_PackageID": package_id}, "where": {"com_ClassID": row_id}})
            else:
                row_id = next_class
                next_class += 1
                class_ids[str(cls.id)] = row_id
                class_inserts.append({"op": "insert", "table": "tCOMd_Class", "rows": [{
                    "com_ClassID": row_id, **session.prototypes["tCOMd_Class"],
                    "com_ClassName": cls.name, "com_PackageID": package_id,
                }]})

        text_index: dict[tuple[str, str], list[Any]] = {}
        for row in package_rows["texts"]:
            text_index.setdefault((self._key(row.get("com_TextTypeCode")),
                                   self._key(row.get("com_TextName"))), []).append(row.get("com_TextID"))
        relobj_index: dict[str, list[Any]] = {}
        for row in package_rows["relobjs"]:
            relobj_index.setdefault(self._key(row.get("com_RelObjName")), []).append(row.get("com_RelObjID"))

        relation_objects = self.context.engineering_relation_service.ensure_relation_objects(snapshot)
        property_relobj: dict[str, Any] = {}
        value_relobj: dict[str, Any] = {}
        for rel in relation_objects:
            raw_id = getattr(rel, "rel_obj_id", None)
            rel_id = self._int(raw_id)
            if not rel_id:
                matches = relobj_index.get(self._key(getattr(rel, "name", "")), [])
                rel_id = self._int(matches[0]) if len(matches) == 1 else 0
            if not rel_id:
                continue
            for prop_id in getattr(rel, "property_ids", []) or []:
                property_relobj.setdefault(str(prop_id), rel_id)
            for value_id in getattr(rel, "value_ids", []) or []:
                value_relobj.setdefault(str(value_id), rel_id)
            prop_id = str(getattr(rel, "property_id", "") or "")
            if prop_id:
                property_relobj.setdefault(prop_id, rel_id)
            value_id = str(getattr(rel, "value_id", "") or "")
            if value_id:
                value_relobj.setdefault(value_id, rel_id)

        property_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in existing_properties:
            property_by_key.setdefault((str(row.get("com_ClassID")), self._key(row.get("com_PropName"))), []).append(row)
        next_property = self._next_id(existing_properties, "com_PropertyID")
        property_ids: dict[tuple[str, str], int] = {}
        property_inserts: list[dict[str, Any]] = []
        property_updates: list[dict[str, Any]] = []
        prop_meta: dict[str, tuple[str, str]] = {}
        source_properties = {str(p.id): p for p in (snapshot.properties or [])}
        for cls in classes:
            class_pk = class_ids.get(str(cls.id))
            if class_pk is None:
                continue
            for position, assignment in enumerate(cls.properties):
                prop_name = XocdExportService._prop_ident(assignment.property_name)
                key = (str(class_pk), self._key(prop_name))
                matches = property_by_key.get(key, [])
                if len(matches) > 1:
                    warnings.append(f"Property '{cls.name}:{prop_name}' is duplicated in the MDB; skipped.")
                    continue
                source_prop = source_properties.get(str(assignment.property_id))
                prefix = self.context.material_picking_service.prop_info_pic_prefix(
                    snapshot, assignment.property_name,
                    str(getattr(source_prop, "code", "") or ""),
                )
                text_name = assignment.text_block or text_block_name(assignment.property_name)
                text_matches = (text_index.get(("property", self._key(text_name)), [])
                                or text_index.get(("option", self._key(text_name)), []))
                text_id = text_matches[0] if len(text_matches) == 1 else None
                computed = {
                    "com_ClassID": class_pk, "com_PropName": prop_name,
                    "com_PropTypeCode": (assignment.type or "C")[:1] or "C",
                    "com_PropScopeCode": "RG" if (assignment.usage or "").lower().startswith("g") else "C",
                    "com_PropPosition": 100 + position * 10,
                    "com_TextID": text_id,
                    "com_RelObjID": property_relobj.get(str(assignment.property_id)),
                    "com_HintTextID": None,
                    "com_PropDigits": digits.get(assignment.property_id, 0) or len(prop_name),
                    "com_PropDecDigits": 0,
                    "com_PropInfoPicPrefix": prefix,
                }
                if matches:
                    row_id = self._int(matches[0].get("com_PropertyID"))
                    property_ids[(str(cls.id), str(assignment.property_id))] = row_id
                    if any(matches[0].get(k) != v for k, v in computed.items()):
                        property_updates.append({"op": "update", "table": "tCOMd_Property",
                            "set": computed, "where": {"com_PropertyID": row_id}})
                else:
                    row_id = next_property
                    next_property += 1
                    property_ids[(str(cls.id), str(assignment.property_id))] = row_id
                    property_inserts.append({"op": "insert", "table": "tCOMd_Property", "rows": [{
                        "com_PropertyID": row_id, **session.prototypes["tCOMd_Property"], **computed,
                    }]})
                prop_meta[str(assignment.property_id)] = (cls.name, prop_name)

        values_by: dict[str, list[Any]] = {}
        for value in snapshot.property_values or []:
            values_by.setdefault(str(value.property_id), []).append(value)
        for value in snapshot.option_values or []:
            values_by.setdefault(str(value.option_id), []).append(value)
        value_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in existing_values:
            value_by_key.setdefault((str(row.get("com_PropertyID")), self._key(row.get("com_PropValueFrom"))), []).append(row)
        next_value = self._next_id(existing_values, "com_ValueID")
        value_inserts: list[dict[str, Any]] = []
        value_updates: list[dict[str, Any]] = []
        for cls in classes:
            for assignment in cls.properties:
                prop_pk = property_ids.get((str(cls.id), str(assignment.property_id)))
                if prop_pk is None or (assignment.type or "").strip().upper().startswith("T"):
                    continue
                values = collapse_duplicate_values(
                    values_by.get(str(assignment.property_id), []),
                    lambda value: codes.get(str(value.id), ""),
                )
                seen: set[str] = set()
                position = 0
                for value in values:
                    code = codes.get(str(value.id), "")
                    if not code or code in seen:
                        continue
                    seen.add(code)
                    text_name = f"{text_block_name(assignment.property_name)}_{code}"
                    text_matches = (text_index.get(("propvalue", self._key(text_name)), [])
                                    or text_index.get(("optionvalue", self._key(text_name)), []))
                    text_id = text_matches[0] if len(text_matches) == 1 else None
                    computed = {
                        "com_PropertyID": prop_pk,
                        "com_PropValPosition": 100 + position * 10,
                        "com_PropValOpCodeFrom": "EQ", "com_PropValueFrom": code,
                        "com_TextID": text_id,
                        "com_RelObjID": value_relobj.get(str(value.id)),
                        "com_PropValIsDefault": False,
                    }
                    key = (str(prop_pk), self._key(code))
                    matches = value_by_key.get(key, [])
                    if len(matches) > 1:
                        warnings.append(f"Value '{code}' for '{assignment.property_name}' is duplicated; skipped.")
                    elif matches:
                        row_id = self._int(matches[0].get("com_ValueID"))
                        if any(matches[0].get(k) != v for k, v in computed.items()):
                            value_updates.append({"op": "update", "table": "tCOMd_PropValue",
                                "set": computed, "where": {"com_ValueID": row_id}})
                    else:
                        value_inserts.append({"op": "insert", "table": "tCOMd_PropValue", "rows": [{
                            "com_ValueID": next_value, **session.prototypes["tCOMd_PropValue"], **computed,
                        }]})
                        next_value += 1
                    position += 1

        # Development _code_schemes() is authoritative for the exact scheme grammar.
        scheme_rows, _, _ = ocd._code_schemes(
            snapshot, package_id, base_codes, classes, codes,
            session.prototypes["tCOMd_CodeScheme"],
        )
        scheme_by_name: dict[str, list[dict[str, Any]]] = {}
        for row in existing_schemes:
            scheme_by_name.setdefault(self._key(row.get("com_CodeSchemeName")), []).append(row)
        next_scheme = self._next_id(data["schemes"], "com_CodeSchemeID")
        scheme_inserts: list[dict[str, Any]] = []
        scheme_updates: list[dict[str, Any]] = []
        for wanted in scheme_rows:
            matches = scheme_by_name.get(self._key(wanted.get("com_CodeSchemeName")), [])
            computed = {
                "com_CodeSchemeBody": wanted.get("com_CodeSchemeBody"),
                "com_PackageID": package_id,
            }
            if len(matches) > 1:
                warnings.append(f"Code scheme '{wanted.get('com_CodeSchemeName')}' is duplicated; left unchanged.")
            elif matches:
                row_id = matches[0].get("com_CodeSchemeID")
                if any(matches[0].get(k) != v for k, v in computed.items()):
                    scheme_updates.append({"op": "update", "table": "tCOMd_CodeScheme",
                        "set": computed, "where": {"com_CodeSchemeID": row_id}})
            else:
                scheme_inserts.append({"op": "insert", "table": "tCOMd_CodeScheme", "rows": [{
                    "com_CodeSchemeID": next_scheme, **session.prototypes["tCOMd_CodeScheme"],
                    "com_CodeSchemeName": wanted.get("com_CodeSchemeName"), **computed,
                }]})
                next_scheme += 1

        # Article/class links use the same grouping rule as Development.
        token_by_base = xocd._group_token_by_base(snapshot, classes)
        existing_ac = {(str(r.get("com_ArticleID")), str(r.get("com_ClassID"))) for r in existing_article_classes}
        next_ac = self._next_id(existing_article_classes, "com_ArticleClassID")
        ac_inserts: list[dict[str, Any]] = []
        for code, article_id in article_ids.items():
            token = token_by_base.get(code)
            order = 100
            for cls in classes:
                if token is not None and cls.name.rsplit("_", 1)[0] != token:
                    continue
                class_id = class_ids.get(str(cls.id))
                if class_id is None:
                    continue
                key = (str(article_id), str(class_id))
                if key not in existing_ac:
                    ac_inserts.append({"op": "insert", "table": "tCOMd_ArticleClass", "rows": [{
                        "com_ArticleClassID": next_ac, **session.prototypes["tCOMd_ArticleClass"],
                        "com_ArticleID": article_id, "com_ClassID": class_id,
                        "com_ArticleClassOrder": order, "com_RelObjID": None, "com_TextID": None,
                    }]})
                    next_ac += 1
                    existing_ac.add(key)
                order += 10

        # Add only missing Article Base restrictions; never delete unrelated restrictions.
        art_base = self.context.engineering_artbase_service.build_art_base(snapshot)
        existing_ab = {
            (str(r.get("com_ArticleID")), self._key(r.get("com_ClassName")),
             self._key(r.get("com_PropName")), self._key(r.get("com_PropValue")))
            for r in existing_artbase
        }
        next_ab = self._next_id(existing_artbase, "com_ArtBaseID")
        ab_inserts: list[dict[str, Any]] = []
        for code, prop_values in (art_base or {}).items():
            article_id = article_ids.get(code)
            if article_id is None:
                continue
            for prop_id, value_ids in prop_values.items():
                meta = prop_meta.get(str(prop_id))
                if meta is None:
                    continue
                class_name, prop_name = meta
                for value_id in value_ids:
                    value_code = codes.get(str(value_id), "")
                    key = (str(article_id), self._key(class_name), self._key(prop_name), self._key(value_code))
                    if not value_code or key in existing_ab:
                        continue
                    ab_inserts.append({"op": "insert", "table": "tCOMd_ArtBase", "rows": [{
                        "com_ArtBaseID": next_ab, **session.prototypes["tCOMd_ArtBase"],
                        "com_ArticleID": article_id, "com_ClassName": class_name,
                        "com_PropName": prop_name, "com_PropValue": value_code,
                    }]})
                    existing_ab.add(key)
                    next_ab += 1

        plan = (class_updates + class_inserts + property_updates + property_inserts
                + value_updates + value_inserts + scheme_updates + scheme_inserts
                + ac_inserts + ab_inserts)
        counts = {
            "classes_inserted": len(class_inserts), "classes_updated": len(class_updates),
            "properties_inserted": len(property_inserts), "properties_updated": len(property_updates),
            "values_inserted": len(value_inserts), "values_updated": len(value_updates),
            "schemes_inserted": len(scheme_inserts), "schemes_updated": len(scheme_updates),
            "article_classes_inserted": len(ac_inserts), "artbase_inserted": len(ab_inserts),
        }
        result = {"ok": True, "dry_run": dry_run, "mdb_path": session.mdb_path,
                  "counts": counts, "warnings": warnings, "operations": len(plan)}
        if dry_run or not plan:
            return result
        batch = db.execute_batch(session.mdb_path, plan, transaction=True)
        if not batch.ok:
            return {**result, "ok": False, "error": batch.first_error() or "Class Creation MDB transaction failed."}

        # Read-back verifies the primary table families before the session is marked complete.
        try:
            verified = db.read_tables(session.mdb_path, {
                "classes": "SELECT com_ClassID FROM tCOMd_Class",
                "properties": "SELECT com_PropertyID FROM tCOMd_Property",
                "values": "SELECT com_ValueID FROM tCOMd_PropValue",
                "schemes": "SELECT com_CodeSchemeID FROM tCOMd_CodeScheme",
                "article_classes": "SELECT com_ArticleClassID FROM tCOMd_ArticleClass",
                "artbase": "SELECT com_ArtBaseID FROM tCOMd_ArtBase",
            })
        except Exception as exc:
            return {**result, "ok": False, "error": f"Class Creation wrote data but read-back failed: {exc}"}
        expected = {
            "classes": len(data["classes"]) + len(class_inserts),
            "properties": len(existing_properties) + len(property_inserts),
            "values": len(existing_values) + len(value_inserts),
            "schemes": len(data["schemes"]) + len(scheme_inserts),
            "article_classes": len(existing_article_classes) + len(ac_inserts),
            "artbase": len(existing_artbase) + len(ab_inserts),
        }
        mismatches = [f"{name}: found {len(verified[name])}, expected at least {count}"
                      for name, count in expected.items() if len(verified[name]) < count]
        if mismatches:
            return {**result, "ok": False, "error": "Class Creation read-back validation failed: " + "; ".join(mismatches)}
        sessions.record_workflow(session, self.WORKFLOW, counts)
        try:
            sessions.save(session)
        except OSError as exc:
            return {**result, "ok": False, "error": f"Class Creation was written but session save failed: {exc}"}
        result["verified"] = True
        return result
