"""Expected values are documented .NET behaviour (int.Parse, double.Parse, Substring, ArrayList)."""
import math

import pytest

from services.syteline_export.pipeline.netsem import (
    LegacyFormatError, LegacyRangeError, double_to_string, is_knoll_catalogue, list_contains,
    list_index_of, list_remove, net_bool, net_double, net_int, remove_non_alphanumeric,
    substring, tostr,
)


def test_tostr_follows_dotnet_tostring_for_database_values():
    assert tostr(None) == ""
    assert tostr(True) == "True" and tostr(False) == "False"
    assert tostr(5.0) == "5" and tostr(0.25) == "0.25"
    assert tostr(1e-05) == "1E-05" and tostr(1e16) == "1E+16"
    assert tostr(7) == "7"


@pytest.mark.parametrize("text,expected", [(" 12 ", 12), ("-3", -3), ("+4", 4), ("007", 7)])
def test_net_int_accepts_what_int_parse_accepts(text, expected):
    assert net_int(text) == expected


@pytest.mark.parametrize("text", ["", "1_0", "1.5", "abc", "PREFIX-4", "99999999999", "٣"])
def test_net_int_rejects_what_int_parse_rejects(text):
    with pytest.raises(LegacyFormatError):
        net_int(text)


@pytest.mark.parametrize("text,expected", [
    ("1.25", 1.25), ("1,234.5", 1234.5), (".5", 0.5), ("5.", 5.0), ("1e3", 1000.0), (" -2 ", -2.0),
])
def test_net_double_accepts_en_us_numbers(text, expected):
    assert net_double(text) == expected


@pytest.mark.parametrize("text", ["", " ", ".", "nan", "inf", "1_0", "PREFIX-4", "1,23", "--1"])
def test_net_double_rejects_non_numbers(text):
    with pytest.raises(LegacyFormatError):
        net_double(text)


def test_net_double_accepts_dotnet_special_symbols_only_by_their_dotnet_names():
    assert math.isnan(net_double("NaN"))
    assert net_double("Infinity") == math.inf


def test_net_bool_matches_bool_parse():
    assert net_bool(" true ") is True and net_bool("False") is False
    with pytest.raises(LegacyFormatError):
        net_bool("1")


def test_substring_raises_like_csharp():
    assert substring("abcdef", 2) == "cdef" and substring("abcdef", 2, 3) == "cde"
    assert substring("abc", 3) == ""
    for args in ((-1,), (4,), (1, 5), (1, -1)):
        with pytest.raises(LegacyRangeError):
            substring("abc", *args)


def test_arraylist_lookups_do_not_coerce_bool_or_string_to_numbers():
    assert list_index_of([1, "1", True], "1") == 1
    assert list_index_of([True, 1], 1) == 1
    assert list_index_of([1.0], 1) == 0  # ints and doubles are both numeric here
    assert not list_contains(["5"], 5)
    items = ["a", "b", "a"]
    list_remove(items, "a")
    assert items == ["b", "a"]
    list_remove(items, "zzz")
    assert items == ["b", "a"]


def test_remove_non_alphanumeric_and_knoll_catalogues():
    assert remove_non_alphanumeric("A-1_b#2 ") == "A1b2"
    assert is_knoll_catalogue(649) and is_knoll_catalogue(769)
    assert not is_knoll_catalogue(229)
