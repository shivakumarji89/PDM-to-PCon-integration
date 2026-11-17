"""Contracts for the bounded parallel pricing batch coordinator."""
from __future__ import annotations

from threading import Barrier, Lock
from types import SimpleNamespace

from models.snapshot import Snapshot
from repositories.pdm_repository import PDMRepository
from services.pricing_service import PriceParams, PricingService


def test_streaming_prices_batches_on_two_connections_and_keeps_item_order(monkeypatch):
    barrier = Barrier(2)
    lock = Lock()
    connections = []
    base_connections = []
    increment_connections = []

    class Connection:
        def __init__(self, number):
            self.number = number
            self.closed = False

        def close(self):
            self.closed = True

    def get_connection(self):
        with lock:
            connection = Connection(len(connections))
            connections.append(connection)
            return connection

    def fetch_base(self, items, currency, mydate, connection=None, site_id=1):
        with lock:
            base_connections.append(connection)
        # Both one-item batches must reach the database together. This fails
        # quickly if the coordinator accidentally falls back to serial work.
        barrier.wait(timeout=5)
        return [SimpleNamespace(Item=item, price=10.0) for item in items]

    def fetch_article(
        self, items, currency, mydate, site_id, connection=None, program_code=""
    ):
        with lock:
            increment_connections.append(connection)
        return []

    monkeypatch.setattr(PDMRepository, "get_connection", get_connection)
    monkeypatch.setattr(PDMRepository, "fetch_item_base_prices", fetch_base)
    monkeypatch.setattr(
        PDMRepository, "fetch_article_option_increment_prices", fetch_article
    )
    monkeypatch.setattr(
        PricingService, "target_currencies", lambda self, snapshot, params: ["EUR"]
    )
    monkeypatch.setattr(PricingService, "_attach_product_codes", lambda *args: None)

    snapshot = Snapshot()
    snapshot.articles = [
        SimpleNamespace(id="1", code="AA.01", product_id="10"),
        SimpleNamespace(id="2", code="BB.02", product_id="20"),
    ]
    streamed = []

    result = PricingService(None).compute_streaming(
        PriceParams(mydate="16-Oct-2026", site_id=1),
        snapshot,
        on_batch=streamed.extend,
        batch_size=1,
    )

    assert [record.article_code for record in result.records] == ["AA.", "BB."]
    assert streamed == result.records
    assert len(base_connections) == 2
    assert base_connections[0] is not base_connections[1]
    assert set(increment_connections) == set(base_connections)
    assert all(connection.closed for connection in connections)
