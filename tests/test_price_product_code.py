"""Product_Code plumbing that lets the exporter build PDM's price-text label."""
from types import SimpleNamespace

from models.price_record import PriceRecord
from repositories.pdm_repository import PDMRepository
from services.pricing_service import PricingService
from services.snapshot_serialization import price_record_from_dict, price_record_to_dict


class _Repo:
    def __init__(self, rows=None, fail=False):
        self.rows, self.fail, self.asked = rows or [], fail, None

    def fetch_item_product_codes(self, items, site_id, conn):
        self.asked = (list(items), site_id)
        if self.fail:
            raise RuntimeError("boom")
        return [SimpleNamespace(Item=i, Product_Code=c) for i, c in self.rows]


def _records():
    return [
        PriceRecord(is_global=True, variant_condition="GE2HBS.", value=1.0, currency="EUR"),
        PriceRecord(is_global=True, variant_condition="GE2HBS. 8=1FD", value=1.0, currency="EUR"),
        PriceRecord(article_code="A1", value=1.0, currency="EUR"),
    ]


def test_global_records_get_the_items_product_code_including_surcharges():
    repo, recs = _Repo([("GE2HBS.", "FR-AA-US")]), _records()
    PricingService._attach_product_codes(recs, repo, None, 3)
    assert [r.product_code for r in recs] == ["FR-AA-US", "FR-AA-US", ""]
    assert repo.asked == (["GE2HBS."], 3)       # one lookup per distinct item, article rows excluded


def test_revive_lookup_keeps_product_identity_separate_from_condition():
    record = PriceRecord(
        is_global=True, variant_condition="3848=RYMPSH.12SW_OKG",
        source_item="RYMPSH.12SW", pdm_lookup_code="3848=RYMPSH.12SW_OKG",
    )
    repo = _Repo([("RYMPSH.12SW", "RYM-PC")])
    PricingService._attach_product_codes([record], repo, None, 1)
    assert repo.asked == (["RYMPSH.12SW"], 1)
    assert record.product_code == "RYM-PC"


def test_lookup_failure_leaves_codes_empty_instead_of_failing_the_compute():
    recs = _records()
    PricingService._attach_product_codes(recs, _Repo(fail=True), None, 1)
    assert all(r.product_code == "" for r in recs)


def test_product_code_and_text_id_survive_snapshot_round_trip():
    rec = PriceRecord(is_global=True, variant_condition="X.1", product_code="P-1", text_id="88")
    back = price_record_from_dict(price_record_to_dict(rec))
    assert (back.product_code, back.text_id) == ("P-1", "88")
    assert price_record_from_dict({"variant_condition": "OLD"}).product_code == ""   # older snapshots


def test_repository_resolves_product_code_with_override_and_site():
    seen = {}
    repo = PDMRepository.__new__(PDMRepository)
    repo._execute = lambda q, params, connection=None: seen.update(q=q, p=params) or []
    repo.fetch_item_product_codes(["A.1", "B.2"], 4, None)
    assert "ProductCodeIdOverride" in seen["q"] and "pc.SiteId = ?" in seen["q"]
    assert seen["p"] == (4, "A.1", "B.2")
