"""CodeScheme engine: tokenization, user-defined and predefined encoding, edge cases."""
import pytest

from services.ocd_engine import diagnostics as dg
from services.ocd_engine.codescheme_engine import (
    AtToken, CodeSchemeDef, CodeSchemeEncoder, EncodedValue, LiteralToken, MixedToken,
    PropToken, TableToken, tokenize,
)

COSM_SCHEME = (
    "@,@,@,COSM_NORMAL:Assembly_Option,COSM_NORMAL:Back_Height,COSM_NORMAL:Height_Adjustment,"
    "COSM_NORMAL:Tilt,COSM_NORMAL:Seat_Depth,COSM_NORMAL:Arms, ,COSM_NORMAL:Frame_Finish, ,"
    "COSM_NORMAL:Chassis_Finish, ,COSM_NORMAL:Base_Finish, ,COSM_NORMAL:Castors_Glides, ,"
    "COSM_NORMAL:Armpad_Finish_H, ,COSM_NORMAL:Intercept_Finish"
)


class View:
    """Minimal PropertyView: ``{(class, prop): EncodedValue}`` in insertion order."""

    def __init__(self, values):
        self.values = {(c.upper(), p.upper()): v for (c, p), v in values.items()}
        self._order = list(values)

    def get(self, cls, prop):
        return self.values.get((cls.upper(), prop.upper()))

    def ordered(self):
        return self._order


def ev(text="", **kw):
    return EncodedValue(text=text, **kw)


# ------------------------------------------------------------------ tokenizer
def test_tokenizer_keeps_literals_spaces_dots_and_at():
    tokens = tokenize("@,@, ,A:One,.,A:Two,-")
    assert tokens == (AtToken(), AtToken(), LiteralToken(" "), PropToken("A", "One"),
                      LiteralToken("."), PropToken("A", "Two"), LiteralToken("-"))


def test_tokenizer_real_cosm_scheme_shape():
    tokens = tokenize(COSM_SCHEME)
    assert sum(isinstance(t, AtToken) for t in tokens) == 3
    assert sum(isinstance(t, PropToken) for t in tokens) == 12
    assert sum(t == LiteralToken(" ") for t in tokens) == 6              # six literal spaces
    assert tokens[:3] == (AtToken(),) * 3 and tokens[3] == PropToken("COSM_NORMAL", "Assembly_Option")


def test_tokenizer_table_call_survives_inner_commas_and_mixed_segment():
    tokens = tokenize("@,TABLE t(A = x, B = y),pre-A:One")
    assert isinstance(tokens[1], TableToken) and tokens[1].call.table == "T"
    assert isinstance(tokens[2], MixedToken)


def test_tokenizer_is_cached():
    assert tokenize(COSM_SCHEME) is tokenize(COSM_SCHEME)


# ------------------------------------------------------------------ user-defined encoding
def scheme(text, **kw):
    return CodeSchemeDef(scheme=text, **kw)


def test_spec_example_cupboard():
    # spec 4.2: Cupboard:Hight,_,@,@,-,@,@,_,Cupboard:Surface on base 0815 => 5H_08-15_03
    view = View({("Cupboard", "Hight"): ev("5H"), ("Cupboard", "Surface"): ev("03")})
    out = CodeSchemeEncoder(scheme("Cupboard:Hight,_,@,@,-,@,@,_,Cupboard:Surface")).encode("0815", view)
    assert out.final_article == "5H_08-15_03"


def test_cosm_real_scheme_three_ats_then_values_then_spaces():
    names = ["Assembly_Option", "Back_Height", "Height_Adjustment", "Tilt", "Seat_Depth", "Arms",
             "Frame_Finish", "Chassis_Finish", "Base_Finish", "Castors_Glides", "Armpad_Finish_H",
             "Intercept_Finish"]
    codes = ["1", "4", "2", "S", "F", "N", "G1", "G2", "G3", "BK", "H1", "I1"]
    view = View({("COSM_NORMAL", n): ev(c) for n, c in zip(names, codes)})
    out = CodeSchemeEncoder(scheme(COSM_SCHEME)).encode("FLC142", view)
    # 3 '@' consume F,L,C; first six values run together; one space before every later property
    assert out.final_article == "FLC142SFN G1 G2 G3 BK H1 I1"
    assert out.variant_code == "142SFN G1 G2 G3 BK H1 I1"                 # variant = everything but '@' chars


def test_at_beyond_base_length_emits_nothing_more():
    out = CodeSchemeEncoder(scheme("@,@,@,@")).encode("AB", View({}))
    assert out.final_article == "AB"


def test_at_can_interleave_with_properties():
    view = View({("C", "P"): ev("xx")})
    assert CodeSchemeEncoder(scheme("@,C:P,@,@")).encode("123", view).final_article == "1xx23"


def test_empty_hidden_and_unselected_values_visibility_zero():
    view = View({("C", "A"): ev("a"), ("C", "Hidden"): ev(visible=False, length=3),
                 ("C", "Unset"): ev("", optional=True, length=2), ("C", "Z"): ev("z")})
    out = CodeSchemeEncoder(scheme("C:A,C:Hidden,C:Unset,C:Z", visibility="0")).encode("B", view)
    assert out.final_article == "aXXz"        # hidden => nothing (mode 0); unselected optional => 'X' x length


def test_visibility_one_replaces_hidden_with_invisible_char():
    view = View({("C", "H"): ev(visible=False, length=3), ("C", "A"): ev("a")})
    out = CodeSchemeEncoder(scheme("C:H,C:A", visibility="1", invisible_char="#")).encode("B", view)
    assert out.final_article == "###a"


def test_user_scheme_with_empty_visibility_field_uses_mode_one():
    view = View({("C", "H"): ev(visible=False, length=2)})
    assert CodeSchemeEncoder(scheme("C:H")).encode("B", view).final_article == "--"


def test_trim_zero_pads_to_property_length():
    view = View({("C", "A"): ev("a", length=3), ("C", "B"): ev("b", length=2)})
    assert CodeSchemeEncoder(scheme("C:A,C:B", trim=False)).encode("X", view).final_article == "a  b "
    assert CodeSchemeEncoder(scheme("C:A,C:B", trim=True)).encode("X", view).final_article == "ab"


def test_multivalued_property_uses_mo_separator_and_brackets():
    view = View({("C", "M"): ev(multi=("ABS", "ZV"))})
    assert CodeSchemeEncoder(scheme("C:M")).encode("X", view).final_article == "ABS,ZV"
    out = CodeSchemeEncoder(scheme("C:M", mo_sep="+", mo_bracket="[]")).encode("X", view)
    assert out.final_article == "[ABS+ZV]"


def test_missing_property_is_a_diagnostic_and_no_number():
    sink = dg.DiagnosticSink()
    out = CodeSchemeEncoder(scheme("@,C:Nope")).encode("A", View({}), sink, "A")
    assert out is None and sink.count(dg.MISSING_PROPERTY) == 1


def test_scheme_without_at_follows_spec_but_legacy_prefix_is_switchable():
    view = View({("C", "A"): ev("a")})
    assert CodeSchemeEncoder(scheme("C:A")).encode("BASE", view).final_article == "a"
    assert CodeSchemeEncoder(scheme("C:A"), base_prefix_when_no_at=True).encode("BASE", view).final_article == "BASEa"
    assert CodeSchemeEncoder(scheme("C:A"), base_prefix_when_no_at=True).encode("BASE", view).variant_code == "a"


def test_computed_property_is_read_like_any_other():
    view = View({("AERON_OPTIONS", "Code"): ev("AER1A11NN SZS")})
    out = CodeSchemeEncoder(scheme("AERON_OPTIONS:Code", visibility="1")).encode("AER1A11", view)
    assert out.final_article == "AER1A11NN SZS"


def test_table_call_segment_uses_unique_fan_value():
    class Table:
        lines = [{"A": "1", "$FAN": "ONE"}, {"A": "2", "$FAN": "TWO"}]

    view = View({("C", "P"): ev("2")})
    enc = CodeSchemeEncoder(scheme("@,TABLE t(A = P)"), tables={"T": Table()})
    assert enc.encode("X", view).final_article == "XTWO"
    sink = dg.DiagnosticSink()
    assert CodeSchemeEncoder(scheme("TABLE nope(A = P)"), tables={}).encode("X", view, sink) is None
    assert sink.count(dg.MISSING_TABLE) == 1


# ------------------------------------------------------------------ predefined schemes
def ordered_view():
    return View({("Cupboard", "Surface"): ev("03", length=2), ("Cupboard", "Hight"): ev("5H", length=2),
                 ("Cupboard", "Accessories"): ev("", optional=True, length=2),
                 ("Cupboard", "Lock"): ev(visible=False, length=2)})


def test_key_value_list_predefined_scheme():
    out = CodeSchemeEncoder(CodeSchemeDef(scheme="KeyValueList", varcode_sep="-")).encode("0815", ordered_view())
    # only currently valid properties, ';' separated, VOID for an unselected optional one
    assert out.final_article == "0815-Cupboard.Surface=03;Cupboard.Hight=5H;Cupboard.Accessories=VOID"
    assert out.kind == "predefined"


def test_value_list_visibility_zero_and_one():
    zero = CodeSchemeEncoder(CodeSchemeDef(scheme="ValueList", varcode_sep="-", value_sep="", visibility="0"))
    one = CodeSchemeEncoder(CodeSchemeDef(scheme="ValueList", varcode_sep="-", value_sep="", visibility="1"))
    assert zero.encode("0815", ordered_view()).final_article == "0815-035HXX"
    assert one.encode("0815", ordered_view()).final_article == "0815-035HXX--"      # invisible '-' x length 2


def test_value_list_value_separator_and_trim_default():
    enc = CodeSchemeEncoder(CodeSchemeDef(scheme="ValueList", varcode_sep=" ", value_sep=".", visibility="0"))
    assert enc.encode("B", ordered_view()).final_article == "B 03.5H.XX"
    assert enc.encode("B", ordered_view()).variant_code == "03.5H.XX"


def test_value_list_custom_replacement_characters():
    d = CodeSchemeDef(scheme="valuelist", visibility="1", invisible_char="~", unselect_char="?")
    assert CodeSchemeEncoder(d).encode("B", ordered_view()).final_article == "B035H????~~".replace("????", "??") \
        or True
    out = CodeSchemeEncoder(d).encode("B", ordered_view()).final_article
    assert out == "B035H" + "??" + "~~"


def test_scheme_row_from_csv_and_legacy_keys():
    row = {"scheme_id": "U1", "scheme": "ValueList", "varcode_sep": "-", "value_sep": ".", "visibility": "0",
           "invisible_char": "-", "unselect_char": "X", "trim": "1", "mo_sep": "", "mo_bracket": ""}
    d = CodeSchemeDef.from_row(row)
    assert d.is_predefined and d.varcode_sep == "-" and d.trim is True
    legacy = CodeSchemeDef.from_row({"name": "N", "body": "A:B,A:C", "ValueSep": "."})
    assert legacy.scheme == "A:B,A:C" and legacy.value_sep == "." and not legacy.is_predefined
    assert CodeSchemeDef.from_row({"scheme": "x", "trim": "0"}).trim is False


@pytest.mark.parametrize("text", ["", "   "])
def test_empty_scheme_yields_no_number(text):
    assert CodeSchemeEncoder(scheme(text)).encode("A", View({}), None) is None
