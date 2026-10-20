"""D2 article values, D4 mode encoding, D6 property format and D5 go_texts encoding. Pure, no I/O except real read-only."""
from pathlib import Path

import pytest

from core.config import AppConfig
from services.metatype.property_rules import (
    ArticleValueTable, ModePolicy, build_property_format, encode_mode,
)
from services.metatype.text_encoding import Encoding, append_text_lines, detect_encoding, detect_line_ending


# -- D4 ----------------------------------------------------------------------------------------------------------------
def test_mode_follows_the_recommended_policy_but_is_unusable_until_confirmed():
    plain = encode_mode(ModePolicy(), False, False)
    assert plain.mode == 3 and not plain.confirmed and not plain.usable and "not confirmed" in plain.problems[0]
    both = encode_mode(ModePolicy(confirmed=True), True, True)
    assert both.mode == 3 | 128 | 8192 and both.usable
    assert encode_mode(ModePolicy(confirmed=True), True, False).mode == 131           # a real selector mode


@pytest.mark.parametrize("base", [3 | 4, 3 | 2048])
def test_bit_4_and_2048_are_always_refused(base):
    decision = encode_mode(ModePolicy(base=base, confirmed=True), False, False)
    assert decision.mode is None and not decision.usable and decision.problems


def test_mode_must_fit_uint16():
    assert encode_mode(ModePolicy(base=0x10000, confirmed=True), False, False).mode is None


# -- D6 ----------------------------------------------------------------------------------------------------------------
def test_property_format_requires_explicit_valid_default():
    fmt = build_property_format(["A", "B"], "B", "GParent, GOther")
    assert fmt.ok and (fmt.format, fmt.default, fmt.filter) == ("ch", "B", "GParent,GOther")
    assert build_property_format(["A", "B"], None).problems                          # never the first value by default
    assert any("not one of" in p for p in build_property_format(["A", "B"], "C").problems)
    assert build_property_format(["A", "B"], "A").filter == ""                         # empty filter is allowed
    assert any("two distinct" in p for p in build_property_format(["A", "A"], "A").problems)
    assert any("Filter name" in p for p in build_property_format(["A", "B"], "A", "bad name").problems)
    assert any("delimiter" in p for p in build_property_format(["A;x", "B"], "B").problems)


# -- D2 ----------------------------------------------------------------------------------------------------------------
def test_article_values_are_never_invented_or_broadcast():
    table = ArticleValueTable(["ART1", "ART2"], ["V1", "V2"], {"ART1": "C1", "ART2": "C2"})
    assert not table.complete and len(table.problems()) == 2 and all("no value" in p for p in table.problems())
    table.set_value("ART1", "V1")
    assert "ART2: no value assigned." in table.problems()
    table.set_value("ART2", "V2")
    assert table.complete and not table.set_value("OTHER", "V1")


def test_article_values_validate_membership_configid_and_sharing():
    table = ArticleValueTable(["ART1", "ART2"], ["V1", "V2"], {"ART1": "C1", "ART2": "C1"})
    table.set_value("ART1", "V1")
    table.set_value("ART2", "V2")
    assert any("shared by articles with different values" in p for p in table.problems())
    table.set_value("ART2", "V9")
    assert any("'V9' is not one of" in p for p in table.problems())
    missing = ArticleValueTable(["ART1"], ["V1"], {})
    missing.set_value("ART1", "V1")
    assert any("never inferred" in p for p in missing.problems()) and not missing.complete
    table.assigned["GHOST"] = "V1"
    assert any("GHOST is not a listed article" in p for p in table.problems())


# -- D5 ----------------------------------------------------------------------------------------------------------------
CP1252 = "Bürostuhl Größe\r\n".encode("cp1252")


def test_detection_covers_the_real_conventions():
    assert detect_encoding(b"") is Encoding.EMPTY and detect_encoding(b"abc\r\n") is Encoding.ASCII
    assert detect_encoding("Größe".encode("utf-8")) is Encoding.UTF8 and detect_encoding(CP1252) is Encoding.CP1252
    assert detect_encoding(b"\xef\xbb\xbfabc") is Encoding.UTF8_BOM
    assert detect_encoding(b"\x81abc") is Encoding.AMBIGUOUS                          # undefined in cp1252
    assert detect_encoding("Größe".encode("utf-8") + b" B\xfcro") is Encoding.AMBIGUOUS   # mixed UTF-8 and cp1252
    assert detect_line_ending(b"a\r\nb\r\n") == "\r\n" and detect_line_ending(b"a\r\nb\n") is None


def test_append_preserves_existing_bytes_encoding_and_line_endings():
    result = append_text_lines(CP1252, ["K;de;Ausführung"])
    assert result.ok and result.encoding is Encoding.CP1252
    assert result.data == CP1252 + "K;de;Ausführung\r\n".encode("cp1252")
    bom = b"\xef\xbb\xbfk;en;x\n"
    assert append_text_lines(bom, ["k;de;ü"]).data == bom + "k;de;ü\n".encode("utf-8")
    assert append_text_lines(b"k;en;x", ["k;de;y"]).data is None                               # no convention: refused
    assert append_text_lines(b"k;en;x\r\nk", ["a"]).data == b"k;en;x\r\nk\r\na\r\n"       # terminates the last line


def test_empty_or_ascii_files_need_an_owner_encoding_for_non_ascii_text():
    for raw in (b"", b"k;en;x\r\n"):
        refused = append_text_lines(raw, ["k;de;Größe"], default_eol="\r\n")
        assert not refused.ok and "decision D5" in refused.problems[0]
        chosen = append_text_lines(raw, ["k;de;Größe"], fallback=Encoding.CP1252, default_eol="\r\n")
        assert chosen.ok and chosen.data.endswith("k;de;Größe\r\n".encode("cp1252"))
        assert append_text_lines(raw, ["k;en;plain"], default_eol="\r\n").ok            # ASCII needs no decision


def test_unencodable_ambiguous_or_multiline_text_is_refused():
    assert not append_text_lines(CP1252, ["k;en;日本"]).ok
    assert not append_text_lines(b"\x81x\r\n", ["a"]).ok
    assert not append_text_lines(CP1252, ["a\nb"]).ok


REAL = Path(AppConfig().metatype_repository_root)


@pytest.mark.skipif(not REAL.exists(), reason="real HMX repository not available")
def test_real_go_texts_files_are_detected_and_roundtrip_unchanged_read_only():
    counts: dict[Encoding, int] = {}
    for path in sorted(REAL.glob("*/*/go_texts.csv")):
        raw = path.read_bytes()
        kind = detect_encoding(raw)
        counts[kind] = counts.get(kind, 0) + 1
        if raw and kind is not Encoding.AMBIGUOUS and detect_line_ending(raw):
            result = append_text_lines(raw, ["PROBE;en;probe"])
            assert result.ok and result.data.startswith(raw)                                  # existing bytes untouched
    assert counts.get(Encoding.CP1252, 0) >= 30 and counts.get(Encoding.AMBIGUOUS, 0) == 0, counts
