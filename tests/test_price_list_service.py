from models.price_list import PriceList
from models.snapshot import Snapshot
from services.price_list_service import PriceListService


def _service():
    return object.__new__(PriceListService)


def test_midyear_price_list_uses_only_suffix_2():
    snapshot = Snapshot(price_lists=[
        PriceList(
            id="EURO_2027", label="EURO 2027", currency="EUR",
            date_from="20270101", date_to="99991231",
        )
    ])

    proposal = _service().propose(
        snapshot, ["EUR"], "20270701", mode="maintenance"
    )[0]

    assert proposal.list_id == "EURO_2027_2"
    assert proposal.previous_id == "EURO_2027"
    assert proposal.previous_date_to == "20270630"
    assert not proposal.conflict


def test_midyear_price_list_conflicts_if_suffix_2_already_exists():
    snapshot = Snapshot(price_lists=[
        PriceList(id="EURO_2027", label="EURO 2027", currency="EUR",
                  date_from="20270101", date_to="20270630"),
        PriceList(id="EURO_2027_2", label="EURO 2027 2", currency="EUR",
                  date_from="20270701", date_to="99991231"),
    ])

    proposal = _service().propose(
        snapshot, ["EUR"], "20271001", mode="maintenance"
    )[0]

    assert proposal.list_id == "EURO_2027_2"
    assert "already exists" in proposal.conflict


def test_existing_price_list_metadata_can_be_edited_without_removal():
    original = PriceList(
        id="EURO_2027", label="EURO 2027", currency="EUR",
        date_from="20270101", date_to="99991231",
    )
    snapshot = Snapshot(price_lists=[original])

    result = _service().update_existing_lists(snapshot, [{
        "original_id": "EURO_2027",
        "id": "EURO_2027_2",
        "label": "EURO 2027 2",
        "currency": "EUR",
        "date_from": "20270701",
        "date_to": "99991231",
    }])

    assert result is True
    assert len(snapshot.price_lists) == 1
    assert original.id == "EURO_2027_2"
    assert original.date_from == "20270701"
    assert original.date_to == "99991231"


def test_existing_price_list_edit_rejects_invalid_dates():
    snapshot = Snapshot(price_lists=[
        PriceList(id="GBP_2027", label="GBP 2027", currency="GBP",
                  date_from="20270101", date_to="99991231")
    ])

    assert not _service().update_existing_lists(snapshot, [{
        "original_id": "GBP_2027",
        "id": "GBP_2027",
        "label": "GBP 2027",
        "currency": "GBP",
        "date_from": "20270230",
        "date_to": "99991231",
    }])
