"""Incremental selected-article Relation Object export to a ProductStudio MDB."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from models.mdb_export_session import MdbExportSession
from models.snapshot import Snapshot
from services.base_service import BaseService
from services.class_creation_selection_service import build_class_creation_scope, classes_for_article
from services.ocd_export_service import OcdExportService


class RelationMdbExportService(BaseService):
    WORKFLOW = "relations"

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
        workflow: str | None = None,
    ) -> dict[str, Any]:
        if snapshot is None or snapshot.product is None:
            return {"ok": False, "error": "Load a product before exporting Relations."}
        selected = {str(v) for v in (selected_article_ids or set()) if str(v)}
        if not selected:
            return {"ok": False, "error": "Select one or more articles in the Articles page Export column first."}
        workflow_name = str(workflow or self.WORKFLOW)
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
        base_codes = set(code for _, code in selected_entries)
        article_map = session.article_ids()
        missing = sorted(base_codes - set(article_map))
        if missing:
            return {"ok": False, "error": "Export Articles first. Missing base article(s): " + ", ".join(missing[:10])}

        scope = build_class_creation_scope(snapshot, selected)
        classes = self.context.engineering_class_service.get_classes(snapshot)
        selected_class_names: dict[str, set[str]] = {}
        property_class_names: dict[str, set[str]] = {}
        for aid, code in selected_entries:
            applicable = classes_for_article(snapshot, classes, aid)
            selected_class_names.setdefault(code, set()).update(
                str(getattr(cls, "name", "") or "") for cls in applicable
                if getattr(cls, "name", "")
            )
            for cls in applicable:
                for assignment in getattr(cls, "properties", []) or []:
                    pid = str(getattr(assignment, "property_id", "") or "")
                    if pid:
                        property_class_names.setdefault(pid, set()).add(str(cls.name))
        selected_property_ids = set(scope.property_ids) | set(scope.option_ids)
        selected_value_ids = {
            str(v) for values in list(scope.property_value_ids.values()) + list(scope.option_value_ids.values())
            for v in values
        }

        all_relations = self.context.engineering_relation_service.ensure_relation_objects(snapshot)
        chosen = []
        for rel in all_relations:
            article_bindings = {str(v) for v in (getattr(rel, "article_codes", []) or [])}
            class_bindings = {
                (str(code), str(name))
                for code, name in (getattr(rel, "article_classes", []) or [])
            }
            prop_ids = {str(v) for v in (getattr(rel, "property_ids", []) or []) if str(v)}
            prop_id = str(getattr(rel, "property_id", "") or "")
            if prop_id:
                prop_ids.add(prop_id)
            value_ids = {str(v) for v in (getattr(rel, "value_ids", []) or []) if str(v)}
            value_id = str(getattr(rel, "value_id", "") or "")
            if value_id:
                value_ids.add(value_id)
            explicitly_bound = bool(article_bindings or class_bindings or prop_ids or value_ids)
            relevant = (
                bool(article_bindings & base_codes)
                or any(code in base_codes and name in selected_class_names.get(code, set())
                       for code, name in class_bindings)
                or bool(prop_ids & selected_property_ids)
                or bool(value_ids & selected_value_ids)
            )
            # Unbound authored relations are product-level and remain in scope.
            if relevant or not explicitly_bound:
                chosen.append(rel)
        if not chosen:
            return {"ok": False, "error": "No Relation Objects are related to the selected articles."}

        tables = {
            "package": f"SELECT com_PackageID FROM tCOMd_Package WHERE com_PackageID = {int(package_id)}",
            "objects": "SELECT com_RelObjID, com_RelObjName, com_PackageID FROM tCOMd_RelObj",
            "relations": "SELECT com_RelationID, com_RelationName, com_RelationBody, com_PackageID FROM tCOMd_Relation",
            "links": "SELECT com_RelObjRelID, com_RelObjID, com_RelationID, com_RelObjTypeCode, com_RelObjDomainCode, com_RelationOrder FROM tCOMd_RelObjRel",
            "articles": "SELECT com_ArticleID, com_ArticleCode, com_RelObjID, com_PackageID FROM tCOMd_Article",
            "article_classes": "SELECT com_ArticleClassID, com_ArticleID, com_ClassID, com_RelObjID FROM tCOMd_ArticleClass",
            "classes": "SELECT com_ClassID, com_ClassName, com_PackageID FROM tCOMd_Class",
            "properties": "SELECT com_PropertyID, com_ClassID, com_PropName, com_RelObjID FROM tCOMd_Property",
            "values": "SELECT com_ValueID, com_PropertyID, com_PropValueFrom, com_RelObjID FROM tCOMd_PropValue",
        }
        try:
            data = db.read_tables(session.mdb_path, tables)
        except Exception as exc:
            return {"ok": False, "error": f"Could not read the session MDB: {exc}"}
        if not data["package"]:
            return {"ok": False, "error": f"Session MDB no longer contains package {package_id}."}

        package_objects = [r for r in data["objects"] if str(r.get("com_PackageID")) == str(package_id)]
        package_relations = [r for r in data["relations"] if str(r.get("com_PackageID")) == str(package_id)]
        object_by_name: dict[str, list[dict[str, Any]]] = {}
        relation_by_name: dict[str, list[dict[str, Any]]] = {}
        object_by_id = {str(row.get("com_RelObjID")): row for row in package_objects}
        relation_by_id = {str(row.get("com_RelationID")): row for row in package_relations}
        for row in package_objects:
            object_by_name.setdefault(self._key(row.get("com_RelObjName")), []).append(row)
        for row in package_relations:
            relation_by_name.setdefault(self._key(row.get("com_RelationName")), []).append(row)

        object_proto = dict(session.prototypes.get("tCOMd_RelObj", {}))
        relation_proto = dict(session.prototypes.get("tCOMd_Relation", {}))
        link_proto = dict(session.prototypes.get("tCOMd_RelObjRel", {}))
        if not object_proto or not relation_proto or not link_proto:
            return {"ok": False, "error": "The session is missing one or more Relation Object table prototypes."}

        next_obj = self._next_id(data["objects"], "com_RelObjID")
        next_relation = self._next_id(data["relations"], "com_RelationID")
        next_link = self._next_id(data["links"], "com_RelObjRelID")
        existing_link_keys = {
            (str(row.get("com_RelObjID")), str(row.get("com_RelationID")),
             str(row.get("com_RelObjTypeCode")), str(row.get("com_RelObjDomainCode")),
             str(self._int(row.get("com_RelationOrder"))))
            for row in data["links"]
        }
        inserts: list[dict[str, Any]] = []
        updates: list[dict[str, Any]] = []
        object_id_by_name: dict[str, int] = {}
        relation_id_by_name: dict[str, int] = {}
        selected_names = {self._key(r.name) for r in chosen}
        for rel in chosen:
            name = str(getattr(rel, "name", "") or "").strip()
            if not name:
                continue
            name_key = self._key(name)
            retained_obj_id = self._int(getattr(rel, "rel_obj_id", ""))
            retained_object = object_by_id.get(retained_obj_id) if retained_obj_id else None
            object_matches = object_by_name.get(name_key, [])
            if len(object_matches) > 1:
                return {"ok": False, "error": f"Duplicate MDB Relation Object name '{name}'."}
            if retained_object is not None:
                if object_matches and self._int(object_matches[0].get("com_RelObjID")) != retained_obj_id:
                    return {"ok": False, "error": (
                        f"Renaming Relation Object to '{name}' would collide with an existing object."
                    )}
                obj_id = retained_obj_id
                if self._key(retained_object.get("com_RelObjName")) != name_key:
                    updates.append({"op": "update", "table": "tCOMd_RelObj",
                                    "set": {"com_RelObjName": name},
                                    "where": {"com_RelObjID": obj_id}})
            elif object_matches:
                obj_id = self._int(object_matches[0].get("com_RelObjID"))
            else:
                obj_id = next_obj
                next_obj += 1
                inserts.append({"op": "insert", "table": "tCOMd_RelObj",
                                "rows": [{"com_RelObjID": obj_id, **object_proto,
                                          "com_RelObjName": name, "com_PackageID": package_id}]})
            object_id_by_name[name_key] = obj_id

            relation_name = str(getattr(rel, "relation_name", "") or
                                OcdExportService._relation_name(name)).strip()
            retained_relation_id = self._int(getattr(rel, "relation_id", ""))
            retained_relation = relation_by_id.get(retained_relation_id) if retained_relation_id else None
            relation_matches = relation_by_name.get(self._key(relation_name), [])
            if len(relation_matches) > 1:
                return {"ok": False, "error": f"Duplicate MDB Relation name '{relation_name}'."}
            body = str(getattr(rel, "body", "") or "")
            if retained_relation is not None:
                if relation_matches and self._int(relation_matches[0].get("com_RelationID")) != retained_relation_id:
                    return {"ok": False, "error": (
                        f"Renaming Relation to '{relation_name}' would collide with an existing relation."
                    )}
                relation_id = retained_relation_id
                changed = {}
                if self._key(retained_relation.get("com_RelationName")) != self._key(relation_name):
                    changed["com_RelationName"] = relation_name
                if str(retained_relation.get("com_RelationBody") or "") != body:
                    changed["com_RelationBody"] = body
                if changed:
                    updates.append({"op": "update", "table": "tCOMd_Relation",
                                    "set": changed, "where": {"com_RelationID": relation_id}})
            elif relation_matches:
                relation_id = self._int(relation_matches[0].get("com_RelationID"))
                if str(relation_matches[0].get("com_RelationBody") or "") != body:
                    updates.append({"op": "update", "table": "tCOMd_Relation",
                                    "set": {"com_RelationBody": body},
                                    "where": {"com_RelationID": relation_id}})
            else:
                relation_id = next_relation
                next_relation += 1
                inserts.append({"op": "insert", "table": "tCOMd_Relation",
                                "rows": [{"com_RelationID": relation_id, **relation_proto,
                                          "com_RelationName": relation_name,
                                          "com_RelationBody": body,
                                          "com_PackageID": package_id}]})
            relation_id_by_name[name_key] = relation_id

            # A RelObjRel link is unique by object/relation/type/domain/order.
            link_key = (
                str(obj_id), str(relation_id), str(getattr(rel, "type_code", "1")),
                str(getattr(rel, "domain", "C")), str(self._int(getattr(rel, "order", 100))),
            )
            if link_key not in existing_link_keys:
                inserts.append({"op": "insert", "table": "tCOMd_RelObjRel",
                                "rows": [{"com_RelObjRelID": next_link, **link_proto,
                                          "com_RelObjID": obj_id, "com_RelationID": relation_id,
                                          "com_RelObjTypeCode": str(getattr(rel, "type_code", "1")),
                                          "com_RelObjDomainCode": str(getattr(rel, "domain", "C")),
                                          "com_RelationOrder": self._int(getattr(rel, "order", 100))}]})
                existing_link_keys.add(link_key)
                next_link += 1

        # Apply relation-object references only to entities in the selected scope.
        ref_updates: dict[tuple[str, str], dict[str, Any]] = {}
        for rel in chosen:
            key = self._key(getattr(rel, "name", ""))
            obj_id = object_id_by_name.get(key)
            if obj_id is None:
                continue
            for code in (getattr(rel, "article_codes", []) or []):
                code = str(code)
                if code in base_codes and code in article_map:
                    ref_updates[("article", str(article_map[code]))] = {"com_RelObjID": obj_id}
            for code, class_name in (getattr(rel, "article_classes", []) or []):
                code, class_name = str(code), str(class_name)
                if code not in base_codes:
                    continue
                article_id = article_map.get(code)
                class_rows = [r for r in data["classes"]
                              if self._key(r.get("com_ClassName")) == self._key(class_name)
                              and str(r.get("com_PackageID")) == str(package_id)]
                if len(class_rows) == 1 and article_id is not None:
                    candidates = [r for r in data["article_classes"]
                                  if str(r.get("com_ArticleID")) == str(article_id)
                                  and str(r.get("com_ClassID")) == str(class_rows[0].get("com_ClassID"))]
                    if len(candidates) == 1:
                        ref_updates[("article_class", str(candidates[0]["com_ArticleClassID"]))] = {"com_RelObjID": obj_id}
            source_property_ids = (
                set(getattr(rel, "property_ids", []) or [])
                | ({str(getattr(rel, "property_id", ""))} if getattr(rel, "property_id", "") else set())
            )
            source_props = {
                str(p.id): p for p in (getattr(snapshot, "properties", []) or [])
                if getattr(p, "id", None) is not None
            }
            source_options = {
                str(o.id): o for o in (getattr(snapshot, "options", []) or [])
                if getattr(o, "id", None) is not None
            }
            class_rows_by_name = {
                self._key(r.get("com_ClassName")): r for r in data["classes"]
                if str(r.get("com_PackageID")) == str(package_id)
            }
            property_rows_by_source: dict[str, list[dict[str, Any]]] = {}
            for source_id in source_property_ids:
                source = source_props.get(str(source_id)) or source_options.get(str(source_id))
                source_name = str(getattr(source, "name", "") or "")
                prop_name = self._key(xocd._prop_ident(source_name)) if source_name else ""
                for class_name in property_class_names.get(str(source_id), set()):
                    class_row = class_rows_by_name.get(self._key(class_name))
                    if class_row is None:
                        continue
                    matches = [
                        row for row in data["properties"]
                        if str(row.get("com_ClassID")) == str(class_row.get("com_ClassID"))
                        and self._key(row.get("com_PropName")) == prop_name
                    ]
                    if len(matches) == 1:
                        mdb_property_id = str(matches[0].get("com_PropertyID"))
                        ref_updates[("property", mdb_property_id)] = {"com_RelObjID": obj_id}
                        property_rows_by_source.setdefault(str(source_id), []).extend(matches)

            # Source value IDs are not MDB surrogate IDs. Resolve them by
            # (selected class, normalized property, exported value code).
            value_parent: dict[str, str] = {}
            for value in getattr(snapshot, "property_values", []) or []:
                value_parent[str(getattr(value, "id", "") or "")] = str(getattr(value, "property_id", "") or "")
            for value in getattr(snapshot, "option_values", []) or []:
                value_parent[str(getattr(value, "id", "") or "")] = str(getattr(value, "option_id", "") or "")
            for source_prop in getattr(snapshot, "properties", []) or []:
                for value in getattr(source_prop, "values", []) or []:
                    value_parent.setdefault(str(getattr(value, "id", "") or ""), str(getattr(source_prop, "id", "") or ""))
            for source_option in getattr(snapshot, "options", []) or []:
                for value in getattr(source_option, "values", []) or []:
                    value_parent.setdefault(str(getattr(value, "id", "") or ""), str(getattr(source_option, "id", "") or ""))
            source_value_ids = (
                set(getattr(rel, "value_ids", []) or [])
                | ({str(getattr(rel, "value_id", ""))} if getattr(rel, "value_id", "") else set())
            )
            value_codes = xocd._value_code_map(snapshot)
            for source_value_id in source_value_ids:
                parent_id = value_parent.get(str(source_value_id), "")
                source = source_props.get(parent_id) or source_options.get(parent_id)
                source_name = str(getattr(source, "name", "") or "")
                prop_name = self._key(xocd._prop_ident(source_name)) if source_name else ""
                code = self._key(value_codes.get(str(source_value_id), ""))
                if not prop_name or not code:
                    continue
                for class_name in property_class_names.get(parent_id, set()):
                    class_row = class_rows_by_name.get(self._key(class_name))
                    if class_row is None:
                        continue
                    mdb_props = [
                        row for row in data["properties"]
                        if str(row.get("com_ClassID")) == str(class_row.get("com_ClassID"))
                        and self._key(row.get("com_PropName")) == prop_name
                    ]
                    for mdb_prop in mdb_props:
                        for mdb_value in data["values"]:
                            if (str(mdb_value.get("com_PropertyID")) == str(mdb_prop.get("com_PropertyID"))
                                    and self._key(mdb_value.get("com_PropValueFrom")) == code):
                                mdb_value_id = str(mdb_value.get("com_ValueID"))
                                ref_updates[("value", mdb_value_id)] = {"com_RelObjID": obj_id}

        table_for_kind = {"article": "tCOMd_Article", "article_class": "tCOMd_ArticleClass",
                          "property": "tCOMd_Property", "value": "tCOMd_PropValue"}
        pk_for_kind = {"article": "com_ArticleID", "article_class": "com_ArticleClassID",
                       "property": "com_PropertyID", "value": "com_ValueID"}
        existing_refs = {
            ("article", str(r.get("com_ArticleID"))): r.get("com_RelObjID") for r in data["articles"]
            if str(r.get("com_PackageID")) == str(package_id)
        }
        existing_refs.update({("article_class", str(r.get("com_ArticleClassID"))): r.get("com_RelObjID") for r in data["article_classes"]})
        existing_refs.update({("property", str(r.get("com_PropertyID"))): r.get("com_RelObjID") for r in data["properties"]})
        existing_refs.update({("value", str(r.get("com_ValueID"))): r.get("com_RelObjID") for r in data["values"]})
        for (kind, identity), fields in ref_updates.items():
            if str(existing_refs.get((kind, identity)) or "") == str(fields["com_RelObjID"]):
                continue
            updates.append({"op": "update", "table": table_for_kind[kind],
                            "set": fields, "where": {pk_for_kind[kind]: int(identity)}})

        counts = {"selected_articles": len(selected), "base_articles": len(base_codes),
                  "relation_objects_selected": len(chosen),
                  "relation_objects_inserted": sum(1 for op in inserts if op["table"] == "tCOMd_RelObj"),
                  "relations_inserted": sum(1 for op in inserts if op["table"] == "tCOMd_Relation"),
                  "relation_links_inserted": sum(1 for op in inserts if op["table"] == "tCOMd_RelObjRel"),
                  "entity_links_updated": sum(1 for op in updates if op["table"] in table_for_kind.values())}
        plan = inserts + updates
        result = {"ok": True, "dry_run": dry_run, "mdb_path": session.mdb_path,
                  "counts": counts, "operations": len(plan)}
        if dry_run:
            return result
        if not plan:
            sessions.record_workflow(session, workflow_name, counts)
            sessions.save(session)
            result["verified"] = True
            return result
        batch = db.execute_batch(session.mdb_path, plan, transaction=True)
        if not batch.ok:
            return {**result, "ok": False, "error": batch.first_error() or "Relations MDB transaction failed."}
        try:
            verified = db.read_tables(session.mdb_path, {
                "objects": "SELECT com_RelObjID FROM tCOMd_RelObj",
                "relations": "SELECT com_RelationID FROM tCOMd_Relation",
                "links": "SELECT com_RelObjRelID FROM tCOMd_RelObjRel",
            })
        except Exception as exc:
            return {**result, "ok": False, "error": f"Relations were written but read-back failed: {exc}"}
        if (len(verified["objects"]) < len(data["objects"]) + counts["relation_objects_inserted"]
                or len(verified["relations"]) < len(data["relations"]) + counts["relations_inserted"]
                or len(verified["links"]) < len(data["links"]) + counts["relation_links_inserted"]):
            return {**result, "ok": False, "error": "Relations read-back count verification failed."}
        sessions.record_workflow(session, workflow_name, counts)
        try:
            sessions.save(session)
        except OSError as exc:
            return {**result, "ok": False, "error": f"Relations were written but workflow status could not be saved: {exc}"}
        result["verified"] = True
        return result
