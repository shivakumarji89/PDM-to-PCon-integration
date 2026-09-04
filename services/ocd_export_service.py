"""Direct OCD MDB (``tCOMd_*``) exporter.

A **parallel** export path to :class:`~services.xocd_export_service.XocdExportService`:
where the XOCD writer emits a name-keyed CSV package for the pCon.creator OCD
Import module, this writer produces a finished ``pcr_data_com_ocd.mdb`` directly
- the COM database creator uses internally.

It mirrors the manual authoring workflow: copy a category template, wipe the
example-product rows, and insert the snapshot's data into the ``tCOMd_*`` tables
(all writes delegated to the 32-bit ADODB bridge via :class:`MDBService`). Ids
are integer surrogate keys assigned here; foreign keys are computed up front.

This module is self-contained so it can be removed in one step if the XOCD path
is the only one adopted: delete this file, its ``application_context`` property,
and the ``Export MDB (Direct)`` menu action. Nothing else depends on it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from models.snapshot import Snapshot
from services.base_service import BaseService
from services.engineering.engineering_reduction_service import collapse_duplicate_values
from services.engineering.engineering_text_service import text_block_name
from services.price_update_service import _mdb_date_literal
from services.xocd_export_service import XocdExportService

#: Broad "always valid" fallback window (YYYYMMDD) when neither the price list
#: nor the record carries dates.
_DATE_MIN = "20200101"
_DATE_MAX = "99991231"

#: Category templates (the "copy, wipe, hand-enter" starting points).
_TEMPLATE_ROOT = Path(r"C:\HermanMillerOFMLSVN\Staging\HermanMiller_old\WS\1_WS_Templates")
_TEMPLATES = {
    "seating": _TEMPLATE_ROOT / "Seating_Template" / "pcr_data_com_ocd.mdb",
    "tables": _TEMPLATE_ROOT / "Tables_Template" / "pcr_data_com_ocd.mdb",
}
#: Keywords in a product's category/range/name that select the Tables template.
_TABLES_KEYWORDS = ("desk", "table", "bench", "worksurface", "credenza", "storage")

#: Languages carried on ``tCOMd_Text`` (one column each).
_TEXT_LANGS = ("de", "en", "fr", "nl")

#: OCD unifies options into properties, so option text is stored under the
#: property text types (golden has no ``option``/``optionvalue`` type codes).
_TEXT_TYPE_OCD = {"option": "property", "optionvalue": "propvalue"}

#: The example-product tables to wipe, ordered children-first so referential
#: integrity holds during the delete.
_PRODUCT_TABLES = [
    "tCOMd_Price", "tCOMd_GlobalPrice",
    "tCOMd_TableLine", "tCOMd_TableColumn", "tCOMd_Table",
    "tCOMd_RelObjRel", "tCOMd_ArtBase", "tCOMd_ArticleClass",
    "tCOMd_PropValue", "tCOMd_Property", "tCOMd_Article", "tCOMd_Class",
    "tCOMd_Relation", "tCOMd_RelObj", "tCOMd_CodeScheme", "tCOMd_Text",
]

#: Autonumber primary key per table (dropped from a prototype row, set explicitly).
_PK = {
    "tCOMd_Text": "com_TextID", "tCOMd_Class": "com_ClassID",
    "tCOMd_Property": "com_PropertyID", "tCOMd_PropValue": "com_ValueID",
    "tCOMd_Article": "com_ArticleID", "tCOMd_ArticleClass": "com_ArticleClassID",
    "tCOMd_ArtBase": "com_ArtBaseID", "tCOMd_RelObj": "com_RelObjID",
    "tCOMd_Relation": "com_RelationID", "tCOMd_RelObjRel": "com_RelObjRelID",
    "tCOMd_CodeScheme": "com_CodeSchemeID", "tCOMd_Table": "com_TableID",
    "tCOMd_TableColumn": "com_TableColumnID", "tCOMd_TableLine": "com_TableLineID",
    "tCOMd_Price": "com_PriceID", "tCOMd_GlobalPrice": "com_GlobalPriceID",
}


@dataclass
class OcdExportResult:
    """Outcome of a direct MDB export."""

    ok: bool = False
    mdb_path: str = ""
    template: str = ""
    table_counts: dict[str, int] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)
    error: str | None = None


class OcdExportService(BaseService):
    """Writes a snapshot straight into a template ``pcr_data_com_ocd.mdb``."""

    # -- Public entry point ---------------------------------------------

    def export(
        self, snapshot: Snapshot, dest: str | Path, template_kind: str | None = None
    ) -> OcdExportResult:
        """Export ``snapshot`` into a copied template MDB at ``dest``.

        ``dest`` may be the target ``.mdb`` file or a folder (the standard
        ``pcr_data_com_ocd.mdb`` is then written inside it). ``template_kind`` is
        ``'seating'``/``'tables'``; when omitted it is inferred from the product.
        """
        result = OcdExportResult()
        if snapshot.product is None:
            result.error = "No product loaded."
            return result

        mdb_svc = self.context.mdb_service
        if not mdb_svc.is_available():
            result.error = "32-bit PowerShell / ACE OLEDB bridge unavailable."
            return result

        kind = (template_kind or self._infer_template(snapshot.product)).lower()
        template = _TEMPLATES.get(kind)
        if template is None or not template.is_file():
            result.error = f"Template not found for '{kind}': {template}"
            return result
        result.template = kind

        mdb = Path(dest)
        if mdb.suffix.lower() != ".mdb":
            mdb = mdb / "pcr_data_com_ocd.mdb"
        result.mdb_path = str(mdb)

        try:
            mdb_svc.copy_template(template, mdb)
        except OSError as exc:
            result.error = f"Copy template failed: {exc}"
            return result

        # Package/ComGroup ids to rename; prototype rows for NOT-NULL boilerplate.
        pkg = mdb_svc.read_table(mdb, "SELECT com_PackageID, com_ComGroupID FROM tCOMd_Package")
        if not pkg:
            result.error = "Template tCOMd_Package is empty."
            return result
        package_id = pkg[0]["com_PackageID"]
        comgroup_id = pkg[0]["com_ComGroupID"]
        protos = {t: self._prototype(mdb, t) for t in _PRODUCT_TABLES}

        product = snapshot.product
        program_code = XocdExportService.program_key(product)
        series_id = XocdExportService.series_id(product)
        label = product.range_name or product.name or program_code

        price_lists = self._price_lists_by_currency(mdb)
        inserts = self._build(
            snapshot, package_id, comgroup_id, series_id, protos, price_lists, result
        )

        ops: list[dict[str, Any]] = [{"op": "delete", "table": t} for t in _PRODUCT_TABLES]
        ops.append({"op": "update", "table": "tCOMd_Package",
                    "set": {"reg_ProgramCode": program_code, "reg_ProgramLabel": label},
                    "where": {"com_PackageID": package_id}})
        ops.append({"op": "update", "table": "tCOMd_ComGroup",
                    "set": {"com_ComGroupCode": series_id, "com_ComGroupLabel": label},
                    "where": {"com_ComGroupID": comgroup_id}})
        for table, rows in inserts:
            if rows:
                ops.append({"op": "insert", "table": table, "rows": rows})

        batch = mdb_svc.execute_batch(mdb, ops)
        result.ok = batch.ok
        result.error = batch.first_error()
        result.logs.append(
            f"Wrote {sum(result.table_counts.values())} rows across "
            f"{len(result.table_counts)} table(s) into {mdb}"
        )
        return result

    # -- Template selection ---------------------------------------------

    def _infer_template(self, product) -> str:
        """Resolve the MDB template from the shared category/workspace context."""
        category = self.context.category_context_service.from_product(product)
        if category.workspace_kind in _TEMPLATES:
            return category.workspace_kind

        # Preserve the previous safe default when the source category is unknown.
        return "seating"

    # -- Prototype rows -------------------------------------------------

    def _prototype(self, mdb: Path, table: str) -> dict[str, Any]:
        """Read one existing row as a boilerplate template: drop the autonumber
        PK and any ``sys_tmp*`` scratch columns so the remaining NOT-NULL
        manufacturer defaults can seed each new row. Empty when the table has no
        rows (then the builder supplies every required column itself)."""
        rows = self.context.mdb_service.read_table(mdb, f"SELECT TOP 1 * FROM [{table}]")
        if not rows:
            return {}
        proto = dict(rows[0])
        proto.pop(_PK.get(table, ""), None)
        for col in [c for c in proto if c.startswith("sys_tmp")]:
            proto.pop(col, None)
        return proto

    @staticmethod
    def _row(proto: dict[str, Any], computed: dict[str, Any]) -> dict[str, Any]:
        """A new row: manufacturer boilerplate (prototype) overlaid with the
        computed columns (which always win, so no stale foreign keys survive)."""
        return {**proto, **computed}

    # -- Row assembly ---------------------------------------------------

    def _build(
        self, snapshot: Snapshot, package_id: Any, comgroup_id: Any,
        series_id: str, protos: dict[str, dict[str, Any]],
        price_lists: dict[str, dict[str, Any]], result: OcdExportResult,
    ) -> list[tuple[str, list[dict[str, Any]]]]:
        """Assemble every ``tCOMd_`` insert batch, parent tables first."""
        xocd = self.context.xocd_export_service
        classes = self.context.engineering_class_service.get_classes(snapshot)
        codes = xocd._value_code_map(snapshot)
        digits = xocd._value_lengths(snapshot)
        base_codes = xocd._base_codes(snapshot)
        token_by_base = xocd._group_token_by_base(snapshot, classes)

        text_rows, text_index = self._text(snapshot, package_id, protos["tCOMd_Text"])
        relobj_rows, relation_rows, relobjrel_rows, value_relobj = self._relations(
            snapshot, package_id, protos
        )
        scheme_rows, scheme_index, scheme_by_code = self._code_schemes(
            snapshot, package_id, base_codes, classes, codes, protos["tCOMd_CodeScheme"]
        )
        class_rows, class_index = self._classes(classes, package_id, protos["tCOMd_Class"])
        property_rows, prop_index = self._properties(
            classes, class_index, text_index, digits, protos["tCOMd_Property"]
        )
        propvalue_rows = self._property_values(
            snapshot, classes, prop_index, text_index, value_relobj, codes,
            protos["tCOMd_PropValue"]
        )
        article_rows, article_index = self._articles(
            base_codes, comgroup_id, package_id, text_index, scheme_index,
            scheme_by_code, protos["tCOMd_Article"]
        )
        articleclass_rows = self._article_classes(
            base_codes, token_by_base, classes, article_index, class_index,
            protos["tCOMd_ArticleClass"]
        )
        artbase_rows = self._artbase(snapshot, article_index, classes, codes, protos["tCOMd_ArtBase"])
        table_rows, column_rows, line_rows = self._value_tables(snapshot, package_id)
        price_rows, global_rows = self._prices(
            snapshot, article_index, price_lists, package_id, text_index,
            protos["tCOMd_Price"], protos["tCOMd_GlobalPrice"]
        )

        sequence: list[tuple[str, list[dict[str, Any]]]] = [
            ("tCOMd_Text", text_rows),
            ("tCOMd_RelObj", relobj_rows),
            ("tCOMd_Relation", relation_rows),
            ("tCOMd_CodeScheme", scheme_rows),
            ("tCOMd_Class", class_rows),
            ("tCOMd_Property", property_rows),
            ("tCOMd_PropValue", propvalue_rows),
            ("tCOMd_Article", article_rows),
            ("tCOMd_ArticleClass", articleclass_rows),
            ("tCOMd_ArtBase", artbase_rows),
            ("tCOMd_RelObjRel", relobjrel_rows),
            ("tCOMd_Table", table_rows),
            ("tCOMd_TableColumn", column_rows),
            ("tCOMd_TableLine", line_rows),
            ("tCOMd_Price", price_rows),
            ("tCOMd_GlobalPrice", global_rows),
        ]
        for table, rows in sequence:
            if rows:
                result.table_counts[table] = len(rows)
        return sequence

    # -- Text -----------------------------------------------------------

    def _text(
        self, snapshot: Snapshot, package_id: Any, proto: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], dict[tuple[str, str], int]]:
        """tCOMd_Text rows + ``{(type_code, name): id}`` index. Includes ``price``
        text blocks (one per option a surcharge price references, named by the
        option id) so upcharge price rows can carry their surcharge label - the
        golden pattern (base rows carry no text)."""
        blocks = self.context.engineering_text_service.ensure_text_blocks(snapshot)
        rows: list[dict[str, Any]] = []
        index: dict[tuple[str, str], int] = {}
        tid = 0
        for block in blocks:
            tid += 1
            index[(block.type_code, block.name)] = tid
            rows.append(self._row(proto, {
                "com_TextID": tid,
                "com_TextName": block.name,
                "com_TextTypeCode": _TEXT_TYPE_OCD.get(block.type_code, block.type_code),
                "com_PackageID": package_id,
                "com_Text_1_de": getattr(block, "de", "") or None,
                "com_Text_1_en": getattr(block, "en", "") or None,
                "com_Text_1_fr": getattr(block, "fr", "") or None,
                "com_Text_1_nl": getattr(block, "nl", "") or None,
            }))
        for option_id, en in self._price_text_map(snapshot).items():
            tid += 1
            index[("price", option_id)] = tid
            rows.append(self._row(proto, {
                "com_TextID": tid, "com_TextName": option_id,
                "com_TextTypeCode": "price", "com_PackageID": package_id,
                "com_Text_1_de": None, "com_Text_1_en": en or None,
                "com_Text_1_fr": None, "com_Text_1_nl": None,
            }))
        return rows, index

    def _price_text_map(self, snapshot: Snapshot) -> dict[str, str]:
        """``{option_id: label}`` for every option referenced by a surcharge
        (``=``) price record - the source of the ``price`` text blocks that
        upcharge rows link to. The label is the option's own name (the closest
        snapshot source for the golden "Surcharge <option>" text)."""
        opt_name = {str(o.id): (o.name or "") for o in snapshot.options}
        out: dict[str, str] = {}
        for rec in snapshot.price_records:
            vc = rec.variant_condition or ""
            if "=" not in vc:
                continue
            _, option_id, _ = self.context.price_update_service._lookup_key(
                bool(getattr(rec, "is_global", False)), rec.article_code or "", vc)
            if option_id and option_id not in out:
                out[option_id] = opt_name.get(option_id, "")
        return out

    @staticmethod
    def _property_text_id(index: dict[tuple[str, str], int], name: str) -> int | None:
        """Text id for a property/option text block, trying both type codes."""
        return index.get(("property", name)) or index.get(("option", name))

    # -- Relations ------------------------------------------------------

    @staticmethod
    def _relation_name(name: str) -> str:
        """MDB relation name: insert an ``A`` after the domain letter
        (``A_Code_Type`` -> ``AA_Code_Type``, ``B_X`` -> ``BA_X``)."""
        parts = name.split("_", 1)
        return f"{parts[0]}A_{parts[1]}" if len(parts) == 2 else name

    def _relations(
        self, snapshot: Snapshot, package_id: Any, protos: dict[str, dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
        """tCOMd_RelObj + tCOMd_Relation + tCOMd_RelObjRel rows and the
        ``{value_id: relobj_id}`` back-reference for value preconditions."""
        relation_objects = self.context.engineering_relation_service.build_relation_objects(snapshot)
        obj_rows: list[dict[str, Any]] = []
        rel_rows: list[dict[str, Any]] = []
        relrel_rows: list[dict[str, Any]] = []
        value_relobj: dict[str, int] = {}
        for i, rel in enumerate(relation_objects, start=1):
            obj_rows.append(self._row(protos["tCOMd_RelObj"], {
                "com_RelObjID": i, "com_RelObjName": rel.name, "com_PackageID": package_id,
            }))
            rel_rows.append(self._row(protos["tCOMd_Relation"], {
                "com_RelationID": i, "com_RelationName": self._relation_name(rel.name),
                "com_RelationBody": rel.body or "", "com_PackageID": package_id,
            }))
            relrel_rows.append(self._row(protos["tCOMd_RelObjRel"], {
                "com_RelObjRelID": i, "com_RelObjID": i, "com_RelationID": i,
                "com_RelObjTypeCode": rel.type_code, "com_RelObjDomainCode": rel.domain,
                "com_RelationOrder": rel.order,
            }))
            if getattr(rel, "value_id", ""):
                value_relobj[str(rel.value_id)] = i
        return obj_rows, rel_rows, relrel_rows, value_relobj

    # -- Code schemes ---------------------------------------------------

    def _code_schemes(
        self, snapshot: Snapshot, package_id: Any, base_codes: list[str],
        classes: list, codes: dict[str, str], proto: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, str]]:
        """tCOMd_CodeScheme rows, ``{scheme_name: id}`` and ``{article_code:
        scheme_name}``. The body is ``@`` per base-code character plus a
        ``<Class>:<Property>`` token per coded config/option property, space
        tokens between them - the manufacturer's code-scheme grammar."""
        pv_by: dict[str, list] = {}
        for pv in snapshot.property_values:
            pv_by.setdefault(str(pv.property_id), []).append(pv)
        ov_by: dict[str, list] = {}
        for ov in snapshot.option_values:
            ov_by.setdefault(str(ov.option_id), []).append(ov)

        prop_tokens: list[str] = []
        for cls in classes:
            if cls.name.lower().endswith("visual"):
                continue
            for a in cls.properties:
                values = pv_by.get(a.property_id) or ov_by.get(a.property_id) or []
                if any(codes.get(str(v.id)) for v in values):
                    prop_tokens.append(f"{cls.name}:{XocdExportService._prop_ident(a.property_name)}")
        tokens: list[str] = []
        for i, tok in enumerate(prop_tokens):
            if i:
                tokens.append(" ")
            tokens.append(tok)

        rows: list[dict[str, Any]] = []
        index: dict[str, int] = {}
        scheme_by_code: dict[str, str] = {}
        for code in base_codes:
            scheme_by_code[code] = code
            if code in index:
                continue
            scheme_id = len(index) + 1
            index[code] = scheme_id
            body = ",".join(["@"] * len(code) + tokens)
            rows.append(self._row(proto, {
                "com_CodeSchemeID": scheme_id, "com_CodeSchemeName": code,
                "com_CodeSchemeBody": body, "com_PackageID": package_id,
            }))
        return rows, index, scheme_by_code

    # -- Classes / properties / values ----------------------------------

    def _classes(
        self, classes: list, package_id: Any, proto: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """tCOMd_Class rows + ``{class.id: com_ClassID}`` index."""
        rows: list[dict[str, Any]] = []
        index: dict[str, int] = {}
        for cid, cls in enumerate(classes, start=1):
            index[str(cls.id)] = cid
            rows.append(self._row(proto, {
                "com_ClassID": cid, "com_ClassName": cls.name, "com_PackageID": package_id,
            }))
        return rows, index

    def _properties(
        self, classes: list, class_index: dict[str, int],
        text_index: dict[tuple[str, str], int], digits: dict[str, int],
        proto: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """tCOMd_Property rows + ``{property_id: com_PropertyID}`` index.

        ``com_PropName`` is the normalized identifier so relations and the code
        scheme reference the same token; ``com_PropDigits`` is the max value-code
        length so the property accepts its values."""
        rows: list[dict[str, Any]] = []
        index: dict[str, int] = {}
        pid = 0
        for cls in classes:
            class_pk = class_index[str(cls.id)]
            for position, a in enumerate(cls.properties):
                pid += 1
                index[str(a.property_id)] = pid
                prop_key = XocdExportService._prop_ident(a.property_name)
                scope = "RG" if (a.usage or "").lower().startswith("g") else "C"
                text_id = self._property_text_id(
                    text_index, a.text_block or text_block_name(a.property_name)
                )
                width = digits.get(a.property_id, 0) or len(prop_key)
                rows.append(self._row(proto, {
                    "com_PropertyID": pid, "com_ClassID": class_pk,
                    "com_PropName": prop_key, "com_PropTypeCode": (a.type or "C")[:1] or "C",
                    "com_PropScopeCode": scope, "com_PropPosition": 100 + position * 10,
                    "com_TextID": text_id, "com_RelObjID": None, "com_HintTextID": None,
                    "com_PropDigits": width, "com_PropDecDigits": 0,
                }))
        return rows, index

    def _property_values(
        self, snapshot: Snapshot, classes: list, prop_index: dict[str, int],
        text_index: dict[tuple[str, str], int], value_relobj: dict[str, int],
        codes: dict[str, str], proto: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """tCOMd_PropValue rows (one per unique value code per property)."""
        # Values live flat on the snapshot, grouped by their parent id.
        values_by: dict[str, list] = {}
        for pv in snapshot.property_values:
            values_by.setdefault(str(pv.property_id), []).append(pv)
        for ov in snapshot.option_values:
            values_by.setdefault(str(ov.option_id), []).append(ov)

        rows: list[dict[str, Any]] = []
        vid = 0
        for cls in classes:
            for a in cls.properties:
                # Free-text (T) properties take no enumerated values.
                if (a.type or "").strip().upper().startswith("T"):
                    continue
                prop_pk = prop_index.get(str(a.property_id))
                if prop_pk is None:
                    continue
                values = values_by.get(str(a.property_id), [])
                values = collapse_duplicate_values(values, lambda v: codes.get(str(v.id), ""))
                seen_codes: set[str] = set()
                position = 0
                for value in values:
                    code = codes.get(str(value.id), "")
                    if not code or code in seen_codes:
                        continue
                    seen_codes.add(code)
                    vid += 1
                    text_id = text_index.get(("propvalue", f"{text_block_name(a.property_name)}_{code}")) \
                        or text_index.get(("optionvalue", f"{text_block_name(a.property_name)}_{code}"))
                    rows.append(self._row(proto, {
                        "com_ValueID": vid, "com_PropertyID": prop_pk,
                        "com_PropValPosition": 100 + position * 10,
                        "com_PropValOpCodeFrom": "EQ", "com_PropValueFrom": code,
                        "com_TextID": text_id, "com_RelObjID": value_relobj.get(str(value.id)),
                        "com_PropValIsDefault": False,
                    }))
                    position += 1
        return rows

    # -- Articles / bindings / artbase ----------------------------------

    def _articles(
        self, base_codes: list[str], comgroup_id: Any, package_id: Any,
        text_index: dict[tuple[str, str], int], scheme_index: dict[str, int],
        scheme_by_code: dict[str, str], proto: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        """tCOMd_Article rows (one per base article) + ``{code: com_ArticleID}``."""
        rows: list[dict[str, Any]] = []
        index: dict[str, int] = {}
        for aid, code in enumerate(base_codes, start=1):
            index[code] = aid
            scheme_pk = scheme_index.get(scheme_by_code.get(code, ""))
            rows.append(self._row(proto, {
                "com_ArticleID": aid, "com_ArticleCode": code, "com_ArticleTypeCode": "C",
                "com_ComGroupID": comgroup_id, "com_PackageID": package_id,
                "com_CodeSchemeID": scheme_pk, "com_RelObjID": None,
                "com_ShortTextID": text_index.get(("artshort", code)),
                "com_LongTextID": text_index.get(("artlong", code)),
                "com_Discountable": True, "com_OrderUnitCode": "C62",
            }))
        return rows, index

    def _article_classes(
        self, base_codes: list[str], token_by_base: dict[str, str], classes: list,
        article_index: dict[str, int], class_index: dict[str, int], proto: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """tCOMd_ArticleClass rows: bind each base article to its own group's
        classes (unknown base -> all classes, never dropping data)."""
        rows: list[dict[str, Any]] = []
        acid = 0
        for code in base_codes:
            article_pk = article_index.get(code)
            if article_pk is None:
                continue
            token = token_by_base.get(code)
            order = 100
            for cls in classes:
                if token is not None and cls.name.rsplit("_", 1)[0] != token:
                    continue
                acid += 1
                rows.append(self._row(proto, {
                    "com_ArticleClassID": acid, "com_ArticleID": article_pk,
                    "com_ClassID": class_index[str(cls.id)], "com_ArticleClassOrder": order,
                    "com_RelObjID": None, "com_TextID": None,
                }))
                order += 10
        return rows

    def _artbase(
        self, snapshot: Snapshot, article_index: dict[str, int], classes: list,
        codes: dict[str, str], proto: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """tCOMd_ArtBase rows: per-article allowed value restrictions."""
        art_base = self.context.engineering_artbase_service.build_art_base(snapshot)
        if not art_base:
            return []
        # Property id -> (class name, normalized property name) for the restriction.
        prop_meta: dict[str, tuple[str, str]] = {}
        for cls in classes:
            for a in cls.properties:
                prop_meta[str(a.property_id)] = (cls.name, XocdExportService._prop_ident(a.property_name))
        rows: list[dict[str, Any]] = []
        abid = 0
        seen: set[tuple] = set()
        for base_code, prop_values in art_base.items():
            article_pk = article_index.get(base_code)
            if article_pk is None:
                continue
            for prop_id, value_ids in prop_values.items():
                meta = prop_meta.get(str(prop_id))
                if meta is None:
                    continue
                class_name, prop_name = meta
                for value_id in value_ids:
                    code = codes.get(str(value_id), "")
                    key = (article_pk, class_name, prop_name, code)
                    if not code or key in seen:
                        continue
                    seen.add(key)
                    abid += 1
                    rows.append(self._row(proto, {
                        "com_ArtBaseID": abid, "com_ArticleID": article_pk,
                        "com_ClassName": class_name, "com_PropName": prop_name,
                        "com_PropValue": code,
                    }))
        return rows

    # -- Value combination tables ---------------------------------------

    def _value_tables(
        self, snapshot: Snapshot, package_id: Any
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        """tCOMd_Table / tCOMd_TableColumn / tCOMd_TableLine rows. These tables
        are empty in the template, so every required column is set explicitly."""
        svc = self.context.engineering_value_table_service
        table_rows: list[dict[str, Any]] = []
        column_rows: list[dict[str, Any]] = []
        line_rows: list[dict[str, Any]] = []
        tid = cid = lid = 0
        for table in svc.ensure_value_tables(snapshot):
            tid += 1
            table_rows.append({
                "com_TableID": tid, "com_TableName": table.name,
                "com_PackageID": package_id, "com_StatusInfoID": 1,
            })
            col_id_of: dict[str, int] = {}
            for position, name in enumerate(table.property_names):
                cid += 1
                col_id_of[name] = cid
                column_rows.append({
                    "com_TableColumnID": cid, "com_TableID": tid,
                    "com_ColumnName": name, "com_ColumnPosition": 100 + position * 10,
                })
            for line_nr, line in enumerate(table.lines, start=1):
                for name in table.property_names:
                    cell = line.get(name)
                    if cell is None:
                        continue
                    values = cell if isinstance(cell, list) else [cell]
                    for value in values:
                        lid += 1
                        line_rows.append({
                            "com_TableLineID": lid, "com_TableColumnID": col_id_of[name],
                            "com_TableLineNr": line_nr, "com_TableLineValue": str(value),
                        })
        return table_rows, column_rows, line_rows

    # -- Prices ---------------------------------------------------------

    def _price_lists_by_currency(self, mdb: Path) -> dict[str, dict[str, Any]]:
        """Map each currency to the template's kept ``tCOMd_PriceList2`` list (its
        id + validity window). Price lists are infra kept unchanged, so new price
        rows attach to the existing list per currency (EUR/GBP). ``NOPRICE`` is
        skipped; the bridge's ``/Date(ms)/`` dates are decoded to ``YYYYMMDD``."""
        bridge_ymd = self.context.price_update_service._bridge_ymd
        out: dict[str, dict[str, Any]] = {}
        for r in self.context.mdb_service.read_table(
            mdb, "SELECT com_PriceListID, com_PriceListLabel, sys_ISOCurrencyCode, "
                 "com_PriceValidFrom, com_PriceValidTo FROM tCOMd_PriceList2"):
            label = str(r.get("com_PriceListLabel") or "")
            ccy = str(r.get("sys_ISOCurrencyCode") or "").upper()
            if not ccy or "NOPRICE" in label.upper() or ccy in out:
                continue
            date_to = bridge_ymd(r.get("com_PriceValidTo")) or _DATE_MAX
            out[ccy] = {
                "id": r["com_PriceListID"],
                "date_from": bridge_ymd(r.get("com_PriceValidFrom")) or _DATE_MIN,
                "date_to": _DATE_MAX if date_to.startswith("9999") else date_to,
            }
        return out

    def _prices(
        self, snapshot: Snapshot, article_index: dict[str, int],
        price_lists: dict[str, dict[str, Any]], package_id: Any,
        text_index: dict[tuple[str, str], int],
        price_proto: dict[str, Any], global_proto: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """tCOMd_Price + tCOMd_GlobalPrice rows from ``snapshot.price_records``.

        Each record attaches to its currency's kept price list, stamped with that
        list's validity window (or the record's own dates). Base/article records
        go to ``tCOMd_Price`` (keyed by article id); global records to
        ``tCOMd_GlobalPrice`` (keyed by package). A surcharge (``=``) row links
        ``com_TextID`` to its option's ``price`` text block (base rows carry no
        text - the golden pattern)."""
        ocd_date = XocdExportService._ocd_date
        lookup_key = self.context.price_update_service._lookup_key
        price_rows: list[dict[str, Any]] = []
        global_rows: list[dict[str, Any]] = []
        next_price = next_global = 1
        for rec in snapshot.price_records:
            pl = price_lists.get((rec.currency or "").upper())
            if pl is None:
                continue  # no template price list for this currency
            is_global = bool(getattr(rec, "is_global", False))
            _, option_id, _ = lookup_key(is_global, rec.article_code or "", rec.variant_condition or "")
            text_id = text_index.get(("price", option_id)) if option_id else None
            common = {
                "com_PriceListID": pl["id"],
                "com_VariantCondition": rec.variant_condition or "",
                "com_PriceTypeCode": "S", "com_PriceLevelCode": (rec.level or "B").strip() or "B",
                "com_PriceRuleCode": None, "com_TextID": text_id, "com_PriceValue": rec.value,
                "sys_ISOCurrencyCode": rec.currency or "", "com_PriceIndex": "",
                "com_PriceValidFrom": _mdb_date_literal(ocd_date(rec.valid_from, pl["date_from"])),
                "com_PriceValidTo": _mdb_date_literal(ocd_date(rec.valid_to, pl["date_to"])),
                "com_RoundingID": None, "com_StatusInfoID": None,
            }
            if is_global:
                global_rows.append(self._row(global_proto, {
                    "com_GlobalPriceID": next_global, "com_PackageID": package_id, **common}))
                next_global += 1
            else:
                article_id = article_index.get(rec.article_code or "")
                if article_id is None:
                    continue  # price for an article outside the export
                price_rows.append(self._row(price_proto, {
                    "com_PriceID": next_price, "com_ArticleID": article_id, **common}))
                next_price += 1
        return price_rows, global_rows
