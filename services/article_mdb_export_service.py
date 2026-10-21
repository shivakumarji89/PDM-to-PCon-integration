"""Non-destructive Maintenance Article export into an existing OCD MDB.

Article rows are matched by base article code. Existing primary keys and
unrelated columns are preserved. Text rows are owned by the Text workflow:
this exporter only reuses existing text IDs and leaves missing links empty for
the later Text export to resolve.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from models.snapshot import Snapshot
from services.base_service import BaseService


class ArticleMdbExportService(BaseService):
    """Upsert Maintenance base-article records without rebuilding the MDB."""

    TABLE = "tCOMd_Article"
    PK = "com_ArticleID"

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

    def _base_articles(self, snapshot: Snapshot) -> list[dict[str, Any]]:
        articles = {str(a.id): a for a in snapshot.articles if a.id is not None}
        unique: dict[str, dict[str, Any]] = {}
        for family in getattr(snapshot.engineering, "families", []) or []:
            for member in getattr(family, "members", []) or []:
                article = articles.get(str(getattr(member, "article_id", "")))
                if article is None or not str(article.code or "").strip():
                    continue
                code = str(getattr(member, "reduced_article", "") or "").strip()
                if not code:
                    source_code = str(article.code).strip()
                    code = source_code[:source_code.find(".")] if "." in source_code else source_code
                if not code:
                    continue
                # One MDB base-article row per base code. The first member is
                # representative; conflicting metadata is surfaced as a warning.
                entry = unique.setdefault(code, {
                    "code": code,
                    "relation_name": str(getattr(member, "relation_object", "") or "").strip()
                                     or f"P_{code}",
                    "scheme_name": str(getattr(member, "code_scheme", "") or "").strip() or code,
                    "short_text": str(getattr(member, "short_description", "") or "").strip(),
                    "long_text": str(getattr(member, "long_description", "") or "").strip(),
                    "member_ids": [],
                })
                entry["member_ids"].append(str(getattr(member, "id", "") or ""))
                for field, attr in (("relation_name", "relation_object"), ("scheme_name", "code_scheme"),
                                    ("short_text", "short_description"), ("long_text", "long_description")):
                    value = str(getattr(member, attr, "") or "").strip()
                    if value and not entry[field]:
                        entry[field] = value
        return list(unique.values())

    def export(self, snapshot: Snapshot, mdb_path: str | Path, dry_run: bool = False) -> dict[str, Any]:
        mdb = Path(mdb_path)
        if not mdb.is_file():
            return {"ok": False, "error": "Select an existing OCD MDB file."}
        if snapshot is None or snapshot.product is None:
            return {"ok": False, "error": "Load a product before exporting Articles."}
        articles = self._base_articles(snapshot)
        if not articles:
            return {"ok": False, "error": "No reduced Base Articles found. Apply the article reduction first."}
        db = self.context.mdb_service
        if not db.is_available():
            return {"ok": False, "error": "32-bit PowerShell / ACE bridge unavailable."}

        queries = {
            "article_proto": "SELECT TOP 1 * FROM [tCOMd_Article]",
            "articles": "SELECT * FROM [tCOMd_Article]",
            "package": "SELECT TOP 1 com_PackageID, com_ComGroupID FROM [tCOMd_Package]",
            "group": "SELECT TOP 1 com_ComGroupID FROM [tCOMd_ComGroup]",
            "schemes": "SELECT com_CodeSchemeID, com_CodeSchemeName, com_PackageID FROM [tCOMd_CodeScheme]",
            "relobjs": "SELECT com_RelObjID, com_RelObjName, com_PackageID FROM [tCOMd_RelObj]",
            "texts": "SELECT com_TextID, com_TextName, com_TextTypeCode, com_PackageID FROM [tCOMd_Text]",
            "max_article": "SELECT MAX(com_ArticleID) AS max_id FROM [tCOMd_Article]",
        }
        try:
            data = db.read_tables(mdb, queries) if callable(getattr(db, "read_tables", None)) else {
                name: db.read_table(mdb, sql) for name, sql in queries.items()
            }
        except Exception as exc:
            return {"ok": False, "error": f"Could not read destination MDB: {exc}"}
        proto = self._prototype(data.get("article_proto", []))
        if not proto:
            return {"ok": False, "error": "Could not read tCOMd_Article schema from the destination MDB."}
        package = (data.get("package") or [{}])[0]
        package_id = package.get("com_PackageID")
        comgroup_id = package.get("com_ComGroupID")
        if package_id in (None, ""):
            return {"ok": False, "error": "Destination MDB has no package row; Article export cannot safely assign package IDs."}
        if comgroup_id in (None, "") and data.get("group"):
            comgroup_id = data["group"][0].get("com_ComGroupID")

        existing_by_code: dict[str, list[dict[str, Any]]] = {}
        for row in data.get("articles", []):
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

        max_row = (data.get("max_article") or [{}])[0]
        next_id = (self._int(max_row.get("max_id")) or 0) + 1
        updates: list[dict[str, Any]] = []
        inserts: list[dict[str, Any]] = []
        expected: dict[str, dict[str, Any]] = {}
        warnings: list[str] = []
        skipped_ambiguous = 0

        def resolve(index: dict, key: str, label: str):
            matches = index.get(self._key(key), [])
            if len(matches) > 1:
                warnings.append(f"{label} '{key}' is ambiguous; existing article link will be preserved.")
                return None
            return matches[0] if matches else None

        for item in articles:
            code = item["code"]
            matches = existing_by_code.get(self._key(code), [])
            if len(matches) > 1:
                skipped_ambiguous += 1
                warnings.append(f"Article '{code}' has {len(matches)} destination rows; skipped rather than guessing.")
                continue
            old = matches[0] if matches else None
            scheme_id = resolve(scheme_by_name, item["scheme_name"], "Code Scheme")
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
            if scheme_id is not None:
                row_values["com_CodeSchemeID"] = scheme_id
            elif old is not None:
                row_values["com_CodeSchemeID"] = old.get("com_CodeSchemeID")
            else:
                row_values["com_CodeSchemeID"] = None
                warnings.append(f"Article '{code}': code scheme '{item['scheme_name']}' was not found; Text/Code Scheme workflow must resolve it.")
            if relobj_id is not None:
                row_values["com_RelObjID"] = relobj_id
            elif old is not None:
                row_values["com_RelObjID"] = old.get("com_RelObjID")
            else:
                row_values["com_RelObjID"] = None
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
            if old is not None:
                row_id = old.get("com_ArticleID")
                if row_id in (None, ""):
                    skipped_ambiguous += 1
                    warnings.append(f"Article '{code}': existing row has no com_ArticleID; skipped.")
                    continue
                # Only write fields supported by the actual destination prototype.
                values = {k: v for k, v in row_values.items() if k in proto}
                if any(old.get(k) != v for k, v in values.items()):
                    updates.append({"op": "update", "table": self.TABLE, "set": values, "where": {self.PK: row_id}})
                expected[code] = {"id": row_id, **values}
            else:
                row_id = next_id
                next_id += 1
                values = {k: v for k, v in row_values.items() if k in proto}
                if self.PK not in proto and not any(k == self.PK for k in data["article_proto"][0]):
                    return {"ok": False, "error": "Destination article schema has no com_ArticleID primary key."}
                inserts.append({"op": "insert", "table": self.TABLE, "rows": [{self.PK: row_id, **proto, **values}]})
                expected[code] = {"id": row_id, **values}

        plan = updates + inserts
        result = {
            "ok": True, "dry_run": dry_run, "inserted": len(inserts),
            "updated": len(updates), "unchanged": len(articles) - len(inserts) - len(updates) - skipped_ambiguous,
            "skipped_ambiguous": skipped_ambiguous, "warnings": warnings,
            "articles": len(articles), "mdb_path": str(mdb),
        }
        if dry_run or not plan:
            return result
        batch = db.execute_batch(mdb, plan, transaction=True)
        if not batch.ok:
            return {"ok": False, "error": batch.first_error() or "Article MDB transaction failed.", **result}

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
            return {"ok": False, "error": f"Article export wrote data but read-back failed: {exc}", **result}
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
            return {"ok": False, "error": "Article read-back validation failed: " + "; ".join(failures[:12]), **result}
        result["verified"] = len(expected)
        return result
