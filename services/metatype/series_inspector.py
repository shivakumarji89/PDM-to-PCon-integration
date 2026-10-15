"""Step 1 of Metatype creation: summarise a series' existing conventions (read-only).

Requirement source: ``POLYMORPHIC_METATYPE_CREATION_TEMPLATE_04092026.md``,
"Step 1 - Read the repository / series data first" (authoritative copy:
``...\\HermanMiller\\AI\\Prompts\\Claude Code\\``). The template asks to inspect

* ``go_types.csv``      - naming pattern, prefixes, flags,
* ``go_propvalues.csv`` and ``go_proporder.csv`` - property/value structure,
* ``go_children.csv``   - existing parent/child patterns,
* in-series ``docs/*.md`` notes,

and to summarise the findings for the user before Step 2. If the target series
has "few or no" examples it names ``hmx/atlas``, ``hmx/pullman`` and
``hmx/layout`` as structural references.

What the template does NOT define, and this module therefore does not decide
(see ``UNRESOLVED``): what "few" means, and which family ``hmx/layout`` is.
The reference series are only consulted automatically when the target defines
no Metatype at all, or when the caller names them explicitly.

``go_texts`` is never interpreted or even opened: the template's Step 1 does not ask for it and
its encoding is an open owner decision. All reading goes through the existing
:class:`MetatypeTableLoader`; the result is returned, not written anywhere.
"""
from __future__ import annotations

import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from models.metatype_series import (
    ChildrenConvention,
    CountedValue,
    Evidence,
    InspectionStatus,
    MetatypeSummary,
    ModeUsage,
    PropertyRef,
    PropOrderConvention,
    PropValuesConvention,
    SeriesConventions,
    SeriesInspection,
    SeriesStatus,
    SourceTable,
    TypesConventions,
)
from models.metatype_tables import LoadedTable, MetatypeFamilyTables, TableLoadState
from services.metatype.metatype_table_loader import MetatypeTableLoader

INSPECTOR_VERSION = "1.0.0"

#: Tables Step 1 reads. Nothing else is interpreted.
STEP1_TABLES = ("go_types", "go_propvalues", "go_proporder", "go_children")
#: Not read: not part of Step 1, and the legacy code page is an undecided owner question.
EXCLUDED_TABLES = ("go_texts",)
#: Template names these families literally ("hmx/layout" has no matching family; see UNRESOLVED).
TEMPLATE_REFERENCE_SERIES = ("atlas", "pullman")

UNRESOLVED = (
    "Template Step 1 consults reference series when the target has 'few or no' examples; 'few' is not "
    "defined, so the reference series are used automatically only when the target defines no Metatype.",
    "The template names 'hmx/layout' as a reference; no family of that name exists (the nearest is "
    "'layout_studio'). It is not substituted; pass it explicitly to use it.",
    "The template says to read in-series 'docs/*.md' notes; none exist in the current HMX data, so only "
    "their names are listed and their content is not interpreted.",
)

#: Documented mode bits (Metatype.md section 5.4).
_BIT_VARIANT, _BIT_CHILD, _BIT_ORDER, _BIT_VALUES = 4, 8, 128, 8192
_MAX_BITS = 16
_EXAMPLES = 3
_REQUIRED_COLUMNS = {
    "go_types": ("id", "name", "format", "default", "mode"),
    "go_propvalues": ("id", "name", "value", "condition"),
    "go_proporder": ("value", "number"),
    "go_children": ("child_key", "manufacturer", "program", "condition"),
}


class SeriesInspector:
    """Inspect one target series, optionally with reference series."""

    def __init__(self, loader: MetatypeTableLoader | None = None) -> None:
        self._loader = loader or MetatypeTableLoader()

    # -- filesystem seam (overridden in tests) -------------------------------------
    def _stat(self, path: str) -> os.stat_result:
        return os.stat(path)

    def _list_names(self, path: Path) -> list[str]:
        with os.scandir(path) as iterator:
            return sorted(entry.name for entry in iterator if entry.is_file())

    # -- public API ------------------------------------------------------------------
    def inspect_series(
        self,
        root: str | Path,
        family_id: str,
        directory: str | None = None,
        reference_series: tuple[str, ...] | list[str] | None = None,
    ) -> SeriesInspection:
        """Summarise ``family_id`` (and, when asked or needed, reference series).

        ``reference_series=None`` applies the template default only if the target
        has no Metatype; an explicit list is always inspected (minus the target).
        """
        result = SeriesInspection(
            repository_root=str(root), target_series=family_id,
            inspected_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            inspector_version=INSPECTOR_VERSION, status=InspectionStatus.FAILED,
            unresolved=list(UNRESOLVED), excluded_tables=list(EXCLUDED_TABLES),
        )
        if not str(root).strip() or not family_id.strip():
            result.messages.append("A repository root and a target series are required.")
            return result

        result.target = self._inspect_family(root, family_id, directory)
        if result.target.status is SeriesStatus.OK:
            result.status = InspectionStatus.OK

        if reference_series is not None:
            wanted = list(dict.fromkeys(reference_series))
            reason = "reference series requested by the caller"
        elif result.target.status is not SeriesStatus.OK:
            wanted = list(TEMPLATE_REFERENCE_SERIES)
            reason = (f"{family_id} defines no Metatype, so the template's reference series are used "
                      "(template Step 1)")
        else:
            wanted, reason = [], ""
        wanted = [name for name in wanted if name != family_id]
        if wanted:
            result.reference_reason = reason
            result.references = [self._inspect_family(root, name, None) for name in wanted]
        if result.status is not InspectionStatus.OK:
            usable = any(ref.status is SeriesStatus.OK for ref in result.references)
            result.status = InspectionStatus.REFERENCE_ONLY if usable else InspectionStatus.INSUFFICIENT
        return result

    def check_staleness(self, inspection: SeriesInspection) -> list[str]:
        """Paths of inspected source files whose size/mtime differ now (or that vanished)."""
        changed: list[str] = []
        for series in ([inspection.target] if inspection.target else []) + inspection.references:
            for source in series.sources:
                if source.modified_ns is None or not source.path:
                    continue
                try:
                    now = self._stat(source.path)
                except OSError:
                    changed.append(source.path)
                    continue
                if now.st_mtime_ns != source.modified_ns or now.st_size != source.size_bytes:
                    changed.append(source.path)
        return changed

    # -- one family ------------------------------------------------------------------
    def _inspect_family(self, root, family_id: str, directory: str | None) -> SeriesConventions:
        tables = self._loader.load_family(root, family_id, directory, tables=STEP1_TABLES)
        series = SeriesConventions(family_id=family_id, status=SeriesStatus.FAILED, directory=tables.directory)
        series.docs_files = self._find_docs(Path(root) / family_id, tables.directory)
        if not tables.tables:
            series.notes += [f"[{d.code}] {d.message}" for d in tables.diagnostics] or ["Nothing was loaded."]
            return series

        usable: dict[str, LoadedTable] = {}
        for name in STEP1_TABLES:
            table = tables.table(name)
            series.sources.append(self._source(name, table))
            if table is None:
                series.notes.append(f"{name} is not declared by mt.inp_descr.")
            elif table.state in (TableLoadState.DECODE_ERROR, TableLoadState.UNREADABLE, TableLoadState.MISSING):
                series.notes.append(f"{table.file_name} is {table.state.value}; it was not inspected.")
            elif missing := [c for c in _REQUIRED_COLUMNS[name] if c not in table.columns]:
                series.notes.append(f"{table.file_name} lacks column(s) {', '.join(missing)}; not inspected.")
            else:
                usable[name] = table
                if table.state is TableLoadState.MALFORMED:
                    series.notes.append(
                        f"{table.file_name}: {len(table.rejected_lines)} line(s) were rejected while loading, "
                        "so the counts may be incomplete.")
                elif not table.rows:
                    series.notes.append(f"{table.file_name} holds no data rows.")

        if "go_types" in usable:
            series.types = _types(usable["go_types"], series.family_id)
        if "go_propvalues" in usable:
            series.propvalues = _propvalues(usable["go_propvalues"], series.types)
        if "go_proporder" in usable:
            series.proporder = _proporder(usable["go_proporder"])
        if "go_children" in usable:
            series.children = _children(usable["go_children"])
        if not series.docs_files:
            series.notes.append("No in-series .md notes were found.")

        if series.types.metatype_count:
            series.status = SeriesStatus.OK
        else:
            series.status = SeriesStatus.NO_EXAMPLES
            series.notes.append("go_types defines no Metatype, so there are no existing examples.")
        return series

    def _source(self, name: str, table: LoadedTable | None) -> SourceTable:
        if table is None:
            return SourceTable(name, f"{name}.csv", "", "not_declared")
        source = SourceTable(
            table.table, table.file_name, table.path, table.state.value, table.size_bytes,
            row_count=len(table.rows), rejected_line_count=len(table.rejected_lines),
        )
        if table.state is not TableLoadState.MISSING:
            try:
                info = self._stat(table.path)
                source.modified_ns, source.size_bytes = info.st_mtime_ns, info.st_size
            except OSError as exc:
                source.note = f"could not stat: {exc}"
        return source

    def _find_docs(self, family_path: Path, directory: str) -> list[str]:
        found: list[str] = []
        spots = [family_path / "docs", family_path]
        if directory:
            spots.append(family_path / directory)
        for spot in spots:
            try:
                found += [str(spot / name) for name in self._list_names(spot) if name.lower().endswith(".md")]
            except OSError:
                continue
        return found


# -- helpers --------------------------------------------------------------------------------------
def _records(table: LoadedTable):
    """Yield ``(line, {column: trimmed value}, trimmed tuple)``."""
    for row in table.rows:
        values = row.trimmed()
        yield row.line, dict(zip(table.columns, values)), values


def _prefix(name: str) -> str:
    """Leading part up to and including the first underscore ('' when there is none)."""
    head, sep, _ = name.partition("_")
    return head + sep if sep else ""


def _counted(counter: Counter, evidence: dict[str, list[Evidence]], limit: int | None = None) -> list[CountedValue]:
    ordered = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    return [CountedValue(value, count, evidence.get(value, [])) for value, count in ordered[:limit]]


def _note(store: dict[str, list[Evidence]], key: str, evidence: Evidence) -> None:
    items = store.setdefault(key, [])
    if len(items) < _EXAMPLES:
        items.append(evidence)


def _bits(mode: int) -> list[int]:
    return [1 << i for i in range(_MAX_BITS) if mode & (1 << i)]


def _types(table: LoadedTable, family_id: str) -> TypesConventions:
    out = TypesConventions(template_prefix=f"G{family_id.upper()}_")
    per_metatype: dict[str, list[int]] = {}
    meta_ev: dict[str, list[Evidence]] = {}
    id_prefix, prop_prefix, formats, modes, settings = Counter(), Counter(), Counter(), Counter(), Counter()
    id_ev: dict[str, list[Evidence]] = {}
    prop_ev: dict[str, list[Evidence]] = {}
    fmt_ev: dict[str, list[Evidence]] = {}
    set_ev: dict[str, list[Evidence]] = {}
    mode_ev: dict[int, list[Evidence]] = {}
    bit_counts: Counter = Counter()

    for line, rec, values in _records(table):
        evidence = Evidence(table.table, line, values)
        out.defined_properties.append(evidence)
        mt_id, name, fmt = rec["id"], rec["name"], rec["format"]
        counts = per_metatype.setdefault(mt_id, [0, 0])
        _note(meta_ev, mt_id, evidence)
        if not fmt:
            counts[1] += 1
            key = f"{name} = {rec['default']}"
            settings[key] += 1
            _note(set_ev, key, evidence)
            continue
        counts[0] += 1
        formats[fmt] += 1
        _note(fmt_ev, fmt, evidence)
        if fmt == "na":
            out.native_wrapper_count += 1
            if len(out.native_wrapper_examples) < _EXAMPLES:
                out.native_wrapper_examples.append(evidence)
        else:
            pre = _prefix(name) or "(no underscore)"
            prop_prefix[pre] += 1
            _note(prop_ev, pre, evidence)
            if name.startswith(out.template_prefix):
                out.properties_following_template_prefix += 1
        try:
            mode = int(rec["mode"])
        except ValueError:
            out.non_numeric_modes.append(evidence)
            continue
        modes[mode] += 1
        mode_ev.setdefault(mode, [])
        if len(mode_ev[mode]) < _EXAMPLES:
            mode_ev[mode].append(evidence)
        ref = PropertyRef(mt_id, name, mode, evidence)
        for bit in _bits(mode):
            bit_counts[bit] += 1
        if mode & _BIT_VARIANT:
            out.polymorphism_properties.append(ref)
        if mode & _BIT_CHILD:
            out.child_properties.append(ref)
        if mode & _BIT_ORDER:
            out.ordered_properties.append(ref)
        if mode & _BIT_VALUES:
            out.value_limited_properties.append(ref)

    for mt_id, (props, sets) in per_metatype.items():
        id_prefix[_prefix(mt_id) or "(no underscore)"] += 1
        id_ev.setdefault(_prefix(mt_id) or "(no underscore)", []).extend(meta_ev[mt_id][:1])
    out.metatype_count = len(per_metatype)
    out.metatypes = [MetatypeSummary(i, p, s, meta_ev[i]) for i, (p, s) in sorted(per_metatype.items())]
    out.metatype_id_prefixes = _counted(id_prefix, id_ev)
    out.property_prefixes = _counted(prop_prefix, prop_ev)
    out.settings = _counted(settings, set_ev)
    out.formats = _counted(formats, fmt_ev)
    out.modes = [ModeUsage(m, c, _bits(m), mode_ev[m]) for m, c in sorted(modes.items(), key=lambda i: (-i[1], i[0]))]
    out.bit_counts = dict(sorted(bit_counts.items()))
    return out


def _propvalues(table: LoadedTable, types: TypesConventions) -> PropValuesConvention:
    out = PropValuesConvention()
    per_prop: Counter = Counter()
    ev: dict[str, list[Evidence]] = {}
    for line, rec, values in _records(table):
        evidence = Evidence(table.table, line, values)
        out.row_count += 1
        key = f"{rec['id']} / {rec['name']}"
        per_prop[key] += 1
        _note(ev, key, evidence)
        if rec["condition"]:
            out.rows_with_condition += 1
            if len(out.condition_examples) < _EXAMPLES:
                out.condition_examples.append(evidence)
    out.properties = _counted(per_prop, ev)
    flagged = {f"{p.metatype} / {p.name}" for p in types.value_limited_properties}
    out.flagged_without_rows = sorted(flagged - set(per_prop))
    # Only meaningful when go_types was read; otherwise there is nothing to compare with.
    if types.metatype_count:
        out.rows_without_flag = sorted(set(per_prop) - flagged)
    return out


def _proporder(table: LoadedTable) -> PropOrderConvention:
    out = PropOrderConvention()
    numbers: list[int] = []
    for line, rec, values in _records(table):
        evidence = Evidence(table.table, line, values)
        out.row_count += 1
        out.entries.append(evidence)
        try:
            numbers.append(int(rec["number"]))
        except ValueError:
            out.non_numeric.append(evidence)
    if numbers:
        out.min_number, out.max_number = min(numbers), max(numbers)
        steps = Counter(b - a for a, b in zip(numbers, numbers[1:]) if b > a)
        if steps:
            out.common_step = sorted(steps.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return out


def _children(table: LoadedTable) -> ChildrenConvention:
    out = ChildrenConvention()
    keys, prefixes, makers, programs = Counter(), Counter(), Counter(), Counter()
    key_ev: dict[str, list[Evidence]] = {}
    pre_ev: dict[str, list[Evidence]] = {}
    maker_ev: dict[str, list[Evidence]] = {}
    prog_ev: dict[str, list[Evidence]] = {}
    for line, rec, values in _records(table):
        evidence = Evidence(table.table, line, values)
        out.row_count += 1
        key = rec["child_key"]
        keys[key] += 1
        _note(key_ev, key, evidence)
        pre = _prefix(key) or "(no underscore)"
        prefixes[pre] += 1
        _note(pre_ev, pre, evidence)
        makers[rec["manufacturer"]] += 1
        _note(maker_ev, rec["manufacturer"], evidence)
        programs[rec["program"]] += 1
        _note(prog_ev, rec["program"], evidence)
        if rec["condition"]:
            out.rows_with_condition += 1
            if len(out.condition_examples) < _EXAMPLES:
                out.condition_examples.append(evidence)
    out.distinct_keys = len(keys)
    out.key_prefixes = _counted(prefixes, pre_ev)
    out.repeated_keys = _counted(Counter({k: c for k, c in keys.items() if c > 1}), key_ev)
    out.manufacturers = _counted(makers, maker_ev)
    out.programs = _counted(programs, prog_ev)
    return out


# -- plain-text summary -----------------------------------------------------------------------------
def format_inspection_summary(result: SeriesInspection) -> str:
    """Brief summary for the user (template Step 1: 'summarize briefly what you found')."""
    lines = [f"Series conventions for {result.target_series} - {result.status.value}"]
    lines += [f"  {m}" for m in result.messages]
    if result.target is not None:
        lines += _series_lines(result.target, "  ")
    if result.references:
        lines.append(f"Reference series ({result.reference_reason}):")
        for ref in result.references:
            lines += _series_lines(ref, "  ")
    lines.append("Not read: " + ", ".join(result.excluded_tables) + " (not part of Step 1).")
    lines.append("Open decisions:")
    lines += [f"  - {item}" for item in result.unresolved]
    return "\n".join(lines)


def _top(items: list[CountedValue], n: int = 4) -> str:
    return ", ".join(f"{i.value} x{i.count}" for i in items[:n]) or "none"


def _series_lines(series: SeriesConventions, pad: str) -> list[str]:
    lines = [f"{pad}{series.family_id}/{series.directory or '?'}: {series.status.value}"]
    if series.status is SeriesStatus.FAILED:
        return lines + [f"{pad}  {note}" for note in series.notes]
    t, v, o, c = series.types, series.propvalues, series.proporder, series.children
    lines += [
        f"{pad}  go_types: {t.metatype_count} metatype(s); id prefix {_top(t.metatype_id_prefixes)}; "
        f"property prefix {_top(t.property_prefixes)} (template expects {t.template_prefix}, "
        f"{t.properties_following_template_prefix} follow it); {t.native_wrapper_count} native wrapper(s) (na) not grouped",
        f"{pad}  modes: {', '.join(f'{m.mode} x{m.count}' for m in t.modes[:6]) or 'none'}; "
        f"polymorphism(4): {len(t.polymorphism_properties)}, child(8): {len(t.child_properties)}, "
        f"value-limited(8192): {len(t.value_limited_properties)}",
        f"{pad}  go_propvalues: {v.row_count} row(s), {v.rows_with_condition} with a condition",
        f"{pad}  go_proporder: {o.row_count} row(s), common step {o.common_step}",
        f"{pad}  go_children: {c.row_count} row(s), {c.distinct_keys} key(s), prefix {_top(c.key_prefixes)}, "
        f"{len(c.repeated_keys)} repeated key(s), {c.rows_with_condition} conditional",
        f"{pad}  docs notes: {len(series.docs_files)} file(s)",
    ]
    lines += [f"{pad}  note: {note}" for note in series.notes]
    return lines
