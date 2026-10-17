"""PDM-versus-Pricing parity for global-price text blocks.

``_pdm_add_missing_global`` is a literal transcription of
``PriceMaintenance.AddMissingGlobalPricingRecords`` (PDM, lines 10161-10232) over
in-memory tables: the same lookups, the same ``text11`` / ``text12`` derivation,
the same INSERT column lists. The Pricing export is run on an equivalent MDB and
the resulting ``tCOMd_Text`` / ``tCOMd_GlobalPrice`` rows must match.
Not a live PDM run (that needs the PDM app + database); see
docs/03_Workflows/pricing_pdm_parity.md.
"""
from __future__ import annotations

from tests.test_price_mdb_export_service import (
    _OptimizedFake, _eur_gbp_lists, _export, _global, _texts_op, _global_op,
)

PACKAGE, LIST_ID, CURRENCY = 1, 21, "EUR"
LANG = ["com_Text_1_en", "com_Text_1_de", "com_Text_1_fr", "com_Text_1_nl"]


def _pdm_add_missing_global(texts, globals_, items):
    """Returns (texts, globals) after PDM's loop over ``items`` = [(variant, Product_Code)]."""
    texts, globals_ = [dict(t) for t in texts], [dict(g) for g in globals_]
    next_text = max([t["com_TextID"] for t in texts], default=0) + 1
    for text10, code in items:
        num7 = -1
        for g in globals_:  # SELECT com_TextID FROM tCOMd_GlobalPrice WHERE package/variant/list
            if g["com_PackageID"] == PACKAGE and g["com_VariantCondition"].lower() == text10.lower() \
                    and g["com_PriceListID"] == LIST_ID and g.get("com_TextID") is not None:
                num7 = g["com_TextID"]
        text11 = text10
        if (" " in text11) and ("=" in text11) and (text11.index(" ") < text11.index("=")):
            text11 = text11[text11.index(" ") + 1:]
            text11 = text11[:text11.index("=")]
            text11 = "Surcharge " + text11
        elif "_" not in text11:
            text11 = text11 + "  (" + code + ")"
        text12 = text11.replace("Surcharge ", "")
        if "  (" in text12:
            text12 = text12[:text12.index("  (")]
        if num7 == -1:
            for t in texts:  # SELECT com_TextID FROM tCOMd_Text WHERE com_PackageId AND com_TextName
                if t["com_PackageID"] == PACKAGE and t["com_TextName"].lower() == text12.lower():
                    num7 = t["com_TextID"]
            if num7 == -1:  # INSERT INTO tCOMd_Text (...)
                texts.append({"com_TextID": next_text, "com_PackageID": PACKAGE, "com_TextTypeCode": "price",
                              "com_TextName": text12, **{c: text11 for c in LANG}})
                num7, next_text = next_text, next_text + 1
            globals_.append({"com_PackageID": PACKAGE, "com_PriceListID": LIST_ID, "com_VariantCondition": text10,
                             "com_PriceTypeCode": "S", "com_PriceLevelCode": "X", "com_TextID": num7,
                             "sys_ISOCurrencyCode": CURRENCY})
    return texts, globals_


def _normal(texts, globals_, only_new_from=0):
    by_id = {t["com_TextID"]: t for t in texts}
    return (
        sorted((t["com_TextName"].lower(), t["com_TextTypeCode"], *(t[c] for c in LANG)) for t in texts),
        sorted((g["com_VariantCondition"], g["com_PriceListID"], g["com_PriceTypeCode"], g["com_PriceLevelCode"],
                g["sys_ISOCurrencyCode"], by_id[g["com_TextID"]]["com_TextName"].lower()) for g in globals_),
    )


def _apply_export(texts, items):
    mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22],
                         texts=[{"com_TextID": t["com_TextID"], "com_TextName": t["com_TextName"]} for t in texts])
    result = _export(mdb, [_global(vc, 10.0, CURRENCY, product_code=code) for vc, code in items])
    assert result["ok"] and result["verified"], result
    new_texts = [dict(r) for op in mdb.ops if op["op"] == "insert" and op["table"] == "tCOMd_Text" for r in op["rows"]]
    new_globals = [dict(r) for op in mdb.ops if op["op"] == "insert" and op["table"] == "tCOMd_GlobalPrice"
                   for r in op["rows"]]
    return [dict(t) for t in texts] + new_texts, new_globals, result


_BASE_TEXTS = [
    {"com_TextID": 77, "com_PackageID": PACKAGE, "com_TextTypeCode": "price", "com_TextName": "8",
     **{c: "Surcharge fabric" for c in LANG}},
    {"com_TextID": 88, "com_PackageID": PACKAGE, "com_TextTypeCode": "price", "com_TextName": "GE2HBS.",
     **{c: "GE2HBS.  (FR-AA-US)" for c in LANG}},
]
_ITEMS = [
    ("GE2HBS.", "FR-AA-US"),            # base item whose text exists  -> reused
    ("GESNNU.1 8=1FD", "FR-AA-US"),     # surcharge: shared option-id text "8" -> reused
    ("NEWITEM.1", "NW-AA-US"),          # base item, text missing      -> created "NEWITEM.1  (NW-AA-US)"
    ("NEWITEM.1 3344=AB", "NW-AA-US"),  # surcharge, option text missing -> created "Surcharge 3344"
    ("NEW_UNDERSCORE.2", "NW-AA-US"),   # underscore: label has no product code
    ("newitem.1 3344=CD", "NW-AA-US"),  # same option, other value, other case -> reuses 3344
]


def test_new_global_rows_and_texts_match_the_pdm_algorithm():
    pdm_texts, pdm_globals = _pdm_add_missing_global(_BASE_TEXTS, [], _ITEMS)
    our_texts, our_globals, result = _apply_export(_BASE_TEXTS, _ITEMS)
    ours = _normal(our_texts, our_globals)
    theirs = _normal(pdm_texts, pdm_globals)
    assert ours[0] == theirs[0]   # identical tCOMd_Text content: names, type, every language column
    assert ours[1] == theirs[1]   # identical new global rows: identity, level X, type S, text by name
    assert result["text_summary"]["text_create"] == 3
    assert result["text_summary"]["text_reuse"] == 2
    assert result["text_summary"]["text_link_new"] == 1


def test_every_new_row_text_id_resolves_to_exactly_one_existing_text():
    texts, globals_, _ = _apply_export(_BASE_TEXTS, _ITEMS)
    ids = [t["com_TextID"] for t in texts]
    assert len(ids) == len(set(ids))
    assert {g["com_TextID"] for g in globals_} <= set(ids)
    names = [t["com_TextName"].lower() for t in texts]
    assert len(names) == len(set(names))      # no duplicate text names introduced


def test_second_run_matches_pdm_second_run_and_adds_nothing():
    texts, globals_, _ = _apply_export(_BASE_TEXTS, _ITEMS)
    pdm_t, pdm_g = _pdm_add_missing_global(*_pdm_add_missing_global(_BASE_TEXTS, [], _ITEMS), _ITEMS)
    assert len(pdm_g) == len(_ITEMS) and len(pdm_t) == len(_BASE_TEXTS) + 3   # PDM is idempotent too
    existing = [{**g, "com_GlobalPriceID": 1000 + i} for i, g in enumerate(globals_)]
    mdb = _OptimizedFake(_eur_gbp_lists(), globals_=existing, linked=[21, 22],
                         texts=[{"com_TextID": t["com_TextID"], "com_TextName": t["com_TextName"]} for t in texts])
    result = _export(mdb, [_global(vc, 10.0, CURRENCY, product_code=c) for vc, c in _ITEMS])
    assert mdb.ops == [] and result["text_result"]["texts_created"] == 0


def test_documented_deviation_existing_text_labels_are_not_rewritten():
    """PDM re-UPDATEs the language columns of every non-surcharge text on each run
    (line 10233). The export preserves existing text content instead: a label that
    was translated by hand must survive a price update. No UPDATE of tCOMd_Text is planned."""
    existing_g = [{"com_GlobalPriceID": 5, "com_PackageID": PACKAGE, "com_PriceListID": LIST_ID,
                   "com_VariantCondition": "GE2HBS.", "com_PriceLevelCode": "X", "sys_ISOCurrencyCode": "EUR",
                   "com_PriceValue": 1.0, "com_TextID": 88}]
    mdb = _OptimizedFake(_eur_gbp_lists(), globals_=existing_g, linked=[21, 22],
                         texts=[{"com_TextID": 88, "com_TextName": "GE2HBS."}])
    _export(mdb, [_global("GE2HBS.", 9.0, CURRENCY, product_code="OTHER")])
    assert all(op["table"] != "tCOMd_Text" for op in mdb.ops)


def test_documented_deviation_only_price_type_texts_are_linked():
    """PDM's name lookup has no ``com_TextTypeCode`` filter and could link a global price
    to e.g. an ``artlong`` text that happens to share the item's name. The export reads
    ``price`` texts only, so such a name gets its own new price text."""
    mdb = _OptimizedFake(_eur_gbp_lists(), linked=[21, 22], texts=[])  # the artlong text is not offered
    _export(mdb, [_global("GEMTD", 9.0, CURRENCY, product_code="P")])
    assert _texts_op(mdb)["rows"][0]["com_TextTypeCode"] == "price"
    assert _global_op(mdb)["rows"][0]["com_TextID"] == _texts_op(mdb)["rows"][0]["com_TextID"]
