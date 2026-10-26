"""ExportThread.cs 2876-3578: per-option loop of the per-item body (stages 14 - 16.15).

Mechanical transliteration of the ``for (int num19 ...)`` loop over the item's options.
Read PORTING_CONVENTIONS.md. Locals shared with other ranges live in ``self.v``;
locals used only inside this range are plain Python locals.

Parallel lists of the option loop (all assigned by earlier stages, ExportThread.cs 2505-2771):
    arrayList45 optionValueId (int)         arrayList47 optionId (int)
    arrayList48 optionValueId (int)         arrayList49 IsFabric (int 0/1/2)
    arrayList50 option name (str)           arrayList52 option value description (str)
    arrayList53 optvalDescId (str)          arrayList55 "<n>|<order code>" (str)
    arrayList56 Status (int)                arrayList57 ParentOptValId (str, "" = none)
    arrayList58 ParentOptValCode (str)      arrayList59 parent-unavailable flags (bool)
    arrayList60 OptChildCount (str)
"""
from __future__ import annotations

from services.syteline_export.pipeline.netsem import (
    index_of,
    list_contains,
    list_index_of,
    net_bool,
    net_double,
    net_int,
    substring,
    tostr,
)
from services.syteline_export.pipeline.run_base import Flow

_INC_PRICE_CASE = (
    "CASE WHEN pc.BasePriceRef = 1 THEN itov.IncrementalPrice "
    "WHEN pc.BasePriceRef = 2 THEN itov.IncrementalPrice2 "
    "WHEN pc.BasePriceRef = 3 THEN itov.IncrementalPrice3 END"
)


def _net_replace(text: str, old: str, new: str) -> str:
    """C# ``string.Replace(old, new)``: an empty ``old`` throws ArgumentException."""
    if old == "":
        raise ValueError("String cannot be of zero length. (Parameter 'oldValue')")
    return text.replace(old, new)


def _increment_text(entry: str, token: str) -> str | None:
    """Amount text of an increment entry ``<token>|<amount>``, or None if the entry is not the token's.

    INTENTIONAL DEVIATION from ExportThread.cs 3269/3316/3362, which tests
    ``entry.IndexOf(token + "|") > -1`` and then ``double.Parse(entry.Replace(token + "|", ""))``.
    The substring match makes an entry such as ``PREFIX-ABC|4`` "match" token ``ABC`` and then crash
    in ``double.Parse("PREFIX-4")``, or silently sum a wrong amount (``2ABC|4`` -> 24). Here an entry
    belongs to the token only when it starts with ``<token>|``. A matching entry with a malformed
    amount still raises (legacy behaviour). Protected by tests/test_syteline_pipeline_stage_p03.py.
    """
    marker = token + "|"
    return entry[len(marker):] if entry.startswith(marker) else None


def _increment_amount(entry: str, token: str) -> float | None:
    text = _increment_text(entry, token)
    return None if text is None else net_double(text)


class P03Mixin:
    def p03_materials(self) -> Flow | None:  # ExportThread.cs:2876-3578
        v = self.v
        # The per-item loop state: v.sqlDataReader is the current item row (dict).

        def is_sp() -> bool:
            # bool.Parse(sqlDataReader["IsSuperProduct"].ToString()) && !flag4
            return net_bool(v.sqlDataReader["IsSuperProduct"]) and not v.flag4

        def inc_head(item_col: str) -> tuple[str, list]:
            # text = "SELECT DISTINCT <item_col>, CASE ... AS MyIncrementalPrice " [+ IncList column]
            sql = f"SELECT DISTINCT {item_col}, {_INC_PRICE_CASE} AS MyIncrementalPrice "
            params: list = []
            if self._millerCAD | (self._syteline & (not self._exportBasePrices)):
                # text9 == "'" + _effectiveDate + "'" (ExportThread.cs:2224); bound as a parameter
                sql += (
                    ", dbo.fnGetListPrice(?, " + _INC_PRICE_CASE
                    + ", pc.PriceCode, ?, 'DMY', pm.Rounding, ?, NULL) AS IncList "
                )
                params += [self._currency, self._effectiveDate, self._siteId]
            return sql, params

        def read_increments(rows: list, target: list) -> None:
            # while (sqlDataReader7.Read()) { ... } shared by the stage 14 and stage 15 readers
            for row in rows:
                self.check_abort()
                # debug-only block omitted (flag default false)
                if self._millerCAD:
                    if tostr(row["IncList"]) != "":
                        target.append(tostr(row["Item"]) + "|" + tostr(net_double(row["IncList"])))
                elif self._syteline & (not self._exportBasePrices):
                    if tostr(row["IncList"]) != "":
                        target.append(tostr(row["Item"]) + "|" + tostr(net_double(row["IncList"])))
                elif tostr(row["MyIncrementalPrice"]) != "":
                    target.append(
                        tostr(row["Item"]) + "|" + tostr(net_double(row["MyIncrementalPrice"]))
                    )

        for num19 in range(v.num18 + 1):  # num18 = arrayList45.Count - 1 (ExportThread.cs:2875, other range)
            self.check_abort()
            arrayList66 = []  # incremental prices "<item>|<increment>" for this option
            # debug-only block omitted (flag default false)  [debugItemsAndOptions text20]
            # NOTE: text20 is only ever read under debugItemsAndOptions/debugExclusions
            # (ExportThread.cs:4486) so every text20/text8 accumulation in this range is dropped.

            # --- stage 14 (ExportThread.cs:2883-2927)
            head, params = inc_head("Item.Item")
            v.text = (
                head
                + "FROM ItemOptionValues itov WITH (NOLOCK) CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x "
                "INNER JOIN Item ON itov.ItemId = Item.ItemId INNER JOIN Product ON Item.ProductId = Product.ProductId "
                "INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) "
                "IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) "
                "ELSE Product.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = ? "
                "INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode "
                "INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency = ? "
                "WHERE OptionValueId = ? AND Item.ItemId = ? "
            )
            params = params + [self._siteId, self._currency, v.arrayList45[num19], v.sqlDataReader["ItemId"]]
            if is_sp():  # 2889
                head, params = inc_head("subitem.Item")
                v.text = (
                    head
                    + "FROM ItemOptionValues itov WITH (NOLOCK) CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x "
                    "INNER JOIN ItemComponents itco ON itov.ItemId = itco.SubItemId "
                    "INNER JOIN Item subitem ON itco.SubItemId = subitem.ItemId "
                    "INNER JOIN Product ON subitem.ProductId = Product.ProductId "
                    "INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = subitem.ItemId ) "
                    "IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = subitem.ItemId ) "
                    "ELSE Product.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = ? "
                    "INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode "
                    "INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency = ? "
                    "WHERE OptionValueId = ? AND itco.ItemId = ? "
                )
                params = params + [self._siteId, self._currency, v.arrayList45[num19], v.sqlDataReader["ItemId"]]
            self.threadStage = "14"
            sqlDataReader7 = self.q("c2", v.text, params)  # CommandTimeout 600 (Db default is 900)
            read_increments(sqlDataReader7, arrayList66)
            self.threadStage = "14.1"
            if is_sp() and len(arrayList66) == 0:  # 2929
                self.threadStage = "14.2"
                if v.arrayList49[num19] == 0:
                    text29 = tostr(v.arrayList55[num19])
                    if index_of(text29, "|") > -1:
                        text29 = substring(text29, index_of(text29, "|") + 1)
                    self.threadStage = "14.2"
                    head, params = inc_head("subitem.Item")
                    v.text = head
                    self.threadStage = "14.3"
                    v.text = (
                        v.text
                        + "FROM ItemOptionValues itov WITH (NOLOCK) CROSS JOIN ( SELECT NULL AS ProductCodeIdOverride ) x "
                        "INNER JOIN OptionValue optval ON itov.OptionValueId = optval.OptionValueId "
                        "INNER JOIN [Option] opt ON optval.OptionId = opt.OptionId AND opt.IsFabric = 0 "
                        "/* Fabrics are global => will not use different OptionValueIds */ "
                        "INNER JOIN ItemComponents itco ON itov.ItemId = itco.SubItemId "
                        "INNER JOIN Item ON itco.ItemId = Item.ItemId "
                        "INNER JOIN Item subitem ON itco.SubItemId = subitem.ItemId "
                        "INNER JOIN Product subproduct ON subitem.ProductId = subproduct.ProductId "
                        "INNER JOIN Product ON Item.ProductId = Product.ProductId "
                        "INNER JOIN Product_Code pc ON CASE WHEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) "
                        "IS NOT NULL THEN ( SELECT ProductCodeIdOverride FROM Item i2 WHERE i2.ItemId = Item.ItemId ) "
                        "ELSE Product.ProductCodeId END = pc.ProductCodeId AND pc.SiteId = ? "
                        "INNER JOIN PriceMatrix pm ON pc.PriceCode = pm.ItemPriceCode "
                        "INNER JOIN Currency ON pm.CustPriceCode = Currency.PriceCode AND Currency.Currency = ? "
                    )
                    params = params + [self._siteId, self._currency]
                    if not self._extendSPOpts:
                        v.text = v.text + "WHERE optval.OptionValueId = ? "
                        params = params + [v.arrayList45[num19]]
                    else:
                        v.text = (
                            v.text
                            + "WHERE ((optval.OrderCodeValue = ? AND subproduct.ProductRangeId <> 999 "
                            "/* for SPs with components that are products in their own right */) "
                            "OR (optval.OptionValueId = ? AND subproduct.ProductRangeId = 999 "
                            "/* for standard SP components */)) "
                        )
                        params = params + [text29, v.arrayList45[num19]]
                    self.threadStage = "14.4"
                    v.text = v.text + "AND Item.ItemId = ? "
                    params = params + [v.sqlDataReader["ItemId"]]
                    self.threadStage = "15"
                    sqlDataReader7 = self.q("c2", v.text, params)
                    read_increments(sqlDataReader7, arrayList66)

            # --- stage 16 (ExportThread.cs:2982-3059): parent item resolution
            flag5 = True  # noqa: F841  (assigned, never read in legacy)
            self.threadStage = "16"
            text30 = tostr(v.sqlDataReader["Item"])  # myparentitem
            text31 = tostr(v.sqlDataReader["Item"])  # fullparentitem
            arrayList67 = []  # additional parents "<item><<optionId>>"
            if is_sp():  # 2987
                flag6 = False
                num20 = 1
                while True:  # do { ... } while (num20 <= 2)
                    self.check_abort()
                    num21 = int(v.arrayList47[num19])  # Conversions.ToInteger(arrayList47[num19].ToString()) (int column)
                    if (num20 == 2) & (tostr(v.arrayList50[num19]).lower() == "access flap finish"):
                        num21 = 1142
                    text32 = ""
                    value2 = tostr(v.sqlDataReader["ItemId"]) + "~" + str(num21)
                    num22 = list_index_of(v.arrayList44, value2)
                    if num22 > -1:
                        text32 = tostr(v.arrayList43[num22])
                        flag6 = True
                    else:
                        v.text = (
                            "SELECT sub_item.Item AS parentitem FROM ItemComponents itco "
                            "INNER JOIN Item sub_item ON itco.SubItemId = sub_item.ItemId "
                            "WHERE itco.ItemId = ? AND (CHARINDEX(convert(varchar, ?) + '|', itco.FeaturePositionString) = 1 "
                            "OR CHARINDEX('|' + convert(varchar, ?) + '|', itco.FeaturePositionString) > 0) "
                            "ORDER BY itco.ComponentSequence"
                        )
                        self.threadStage = "16.1"
                        sqlDataReader2 = self.q("c2", v.text, [v.sqlDataReader["ItemId"], num21, num21])
                        for row in sqlDataReader2:
                            self.check_abort()
                            if tostr(row["parentitem"]) != "":
                                text32 = text32 + tostr(row["parentitem"]) + "|"
                                flag6 = True
                        if flag6:
                            v.arrayList43.append(text32)
                            v.arrayList44.append(value2)
                    if flag6:
                        text30 = text32
                        text31 = text32
                        # debug-only block omitted (flag default false)
                        array = text30.split("|")
                        for num24 in range(len(array)):
                            self.check_abort()
                            if array[num24] == "":
                                continue
                            if num24 == 0:
                                text30 = array[num24]
                                continue
                            arrayList67.append(array[num24] + "<" + str(v.arrayList47[num19]) + ">")
                            if not list_contains(v.arrayList26, v.arrayList47[num19]):
                                v.arrayList26.append(v.arrayList47[num19])
                        break
                    num20 += 1
                    if not (num20 <= 2):
                        break

            # --- 16.2 (ExportThread.cs:3060-3112): parent option value lookup
            self.threadStage = "16.2"
            # debug-only block omitted (flag default false)
            text33 = "0"  # sequence
            flag7 = False  # foundAtLeastOneParent
            if v.arrayList57[num19] != "":
                for num26 in range(len(v.arrayList63)):
                    self.check_abort()
                    if not (v.arrayList63[num26] == net_int(v.arrayList57[num19])):
                        continue
                    flag7 = True
                    # debug-only block omitted (flag default false)
                    if (
                        (index_of(tostr(v.arrayList64[num26]), text30) > -1)
                        or (v.arrayList49[num19] == 2)
                        or (v.arrayList47[num19] == 9275)
                        or (v.arrayList47[num19] == 9313)
                        or (v.arrayList47[num19] == 9279)
                        or (v.arrayList47[num19] == 9325)
                        or (v.arrayList47[num19] == 9283)
                        or (v.arrayList47[num19] == 9327)
                        or (v.arrayList47[num19] == 9287)
                        or (v.arrayList47[num19] == 9329)
                        or ((text30.startswith("GHS") | text30.startswith("GHG"))
                            and ((v.arrayList47[num19] == 8) or (v.arrayList47[num19] == 9487)))
                    ):
                        text30 = tostr(v.arrayList64[num26])
                        # debug-only block omitted (flag default false)
                    self.threadStage = "16.3"
                    for num28 in range(len(arrayList67)):
                        self.check_abort()
                        text34 = tostr(arrayList67[num28])
                        if index_of(text34, "<") > -1:
                            text34 = substring(text34, 0, index_of(text34, "<"))
                        if index_of(tostr(v.arrayList64[num26]), text34) > -1:
                            arrayList67[num28] = v.arrayList64[num26]
                if not text30.startswith("9-"):
                    v.arrayList59[num19] = True

            # --- 16.4 - 16.8 (ExportThread.cs:3113-3199): sequence and material code
            self.threadStage = "16.4"
            # debug-only block omitted (flag default false)
            text35 = ""
            _o55 = tostr(v.arrayList55[num19])
            # NewLateBinding Substring(0, IndexOf("|")) -> Conversions.ToInteger(string)
            num29 = net_int(substring(_o55, 0, index_of(_o55, "|")))  # option position number
            text36 = ""  # "_#_" when the option has more than one parent
            _sp = net_bool(v.sqlDataReader["IsSuperProduct"])
            if (len(arrayList67) > 0) | (((text30 != tostr(v.sqlDataReader["Item"])) & _sp) and not v.flag4):
                text36 = "_#_"
            self.threadStage = "16.5"
            if text30.startswith("9-"):
                if not list_contains(v.arrayList14, text30):
                    v.arrayList14.append(text30)
                    v.arrayList15.append(2)
                else:
                    v.arrayList15[list_index_of(v.arrayList14, text30)] = (
                        v.arrayList15[list_index_of(v.arrayList14, text30)] + 1
                    )
                text33 = str(v.arrayList15[list_index_of(v.arrayList14, text30)])
                # debugMaterialSequence is false: prefix omitted
            else:
                text33 = str(self.get_item_sequence(text30, tostr(v.arrayList55[num19])))
                v.text14 = text30 + text35
                v.text15 = tostr(v.arrayList55[num19])
            self.threadStage = "16.6"
            text37 = "9-"  # material code
            if ((v.arrayList49[num19] != 1) & (not self._ignoreOptDeps)) and net_double(v.arrayList60[num19]) > 0:
                # ConditionalCompareObjectGreater(string, 0): VB converts the string to Double
                if is_sp():
                    text37 = text37 + text30 + "-"
                else:
                    text37 = text37 + tostr(v.sqlDataReader["Item"]) + "-"
            # debug-only block omitted (flag default false)
            self.threadStage = "16.7"
            text37 = (
                text37 + "[opt" + str(num29) + "]-"
                + substring(_o55, index_of(_o55, "|") + 1).replace(" ", "_")
            )
            if (text30.startswith("MRFN") | text30.startswith("9-MRFN")) and (
                (v.arrayList48[num19] == 300464)
                or (v.arrayList48[num19] == 300563)
                or (v.arrayList48[num19] == 300564)
                or (v.arrayList48[num19] == 300565)
                or (v.arrayList48[num19] == 300566)
                or (v.arrayList48[num19] == 300567)
            ):
                text37 = text37 + "-" + tostr(v.arrayList58[num19])
            text38 = ""  # material line
            self.threadStage = "16.8"
            num30 = 0.0  # accumulated increment
            # debug-only block omitted (flag default false)

            # --- increment accumulation (ExportThread.cs:3200-3277)
            for num32 in range(len(arrayList66)):
                self.check_abort()
                text39 = text30
                if text39.startswith("9-"):
                    text39 = substring(text39, 2)
                # debug-only block omitted (flag default false)
                if index_of(text39, "-") > -1:
                    num33 = 0
                    _item = tostr(v.sqlDataReader["Item"])
                    if index_of(_item, "-") > -1:
                        text39 = _net_replace(text39, _item, _item.replace("-", "_"))
                        num33 = 1
                    elif index_of(text31, "-") > -1:
                        array5 = text31.split("|")
                        for num35 in range(len(array5)):
                            self.check_abort()
                            if array5[num35] != "":
                                text39 = _net_replace(text39, array5[num35], array5[num35].replace("-", "~"))
                        num33 = 2
                    if index_of(text39, "-") > -1:
                        text39 = substring(text39, 0, index_of(text39, "-"))
                    if num33 == 1:
                        text39 = _net_replace(text39, _item.replace("-", "_"), _item)
                    elif num33 == 2:
                        array6 = text31.split("|")
                        for num37 in range(len(array6)):
                            self.check_abort()
                            if array6[num37] != "":
                                text39 = _net_replace(text39, array6[num37].replace("-", "~"), array6[num37])
                # debug-only block omitted (flag default false)
                # DEVIATION (legacy substring match fixed): see _increment_amount
                amount = _increment_amount(tostr(arrayList66[num32]), text39)
                if amount is not None:
                    num30 += amount
                # else: debug-only block omitted (flag default false)

            # --- 16.9 / 16.10 (ExportThread.cs:3278-3375): material line text38
            self.threadStage = "16.9"
            text40 = ""
            # Array.Reverse(text37.ToCharArray()) result is never used: omitted (no side effects)
            text41 = "10"
            self.threadStage = "16.10"
            # debug-only block omitted (flag default false)

            def opt_code() -> str:
                # parseOptCode(arrayList55[num19].Substring(arrayList55[num19].IndexOf("|") + 1), (int)arrayList48, (int)arrayList47)
                return self.parse_opt_code(
                    substring(_o55, index_of(_o55, "|") + 1),
                    int(v.arrayList48[num19]),
                    int(v.arrayList47[num19]),
                )

            if num30 == 0.0:
                self.threadStage = "16.10a"
                text38 = (
                    text30 + "\t[opt" + text36 + str(num29) + "]\t"
                    + text37.replace("[opt", "[opt" + text36) + "\t"
                )
                text38 += opt_code()
                if text36 != "":
                    text38 = text38 + "|" + self.get_translation(
                        v.arrayList52, v.arrayList53, v.arrayList29, v.arrayList30, num19
                    )
                text38 = text38 + "\t" + tostr(num30) + "\t1\t0\t"
                if text36 != "":
                    text38 = text38 + ("[opt" + text36 + str(num29) + "]").replace("_", "~") + "[seq]" + text33 + "\t\t\t10\t\r\n"
                else:
                    text38 = text38 + text33 + "\t\t\t" + text41 + "\t\r\n"
                self.threadStage = "16.11a"
                for num39 in range(len(arrayList67) - 1, -1, -1):
                    self.check_abort()
                    text42 = tostr(arrayList67[num39])
                    if index_of(text42, "<") > -1:
                        text42 = substring(text42, 0, index_of(text42, "<"))
                    num30 = 0.0
                    for num41 in range(len(arrayList66)):
                        self.check_abort()
                        # debug-only block omitted (flag default false)
                        # DEVIATION (legacy substring match fixed): see _increment_amount
                        if text42 != "":
                            text43 = _increment_text(tostr(arrayList66[num41]), text42)
                            if text43 is not None and text43 != "":
                                num30 += net_double(text43)
                    text38 = (
                        text38 + text40 + tostr(arrayList67[num39]) + "\t[opt_" + str(num39 + 1) + "_" + str(num29) + "]\t"
                        + _net_replace(text37, text30, text42).replace("[opt", "[opt_" + str(num39 + 1) + "_") + "\t"
                    )
                    text38 += opt_code()
                    if text36 != "":
                        text38 = text38 + "|" + self.get_translation(
                            v.arrayList52, v.arrayList53, v.arrayList29, v.arrayList30, num19
                        )
                    text38 = (
                        text38 + "\t" + tostr(num30) + "\t1\t0\t"
                        + ("[opt_" + str(num39 + 1) + "_" + str(num29) + "]").replace("_", "~")
                        + "[seq]" + text33 + "\t\t\t10\t\r\n"
                    )
            else:
                self.threadStage = "16.10b"
                text38 = (
                    text30 + "\t[opt" + text36 + str(num29) + "]\t"
                    + text37.replace("[opt", "[opt" + text36) + "\t"
                )
                text38 += opt_code()
                if text36 != "":
                    text38 = text38 + "|" + self.get_translation(
                        v.arrayList52, v.arrayList53, v.arrayList29, v.arrayList30, num19
                    )
                text38 = text38 + "\t" + tostr(num30) + "\t1\t0\t"
                if text36 != "":
                    text38 = text38 + ("[opt" + text36 + str(num29) + "]").replace("_", "~") + "[seq]" + text33 + "\t\t\t10\t\r\n"
                else:
                    text38 = text38 + text33 + "\t\t\t" + text41 + "\t\r\n"
                self.threadStage = "16.11b"
                for num43 in range(len(arrayList67) - 1, -1, -1):
                    self.check_abort()
                    text44 = tostr(arrayList67[num43])
                    if index_of(text44, "<") > -1:
                        text44 = substring(text44, 0, index_of(text44, "<"))
                    num30 = 0.0
                    for num45 in range(len(arrayList66)):
                        self.check_abort()
                        # debug-only block omitted (flag default false)
                        # DEVIATION (legacy substring match fixed): see _increment_amount
                        amount = _increment_amount(tostr(arrayList66[num45]), text44)
                        if amount is not None:
                            num30 += amount
                    text38 = (
                        text38 + text40 + tostr(arrayList67[num43]) + "\t[opt_" + str(num43 + 1) + "_" + str(num29) + "]\t"
                        + _net_replace(text37, text30, text44).replace("[opt", "[opt_" + str(num43 + 1) + "_") + "\t"
                    )
                    text38 += opt_code()
                    if text36 != "":
                        text38 = text38 + "|" + self.get_translation(
                            v.arrayList52, v.arrayList53, v.arrayList29, v.arrayList30, num19
                        )
                    text38 = (
                        text38 + "\t" + tostr(num30) + "\t1\t0\t"
                        + ("[opt_" + str(num43 + 1) + "_" + str(num29) + "]").replace("_", "~")
                        + "[seq]" + text33 + "\t\t\t10\t\r\n"
                    )

            # --- 16.12 - 16.15 (ExportThread.cs:3376-3577): dedupe and registration
            self.threadStage = "16.12"
            # debug-only block omitted (flag default false)
            self.threadStage = "16.13"
            if text30.startswith("9-") or (v.arrayList57[num19] == "") or (v.arrayList59[num19] is True):
                text45 = text30 + "|[opt" + text36 + str(num29) + "]|" + substring(_o55, index_of(_o55, "|") + 1)
                if not list_contains(v.arrayList9, text30):
                    v.arrayList9.append(text30)
                    v.arrayList10.append([])
                    v.arrayList11.append([])
                text46 = text37.replace("[opt", "[opt" + text36)
                flag8 = False  # skip
                if v.arrayList49[num19] == 2:
                    # text20 "SKIPPING fabric colour" (debug-only accumulator) omitted
                    flag8 = True
                if (v.arrayList49[num19] == 1) or (v.arrayList49[num19] == 2):
                    num46 = num29
                    text47 = tostr(v.arrayList55[num19]) + ":" + tostr(v.arrayList52[num19]) + "~" + str(num46)
                    if not list_contains(self.skippedFabricColours, text47):
                        self.skippedFabricColours.append(text47)
                if self._ignoreOptDeps:
                    flag8 = True
                    num47 = list_index_of(v.arrayList9, text30)
                    left = (not list_contains(v.arrayList65, text45)) and (
                        (not list_contains(v.arrayList64, text46)) or (text45 != text46)
                    )
                    obj2 = list_contains(v.arrayList11[num47], text45)
                    left2 = left and (obj2 == False)  # noqa: E712
                    obj2 = list_contains(v.arrayList10[num47], text46)
                    if left2 and ((obj2 == False) or (text45 != text46)):  # noqa: E712
                        flag8 = False
                    # else: debug-only block omitted (flag default false)
                if ((not net_bool(v.sqlDataReader["IsSuperProduct"])) and (not v.flag4)) and (v.arrayList59[num19] is True):
                    # text20 "SKIPPING ... non-super product" (debug-only accumulator) omitted
                    flag8 = True
                self.threadStage = "16.14"
                # debug-only block omitted (flag default false)
                if not flag8:
                    self.threadStage = "16.15a"
                    v.arrayList65.append(text45)
                    v.arrayList11[list_index_of(v.arrayList9, text30)].append(text45)
                    self.materialstr += text38.replace(
                        tostr(v.sqlDataReader["Item"]) + "\t", tostr(v.sqlDataReader["LongItem"]) + "\t"
                    )
                    v.arrayList3.append(text46)
                    v.arrayList4.append("[opt" + text36 + str(num29) + "]")
                    v.arrayList63.append(v.arrayList45[num19])
                    v.arrayList64.append(text46)
                    v.arrayList10[list_index_of(v.arrayList9, text30)].append(text46)
                    for num49 in range(len(arrayList67)):
                        self.check_abort()
                        text48 = tostr(arrayList67[num49])
                        if index_of(text48, "<") > -1:
                            text48 = substring(text48, 0, index_of(text48, "<"))
                        v.arrayList63.append(v.arrayList45[num19])
                        text49 = _net_replace(text46, text30, text48)
                        if index_of(text49, "[opt_0") > -1:
                            text49 = text49.replace("[opt_0", "[opt_" + str(num49 + 1))
                        if index_of(text49, "[opt_#") > -1:
                            text49 = text49.replace("[opt_#", "[opt_" + str(num49 + 1))
                        v.arrayList64.append(text49)
                    text50 = ""
                    num50 = list_index_of(v.arrayList30, v.arrayList53[num19])
                    if num50 > -1:
                        text50 = tostr(v.arrayList29[num50])
                    if text50 != "":
                        v.arrayList5.append(text50)
                    else:
                        v.arrayList5.append(v.arrayList52[num19])
                    num51 = list_index_of(v.arrayList32, v.arrayList53[num19])
                    if num51 > -1:
                        v.arrayList6.append(v.arrayList31[num51])
                    else:
                        v.arrayList6.append("")
                    v.arrayList7.append(v.arrayList56[num19])
                    continue
                self.threadStage = "16.15b"
                text51 = text31
                if (not text51.endswith("|")) & (len(text51) > 0):
                    text51 += "|"
                while index_of(text51, "|") > -1:
                    self.check_abort()
                    text52 = substring(text51, 0, index_of(text51, "|"))
                    if (not list_contains(v.arrayList12, text52)) and v.arrayList49[num19] < 2:
                        v.arrayList12.append(text52)
                        v.arrayList13.append(v.arrayList55[num19])
                    text51 = "" if index_of(text51, "|") >= len(text51) - 1 else substring(text51, index_of(text51, "|") + 1)
            else:
                pass  # text20 "IGNORED myparentitem" (debug-only accumulator) omitted
        return None
