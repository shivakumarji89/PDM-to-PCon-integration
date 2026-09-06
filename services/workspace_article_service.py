"""Workspace article loading service.

Loads existing-series article data directly from the repository OCD into the
working Snapshot. This path is deliberately independent from PDM.

This is a SOURCE ADAPTER only: every method here reads/normalizes raw
``tCOMd_*`` rows into the same domain objects the PDM path builds
(``Article``, ``Property``/``PropertyValue``, ``EngineeringClass``,
``TextBlock``, ``RelationObject``, ``PriceRecord``/``PriceList``), then hands
them to the existing central services (``engineering_reduction_service``,
``engineering_initialization_service``). No grouping/base/class/text/
relation/pricing business logic is duplicated here - it is derived directly
from the write-side column mapping in ``services/ocd_export_service.py``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from models.article import Article
from models.engineering_class import ClassPropertyAssignment, ClassValue, EngineeringClass
from models.price_list import PriceList
from models.price_record import PriceRecord
from models.product import Product
from models.property import Property
from models.property_value import PropertyValue
from models.relation_object import RelationObject
from models.snapshot import Snapshot
from models.text_block import TextBlock
from services.base_service import BaseService


class WorkspaceArticleService(BaseService):
    """Create an Article workflow snapshot from an existing repository OCD."""

    _OCD_FILE = "pcr_data_com_ocd.mdb"

    def load_active_repository(self) -> Snapshot | None:
        active = self.context.repository_context_service.active_context
        if active is None:
            return None
        return self.load_repository(
            active.repository_path, active.series_name, active.category
        )

    def load_repository(
        self,
        repository_path: str | Path,
        series_name: str = "",
        category: str = "",
    ) -> Snapshot | None:
        folder = Path(repository_path)
        mdb_path = folder / self._OCD_FILE
        if not mdb_path.is_file():
            return None

        rows = self.context.mdb_service.read_table(
            mdb_path,
            "SELECT com_ArticleID, com_ArticleCode FROM tCOMd_Article "
            "WHERE com_ArticleCode IS NOT NULL",
        )

        seen: set[str] = set()
        articles: list[Article] = []
        for row in rows:
            code = str(row.get("com_ArticleCode") or "").strip()
            if not code or code in seen:
                continue
            seen.add(code)
            article_id = str(row.get("com_ArticleID") or code)
            articles.append(
                Article(
                    id=article_id,
                    product_id=str(folder),
                    code=code,
                    source="repository_ocd",
                    selected=True,
                )
            )

        product = Product(
            id=str(folder),
            code=series_name or folder.name,
            name=series_name or folder.name,
            category=category,
            articles=articles,
        )
        snapshot = self.context.snapshot_service.create_snapshot(product)
        # Replaces whatever repository/series was previously active: create_snapshot
        # always installs a brand new Snapshot on the shared SnapshotManager. `id`
        # must be set (mirrors the PDM path, e.g. services/pdm_service.py) so
        # snapshot-keyed UI caches (e.g. ArticlesPage._snapshot_key) detect the
        # change and drop stale per-snapshot state instead of leaking it across
        # repositories.
        snapshot.id = product.id
        snapshot.articles = articles
        snapshot.metadata.source = "repository_ocd"
        snapshot.metadata.product_code = product.code
        snapshot.metadata.notes = f"Loaded directly from {mdb_path}"

        # Same central pipeline PDM loading uses for base article / base length /
        # article-set grouping (services/engineering/engineering_reduction_service.py)
        # and for engineering initialization - no repository-specific duplicate.
        self.context.engineering_reduction_service.materialize_article_sets(snapshot)
        self.context.engineering_initialization_service.initialize(snapshot)

        code_to_article_id = {a.code: a.id for a in articles}
        text_index = self._load_texts(mdb_path, snapshot)
        self._load_classes(mdb_path, snapshot, text_index)
        self._load_relations(mdb_path, snapshot)
        self._load_art_base(mdb_path, snapshot, code_to_article_id)
        self._load_prices(mdb_path, snapshot, text_index)
        return snapshot

    # -- Texts --------------------------------------------------------------

    def _load_texts(
        self, mdb_path: Path, snapshot: Snapshot
    ) -> dict[Any, TextBlock]:
        """Read ``tCOMd_Text`` into ``snapshot.text_blocks`` and return the
        ``{com_TextID: TextBlock}`` index other readers resolve their own
        ``*TextID`` foreign keys through - mirrors ``OcdExportService._text``
        in reverse (same table, same ``de/en/fr/nl`` columns)."""
        rows = self.context.mdb_service.read_table(
            mdb_path,
            "SELECT com_TextID, com_TextName, com_TextTypeCode, com_Text_1_de, "
            "com_Text_1_en, com_Text_1_fr, com_Text_1_nl FROM tCOMd_Text",
        )
        by_id: dict[Any, TextBlock] = {}
        for row in rows:
            block = TextBlock(
                name=str(row.get("com_TextName") or ""),
                type_code=str(row.get("com_TextTypeCode") or ""),
                de=str(row.get("com_Text_1_de") or ""),
                en=str(row.get("com_Text_1_en") or ""),
                fr=str(row.get("com_Text_1_fr") or ""),
                nl=str(row.get("com_Text_1_nl") or ""),
            )
            by_id[row.get("com_TextID")] = block
            snapshot.text_blocks.append(block)
        return by_id

    # -- Classes / properties / values --------------------------------------

    def _load_classes(
        self, mdb_path: Path, snapshot: Snapshot, text_index: dict[Any, TextBlock]
    ) -> None:
        """Read ``tCOMd_Class``/``tCOMd_Property``/``tCOMd_PropValue`` back into
        ``snapshot.engineering.classes`` (the same structure
        ``EngineeringClassService`` manages) plus the flat ``snapshot.properties``/
        ``property_values`` indexes other central services key off of. Mirrors
        ``OcdExportService._classes``/``_properties``/``_property_values``."""
        class_rows = self.context.mdb_service.read_table(
            mdb_path, "SELECT com_ClassID, com_ClassName FROM tCOMd_Class"
        )
        if not class_rows:
            return
        property_rows = self.context.mdb_service.read_table(
            mdb_path,
            "SELECT com_PropertyID, com_ClassID, com_PropName, com_PropTypeCode, "
            "com_PropScopeCode, com_PropPosition, com_TextID, com_PropDigits "
            "FROM tCOMd_Property",
        )
        value_rows = self.context.mdb_service.read_table(
            mdb_path,
            "SELECT com_ValueID, com_PropertyID, com_PropValPosition, "
            "com_PropValueFrom, com_TextID FROM tCOMd_PropValue",
        )

        properties_by_class: dict[Any, list[dict]] = {}
        for row in property_rows:
            properties_by_class.setdefault(row.get("com_ClassID"), []).append(row)
        values_by_property: dict[Any, list[dict]] = {}
        for row in value_rows:
            values_by_property.setdefault(row.get("com_PropertyID"), []).append(row)

        classes: list[EngineeringClass] = []
        for class_row in sorted(class_rows, key=lambda r: r.get("com_ClassID") or 0):
            class_id = class_row.get("com_ClassID")
            engineering_class = EngineeringClass(
                id=f"mdb-class-{class_id}", name=str(class_row.get("com_ClassName") or "")
            )
            props = sorted(
                properties_by_class.get(class_id, []),
                key=lambda r: r.get("com_PropPosition") or 0,
            )
            for prop_row in props:
                property_id = f"mdb-prop-{prop_row.get('com_PropertyID')}"
                property_name = str(prop_row.get("com_PropName") or "")
                type_code = str(prop_row.get("com_PropTypeCode") or "C") or "C"
                usage = "Graphic" if str(prop_row.get("com_PropScopeCode") or "") == "RG" else "Configuration"
                text_block = text_index.get(prop_row.get("com_TextID"))
                text_block_name = text_block.name if text_block is not None else property_name
                width = int(prop_row.get("com_PropDigits") or 0)

                values = sorted(
                    values_by_property.get(prop_row.get("com_PropertyID"), []),
                    key=lambda r: r.get("com_PropValPosition") or 0,
                )
                class_values: list[ClassValue] = []
                property_values: list[PropertyValue] = []
                for value_row in values:
                    code = str(value_row.get("com_PropValueFrom") or "")
                    if not code:
                        continue
                    value_text = text_index.get(value_row.get("com_TextID"))
                    value_name = value_text.en if value_text is not None and value_text.en else code
                    value_id = f"mdb-val-{value_row.get('com_ValueID')}"
                    class_values.append(ClassValue(code=code, value=value_name, source="repository_ocd"))
                    property_values.append(
                        PropertyValue(id=value_id, property_id=property_id, value=value_name, code=code)
                    )

                engineering_class.properties.append(
                    ClassPropertyAssignment(
                        property_id=property_id,
                        property_name=property_name,
                        width=width,
                        type=type_code,
                        usage=usage,
                        text_block=text_block_name,
                        values=class_values,
                    )
                )
                snapshot.properties.append(
                    Property(id=property_id, code=property_name, name=property_name, data_type=type_code)
                )
                snapshot.property_values.extend(property_values)
            classes.append(engineering_class)

        snapshot.engineering.classes = classes

    # -- Relations ------------------------------------------------------------

    def _load_relations(self, mdb_path: Path, snapshot: Snapshot) -> None:
        """Read ``tCOMd_RelObj``/``tCOMd_Relation``/``tCOMd_RelObjRel`` back into
        ``snapshot.relation_objects``. Mirrors ``OcdExportService._relations``:
        one relation object per (RelObj, Relation) pair joined through RelObjRel."""
        rows = self.context.mdb_service.read_table(
            mdb_path,
            "SELECT ro.com_RelObjName, r.com_RelationBody, rr.com_RelObjTypeCode, "
            "rr.com_RelObjDomainCode, rr.com_RelationOrder "
            "FROM (tCOMd_RelObjRel rr "
            "INNER JOIN tCOMd_RelObj ro ON rr.com_RelObjID = ro.com_RelObjID) "
            "INNER JOIN tCOMd_Relation r ON rr.com_RelationID = r.com_RelationID",
        )
        for row in rows:
            snapshot.relation_objects.append(
                RelationObject(
                    name=str(row.get("com_RelObjName") or ""),
                    type_code=str(row.get("com_RelObjTypeCode") or "1"),
                    domain=str(row.get("com_RelObjDomainCode") or "C"),
                    order=int(row.get("com_RelationOrder") or 100),
                    body=str(row.get("com_RelationBody") or ""),
                )
            )

    # -- Article base (per-base value restrictions) --------------------------

    def _load_art_base(
        self, mdb_path: Path, snapshot: Snapshot, code_to_article_id: dict[str, str]
    ) -> None:
        """Read ``tCOMd_ArtBase`` back into ``snapshot.art_base``
        (``base article code -> {property_id: [value_id, ...]}``), resolving
        each row's ``(class_name, prop_name, value code)`` against the classes
        just rebuilt by :meth:`_load_classes`. Mirrors ``OcdExportService._artbase``."""
        rows = self.context.mdb_service.read_table(
            mdb_path,
            "SELECT a.com_ArticleCode, ab.com_ClassName, ab.com_PropName, "
            "ab.com_PropValue FROM tCOMd_ArtBase ab "
            "INNER JOIN tCOMd_Article a ON ab.com_ArticleID = a.com_ArticleID",
        )
        if not rows:
            return

        # (class_name, prop_name) -> (property_id, {code: value_id})
        lookup: dict[tuple[str, str], tuple[str, dict[str, str]]] = {}
        for engineering_class in snapshot.engineering.classes:
            for assignment in engineering_class.properties:
                code_to_value_id = {
                    value.code: value_id
                    for value, value_id in zip(
                        assignment.values,
                        (
                            pv.id
                            for pv in snapshot.property_values
                            if pv.property_id == assignment.property_id
                        ),
                    )
                }
                lookup[(engineering_class.name, assignment.property_name)] = (
                    assignment.property_id,
                    code_to_value_id,
                )

        for row in rows:
            code = str(row.get("com_ArticleCode") or "")
            if code not in code_to_article_id:
                continue
            key = (str(row.get("com_ClassName") or ""), str(row.get("com_PropName") or ""))
            match = lookup.get(key)
            if match is None:
                continue
            property_id, code_to_value_id = match
            value_id = code_to_value_id.get(str(row.get("com_PropValue") or ""))
            if value_id is None:
                continue
            snapshot.art_base.setdefault(code, {}).setdefault(property_id, []).append(value_id)

    # -- Prices ---------------------------------------------------------------

    def _load_prices(
        self, mdb_path: Path, snapshot: Snapshot, text_index: dict[Any, TextBlock]
    ) -> None:
        """Read ``tCOMd_Price``/``tCOMd_GlobalPrice``/``tCOMd_PriceList2`` back
        into ``snapshot.price_records``/``price_lists``. Mirrors
        ``OcdExportService._prices``/``_price_lists_by_currency`` in reverse -
        each price row already carries its own currency and validity window, so
        no re-derivation is needed."""
        bridge_ymd = self.context.price_update_service._bridge_ymd

        list_rows = self.context.mdb_service.read_table(
            mdb_path,
            "SELECT com_PriceListID, com_PriceListLabel, sys_ISOCurrencyCode, "
            "com_PriceValidFrom, com_PriceValidTo FROM tCOMd_PriceList2",
        )
        seen_lists: set[str] = set()
        for row in list_rows:
            list_id = str(row.get("com_PriceListID") or "")
            if not list_id or list_id in seen_lists:
                continue
            seen_lists.add(list_id)
            snapshot.price_lists.append(
                PriceList(
                    id=list_id,
                    label=str(row.get("com_PriceListLabel") or ""),
                    currency=str(row.get("sys_ISOCurrencyCode") or "").upper(),
                    date_from=bridge_ymd(row.get("com_PriceValidFrom")),
                    date_to=bridge_ymd(row.get("com_PriceValidTo")),
                )
            )

        price_rows = self.context.mdb_service.read_table(
            mdb_path,
            "SELECT a.com_ArticleCode, p.com_VariantCondition, p.com_PriceLevelCode, "
            "p.com_PriceValue, p.sys_ISOCurrencyCode, p.com_PriceValidFrom, "
            "p.com_PriceValidTo FROM tCOMd_Price p "
            "INNER JOIN tCOMd_Article a ON p.com_ArticleID = a.com_ArticleID",
        )
        for row in price_rows:
            snapshot.price_records.append(
                PriceRecord(
                    is_global=False,
                    article_code=str(row.get("com_ArticleCode") or ""),
                    variant_condition=str(row.get("com_VariantCondition") or ""),
                    level=str(row.get("com_PriceLevelCode") or "B"),
                    value=float(row.get("com_PriceValue") or 0.0),
                    currency=str(row.get("sys_ISOCurrencyCode") or "").upper(),
                    valid_from=bridge_ymd(row.get("com_PriceValidFrom")),
                    valid_to=bridge_ymd(row.get("com_PriceValidTo")),
                )
            )

        global_rows = self.context.mdb_service.read_table(
            mdb_path,
            "SELECT com_VariantCondition, com_PriceLevelCode, com_PriceValue, "
            "sys_ISOCurrencyCode, com_PriceValidFrom, com_PriceValidTo "
            "FROM tCOMd_GlobalPrice",
        )
        for row in global_rows:
            snapshot.price_records.append(
                PriceRecord(
                    is_global=True,
                    article_code="",
                    variant_condition=str(row.get("com_VariantCondition") or ""),
                    level=str(row.get("com_PriceLevelCode") or "B"),
                    value=float(row.get("com_PriceValue") or 0.0),
                    currency=str(row.get("sys_ISOCurrencyCode") or "").upper(),
                    valid_from=bridge_ymd(row.get("com_PriceValidFrom")),
                    valid_to=bridge_ymd(row.get("com_PriceValidTo")),
                )
            )
