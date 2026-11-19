"""Non-destructive Article export into an existing OCD MDB.

Article rows are matched by base article code. Existing primary keys and
unrelated columns are preserved. Text rows are owned by the Text workflow:
this exporter only reuses existing text IDs and leaves missing links empty for
the later Text export to resolve.

Two entry points share one implementation:

* :meth:`ArticleMdbExportService.export` - upsert into a caller-chosen MDB
  (original behaviour, unchanged).
* :meth:`ArticleMdbExportService.export_to_session` - the ProductStudio
  Articles workflow: upsert the *selected* articles into the product's single
  session MDB, retain the source-article -> ``com_ArticleID`` mapping in the
  session and create only the minimum supporting ``tCOMd_CodeScheme`` rows.

Tables written by the session path: ``tCOMd_Article`` and ``tCOMd_CodeScheme``
- nothing else (no classes, properties, values, relations, text or prices).

Why CodeScheme: ``tCOMd_Article.com_CodeSchemeID`` is a mandatory reference to
``tCOMd_CodeScheme``. The minimum valid record is a scheme named after the
article's scheme with the body ``@,@,...`` (one ``@`` per article-code
character). The property tokens that normally follow belong to Class Creation
and are added by that workflow later.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from models.mdb_export_session import MdbExportSession
from models.snapshot import Snapshot
from services.relation_link_policy import legacy_session_error
from services.base_service import BaseService
from services.relation_link_policy import (
    LinkDescriber, conflict_entry, conflict_message, decide, is_attached,
)


class ArticleMdbExportService(BaseService):
    """Upsert base-article records without rebuilding the MDB."""

    TABLE = "tCOMd_Article"
    PK = "com_ArticleID"
    SCHEME_TABLE = "tCOMd_CodeScheme"
    SCHEME_PK = "com_CodeSchemeID"
    WORKFLOW = "articles"

    @staticmethod
    def _key(value: Any) -> str:
        return str(value or "").strip().casefold()

    @staticmethod
    def _int(value: Any) -> int | None:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _prototype(rows: list[dict[str, Any]]) -> dict[str, Any]:
        if not rows:
            return {}
        row = dict(rows[0])
        row.pop("com_ArticleID", None)
        for column in list(row):
            if column.startswith("sys_tmp"):
                row.pop(column, None)
        return row

    def _price_base_of(self, snapshot: Snapshot) -> dict[str, str]:
        """Article code -> price base, so MDB articles line up with prices.

        Falls back to an empty map (member ``reduced_article`` is then used)
        when the pricing helper is unavailable for this snapshot.
        """
        xocd = getattr(self.context, "xocd_export_service", None)
        if xocd is None:
            return {}
        try:
            return dict(xocd._price_base_of(snapshot))
        except Exception:
            return {}

    def _base_articles(
        self, snapshot: Snapshot, selected_article_ids: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        articles = {str(a.id): a for a in snapshot.articles if a.id is not None}
        selected = (
            {str(v) for v in selected_article_ids} if selected_article_ids is not None else None
        )
        base_of = self._price_base_of(snapshot)
        unique: dict[str, dict[str, Any]] = {}
        for family in getattr(snapshot.engineering, "families", []) or []:
            for member in getattr(family, "members", []) or []:
                article_id = str(getattr(member, "article_id", ""))
                if selected is not None and article_id not in selected:
                    continue
                article = articles.get(article_id)
                source_code = str(getattr(article, "code", "") or "").strip()
                # Keep the Development/full-export rule exactly: price base first,
                # then member.reduced_article. Do not invent a base by splitting
                # the source code; _base_codes() does not do that.
                code = (base_of.get(source_code) or "").strip() or str(
                    getattr(member, "reduced_article", "") or ""
                ).strip()
                if not code:
                    continue
                # One MDB base-article row per base code. The first member is
                # representative; conflicting metadata is surfaced as a warning.
                entry = unique.setdefault(code, {
                    "code": code,
                    "relation_name": str(getattr(member, "relation_object", "") or "").strip()
                                     or f"P_{code}",
                    # Development _code_schemes() names each scheme after its
                    # base article code; member.code_scheme is not its authority.
                    "scheme_name": code,
                    "short_text": str(getattr(member, "short_description", "") or "").strip(),
                    "long_text": str(getattr(member, "long_description", "") or "").strip(),
                    "member_ids": [],
                    "source_ids": [],
                    "source_codes": [],
                })
                entry["member_ids"].append(str(getattr(member, "id", "") or ""))
                if article_id not in entry["source_ids"]:
                    entry["source_ids"].append(article_id)
                    if source_code:
                        entry["source_codes"].append(source_code)
                for field, attr in (("relation_name", "relation_object"),
                                    ("short_text", "short_description"), ("long_text", "long_description")):
                    value = str(getattr(member, attr, "") or "").strip()
                    if value and not entry[field]:
                        entry[field] = value
        return list(unique.values())

    # -- ProductStudio session entry point ------------------------------

    def export_to_session(
        self, snapshot: Snapshot, session: MdbExportSession, selected_article_ids: set[str],
        dry_run: bool = False, replace_existing_links: bool = False,
    ) -> dict[str, Any]:
        """Export the selected articles into the product's session MDB.

        In an attached production workspace an existing valid relation-object / code-scheme link of an
        article is preserved and reported in ``conflicts``; ``replace_existing_links=True`` is the
        separate, explicit authorization to replace them (not used by the normal export buttons).

        On success the session (``article_map``, ``scheme_map``,
        ``workflow_status``) is updated and persisted. Nothing is recorded for
        a failed or dry run.
        """
        if not selected_article_ids:
            return {"ok": False, "error": "Select at least one article to export."}
        if snapshot is None or snapshot.product is None:
            return {"ok": False, "error": "Load a product before exporting Articles."}
        legacy = legacy_session_error(session)
        if legacy:
            return {"ok": False, "error": legacy, "legacy_session": True}
        sessions = getattr(self.context, "mdb_export_session_service", None)
        try:
            from services.mdb_export_session_service import MdbExportSessionService
            if sessions is None:
                sessions = MdbExportSessionService(self.context)
            if sessions.product_key(snapshot) != session.product_key:
                return {"ok": False, "error": "The export session belongs to a different product."}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        result = self.export(
            snapshot, session.mdb_path, dry_run=dry_run,
            selected_article_ids=selected_article_ids, session=session,
            replace_existing_links=replace_existing_links,
        )
        if not result.get("ok") or dry_run:
            return result

        session.article_map.update(result.pop("_article_map"))
        session.scheme_map.update(result.pop("_scheme_map"))
        sessions.record_workflow(session, self.WORKFLOW, {
            "inserted": result["inserted"], "updated": result["updated"],
            "skipped": result["skipped"], "schemes_created": result["schemes_created"],
        })
        try:
            sessions.save(session)
        except OSError as exc:
            return {**result, "ok": False,
                    "error": f"Articles were written but the export session could not be saved: {exc}"}
        result["article_ids"] = session.article_ids()
        return result

    # -- Shared implementation ----------------------------------------------

    def export(
        self, snapshot: Snapshot, mdb_path: str | Path, dry_run: bool = False,
        selected_article_ids: set[str] | None = None,
        session: MdbExportSession | None = None,
        replace_existing_links: bool = False,
    ) -> dict[str, Any]:
        mdb = Path(mdb_path)
        if not mdb.is_file():
            return {"ok": False, "error": "Select an existing OCD MDB file."}
        if snapshot is None or snapshot.product is None:
            return {"ok": False, "error": "Load a product before exporting Articles."}
        articles = self._base_articles(snapshot, selected_article_ids)
        if not articles:
            return {"ok": False, "error": (
                "None of the selected articles has a reduced Base Article."
                if selected_article_ids is not None else
                "No reduced Base Articles found. Apply the article reduction first.")}
        db = self.context.mdb_service
        if not db.is_available():
            return {"ok": False, "error": "32-bit PowerShell / ACE bridge unavailable."}

        in_session = session is not None
        queries = {
            "articles": "SELECT * FROM [tCOMd_Article]",
            "package": (
                f"SELECT TOP 1 com_PackageID, com_ComGroupID FROM [tCOMd_Package] "
                f"WHERE com_PackageID = {int(session.package_id)}"
                if in_session else "SELECT TOP 1 com_PackageID, com_ComGroupID FROM [tCOMd_Package]"
            ),
            "group": "SELECT TOP 1 com_ComGroupID FROM [tCOMd_ComGroup]",
            "schemes": "SELECT com_CodeSchemeID, com_CodeSchemeName, com_PackageID FROM [tCOMd_CodeScheme]",
            "relobjs": "SELECT com_RelObjID, com_RelObjName, com_PackageID FROM [tCOMd_RelObj]",
            "texts": "SELECT com_TextID, com_TextName, com_TextTypeCode, com_PackageID FROM [tCOMd_Text]",
            "max_article": "SELECT MAX(com_ArticleID) AS max_id FROM [tCOMd_Article]",
            "max_scheme": "SELECT MAX(com_CodeSchemeID) AS max_id FROM [tCOMd_CodeScheme]",
        }
        if not in_session:
            queries["article_proto"] = "SELECT TOP 1 * FROM [tCOMd_Article]"
        try:
            data = db.read_tables(mdb, queries) if callable(getattr(db, "read_tables", None)) else {
                name: db.read_table(mdb, sql) for name, sql in queries.items()
            }
        except Exception as exc:
            return {"ok": False, "error": f"Could not read destination MDB: {exc}"}

        if in_session:
            proto = dict(session.prototypes.get(self.TABLE, {}))
            scheme_proto = dict(session.prototypes.get(self.SCHEME_TABLE, {}))
        else:
            proto = self._prototype(data.get("article_proto", []))
            scheme_proto = {}
            if not proto:
                return {"ok": False, "error": "Could not read tCOMd_Article schema from the destination MDB."}
        package = (data.get("package") or [{}])[0]
        package_id = package.get("com_PackageID")
        comgroup_id = package.get("com_ComGroupID")
        if package_id in (None, ""):
            if in_session:
                return {"ok": False, "error": (
                    f"The export MDB no longer contains package {session.package_id}; "
                    "it was replaced or altered outside ProductStudio. Nothing was written.")}
            return {"ok": False, "error": "Destination MDB has no package row; Article export cannot safely assign package IDs."}
        if comgroup_id in (None, "") and data.get("group"):
            comgroup_id = data["group"][0].get("com_ComGroupID")

        by_id: dict[str, dict[str, Any]] = {}
        existing_by_code: dict[str, list[dict[str, Any]]] = {}
        for row in data.get("articles", []):
            if in_session and str(row.get("com_PackageID")) != str(package_id):
                continue
            by_id[str(row.get("com_ArticleID"))] = row
            code = self._key(row.get("com_ArticleCode"))
            if code:
                existing_by_code.setdefault(code, []).append(row)
        scheme_by_name: dict[str, list[Any]] = {}
        for row in data.get("schemes", []):
            if str(row.get("com_PackageID")) == str(package_id):
                scheme_by_name.setdefault(self._key(row.get("com_CodeSchemeName")), []).append(row.get("com_CodeSchemeID"))
        relobj_by_name: dict[str, list[Any]] = {}
        for row in data.get("relobjs", []):
            if str(row.get("com_PackageID")) == str(package_id):
                relobj_by_name.setdefault(self._key(row.get("com_RelObjName")), []).append(row.get("com_RelObjID"))
        text_by_key: dict[tuple[str, str], list[Any]] = {}
        for row in data.get("texts", []):
            if str(row.get("com_PackageID")) != str(package_id):
                continue
            text_by_key.setdefault((self._key(row.get("com_TextTypeCode")), self._key(row.get("com_TextName"))), []).append(row.get("com_TextID"))

        recorded_ids = [
            self._int(e.get("mdb_id")) or 0 for e in (session.article_map.values() if in_session else [])
        ]
        max_row = (data.get("max_article") or [{}])[0]
        next_id = max([self._int(max_row.get("max_id")) or 0, *recorded_ids]) + 1
        next_scheme = (self._int(((data.get("max_scheme") or [{}])[0]).get("max_id")) or 0) + 1
        taken_ids = set(by_id)
        updates: list[dict[str, Any]] = []
        inserts: list[dict[str, Any]] = []
        scheme_inserts: list[dict[str, Any]] = []
        new_schemes: dict[str, int] = {}
        expected: dict[str, dict[str, Any]] = {}
        warnings: list[str] = []
        skipped_ambiguous = 0
        conflicts: list[dict[str, Any]] = []
        # Link policy: in an attached production workspace an existing valid link is preserved.
        attached = in_session and is_attached(session)
        describer = LinkDescriber(data.get("relobjs", []))  # existence + names; relation info is read lazily
        scheme_rows = {str(r.get("com_CodeSchemeID")): r for r in data.get("schemes", [])}
        scheme_describer = LinkDescriber(
            [{"com_RelObjID": r.get("com_CodeSchemeID"), "com_RelObjName": r.get("com_CodeSchemeName")}
             for r in data.get("schemes", [])])

        def resolve(index: dict, key: str, label: str):
            matches = index.get(self._key(key), [])
            if len(matches) > 1:
                warnings.append(f"{label} '{key}' is ambiguous; existing article link will be preserved.")
                return None
            return matches[0] if matches else None

        for item in articles:
            code = item["code"]
            old = None
            recorded = (session.article_map.get(code) or {}).get("mdb_id") if in_session else None
            if recorded is not None:
                old = by_id.get(str(recorded))
                if old is not None and self._key(old.get("com_ArticleCode")) != self._key(code):
                    skipped_ambiguous += 1
                    warnings.append(
                        f"Article '{code}': retained id {recorded} now belongs to "
                        f"'{old.get('com_ArticleCode')}'; skipped rather than guessing.")
                    continue
            if old is None:
                matches = existing_by_code.get(self._key(code), [])
                if len(matches) > 1:
                    skipped_ambiguous += 1
                    warnings.append(f"Article '{code}' has {len(matches)} destination rows; skipped rather than guessing.")
                    continue
                old = matches[0] if matches else None
            scheme_id = resolve(scheme_by_name, item["scheme_name"], "Code Scheme")
            if (scheme_id is None and in_session
                    and not scheme_by_name.get(self._key(item["scheme_name"]))
                    and (old is None or old.get("com_CodeSchemeID") in (None, ""))):
                # Minimum supporting record for the mandatory scheme reference.
                skey = self._key(item["scheme_name"])
                if skey not in new_schemes:
                    new_schemes[skey] = next_scheme
                    scheme_inserts.append({"op": "insert", "table": self.SCHEME_TABLE, "rows": [{
                        self.SCHEME_PK: next_scheme, **scheme_proto,
                        "com_CodeSchemeName": item["scheme_name"],
                        "com_CodeSchemeBody": ",".join(["@"] * len(code)),
                        "com_PackageID": package_id,
                    }]})
                    next_scheme += 1
                scheme_id = new_schemes[skey]
            relobj_id = resolve(relobj_by_name, item["relation_name"], "Relation Object")
            short_ids = text_by_key.get(("artshort", self._key(code)), [])
            long_ids = text_by_key.get(("artlong", self._key(code)), [])
            row_values: dict[str, Any] = {
                "com_ArticleCode": code,
                "com_ArticleTypeCode": "C",
                "com_PackageID": package_id,
                "com_ComGroupID": comgroup_id,
                "com_Discountable": True,
                "com_OrderUnitCode": "C62",
            }
            if scheme_id is not None and old is not None:
                value, action = decide(old.get("com_CodeSchemeID"), scheme_id, attached=attached,
                                       replace_existing=replace_existing_links,
                                       valid=lambda v: str(v) in scheme_rows)
                row_values["com_CodeSchemeID"] = value
                if action in ("preserved", "replaced"):
                    conflicts.append(("code_scheme", f"Article '{code}'", old.get("com_CodeSchemeID"),
                                      scheme_id, action))
            elif scheme_id is not None:
                row_values["com_CodeSchemeID"] = scheme_id
            elif old is not None:
                row_values["com_CodeSchemeID"] = old.get("com_CodeSchemeID")
            else:
                row_values["com_CodeSchemeID"] = None
                warnings.append(f"Article '{code}': code scheme '{item['scheme_name']}' was not found; Text/Code Scheme workflow must resolve it.")
            if relobj_id is not None and old is not None:
                value, action = decide(old.get("com_RelObjID"), relobj_id, attached=attached,
                                       replace_existing=replace_existing_links, valid=describer.exists)
                row_values["com_RelObjID"] = value
                if action in ("preserved", "replaced"):
                    conflicts.append(("relation_object", f"Article '{code}'",
                                      old.get("com_RelObjID"), relobj_id, action))
            elif relobj_id is not None:
                row_values["com_RelObjID"] = relobj_id
            elif old is not None:
                row_values["com_RelObjID"] = old.get("com_RelObjID")
            else:
                row_values["com_RelObjID"] = None
                if not in_session:
                    warnings.append(f"Article '{code}': relation object '{item['relation_name']}' was not found; Relation Object export must resolve it.")
            # Do not create text records here. Reuse existing links if found;
            # otherwise keep the current link or leave it null for Text export.
            for column, matches_text in (("com_ShortTextID", short_ids), ("com_LongTextID", long_ids)):
                if len(matches_text) == 1:
                    row_values[column] = matches_text[0]
                elif len(matches_text) > 1:
                    warnings.append(f"Article '{code}': multiple {column} text rows found; existing link preserved.")
                    if old is not None:
                        row_values[column] = old.get(column)
                elif old is not None:
                    row_values[column] = old.get(column)
                else:
                    row_values[column] = None
            # Only write fields supported by the destination (empty prototype = unknown).
            allowed = (lambda k: k in proto) if proto else (lambda k: True)
            if old is not None:
                row_id = old.get("com_ArticleID")
                if row_id in (None, ""):
                    skipped_ambiguous += 1
                    warnings.append(f"Article '{code}': existing row has no com_ArticleID; skipped.")
                    continue
                values = {k: v for k, v in row_values.items() if allowed(k)}
                if any(old.get(k) != v for k, v in values.items()):
                    updates.append({"op": "update", "table": self.TABLE, "set": values, "where": {self.PK: row_id}})
                expected[code] = {"id": row_id, **values}
            else:
                # Reuse the id this session already issued for the code, if free.
                if recorded is not None and str(recorded) not in taken_ids:
                    row_id = self._int(recorded)
                else:
                    row_id = next_id
                    next_id += 1
                taken_ids.add(str(row_id))
                values = {k: v for k, v in row_values.items() if allowed(k)}
                if not in_session and self.PK not in proto and not any(k == self.PK for k in data["article_proto"][0]):
                    return {"ok": False, "error": "Destination article schema has no com_ArticleID primary key."}
                inserts.append({"op": "insert", "table": self.TABLE, "rows": [{self.PK: row_id, **proto, **values}]})
                expected[code] = {"id": row_id, **values}

        if conflicts:
            # Relation information (relation name / type / domain) is only needed to describe a conflict, so it
            # is read here, once, and its absence (a minimal schema) only reduces the description.
            try:
                extra = db.read_tables(mdb, {
                    "relobj_links": (
                        "SELECT com_RelObjID, com_RelationID, com_RelObjTypeCode, com_RelObjDomainCode, "
                        "com_RelationOrder FROM [tCOMd_RelObjRel]"
                    ),
                    "relations": "SELECT com_RelationID, com_RelationName FROM [tCOMd_Relation]",
                }) if callable(getattr(db, "read_tables", None)) else {}
            except Exception:
                extra = {}
            describer = LinkDescriber(data.get("relobjs", []), extra.get("relobj_links", []), extra.get("relations", []))
            conflicts = [
                conflict_entry(kind, entity, existing, incoming, action,
                               scheme_describer if kind == "code_scheme" else describer,
                               "com_CodeSchemeID" if kind == "code_scheme" else "com_RelObjID")
                for kind, entity, existing, incoming, action in conflicts
            ]
        warnings.extend(conflict_message(entry) for entry in conflicts)
        plan = scheme_inserts + updates + inserts
        result = {
            "conflicts": conflicts,
            "links_preserved": sum(1 for entry in conflicts if entry["action"] == "preserved"),
            "ok": True, "dry_run": dry_run, "inserted": len(inserts),
            "updated": len(updates), "unchanged": len(articles) - len(inserts) - len(updates) - skipped_ambiguous,
            "skipped_ambiguous": skipped_ambiguous, "warnings": warnings,
            "articles": len(articles), "mdb_path": str(mdb),
            "schemes_created": len(scheme_inserts),
        }
        result["skipped"] = result["unchanged"] + skipped_ambiguous

        def retained() -> dict[str, Any]:
            """Identity maps handed back for the session to persist."""
            amap = {}
            for item in articles:
                if item["code"] not in expected:
                    continue
                prior = (session.article_map.get(item["code"]) if in_session else None) or {}
                amap[item["code"]] = {
                    "mdb_id": expected[item["code"]]["id"],
                    "source_ids": sorted({*prior.get("source_ids", []), *item["source_ids"]}),
                    "source_codes": sorted({*prior.get("source_codes", []), *item["source_codes"]}),
                }
            return {"_article_map": amap,
                    "_scheme_map": {name: sid for name, sid in
                                    ((s["rows"][0]["com_CodeSchemeName"], s["rows"][0][self.SCHEME_PK])
                                     for s in scheme_inserts)}}

        if dry_run:
            return result
        if not plan:
            return {**result, **retained()} if in_session else result
        batch = db.execute_batch(mdb, plan, transaction=True)
        if not batch.ok:
            return {**result, "ok": False, "error": batch.first_error() or "Article MDB transaction failed."}

        # Verify each changed row by natural key and primary key after commit.
        codes = list(expected)
        sql_codes = ", ".join("'" + c.replace("'", "''") + "'" for c in codes) or "NULL"
        try:
            readback = db.read_table(
                mdb,
                "SELECT com_ArticleID, com_ArticleCode, com_PackageID, com_ComGroupID, "
                "com_CodeSchemeID, com_RelObjID, com_ShortTextID, com_LongTextID "
                "FROM [tCOMd_Article] WHERE com_ArticleCode IN (" + sql_codes + ")",
            )
        except Exception as exc:
            return {**result, "ok": False, "error": f"Article export wrote data but read-back failed: {exc}"}
        by_code = {self._key(row.get("com_ArticleCode")): row for row in readback}
        failures = []
        for code, want in expected.items():
            got = by_code.get(self._key(code))
            if got is None or str(got.get("com_ArticleID")) != str(want["id"]):
                failures.append(f"{code}: article row/id not found after write")
                continue
            for field in ("com_PackageID", "com_ComGroupID", "com_CodeSchemeID", "com_RelObjID", "com_ShortTextID", "com_LongTextID"):
                if field in want and str(got.get(field) or "") != str(want.get(field) or ""):
                    failures.append(f"{code}: {field} did not match intended value")
        if failures:
            return {**result, "ok": False, "error": "Article read-back validation failed: " + "; ".join(failures[:12])}
        result["verified"] = len(expected)
        return {**result, **retained()} if in_session else result
