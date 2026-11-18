"""Incremental, article-scoped Class Creation export into a ProductStudio MDB.

Class Creation writes only tCOMd_Class and tCOMd_ArticleClass. Article and
CodeScheme rows/IDs are owned by the Articles workflow; Properties and values
are separate workflows. Selection comes from the Articles page Export column.
"""
from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from models.mdb_export_session import MdbExportSession
from models.snapshot import Snapshot
from services.base_service import BaseService
from services.class_creation_selection_service import classes_for_article


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

    @classmethod
    def _next_id(cls, rows: list[dict[str, Any]], column: str) -> int:
        return max((cls._int(row.get(column)) for row in rows), default=0) + 1

    def export_to_session(
        self,
        snapshot: Snapshot,
        session: MdbExportSession,
        selected_article_ids: set[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Export only the classes related to the selected Articles-page rows."""
        if snapshot is None or snapshot.product is None:
            return {"ok": False, "error": "Load a product before exporting Class Creation."}
        selected = {str(value) for value in (selected_article_ids or set()) if str(value)}
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
        all_classes = self.context.engineering_class_service.get_classes(snapshot)
        if not all_classes:
            return {"ok": False, "error": "No engineering classes are available to export."}

        # Keep source article IDs distinct until the Article -> base-code
        # mapping is applied. One MDB Article row may represent several source
        # variants sharing the same priced base article.
        entries = xocd.base_code_entries(snapshot)
        selected_entries = [
            (str(article_id), str(base_code))
            for article_id, base_code in entries
            if str(article_id) in selected and str(base_code or "")
        ]
        found_ids = {article_id for article_id, _base in selected_entries}
        unknown = sorted(selected - found_ids)
        if unknown:
            return {"ok": False, "error": (
                "Some selected articles have no generated base article: "
                + ", ".join(unknown[:10])
                + ". Check their base-length / reduction mapping first."
            )}
        selected_base_codes = list(dict.fromkeys(base for _aid, base in selected_entries))
        if not selected_base_codes:
            return {"ok": False, "error": "The selected articles do not resolve to any base article codes."}

        session_article_ids = session.article_ids()
        missing = [code for code in selected_base_codes if code not in session_article_ids]
        if missing:
            return {"ok": False, "error": (
                "Export the selected Articles first. These base article(s) are not in the session MDB: "
                + ", ".join(missing[:10])
            )}
        selected_article_map = {
            code: session_article_ids[code] for code in selected_base_codes
        }

        # Resolve the class names separately for each selected base. If several
        # selected source articles share a base, their related classes are
        # unioned, then linked once to that MDB Article row.
        class_names_by_base: dict[str, list[str]] = {}
        class_objects_by_base: dict[str, list[Any]] = {}
        for base_code in selected_base_codes:
            source_ids = [
                article_id for article_id, base in selected_entries if base == base_code
            ]
            names: list[str] = []
            selected_classes: list[Any] = []
            seen_names: set[str] = set()
            for article_id in source_ids:
                for cls in classes_for_article(snapshot, all_classes, article_id):
                    name = str(getattr(cls, "name", "") or "")
                    if name and name not in seen_names:
                        seen_names.add(name)
                        names.append(name)
                        selected_classes.append(cls)
            class_names_by_base[base_code] = names
            class_objects_by_base[base_code] = selected_classes

        all_selected_class_names = list(dict.fromkeys(
            name for names in class_names_by_base.values() for name in names
        ))
        if not all_selected_class_names:
            return {"ok": False, "error": "No Class Creation classes are related to the selected article(s)."}

        try:
            data = db.read_tables(session.mdb_path, {
                "package": (
                    "SELECT com_PackageID FROM tCOMd_Package "
                    f"WHERE com_PackageID = {int(package_id)}"
                ),
                "classes": "SELECT com_ClassID, com_ClassName, com_PackageID FROM tCOMd_Class",
                "articles": (
                    "SELECT com_ArticleID, com_ArticleCode, com_PackageID "
                    "FROM tCOMd_Article"
                ),
                "article_classes": (
                    "SELECT com_ArticleClassID, com_ArticleID, com_ClassID, "
                    "com_ArticleClassOrder FROM tCOMd_ArticleClass"
                ),
                "schemes": (
                    "SELECT com_CodeSchemeID, com_CodeSchemeName, com_CodeSchemeBody, "
                    "com_PackageID FROM tCOMd_CodeScheme"
                ),
            })
        except Exception as exc:
            return {"ok": False, "error": f"Could not read the session MDB: {exc}"}
        if not data["package"]:
            return {"ok": False, "error": f"Session MDB no longer contains package {package_id}."}

        package_articles = [
            row for row in data["articles"]
            if str(row.get("com_PackageID")) == str(package_id)
        ]
        actual_articles = {
            (str(row.get("com_ArticleID")), self._key(row.get("com_ArticleCode")))
            for row in package_articles
        }
        invalid = [
            code for code, article_id in selected_article_map.items()
            if (str(article_id), self._key(code)) not in actual_articles
        ]
        if invalid:
            return {"ok": False, "error": (
                "The selected Article mapping no longer matches the MDB for: "
                + ", ".join(invalid[:10])
                + ". Re-export Articles or repair the MDB before Class Creation."
            )}

        package_classes = [
            row for row in data["classes"]
            if str(row.get("com_PackageID")) == str(package_id)
        ]
        package_schemes = [
            row for row in data["schemes"]
            if str(row.get("com_PackageID")) == str(package_id)
        ]
        existing_by_name: dict[str, list[dict[str, Any]]] = {}
        for row in package_classes:
            existing_by_name.setdefault(self._key(row.get("com_ClassName")), []).append(row)

        class_ids: dict[str, int] = {}
        class_inserts: list[dict[str, Any]] = []
        warnings: list[str] = []
        next_class_id = self._next_id(data["classes"], "com_ClassID")
        for name in all_selected_class_names:
            matches = existing_by_name.get(self._key(name), [])
            if len(matches) > 1:
                warnings.append(f"Class '{name}' is duplicated in the MDB; its ArticleClass links were skipped.")
                continue
            if matches:
                class_ids[name] = self._int(matches[0].get("com_ClassID"))
            else:
                class_ids[name] = next_class_id
                class_inserts.append({
                    "op": "insert",
                    "table": "tCOMd_Class",
                    "rows": [{
                        "com_ClassID": next_class_id,
                        **session.prototypes.get("tCOMd_Class", {}),
                        "com_ClassName": name,
                        "com_PackageID": package_id,
                    }],
                })
                next_class_id += 1

        # Do not let ambiguous duplicate class names leak into ArticleClass or
        # CodeScheme references.
        for base_code in selected_base_codes:
            class_names_by_base[base_code] = [
                name for name in class_names_by_base.get(base_code, []) if name in class_ids
            ]
            class_objects_by_base[base_code] = [
                cls for cls in class_objects_by_base.get(base_code, [])
                if str(getattr(cls, "name", "") or "") in class_ids
            ]
        all_selected_class_names = list(dict.fromkeys(
            name for names in class_names_by_base.values() for name in names
        ))
        if not all_selected_class_names:
            return {"ok": False, "error": "No unambiguous Class Creation classes remain for the selected article(s)."}

        # Extend each selected Article's existing CodeScheme body in place.
        # The scheme's primary key and name are owned by the Articles workflow.
        scheme_by_name: dict[str, list[dict[str, Any]]] = {}
        for row in package_schemes:
            scheme_by_name.setdefault(self._key(row.get("com_CodeSchemeName")), []).append(row)
        code_scheme_updates: list[dict[str, Any]] = []
        code_map = xocd._value_code_map(snapshot)
        for base_code in selected_base_codes:
            matches = scheme_by_name.get(self._key(base_code), [])
            if len(matches) != 1:
                return {"ok": False, "error": (
                    f"Expected one existing CodeScheme named '{base_code}' in the session MDB; "
                    "re-export Articles or repair the MDB before Class Creation."
                )}
            desired_rows, _scheme_index, _scheme_names = self.context.ocd_export_service._code_schemes(
                snapshot, package_id, [base_code], class_objects_by_base.get(base_code, []),
                code_map, session.prototypes.get("tCOMd_CodeScheme", {}),
            )
            if not desired_rows:
                return {"ok": False, "error": f"Could not build the Development CodeScheme mapping for '{base_code}'."}
            desired_body = desired_rows[0].get("com_CodeSchemeBody") or ""
            existing_scheme = matches[0]
            token_pattern = re.compile(r"[A-Za-z0-9_]+:[A-Za-z0-9_]+")
            merged_tokens = list(dict.fromkeys(
                token_pattern.findall(str(existing_scheme.get("com_CodeSchemeBody") or ""))
                + token_pattern.findall(str(desired_body))
            ))
            scheme_body = ",".join(
                ["@"] * len(base_code)
                + [part for index, token in enumerate(merged_tokens)
                   for part in (([" "] if index else []) + [token])]
            )
            if existing_scheme.get("com_CodeSchemeBody") != scheme_body:
                code_scheme_updates.append({
                    "op": "update",
                    "table": "tCOMd_CodeScheme",
                    "set": {"com_CodeSchemeBody": scheme_body},
                    "where": {"com_CodeSchemeID": existing_scheme.get("com_CodeSchemeID")},
                })

        existing_links = {
            (str(row.get("com_ArticleID")), str(row.get("com_ClassID")))
            for row in data["article_classes"]
        }
        next_link_id = self._next_id(data["article_classes"], "com_ArticleClassID")
        link_inserts: list[dict[str, Any]] = []
        for base_code in selected_base_codes:
            article_id = selected_article_map[base_code]
            order = 100
            for name in class_names_by_base.get(base_code, []):
                class_id = class_ids.get(name)
                if class_id is None:
                    continue
                key = (str(article_id), str(class_id))
                if key not in existing_links:
                    link_inserts.append({
                        "op": "insert",
                        "table": "tCOMd_ArticleClass",
                        "rows": [{
                            "com_ArticleClassID": next_link_id,
                            **session.prototypes.get("tCOMd_ArticleClass", {}),
                            "com_ArticleID": article_id,
                            "com_ClassID": class_id,
                            "com_ArticleClassOrder": order,
                            "com_RelObjID": None,
                            "com_TextID": None,
                        }],
                    })
                    existing_links.add(key)
                    next_link_id += 1
                order += 10

        plan = class_inserts + code_scheme_updates + link_inserts
        counts = {
            "selected_articles": len(selected),
            "base_articles": len(selected_article_map),
            "classes_inserted": len(class_inserts),
            "classes_reused": len(class_ids) - len(class_inserts),
            "code_schemes_updated": len(code_scheme_updates),
            "article_classes_inserted": len(link_inserts),
        }
        result = {
            "ok": True,
            "dry_run": dry_run,
            "mdb_path": session.mdb_path,
            "counts": counts,
            "warnings": warnings,
            "operations": len(plan),
            "classes": all_selected_class_names,
        }
        if dry_run:
            return result
        if not plan:
            sessions.record_workflow(session, self.WORKFLOW, counts)
            try:
                sessions.save(session)
            except OSError as exc:
                return {**result, "ok": False, "error": f"Could not save Class Creation workflow status: {exc}"}
            result["verified"] = True
            return result

        batch = db.execute_batch(session.mdb_path, plan, transaction=True)
        if not batch.ok:
            return {**result, "ok": False, "error": batch.first_error() or "Class Creation MDB transaction failed."}

        try:
            verified = db.read_tables(session.mdb_path, {
                "classes": "SELECT com_ClassID FROM tCOMd_Class",
                "article_classes": "SELECT com_ArticleClassID FROM tCOMd_ArticleClass",
                "schemes": (
                    "SELECT com_CodeSchemeID, com_CodeSchemeName, com_CodeSchemeBody "
                    "FROM tCOMd_CodeScheme"
                ),
            })
        except Exception as exc:
            return {**result, "ok": False, "error": f"Class Creation wrote data but read-back failed: {exc}"}
        expected = {
            "classes": len(data["classes"]) + len(class_inserts),
            "article_classes": len(data["article_classes"]) + len(link_inserts),
        }
        mismatches = []
        verified_scheme_bodies = {
            self._key(row.get("com_CodeSchemeName")): row.get("com_CodeSchemeBody")
            for row in verified["schemes"]
        }
        for update in code_scheme_updates:
            scheme_id = update["where"]["com_CodeSchemeID"]
            expected_body = update["set"]["com_CodeSchemeBody"]
            original = next(
                (row for row in package_schemes
                 if str(row.get("com_CodeSchemeID")) == str(scheme_id)),
                {},
            )
            scheme_name = self._key(original.get("com_CodeSchemeName"))
            if verified_scheme_bodies.get(scheme_name) != expected_body:
                mismatches.append(f"CodeScheme '{original.get('com_CodeSchemeName')}' body did not verify")
        mismatches.extend(
            f"{name}: found {len(verified[name])}, expected at least {count}"
            for name, count in expected.items()
            if len(verified[name]) < count
        )
        if mismatches:
            return {**result, "ok": False, "error": "Class Creation read-back validation failed: " + "; ".join(mismatches)}
        sessions.record_workflow(session, self.WORKFLOW, counts)
        try:
            sessions.save(session)
        except OSError as exc:
            return {**result, "ok": False, "error": f"Class Creation was written but session save failed: {exc}"}
        result["verified"] = True
        return result
