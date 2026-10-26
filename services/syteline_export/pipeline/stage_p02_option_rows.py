"""Stage P2: option-report row loop + stages 11-13 (ExportThread.cs 2607-2875).

Mechanical transliteration; see PORTING_CONVENTIONS.md. The chunk runs inside
``if (_exportMaterialsForPDMReport & !_superProductsOnly)`` of the per-item loop and expects the
previous chunk (lines 2475-2606) to have left in ``self.v``:

* ``option_rows``  rows of the PDMOptionDataReport batch (``sqlDataReader2`` rows, list of dict)
* ``arrayList45`` .. ``arrayList62``, ``num7``, ``num8`` (fresh per item), ``text``
* per-run caches ``arrayList16/19/20/29..34`` and ``sqlDataReader`` (current item row)
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from services.syteline_export.pipeline.netsem import (
    index_of,
    list_contains,
    list_index_of,
    list_remove,
    net_int,
    substring,  # noqa: F401  (kept for parity with sibling modules)
    tostr,
)
from services.syteline_export.pipeline.run_base import Flow


class LegacyCastError(TypeError):
    """VB ``InvalidCastException`` raised by late-bound ``Operators.CompareObject*`` on DBNull etc."""


def _vb_number(value: Any) -> float:
    """Operand conversion used by ``Operators.CompareObject(Not)Equal(obj, <int literal>)``.

    DBNull (None) raises InvalidCastException; Boolean True is -1 in VB (so ``True != 1``).
    """
    if value is None:
        raise LegacyCastError("Conversion from type 'DBNull' to type 'Integer' is not valid.")
    if isinstance(value, bool):
        return -1 if value else 0
    if isinstance(value, (int, float, Decimal)):
        return value
    try:
        return float(str(value).strip())
    except ValueError as exc:
        raise LegacyCastError(f"Conversion from string {value!r} to type 'Double' is not valid.") from exc


def _vb_equal(value: Any, number: int) -> bool:
    return _vb_number(value) == number


def _vb_not_equal(value: Any, number: int) -> bool:
    return _vb_number(value) != number


class P02Mixin:
    # ExportThread.cs 2607-2875
    def p02_option_rows(self) -> Flow | None:
        v = self.v
        for row in v.option_rows:                                                    # 2607
            self.check_abort()
            value = tostr(row["Option2"])                                            # 2609 (option name)
            text24 = tostr(row["optval_name"])                                       # 2610
            if _vb_equal(row["fsccompliant"], 1):                                    # 2611
                text24 += "#"
            self.threadStage = "10.1"
            if not (not tostr(row["OrderCodeValue2"]).endswith("#") or not self._flattenFabrics):  # 2616
                continue
            # 2620: '|' (non short-circuit) -> int.Parse always evaluated
            cov = list_contains(v.arrayList16, net_int(row["OptionValueId"]))
            cpove = list_contains(
                v.arrayList19, tostr(v.sqlDataReader["ProductId"]) + "~" + tostr(row["OptionValueId"])
            )
            ciove = list_contains(
                v.arrayList20, tostr(v.sqlDataReader["ItemId"]) + "~" + tostr(row["OptionValueId"])
            )
            if (cov and not cpove and not ciove) or not self._syteline:
                self.threadStage = "10.2"
                text25 = (
                    tostr(row["OptionValueId"]) + "|" + tostr(row["OptionId"]) + "|" + tostr(row["IsFabric"])
                    + "|" + tostr(row["OptDescId"]) + "|" + tostr(row["optvalDescId"]) + "|"
                    + tostr(row["OrderCodeValue2"]) + "|" + tostr(row["ParentOptValId"]) + "|"
                    + tostr(row["OptChildCount"]) + "|"
                )
                if self._catalogueId != 30:                                          # 2624
                    self.threadStage = "10.3"
                    text26 = tostr(v.sqlDataReader["LongItem"])
                    if text26.startswith("AE"):                                      # 2628
                        self.threadStage = "10.4"
                        if not list_contains(v.arrayList62, text25):
                            v.arrayList62.append(text25)
                            # debug accumulator text23 omitted (only read under debugExclusions)
                            n292 = _vb_not_equal(row["OptionValueId"], 292)          # 2635 (And on objects: no short circuit)
                            n299 = _vb_not_equal(row["OptionValueId"], 299)
                            n300 = _vb_not_equal(row["OptionValueId"], 300)
                            if n292 and n299 and n300:
                                self.threadStage = "10.5"
                                self._p02_add_option(row, value, text24)             # 2638-2672
                        else:
                            self.threadStage = "10.6"
                            self._p02_merge_child(row, v.arrayList62, "10.6")        # 2678-2682
                        continue                                                     # 2684
                    self.threadStage = "10.7"
                    if not list_contains(v.arrayList62, text25):
                        self.threadStage = "10.8"
                        v.arrayList62.append(text25)
                        # debug accumulator text23 omitted
                        self._p02_add_option(row, value, text24)                     # 2692-2726
                    else:
                        self.threadStage = "10.9"
                        self._p02_merge_child(row, v.arrayList62, "10.9")            # 2731-2735
                    continue                                                         # 2737
                self.threadStage = "10.11"
                n292 = _vb_not_equal(row["OptionValueId"], 292)                      # 2740
                n299 = _vb_not_equal(row["OptionValueId"], 299)
                n300 = _vb_not_equal(row["OptionValueId"], 300)
                if not (n292 and n299 and n300):
                    continue                                                         # 2742
                self.threadStage = "10.12"
                if not list_contains(v.arrayList62, text25):
                    self.threadStage = "10.13"
                    v.arrayList62.append(text25)
                    self._p02_add_option(row, value, text24)                         # 2749-2783
                else:
                    self.threadStage = "10.14"
                    self._p02_merge_child(row, v.arrayList62, "10.14")               # 2788-2792
            # else (2795-2798): only text22 debug accumulator (debugExclusions) -> omitted
        # sqlDataReader2.Close() (2800); debugExclusions block 2801-2806 omitted (flag default false)

        self.threadStage = "11"                                                      # 2807
        num11 = len(v.arrayList53) - 1
        for l in range(0, num11 + 1):                                                # 2809
            self.check_abort()
            num12 = list_index_of(v.arrayList30, v.arrayList53[l])
            if num12 <= -1:
                text27 = ""
                # 2815: ids bound as parameters (net_int keeps legacy failure on an empty id)
                v.text = (
                    "SELECT SUBSTRING(ShortDescription, 1, ?) AS ShortDescription FROM OtherDescription WITH (NOLOCK) "
                    "WHERE DescriptionId = ? AND LanguageId = ?"
                )
                rows = self.q("c2", v.text, (self._maxDescriptionLength, net_int(v.arrayList53[l]), self._languageId))
                for r in rows:                                                       # 2818
                    self.check_abort()
                    text27 += tostr(r["ShortDescription"]).replace(">", " ")
                v.arrayList29.append(text27)
                v.arrayList30.append(v.arrayList53[l])

        self.threadStage = "12"                                                      # 2827
        num13 = len(v.arrayList53) - 1
        for m in range(0, num13 + 1):                                                # 2829
            self.check_abort()
            num14 = list_index_of(v.arrayList32, v.arrayList53[m])
            if num14 <= -1:
                text28 = ""
                v.text = (
                    "SELECT SUBSTRING(ShortDescription, 1, ?) as ShortDescription FROM OtherDescription WITH (NOLOCK) "
                    "WHERE DescriptionId = ? AND LanguageId = ?"
                )
                rows = self.q("c2", v.text, (self._maxDescriptionLength, net_int(v.arrayList53[m]), self._otherlanguageId))
                for r in rows:                                                       # 2838
                    self.check_abort()
                    text28 += tostr(r["ShortDescription"]).replace(">", " ")
                v.arrayList31.append(text28)
                v.arrayList32.append(v.arrayList53[m])

        self.threadStage = "13"                                                      # 2847
        num15 = len(v.arrayList47) - 1
        for n in range(0, num15 + 1):                                                # 2849
            self.check_abort()
            num16 = 2
            num17 = list_index_of(v.arrayList34, v.arrayList47[n])
            if num17 > -1:
                num16 = int(v.arrayList33[num17])                                    # Conversions.ToInteger
            else:
                v.text = "SELECT SLFeatureLength FROM [Option] WITH (NOLOCK) WHERE OptionId = ?"
                rows = self.q("c2", v.text, (v.arrayList47[n],))
                for r in rows:                                                       # 2862
                    self.check_abort()
                    num16 = net_int(r["SLFeatureLength"])
                v.arrayList33.append(num16)
                v.arrayList34.append(v.arrayList47[n])
            v.arrayList54.append(num16)                                              # 2870
        v.arrayList63 = []                                                           # 2872
        v.arrayList64 = []
        v.arrayList65 = []
        v.num18 = len(v.arrayList45) - 1                                             # 2875
        return None

    # --- the three identical "add option" blocks (2638-2672, 2692-2726, 2749-2783), statement order kept
    def _p02_add_option(self, row: dict, value: str, text24: str) -> None:
        v = self.v
        if net_int(row["OptionId"]) != v.num8:
            v.num8 = net_int(row["OptionId"])
            v.num7 += 1
        v.arrayList47.append(net_int(row["OptionId"]))             # option id
        v.arrayList48.append(net_int(row["OptionValueId"]))        # option value id
        v.arrayList49.append(net_int(row["IsFabric"]))             # is fabric
        if net_int(row["IsFabric"]) > 0 and not list_contains(
            self.itemHasFabrics, tostr(v.sqlDataReader["LongItem"])
        ):
            self.itemHasFabrics.append(tostr(v.sqlDataReader["LongItem"]))
        v.arrayList45.append(net_int(row["OptionValueId"]))        # option value id (optvals)
        v.arrayList50.append(value)                                # option name
        v.arrayList51.append(tostr(row["OptDescId"]))
        v.arrayList52.append(text24)                               # option value name (+ '#' if FSC)
        v.arrayList53.append(tostr(row["optvalDescId"]))
        v.arrayList55.append(str(v.num7) + "|" + tostr(row["OrderCodeValue2"]).replace("#", ""))
        v.arrayList56.append(net_int(row["Status"]))
        v.arrayList57.append(tostr(row["ParentOptValId"]))
        v.arrayList58.append(tostr(row["ParentOptValCode"]))
        v.arrayList59.append(False)
        v.arrayList60.append(tostr(row["OptChildCount"]))
        if tostr(row["OptChildId"]) != "":
            v.arrayList61.append([net_int(row["OptChildId"])])
        elif index_of(tostr(row["optval_name"]).lower(), "customers own") > -1:
            v.arrayList61.append([8512])
        else:
            v.arrayList61.append([-2])

    # --- the three identical "child id replace" blocks (2678-2682, 2731-2735, 2788-2792)
    def _p02_merge_child(self, row: dict, arrayList62: list, stage: str) -> None:
        v = self.v
        text25 = (
            tostr(row["OptionValueId"]) + "|" + tostr(row["OptionId"]) + "|" + tostr(row["IsFabric"])
            + "|" + tostr(row["OptDescId"]) + "|" + tostr(row["optvalDescId"]) + "|"
            + tostr(row["OrderCodeValue2"]) + "|" + tostr(row["ParentOptValId"]) + "|"
            + tostr(row["OptChildCount"]) + "|"
        )
        if tostr(row["OptChildId"]) != "":
            list_remove(v.arrayList61[list_index_of(arrayList62, text25)], -2)
            v.arrayList61[list_index_of(arrayList62, text25)].append(net_int(row["OptChildId"]))
