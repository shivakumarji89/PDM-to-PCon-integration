"""OCD table schemas: parsed from ``pdata.ocd_<table>.inp_descr`` descriptors.

Columns are addressed by *name*, never by position, so a range whose CSV
column order differs from the default is still read correctly. When a folder
carries no descriptors the OCD 4.3 default layouts below are used.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TableSchema:
    name: str                       # short name, e.g. "price"
    file: str                       # e.g. "ocd_price.csv"
    fields: tuple[str, ...]
    types: tuple[str, ...] = ()
    delimiter: str = ";"

    def index(self, field: str) -> int:
        return self.fields.index(field)


def _defaults() -> dict[str, TableSchema]:
    layouts = {
        "article": "article_nr art_type manufacturer series short_textnr long_textnr rel_obj "
                   "fast_supply discountable order_unit scheme_id",
        "artbase": "article_nr prop_class property prop_value",
        "propertyclass": "article_nr pos_class prop_class textnr rel_obj",
        "property": "prop_class property pos_prop prop_textnr rel_obj prop_type digits dec_digits "
                    "need_input add_values restrictable multi_option scope txt_control hint_text_id",
        "propertyvalue": "prop_class property pos_pval pval_textnr rel_obj is_default suppress_txt "
                         "op_from value_from op_to value_to raster date_from date_to",
        "relationobj": "rel_obj position rel_name rel_type rel_domain",
        "relation": "rel_name rel_blocknr rel_block",
        "price": "article_nr var_cond price_type price_level price_rule price_textnr price is_fix "
                 "currency date_from date_to scale_quantity rounding_id",
        "codescheme": "scheme_id scheme varcode_sep value_sep visibility invisible_char "
                      "unselect_char trim mo_sep mo_bracket",
        "rounding": "id nr min max type precision add_before add_after",
        "version": "format_version rel_coding data_version date_from date_to region varcond_var "
                   "placeholder_on tables comment",
    }
    return {
        name: TableSchema(name=name, file=f"ocd_{name}.csv", fields=tuple(cols.split()))
        for name, cols in layouts.items()
    }


DEFAULT_SCHEMAS: dict[str, TableSchema] = _defaults()


def parse_descriptor(path: str | Path) -> list[TableSchema]:
    """Parse one ``.inp_descr`` file (it may describe several tables)."""
    schemas: list[TableSchema] = []
    current: dict | None = None

    def flush() -> None:
        if current and current["fields"]:
            schemas.append(TableSchema(
                name=current["name"], file=current["file"],
                fields=tuple(n for n, _ in current["fields"]),
                types=tuple(t for _, t in current["fields"]),
                delimiter=current["delim"],
            ))

    for raw in Path(path).read_text(encoding="latin-1").splitlines():
        parts = raw.split("\t")
        if not parts or not parts[0]:
            continue
        if parts[0] == "table" and len(parts) >= 3:
            flush()
            file = parts[2]
            short = file[4:-4] if file.startswith("ocd_") and file.endswith(".csv") else file
            current = {"name": short, "file": file, "fields": [], "delim": ";"}
        elif parts[0] == "field" and current is not None and len(parts) >= 4:
            current["fields"].append((parts[2], parts[3]))
            delim = next((p for p in parts[4:] if p.startswith("delim")), "")
            if delim:
                tokens = delim.split()
                if len(tokens) > 1:
                    current["delim"] = tokens[1]
    flush()
    return schemas


def load_schemas(db_dir: str | Path) -> dict[str, TableSchema]:
    """Schemas for every table in ``db_dir``: descriptors win over defaults."""
    schemas = dict(DEFAULT_SCHEMAS)
    for descriptor in sorted(Path(db_dir).glob("pdata.ocd_*.inp_descr")):
        for schema in parse_descriptor(descriptor):
            schemas[schema.name] = schema
    return schemas
