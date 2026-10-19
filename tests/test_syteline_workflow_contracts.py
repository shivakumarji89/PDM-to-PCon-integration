"""Workflow-level contracts for the SyteLine export building blocks.

Expected values come from ExportThread.cs (line numbers in comments) or from
safety requirements (bound parameters, deterministic output, no silent errors).
"""
import itertools

import pytest

from services.syteline_export.item_selection_query import ItemSelection, build_item_selection_query
from services.syteline_export.item_source_service import SyteLineItemSourceService


class _Cursor:
    def __init__(self, description, rows):
        self.timeout = 0
        self.description = description
        self._rows = rows

    def execute(self, sql, *params):
        self.sql, self.params = sql, params

    def fetchall(self):
        return self._rows


class _Connection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.closed = False

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


def _selection(**overrides):
    base = dict(site_id=1, catalogue_id=2, language_id=3, other_language_id=4)
    base.update(overrides)
    return ItemSelection(**base)


def test_empty_selection_is_distinct_from_a_missing_result_set():
    empty = _Connection(_Cursor([("LongItem",)], []))
    assert SyteLineItemSourceService(connection_factory=lambda: empty).fetch_items(_selection()) == []
    assert empty.closed

    broken = _Connection(_Cursor(None, []))
    with pytest.raises(RuntimeError, match="no result set"):
        SyteLineItemSourceService(connection_factory=lambda: broken).fetch_items(_selection())
    assert broken.closed


def test_feature_length_query_without_result_set_raises_and_closes():
    broken = _Connection(_Cursor(None, []))
    service = SyteLineItemSourceService(connection_factory=lambda: broken)
    with pytest.raises(RuntimeError, match="no result set"):
        service.fetch_legacy_option_feature_length_rows(5, 7)
    assert broken.closed


_SCOPES = [
    dict(scope_mode="catalogue"),
    dict(scope_mode="products", product_code_id=9),
    dict(scope_mode="range", min_item="A", max_item="Z"),
    dict(scope_mode="range", min_item="BRW", max_item="BRW"),
    dict(scope_mode="list", item_list=("X.1", "Y.2", "Z.3")),
]


@pytest.mark.parametrize(
    "scope,active,syteline,cad,report,exclude_sp",
    list(itertools.product(_SCOPES, (False, True), (True, False), (False, True), (False, True), (False, True))),
)
def test_every_scope_combination_binds_one_value_per_placeholder(
    scope, active, syteline, cad, report, exclude_sp
):
    try:
        query = build_item_selection_query(_selection(
            active_only=active, syteline=syteline, miller_cad=cad, item_report=report,
            exclude_superproducts=exclude_sp, **scope,
        ))
    except ValueError:
        pytest.skip("combination rejected by validation")
    assert query.sql.count("?") == len(query.parameters)
    # No caller-supplied value may be interpolated into the SQL text.
    for value in ("X.1", "Y.2", "Z.3"):
        assert value not in query.sql


def test_identical_selection_produces_identical_query():
    first = build_item_selection_query(_selection(scope_mode="list", item_list=("B.1", "A.1")))
    second = build_item_selection_query(_selection(scope_mode="list", item_list=("B.1", "A.1")))
    assert first == second
    # List order is preserved as supplied, not re-sorted.
    assert first.parameters[-2:] == ("B.1", "A.1")


def test_feature_positions_skip_option_values_292_299_300_like_legacy():
    # ExportThread.cs 2635 (AE/cat-30 gate) and 2740 (general branch `continue`).
    from services.syteline_export.material_conversion import assign_legacy_feature_positions

    rows = [
        {"OptionValueId": v, "OptionId": o, "OrderCodeValue2": c}
        for v, o, c in ((292, 1, "A"), (10, 1, "B"), (299, 2, "C"), (11, 2, "D"), (300, 3, "E"))
    ]
    out = assign_legacy_feature_positions(rows)
    assert [r["FeaturePosition"] for r in out] == ["1|B", "2|D"]


def test_length5_rule_matrix_from_stage_20():
    # ExportThread.cs 4655-4676: raise 2 -> max length, then non-fabric >2 -> 5 when length5 is on.
    from services.syteline_export.material_conversion import resolve_legacy_feature_length as r

    cases = [
        (2, 3, False, True, 5), (2, 3, False, False, 3), (3, 3, False, True, 5),
        (4, 2, False, True, 5), (4, 2, True, True, 4), (2, 2, False, True, 2),
        (1, 9, False, True, 1),  # only a configured 2 is raised to the maximum
    ]
    for configured, maximum, fabric, l5, expected in cases:
        assert r(configured_length=configured, maximum_order_code_length=maximum,
                 is_fabric=fabric, length5_features=l5) == expected
