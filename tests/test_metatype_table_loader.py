"""Metatype table loader: real-format fixtures (shapes copied from the HMX repository)."""
import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

import services.metatype.metatype_table_loader as loader_module
from core.application_context import ApplicationContext
from core.config import AppConfig
from models.metatype_scan import BuildStatus
from models.metatype_tables import LoadStatus, TableLoadState
from services.metatype.metatype_table_loader import MetatypeTableLoader, parse_table_text, split_fields
from services.metatype.metatype_table_loader_service import MetatypeTableLoaderService
from services.metatype.repository_scanner import MetatypeRepositoryScanner
from services.metatype.schema_parser import parse_mt_schema

# Same shape as the real mt.inp_descr: TAB separated, "comment ... end comment"
# disables go_propindex/go_propmapping (as in all 49 real files).
MT_INP_DESCR = (
    "# GO III (MT) Input Description, Version 1.16\n"
    "# Copyright (C) 2002-2012 EasternGraphics.\n"
    "name    go_tables\n\n"
    "table   go_types\tgo_types.csv\t\tcsv\nfields  6\n"
    "field   1  id\t\tvstring\t\tdelim ; trim hidx link\n"
    "field   2  name\t\tvstring\t\tdelim ; trim hidx link\n"
    "field   3  format\tvstring\t\tdelim ; trim\n"
    "field   4  default\tvstring\t\tdelim ; trim\n"
    "field   5  mode\t\tuint16\t\ttrim\n"
    "field   6  filter\tvstring\t\tdelim ; trim\n"
    "index btree id name\n\n"
    "table   go_children\tgo_children.csv\t\tcsv\nfields  4\n"
    "field   1  child_key\tvstring\tdelim ; trim\n"
    "field   2  manufacturer\tvstring\tdelim ; trim\n"
    "field   3  program\tvstring\tdelim ; trim\n"
    "field   4  condition\tvstring\tdelim ; trim\n\n"
    "table   go_actions\tgo_actions.csv\t\tcsv\nfields  3\n"
    "field   1  id\t\tvstring\tdelim ; trim\n"
    "field   2  own_key\tvstring\tdelim ; trim\n"
    "field   3  action\tvstring\tdelim ; trim\n\n"
    "table   go_texts\tgo_texts.csv\t\tcsv\nfields  3\n"
    "field   1  key\t\tvstring\tdelim ; trim\n"
    "field   2  language\tvstring\tdelim ; trim\n"
    "field   3  text\t\tvstring\tdelim ; trim\n\n"
    "table   go_info\tgo_info.csv\t\tcsv\nfields  2\n"
    "field   1  key\t\tvstring\tdelim ; trim\n"
    "field   2  value\tvstring\tdelim ; trim\n\n"
    "comment\n\nThe following tables must be customized!\n\n"
    "table   go_propindex\tgo_propindex.csv\tcsv\nfields  2\n"
    "field   1  id\t\tvstring\tdelim ; trim\nfield   2  key\t\tvstring\tdelim ; trim\n\n"
    "end comment\n"
)
GO_TYPES = (
    "################################################################\r\n"
    "#\r\n#   Atlas - Types\r\n#\r\n"
    "################################################################\r\n"
    "\r\n"
    "MT_ATLAS       ;GATLAS_Type      ;ch ;@ATLAS_Type_SG ;131  ;\r\n"
    "MT_ATLAS       ;GATLAS_OffsetX   ;fn ;0              ;3    ;GATLAS_OffsetZ\r\n"
)
GO_CHILDREN = "CH_FE21         ;hmx            ;cyclade_tables ;\r\n"   # empty last field, as in real go_children
GO_ACTIONS = "MT_X;GVERUS_Type;SET_PROP\r\nchild_GrommetMeeting\r\nchild_BachmannFrame_Small\r\nMT_X;GA;CON_PROP"
GO_TEXTS = (
    "SETU_REFRESH_Type_MCD  ;de; Farben \"Dipped in colour\"\r\n"      # interior quote is data
    "GAE_Type_C \t\t\t ;en;Work Chair Size C\r\n"
    "KEY_Q;en;\"say \"\"hi\"\"; then go\"\r\n"                         # quoted, ';' and "" inside
)


def make_family(root: Path, name="atlas", directory="1", **files):
    data = root / name / directory
    data.mkdir(parents=True)
    defaults = {
        "mt.inp_descr": MT_INP_DESCR,
        "go_types.csv": GO_TYPES, "go_children.csv": GO_CHILDREN,
        "go_actions.csv": "", "go_texts.csv": GO_TEXTS, "go_info.csv": "",
    }
    defaults.update(files)
    for file_name, content in defaults.items():
        if content is None:
            continue
        payload = content if isinstance(content, bytes) else content.encode("utf-8")
        (data / file_name).write_bytes(payload)
    return data


@pytest.fixture
def root(tmp_path):
    path = tmp_path / "hmx"
    path.mkdir()
    return path


def load(root, family="atlas", **kwargs):
    return MetatypeTableLoader(**kwargs.pop("loader", {})).load_family(root, family, **kwargs)


def codes(diagnostics):
    return [d.code for d in diagnostics]


# parsing ----------------------------------------------------------------------
@pytest.mark.parametrize("line, expected", [
    ("a;b;c", ["a", "b", "c"]),
    ("a;;c;", ["a", "", "c", ""]),                                  # trailing separator = empty last field
    (" a ; b ", [" a ", " b "]),                                    # padding preserved
    ('Farben "x" y;z', ['Farben "x" y', "z"]),                      # interior quote is data
    (' "x";y', [' "x"', "y"]),                                      # quote not at field start is data
    ('"a;b";c', ["a;b", "c"]),
    ('"say ""hi""";c', ['say "hi"', "c"]),
    ('"";x', ["", "x"]),
    ("", [""]),
])
def test_split_fields_follows_the_metatype_quoting_rule(line, expected):
    assert split_fields(line) == expected


@pytest.mark.parametrize("line, code", [('"open;x', "UNTERMINATED_QUOTE"), ('"a"b;c', "TEXT_AFTER_QUOTE")])
def test_split_fields_rejects_bad_quotes(line, code):
    from services.metatype.metatype_table_loader import QuoteError
    with pytest.raises(QuoteError) as info:
        split_fields(line)
    assert info.value.code == code


def test_parse_table_text_handles_comments_blanks_and_line_endings():
    text = "# c\r\n\r\n  \t \r\na;b\r\n#x\nc;d\re;f"      # CRLF, LF and CR in one file, no final newline
    rows, rejected, comments, blanks = parse_table_text(text, 2)
    assert [r.values for r in rows] == [("a", "b"), ("c", "d"), ("e", "f")]
    assert [r.line for r in rows] == [4, 6, 7]
    assert (comments, blanks, rejected) == (2, 2, [])


def test_unicode_line_separators_are_data_not_line_breaks():
    rows, rejected, *_ = parse_table_text("a;b c\n", 2)
    assert rows[0].values == ("a", "b c") and not rejected


# schema parser -------------------------------------------------------------------
def test_schema_parser_reads_columns_and_skips_comment_blocks():
    tables = parse_mt_schema(MT_INP_DESCR)
    assert [t.name for t in tables] == ["go_types", "go_children", "go_actions", "go_texts", "go_info"]
    assert tables[0].columns == ["id", "name", "format", "default", "mode", "filter"]
    assert tables[0].file_name == "go_types.csv" and tables[0].declared_field_count == 6
    assert all(not t.problems for t in tables)


def test_schema_parser_reports_inconsistent_declarations():
    broken = "table go_x go_x.csv csv\nfields 5\nfield 1 a vstring\nfield 3 b vstring\nfield 4 a vstring\n"
    (table,) = parse_mt_schema(broken)
    assert len(table.problems) == 3        # count, positions, duplicate names


def test_scanner_does_not_expect_tables_inside_comment_blocks(tmp_path):
    root = tmp_path / "hmx"
    data = make_family(root, "atlas", **{"go_propindex.csv": "", "go_texts.csv": GO_TEXTS})
    (data / "atlas.ebase").write_bytes(b"x")
    declared = MetatypeRepositoryScanner().scan(root).family("atlas").numbered_directories[0].expected_tables
    assert "go_propindex" not in [t.table for t in declared]


# valid load / raw preservation -------------------------------------------------------
def test_valid_family_load_preserves_names_values_and_sources(root):
    make_family(root)
    result = load(root)
    types = result.table("go_types")

    assert result.status is LoadStatus.OK and result.directory == "1" and result.schema_source == "mt.inp_descr"
    assert types.state is TableLoadState.VALID and types.file_name == "go_types.csv"
    assert types.path.endswith(os.path.join("atlas", "1", "go_types.csv"))
    assert types.columns == ["id", "name", "format", "default", "mode", "filter"]
    assert len(types.rows) == 2 and (types.comment_lines, types.blank_lines) == (5, 1)
    first = types.rows[0]
    assert first.line == 7
    assert first.values == ("MT_ATLAS       ", "GATLAS_Type      ", "ch ", "@ATLAS_Type_SG ", "131  ", "")   # untouched
    assert first.trimmed() == ("MT_ATLAS", "GATLAS_Type", "ch", "@ATLAS_Type_SG", "131", "")
    assert types.records()[1]["filter"] == "GATLAS_OffsetZ" and types.encoding == "utf-8"
    children = result.table("go_children")
    assert len(children.rows) == 1 and len(children.rows[0].values) == 4 and children.rows[0].values[3] == ""
    assert result.table("go_texts").rows[2].values == ("KEY_Q", "en", 'say "hi"; then go')
    assert result.table("go_texts").rows[0].values[2] == ' Farben "Dipped in colour"'
    assert result.table("go_texts").rows[1].values[0] == "GAE_Type_C \t\t\t "
    assert result.table("go_types.csv") is types


def test_json_serialisation_round_trips(root):
    make_family(root)
    document = json.loads(json.dumps(load(root).to_dict()))
    assert document["status"] == "ok" and document["tables"][0]["state"] == "valid"
    assert document["tables"][0]["rows"][0]["values"][1].strip() == "GATLAS_Type"


# states and diagnostics -------------------------------------------------------------------
def test_missing_file_is_reported_with_table_and_file(root):
    make_family(root, **{"go_children.csv": None})
    result = load(root)
    table = result.table("go_children")

    assert table.state is TableLoadState.MISSING and result.status is LoadStatus.PARTIAL
    (diagnostic,) = table.diagnostics
    assert (diagnostic.severity, diagnostic.code, diagnostic.table, diagnostic.file) == (
        "error", "TABLE_MISSING", "go_children", "go_children.csv")


def test_empty_and_comment_only_files_are_distinguished(root):
    make_family(root, **{"go_children.csv": "# nothing here\r\n\r\n"})
    result = load(root)

    assert result.table("go_info").state is TableLoadState.EMPTY and result.table("go_info").size_bytes == 0
    assert result.table("go_children").state is TableLoadState.NO_DATA
    assert result.status is LoadStatus.OK and not result.all_diagnostics()


def test_malformed_lines_are_rejected_but_good_rows_are_kept(root):
    make_family(root, **{"go_actions.csv": GO_ACTIONS + '\r\nMT;"open;x;y'})
    table = load(root).table("go_actions")

    assert table.state is TableLoadState.MALFORMED
    assert [(r.line, r.values) for r in table.rows] == [
        (1, ("MT_X", "GVERUS_Type", "SET_PROP")), (4, ("MT_X", "GA", "CON_PROP"))]
    assert [(r.line, r.code) for r in table.rejected_lines] == [
        (2, "FIELD_COUNT_MISMATCH"), (3, "FIELD_COUNT_MISMATCH"), (5, "UNTERMINATED_QUOTE")]
    assert table.rejected_lines[0].text == "child_GrommetMeeting"
    errors = [d for d in table.diagnostics if d.severity == "error"]
    assert [(d.table, d.file, d.line) for d in errors] == [("go_actions", "go_actions.csv", n) for n in (2, 3, 5)]
    assert "expected 3 field(s), found 1" in errors[0].message


def test_invalid_utf8_is_a_decode_error_not_silently_repaired(root):
    latin = b"KEY;de;Gr\xfc\xdfe\r\nKEY2;de;Caf\xe9\r\n"          # real go_texts bytes: FC DF E9
    make_family(root, **{"go_texts.csv": latin})
    result = load(root)
    table = result.table("go_texts")

    assert table.state is TableLoadState.DECODE_ERROR and table.rows == [] and table.encoding == ""
    (diagnostic,) = table.diagnostics
    assert diagnostic.code == "DECODE_ERROR" and diagnostic.line == 1
    assert "0xFC" in diagnostic.message and "offset 9" in diagnostic.message
    assert result.status is LoadStatus.PARTIAL


def test_fallback_encoding_is_opt_in_and_reported(root):
    make_family(root, **{"go_texts.csv": b"KEY;de;Gr\xfc\xdfe\r\n"})
    table = load(root, loader={"fallback_encoding": "cp1252"}).table("go_texts")

    assert table.state is TableLoadState.VALID and table.encoding == "cp1252"
    assert table.rows[0].values == ("KEY", "de", "Grüße")
    assert codes(table.diagnostics) == ["ENCODING_FALLBACK"] and table.diagnostics[0].severity == "warning"


def test_fallback_that_also_fails_is_still_a_decode_error(root):
    make_family(root, **{"go_texts.csv": b"K;de;\x81\r\n"})                 # undefined in cp1252
    table = load(root, loader={"fallback_encoding": "cp1252"}).table("go_texts")
    assert table.state is TableLoadState.DECODE_ERROR and "fallback" in table.diagnostics[0].message


def test_utf8_bom_is_skipped_with_a_warning(root):
    make_family(root, **{"go_texts.csv": b"\xef\xbb\xbfKEY;en;Text\r\n"})
    table = load(root).table("go_texts")
    assert table.state is TableLoadState.VALID and table.rows[0].values[0] == "KEY"
    assert codes(table.diagnostics) == ["BOM_PRESENT"]


def test_undeclared_go_files_are_listed_not_loaded(root):
    make_family(root, **{"go_propindex.csv": "", "go_texts.csv.bak": "x", "go_resetnativeprops.csv": ""})
    result = load(root)
    assert result.unlisted_go_files == ["go_propindex.csv", "go_resetnativeprops.csv", "go_texts.csv.bak"]
    assert result.table("go_propindex") is None


def test_unreadable_file_does_not_stop_other_tables(root):
    make_family(root)

    class Flaky(MetatypeTableLoader):
        def _read_bytes(self, path, limit):
            if path.endswith("go_children.csv"):
                raise PermissionError("denied")
            return super()._read_bytes(path, limit)

    result = Flaky().load_family(root, "atlas")
    assert result.table("go_children").state is TableLoadState.UNREADABLE
    assert codes(result.table("go_children").diagnostics) == ["FILE_UNREADABLE"]
    assert result.table("go_types").state is TableLoadState.VALID and result.status is LoadStatus.PARTIAL


def test_oversized_file_is_refused(root, monkeypatch):
    make_family(root)
    monkeypatch.setattr(loader_module, "MAX_TABLE_BYTES", 10)
    table = load(root).table("go_types")
    assert table.state is TableLoadState.UNREADABLE and codes(table.diagnostics) == ["FILE_TOO_LARGE"]


def test_linked_table_file_is_not_read(root, monkeypatch):
    make_family(root)
    monkeypatch.setattr(loader_module, "_is_link", lambda entry: entry.name == "go_types.csv")
    table = load(root).table("go_types")
    assert table.state is TableLoadState.UNREADABLE and codes(table.diagnostics) == ["LINKED_FILE_NOT_FOLLOWED"]
    assert table.rows == []


# family / directory / schema selection ---------------------------------------------------
@pytest.mark.parametrize("family", ["", "..", "a/b", "a\\b", "C:evil"])
def test_invalid_family_ids_are_rejected(root, family):
    result = load(root, family)
    assert result.status is LoadStatus.FAILED and codes(result.diagnostics) == ["INVALID_SELECTION"]


def test_unknown_family_and_missing_numbered_directory_fail_cleanly(root):
    (root / "bare").mkdir()
    assert codes(load(root, "nope").diagnostics) == ["FAMILY_NOT_FOUND"]
    bare = load(root, "bare")
    assert bare.status is LoadStatus.FAILED and codes(bare.diagnostics) == ["NUMBERED_DIRECTORY_NOT_FOUND"]
    assert codes(load(root / "missing_root", "x").diagnostics) == ["FAMILY_NOT_FOUND"]


def test_multiple_numbered_directories_are_not_guessed(root):
    make_family(root, directory="1")
    make_family(root, directory="2", **{"go_types.csv": "A;B;C;D;1;\r\n"})
    ambiguous = load(root)
    assert ambiguous.status is LoadStatus.FAILED and codes(ambiguous.diagnostics) == ["AMBIGUOUS_NUMBERED_DIRECTORY"]
    chosen = load(root, directory="2")
    assert chosen.directory == "2" and chosen.table("go_types").rows[0].values[0] == "A"
    assert codes(load(root, directory="7").diagnostics) == ["NUMBERED_DIRECTORY_NOT_FOUND"]
    assert codes(load(root, directory="../1").diagnostics) == ["INVALID_SELECTION"]


def test_linked_numbered_directory_is_not_followed(root, monkeypatch):
    make_family(root)
    monkeypatch.setattr(loader_module, "_is_link", lambda entry: entry.name == "1")
    result = load(root)
    assert result.status is LoadStatus.FAILED
    assert codes(result.diagnostics) == ["LINKED_DIRECTORY_SKIPPED", "NUMBERED_DIRECTORY_NOT_FOUND"]


def test_missing_schema_fails_without_guessing_columns(root):
    make_family(root, **{"mt.inp_descr": None})
    result = load(root)
    assert result.status is LoadStatus.FAILED and result.tables == []
    assert [(d.code, d.file) for d in result.diagnostics] == [("SCHEMA_MISSING", "mt.inp_descr")]


def test_schema_declaring_no_tables_fails(root):
    make_family(root, **{"mt.inp_descr": "# nothing\ncomment\ntable go_x go_x.csv csv\nend comment\n"})
    assert codes(load(root).diagnostics) == ["SCHEMA_NO_TABLES"]


def test_inconsistent_schema_declaration_is_warned(root):
    broken = MT_INP_DESCR.replace("fields  2\nfield   1  key\t\tvstring\tdelim ; trim\nfield   2  value", "fields  5\nfield   1  key\t\tvstring\tdelim ; trim\nfield   2  value", 1)
    make_family(root, **{"mt.inp_descr": broken})
    result = load(root)
    assert "SCHEMA_DECLARATION_PROBLEM" in codes(result.diagnostics)
    assert next(d for d in result.diagnostics if d.code == "SCHEMA_DECLARATION_PROBLEM").table == "go_info"


def test_optional_missing_table_is_only_a_warning(root):
    schema = MT_INP_DESCR.replace("comment\n\nThe following", "table go_propindex\tgo_propindex.csv\tcsv\nfields 1\nfield 1 id vstring\n\ncomment\n\nThe following")
    make_family(root, **{"mt.inp_descr": schema})
    result = load(root)
    table = result.table("go_propindex")
    assert table.state is TableLoadState.MISSING and table.diagnostics[0].severity == "warning"
    assert result.status is LoadStatus.OK


# safety ------------------------------------------------------------------------------------------
def test_loading_is_read_only_and_repeatable(root):
    make_family(root, **{"go_texts.csv": b"K;de;\xfc\r\n", "go_actions.csv": GO_ACTIONS})

    def snapshot():
        return sorted((str(p.relative_to(root)), p.stat().st_size, p.stat().st_mtime_ns, p.read_bytes() if p.is_file() else b"")
                      for p in root.rglob("*"))

    before = snapshot()
    first, second = load(root).to_dict(), load(root).to_dict()
    assert snapshot() == before
    first.pop("loaded_at"), second.pop("loaded_at")
    assert first == second


def test_loader_module_has_no_write_or_process_capability():
    source = Path(loader_module.__file__).read_text(encoding="utf-8")
    for forbidden in ("subprocess", "os.system", "Popen", "'wb'", '"wb"', '"w"', ".write_", "os.remove", "os.rename", "shutil"):
        assert forbidden not in source


# integration with the Metatype module ----------------------------------------------------------------
def test_service_loads_through_context_using_the_scanned_root(root):
    make_family(root)
    context = ApplicationContext(AppConfig(metatype_repository_root=str(root)))
    service = context.metatype_table_loader_service

    assert service is context.get_service(MetatypeTableLoaderService) and service.last_result is None
    assert service.default_root() == str(root)                   # no scan yet: configured root
    context.metatype_repository_service.scan()
    result = service.load_family("atlas")
    assert result.status is LoadStatus.OK and service.last_result is result
    text = service.summary_text(result)
    assert "go_types.csv" in text and "valid" in text and "2 row(s)" in text
    assert service.load_family("nope").status is LoadStatus.FAILED


def test_page_loads_the_selected_product_family_only(root):
    from PySide6.QtWidgets import QApplication
    from ui.pages.metatype_repository_page import MetatypeRepositoryPage

    app = QApplication.instance() or QApplication([])
    make_family(root, "atlas")
    (root / "plain").mkdir()
    (root / "plain" / "1").mkdir()
    (root / "plain" / "1" / "notes.txt").write_text("x")
    page = MetatypeRepositoryPage(ApplicationContext(AppConfig(metatype_repository_root=str(root))))
    page.scan_button.click()
    rows = {page.table.item(r, 0).text(): r for r in range(page.table.rowCount())}

    assert not page.load_button.isEnabled()
    page.table.selectRow(rows["plain"])                         # unclassified: not loadable
    assert page.selected_family_id() == "" and not page.load_button.isEnabled()
    page.table.selectRow(rows["atlas"])
    assert page.selected_family_id() == "atlas" and page.load_button.isEnabled()
    page.load_button.click()
    assert "go_types.csv" in page.load_output.toPlainText() and "atlas/1" in page.load_output.toPlainText()
    app.processEvents()
