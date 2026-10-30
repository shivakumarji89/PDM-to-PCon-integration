"""Load an OCD CSV folder and build the engine's :class:`ArticleModel`.

Tables are read by column *name* using the folder's descriptors
(``schema_loader``). OCD CSV files are ISO-8859-1 (spec 1); the loader decodes
accordingly and reports non-ASCII bytes once so the assumption stays testable.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from services.ocd_engine import diagnostics as dg
from services.ocd_engine import model as m
from services.ocd_engine.codescheme_engine import CodeSchemeDef
from services.ocd_engine.relation_parser import assemble_relation_text
from services.ocd_engine.schema_loader import TableSchema, load_schemas

_NUMERIC = ("uint", "int", "float")


@dataclass
class OcdDataset:
    """All tables of one OCD folder, with the lookup indexes the engine needs."""

    db_dir: Path
    schemas: dict[str, TableSchema]
    tables: dict[str, list[dict]] = field(default_factory=dict)
    sink: dg.DiagnosticSink = field(default_factory=dg.DiagnosticSink)

    def __post_init__(self) -> None:
        self._built = False

    def _index(self) -> None:
        if self._built:
            return
        t = self.tables.get
        self.articles = {r["article_nr"]: r for r in t("article", [])}
        self.artbase = defaultdict(list)
        for r in t("artbase", []):
            self.artbase[r["article_nr"]].append(r)
        self.classes = defaultdict(list)
        for r in t("propertyclass", []):
            self.classes[r["article_nr"]].append(r)
        self.properties = defaultdict(list)
        for r in t("property", []):
            self.properties[r["prop_class"]].append(r)
        self.values = defaultdict(list)
        for r in t("propertyvalue", []):
            self.values[(r["prop_class"], r["property"])].append(r)
        self.relobjs = defaultdict(list)
        for r in t("relationobj", []):
            self.relobjs[str(r["rel_obj"])].append(r)
        blocks = defaultdict(list)
        for r in t("relation", []):
            blocks[r["rel_name"]].append((int(r["rel_blocknr"] or 0), r["rel_block"]))
        self._blocks = blocks
        self.prices = defaultdict(list)
        for r in t("price", []):
            self.prices[r["article_nr"]].append(r)
        self.schemes = {r["scheme_id"]: r for r in t("codescheme", [])}
        self._built = True

    def relation_text(self, rel_name: str) -> str | None:
        self._index()
        blocks = self._blocks.get(rel_name)
        return None if blocks is None else assemble_relation_text(blocks)

    def article_numbers(self) -> list[str]:
        self._index()
        return sorted(self.articles)

    def code_scheme(self, scheme_id: str) -> CodeSchemeDef | None:
        self._index()
        row = self.schemes.get(scheme_id)
        return CodeSchemeDef.from_row(row) if row else None


class OcdCsvLoader:
    def __init__(self, encoding: str = "latin-1") -> None:
        self.encoding = encoding

    def load(self, db_dir: str | Path) -> OcdDataset:
        folder = Path(db_dir)
        dataset = OcdDataset(folder, load_schemas(folder))
        for name, schema in dataset.schemas.items():
            path = folder / schema.file
            if not path.exists():
                continue
            dataset.tables[name] = self._read(path, schema, dataset.sink)
        for required in ("article", "property", "propertyvalue", "price"):
            if required not in dataset.tables:
                dataset.sink.add(dg.MISSING_TABLE, f"obligatory table {required} not found in {folder}",
                                 dg.Severity.ERROR)
        return dataset

    def _read(self, path: Path, schema: TableSchema, sink: dg.DiagnosticSink) -> list[dict]:
        rows: list[dict] = []
        numeric = [any(t.startswith(p) for p in _NUMERIC) for t in schema.types] or \
                  [False] * len(schema.fields)
        non_ascii = False
        with path.open(newline="", encoding=self.encoding) as handle:
            for number, record in enumerate(csv.reader(handle, delimiter=schema.delimiter, quotechar='"'), 1):
                if not record:
                    continue
                if len(record) < len(schema.fields):
                    record = record + [""] * (len(schema.fields) - len(record))
                row = {}
                for index, field_name in enumerate(schema.fields):
                    text = record[index]
                    if numeric[index] and index < len(numeric):
                        text = text.strip()
                    if not non_ascii and any(ord(ch) > 127 for ch in text):
                        non_ascii = True
                    row[field_name] = text
                rows.append(row)
        if non_ascii:
            sink.add(dg.LOAD_ERROR, f"{path.name} contains non-ASCII text decoded as {self.encoding}",
                     dg.Severity.INFO, source=path.name)
        return rows


# --------------------------------------------------------------------------- model builder


def _relations(dataset: OcdDataset, rel_obj: str, article: str, owner: str) -> tuple[m.RelationRef, ...]:
    if not rel_obj or rel_obj.strip() in {"", "0"}:
        return ()
    refs: list[m.RelationRef] = []
    for row in dataset.relobjs.get(str(int(rel_obj)) if rel_obj.strip().isdigit() else rel_obj, []):
        text = dataset.relation_text(row["rel_name"])
        if text is None:
            dataset.sink.add(dg.MISSING_RELATION, f"relation {row['rel_name']} has no code blocks",
                             article=article, relation=row["rel_name"], source=owner)
            continue
        try:
            rel_type = int(row["rel_type"])
        except ValueError:
            dataset.sink.add(dg.UNSUPPORTED_SYNTAX, f"unknown relation type {row['rel_type']!r}",
                             article=article, relation=row["rel_name"], source=owner)
            continue
        refs.append(m.RelationRef(
            name=f"{rel_obj}/{row['rel_name'].lstrip('0') or '0'}",
            rel_type=rel_type, domain=row["rel_domain"] or "C",
            order=int(row["position"] or 0), text=text,
        ))
    return tuple(refs)


def build_article_model(dataset: OcdDataset, article_nr: str) -> m.ArticleModel | None:
    """Assemble classes, properties, values, ArtBase restrictions and relations of one article."""
    dataset._index()
    sink = dataset.sink
    article = dataset.articles.get(article_nr)
    if article is None:
        sink.add(dg.MISSING_PROPERTY, f"article {article_nr} not found", article=article_nr)
        return None

    fixed: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in dataset.artbase.get(article_nr, []):
        fixed[(row["prop_class"], row["property"])].add(row["prop_value"])

    classes: list[m.ClassDef] = []
    properties: list[m.PropertyDef] = []
    order = 0
    for class_row in sorted(dataset.classes.get(article_nr, []), key=lambda r: int(r["pos_class"] or 0)):
        class_name = class_row["prop_class"]
        class_props: list[str] = []
        for prop_row in sorted(dataset.properties.get(class_name, []), key=lambda r: int(r["pos_prop"] or 0)):
            name = prop_row["property"]
            key = f"{class_name}:{name}"
            values: list[m.ValueDef] = []
            for value_row in sorted(dataset.values.get((class_name, name), []),
                                    key=lambda r: int(r["pos_pval"] or 0)):
                if value_row["op_from"].upper() != "EQ" or value_row["op_to"]:
                    sink.add(dg.UNSUPPORTED_SYNTAX,
                             f"interval/free-range value of {key} is not enumerable",
                             dg.Severity.INFO, article=article_nr, property=key)
                    continue
                values.append(m.ValueDef(
                    key=f"{key}:{value_row['value_from']}", value=value_row["value_from"],
                    code=value_row["value_from"], order=int(value_row["pos_pval"] or 0),
                    relations=_relations(dataset, value_row["rel_obj"], article_nr,
                                         f"value {key}={value_row['value_from']}"),
                ))
            allowed = None
            if (class_name, name) in fixed:
                wanted = fixed[(class_name, name)]
                existing = {v.value for v in values}
                for missing in sorted(wanted - existing):
                    values.append(m.ValueDef(key=f"{key}:{missing}", value=missing, code=missing))
                allowed = frozenset(f"{key}:{v}" for v in wanted)
            properties.append(m.PropertyDef(
                key=key, name=name, class_name=class_name, order=order, values=tuple(values),
                relations=_relations(dataset, prop_row["rel_obj"], article_nr, f"property {key}"),
                length=int(prop_row["digits"] or 0), optional=prop_row["need_input"] in {"", "0"},
                restrictable=prop_row["restrictable"] == "1", multi_option=prop_row["multi_option"] == "1",
                scope=prop_row["scope"], allowed_keys=allowed,
            ))
            class_props.append(key)
            order += 1
        classes.append(m.ClassDef(
            name=class_name, order=int(class_row["pos_class"] or 0),
            relations=_relations(dataset, class_row["rel_obj"], article_nr, f"class {class_name}"),
            property_keys=tuple(class_props),
        ))

    return m.ArticleModel(
        base_code=article_nr, article_key=article_nr, properties=tuple(properties),
        classes=tuple(classes),
        article_relations=_relations(dataset, article["rel_obj"], article_nr, "article"),
        scheme_id=article.get("scheme_id", ""),
    )
