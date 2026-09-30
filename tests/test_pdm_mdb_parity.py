from models.article import Article
from models.price_list import PriceList
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


def test_normalizers_ignore_source_ids():
    left = _snapshot()
    right = _snapshot()
    right.articles[0].id = "mdb:article:500"

    assert PdmMdbParityService._articles(left) == PdmMdbParityService._articles(right)
    assert PdmMdbParityService._price_lists(left) == PdmMdbParityService._price_lists(right)
