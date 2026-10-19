"""Tests for stage P2 (ExportThread.cs 2607-2875). All fixtures are synthetic."""
from __future__ import annotations

import pytest

from services.syteline_export.pipeline.db import ScriptedExportDb
from services.syteline_export.pipeline.netsem import LegacyFormatError
from services.syteline_export.pipeline.run_base import ExportRunBase
from services.syteline_export.pipeline.stage_p02_option_rows import LegacyCastError, P02Mixin


class H(P02Mixin, ExportRunBase):
    pass


def opt_row(**kw):
    row = {
        "Option2": "Colour", "optval_name": "Red", "fsccompliant": 0, "OrderCodeValue2": "R1",
        "OptionValueId": 10, "OptionId": 1, "IsFabric": 0, "OptDescId": 100, "optvalDescId": 200,
        "ParentOptValId": None, "ParentOptValCode": None, "OptChildCount": 0, "OptChildId": None,
        "Status": 1,
    }
    row.update(kw)
    return row


def make(rows, script=None, *, longitem="XY1", **fields):
    h = H(ScriptedExportDb(script or {}))
    v = h.v
    v.option_rows = rows
    v.sqlDataReader = {"LongItem": longitem, "ProductId": 5, "ItemId": 7}
    for i in list(range(16, 17)) + [19, 20, 29, 30, 31, 32, 33, 34] + list(range(45, 63)):
        setattr(v, f"arrayList{i}", [])
    v.num7 = 0
    v.num8 = -1
    h._syteline = False
    for k, val in fields.items():
        setattr(h, k, val)
    return h


def test_basic_add_aligned_arrays_and_stage13_cache():  # 2692-2726, 2849-2871
    script = {
        "FROM OtherDescription": [{"ShortDescription": "a>b"}],
        "SLFeatureLength": [{"SLFeatureLength": "3"}],
    }
    h = make([opt_row(), opt_row(OptionValueId=11, OptionId=1, OrderCodeValue2="R2#", optvalDescId=201)], script)
    assert h.p02_option_rows() is None
    v = h.v
    assert v.arrayList45 == [10, 11] and v.arrayList47 == [1, 1] and v.arrayList48 == [10, 11]
    assert v.arrayList55 == ["1|R1", "1|R2"]  # num7 stays 1 for same OptionId, '#' stripped (2709)
    assert v.arrayList53 == ["200", "201"] and v.arrayList61 == [[-2], [-2]]
    assert v.arrayList59 == [False, False] and v.arrayList60 == ["0", "0"]
    assert v.arrayList29 == ["a b", "a b"] and v.arrayList30 == ["200", "201"]
    assert v.arrayList31 == ["a b", "a b"]
    # stage 13: one query for OptionId 1, cached for the second
    assert v.arrayList54 == [3, 3] and v.arrayList33 == [3] and v.arrayList34 == [1]
    assert v.arrayList63 == [] and v.num18 == 1
    assert h.threadStage == "13"
    # parameterised SQL (c2), no data in text
    for conn, sql, params, _ in h.db.calls:
        assert conn == "c2" and "200" not in sql and "?" in sql
    assert h.db.calls[0][2] == (200, 200, -1)


def test_option_counter_increments_on_option_change():  # 2692-2695
    h = make([opt_row(), opt_row(OptionValueId=11, OptionId=2, OrderCodeValue2="B")],
             {"FROM OtherDescription": [], "SLFeatureLength": []})
    h.p02_option_rows()
    assert h.v.arrayList55 == ["1|R1", "2|B"] and h.v.num7 == 2 and h.v.num8 == 2
    assert h.v.arrayList54 == [2, 2]  # default 2 when no row (2851)


def test_fsc_suffix_fabric_and_customers_own_and_child_id():  # 2611, 2700, 2715-2725
    rows = [
        opt_row(fsccompliant=1, IsFabric=2, optval_name="Customers Own Fabric"),
        opt_row(OptionValueId=11, OptChildId=77, OrderCodeValue2="C"),
    ]
    h = make(rows, {"FROM OtherDescription": [], "SLFeatureLength": []})
    h.p02_option_rows()
    assert h.v.arrayList52 == ["Customers Own Fabric#", "Red"]
    assert h.itemHasFabrics == ["XY1"]
    assert h.v.arrayList61 == [[8512], [77]]
    assert h.v.arrayList49 == [2, 0]


def test_duplicate_row_replaces_minus2_with_child_id():  # 2728-2735
    rows = [opt_row(), opt_row(OptChildId=55)]
    h = make(rows, {"FROM OtherDescription": [], "SLFeatureLength": []})
    h.p02_option_rows()
    assert len(h.v.arrayList45) == 1 and h.v.arrayList61 == [[55]]
    assert h.v.arrayList62 == ["10|1|0|100|200|R1||0|"] and h.v.arrayList53 == ["200"]


def test_duplicate_row_without_child_id_leaves_list():
    h = make([opt_row(), opt_row()], {"FROM OtherDescription": [], "SLFeatureLength": []})
    h.p02_option_rows()
    assert h.v.arrayList61 == [[-2]]


def test_flatten_fabrics_hash_skipped():  # 2616
    h = make([opt_row(OrderCodeValue2="X#")], {"FROM OtherDescription": [], "SLFeatureLength": []},
             _flattenFabrics=True)
    h.p02_option_rows()
    assert h.v.arrayList45 == [] and h.v.arrayList62 == []
    h2 = make([opt_row(OrderCodeValue2="X#")], {"FROM OtherDescription": [], "SLFeatureLength": []})
    h2.p02_option_rows()
    assert h2.v.arrayList45 == [10]


def test_syteline_availability_filtering():  # 2620, 2795
    script = {"FROM OtherDescription": [], "SLFeatureLength": []}
    # syteline on, value not in arrayList16 -> skipped
    h = make([opt_row()], script, _syteline=True)
    h.p02_option_rows()
    assert h.v.arrayList45 == []
    # in arrayList16 -> kept
    h = make([opt_row()], script, _syteline=True)
    h.v.arrayList16.append(10)
    h.p02_option_rows()
    assert h.v.arrayList45 == [10]
    # excluded by product (arrayList19) or item (arrayList20)
    for lst, key in (("arrayList19", "5~10"), ("arrayList20", "7~10")):
        h = make([opt_row()], script, _syteline=True)
        h.v.arrayList16.append(10)
        getattr(h.v, lst).append(key)
        h.p02_option_rows()
        assert h.v.arrayList45 == []


def test_ae_branch_skips_292_299_300_but_records_key():  # 2628-2684
    rows = [opt_row(OptionValueId=292), opt_row(OptionValueId=299, OrderCodeValue2="B"),
            opt_row(OptionValueId=300, OrderCodeValue2="C"), opt_row(OptionValueId=12, OrderCodeValue2="D")]
    h = make(rows, {"FROM OtherDescription": [], "SLFeatureLength": []}, longitem="AE100")
    h.p02_option_rows()
    assert len(h.v.arrayList62) == 4          # keys added even when skipped (2633)
    assert h.v.arrayList45 == [12] and h.v.arrayList55 == ["1|D"]


def test_ae_duplicate_after_skipped_index_misalignment_is_kept():  # legacy 2680 uses arrayList62 index
    rows = [opt_row(OptionValueId=292), opt_row(OptionValueId=12, OrderCodeValue2="D"),
            opt_row(OptionValueId=12, OrderCodeValue2="D", OptChildId=9)]
    h = make(rows, {"FROM OtherDescription": [], "SLFeatureLength": []}, longitem="AE100")
    with pytest.raises(IndexError):           # arrayList62 index 1 vs arrayList61 length 1
        h.p02_option_rows()


def test_catalogue_30_branch():  # 2739-2793
    rows = [opt_row(OptionValueId=292), opt_row(OptionValueId=12, OrderCodeValue2="D"),
            opt_row(OptionValueId=12, OrderCodeValue2="D", OptChildId=4)]
    h = make(rows, {"FROM OtherDescription": [], "SLFeatureLength": []}, _catalogueId=30)
    h.p02_option_rows()
    assert h.v.arrayList45 == [12] and h.v.arrayList62 == ["12|1|0|100|200|D||0|"]
    assert h.v.arrayList61 == [[4]]
    assert h.threadStage == "13"


def test_stage11_12_use_caches_and_languages():  # 2811, 2831
    script = {"FROM OtherDescription": lambda c, s, p: [{"ShortDescription": f"L{p[2]}"}],
              "SLFeatureLength": []}
    h = make([opt_row()], script, _languageId=1, _otherlanguageId=4, _maxDescriptionLength=40)
    h.v.arrayList30.append("200")  # cached stage 11
    h.p02_option_rows()
    assert h.v.arrayList29 == [] and h.v.arrayList31 == ["L4"]
    assert h.db.calls[0][2] == (40, 200, 4)


def test_stage13_cached_value_used():  # 2853-2856
    h = make([opt_row()], {"FROM OtherDescription": []})
    h.v.arrayList34.append(1)
    h.v.arrayList33.append(5)
    h.p02_option_rows()
    assert h.v.arrayList54 == [5]


def test_malformed_data_raises():
    script = {"FROM OtherDescription": [], "SLFeatureLength": []}
    with pytest.raises(LegacyFormatError):
        make([opt_row(OptionValueId="x")], script).p02_option_rows()
    with pytest.raises(LegacyFormatError):
        make([opt_row(Status=None)], script).p02_option_rows()
    with pytest.raises(LegacyCastError):       # DBNull = 1 in VB late binding (2611)
        make([opt_row(fsccompliant=None)], script).p02_option_rows()
    with pytest.raises(LegacyFormatError):     # empty optvalDescId -> legacy SQL error at stage 11
        make([opt_row(optvalDescId=None)], script).p02_option_rows()
    with pytest.raises(LegacyFormatError):     # 2864
        make([opt_row()], {"FROM OtherDescription": [], "SLFeatureLength": [{"SLFeatureLength": ""}]}).p02_option_rows()


def test_bit_true_is_not_one_in_vb_compare():  # VB Boolean True = -1
    h = make([opt_row(fsccompliant=True)], {"FROM OtherDescription": [], "SLFeatureLength": []})
    h.p02_option_rows()
    assert h.v.arrayList52 == ["Red"]
