"""A deterministic fake PDM for ``VarCondService.generate_live`` (no database, no network).

``install(monkeypatch)`` replaces ``repositories.pdm_repository.PDMRepository`` (``generate_live`` imports it
inside the function) with ``FakeLiveRepo``, which serves a small BOM: several parents that share component
prefixes, quantities above 1 (``$SET_PRICING_FACTOR`` rules), parametric attributes, option increments for some
prefixes and none for others. ``FakeLiveRepo.calls`` records every query so tests can count them.
"""
from __future__ import annotations

PARENTS = {
    # parent item -> (item id, notes, category id)
    "GESCRNNU.105508F": (1, "8", 10),
    "GESCRNNS.105508F": (2, "8", 10),
    "GESCRNPU.105508F": (3, "", 10),          # prefix length from the category master notes
    "RYTWKRNU.220110F": (4, "6", 11),
    "RYTWKRNS.220110F": (5, "6", 11),
    "RYTWKRPU.330220F": (6, "", 12),          # no master notes either: warning
}

COMPONENTS = {
    1: [("GESNNU.105508F", 1), ("GESNNS.105508F", 2), ("GESG.", 1)],
    2: [("GESNNS.105508F", 1), ("GESG.", 3), ("GEST.", 1)],
    3: [("GESNNU.105508F", 1), ("GESY.", 1)],
    4: [("RYT1.220110F", 1), ("GESG.", 1), ("RYT2.220110F", 2)],
    5: [("RYT1.220110F", 1), ("RYT2.220110F", 1)],
    6: [],                                    # a parent without a BOM: skipped
}

# component prefix (item up to and including the first dot) -> option increments
INCREMENTS = {
    "GESNNU.": [(8, "Fabric type"), (12, "Arm / pad finish"), (8, "Fabric type")],
    "GESNNS.": [(8, "Fabric type")],
    "RYT1.": [(5, "Worktop finish"), (7, "Edge band")],
    "GESG.": [],
    "GEST.": [],
    "GESY.": [(9, "base colour")],
    "RYT2.": [(5, "Worktop finish")],
}

MASTER_NOTES = {10: "8", 11: "6"}

ATTRIBUTES = {
    # parent -> [(display order, attribute name, order code or None, has dependent options)]
    "default": [
        (1, "Chair type", "C", 0),
        (2, "Overall width", None, 2),
        (3, "Arm pad", "AP", 0),
        (4, "fabric (front)", "F1", 0),
    ],
}


class _Row:
    def __init__(self, **values):
        self.__dict__.update(values)


class _Conn:
    def close(self):
        pass


class FakeLiveRepo:
    calls: list = []

    def __init__(self, context=None):
        self.context = context

    def get_connection(self):
        return _Conn()

    def _execute(self, sql, params=(), connection=None):
        FakeLiveRepo.calls.append(("sql", sql[:40], tuple(params)))
        if sql.startswith("SELECT i.ItemId, i.Item, i.Notes"):
            item = params[0]
            if item not in PARENTS:
                return []
            item_id, notes, category = PARENTS[item]
            return [_Row(ItemId=item_id, Item=item, Notes=notes, ProductCategoryId=category, Product="PROD")]
        if sql.startswith("SELECT DISTINCT Product.Product"):
            parent = params[1]
            return [
                _Row(prop=name, OrderCodeValue=(code if code is not None else f"{parent[8:10]}"), DisplayOrder=order)
                for order, name, code, _hdo in ATTRIBUTES["default"]
            ]
        raise AssertionError(f"unexpected query: {sql[:60]}")

    def fetch_item_components(self, item_ids, connection=None):
        FakeLiveRepo.calls.append(("components", tuple(item_ids)))
        rows = []
        for item_id in item_ids:
            rows += [_Row(SubItem=sub, Quantity=qty) for sub, qty in COMPONENTS.get(item_id, [])]
        return rows

    def fetch_category_master_notes(self, category_ids, connection=None):
        FakeLiveRepo.calls.append(("master", tuple(category_ids)))
        return [_Row(ProductCategoryId=c, Notes=MASTER_NOTES[c]) for c in category_ids if c in MASTER_NOTES]

    def fetch_item_option_increments(self, prefixes, connection=None):
        FakeLiveRepo.calls.append(("increments", tuple(prefixes)))
        rows = []
        for prefix in prefixes:
            rows += [_Row(OptionId=option_id, OptionName=name) for option_id, name in INCREMENTS.get(prefix, [])]
        return rows


def install(monkeypatch):
    import repositories.pdm_repository as module

    FakeLiveRepo.calls = []
    monkeypatch.setattr(module, "PDMRepository", FakeLiveRepo)
    return FakeLiveRepo


def increment_queries() -> int:
    return sum(1 for call in FakeLiveRepo.calls if call[0] == "increments")


def build_context():
    """An ApplicationContext whose snapshot matches the fake PDM: one article per parent, its BOM, and one
    engineering member per article (reduced to the first six characters) so XOCD base codes can be computed."""
    from core.application_context import ApplicationContext
    from models.article import Article
    from models.engineering import Engineering
    from models.engineering_family import EngineeringFamily
    from models.member_article import MemberArticle
    from models.product import Product
    from models.snapshot import Snapshot

    snapshot = Snapshot(id="varcond-fake")
    snapshot.metadata.source = "PDM"
    snapshot.product = Product(id="p1", code="GES", name="Ges", category="Seating", range_name="Ges")
    articles, components, members = [], {}, []
    for code, (item_id, _notes, _category) in PARENTS.items():
        article_id = str(item_id)
        articles.append(Article(id=article_id, product_id="p1", code=code, name=code))
        if COMPONENTS.get(item_id):
            components[article_id] = [
                {"sub_item": sub, "quantity": qty, "sequence": str(i + 1)}
                for i, (sub, qty) in enumerate(COMPONENTS[item_id])
            ]
        members.append(MemberArticle(id=f"m{item_id}", article_id=article_id, family_id="f1",
                                     reduced_article=code[:6]))
    snapshot.articles = articles
    snapshot.article_components = components
    snapshot.engineering = Engineering(families=[EngineeringFamily(id="f1", name="Fam", members=members)])
    context = ApplicationContext()
    context.register_pdm_snapshot(snapshot)
    context.activate_snapshot_source("pdm")
    return context


def relation_digest(relations) -> str:
    import hashlib
    import json

    blob = json.dumps(
        [[r.name, r.type_code, r.domain, r.order, r.body, list(r.article_codes)] for r in relations],
        sort_keys=True,
    )
    return hashlib.sha256(blob.encode()).hexdigest()
