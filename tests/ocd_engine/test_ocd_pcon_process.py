"""The pCon SKU-generation process step by step: structure trace, encoding mechanisms, fabric defaults.

Synthetic range ``FB``: article FB1 with class ``F`` - Fabric_Type A|B, Fabric_Colour A1 (default) A2 B1 B2 where
each colour carries a precondition on the type, plus Finish X|Y. FB2 is encoded through a computed ``Code``
property (a code relation). The real-data tests use Betwixt LN10 and skip when the repository is absent.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from services.ocd_engine.generator import GenerationError, OcdArticleGenerator
from tests.ocd_engine.ocd_repo_fixture import write

DATE = "2026-01-15"
PRICE = "{a};;S;B;;;100;1;EUR;20250101;99991231;1;"
SCHEME = 'U1;@,@,@,@, ,F:Fabric_Type,F:Fabric_Colour, ,F:Finish;"";"";0;"-";"X";1;"";""'
CODE_SCHEME = 'U2;CODE:Code;"";"";1;"-";"X";1;"";""'


def build(root: Path, *, default_a=True, default_b=False, artbase="") -> Path:
    db = root / "fb" / "ANY" / "1" / "db"
    db.mkdir(parents=True)
    write(db, "ocd_article.csv", "FB1;C;MK;DM;T1;;0;0;1;C62;U1\nFB2;C;MK;DM;T1;;0;0;1;C62;U2")
    write(db, "ocd_propertyclass.csv", "FB1;1;F;10;0\nFB2;1;F;10;0\nFB2;2;CODE;;0")
    write(db, "ocd_property.csv",
          "F;Fabric_Type;1;;0;C;1;0;1;0;1;0;C;0;\nF;Fabric_Colour;2;;0;C;1;0;1;0;1;0;C;0;\n"
          "F;Finish;3;;0;C;1;0;1;0;0;0;C;0;\nCODE;Code;1;;9;C;1;0;1;0;0;0;R;0;")
    flag = {"A1": int(default_a), "B1": int(default_b)}
    rows = ["F;Fabric_Type;1;;0;0;0;EQ;A;;;;;", "F;Fabric_Type;2;;0;0;0;EQ;B;;;;;"]
    for i, (colour, rel) in enumerate([("A1", 1), ("A2", 1), ("B1", 2), ("B2", 2)], 1):
        rows.append(f"F;Fabric_Colour;{i};;{rel};{flag.get(colour, 0)};0;EQ;{colour};;;;;")
    rows += ["F;Finish;1;;0;0;0;EQ;X;;;;;", "F;Finish;2;;0;0;0;EQ;Y;;;;;"]
    write(db, "ocd_propertyvalue.csv", "\n".join(rows))
    write(db, "ocd_artbase.csv", artbase)
    write(db, "ocd_relationobj.csv", "1;1;000000000000000001;1;C\n2;1;000000000000000002;1;C\n"
                                     "9;1;000000000000000009;3;C")
    write(db, "ocd_relation.csv",
          "000000000000000001; 1;\"Fabric_Type = 'A'\"\n000000000000000002; 1;\"Fabric_Type = 'B'\"\n"
          "000000000000000009; 1;\"Code = $BAN + Fabric_Type + Fabric_Colour\"")
    write(db, "ocd_codescheme.csv", SCHEME + "\n" + CODE_SCHEME)
    write(db, "ocd_price.csv", PRICE.format(a="FB1") + "\n" + PRICE.format(a="FB2"))
    return db


def run(db, **kwargs):
    return OcdArticleGenerator(db).generate(["FB1"], currency="EUR", price_date=DATE, **kwargs)


def colours(outcome):
    return {s.final_article.split()[1] for s in outcome.skus}


# ------------------------------------------------------------------ steps 1-6: the explicit chain
def test_structure_traces_article_encoding_classes_properties_values(tmp_path):
    structure = OcdArticleGenerator(build(tmp_path, artbase="FB1;F;Finish;X")).structure("FB1")
    assert [c.name for c in structure.classes] == ["F"]
    props = {p.name: p for p in structure.properties()}
    assert [props[n].offered_values for n in ("Fabric_Type", "Fabric_Colour", "Finish")] == [2, 4, 1]
    assert props["Finish"].restricted_by_artbase and props["Finish"].all_values == 2   # ArtBase narrows to X
    assert structure.artbase == {"F:Finish": ("X",)}
    assert structure.encoding.mechanisms == ("article encoding (codescheme)",)


def test_encoding_comes_from_a_code_relation_when_the_scheme_reads_a_computed_property(tmp_path):
    structure = OcdArticleGenerator(build(tmp_path)).structure("FB2")
    assert structure.encoding.scheme_properties == ("CODE:Code",)
    assert structure.encoding.code_relation_properties == ("Code",)
    assert structure.encoding.mechanisms == ("article encoding (codescheme)", "code relation (computed property)")


def test_unknown_article_is_a_clear_error(tmp_path):
    with pytest.raises(GenerationError, match="not in"):
        OcdArticleGenerator(build(tmp_path)).structure("NOPE")


# ------------------------------------------------------------------ real data: Betwixt LN10
LN10_DB = Path(r"C:\HermanMillerOFMLSVN\Staging\HermanMiller\_repository\hmx\betwixt\ANY\1\db")
needs_ln10 = pytest.mark.skipif(not (LN10_DB / "ocd_article.csv").is_file(), reason="Betwixt OCD data not available")


@needs_ln10
def test_ln10_structure_follows_the_real_chain():
    structure = OcdArticleGenerator(LN10_DB).structure("LN10")
    assert [c.name for c in structure.classes] == ["FEATURES", "FINISHES", "CODE", "PLC"]
    assert structure.artbase == {"PLC:PLC": ("LN",)}
    assert structure.encoding.mechanisms == ("article encoding (codescheme)", "code relation (computed property)")
    props = {p.name: p.offered_values for p in structure.properties()}
    assert props["Seat_Fabric_Colour"] == 448 and props["Seat_Fabric_Type"] == 17
    by_type = {t.type_value: t for t in structure.fabrics if t.colour_property == "Seat_Fabric_Colour"}
    assert len(by_type) == 17 and by_type["172"].colours[:2] == ("17201", "17202") and len(by_type["172"].colours) == 12
    assert by_type["172"].default_colour == "17201"                      # static preview: first by pos_pval


@needs_ln10
def test_ln10_default_only_set_and_its_relation_to_the_full_set():
    generator = OcdArticleGenerator(LN10_DB)
    outcome = generator.generate(["LN10"], currency="GBP", price_date="2026-11-02")
    digest = hashlib.sha256(chr(10).join(sorted(s.final_article for s in outcome.skus)).encode()).hexdigest()
    assert len(outcome.skus) == 432 and outcome.duplicates == 0 and outcome.invalid == 0 and not outcome.truncated
    assert digest == "69e06593d7131dd994401c14ef85e43992fda8c12f62afde2a6f0ba63caaf377"
    first = {}                                         # (side, type) -> first colour in pos_pval order
    for side in ("Seat", "Back"):
        for row in generator.dataset.values[("FINISHES", f"{side}_Fabric_Colour")]:
            relation = generator.dataset.relation_text(
                generator.dataset.relobjs[row["rel_obj"]][0]["rel_name"])
            if "'" in relation:
                first.setdefault((side, relation.split("'")[1]), (int(row["pos_pval"]), row["value_from"]))
    for sku in outcome.skus:
        values = {name: value for _, name, value, _ in sku.values}
        for side in ("Seat", "Back"):
            if f"{side}_Fabric_Colour" in values:
                assert values[f"{side}_Fabric_Colour"] == first[(side, values[f"{side}_Fabric_Type"])][1]


@needs_ln10
def test_ln10_default_only_set_is_a_subset_of_the_full_enumeration():
    generator = OcdArticleGenerator(LN10_DB)
    default_only = {s.final_article for s in generator.generate(["LN10"], currency="GBP", price_date="2026-11-02").skus}
    full = generator.generate(["LN10"], currency="GBP", price_date="2026-11-02", fabric_default_only=False)
    assert len(full.skus) == 254_043 and default_only <= {s.final_article for s in full.skus}
