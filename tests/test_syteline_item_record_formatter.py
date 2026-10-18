from services.syteline_export.item_record_formatter import (
    SyteLineItemRecord,
    format_syteline_item_record,
)


def test_standard_item_record_formats_status_price_and_fixed_fields():
    line = format_syteline_item_record(SyteLineItemRecord(
        long_item="ITEM-001", is_superproduct=False, description="Seat > Back",
        status=1, base_price="12.50", list_price="18", product_code="CHAIR",
        price_code="GBP", volume_litres=2.5, weight_kilos=3,
        commodity_code="9401", notes="ABCX-",
        feature_codes=("RED", "FAB-BLUE"), height=10, width=20, depth=30,
    ))
    fields = line.rstrip("\r\n").split("\t")
    assert fields[0:6] == ["ITEM-001", "no", "Seat   Back", "A", "", "12.5"]
    assert fields[9] == "CHAIR"
    assert fields[10:12] == ["2.5", "3"]
    assert fields[-4:] == ["10", "20", "30", ""]
    assert line.endswith("\r\n")


def test_inactive_status_and_list_price_selection_are_source_defined():
    line = format_syteline_item_record(SyteLineItemRecord(
        long_item="OLD", is_superproduct=True, description="Old item",
        status=2, base_price=9, list_price=11, export_base_prices=False,
        product_code="PC", commodity_code="C", notes="",
    ))
    fields = line.rstrip("\r\n").split("\t")
    assert fields[1] == "yes"
    assert fields[3:5] == ["O", "OBS"]
    assert fields[5] == "11"
    assert fields[20] == "SUP"


def test_negative_prices_are_clamped_and_marker_is_selected_from_notes_then_legacy():
    line = format_syteline_item_record(SyteLineItemRecord(
        long_item="X", is_superproduct=False, description="desc",
        status=3, base_price=-5, product_code="P", notes="NO-X-",
        legacy_item="LEGACYX",
    ))
    fields = line.rstrip("\r\n").split("\t")
    assert fields[5] == "0"
    assert fields[4] == "ON HOLD"
    assert fields[28] == "NO-X"
    assert fields[32] == "BOC"
