from models.article import Article
from models.price_list import PriceList
from models.price_record import PriceRecord
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.pdm_mdb_parity_service import (
    PdmMdbParityService,
    ParityReport,
)


def _snapshot() -> Snapshot:
    snapshot = Snapshot()
    prop = Property(id="p1", code="COLOR", name="Color", data_type="C")
    value = PropertyValue(
        id="v1", property_id="p1", code="BLK", value="Black"
    )
    prop.values.append(value)
    snapshot.properties = [prop]
    snapshot.property_values = [value]
    snapshot.articles = [Article(id="a1", code="A100", name="Chair")]
    snapshot.price_lists = [
        PriceList(
            id="EURO_2027",
            label="EURO_2027",
            currency="EUR",
            date_from="20270101",
            date_to="99991231",
        )
    ]
    return snapshot


def test_compare_domain_classifies_all_difference_types():
    report = ParityReport()
    PdmMdbParityService._compare_domain(
        report,
        "Test",
        {"same": "x", "missing": "x", "changed": "old"},
        {"same": "x", "extra": "x", "changed": "new"},
    )

    assert report.match_count == 1
    assert report.missing_count == 1
    assert report.extra_count == 1
    assert report.different_count == 1



def test_price_parity_resolves_mdb_surrogate_price_list_id_to_business_identity():
    snapshot = _snapshot()
    snapshot.price_records = [
        PriceRecord(
            article_code="A100",
            level="B",
            value=125.0,
            currency="EUR",
            valid_from="20270101",
            valid_to="99991231",
        )
    ]

    class Data:
        def rows(self, table):
            return {
                "tCOMd_Price": [
                    {
                        "com_PriceListID": 77,
                        "com_ArticleID": 456,
                        "com_VariantCondition": "",
                        "com_PriceLevelCode": "B",
                        "com_PriceValue": 125.0,
                        "sys_ISOCurrencyCode": "EUR",
                    }
                ],
                "tCOMd_GlobalPrice": [],
            }.get(table, [])

    mdb_snapshot = _snapshot()
    mdb_snapshot.price_records = list(snapshot.price_records)
    mdb_snapshot.price_lists = [
        PriceList(
            id="77",
            label="EURO_2027",
            currency="EUR",
            date_from="20270101",
            date_to="99991231",
        )
    ]

    expected = PdmMdbParityService._prices(snapshot)
    actual = PdmMdbParityService._mdb_prices(Data(), mdb_snapshot)

    assert expected == actual
    assert all("77" not in key for key in actual)
    assert any("euro_2027" in key for key in actual)


def test_normalizers_ignore_source_ids():
    left = _snapshot()
    right = _snapshot()
    right.articles[0].id = "mdb:article:500"

    assert PdmMdbParityService._articles(left) == PdmMdbParityService._articles(right)
    assert PdmMdbParityService._price_lists(left) == PdmMdbParityService._price_lists(right)
