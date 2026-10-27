from __future__ import annotations

from types import SimpleNamespace

from scripts.pdm_differential import differential


class _Cursor:
    def execute(self, *_args):
        return self

    def fetchone(self):
        return None


class _Connection:
    def cursor(self):
        return _Cursor()

    def close(self):
        pass


class _Repository:
    def __init__(self, _ctx):
        self.calls = []
        self.connection = _Connection()
        self.last_instance = self

    def get_connection(self):
        return self.connection

    def fetch_item_base_prices(self, items, currency, mydate, connection, site_id=1):
        self.calls.append(("base", list(items), site_id))
        return []

    def fetch_article_option_increment_prices(
        self, items, currency, mydate, site_id, connection, program_code=""
    ):
        self.calls.append(("article_increments", list(items), site_id, program_code))
        return []

    def fetch_global_option_increment_prices(
        self, items, currency, mydate, site_id, connection, *, catalogue_id, program_code=""
    ):
        self.calls.append(("global_increments", list(items), site_id, catalogue_id, program_code))
        return []


def test_global_super_products_use_legacy_global_query(monkeypatch):
    repo_instances = []

    def make_repo(ctx):
        value = _Repository(ctx)
        repo_instances.append(value)
        return value

    captured = {}

    def build_records(base, increments, super_codes, prefixes, params):
        captured["base"] = base
        captured["increments"] = increments
        captured["super_codes"] = super_codes
        captured["params"] = params
        return [], []

    monkeypatch.setattr(differential, "PDMRepository", make_repo)
    monkeypatch.setattr(differential.PricingService, "build_records", build_records)
    monkeypatch.setattr(differential.PricingService, "_attach_product_codes", lambda *_args: None)

    records, unresolved = differential.pricing_records(
        object(),
        ["ARTICLE.01", "SUPER.PRODUCT"],
        "GBP",
        {"SUPER.PRODUCT"},
        prefix_from_notes=False,
        catalogue_id=660,
        program_code="layout_studio",
    )

    assert records == []
    assert unresolved == []
    assert repo_instances[0].calls == [
        ("base", ["ARTICLE.01", "SUPER.PRODUCT"], 1),
        ("article_increments", ["ARTICLE.01"], 1, "layout_studio"),
        ("global_increments", ["SUPER.PRODUCT"], 1, 660, "layout_studio"),
    ]
    assert captured["super_codes"] == {"SUPER.PRODUCT"}
    assert captured["params"].catalogue_id == 660
    assert captured["params"].program_code == "layout_studio"


def test_article_only_scenario_does_not_call_global_query(monkeypatch):
    repo_instances = []

    def make_repo(ctx):
        value = _Repository(ctx)
        repo_instances.append(value)
        return value

    monkeypatch.setattr(differential, "PDMRepository", make_repo)
    monkeypatch.setattr(differential.PricingService, "build_records", lambda *_args: ([], []))
    monkeypatch.setattr(differential.PricingService, "_attach_product_codes", lambda *_args: None)

    differential.pricing_records(
        object(), ["ARTICLE.01"], "GBP", set(), prefix_from_notes=False
    )

    assert repo_instances[0].calls == [
        ("base", ["ARTICLE.01"], 1),
        ("article_increments", ["ARTICLE.01"], 1, "layout_studio"),
    ]
