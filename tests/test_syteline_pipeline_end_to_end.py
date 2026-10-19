"""End-to-end run of the composed ExportRun against a SYNTHETIC scripted database.

These fixtures are invented (not production data, not genuine legacy output) so they prove that the
transliterated stages work together (shared state, control flow, output files) - not full legacy parity.
Expectations come from the C# rules cited below.
"""
from decimal import Decimal

from services.syteline_export.pipeline.db import ScriptedExportDb
from services.syteline_export.pipeline.run import ExportRun

ITEM = dict(
    LongItem="ABC.XY", Notes=None, LegacyItem=None, Height=None, Width=None, Depth=None, Item="ABC.XY",
    Status=1, FSCCompliant=0, WeightKilos=1.5, VolumeLitres=2.5, Product="ABC", IsSuperProduct=False,
    ItemId=11, ShortDescription="A chair", AltDescription=None, MyBasePrice=Decimal("100.00"), ProductId=5,
    Product_Code="PC1", Description="Chairs", prodFS=None, ProductRangeId=1, rangeFS=None,
    ProductCategoryId=1, CommodityCode="CC", PriceCode="P1", ListPrice=None,
)


def opt(**kw):
    base = dict(Option2="Colour", optval_name="Red", fsccompliant=0, OrderCodeValue2="X", OptionValueId=1001,
                OptionId=100, IsFabric=0, OptDescId=7, optvalDescId=8, ParentOptValId=None,
                ParentOptValCode=None, OptChildCount=0, OptChildId=None, Status=1)
    base.update(kw)
    return base


OPTIONS = [
    opt(OptionValueId=1001, OrderCodeValue2="X", optval_name="Red", optvalDescId=8),
    opt(OptionValueId=1002, OrderCodeValue2="Y", optval_name="Blue", optvalDescId=9),
    opt(OptionValueId=2001, OptionId=200, Option2="Arms", OptDescId=17, OrderCodeValue2="A",
        optval_name="Arms", optvalDescId=18),
]


class Db(ScriptedExportDb):
    """Unscripted statements return an empty result set."""

    def _lookup(self, conn, sql, params):
        for needle, result in self.script.items():
            if needle in sql:
                return result(conn, sql, params) if callable(result) else result
        return []


def script(items=(ITEM,), options=OPTIONS):
    return {
        "SELECT DISTINCT Item.Item AS LongItem": list(items),
        "SELECT DISTINCT optval.OptionValueId, optval.OptionId FROM CatalogueOptionValues": [
            {"OptionValueId": o["OptionValueId"], "OptionId": o["OptionId"]} for o in options],
        "SELECT OptionValueId FROM OptionValue WITH (NOLOCK) WHERE Status = 1": [
            {"OptionValueId": o["OptionValueId"]} for o in options],
        "PDMOptionDataReport": list(options),
        "SELECT SLFeatureLength FROM [Option]": [{"SLFeatureLength": 2}],
    }


def make_run(tmp_path, db, **overrides):
    run = ExportRun(db)
    args = dict(
        filename="PDMExport", directory=str(tmp_path) + "\\", siteId=1, site="uk", catalogueId=2,
        languageId=1, currency="GBP", productCodeId=-1, productcheck=False, rangecheck=False, minitem="",
        maxitem="", listcheck=False, itemlist=[], activeonly=True, syteline=True, millerCAD=False,
        itemreport=False, sendTradeNet="", sendContract="", exportBasePrices=True,
        effectiveDate="01-Jan-2026", exportAllCataloguesInSite=False, otherlanguageId=2, exportBOMData=False,
        extendSPOpts=False, runAsService=True, length5Feats=True, ignoreOptDeps=False,
        uniqueComponents=False, formatCSI=False, plcPhantoms=False, excludeSuperProducts=False,
        superProductsOnly=False, flattenFabrics=False,
    )
    args.update(overrides)
    run.init_thread(**args)
    return run


def read_rows(tmp_path, kind):
    data = (tmp_path / "temp" / f"PDMExport_{kind}_data.txt").read_bytes().decode("utf-8")
    return data.split("\r\n")[1:-1]          # drop the header and the trailing empty element


def test_item_with_two_options_produces_item_feature_slots_and_material_rows(tmp_path):
    run = make_run(tmp_path, Db(script()))
    run.exec_thread()
    assert run.fatal_error is None and run.errors == [] and run.outputs_written
    (item_row, *component_rows) = read_rows(tmp_path, "item")
    fields = item_row.split("\t")
    assert fields[:4] == ["ABC.XY", "no", "A chair", "A"]
    assert fields[9] == "PC1"                       # Product_Code (ExportThread.cs 4385-4417)
    # Two options of feature length 2: first position F01 (num6 starts at 1), the next advances by 2.
    assert fields[34:36] == ["F01-02", "F03-02"] and set(fields[36:54]) == {""}
    assert fields[27] == "XX-XX"                    # feature template, one X per code character per option
    # One item-tab row per option value (9-Fnn-0m-<code>), written once each.
    assert [r.split("\t")[0] for r in component_rows] == ["9-F01-02-X", "9-F01-02-Y", "9-F03-02-A"]
    materials = [r.split("\t") for r in read_rows(tmp_path, "material")]
    assert [(m[0], m[1], m[2], m[3]) for m in materials] == [
        ("ABC.XY", "F01-02", "9-F01-02-X", "X"), ("ABC.XY", "F01-02", "9-F01-02-Y", "Y"),
        ("ABC.XY", "F03-02", "9-F03-02-A", "A"),
    ]
    assert [m[7] for m in materials] == ["2", "3", "4"]      # getItemSequence starts at 2 (ExportThread.cs 1123)


def test_two_items_are_processed_in_query_order(tmp_path):
    second = dict(ITEM, LongItem="ABC.ZZ", Item="ABC.ZZ", ItemId=12)
    run = make_run(tmp_path, Db(script(items=(ITEM, second))))
    run.exec_thread()
    assert run.fatal_error is None and run.errors == []
    primary = [r.split("\t")[0] for r in read_rows(tmp_path, "item") if not r.startswith("9-")]
    assert primary == ["ABC.XY", "ABC.ZZ"]
    assert run.items_processed == 2


def test_cancel_stops_before_the_next_item_but_finishes_cleanly(tmp_path):
    second = dict(ITEM, LongItem="ABC.ZZ", Item="ABC.ZZ", ItemId=12)
    db = Db(script(items=(ITEM, second)))
    run = make_run(tmp_path, db)
    original = db.query

    def query(conn, sql, params=(), *, stage=""):
        if "PDMOptionDataReport" in sql:
            run.abort_thread()
        return original(conn, sql, params, stage=stage)
    db.query = query
    run.exec_thread()
    assert run.items_processed == 1 and run._abortThread
    assert run.fatal_error is None


def test_database_failure_is_fatal_and_cleanup_still_runs(tmp_path):
    db = Db(script())
    original = db.query

    def query(conn, sql, params=(), *, stage=""):
        if "PDMOptionDataReport" in sql:
            raise RuntimeError("connection reset")
        return original(conn, sql, params, stage=stage)
    db.query = query
    run = make_run(tmp_path, db)
    run.exec_thread()
    assert isinstance(run.fatal_error, RuntimeError) and "connection reset" in str(run.fatal_error)
    assert not run.outputs_written
    assert db.closed                                  # the finally block closed every session


def test_an_item_with_no_option_rows_still_produces_its_item_row(tmp_path):
    run = make_run(tmp_path, Db(script(options=[])))
    run.exec_thread()
    assert run.fatal_error is None and run.errors == []
    (item_row,) = read_rows(tmp_path, "item")
    assert item_row.split("\t")[0] == "ABC.XY" and read_rows(tmp_path, "material") == []


def test_empty_item_selection_writes_headers_only(tmp_path):
    run = make_run(tmp_path, Db(script(items=())))
    run.exec_thread()
    assert run.fatal_error is None and run.errors == [] and run.items_processed == 0
    assert read_rows(tmp_path, "item") == [] and read_rows(tmp_path, "material") == []
