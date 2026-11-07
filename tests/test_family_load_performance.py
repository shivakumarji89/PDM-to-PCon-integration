"""Large-family loading: product-scoped link fetches, batching and equivalence.

The family load used to look articles up by ItemId lists (one query per 500
ids, per table). It now selects the per-article links by owning ProductId. These
tests pin the contract: the same articles, links, components and prefix lengths
come back, in far fewer queries, and cancellation / errors / fallbacks behave
exactly as before. A 6,474-article dataset stands in for the Ratio Desks family.
"""
import time
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from core.cancellation import (
    CancellationToken, OperationCancelled, cancellation_scope, checkpoint,
)
from core.errors import PDMQueryError
from core.snapshot_manager import SnapshotManager
from models.product import Product
from repositories.pdm_repository import PDMRepository
from services.engineering.engineering_reduction_service import (
    EngineeringReductionService,
)
from services.pdm_service import PDMService

LARGE_ARTICLES = 6474


class FakeFamilyRepo:
    """In-memory PDM exposing both the item-id and the product-scoped reads."""

    def __init__(self, products: int, per_product: int, *, links_per_item: int = 3,
                 components_per_item: int = 2, range_name: str = "Desks"):
        self.calls: list[str] = []
        self._products = [str(1000 + i) for i in range(products)]
        self._range = range_name
        self.items = []
        for p, pid in enumerate(self._products):
            for n in range(per_product):
                iid = str(p * 100000 + n + 1)
                self.items.append(NS(
                    ProductId=pid, ItemId=iid, Item=f"R{p:03d}.{n:04d}", Status=1,
                    IsSuperItem=False, Notes="6,x" if n % 2 else "", WeightKilos=None,
                    VolumeLitres=None, Height=None, Width=None, Depth=None,
                    Description=f"Item {iid}",
                ))
        self.by_product = {}
        for it in self.items:
            self.by_product.setdefault(it.ProductId, []).append(it)
        self.links = [
            NS(ItemId=it.ItemId, AttributeValueId=f"v{k}", Code="C", ModelSuffix="",
               DisplayOrder=k, DisplayOrdinal=k, AttrName=f"Attr{k}",
               HasDependentOptions=0)
            for it in self.items for k in range(links_per_item)
        ]
        # a duplicate relationship row: indexes must keep it unique
        if self.links:
            self.links.append(self.links[0])
        self.components = [
            NS(ParentItemId=it.ItemId, SubItem=f"SUB{k}", Quantity=1,
               ComponentSequence=str(k))
            for it in self.items for k in range(components_per_item)
        ]
        self.prefix = [
            NS(ItemId=it.ItemId, Item=it.Item, Notes=it.Notes, ProductCategoryId=7)
            for it in self.items
        ]

    # -- helpers -----------------------------------------------------------
    def _select(self, rows, key, ids):
        wanted = {str(i) for i in ids}
        return [r for r in rows if str(getattr(r, key)) in wanted]

    def _items_of(self, product_ids):
        wanted = {str(p) for p in product_ids}
        return {i.ItemId for i in self.items if i.ProductId in wanted}

    # -- shared reads ------------------------------------------------------
    def get_connection(self):
        return NS(close=lambda: None)

    def fetch_products_items(self, ids, connection=None):
        self.calls.append("items")
        return [i for p in ids for i in self.by_product.get(str(p), [])]

    def fetch_products_info(self, ids, connection=None):
        self.calls.append("info")
        return [
            NS(ProductId=p, ProductName=f"P{p}", ProductCode=f"C{p}", Status=1,
               NewProduct=0, IsSuperProduct=0, RangeName=self._range)
            for p in ids
        ]

    def fetch_products_attributes(self, ids, connection=None):
        return []

    def fetch_products_options(self, ids, catalogue_by_product=None, connection=None):
        return []

    def fetch_products_option_dependencies(self, ids, connection=None):
        return []

    def fetch_category_master_notes(self, ids, connection=None):
        return []

    def fetch_item_head_attribute_names(self, codes, connection=None):
        return []

    def fetch_item_option_increments(self, prefixes, connection=None):
        return []

    # -- item-id reads (legacy path) --------------------------------------
    def fetch_item_attribute_values(self, ids, connection=None):
        self.calls.append("links_by_item")
        return self._select(self.links, "ItemId", ids)

    def fetch_item_components(self, ids, connection=None):
        self.calls.append("components_by_item")
        return self._select(self.components, "ParentItemId", ids)

    def fetch_article_prefix_lengths(self, ids, connection=None):
        self.calls.append("prefix_by_item")
        return self._select(self.prefix, "ItemId", ids)

    # -- product-scoped reads (new path) ----------------------------------
    def fetch_products_item_attribute_values(self, pids, connection=None):
        self.calls.append("links_by_product")
        return self._select(self.links, "ItemId", self._items_of(pids))

    def fetch_products_item_components(self, pids, connection=None):
        self.calls.append("components_by_product")
        return self._select(self.components, "ParentItemId", self._items_of(pids))

    def fetch_products_article_prefix_lengths(self, pids, connection=None):
        self.calls.append("prefix_by_product")
        return self._select(self.prefix, "ItemId", self._items_of(pids))


def make_service(repo):
    context = NS(
        config=NS(pdm_server="srv", pdm_database="db"),
        snapshot_manager=SnapshotManager(),
        set_product_registry=Mock(),
        engineering_reduction_service=NS(materialize_article_sets=lambda s: []),
        engineering_class_service=NS(commit_config_codes=lambda s: None),
    )
    service = PDMService(context)
    service._repository = repo
    service.save_family_snapshot = Mock()
    return service


def products_of(repo):
    return [Product(id=pid, code=f"C{pid}") for pid in repo._products]


def snapshot_view(snapshot):
    return (
        [(a.id, a.code, a.product_id) for a in snapshot.articles],
        snapshot.article_property_value_ids,
        snapshot.article_varcond_terms,
        snapshot.article_components,
        snapshot.article_prefix_length,
        snapshot.product_range,
    )


# -- small / large family ---------------------------------------------------
def test_small_family_loads_every_article_and_link():
    repo = FakeFamilyRepo(products=3, per_product=4)
    result = make_service(repo).load_family(products_of(repo), "Small")
    assert result.ok, result.message
    snap = result.snapshot
    assert len(snap.articles) == 12
    assert all(len(v) == 3 for v in snap.article_property_value_ids.values())
    assert all(len(v) == 2 for v in snap.article_components.values())
    assert set(snap.article_prefix_length) == {a.id for a in snap.articles}


def test_large_family_uses_product_scoped_fetches_only():
    repo = FakeFamilyRepo(products=162, per_product=40)        # 6,480 ~ 6,474
    assert len(repo.items) >= LARGE_ARTICLES
    result = make_service(repo).load_family(products_of(repo), "Large")
    assert result.ok, result.message
    assert len(result.snapshot.articles) == len(repo.items)
    # one product-scoped query per table; the per-500-ItemId paths are unused
    assert repo.calls.count("links_by_product") == 1
    assert repo.calls.count("components_by_product") == 1
    assert repo.calls.count("prefix_by_product") == 1
    assert not {"links_by_item", "components_by_item", "prefix_by_item"} & set(repo.calls)


def test_article_link_completeness_and_duplicates_collapse():
    repo = FakeFamilyRepo(products=2, per_product=3)
    snap = make_service(repo).load_family(products_of(repo), "Dup").snapshot
    first = repo.items[0].ItemId
    assert snap.article_property_value_ids[first] == ["v0", "v1", "v2"]   # not v0 twice
    assert sum(len(v) for v in snap.article_property_value_ids.values()) == 6 * 3
    assert len(snap.article_components) == 6


def test_articles_map_to_their_own_family_products():
    repo = FakeFamilyRepo(products=4, per_product=5)
    snap = make_service(repo).load_family(products_of(repo), "Rel").snapshot
    expected = {i.ItemId: i.ProductId for i in repo.items}
    assert {a.id: str(a.product_id) for a in snap.articles} == expected


def test_scoped_result_equals_item_id_lookup():
    scoped_repo = FakeFamilyRepo(products=5, per_product=7)
    legacy_repo = FakeFamilyRepo(products=5, per_product=7)
    legacy_repo.fetch_products_item_attribute_values = None   # force legacy path
    scoped = make_service(scoped_repo).load_family(products_of(scoped_repo), "A")
    # a snapshot article from a foreign product disables the scoped path
    service = make_service(legacy_repo)
    first = service.load_family_articles(products_of(legacy_repo), "A")
    first.snapshot.articles[0].product_id = "foreign"
    legacy = service.load_family_details(
        first.snapshot, products_of(legacy_repo), "A"
    )
    assert snapshot_view(scoped.snapshot)[1:5] == snapshot_view(legacy.snapshot)[1:5]
    assert "links_by_item" in legacy_repo.calls


def test_rows_outside_the_article_set_are_filtered():
    repo = FakeFamilyRepo(products=2, per_product=3)
    service = make_service(repo)
    first = service.load_family_articles(products_of(repo), "F")
    kept = first.snapshot.articles[:-1]                      # drop one article
    first.snapshot.articles = kept
    snap = service.load_family_details(
        first.snapshot, products_of(repo), "F"
    ).snapshot
    dropped = repo.items[-1].ItemId
    assert dropped not in snap.article_property_value_ids
    assert dropped not in snap.article_components
    assert dropped not in snap.article_prefix_length


# -- repeated selection / snapshot consistency -------------------------------
def test_repeated_family_selection_is_deterministic():
    repo = FakeFamilyRepo(products=6, per_product=10)
    service = make_service(repo)
    one = service.load_family(products_of(repo), "Rep").snapshot
    two = service.load_family(products_of(repo), "Rep").snapshot
    assert one is not two
    assert snapshot_view(one) == snapshot_view(two)


def test_details_phase_does_not_mutate_phase1_articles():
    repo = FakeFamilyRepo(products=2, per_product=5)
    service = make_service(repo)
    phase1 = service.load_family_articles(products_of(repo), "S")
    before = [(a.id, a.code, a.product_id) for a in phase1.snapshot.articles]
    service.load_family_details(phase1.snapshot, products_of(repo), "S")
    assert [(a.id, a.code, a.product_id) for a in phase1.snapshot.articles] == before


# -- product range reuse -----------------------------------------------------
def test_details_phase_reuses_phase1_range_names():
    repo = FakeFamilyRepo(products=3, per_product=2)
    service = make_service(repo)
    products = products_of(repo)
    snap = service.load_family(products, "R").snapshot
    assert repo.calls.count("info") == 1                     # not re-queried
    assert set(snap.product_range.values()) == {"Desks"}


def test_details_phase_queries_only_products_missing_a_range():
    repo = FakeFamilyRepo(products=3, per_product=2)
    service = make_service(repo)
    products = products_of(repo)
    phase1 = service.load_family_articles(products, "R")
    products[1].range_name = ""
    asked: list = []
    orig = repo.fetch_products_info
    repo.fetch_products_info = lambda ids, connection=None: (
        asked.extend(ids) or orig(ids, connection=connection)
    )
    snap = service.load_family_details(phase1.snapshot, products, "R").snapshot
    assert asked == [products[1].id]
    assert snap.product_range[str(products[1].id)] == "Desks"


# -- cancellation and errors -------------------------------------------------
def test_cancellation_during_link_fetch_aborts_without_saving():
    repo = FakeFamilyRepo(products=3, per_product=4)
    service = make_service(repo)
    token = CancellationToken()
    orig = repo.fetch_products_item_components

    def cancelling(pids, connection=None):
        token.request_cancel()
        checkpoint()
        return orig(pids, connection=connection)

    repo.fetch_products_item_components = cancelling
    with cancellation_scope(token), pytest.raises(OperationCancelled):
        service.load_family(products_of(repo), "C")
    service.save_family_snapshot.assert_not_called()


def test_query_error_is_reported_not_raised():
    repo = FakeFamilyRepo(products=2, per_product=2)

    def boom(pids, connection=None):
        raise PDMQueryError("PDM query failed: timeout")

    repo.fetch_products_item_attribute_values = boom
    result = make_service(repo).load_family(products_of(repo), "E")
    assert not result.ok and "timeout" in result.message


# -- repository batching -----------------------------------------------------
class RecordingRepo(PDMRepository):
    def __init__(self):
        self.queries: list[tuple[str, int]] = []

    def _execute(self, query, params, connection=None):
        self.queries.append((query, len(params)))
        return []


def test_product_scoped_queries_batch_by_chunk():
    repo = RecordingRepo()
    ids = list(range(1, 631))                                # the 630-product family
    for method in (
        repo.fetch_products_item_attribute_values,
        repo.fetch_products_item_components,
        repo.fetch_products_article_prefix_lengths,
    ):
        repo.queries.clear()
        method(ids)
        assert len(repo.queries) == 2                        # 500 + 130, not 16
        assert "i.ProductId IN" in repo.queries[0][0] or "parent.ProductId IN" in repo.queries[0][0]
        assert max(n for _, n in repo.queries) <= PDMRepository._IN_CHUNK


def test_option_increment_prefixes_batch_at_chunk_size():
    repo = RecordingRepo()
    repo.fetch_item_option_increments([f"P{i}." for i in range(655)])
    assert [n for _, n in repo.queries] == [500, 155]        # was 14 queries of 50


# -- _set_attributes ---------------------------------------------------------
def _reference_set_attributes(article_ids, product_of, product_values, lookup, article_values):
    """The pre-optimisation algorithm (list-scan uniqueness)."""
    by_attribute, order = {}, []
    for article_id in article_ids:
        selected = [str(v) for v in article_values.get(article_id, [])]
        fallback = [str(v) for v in product_values.get(product_of.get(article_id, ""), [])]
        for value_id in selected if selected else fallback:
            info = lookup.get(str(value_id))
            if info is None:
                continue
            attribute_id, name, _v, _c = info
            if attribute_id not in by_attribute:
                by_attribute[attribute_id] = (name, {})
                order.append(attribute_id)
            carriers = by_attribute[attribute_id][1].setdefault(str(value_id), [])
            if article_id not in carriers:
                carriers.append(article_id)
    return [
        (aid, by_attribute[aid][0], [(v, list(c)) for v, c in by_attribute[aid][1].items()])
        for aid in order
    ]


def test_set_attributes_matches_reference_and_is_not_quadratic():
    n = LARGE_ARTICLES
    ids = [str(i) for i in range(n)]
    ids += ids[:50]                                          # repeated article ids
    lookup = {f"v{k}": (f"a{k % 3}", f"Attr{k % 3}", f"Val{k}", f"C{k}") for k in range(6)}
    article_values = {i: [f"v{int(i) % 2}", "v4", "v5"] for i in ids}   # v4/v5 on everyone
    product_of = {i: "p" for i in ids}
    started = time.perf_counter()
    got = EngineeringReductionService._set_attributes(
        ids, product_of, {"p": ["v0"]}, lookup, article_values
    )
    elapsed = time.perf_counter() - started
    flat = [(a.id, a.name, [(v.id, list(v.article_ids)) for v in a.values]) for a in got]
    assert flat == _reference_set_attributes(ids, product_of, {"p": ["v0"]}, lookup, article_values)
    assert elapsed < 2.0, f"_set_attributes took {elapsed:.2f}s for {n} articles"
