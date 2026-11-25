"""Incremental, article-scoped Class Creation export into a ProductStudio MDB.

Class Creation inserts tCOMd_Class and tCOMd_ArticleClass rows and extends
existing CodeScheme bodies without changing their IDs. Properties and values
are separate workflows. Selection comes from the Articles page Export column.
"""
from __future__ import annotations

from copy import copy
from hashlib import sha1
from pathlib import Path
import re
from typing import Any

from models.mdb_export_session import MdbExportSession
from models.snapshot import Snapshot
from services.relation_link_policy import legacy_session_error
from services.base_service import BaseService
from services.class_creation_selection_service import classes_for_article
from services.relation_link_policy import is_attached


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

    # -- CodeScheme planning: in place, or clone-on-write when a scheme is shared ---------------------

    _TOKEN = re.compile(r"[A-Za-z0-9_]+:[A-Za-z0-9_]+")
    _CLONE_SUFFIX = re.compile(r"_CS[0-9a-f]{8}$")
    SCHEME_NAME_LIMIT = 30  # tCOMd_CodeScheme.com_CodeSchemeName length

    @staticmethod
    def _leading_at(body: Any) -> int:
        count = 0
        for part in str(body or "").split(","):
            if part != "@":
                break
            count += 1
        return count

    @classmethod
    def _extend_body(cls, existing_body: Any, desired_tokens: list[str], prefix_len: int) -> str:
        """``existing_body`` verbatim plus the missing ``class:property`` tokens, appended in the usual
        ``TOKEN, ,TOKEN`` form. Nothing already present is rewritten or reordered."""
        existing = str(existing_body or "")
        present = cls._TOKEN.findall(existing)
        missing = [t for t in dict.fromkeys(desired_tokens) if t not in present]
        parts = existing.split(",") if existing.strip() else ["@"] * prefix_len
        if not missing:
            return existing if existing.strip() else ",".join(parts)
        have_tokens = bool(present)
        for token in missing:
            if have_tokens:
                parts.append(" ")
            parts.append(token)
            have_tokens = True
        return ",".join(parts)

    @classmethod
    def clone_name(cls, source_name: Any, body: str) -> str:
        """Deterministic clone name: the root scheme name plus ``_CS`` and 8 hex digits of the clone body."""
        suffix = "_CS" + sha1(str(body).encode("utf-8")).hexdigest()[:8]
        root = cls._CLONE_SUFFIX.sub("", str(source_name or ""))
        return root[: cls.SCHEME_NAME_LIMIT - len(suffix)] + suffix

    def _plan_code_schemes(
        self, *, snapshot: Snapshot, package_id: Any, session: MdbExportSession,
        selected_base_codes: list[str], selected_article_map: dict[str, Any],
        class_objects_by_base: dict[str, list[Any]], data: dict[str, list[dict[str, Any]]],
        package_schemes: list[dict[str, Any]], xocd: Any,
    ) -> dict[str, Any]:
        """Plan the CodeScheme writes for the selected articles.

        * Every article is resolved through its own ``com_CodeSchemeID`` (production workspaces share
          schemes across many articles); only an article with no scheme link falls back to the scheme
          named after its code.
        * A scheme used only by selected articles is extended **in place**.
        * A scheme also used by unselected articles is **cloned**: the original is untouched, the clone
          carries the original body plus the new class tokens, and only the selected articles are
          reassigned. The clone name is deterministic, so a later export reuses it.
        * Anything that cannot be identified safely is an error; nothing is written.
        """
        scheme_by_id = {str(r.get("com_CodeSchemeID")): r for r in package_schemes}
        scheme_by_name: dict[str, list[dict[str, Any]]] = {}
        for row in package_schemes:
            scheme_by_name.setdefault(self._key(row.get("com_CodeSchemeName")), []).append(row)
        articles_by_id = {str(r.get("com_ArticleID")): r for r in data["articles"]}
        selected_ids = {str(v) for v in selected_article_map.values()}
        users: dict[str, set[str]] = {}
        for row in data["articles"]:
            sid = row.get("com_CodeSchemeID")
            if sid not in (None, ""):
                users.setdefault(str(sid), set()).add(str(row.get("com_ArticleID")))

        groups: dict[str, list[str]] = {}
        for base_code in selected_base_codes:
            article_row = articles_by_id.get(str(selected_article_map[base_code]), {})
            sid = article_row.get("com_CodeSchemeID")
            if sid not in (None, ""):
                if str(sid) not in scheme_by_id:
                    return {"error": (
                        f"Article '{base_code}' references CodeScheme id {sid}, which is not in the export "
                        "package; its scheme cannot be identified safely. Repair the MDB before Class Creation."
                    )}
                groups.setdefault(str(sid), []).append(base_code)
                continue
            matches = scheme_by_name.get(self._key(base_code), [])
            if len(matches) != 1:
                return {"error": (
                    f"Expected one existing CodeScheme named '{base_code}' in the session MDB; "
                    "re-export Articles or repair the MDB before Class Creation."
                )}
            groups.setdefault(str(matches[0].get("com_CodeSchemeID")), []).append(base_code)

        code_map = xocd._value_code_map(snapshot)
        proto = session.prototypes.get("tCOMd_CodeScheme", {})
        next_scheme_id = self._next_id(data["schemes"], "com_CodeSchemeID")
        updates: list[dict[str, Any]] = []
        clone_inserts: list[dict[str, Any]] = []
        reassignments: list[dict[str, Any]] = []
        clones_reused = 0
        notes: list[str] = []
        created: dict[str, dict[str, Any]] = {}  # clone name key -> inserted row (shared inside one export)

        for sid, bases in groups.items():
            source = scheme_by_id[sid]
            tokens: list[str] = []
            for base_code in bases:
                desired_rows, _index, _names = self.context.ocd_export_service._code_schemes(
                    snapshot, package_id, [base_code], class_objects_by_base.get(base_code, []),
                    code_map, proto,
                )
                if not desired_rows:
                    return {"error": f"Could not build the Development CodeScheme mapping for '{base_code}'."}
                tokens.extend(self._TOKEN.findall(str(desired_rows[0].get("com_CodeSchemeBody") or "")))
            existing_body = str(source.get("com_CodeSchemeBody") or "")
            prefix_len = self._leading_at(existing_body) or len(bases[0])
            too_long = [b for b in bases if existing_body.strip() and len(b) != prefix_len]
            unselected = users.get(sid, set()) - selected_ids

            body = self._extend_body(existing_body, tokens, prefix_len)
            if not unselected:
                if existing_body != body:
                    updates.append({
                        "op": "update", "table": "tCOMd_CodeScheme", "set": {"com_CodeSchemeBody": body},
                        "where": {"com_CodeSchemeID": source.get("com_CodeSchemeID")},
                    })
                continue

            if body == existing_body:
                continue  # the shared scheme already carries every needed class; nothing to write
            if too_long:
                return {"error": (
                    f"CodeScheme '{source.get('com_CodeSchemeName')}' is shared with "
                    f"{len(unselected)} unselected article(s) and its pattern is {prefix_len} characters wide, "
                    f"but selected article(s) {', '.join(too_long[:5])} have a different length; "
                    "the correct scheme cannot be identified safely."
                )}
            name = self.clone_name(source.get("com_CodeSchemeName"), body)
            name_key = self._key(name)
            existing_clone = scheme_by_name.get(name_key, [])
            if len(existing_clone) > 1:
                return {"error": f"CodeScheme clone name '{name}' is duplicated in the MDB; repair it first."}
            if existing_clone:
                clone = existing_clone[0]
                if str(clone.get("com_CodeSchemeBody") or "") != body:
                    return {"error": (
                        f"CodeScheme '{name}' already exists but is not the expected clone of "
                        f"'{source.get('com_CodeSchemeName')}'; refusing to reuse or overwrite it."
                    )}
                clone_id = clone.get("com_CodeSchemeID")
                clones_reused += 1
            elif name_key in created:
                clone_id = created[name_key]["com_CodeSchemeID"]
            else:
                clone_id = next_scheme_id
                next_scheme_id += 1
                carry = {k: v for k, v in source.items()
                         if k not in ("com_CodeSchemeID", "com_CodeSchemeName", "com_CodeSchemeBody",
                                      "com_PackageID") and not str(k).startswith("sys_tmp")}
                row = {"com_CodeSchemeID": clone_id, **(carry or proto),
                       "com_CodeSchemeName": name, "com_CodeSchemeBody": body, "com_PackageID": package_id}
                created[name_key] = row
                clone_inserts.append({"op": "insert", "table": "tCOMd_CodeScheme", "rows": [row]})
            notes.append(
                f"CodeScheme '{source.get('com_CodeSchemeName')}' is shared with {len(unselected)} unselected "
                f"article(s): {'reusing' if existing_clone else 'cloning it as'} '{name}' for "
                f"{', '.join(bases[:6])}{' ...' if len(bases) > 6 else ''}. The original scheme and the "
                "unselected articles are unchanged."
            )
            for base_code in bases:
                article_id = selected_article_map[base_code]
                if str(articles_by_id.get(str(article_id), {}).get("com_CodeSchemeID")) != str(clone_id):
                    reassignments.append({
                        "op": "update", "table": "tCOMd_Article", "set": {"com_CodeSchemeID": clone_id},
                        "where": {"com_ArticleID": article_id},
                    })
        return {"updates": updates, "clone_inserts": clone_inserts, "reassignments": reassignments,
                "clones_reused": clones_reused, "notes": notes}

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
        legacy = legacy_session_error(session)
        if legacy:
            return {"ok": False, "error": legacy, "legacy_session": True}
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
        # Canonical base of every article from the context-aware resolver (price tier
        # included), resolved once and handed to the class selection below.
        base_of = {str(_aid): str(_base or "") for _aid, _base in entries}
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
            selected_classes_by_name: dict[str, Any] = {}
            for article_id in source_ids:
                for cls in classes_for_article(snapshot, all_classes, article_id, base_of=base_of):
                    name = str(getattr(cls, "name", "") or "")
                    if not name:
                        continue
                    existing_class = selected_classes_by_name.get(name)
                    if existing_class is None:
                        # Work on a detached class/property list. The engineering
                        # snapshot is shared by later workflows and must remain
                        # unchanged when selected variants are unioned.
                        selected_class = copy(cls)
                        selected_class.properties = list(
                            getattr(cls, "properties", []) or []
                        )
                        selected_classes_by_name[name] = selected_class
                        continue
                    existing_property_ids = {
                        str(getattr(assignment, "property_id", "") or "")
                        for assignment in getattr(existing_class, "properties", []) or []
                    }
                    for assignment in getattr(cls, "properties", []) or []:
                        property_id = str(getattr(assignment, "property_id", "") or "")
                        if property_id and property_id not in existing_property_ids:
                            existing_class.properties.append(assignment)
                            existing_property_ids.add(property_id)
            class_names_by_base[base_code] = list(selected_classes_by_name)
            class_objects_by_base[base_code] = list(selected_classes_by_name.values())

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
                    "SELECT com_ArticleID, com_ArticleCode, com_PackageID, com_CodeSchemeID "
                    "FROM tCOMd_Article"
                ),
                "article_classes": (
                    "SELECT com_ArticleClassID, com_ArticleID, com_ClassID, "
                    "com_ArticleClassOrder FROM tCOMd_ArticleClass"
                ),
                "schemes": "SELECT * FROM tCOMd_CodeScheme",
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

        # Attached production workspace: never add a second class set next to production classes whose
        # identity cannot be established. A class that is NEW by name while a selected base article is
        # already linked to production classes this export does not resolve (e.g. engineering
        # ``Dalby_Attribute`` vs production ``DALBY_ATTR``) is reported as an identity conflict and the
        # whole class operation stops with zero writes. Names are never fuzzy-matched; no mapping exists
        # yet (see docs/03_Workflows/productstudio_incremental_mdb_export.md, "Production class identity").
        identity_conflicts: list[dict[str, Any]] = []
        if is_attached(session):
            production_name_by_id = {
                str(row.get("com_ClassID")): str(row.get("com_ClassName") or "") for row in package_classes
            }
            new_names = {self._key(row["rows"][0]["com_ClassName"]) for row in class_inserts}
            for base_code in selected_base_codes:
                article_key = str(selected_article_map[base_code])
                linked = {str(row.get("com_ClassID")) for row in data["article_classes"]
                          if str(row.get("com_ArticleID")) == article_key
                          and str(row.get("com_ClassID")) in production_name_by_id}
                resolved = {str(class_ids[name]) for name in class_names_by_base.get(base_code, [])
                            if name in class_ids and self._key(name) not in new_names}
                unresolved_production = sorted(production_name_by_id[c] for c in linked - resolved)
                incoming_new = [name for name in class_names_by_base.get(base_code, [])
                                if self._key(name) in new_names]
                if unresolved_production and incoming_new:
                    identity_conflicts.append({
                        "kind": "class_identity", "article": base_code, "action": "stopped",
                        "incoming_classes": incoming_new,
                        "existing_production_classes": unresolved_production,
                        "reason": "no stable mapping between the engineering and production classes",
                    })
        if identity_conflicts:
            return {
                "ok": False, "dry_run": dry_run, "conflicts": identity_conflicts,
                "error": "Class identity cannot be established, nothing was written. " + " ".join(
                    f"{c['article']}: incoming {', '.join(c['incoming_classes'])} would sit next to existing "
                    f"production class(es) {', '.join(c['existing_production_classes'])}; no reliable mapping "
                    "exists between them." for c in identity_conflicts[:5]),
            }

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

        # CodeSchemes: update in place when every article using a scheme is selected, otherwise
        # clone-on-write so unselected articles keep exactly what they had.
        scheme_plan = self._plan_code_schemes(
            snapshot=snapshot, package_id=package_id, session=session,
            selected_base_codes=selected_base_codes, selected_article_map=selected_article_map,
            class_objects_by_base=class_objects_by_base, data=data, package_schemes=package_schemes, xocd=xocd,
        )
        if "error" in scheme_plan:
            return {"ok": False, "error": scheme_plan["error"]}
        code_scheme_updates = scheme_plan["updates"]
        scheme_clone_inserts = scheme_plan["clone_inserts"]
        article_reassignments = scheme_plan["reassignments"]
        warnings.extend(scheme_plan["notes"])

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

        plan = class_inserts + scheme_clone_inserts + code_scheme_updates + article_reassignments + link_inserts
        counts = {
            "selected_articles": len(selected),
            "base_articles": len(selected_article_map),
            "classes_inserted": len(class_inserts),
            "classes_reused": len(class_ids) - len(class_inserts),
            "code_schemes_updated": len(code_scheme_updates),
            "code_schemes_cloned": len(scheme_clone_inserts),
            "code_schemes_clone_reused": scheme_plan["clones_reused"],
            "articles_reassigned": len(article_reassignments),
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
                "articles": "SELECT com_ArticleID, com_CodeSchemeID FROM tCOMd_Article",
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
        for insert in scheme_clone_inserts:
            row = insert["rows"][0]
            if verified_scheme_bodies.get(self._key(row["com_CodeSchemeName"])) != row["com_CodeSchemeBody"]:
                mismatches.append(f"Cloned CodeScheme '{row['com_CodeSchemeName']}' did not verify")
        verified_article_scheme = {
            str(row.get("com_ArticleID")): row.get("com_CodeSchemeID") for row in verified.get("articles", [])
        }
        for update in article_reassignments:
            article_id = str(update["where"]["com_ArticleID"])
            if str(verified_article_scheme.get(article_id)) != str(update["set"]["com_CodeSchemeID"]):
                mismatches.append(f"Article {article_id} was not reassigned to its cloned CodeScheme")
        mismatches.extend(
            f"{name}: found {len(verified[name])}, expected at least {count}"
            for name, count in expected.items()
            if len(verified[name]) < count
        )
        if mismatches:
            return {**result, "ok": False, "error": "Class Creation read-back validation failed: " + "; ".join(mismatches)}
        for insert in scheme_clone_inserts:
            row = insert["rows"][0]
            session.scheme_map[row["com_CodeSchemeName"]] = row["com_CodeSchemeID"]
        sessions.record_workflow(session, self.WORKFLOW, counts)
        try:
            sessions.save(session)
        except OSError as exc:
            return {**result, "ok": False, "error": f"Class Creation was written but session save failed: {exc}"}
        result["verified"] = True
        return result
