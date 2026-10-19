"""Regression tests for defects found by the independent fidelity review of the ExportThread port.

Each expected value is derived from the C# (line cited) or from documented .NET Framework behaviour.
"""
import itertools

import pytest

from services.syteline_export.pipeline.db import PyodbcExportDb
from services.syteline_export.pipeline.netsem import double_to_string
from tests.test_syteline_pipeline_stage_p05 import base_row, make as make_p05


@pytest.mark.parametrize("exp_components,super_only", list(itertools.product((True, False), (True, False))))
def test_p05_17_14_branch_condition_is_C_sharp_precedence_4316(exp_components, super_only):
    # C# 4316: (text5 == "yes") & (!_exportSPComponentMaterials | _superProductsOnly)
    # i.e. skip the component rows when components are NOT exported OR only super products are exported.
    h = make_p05(base_row(IsSuperProduct=True), _syteline=True,
                 _exportSPComponentMaterials=exp_components, _superProductsOnly=super_only)
    h.p05_item_row_and_renumber()
    expect_skip_branch = (not exp_components) or super_only
    assert (h.v.p05_else_branch is False) == expect_skip_branch


def test_f2_rounds_like_dotnet_framework_half_away_from_zero_on_15_digits():
    from services.syteline_export.pipeline.stage_p05_item_row import _f2
    assert _f2(10.125) == "10.13"      # Python format() would give 10.12 (exact binary half-even)
    assert _f2(2.675) == "2.68"        # exact binary value is 2.67499999...; .NET reduces to 15 digits first
    assert _f2(0.0) == "0.00" and _f2(5) == "5.00"


@pytest.mark.parametrize("value,text", [
    (0.1 + 0.2, "0.3"), (1 / 3, "0.333333333333333"), (5.0, "5"), (100.0, "100"), (1e-05, "1E-05"),
    (0.0001, "0.0001"), (1e15, "1E+15"), (123456789012345.0, "123456789012345"), (-2.5, "-2.5"),
])
def test_double_to_string_is_dotnet_framework_15_significant_digits(value, text):
    assert double_to_string(value) == text


def test_pyodbc_query_skips_row_count_results_before_the_select():
    class Cursor:
        timeout = 0

        def __init__(self):
            self.sets = [None, None, [("a",)]]
            self.description = None

        def execute(self, sql, *params):
            self._advance()

        def _advance(self):
            current = self.sets.pop(0)
            self.description = [("col",)] if current is not None else None
            self._rows = current or []

        def nextset(self):
            if not self.sets:
                return False
            self._advance()
            return True

        def fetchall(self):
            return self._rows

        def close(self):
            pass

    class Connection:
        def cursor(self):
            return Cursor()

        def close(self):
            pass

    rows = PyodbcExportDb(lambda: Connection()).query("c1", "EXEC p")
    assert rows == [{"col": "a"}]


def test_pyodbc_query_without_any_result_set_is_an_error():
    class Cursor:
        timeout = 0
        description = None

        def execute(self, *a):
            pass

        def nextset(self):
            return False

        def close(self):
            pass

    class Connection:
        def cursor(self):
            return Cursor()

    with pytest.raises(RuntimeError, match="no result set"):
        PyodbcExportDb(lambda: Connection()).query("c1", "EXEC p")


def test_pyodbc_sessions_use_autocommit_and_per_name_factories():
    created = []

    class Connection:
        autocommit = False

        def __init__(self, label):
            self.label = label
            created.append(self)

        def cursor(self):
            raise AssertionError("not used")

        def close(self):
            pass

    db = PyodbcExportDb(lambda: Connection("default"), session_factories={"tradenet": lambda: Connection("tn")})
    db._session("c1")
    db._session("tradenet")
    assert [(c.label, c.autocommit) for c in created] == [("default", True), ("tn", True)]
    db.close()


def test_xlsx_control_characters_are_stripped_not_fatal():
    from services.syteline_export.pipeline.io_output import _XLSX_ILLEGAL
    assert _XLSX_ILLEGAL.sub("", "a\x0bb\x00c\td") == "abc\td"      # tab (0x09) is legal, kept
