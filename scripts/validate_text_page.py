"""Validate the Text workflow step (Phase A).

Headless, PDM-free check that the EngineeringTextService derives text blocks
from a synthetic snapshot with the correct names/type codes, that edits persist,
that a rebuild re-derives, and that text blocks round-trip through JSON.

Run:  python scripts/validate_text_page.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.application_context import ApplicationContext
from models.article import Article
from models.engineering import Engineering
from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.option import Option
from models.option_value import OptionValue
from models.property import Property
from models.property_value import PropertyValue
from models.snapshot import Snapshot
from services.snapshot_serialization import snapshot_from_dict, snapshot_to_dict


def _make_snapshot() -> Snapshot:
    article = Article(id="A1", code="GEPBE", name="Back to Back extension",
                      description="B2B ext", product_id="P1")
    prop = Property(id="PR1", name="Top Material", values=[
        PropertyValue(id="V1", property_id="PR1", value="Melamine", code="M"),
        PropertyValue(id="V2", property_id="PR1", value="Veneer", code="W"),
        PropertyValue(id="V3", property_id="PR1", value="Uncoded", code=""),
    ])
    option = Option(id="OP1", name="Base Frame", code="BF", values=[
        OptionValue(id="OV1", option_id="OP1", value="Polished", code="P"),
        OptionValue(id="OV2", option_id="OP1", value="Black", code=""),
    ])
    member = MemberArticle(id="M1", article_id="A1", family_id="F1",
                           reduced_article="GEPBE",
                           short_description="Short S", long_description="Long L")
    family = EngineeringFamily(id="F1", members=[member])
    eng = Engineering(families=[family])
    return Snapshot(id="S1", articles=[article], properties=[prop],
                    options=[option], engineering=eng)


def main() -> None:
    context = ApplicationContext()
    service = context.engineering_text_service
    snapshot = _make_snapshot()

    blocks = service.ensure_text_blocks(snapshot)
    by_key = {(b.type_code, b.name): b for b in blocks}

    # Article short/long keyed by the base (reduced) code.
    assert ("artshort", "GEPBE") in by_key, "missing artshort GEPBE"
    assert ("artlong", "GEPBE") in by_key, "missing artlong GEPBE"
    assert by_key[("artshort", "GEPBE")].en == "Short S"
    assert by_key[("artlong", "GEPBE")].en == "Long L"

    # Property text block uses the underscore-joined name.
    assert ("property", "Top_Material") in by_key, "missing property Top_Material"
    assert by_key[("property", "Top_Material")].en == "Top Material"

    # EVERY coded value produces a propvalue keyed by <Property>_<code>.
    assert ("propvalue", "Top_Material_M") in by_key, "missing propvalue _M"
    assert ("propvalue", "Top_Material_W") in by_key, "missing propvalue _W"
    assert by_key[("propvalue", "Top_Material_M")].en == "Melamine"
    # A value with no code (and no resolved config code) has no propvalue.
    assert ("propvalue", "Top_Material_") not in by_key, "uncoded value leaked"

    # Options and their coded values are added, keyed by <Option>_<code>.
    assert ("option", "Base_Frame") in by_key, "missing option Base_Frame"
    assert ("optionvalue", "Base_Frame_P") in by_key, "missing optionvalue _P"
    assert ("optionvalue", "Base_Frame_") not in by_key, "uncoded option leaked"

    # ensure_text_blocks is idempotent (preserves the same list / edits).
    edited = by_key[("property", "Top_Material")]
    assert service.set_language(edited, "de", "Oberflaeche")
    assert service.ensure_text_blocks(snapshot) is blocks, "ensure re-derived"
    assert edited.de == "Oberflaeche", "edit lost"

    # JSON round-trip preserves the edit.
    restored = snapshot_from_dict(snapshot_to_dict(snapshot))
    r_by_key = {(b.type_code, b.name): b for b in restored.text_blocks}
    assert r_by_key[("property", "Top_Material")].de == "Oberflaeche", "round-trip lost edit"

    # Rebuild re-derives (discards edits).
    rebuilt = service.rebuild_text_blocks(snapshot)
    rb = {(b.type_code, b.name): b for b in rebuilt}
    assert rb[("property", "Top_Material")].de == "", "rebuild kept stale edit"

    # Fill-from-EN copies English into empty languages, never overwriting.
    block = rb[("property", "Top_Material")]
    assert service.is_untranslated(block), "fresh block should be untranslated"
    block.fr = "Existant"
    filled = service.fill_empty_from_en([block])
    assert filled == 2, filled  # de + nl filled, fr preserved
    assert block.de == "Top Material" and block.nl == "Top Material"
    assert block.fr == "Existant", "existing translation overwritten"
    assert not service.is_untranslated(block), "block should now be fully translated"

    print("validate_text_page: PASS")


if __name__ == "__main__":
    main()
