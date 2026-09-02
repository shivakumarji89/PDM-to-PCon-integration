"""XOCD (Extended OFML Commercial Data) CSV exporter.

Writes a snapshot's engineering data as an XOCD CSV package - the format the
pCon.creator "OCD Import" module consumes to build a workspace. Unlike the
direct-MDB writer, XOCD is:

* **CSV**, semicolon-delimited, CRLF, positional (no header) - matching the OCD
  ``<name>_tbl.csv`` convention the app already uses;
* **name-keyed** - the article -> class -> property -> value chain is keyed by
  ``Program`` (series) + article code + class/property/value names, so the
  import module assigns internal ids. Only ``RelObjID`` is numeric;
* **multi-series** - every table's first field is the ``Program`` (series) key,
  so one package (one SVN folder) holds every series. Export is a per-series
  **upsert**: rows for the exported series are replaced, other series are kept.

Writes the full package: registry, structural tables, text, relations, code
schemes, prices and value-combination tables.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from models.snapshot import Snapshot
from services.base_service import BaseService
from services.engineering.engineering_reduction_service import collapse_duplicate_values
from services.engineering.engineering_text_service import LANGUAGES, text_block_name

#: OCD CSV dialect: semicolon-delimited, CRLF, minimal quoting.
_DELIM = ";"
_LINEEND = "\r\n"
#: OCD mandates ISO-8859-1 (Latin-1) as the CSV character set (spec 1.1).
_ENCODING = "latin-1"

#: Broad "always valid" OCD date range (YYYYMMDD) for NOT-NULL validity fields
#: when the source carries none.
_DATE_MIN = "20200101"
_DATE_MAX = "99991231"

#: Sales manufacturer key (XOCD ``Article.ManufacturerID``); Herman Miller.
_MANUFACTURER_ID = "HM"

#: Text-block type code -> XOCD description file. OCD models options as
#: properties, so option text folds into the property text files.
_TEXT_FILES = {
    "artshort": "xocd_artshorttext.csv",
    "artlong": "xocd_artlongtext.csv",
    "propclass": "xocd_propclasstext.csv",
    "property": "xocd_propertytext.csv",
    "propvalue": "xocd_propvaluetext.csv",
    "option": "xocd_propertytext.csv",
    "optionvalue": "xocd_propvaluetext.csv",
    "price": "xocd_pricetext.csv",
}

#: Max characters per ``TextLine`` (XOCD description tables) / ``CodeBlock``.
_TEXT_LINE_MAX = 80
_CODE_BLOCK_MAX = 255


@dataclass
class XocdExportResult:
    """Outcome of an XOCD series export.

    When the series already exists and ``force`` was not set, nothing is written:
    ``needs_validation`` is True and ``diff`` holds the per-file row changes for
    the user to review before re-running with ``force=True``.
    """

    ok: bool = False
    folder: str = ""
    program: str = ""
    applied: bool = False
    needs_validation: bool = False
    files: dict[str, int] = field(default_factory=dict)
    diff: dict[str, dict[str, list[list[str]]]] = field(default_factory=dict)
    logs: list[str] = field(default_factory=list)
    error: str | None = None


class XocdExportService(BaseService):
    """Writes/merges a snapshot into an XOCD CSV package folder, per series."""

    # -- Program (series) key -------------------------------------------

    @staticmethod
    def _series_source(product) -> str:
        """The raw series name both keys derive from: the product's range (the
        commercial series, e.g. 'Aeron'), falling back to its code. Shared so the
        lower-case Program key and the upper-case Program_ID always name the same
        series - matching the OCD ``ocd_article.series`` field (e.g. 'AERON')."""
        return (getattr(product, "range_name", "") or getattr(product, "code", "") or "series")

    @staticmethod
    def program_key(product) -> str:
        """Derive the XOCD ``Program`` serial key from a product: lower-case
        alphanumeric starting with a letter (``[a-z][a-z0-9]*``)."""
        raw = XocdExportService._series_source(product)
        key = re.sub(r"[^a-z0-9]", "", raw.lower())
        if not key or not key[0].isalpha():
            key = "s" + key
        return key

    @staticmethod
    def series_id(product) -> str:
        """The sales product-line key (``Program_ID`` / OCD ``series``): the same
        series as :meth:`program_key`, upper-cased ``[A-Z0-9_]+`` (e.g. 'AERON').
        """
        raw = XocdExportService._series_source(product)
        return re.sub(r"[^A-Z0-9_]", "", raw.upper()) or "SERIES"

    # -- Public entry point ---------------------------------------------

    def export_series(
        self,
        snapshot: Snapshot,
        folder: str | Path,
        program: str | None = None,
        program_id: str | None = None,
        label: str | None = None,
        price_list: str = "STD",
        text_category: str = "1",
        force: bool = False,
    ) -> XocdExportResult:
        """Export ``snapshot`` as one series into the XOCD package at ``folder``.

        A **new** series is written straight away. If the series **already
        exists** and ``force`` is False, nothing is written: the result carries
        ``needs_validation`` + a per-file ``diff`` for the user to review, then
        re-run with ``force=True`` to apply.
        """
        result = XocdExportResult(folder=str(folder))
        if snapshot.product is None:
            result.error = "No product loaded."
            return result

        product = snapshot.product
        program = program or self.program_key(product)
        program_id = program_id or self.series_id(product)
        # Label = the series designation (the range, e.g. 'Aeron'), NOT a single
        # product's name; matches the golden tCOMd_Package.reg_ProgramLabel.
        label = label or (product.range_name or product.name or program)
        result.program = program

        out = Path(folder)
        out.mkdir(parents=True, exist_ok=True)

        ctx = {
            "program": program, "program_id": program_id, "label": label,
            "price_list": price_list, "text_category": text_category,
        }
        plan = self._plan(snapshot, out, ctx)

        # Existing series without force -> diff only, write nothing.
        if not force and self._program_exists(out, program):
            for path, key_index, key_value, rows in plan:
                if key_value != program:  # skip shared registry (price list / text category)
                    continue
                changes = self._diff(path, key_index, key_value, rows)
                if changes["added"] or changes["removed"]:
                    result.diff[path.name] = changes
            result.ok = True
            result.needs_validation = bool(result.diff)
            if result.needs_validation:
                result.logs.append(
                    f"Series '{program}' already exists; {len(result.diff)} file(s) "
                    "changed - review, then re-run with force=True."
                )
            else:
                result.logs.append(f"Series '{program}' already exists and is unchanged.")
            return result

        for path, key_index, key_value, rows in plan:
            self._merge(path, key_index, key_value, rows, result)
        self._write_value_tables(snapshot, out, ctx, result)
        self._write_version(out, result)
        result.applied = True
        result.ok = result.error is None
        result.logs.append(f"Exported series '{program}' into {out}")
        return result

    # -- Plan (build every file's rows without writing) -----------------

    def _plan(
        self, snapshot: Snapshot, out: Path, ctx: dict[str, Any]
    ) -> list[tuple[Path, int, str, list[list[Any]]]]:
        """Build every target file's rows as ``(path, key_index, key_value, rows)``
        without touching disk. ``key_value`` is the value the upsert replaces."""
        program = ctx["program"]
        classes = self.context.engineering_class_service.get_classes(snapshot)
        relobj_rows, relation_rows, value_relobj = self._relations(snapshot, ctx)
        scheme_rows, scheme_by_code = self._code_schemes(snapshot, ctx, classes)
        price_lists = self._active_price_lists(snapshot, ctx)
        plan: list[tuple[Path, int, str, list[list[Any]]]] = [
            (out / "xocd_programs.csv", 0, program,
             [[program, ctx["program_id"], ctx["label"], ""]]),
            (out / "xocd_textcategories.csv", 0, ctx["text_category"],
             [[ctx["text_category"], "Default"]]),
            (out / "xocd_relationobj.csv", 0, program, relobj_rows),
            (out / "xocd_relation.csv", 0, program, relation_rows),
            (out / "xocd_article.csv", 0, program, self._articles(snapshot, ctx, scheme_by_code)),
            (out / "xocd_propertyclass.csv", 0, program, self._property_classes(snapshot, ctx, classes)),
            (out / "xocd_property.csv", 0, program, self._properties(snapshot, ctx, classes)),
            (out / "xocd_propertyvalue.csv", 0, program,
             self._property_values(snapshot, ctx, classes, value_relobj)),
            (out / "xocd_artbase.csv", 0, program, self._artbase(snapshot, ctx, classes)),
            (out / "xocd_codescheme.csv", 0, program, scheme_rows),
            (out / "xocd_price.csv", 0, program, self._prices(snapshot, ctx, price_lists)),
            (out / "xocd_packaging.csv", 0, program, self._packaging(snapshot, ctx)),
            # Optional tables with no snapshot source yet - written empty so the
            # package structure is complete; populate when a source exists.
            (out / "xocd_article2propgroup.csv", 0, program, []),
            (out / "xocd_propertygroup.csv", 0, program, []),
            (out / "xocd_rounding.csv", 0, program, []),
            (out / "xocd_articletaxes.csv", 0, program, []),
            (out / "xocd_taxscheme.csv", 0, program, []),
            (out / "xocd_classification.csv", 0, program, []),
        ]
        # One xocd_pricelists row per list (each upserts by its own id).
        for price_list in price_lists:
            plan.append((
                out / "xocd_pricelists.csv", 0, price_list["id"],
                [[price_list["id"], price_list["label"]]],
            ))
        for filename, rows in self._text_files(snapshot, ctx).items():
            plan.append((out / filename, 0, program, rows))
        return plan

    def _program_exists(self, out: Path, program: str) -> bool:
        """True when the series is already registered in ``xocd_programs.csv``."""
        path = out / "xocd_programs.csv"
        if not path.is_file():
            return False
        with path.open("r", encoding=_ENCODING, newline="") as fh:
            return any(row and row[0] == program for row in csv.reader(fh, delimiter=_DELIM))

    def _diff(
        self, path: Path, key_index: int, key_value: str, new_rows: list[list[Any]]
    ) -> dict[str, list[list[str]]]:
        """Row-level diff of this series' rows in ``path`` vs the freshly built
        ``new_rows``: ``{'added': [...], 'removed': [...]}`` (a change = one of each)."""
        existing: set[tuple[str, ...]] = set()
        if path.is_file():
            with path.open("r", encoding=_ENCODING, newline="") as fh:
                for row in csv.reader(fh, delimiter=_DELIM):
                    if row and len(row) > key_index and row[key_index] == key_value:
                        existing.add(tuple(row))
        new = {tuple(self._fmt(v) for v in r) for r in new_rows}
        return {
            "added": [list(r) for r in sorted(new - existing)],
            "removed": [list(r) for r in sorted(existing - new)],
        }

    # -- CSV read / merge / write ---------------------------------------

    def _merge(
        self, path: Path, key_index: int, key_value: str,
        new_rows: list[list[Any]], result: XocdExportResult,
    ) -> None:
        """Upsert: drop existing rows whose ``row[key_index] == key_value``, keep
        every other row (other series, ``*``/``$`` globals), append ``new_rows``."""
        try:
            kept: list[list[str]] = []
            if path.is_file():
                with path.open("r", encoding=_ENCODING, newline="") as fh:
                    for row in csv.reader(fh, delimiter=_DELIM):
                        if not row or (len(row) > key_index and row[key_index] == key_value):
                            continue
                        kept.append(row)
            formatted = [[self._fmt(v) for v in r] for r in new_rows]
            with path.open("w", encoding=_ENCODING, newline="") as fh:
                writer = csv.writer(fh, delimiter=_DELIM, lineterminator=_LINEEND)
                writer.writerows(kept)
                writer.writerows(formatted)
            result.files[path.name] = len(formatted)
        except OSError as exc:
            result.error = f"{path.name}: {exc}"

    @staticmethod
    def _fmt(value: Any) -> str:
        """Format a cell for OCD CSV: bool -> 1/0, None -> '', else str."""
        if value is None:
            return ""
        if isinstance(value, bool):
            return "1" if value else "0"
        return str(value)

    # -- Value-code helper ----------------------------------------------

    def _value_code_map(self, snapshot: Snapshot) -> dict[str, str]:
        """``{value_id: code}`` over property + option values, head-config codes
        resolved via :meth:`resolve_config_codes`."""
        resolved = self.context.engineering_class_service.resolve_config_codes(snapshot)
        flat: dict[str, str] = {}
        for pv in snapshot.property_values:
            code = ((pv.code or "").strip() or resolved.get(str(pv.property_id), {}).get(str(pv.id), ""))
            flat[str(pv.id)] = code.replace("#", "")
        for ov in snapshot.option_values:
            flat[str(ov.id)] = (ov.code or "").strip().replace("#", "")
        return flat

    @staticmethod
    def _prop_ident(name: str) -> str:
        """Valid OCD property identifier: alphanumeric + underscore only, first
        char a letter (pCon rejects spaces/special chars). Parenthetical
        qualifiers are KEPT (as ``_Qualifier``) so distinct properties like
        ``Fabric type`` and ``Fabric type (Secondary)`` don't collapse into one
        name and collide in their class."""
        ident = re.sub(r"[^0-9A-Za-z_]", "", text_block_name(name.replace("(", " ").replace(")", " ")))
        ident = re.sub(r"_+", "_", ident).strip("_")
        if not ident or not ident[0].isalpha():
            ident = "P_" + ident
        return ident

    @staticmethod
    def _ocd_date(value: Any, default: str) -> str:
        """OCD date as ``YYYYMMDD``. Accepts ISO ``YYYY-MM-DD`` (or any
        separatored form) and strips to digits; falls back to ``default`` when
        the source is empty or not a full date."""
        digits = re.sub(r"\D", "", str(value or ""))
        return digits[:8] if len(digits) >= 8 else default

    def _value_lengths(self, snapshot: Snapshot) -> dict[str, int]:
        """``{property_id: max value-code length}`` - the ``Digits`` a Char
        property needs so pCon accepts its values (0 = reject everything)."""
        codes = self._value_code_map(snapshot)
        lengths: dict[str, int] = {}
        for pv in snapshot.property_values:
            code = codes.get(str(pv.id), "")
            lengths[str(pv.property_id)] = max(lengths.get(str(pv.property_id), 0), len(code))
        for ov in snapshot.option_values:
            code = codes.get(str(ov.id), "")
            lengths[str(ov.option_id)] = max(lengths.get(str(ov.option_id), 0), len(code))
        return lengths

    # -- Structural table builders --------------------------------------

    def _base_codes(self, snapshot: Snapshot) -> list[str]:
        """Distinct base article codes, sliced the SAME way prices are.

        The base article MUST match the price ``ArticleID`` (``rec.article_code``,
        the article-set ``base_length`` slice) so pCon can map prices to articles.
        Using ``member.reduced_article`` here diverged from the priced base (e.g.
        reduced 'AER1A11AF' vs priced 'AER'), leaving imported prices unlinked.
        """
        base_of = self._price_base_of(snapshot)
        code_by_id = {str(a.id): a.code for a in snapshot.articles if a.code}
        seen: set[str] = set()
        ordered: list[str] = []
        # Follow member order so the article rows keep their engineering order.
        for family in snapshot.engineering.families:
            for member in family.members:
                code = code_by_id.get(str(getattr(member, "article_id", "")), "")
                base = base_of.get(code) or (member.reduced_article or "").strip()
                if base and base not in seen:
                    seen.add(base)
                    ordered.append(base)
        return ordered

    def _price_base_of(self, snapshot: Snapshot) -> dict[str, str]:
        """Map each article code to its price base (article-set ``base_length``
        slice) - identical to ``PricingService._prefix_by_item`` so xocd_article
        and xocd_price share one base article key."""
        from services.pricing_service import PricingService
        return PricingService(self.context)._prefix_by_item(snapshot)


    def _articles(
        self, snapshot: Snapshot, ctx: dict[str, Any], scheme_by_code: dict[str, str]
    ) -> list[list[Any]]:
        """xocd_article rows (one per distinct base article), linked to their
        generated code scheme via ``SchemeID``."""
        rows: list[list[Any]] = []
        for code in self._base_codes(snapshot):
            rows.append([
                ctx["program"], "", code, "C", _MANUFACTURER_ID, ctx["program_id"],
                code, code, 0, True, "C62", scheme_by_code.get(code, ""),
            ])
        return rows

    def _property_classes(
        self, snapshot: Snapshot, ctx: dict[str, Any], classes: list
    ) -> list[list[Any]]:
        """xocd_propertyclass rows: bind each base article only to the classes of
        its own group (the article set it belongs to), not every class."""
        token_by_base = self._group_token_by_base(snapshot, classes)
        rows: list[list[Any]] = []
        for code in self._base_codes(snapshot):
            token = token_by_base.get(code)
            position = 0
            for cls in classes:
                # Bind only to this base's group's classes. Unknown base -> bind
                # to all (never drop data).
                if token is not None and cls.name.rsplit("_", 1)[0] != token:
                    continue
                rows.append([ctx["program"], code, 100 + position * 10, cls.name, "", 0])
                position += 1
        return rows

    def _group_token_by_base(self, snapshot: Snapshot, classes: list) -> dict[str, str]:
        """base article code -> the class-name token of its group. Each article
        set is matched to the group whose class properties overlap it most; the
        set's base articles inherit that group's token, so a base binds only to
        its group's ``<Token>_*`` classes."""
        token_ents: dict[str, set] = {}
        for cls in classes:
            token = cls.name.rsplit("_", 1)[0]
            token_ents.setdefault(token, set()).update(a.property_id for a in cls.properties)
        base_of = self._price_base_of(snapshot)
        code_by_id = {str(a.id): a.code for a in snapshot.articles if a.code}
        out: dict[str, str] = {}
        for aset in getattr(snapshot, "article_sets", None) or []:
            set_ents = {str(a.id) for a in aset.properties} | {str(a.id) for a in aset.options}
            # Best fit = most overlap, then the SMALLEST group (most specific) so a
            # subset set (e.g. AER7) doesn't get pulled into a larger group (AER).
            best, best_key = None, (0, 0)
            for token, ents in token_ents.items():
                overlap = len(ents & set_ents)
                if overlap == 0:
                    continue
                key = (overlap, -len(ents))
                if key > best_key:
                    best, best_key = token, key
            if best is None:
                continue
            for aid in aset.article_ids:
                code = code_by_id.get(str(aid), "")
                base = base_of.get(code) or code
                if base:
                    out[base] = best
        return out

    def _properties(
        self, snapshot: Snapshot, ctx: dict[str, Any], classes: list
    ) -> list[list[Any]]:
        """xocd_property rows. PropertyName is the normalized identifier (no
        spaces) so relations and the code scheme can reference it."""
        digits = self._value_lengths(snapshot)
        rows: list[list[Any]] = []
        for cls in classes:
            for position, a in enumerate(cls.properties):
                prop_key = self._prop_ident(a.property_name)
                scope = "RG" if (a.usage or "").lower().startswith("g") else "C"
                width = digits.get(a.property_id, 0) or len(prop_key)
                rows.append([
                    ctx["program"], cls.name, prop_key, 100 + position * 10,
                    a.text_block or prop_key, 0, (a.type or "C")[:1] or "C",
                    width, 0, False, False, False, False, scope, 0, "",
                ])
        return rows

    def _property_values(
        self, snapshot: Snapshot, ctx: dict[str, Any], classes: list,
        value_relobj: dict[str, int],
    ) -> list[list[Any]]:
        """xocd_propertyvalue rows (per class property value, keyed by code).
        A value precondition sets ``RelObjID`` to its relation object."""
        pv_by: dict[str, list] = {}
        for pv in snapshot.property_values:
            pv_by.setdefault(str(pv.property_id), []).append(pv)
        ov_by: dict[str, list] = {}
        for ov in snapshot.option_values:
            ov_by.setdefault(str(ov.option_id), []).append(ov)
        codes = self._value_code_map(snapshot)

        rows: list[list[Any]] = []
        for cls in classes:
            for a in cls.properties:
                # Text (T) properties take free-text input, not enumerated values;
                # pCon rejects values on them, so never emit value rows for them.
                if (a.type or "").strip().upper().startswith("T"):
                    continue
                prop_key = self._prop_ident(a.property_name)
                values = pv_by.get(a.property_id) or ov_by.get(a.property_id) or []
                # PDM lists a value once per product sub-series, so the union
                # carries the same value under several ids. Collapse them exactly
                # as Class Creation does (keep the coded twin, distinct codes).
                values = collapse_duplicate_values(values, lambda v: codes.get(str(v.id), ""))
                pos = 0
                # OCD requires a unique code per property. After collapsing true
                # duplicates, distinct values that still decode to the same code
                # (a lumped property golden models as several) would collide, so
                # keep the first per code.
                seen_codes: set[str] = set()
                for value in values:
                    code = codes.get(str(value.id), "")
                    if not code or code in seen_codes:
                        continue
                    seen_codes.add(code)
                    rows.append([
                        ctx["program"], "", cls.name, prop_key, 100 + pos * 10,
                        f"{prop_key}_{code}", value_relobj.get(str(value.id), 0),
                        False, False, "EQ", code, "", "", "", "", "",
                    ])
                    pos += 1
        return rows

    def _relations(
        self, snapshot: Snapshot, ctx: dict[str, Any]
    ) -> tuple[list[list[Any]], list[list[Any]], dict[str, int]]:
        """xocd_relationobj + xocd_relation rows, plus ``{value_id: relobj_id}``.

        XOCD links a relation object to its knowledge by NAME (``RelName`` ==
        ``RelationName``); the body is split into ``BlockNr`` lines of <= 255
        characters. ``RelObjID`` is the only numeric key in the XOCD data.
        """
        relation_objects = self.context.engineering_relation_service.build_relation_objects(snapshot)
        obj_rows: list[list[Any]] = []
        rel_rows: list[list[Any]] = []
        value_relobj: dict[str, int] = {}
        next_id = 1
        for rel in relation_objects:
            rel_id = next_id
            next_id += 1
            obj_rows.append([ctx["program"], rel_id, rel.order, rel.name, rel.type_code, rel.domain])
            block_nr = 1
            for line in (rel.body or "").splitlines() or [""]:
                chunk = line
                while len(chunk) > _CODE_BLOCK_MAX:
                    rel_rows.append([ctx["program"], rel.name, block_nr, chunk[:_CODE_BLOCK_MAX]])
                    block_nr += 1
                    chunk = chunk[_CODE_BLOCK_MAX:]
                rel_rows.append([ctx["program"], rel.name, block_nr, chunk])
                block_nr += 1
            if getattr(rel, "value_id", ""):
                value_relobj[str(rel.value_id)] = rel_id
        return obj_rows, rel_rows, value_relobj

    def _code_schemes(
        self, snapshot: Snapshot, ctx: dict[str, Any], classes: list
    ) -> tuple[list[list[Any]], dict[str, str]]:
        """xocd_codescheme rows + ``{article_code: scheme_id}``.

        Builds the OCD code-scheme body per base article: ``@`` for each
        character of the base article number, then a ``<Class>:<Property>`` token
        for every coded config/option property (Visual classes excluded). Property
        tokens are separated from one another by a literal space token - the
        grammar used in the manufacturer's own data.
        """
        # Coded config/option properties, as (class name, normalized identifier).
        codes = self._value_code_map(snapshot)
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
                    prop_tokens.append(f"{cls.name}:{self._prop_ident(a.property_name)}")

        # Intersperse a literal space token between consecutive property tokens.
        tokens: list[str] = []
        for i, tok in enumerate(prop_tokens):
            if i:
                tokens.append(" ")
            tokens.append(tok)

        rows: list[list[Any]] = []
        scheme_by_code: dict[str, str] = {}
        for code in self._base_codes(snapshot):
            body = ",".join(["@"] * len(code) + tokens)
            scheme_id = code
            scheme_by_code[code] = scheme_id
            # SchemeID, Scheme(body), VarCodeSep, ValueSep, Visibility,
            # InVisibleChar, UnselectChar, Trim, MO_Sep, MO_Bracket.
            rows.append([ctx["program"], scheme_id, body, "", "", "0", "-", "X", True, "", ""])
        return rows, scheme_by_code

    @staticmethod
    def _active_price_lists(snapshot: Snapshot, ctx: dict[str, Any]) -> list[dict]:
        """The price lists driving the price export: the snapshot's defined lists
        (id/label/currency/validity), or - when none are defined - one default
        list PER CURRENCY actually priced. OCD requires a price list to be
        single-currency, so a multi-currency snapshot must never share one list.
        """
        defined = getattr(snapshot, "price_lists", None) or []
        if defined:
            return [
                {
                    "id": pl.id,
                    "label": pl.label or pl.id,
                    "currency": (pl.currency or "").upper(),
                    "date_from": pl.date_from or "",
                    "date_to": pl.date_to or "",
                }
                for pl in defined
            ]
        pid = ctx["price_list"]
        currencies = sorted({
            (r.currency or "").upper()
            for r in snapshot.price_records if (r.currency or "").strip()
        })
        if len(currencies) <= 1:
            cur = currencies[0] if currencies else ""
            return [{"id": pid, "label": pid, "currency": cur,
                     "date_from": "", "date_to": ""}]
        return [
            {"id": f"{pid}_{cur}", "label": f"{pid} {cur}", "currency": cur,
             "date_from": "", "date_to": ""}
            for cur in currencies
        ]

    def _prices(
        self, snapshot: Snapshot, ctx: dict[str, Any], price_lists: list[dict]
    ) -> list[list[Any]]:
        """xocd_price rows from ``snapshot.price_records``, emitted once per price
        list: a list with a currency takes only its currency's records and stamps
        the list's validity window; the fallback list (no currency) takes every
        record with its source dates. Global rows use ``*`` for ArticleID."""
        rows: list[list[Any]] = []
        for price_list in price_lists:
            want = price_list["currency"]
            for rec in snapshot.price_records:
                if want and (rec.currency or "").upper() != want:
                    continue
                article = "*" if getattr(rec, "is_global", False) else (rec.article_code or "")
                level = (rec.level or "B").strip() or "B"
                fix = level in ("B", "X")  # base/extra = fix amount; D = percentage
                # Per-list validity when the list defines it; else the record's
                # own dates, falling back to the broad "always valid" range.
                date_from = price_list["date_from"] or self._ocd_date(rec.valid_from, _DATE_MIN)
                date_to = price_list["date_to"] or self._ocd_date(rec.valid_to, _DATE_MAX)
                rows.append([
                    ctx["program"], price_list["id"], article, rec.variant_condition or "",
                    "S", level, "", "", rec.value, fix, rec.currency or "",
                    date_from, date_to, "",
                ])
        return rows

    def _packaging(self, snapshot: Snapshot, ctx: dict[str, Any]) -> list[list[Any]]:
        """xocd_packaging rows from base-article dimensions/weight/volume, where
        present (UN/ECE units: MMT=mm, LTR=litre, KGM=kg)."""
        by_code: dict[str, Any] = {}
        for a in snapshot.articles:
            if a.code and a.code not in by_code:
                by_code[a.code] = a
        rows: list[list[Any]] = []
        for code in self._base_codes(snapshot):
            art = by_code.get(code)
            if art is None:
                continue
            w, h, d, vol, wt = art.width, art.height, art.depth, art.volume_l, art.weight_kg
            if not any(v for v in (w, h, d, vol, wt)):
                continue
            dim_unit = "MMT" if any(v for v in (w, h, d)) else ""
            rows.append([
                ctx["program"], code, "", w or "", h or "", d or "", dim_unit,
                vol or "", "LTR" if vol else "", "", wt or "", "KGM" if wt else "",
                "", "",
            ])
        return rows

    def _write_value_tables(
        self, snapshot: Snapshot, out: Path, ctx: dict[str, Any], result: XocdExportResult
    ) -> None:
        """Write each value combination table as ``<Program>_<name>_tbl.csv`` (the
        OCD ``LineNr;PROP;VAL`` format, one file per series+table)."""
        svc = self.context.engineering_value_table_service
        for table in svc.ensure_value_tables(snapshot):
            csv_rows = svc.to_csv_rows(table)
            path = out / f"{ctx['program']}_{table.name}_tbl.csv"
            try:
                text = _LINEEND.join(csv_rows)
                if csv_rows:
                    text += _LINEEND
                path.write_text(text, encoding=_ENCODING)
                result.files[path.name] = len(csv_rows)
            except OSError as exc:
                result.error = f"{path.name}: {exc}"

    def _write_version(self, out: Path, result: XocdExportResult) -> None:
        """Write the package-wide ``xocd_version.csv`` (single row): OCD format
        version + relation-coding language layer + validity + region.

        Region = the master distribution region (OFML standard ``ANY``); pCon's
        OCD export later splits it into the market regions (EURO/GBP/NOPRICE).
        """
        region = self.context.distribution_region_service.master_region_code()
        # FormatVersion, RelCoding, DataVersion, DateFrom, DateTo, Region,
        # VarCondVar, PlaceHolderOn, Tables, Comment.
        row = ["4.2", "OCD_4", "1.0.0", _DATE_MIN, _DATE_MAX, region,
               "", False, "", ""]
        path = out / "xocd_version.csv"
        try:
            with path.open("w", encoding=_ENCODING, newline="") as fh:
                csv.writer(fh, delimiter=_DELIM, lineterminator=_LINEEND).writerow(
                    [self._fmt(v) for v in row]
                )
            result.files[path.name] = 1
        except OSError as exc:
            result.error = f"{path.name}: {exc}"

    def _artbase(
        self, snapshot: Snapshot, ctx: dict[str, Any], classes: list
    ) -> list[list[Any]]:
        """xocd_artbase rows from ``build_art_base`` (per-base allowed values)."""
        art_base = self.context.engineering_artbase_service.build_art_base(snapshot)
        if not art_base:
            return []
        # (token, prop) -> (class name, prop ident), so a base picks the class of
        # its OWN group when a property is shared across group classes.
        by_token_prop: dict[tuple[str, str], tuple[str, str]] = {}
        entity_meta: dict[str, tuple[str, str]] = {}
        for cls in classes:
            token = cls.name.rsplit("_", 1)[0]
            for a in cls.properties:
                ident = self._prop_ident(a.property_name)
                by_token_prop[(token, a.property_id)] = (cls.name, ident)
                entity_meta[a.property_id] = (cls.name, ident)
        token_by_base = self._group_token_by_base(snapshot, classes)
        codes = self._value_code_map(snapshot)
        rows: list[list[Any]] = []
        seen: set[tuple[str, str, str, str]] = set()
        for base_code, prop_map in art_base.items():
            token = token_by_base.get(base_code)
            for prop_id, value_ids in prop_map.items():
                meta = by_token_prop.get((token, prop_id)) or entity_meta.get(prop_id)
                if meta is None:
                    continue
                class_name, prop_name = meta
                for value_id in value_ids:
                    code = codes.get(str(value_id), "")
                    if not code:
                        continue
                    key = (base_code, class_name, prop_name, code)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append([ctx["program"], "", base_code, class_name, prop_name, code])
        return rows

    # -- Text (description) tables --------------------------------------

    def _text_files(
        self, snapshot: Snapshot, ctx: dict[str, Any]
    ) -> dict[str, list[list[Any]]]:
        """Per-type description files. One row per (TextID, language, line):
        ``[Program, TextCat, TextID, Language, LineNr, TextLine]`` with each
        text split into <= 80-character lines."""
        blocks = self.context.engineering_text_service.ensure_text_blocks(snapshot)
        files: dict[str, list[list[Any]]] = {}
        for block in blocks:
            filename = _TEXT_FILES.get(block.type_code)
            if filename is None:
                continue
            rows = files.setdefault(filename, [])
            for lang in LANGUAGES:
                text = getattr(block, lang, "") or ""
                if not text:
                    continue
                line_nr = 1
                for physical in text.splitlines() or [text]:
                    chunk = physical
                    while len(chunk) > _TEXT_LINE_MAX:
                        rows.append([ctx["program"], ctx["text_category"], block.name,
                                     lang, line_nr, chunk[:_TEXT_LINE_MAX]])
                        line_nr += 1
                        chunk = chunk[_TEXT_LINE_MAX:]
                    rows.append([ctx["program"], ctx["text_category"], block.name,
                                 lang, line_nr, chunk])
                    line_nr += 1
        return files
