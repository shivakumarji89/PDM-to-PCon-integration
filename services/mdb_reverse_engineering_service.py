"""Read an existing OCD MDB into a structured, maintenance-friendly model.

This service deliberately sits *above* :class:`MDBService`.  MDBService remains
our only low-level MDB I/O gateway; this module owns only the domain-level
selection, normalization, and relationship indexing needed by Maintenance and
future Metatype work.

The reader is intentionally non-mutating.  It never writes to the MDB and it
keeps pricing out of the generic structural read path.  Price data can be read
explicitly through ``include_prices`` so callers do not accidentally treat
pricing as ordinary product structure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from datetime import datetime, timedelta

from models.article import Article
from models.engineering_class import ClassPropertyAssignment, ClassValue, EngineeringClass
from models.product import Product
from models.property import Property
from models.property_value import PropertyValue
from models.price_list import PriceList
from models.price_record import PriceRecord
from models.relation_object import RelationObject
from models.snapshot import Snapshot
from models.text_block import TextBlock

from services.base_service import BaseService


# Product/engineering tables already used by OcdExportService.  Keep this list
# centralized so Maintenance and Metatype consume the same structural scope.
STRUCTURAL_TABLES: tuple[str, ...] = (
    "tCOMd_Text",
    "tCOMd_RelObj",
    "tCOMd_Relation",
    "tCOMd_CodeScheme",
    "tCOMd_Class",
    "tCOMd_Property",
    "tCOMd_PropValue",
    "tCOMd_Article",
    "tCOMd_ArticleClass",
    "tCOMd_ArtBase",
    "tCOMd_RelObjRel",
    "tCOMd_Table",
    "tCOMd_TableColumn",
    "tCOMd_TableLine",
)

PRICE_TABLES: tuple[str, ...] = (
    "tCOMd_PriceList2",
    "tCOMd_Price",
    "tCOMd_GlobalPrice",
)

PACKAGE_TABLES: tuple[str, ...] = (
    "tCOMd_Package",
    "tCOMd_ComGroup",
)

READABLE_TABLES = frozenset(PACKAGE_TABLES + STRUCTURAL_TABLES + PRICE_TABLES)


@dataclass(frozen=True)
class MdbTableData:
    """Rows read from one MDB table."""

    name: str
    rows: tuple[dict[str, Any], ...] = ()

    @property
    def count(self) -> int:
        return len(self.rows)

    @property
    def columns(self) -> tuple[str, ...]:
        if not self.rows:
            return ()
        # Preserve the column order returned by Access for stable diagnostics.
        return tuple(self.rows[0].keys())


@dataclass
class MdbPackageData:
    """Non-mutating structural snapshot of an existing OCD MDB."""

    path: str
    package: dict[str, Any] | None = None
    com_group: dict[str, Any] | None = None
    tables: dict[str, MdbTableData] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def table_counts(self) -> dict[str, int]:
        return {name: table.count for name, table in self.tables.items()}

    def rows(self, table: str) -> tuple[dict[str, Any], ...]:
        data = self.tables.get(table)
        return data.rows if data else ()

    def first(self, table: str) -> dict[str, Any] | None:
        rows = self.rows(table)
        return rows[0] if rows else None


class MdbReverseEngineeringService(BaseService):
    """Read and normalize an existing OCD MDB without modifying it.

    The service uses ``context.mdb_service`` for every database operation.  It
    therefore does not introduce another OLEDB/PowerShell connection or another
    MDB abstraction.
    """

    def read(
        self,
        mdb_path: str | Path,
        *,
        include_prices: bool = False,
        tables: Iterable[str] | None = None,
    ) -> MdbPackageData:
        """Read the selected OCD tables from ``mdb_path``.

        By default only package metadata and structural/engineering tables are
        loaded.  Pricing is opt-in because it has its own maintenance pipeline.
        ``tables`` may narrow the read to a specific allow-listed set.
        """
        path = Path(mdb_path)
        result = MdbPackageData(path=str(path))

        if not path.is_file():
            result.notes.append(f"MDB not found: {path}")
            return result

        requested = tuple(tables) if tables is not None else (
            STRUCTURAL_TABLES + (PRICE_TABLES if include_prices else ())
        )
        invalid = [table for table in requested if table not in READABLE_TABLES]
        if invalid:
            raise ValueError(f"Unsupported MDB table(s): {', '.join(invalid)}")

        # Read the complete requested structural scope in one MDB/ADODB
        # session.  The bridge is comparatively expensive to start, so doing
        # one process per table makes large MDB imports unnecessarily slow.
        table_names = ("tCOMd_Package", "tCOMd_ComGroup") + tuple(requested)
        sql_by_name = {
            table: f"SELECT * FROM [{table}]"
            for table in dict.fromkeys(table_names)
        }
        rows_by_table = self.context.mdb_service.read_tables(path, sql_by_name)

        package_rows = rows_by_table.get("tCOMd_Package", [])
        group_rows = rows_by_table.get("tCOMd_ComGroup", [])
        result.package = package_rows[0] if package_rows else None
        result.com_group = group_rows[0] if group_rows else None

        if result.package is None:
            result.notes.append("tCOMd_Package is empty.")
        if result.com_group is None:
            result.notes.append("tCOMd_ComGroup is empty.")

        for table in requested:
            result.tables[table] = MdbTableData(
                name=table,
                rows=tuple(rows_by_table.get(table, [])),
            )

        return result

    def import_snapshot(self, data: MdbPackageData) -> Snapshot:
        """Map an extracted OCD MDB into the same Snapshot consumed by all workflows."""
        package = data.package or {}
        program = str(package.get("reg_ProgramCode") or "").strip()
        label = str(package.get("reg_ProgramLabel") or "").strip()
        product = Product(
            id=f"mdb:package:{package.get('com_PackageID', program)}",
            code=program,
            name=label or program,
            description=label,
            range_name=program,
            status="MDB",
        )
        snapshot = Snapshot(product=product)
        snapshot.metadata.source = "MDB"
        snapshot.metadata.product_code = program
        snapshot.metadata.notes = f"Imported from {data.path}"

        # Discover every language column exposed by this MDB instead of
        # assuming the legacy four-language set. Access returns the actual
        # columns through the shared MDB reader, so no language list is hard-coded.
        text_rows = data.rows("tCOMd_Text")
        language_columns = {
            str(column)[len("com_Text_1_"):].strip().lower(): str(column)
            for row in text_rows
            for column in row.keys()
            if str(column).lower().startswith("com_text_1_")
            and str(column)[len("com_Text_1_"):].strip()
        }
        text_by_id: dict[str, TextBlock] = {}
        for row in text_rows:
            tid = str(row.get("com_TextID") or "")
            if not tid:
                continue
            type_code = str(row.get("com_TextTypeCode") or "").strip()
            translations = {
                language: str(row.get(column) or "")
                for language, column in language_columns.items()
            }
            text_by_id[tid] = TextBlock(
                name=str(row.get("com_TextName") or ""),
                type_code=type_code,
                de=translations.get("de", ""),
                en=translations.get("en", ""),
                fr=translations.get("fr", ""),
                nl=translations.get("nl", ""),
                translations=translations,
            )
        snapshot.text_blocks = list(text_by_id.values())

        class_by_mdb: dict[str, EngineeringClass] = {}
        for row in data.rows("tCOMd_Class"):
            cid = str(row.get("com_ClassID") or "")
            name = str(row.get("com_ClassName") or "").strip()
            if not cid or not name:
                continue
            cls = EngineeringClass(id=f"mdb:class:{cid}", name=name)
            class_by_mdb[cid] = cls
            snapshot.engineering.classes.append(cls)

        prop_by_mdb: dict[str, Property] = {}
        for row in data.rows("tCOMd_Property"):
            pid = str(row.get("com_PropertyID") or "")
            name = str(row.get("com_PropName") or "").strip()
            if not pid or not name:
                continue
            prop = Property(
                id=f"mdb:property:{pid}",
                code=name,
                name=name,
                data_type=str(row.get("com_PropTypeCode") or ""),
                display_order=int(row.get("com_PropPosition") or 0),
            )
            prop_by_mdb[pid] = prop
            snapshot.properties.append(prop)
            cls = class_by_mdb.get(str(row.get("com_ClassID") or ""))
            if cls is not None:
                scope = str(row.get("com_PropScopeCode") or "").upper()
                text = text_by_id.get(str(row.get("com_TextID") or ""))
                cls.properties.append(ClassPropertyAssignment(
                    property_id=prop.id or "",
                    property_name=prop.name,
                    width=int(row.get("com_PropDigits") or 0),
                    placement=max(0, int(row.get("com_PropPosition") or 100) - 100),
                    type=(str(row.get("com_PropTypeCode") or "C")[:1] or "C"),
                    usage="Graphic" if scope == "RG" else "Configuration",
                    text_block=text.name if text else "",
                ))

        value_by_mdb: dict[str, PropertyValue] = {}
        for row in data.rows("tCOMd_PropValue"):
            vid = str(row.get("com_ValueID") or "")
            parent = str(row.get("com_PropertyID") or "")
            if not vid or parent not in prop_by_mdb:
                continue
            text = text_by_id.get(str(row.get("com_TextID") or ""))
            code = str(row.get("com_PropValueFrom") or "").strip()
            value_text = (text.en if text else "") or (text.de if text else "") or code
            value = PropertyValue(
                id=f"mdb:value:{vid}",
                property_id=prop_by_mdb[parent].id,
                value=value_text,
                code=code,
                display_order=int(row.get("com_PropValPosition") or 0),
            )
            value_by_mdb[vid] = value
            prop_by_mdb[parent].values.append(value)
            snapshot.property_values.append(value)

        for cls in snapshot.engineering.classes:
            for assignment in cls.properties:
                prop = next((p for p in snapshot.properties if p.id == assignment.property_id), None)
                assignment.values = [
                    ClassValue(value_id=str(v.id or ""), code=v.code or "",
                               value=v.value or "", source="mdb")
                    for v in (prop.values if prop else [])
                ]

        # Repository code schemes define how each base article's variant code
        # is assembled. Keep the source definition in the Snapshot so later
        # permutation generation never needs to reopen the MDB.
        for row in data.rows("tCOMd_CodeScheme"):
            scheme_id = str(row.get("com_CodeSchemeID") or "").strip()
            if not scheme_id:
                continue
            snapshot.code_schemes[scheme_id] = {
                "name": str(row.get("com_CodeSchemeName") or "").strip(),
                "body": str(row.get("com_CodeSchemeBody") or "").strip(),
            }

        article_by_mdb: dict[str, Article] = {}
        for row in data.rows("tCOMd_Article"):
            aid = str(row.get("com_ArticleID") or "")
            code = str(row.get("com_ArticleCode") or "").strip()
            if not aid or not code:
                continue
            short = text_by_id.get(str(row.get("com_ShortTextID") or ""))
            long = text_by_id.get(str(row.get("com_LongTextID") or ""))
            article = Article(
                id=f"mdb:article:{aid}", product_id=product.id, code=code,
                name=(short.en if short else "") or code,
                description=(long.en if long else "") or (short.en if short else ""),
                source="MDB",
            )
            article_by_mdb[aid] = article
            snapshot.articles.append(article)
            product.articles.append(article)
            scheme_id = str(row.get("com_CodeSchemeID") or "").strip()
            if scheme_id:
                snapshot.article_code_scheme_ids[article.id] = scheme_id

        # Base Article -> PropertyClass membership is the other half of the
        # repository configuration model. Keep every ArticleClass link; the
        # permutation builder uses the linked class properties as dimensions.
        for row in data.rows("tCOMd_ArticleClass"):
            article_row_id = str(row.get("com_ArticleID") or "").strip()
            class_row_id = str(row.get("com_ClassID") or "").strip()
            if article_row_id.endswith(".0"):
                article_row_id = article_row_id[:-2]
            if class_row_id.endswith(".0"):
                class_row_id = class_row_id[:-2]
            if article_row_id and class_row_id:
                article_key = f"mdb:article:{article_row_id}"
                class_key = f"mdb:class:{class_row_id}"
                snapshot.article_class_ids.setdefault(article_key, []).append(class_key)

        # Resolve the MDB relationship chain strictly through stored IDs.
        #
        #   tCOMd_RelObj.com_RelObjID
        #       -> tCOMd_RelObjRel.com_RelObjID
        #       -> tCOMd_RelObjRel.com_RelationID
        #       -> tCOMd_Relation.com_RelationID
        #
        # Property/value bindings use their own RelObjID foreign key:
        #
        #   tCOMd_Property.com_RelObjID  -> tCOMd_RelObj.com_RelObjID
        #   tCOMd_PropValue.com_RelObjID -> tCOMd_RelObj.com_RelObjID
        #
        # Never assume RelObjID == RelationID. Keep every RelObjRel row so
        # multiple relation links on one relation object are not lost.
        def _mdb_id(value: Any) -> str:
            if value is None:
                return ""
            text = str(value).strip()
            if not text:
                return ""
            # Access/ADO may expose an integer key as 125.0.
            if text.endswith(".0"):
                try:
                    return str(int(float(text)))
                except (TypeError, ValueError):
                    pass
            return text

        relation_by_id = {
            _mdb_id(r.get("com_RelationID")): r
            for r in data.rows("tCOMd_Relation")
            if _mdb_id(r.get("com_RelationID"))
        }
        relobj_by_id = {
            _mdb_id(r.get("com_RelObjID")): r
            for r in data.rows("tCOMd_RelObj")
            if _mdb_id(r.get("com_RelObjID"))
        }

        relmeta_by_obj: dict[str, list[dict[str, Any]]] = {}
        for row in data.rows("tCOMd_RelObjRel"):
            obj_id = _mdb_id(row.get("com_RelObjID"))
            relation_id = _mdb_id(row.get("com_RelationID"))
            if not obj_id or not relation_id:
                continue
            relmeta_by_obj.setdefault(obj_id, []).append(row)

        prop_relobj: dict[str, list[str]] = {}
        for row in data.rows("tCOMd_Property"):
            obj_id = _mdb_id(row.get("com_RelObjID"))
            prop_id = _mdb_id(row.get("com_PropertyID"))
            if obj_id and prop_id:
                prop_relobj.setdefault(obj_id, []).append(prop_id)

        value_relobj: dict[str, list[str]] = {}
        for row in data.rows("tCOMd_PropValue"):
            obj_id = _mdb_id(row.get("com_RelObjID"))
            value_id = _mdb_id(row.get("com_ValueID"))
            if obj_id and value_id:
                value_relobj.setdefault(obj_id, []).append(value_id)

        for obj_id, obj_row in relobj_by_id.items():
            property_ids = prop_relobj.get(obj_id, [])
            value_ids = value_relobj.get(obj_id, [])

            for meta in relmeta_by_obj.get(obj_id, []):
                relation_id = _mdb_id(meta.get("com_RelationID"))
                rel = relation_by_id.get(relation_id)
                if rel is None:
                    continue

                property_id = next(
                    (prop_by_mdb[pid].id for pid in property_ids if pid in prop_by_mdb),
                    "",
                )
                value_id = next(
                    (value_by_mdb[vid].id for vid in value_ids if vid in value_by_mdb),
                    "",
                )

                snapshot.relation_objects.append(RelationObject(
                    name=str(obj_row.get("com_RelObjName") or ""),
                    type_code=str(meta.get("com_RelObjTypeCode") or "1"),
                    domain=str(meta.get("com_RelObjDomainCode") or "C"),
                    order=int(meta.get("com_RelationOrder") or 100),
                    body=str(rel.get("com_RelationBody") or ""),
                    property_id=property_id,
                    value_id=value_id,
                    rel_obj_id=obj_id,
                    relation_id=relation_id,
                    relation_name=str(rel.get("com_RelationName") or ""),
                ))

        # ArtBase is the MDB's base-article restriction model. Keep it in
        # Snapshot so the existing Review/engineering workflows can consume the
        # same base -> property -> value restriction information.
        value_by_code: dict[tuple[str, str], str] = {}
        for value in snapshot.property_values:
            value_by_code[(str(value.property_id), value.code)] = str(value.id or "")
        for row in data.rows("tCOMd_ArtBase"):
            article_row_id = str(row.get("com_ArticleID") or "")
            article = article_by_mdb.get(article_row_id)
            if article is None:
                continue
            class_name = str(row.get("com_ClassName") or "")
            prop_name = str(row.get("com_PropName") or "").strip()
            code = str(row.get("com_PropValue") or "").strip()
            prop = next(
                (p for p in snapshot.properties
                 if p.name == prop_name or p.code == prop_name),
                None,
            )
            if prop is None:
                # ArtBase property names are normalized identifiers; compare
                # case-insensitively only as a mapping aid, never inventing a property.
                prop = next(
                    (p for p in snapshot.properties
                     if p.name.casefold() == prop_name.casefold()
                     or p.code.casefold() == prop_name.casefold()),
                    None,
                )
            if prop is None:
                continue
            value_id = value_by_code.get((str(prop.id), code), "")
            if not value_id:
                continue
            snapshot.art_base.setdefault(article.code, {}).setdefault(
                str(prop.id), []
            ).append(value_id)

        for row in data.rows("tCOMd_PriceList2"):
            snapshot.price_lists.append(PriceList(
                id=str(row.get("com_PriceListID") or ""),
                label=str(row.get("com_PriceListLabel") or ""),
                currency=str(row.get("sys_ISOCurrencyCode") or ""),
                date_from=self._mdb_date(row.get("com_PriceValidFrom")),
                date_to=self._mdb_date(row.get("com_PriceValidTo")),
            ))
        article_code_by_id = {aid: article.code for aid, article in article_by_mdb.items()}
        for row in data.rows("tCOMd_Price"):
            snapshot.price_records.append(PriceRecord(
                is_global=False,
                article_code=article_code_by_id.get(str(row.get("com_ArticleID") or ""), ""),
                variant_condition=str(row.get("com_VariantCondition") or ""),
                level=str(row.get("com_PriceLevelCode") or "B"),
                value=float(row.get("com_PriceValue") or 0),
                currency=str(row.get("sys_ISOCurrencyCode") or ""),
                valid_from=self._mdb_date(row.get("com_PriceValidFrom")),
                valid_to=self._mdb_date(row.get("com_PriceValidTo")),
            ))
        for row in data.rows("tCOMd_GlobalPrice"):
            snapshot.price_records.append(PriceRecord(
                is_global=True,
                variant_condition=str(row.get("com_VariantCondition") or ""),
                level=str(row.get("com_PriceLevelCode") or "B"),
                value=float(row.get("com_PriceValue") or 0),
                currency=str(row.get("sys_ISOCurrencyCode") or ""),
                valid_from=self._mdb_date(row.get("com_PriceValidFrom")),
                valid_to=self._mdb_date(row.get("com_PriceValidTo")),
            ))
        return snapshot

    @staticmethod
    def _mdb_date(value: Any) -> str:
        raw = str(value or "")
        if "/Date(" in raw:
            import re
            match = re.search(r"-?\d+", raw)
            if match:
                try:
                    return (datetime(1970, 1, 1) + timedelta(milliseconds=int(match.group(0)))).strftime("%Y%m%d")
                except (ValueError, OverflowError):
                    pass
        digits = "".join(ch for ch in raw if ch.isdigit())
        return digits[:8] if len(digits) >= 8 else ""

    def read_table(self, mdb_path: str | Path, table: str) -> MdbTableData:
        """Read one allow-listed table through the shared MDB service."""
        self._validate_table(table)
        rows = self._read(Path(mdb_path), table)
        return MdbTableData(name=table, rows=tuple(rows))

    def inspect_schema(self, mdb_path: str | Path, table: str) -> tuple[str, ...]:
        """Return the columns present in a live MDB table.

        This is intentionally implemented as ``SELECT TOP 1 *`` rather than a
        second schema/ADO abstraction, keeping all MDB access in MDBService.
        Empty tables cannot expose columns through the current MDBService API;
        in that case an empty tuple is returned.
        """
        return self.read_table(mdb_path, table).columns

    def table_counts(
        self,
        mdb_path: str | Path,
        *,
        include_prices: bool = False,
    ) -> dict[str, int]:
        """Return row counts using the same structural scope as ``read``."""
        data = self.read(mdb_path, include_prices=include_prices)
        return data.table_counts

    def _read(self, path: Path, table: str) -> list[dict[str, Any]]:
        self._validate_table(table)
        # Table names are constants from READABLE_TABLES, never user-supplied
        # SQL fragments.  Brackets protect Access identifiers safely.
        return self.context.mdb_service.read_table(
            path,
            f"SELECT * FROM [{table}]",
        )

    @staticmethod
    def _validate_table(table: str) -> None:
        if table not in READABLE_TABLES:
            raise ValueError(f"Unsupported MDB table: {table}")
