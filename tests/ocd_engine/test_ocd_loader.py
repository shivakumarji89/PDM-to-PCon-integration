"""CSV/schema loading and model building, on a synthetic OCD folder (no external data)."""
from pathlib import Path

import pytest

from services.ocd_engine import diagnostics as dg
from services.ocd_engine.codescheme_engine import CodeSchemeEncoder
from services.ocd_engine.configuration_engine import ConfigurationEngine
from services.ocd_engine.csv_loader import OcdCsvLoader, build_article_model
from services.ocd_engine.obx_serialization import ofml_varcode
from services.ocd_engine.pricing import PriceCalculator, PriceRow
from services.ocd_engine.schema_loader import DEFAULT_SCHEMAS, load_schemas, parse_descriptor

DESCRIPTOR = "\n".join([
    "table\tocd_widget\tocd_widget.csv\tmscsv", "fields\t3",
    "field\t1\tzeta\tvstring\t\tdelim ; hidx", "field\t2\talpha\tuint16\t\tdelim ;",
    "field\t3\tbeta\tvstring\t\tdelim ;", "",
])


def write(folder: Path, name: str, text: str, encoding="latin-1"):
    (folder / name).write_bytes(text.replace("\n", "\r\n").encode(encoding))


@pytest.fixture()
def ocd(tmp_path):
    """A tiny Dalby-shaped program: Top drives a hidden/derived Bottom; one price relation."""
    write(tmp_path, "ocd_article.csv", "TBL1;C;HM;DEMO;1;2;900;0;1;C62;U1\nTBL2;C;HM;DEMO;1;2;900;0;1;C62;U1")
    write(tmp_path, "ocd_artbase.csv", "TBL1;DEMO_OPT;PLC;SE\nTBL2;DEMO_OPT;PLC;SE")
    write(tmp_path, "ocd_propertyclass.csv", "TBL1;1;DEMO_OPT;10;0\nTBL2;1;DEMO_OPT;10;0")
    write(tmp_path, "ocd_property.csv",
          "DEMO_OPT;Top;1;11;0;C;3;0;1;0;0;0;C;0;\n"
          "DEMO_OPT;Bottom;2;;100;C;3;0;1;0;0;0;RG;0;\n"
          "DEMO_OPT;PLC;3;12;0;C;8;0;1;0;0;0;RG;0;")
    write(tmp_path, "ocd_propertyvalue.csv",
          "DEMO_OPT;Top;1;21;0;0;0;EQ;Q1;;;;;\nDEMO_OPT;Top;2;22;0;0;0;EQ;OAK;;;;;\n"
          "DEMO_OPT;Bottom;1;23;101;0;0;EQ;MDF;;;;;\nDEMO_OPT;Bottom;2;24;102;0;0;EQ;OAK;;;;;\n"
          "DEMO_OPT;Top;3;25;0;0;0;GE;10;LE;20;;;")
    write(tmp_path, "ocd_relationobj.csv",
          "100;1;000000000000000001;1;C\n101;1;000000000000000002;1;C\n102;1;000000000000000003;1;C\n"
          "900;1;000000000000000004;3;P")
    write(tmp_path, "ocd_relation.csv",
          '000000000000000001; 1;"(SPECIFIED Top) AND (Top IN (\'Q1\', \'OAK\'))"\n'
          '000000000000000002; 1;"* a comment"\n000000000000000002; 2;"(SPECIFIED Top) AND (Top = \'Q1\')"\n'
          '000000000000000003; 1;"Top = \'OAK\'"\n'
          '000000000000000004; 1;"$VARCOND = \'TOP=\' + Top,"')
    write(tmp_path, "ocd_codescheme.csv", 'U1;@,@,@,@, ,DEMO_OPT:Top, ,DEMO_OPT:Bottom;"";"";0;"-";"X";1;"";""')
    write(tmp_path, "ocd_price.csv",
          "TBL1;;S;B;;;100;1;EUR;20250101;99991231;1;\nTBL1;TOP=Q1;S;X;;;10;1;EUR;20250101;99991231;1;\n"
          "TBL1;TOP=OAK;S;X;;;20;1;EUR;20250101;99991231;1;")
    return tmp_path


def test_descriptor_parsing_names_types_and_delimiter(tmp_path):
    (tmp_path / "pdata.ocd_widget.inp_descr").write_text(DESCRIPTOR, encoding="latin-1")
    (schema,) = parse_descriptor(tmp_path / "pdata.ocd_widget.inp_descr")
    assert (schema.name, schema.file, schema.fields) == ("widget", "ocd_widget.csv", ("zeta", "alpha", "beta"))
    assert schema.types == ("vstring", "uint16", "vstring") and schema.delimiter == ";"


def test_defaults_used_without_descriptors_and_descriptor_wins_when_present(tmp_path):
    assert load_schemas(tmp_path)["price"] == DEFAULT_SCHEMAS["price"]
    (tmp_path / "pdata.ocd_price.inp_descr").write_text(
        "table\tocd_price\tocd_price.csv\tmscsv\nfields\t2\nfield\t1\tarticle_nr\tvstring\t\tdelim ;\n"
        "field\t2\tprice\tfloat64\t\tdelim ;\n", encoding="latin-1")
    assert load_schemas(tmp_path)["price"].fields == ("article_nr", "price")


def test_columns_are_read_by_name_not_position(tmp_path):
    (tmp_path / "pdata.ocd_widget.inp_descr").write_text(DESCRIPTOR, encoding="latin-1")
    write(tmp_path, "ocd_widget.csv", 'Z1; 7;"has;semicolon"\nZ2; 8;plain')
    rows = OcdCsvLoader().load(tmp_path).tables["widget"]
    assert rows == [{"zeta": "Z1", "alpha": "7", "beta": "has;semicolon"},
                    {"zeta": "Z2", "alpha": "8", "beta": "plain"}]


def test_non_ascii_text_is_decoded_as_latin1_and_reported_once(tmp_path):
    (tmp_path / "pdata.ocd_widget.inp_descr").write_text(DESCRIPTOR, encoding="latin-1")
    write(tmp_path, "ocd_widget.csv", "Z1;1;Fußgestell\nZ2;2;Fußboden")
    dataset = OcdCsvLoader().load(tmp_path)
    assert dataset.tables["widget"][0]["beta"] == "Fußgestell"
    assert dataset.sink.count(dg.LOAD_ERROR) == 1


def test_missing_obligatory_tables_are_diagnosed(tmp_path):
    dataset = OcdCsvLoader().load(tmp_path)
    assert {d.message.split()[2] for d in dataset.sink.by_code(dg.MISSING_TABLE)} >= {"article", "price"}


def test_relation_text_is_assembled_from_blocks_without_comments(ocd):
    dataset = OcdCsvLoader().load(ocd)
    assert dataset.relation_text("000000000000000002") == "(SPECIFIED Top) AND (Top = 'Q1')"
    assert dataset.relation_text("nope") is None


def test_model_builds_classes_properties_values_artbase_and_relations(ocd):
    dataset = OcdCsvLoader().load(ocd)
    model = build_article_model(dataset, "TBL1")
    assert [p.name for p in model.properties] == ["Top", "Bottom", "PLC"]
    top, bottom, plc = model.properties
    assert [v.value for v in top.values] == ["Q1", "OAK"]               # interval value (GE/LE) is not enumerable
    assert dataset.sink.count(dg.UNSUPPORTED_SYNTAX) == 1
    assert bottom.relations and bottom.relations[0].rel_type == 1
    assert [v.value for v in plc.values] == ["SE"] and plc.allowed_keys == frozenset({"DEMO_OPT:PLC:SE"})
    assert model.scheme_id == "U1" and model.article_relations[0].domain == "P"


def test_unknown_article_is_a_diagnostic_not_an_exception(ocd):
    dataset = OcdCsvLoader().load(ocd)
    assert build_article_model(dataset, "NOPE") is None
    assert dataset.sink.count(dg.MISSING_PROPERTY) == 1


def test_end_to_end_configurations_encoding_varcode_and_prices(ocd):
    dataset = OcdCsvLoader().load(ocd)
    model = build_article_model(dataset, "TBL1")
    engine = ConfigurationEngine(model)
    encoder = CodeSchemeEncoder(dataset.code_scheme(model.scheme_id))
    calc = PriceCalculator([PriceRow.from_csv(r) for r in dataset.tables["price"]])
    rows = {}
    for config, result in engine.generate():
        final = encoder.encode("TBL1", engine.view(config.assignments, result.computed)).final_article
        priced = calc.price("TBL1", result.varconds, price_date="20260101", currency="EUR")
        rows[final] = (ofml_varcode(config.assignments, model), result.varconds, priced.total)
    # Q1: Bottom MDF is valid (rel 101: Top = Q1); OAK: Bottom OAK (rel 102)
    assert set(rows) == {"TBL1 Q1 MDF", "TBL1 OAK OAK"}
    varcode, varconds, total = rows["TBL1 Q1 MDF"]
    # Bottom/PLC are scope RG (derived), so only the configurable Top reaches ofmlvarcode
    assert varcode == "DEMO_OPT.Top=Q1" and varconds == ["TOP=Q1"] and str(total) == "110.00"
    assert str(rows["TBL1 OAK OAK"][2]) == "120.00"
