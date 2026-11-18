"""Price Relation full-MDB export: naming, snapshot isolation, binding validation, overwrite safety.

* Generated price relations are ``P_<prefix>`` relation objects whose relation is ``PA_<prefix>`` -
  checked on the real ``tCOMd_RelObj`` / ``tCOMd_Relation`` / ``tCOMd_RelObjRel`` / ``tCOMd_Article`` rows
  ``OcdExportService`` builds, not on helper return values.
* The generated relations go onto the export's snapshot copy; B_/A_ relations are kept (or derived when the
  snapshot has none) and the live snapshot never changes.
* Missing, unknown, conflicting or unreachable article bindings block the export with a clear message.
* ``OcdExportService.export`` builds in a temporary file inside one transaction and replaces the destination
  only after the row counts check out; an existing destination needs ``overwrite=True``.
"""
from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace

import pytest

from models.product import Product
from models.relation_object import RelationObject
from models.snapshot import Snapshot
from services import ocd_export_service as ocd
from services.ocd_export_service import OcdExportService
from services.pricing_relation_service import (
    PriceRelationExportError,
    merge_generated_price_relations,
    prepare_price_relation_export,
    price_relation_names,
    validate_price_relation_bindings,
)

_PROTOS = {"tCOMd_RelObj": {}, "tCOMd_Relation": {}, "tCOMd_RelObjRel": {}}


def price_relation(prefix: str, codes, order: int = 100) -> RelationObject:
    """A relation exactly as ``VarCondGenerationPanel.build_relation_objects`` creates it."""
    object_name, relation_name = price_relation_names(prefix)
    return RelationObject(name=object_name, relation_name=relation_name, type_code="3", domain="P",
                          order=order, body=f"$VARCOND = '{prefix}'", article_codes=list(codes))


def config_relations() -> list[RelationObject]:
    return [RelationObject(name="B_Type_6", type_code="1", domain="C", body="$ BAN NOT IN ('X')"),
            RelationObject(name="A_Code_Arms", type_code="3", domain="C", body="CodeArms = 'N'")]


class _RelationService:
    """Derives the configuration relations only for a snapshot that has none (as the real one does)."""

    derived = 0

    def ensure_relation_objects(self, snapshot):
        if not snapshot.relation_objects:
            type(self).derived += 1
            snapshot.relation_objects = config_relations()
        return snapshot.relation_objects


def context(valid_codes=("AAA1", "AAA2", "BBB1")):
    return SimpleNamespace(
        engineering_relation_service=_RelationService(),
        xocd_export_service=SimpleNamespace(_base_codes=lambda snapshot, selected_article_ids=None: list(valid_codes)),
    )


def export_rows(relations):
    ctx = SimpleNamespace(engineering_relation_service=SimpleNamespace(
        ensure_relation_objects=lambda snapshot: snapshot.relation_objects))
    bindings: dict = {}
    obj, rel, link, _p, _v = OcdExportService(ctx)._relations(Snapshot(relation_objects=relations), 1, _PROTOS, bindings)
    return obj, rel, link, bindings


# --------------------------------------------------------------------------------------
# 1. naming on the exported rows
# --------------------------------------------------------------------------------------
def test_names_helper_matches_the_legacy_convention():
    assert price_relation_names("GESCRNNS") == ("P_GESCRNNS", "PA_GESCRNNS")


def test_exported_rows_carry_p_object_pa_relation_and_a_valid_link():
    generated = [price_relation("AAA", ["AAA1", "AAA2"], 100), price_relation("BBB", ["BBB1"], 101)]
    obj, rel, link, bindings = export_rows(config_relations() + generated)

    objects = {r["com_RelObjName"]: r["com_RelObjID"] for r in obj}
    relations = {r["com_RelationName"]: r["com_RelationID"] for r in rel}
    assert {"P_AAA", "P_BBB"} <= set(objects) and {"PA_AAA", "PA_BBB"} <= set(relations)
    assert not any(name.startswith(("PA_", "PAA_")) for name in objects)       # no object called PA_*
    assert not any(name.startswith("PAA_") for name in relations)               # the PAA_ defect is gone
    # config relations keep their conventional names
    assert {"B_Type_6", "A_Code_Arms"} <= set(objects) and {"BA_Type_6", "AA_Code_Arms"} <= set(relations)

    price_links = [(l["com_RelObjID"], l["com_RelationID"], l["com_RelObjTypeCode"],
                    l["com_RelObjDomainCode"], l["com_RelationOrder"]) for l in link
                   if l["com_RelObjDomainCode"] == "P"]
    assert sorted(price_links) == sorted([
        (objects["P_AAA"], relations["PA_AAA"], "3", "P", 100),
        (objects["P_BBB"], relations["PA_BBB"], "3", "P", 101),
    ])
    # every link points at an existing object and relation, and ids are unique
    assert {l["com_RelObjID"] for l in link} <= set(objects.values())
    assert {l["com_RelationID"] for l in link} <= set(relations.values())
    assert len(set(objects.values())) == len(objects) and len(set(relations.values())) == len(relations)


def test_article_com_relobjid_points_at_the_p_object_of_its_prefix():
    generated = [price_relation("AAA", ["AAA1", "AAA2"]), price_relation("BBB", ["BBB1"], 101)]
    obj, _rel, _link, bindings = export_rows(config_relations() + generated)
    ids = {r["com_RelObjName"]: r["com_RelObjID"] for r in obj}

    rows, _ = OcdExportService(SimpleNamespace())._articles(
        ["AAA1", "AAA2", "BBB1", "CCC1"], 1, 1, {}, {}, {}, {}, bindings["article"])

    assert [(r["com_ArticleCode"], r["com_RelObjID"]) for r in rows] == [
        ("AAA1", ids["P_AAA"]), ("AAA2", ids["P_AAA"]), ("BBB1", ids["P_BBB"]), ("CCC1", None)]
    assert bindings["conflicts"] == []


# --------------------------------------------------------------------------------------
# replacement of generated price relations only
# --------------------------------------------------------------------------------------
def test_replacement_removes_only_superseded_price_actions():
    old_generated_style = RelationObject(name="PA_AAA", type_code="3", domain="P", body="old")
    same_name = RelationObject(name="P_AAA", type_code="3", domain="P", body="older")
    imported_other = RelationObject(name="P_PRICING_STOOL", relation_name="PA_PRICING_STOOL", type_code="3",
                                    domain="P", rel_obj_id="11935", relation_id="564131")
    imported_pa_named = RelationObject(name="PA_KEEP", type_code="3", domain="P", rel_obj_id="7", relation_id="8")
    table_constraint = RelationObject(name="PA_LOOKALIKE", type_code="4", domain="C")
    price_precondition = RelationObject(name="PA_PRECOND", type_code="1", domain="P")
    existing = config_relations() + [old_generated_style, same_name, imported_other, imported_pa_named,
                                     table_constraint, price_precondition]
    generated = [price_relation("AAA", ["AAA1"])]

    merged = merge_generated_price_relations(existing, generated)

    assert [r.name for r in merged] == ["B_Type_6", "A_Code_Arms", "P_PRICING_STOOL", "PA_KEEP",
                                        "PA_LOOKALIKE", "PA_PRECOND", "P_AAA"]
    assert merged[-1] is generated[0]
    assert len(existing) == 8                                   # the input list is not modified


# --------------------------------------------------------------------------------------
# 2. snapshot isolation and B_/A_ preservation
# --------------------------------------------------------------------------------------
def _snapshot(relations):
    return Snapshot(product=Product(id="p", code="P", name="P"), relation_objects=list(relations))


def test_populated_snapshot_keeps_its_relations_and_gets_the_generated_ones_once():
    live = _snapshot(config_relations() + [RelationObject(name="PA_AAA", type_code="3", domain="P", body="old")])
    before = copy.deepcopy(live.relation_objects)
    export = copy.deepcopy(live)
    generated = [price_relation("AAA", ["AAA1", "AAA2"]), price_relation("BBB", ["BBB1"], 101)]
    _RelationService.derived = 0

    prepare_price_relation_export(context(), export, generated)

    assert [r.name for r in export.relation_objects] == ["B_Type_6", "A_Code_Arms", "P_AAA", "P_BBB"]
    assert _RelationService.derived == 0                         # existing relations were not re-derived
    assert live.relation_objects == before                       # live snapshot untouched
    assert len({r.name for r in export.relation_objects}) == len(export.relation_objects)


def test_empty_snapshot_gets_the_config_relations_derived_before_export():
    live = _snapshot([])
    export = copy.deepcopy(live)
    _RelationService.derived = 0

    prepare_price_relation_export(context(), export, [price_relation("AAA", ["AAA1"])])

    assert [r.name for r in export.relation_objects] == ["B_Type_6", "A_Code_Arms", "P_AAA"]
    assert _RelationService.derived == 1
    assert live.relation_objects == []                           # nothing leaked into the live snapshot


def test_snapshot_holding_only_old_generated_relations_still_gets_config_relations():
    export = _snapshot([RelationObject(name="PA_AAA", type_code="3", domain="P", body="old")])

    prepare_price_relation_export(context(), export, [price_relation("AAA", ["AAA1"])])

    assert [r.name for r in export.relation_objects] == ["B_Type_6", "A_Code_Arms", "P_AAA"]


def test_exported_rows_of_an_empty_snapshot_contain_config_and_price_relations():
    export = _snapshot([])
    prepare_price_relation_export(context(), export, [price_relation("AAA", ["AAA1"])])

    obj, rel, link, bindings = export_rows(export.relation_objects)

    assert sorted(r["com_RelObjName"] for r in obj) == ["A_Code_Arms", "B_Type_6", "P_AAA"]
    assert sorted(r["com_RelationName"] for r in rel) == ["AA_Code_Arms", "BA_Type_6", "PA_AAA"]
    assert bindings["article"] != {}


# --------------------------------------------------------------------------------------
# 3. binding validation
# --------------------------------------------------------------------------------------
def test_valid_distinct_groups_pass():
    generated = [price_relation("AAA", ["AAA1", "AAA2"]), price_relation("BBB", ["BBB1"], 101)]
    validate_price_relation_bindings(generated, config_relations() + generated, {"AAA1", "AAA2", "BBB1"})


def test_empty_article_group_is_rejected_with_the_prefix():
    generated = [price_relation("AAA", ["AAA1"]), price_relation("BBB", [])]
    with pytest.raises(PriceRelationExportError, match=r"PA_BBB: no articles to bind"):
        validate_price_relation_bindings(generated, generated, {"AAA1"})


def test_blank_article_codes_count_as_empty():
    generated = [price_relation("AAA", ["", "  "])]
    with pytest.raises(PriceRelationExportError, match="PA_AAA: no articles"):
        validate_price_relation_bindings(generated, generated)


def test_articles_outside_the_export_are_rejected_not_ignored():
    generated = [price_relation("AAA", ["AAA1", "ZZZ9"])]
    with pytest.raises(PriceRelationExportError, match=r"PA_AAA: article\(s\) not in the export: ZZZ9"):
        validate_price_relation_bindings(generated, generated, {"AAA1"})


def test_one_article_in_two_generated_relations_is_a_conflict():
    generated = [price_relation("AAA", ["AAA1", "SHARED"]), price_relation("BBB", ["SHARED"], 101)]
    with pytest.raises(PriceRelationExportError, match=r"SHARED is bound to 2 different relation objects"):
        validate_price_relation_bindings(generated, generated, {"AAA1", "SHARED"})


def test_relation_whose_articles_all_belong_to_an_imported_object_is_unreachable():
    imported = RelationObject(name="P_PRICING_STOOL", relation_name="PA_PRICING_STOOL", type_code="3", domain="P",
                              rel_obj_id="11935", relation_id="564131", article_codes=["AAA1"])
    generated = [price_relation("AAA", ["AAA1"])]
    with pytest.raises(PriceRelationExportError, match="PA_AAA: every article is already bound"):
        validate_price_relation_bindings(generated, [imported] + generated, {"AAA1"})


def test_prepare_blocks_on_unknown_articles_through_the_real_base_codes():
    export = _snapshot(config_relations())
    with pytest.raises(PriceRelationExportError, match="not in the export"):
        prepare_price_relation_export(context(valid_codes=("AAA1",)), export, [price_relation("AAA", ["AAA1", "NOPE"])])


# --------------------------------------------------------------------------------------
# 4. overwrite protection, temporary file, transaction
# --------------------------------------------------------------------------------------
class FakeMdb:
    """Stands in for ``MdbService``: a "database" is a file holding text; records the batches."""

    def __init__(self, count_override=None, batch_ok=True):
        self.batches = []
        self.batch_ok = batch_ok
        self.count_override = count_override

    def is_available(self):
        return True

    def copy_template(self, template, dest):
        Path(dest).parent.mkdir(parents=True, exist_ok=True)      # as MdbService.copy_template does
        Path(dest).write_bytes(b"TEMPLATE")

    def read_table(self, mdb, sql):
        if "COUNT(*)" in sql:
            table = sql.split("[")[1].split("]")[0]
            n = self.count_override if self.count_override is not None else 2
            return [{"n": n}]
        if "tCOMd_Package" in sql and "reg_ManufacturerCode" not in sql:
            return [{"com_PackageID": 1, "com_ComGroupID": 1, "com_ManufacturerID": 1}]
        return []

    def execute_batch(self, mdb, ops, transaction=False):
        self.batches.append((Path(mdb), transaction, [o["op"] for o in ops]))
        if self.batch_ok:
            Path(mdb).write_bytes(b"NEW-EXPORT")
        return SimpleNamespace(ok=self.batch_ok, first_error=lambda: None if self.batch_ok else "disk full")


def service(monkeypatch, tmp_path, mdb):
    template = tmp_path / "template.mdb"
    template.write_bytes(b"TEMPLATE")
    monkeypatch.setattr(ocd, "_template_for_kind", lambda kind: template)
    ctx = SimpleNamespace(
        mdb_service=mdb,
        material_picking_service=SimpleNamespace(ensure_package_defaults=lambda s: None, DEFAULT_MAP="m"),
        mdb_export_session_service=None,
    )
    svc = OcdExportService(ctx)
    monkeypatch.setattr(svc, "_prototype", lambda mdb_path, table: {})
    monkeypatch.setattr(svc, "_price_list_rows", lambda snapshot, mdb_path: [])
    monkeypatch.setattr(svc, "_price_lists_by_currency", lambda mdb_path, snapshot=None: {})
    monkeypatch.setattr(svc, "_material_map_id", lambda *a, **k: None)
    monkeypatch.setattr(svc, "_build", lambda snapshot, *a, **k: (
        a[-2].table_counts.update({"tCOMd_Article": 2, "tCOMd_Price": 2}) or []))
    return svc


def full_snapshot():
    return Snapshot(product=Product(id="p", code="DSK", name="Desk", category="Desks", range_name="Desk"),
                    generation_template="knoll")


def leftovers(folder: Path):
    return sorted(p.name for p in folder.iterdir() if p.name.endswith(".tmp"))


def test_new_destination_is_written_through_a_temp_file_in_one_transaction(monkeypatch, tmp_path):
    mdb = FakeMdb()
    result = service(monkeypatch, tmp_path, mdb).export(full_snapshot(), tmp_path / "out", "knoll")

    final = tmp_path / "out" / "pcr_data_com_ocd.mdb"
    assert result.ok and not result.error and result.mdb_path == str(final)
    assert final.read_bytes() == b"NEW-EXPORT"
    assert leftovers(final.parent) == []
    [(written, transaction, ops)] = mdb.batches
    assert written != final and written.name.endswith(".tmp")      # never written in place
    assert transaction is True and ops[0] == "delete"


def test_existing_destination_without_confirmation_is_not_touched(monkeypatch, tmp_path):
    final = tmp_path / "pcr_data_com_ocd.mdb"
    final.write_bytes(b"PRECIOUS")
    mdb = FakeMdb()

    result = service(monkeypatch, tmp_path, mdb).export(full_snapshot(), tmp_path, "knoll")

    assert not result.ok and result.destination_exists and "already exists" in result.error
    assert final.read_bytes() == b"PRECIOUS" and mdb.batches == [] and leftovers(tmp_path) == []


def test_existing_destination_with_confirmation_is_replaced(monkeypatch, tmp_path):
    final = tmp_path / "pcr_data_com_ocd.mdb"
    final.write_bytes(b"PRECIOUS")

    result = service(monkeypatch, tmp_path, FakeMdb()).export(full_snapshot(), tmp_path, "knoll", overwrite=True)

    assert result.ok and final.read_bytes() == b"NEW-EXPORT" and leftovers(tmp_path) == []


def test_failed_write_leaves_the_previous_destination_intact(monkeypatch, tmp_path):
    final = tmp_path / "pcr_data_com_ocd.mdb"
    final.write_bytes(b"PRECIOUS")

    result = service(monkeypatch, tmp_path, FakeMdb(batch_ok=False)).export(
        full_snapshot(), tmp_path, "knoll", overwrite=True)

    assert not result.ok and result.error == "disk full"
    assert final.read_bytes() == b"PRECIOUS" and leftovers(tmp_path) == []


def test_failed_write_to_a_new_destination_leaves_no_file(monkeypatch, tmp_path):
    result = service(monkeypatch, tmp_path, FakeMdb(batch_ok=False)).export(full_snapshot(), tmp_path / "new", "knoll")

    assert not result.ok
    assert not (tmp_path / "new" / "pcr_data_com_ocd.mdb").exists() and leftovers(tmp_path / "new") == []


def test_row_count_mismatch_discards_the_export_and_keeps_the_old_file(monkeypatch, tmp_path):
    final = tmp_path / "pcr_data_com_ocd.mdb"
    final.write_bytes(b"PRECIOUS")

    result = service(monkeypatch, tmp_path, FakeMdb(count_override=1)).export(
        full_snapshot(), tmp_path, "knoll", overwrite=True)

    assert not result.ok and "Verification failed" in result.error and "expected 2" in result.error
    assert final.read_bytes() == b"PRECIOUS" and leftovers(tmp_path) == []


def test_replace_failure_keeps_the_old_file_and_cleans_up(monkeypatch, tmp_path):
    final = tmp_path / "pcr_data_com_ocd.mdb"
    final.write_bytes(b"PRECIOUS")
    monkeypatch.setattr(ocd.os, "replace", lambda src, dst: (_ for _ in ()).throw(PermissionError("in use")))

    result = service(monkeypatch, tmp_path, FakeMdb()).export(full_snapshot(), tmp_path, "knoll", overwrite=True)

    assert not result.ok and "left unchanged" in result.error
    assert final.read_bytes() == b"PRECIOUS" and leftovers(tmp_path) == []


def test_active_session_mdb_is_still_refused(monkeypatch, tmp_path):
    final = tmp_path / "pcr_data_com_ocd.mdb"
    final.write_bytes(b"SESSION")
    svc = service(monkeypatch, tmp_path, FakeMdb())
    svc.context.mdb_export_session_service = SimpleNamespace(session_for_mdb_path=lambda path: object())

    result = svc.export(full_snapshot(), tmp_path, "knoll", overwrite=True)

    assert not result.ok and "active ProductStudio export MDB" in result.error
    assert final.read_bytes() == b"SESSION"
