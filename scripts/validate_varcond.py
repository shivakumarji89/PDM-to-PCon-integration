"""Headless validation for the offline PDM-parity VARCOND generator.

Builds a synthetic super product (BOM + ordered attribute rows + article prefix
length) and checks the generated rules match PDM's ``VarCondThread`` shape,
including parametric dimension slicing from the article number, the property
name parser, and PDM's exclusion/substitution substring semantics. No database.

Run:  $env:PYTHONPATH="."; python scripts/validate_varcond.py
"""
from __future__ import annotations

from models.article import Article
from models.snapshot import Snapshot
from services.varcond_service import VarCondService


def _snapshot() -> Snapshot:
    snap = Snapshot()
    # Article number: DWE36 (prefix, 5 chars) + parametric codes "2S" + "4" ...
    #   positions: D1 W2 E3 3(4) 6(5) 2(6) S(7) 4(8) C(9) . 0 8 1 2
    snap.articles = [Article(id="sup1", code="DWE362S4C.0812")]
    snap.article_prefix_length = {"sup1": 5}
    # Ordered attribute rows (as PDM's attribute query returns them):
    #   WorktopWidth  parametric width 2 -> slice chars 6-7 -> "2S"
    #   WorktopDepth  parametric width 1 -> slice char 8    -> "4"
    #   LegStyle      fixed order code   -> "C"
    snap.article_varcond_terms = {
        "sup1": [
            {"name": "WorktopWidth", "order": 1, "has_dependent_options": 2,
             "order_code": ""},
            {"name": "WorktopDepth", "order": 2, "has_dependent_options": 1,
             "order_code": ""},
            {"name": "LegStyle", "order": 3, "has_dependent_options": 0,
             "order_code": "C"},
        ],
    }
    snap.article_components = {
        "sup1": [
            {"sub_item": "DWE3UH4.", "quantity": 1, "sequence": "1"},
            {"sub_item": "RY3UCCB.", "quantity": 2, "sequence": "2"},
        ],
    }
    # Option increment prices keyed by sub-item prefix (PDM ItemOptionValues).
    snap.option_increments = {
        "DWE3UH4.": [
            {"item": "DWE3UH4.", "option_id": 9502, "option_name": "worktop finish",
             "value_name": "Oak", "code": "OK", "increment": 25.0},
            {"item": "DWE3UH4.", "option_id": 9502, "option_name": "worktop finish",
             "value_name": "Walnut", "code": "WN", "increment": 40.0},  # same opt id
        ],
    }
    return snap


def main() -> int:
    svc = VarCondService.__new__(VarCondService)  # no context needed for generate()
    body = "IF WorktopWidth = '2S' AND WorktopDepth = '4' AND LegStyle = 'C'"

    # 1) Parametric slicing + fixed codes + ordering + one rule per sub-item.
    res = svc.generate(snapshot=_snapshot())
    rules = [r.rule for r in res.rules]
    assert f"$VARCOND = 'DWE3UH4.' {body}" in rules, rules
    assert f"$VARCOND = 'RY3UCCB.' {body}" in rules, rules
    print("OK: parametric dims sliced from article number; one $VARCOND per sub-item")

    # 2) Quantity > 1 emits $SET_PRICING_FACTOR; qty 1 does not.
    assert f"$SET_PRICING_FACTOR('RY3UCCB.', 2) {body}" in rules, rules
    assert not any("SET_PRICING_FACTOR('DWE3UH4." in r for r in rules)
    print("OK: quantity > 1 adds $SET_PRICING_FACTOR")

    # 3) Output joined with ",\r\n" and terminated with a trailing "\r\n".
    assert res.text.endswith("\r\n"), repr(res.text[-4:])
    assert ",\r\n" in res.text
    print("OK: rules joined with ',\\r\\n' and trailing '\\r\\n'")

    # 4) No property prefix by default; prefix is applied when given.
    assert all("PA_PRICING." not in r for r in rules)
    pref = svc.generate(prefix="PA_PRICING", snapshot=_snapshot())
    assert any("PA_PRICING.WorktopWidth = '2S'" in r.rule for r in pref.rules)
    print("OK: prefix empty by default, applied when supplied")

    # 5) Exclusions use PDM substring semantics (drops LegStyle).
    excl = svc.generate(property_exclusions="LegStyle", snapshot=_snapshot())
    assert all("LegStyle" not in r.rule for r in excl.rules), excl.rules[0].rule
    assert "LegStyle" in excl.excluded
    print("OK: exclusions drop matching properties (substring)")

    # 6) Substitutions rename a property (old=new).
    subs = svc.generate(
        property_substitutions="WorktopWidth=WTW", snapshot=_snapshot()
    )
    assert any("WTW = '2S'" in r.rule for r in subs.rules), subs.rules[0].rule
    print("OK: substitutions rename a property")

    # 7) Property-name parser ports (special cases + second-word capitalisation).
    assert svc._pcon_property_name("castor & glides", "X") == "Castors_Glides"
    assert svc._pcon_property_name("Hinge / closure", "X") == "Hinge"
    assert svc._pcon_property_name("Power Entry cord", "X") == "Power_Entry"
    assert svc._pcon_property_name("Power entry", "X") == "Power_Entry"
    assert svc._pcon_property_name("Width", "RYSCR2") == "Screen_Width"
    assert svc._pcon_property_name("Width", "RYSCRL9") == "Screen_Width_FS"
    assert svc._pcon_property_name("Width", "RYSCRM8") == "Panel_Width"
    assert svc._pcon_property_name("Foot", "HZ13") == "Glides_Castors"
    assert svc._pcon_property_name("Colour (A)", "RY3X5") == "Colour_A"
    print("OK: property-name parser matches PDM special cases")

    # 8) No super-product BOM -> no rules + a warning.
    empty = svc.generate(snapshot=Snapshot())
    assert empty.rules == []
    assert any("ItemComponents" in w for w in empty.warnings)
    print("OK: no BOM -> no rules (warns)")

    # 9) Option-increment price-suffix lines (general path), deduped by option id.
    assert f"$VARCOND = 'DWE3UH4. 9502=' + Worktop_Finish {body}" in rules, rules
    # only one suffix per option id despite two increment rows for 9502:
    assert sum("9502=" in r for r in rules) == 1, rules
    # camelCase option-name parser (lower-cases the rest, spaces -> underscore):
    assert svc._pcon_option_name("worktop finish") == "Worktop_Finish"
    assert svc._pcon_option_name("BASE/TRIM colour") == "Basetrim_Colour"
    print("OK: option-increment price-suffix lines emitted (deduped, camelCase)")

    # 10) Automatic exclusion: a parametric property whose code does not resolve
    #     from the article number (empty decode) is dropped from the IF; only
    #     the properties actually encoded in the article number remain.
    snap10 = Snapshot()
    snap10.articles = [Article(id="s", code="ABC12")]   # 5 chars
    snap10.article_prefix_length = {"s": 3}              # base 'ABC'
    snap10.article_varcond_terms = {
        "s": [
            {"name": "Size", "order": 1, "has_dependent_options": 2,
             "order_code": ""},   # chars 4-5 -> "12" (applicable)
            {"name": "Extra", "order": 2, "has_dependent_options": 2,
             "order_code": ""},   # chars 6-7 -> "" (not in this article number)
            {"name": "Leg", "order": 3, "has_dependent_options": 0,
             "order_code": "C"},  # fixed code (applicable)
        ],
    }
    snap10.article_components = {"s": [{"sub_item": "SUB.", "quantity": 1}]}
    rule10 = svc.generate(snapshot=snap10).rules[0].rule
    assert "Size = '12'" in rule10, rule10
    assert "Leg = 'C'" in rule10, rule10
    assert "Extra" not in rule10, rule10   # auto-dropped: no code resolves
    print("OK: parametric property with no resolvable code auto-excluded")

    # 11) Per-component head-property filtering: each component's IF uses only the
    #     head properties it itself carries (its own BaseAttributeValues), not the
    #     parent super item's full set. Real case: a leg component is not
    #     controlled by Top material; a top component is not controlled by Base
    #     type.
    snap11 = Snapshot()
    snap11.articles = [Article(id="p1", code="1580TA1W")]   # base '1580' + T A
    snap11.article_prefix_length = {"p1": 4}
    snap11.article_varcond_terms = {
        "p1": [
            {"name": "Base type", "order": 5, "has_dependent_options": 1,
             "order_code": ""},    # pos 5 -> 'T'
            {"name": "Top material", "order": 6, "has_dependent_options": 1,
             "order_code": ""},    # pos 6 -> 'A'
        ],
    }
    snap11.article_components = {
        "p1": [
            {"sub_item": "FKCKITLEG1", "quantity": 1, "sequence": "1"},
            {"sub_item": "FKCTOP1580W", "quantity": 1, "sequence": "2"},
        ],
    }
    snap11.component_head_attrs = {
        "FKCKITLEG1": ["Base type"],       # leg -> only Base type
        "FKCTOP1580W": ["Top material"],   # top -> only Top material
    }
    res11 = VarCondService.__new__(VarCondService).generate(snapshot=snap11)
    leg = next(r.rule for r in res11.rules if "'FKCKITLEG1'" in r.rule)
    top = next(r.rule for r in res11.rules if "'FKCTOP1580W'" in r.rule)
    assert "Base_Type = 'T'" in leg and "Top_Material" not in leg, leg
    assert "Top_Material = 'A'" in top and "Base_Type" not in top, top
    print("OK: each component's IF uses only its own controlling head properties")

    # 12) Exact-duplicate rules collapse to one; the short-code warning fires
    #     only for dimension attributes (Height/Width/Depth), not a width-1
    #     attribute like Base type.
    snap12 = Snapshot()
    snap12.articles = [
        Article(id="pa", code="1580TA1W"),
        Article(id="pb", code="1580TACW"),   # variant that reuses the same top
    ]
    snap12.article_prefix_length = {"pa": 4, "pb": 4}
    terms = [
        {"name": "Base type", "order": 5, "has_dependent_options": 1,
         "order_code": ""},
        {"name": "Top material", "order": 6, "has_dependent_options": 1,
         "order_code": ""},
    ]
    snap12.article_varcond_terms = {"pa": terms, "pb": terms}
    snap12.article_components = {
        "pa": [{"sub_item": "FKCTOP1580W", "quantity": 1, "sequence": "1"}],
        "pb": [{"sub_item": "FKCTOP1580W", "quantity": 1, "sequence": "1"}],
    }
    snap12.component_head_attrs = {"FKCTOP1580W": ["Top material"]}
    res12 = VarCondService.__new__(VarCondService).generate(snapshot=snap12)
    top_rules = [r.rule for r in res12.rules if "'FKCTOP1580W'" in r.rule
                 and r.rule.startswith("$VARCOND = '")]
    assert len(top_rules) == 1, top_rules   # identical rule from pa+pb -> deduped
    # Base type (width 1) must NOT raise the short-code warning.
    assert not any("Base type" in w for w in res12.warnings), res12.warnings
    print("OK: exact-duplicate rules deduped; short-code warning is dimension-only")

    print("ALL VARCOND CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
