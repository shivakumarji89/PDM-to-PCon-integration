"""Synthetic OCD repository used by the generator, exporter and page tests (no external data).

Layouts follow the real ``pdata.ocd_*.inp_descr`` / OCD 4.3 column order. Only the three text tables
need a descriptor (the engine has no default layout for them), exactly as in real repositories.

``demo/ANY/1/db`` holds, for article CHAIR1 (scheme ``U1`` = ``@x6, ' ', Material, ' ', Size``):

* Material  W | M(default)     Size  S(default) | L
* value ``Size=L`` has the precondition ``Material = 'W'``  ->  Metal/Large is invalid, 3 valid SKUs
* price relation ``$VARCOND = 'SIZE=' + Size,``; base 100 EUR / 90 GBP, ``SIZE=L`` adds 25 EUR

Other articles: STOOL1 (no properties, no code scheme, no price), BROKEN (malformed class position),
DUPE (listed twice), SIDE1 (a property that does not feed the code scheme -> duplicate final numbers).
"""
from __future__ import annotations

from pathlib import Path

TEXT_DESCRIPTOR = (
    "table\t{table}\t{table}.csv\tmscsv\n"
    "fields\t5\n"
    "field\t1\ttextnr\tvstring\t\tdelim ;\n"
    "field\t2\tlanguage\tvstring\t\tdelim ;\n"
    "field\t3\tline_nr\tuint8\t\tdelim ;\n"
    "field\t4\tline_fmt\tvstring\t\tdelim ;\n"
    "field\t5\ttext\tvstring\t\tdelim ;\n"
)


def write(folder: Path, name: str, text: str) -> None:
    (folder / name).write_bytes(text.strip("\n").replace("\n", "\r\n").encode("latin-1") + b"\r\n")


def text_table(folder: Path, table: str, entries: dict[str, str]) -> None:
    rows = []
    for number, label in entries.items():
        rows.append(f'{number};en; 1;\\;"{label}"')
        rows.append(f'{number};de; 1;\\;"de {label}"')
    write(folder, f"{table}.csv", "\n".join(rows))
    (folder / f"pdata.{table}.inp_descr").write_text(TEXT_DESCRIPTOR.format(table=table), encoding="latin-1")


def article_row(number, manufacturer, series, text_nr, rel_obj="0", scheme=""):
    return f"{number};C;{manufacturer};{series};{text_nr};;{rel_obj};0;1;C62;{scheme}"


def write_plain_range(root: Path, name: str, articles) -> Path:
    """A range with articles and short texts only; ``articles`` = [(number, manufacturer, series, label)]."""
    db = root / name / "ANY" / "1" / "db"
    db.mkdir(parents=True)
    rows, texts = [], {}
    for index, (number, manufacturer, series, label) in enumerate(articles, 1):
        text_nr = f"{name}{index:04d}"
        rows.append(article_row(number, manufacturer, series, text_nr))
        texts[text_nr] = label
    write(db, "ocd_article.csv", "\n".join(rows))
    text_table(db, "ocd_artshorttext", texts)
    return db


def write_demo_range(root: Path, name: str = "demo", *, extra_articles=()) -> Path:
    """The configurable ``demo`` range described in the module docstring."""
    db = root / name / "ANY" / "1" / "db"
    db.mkdir(parents=True)
    articles = [
        ("CHAIR1", "MK", "DM", "Demo Chair", "900", "U1"),
        ("STOOL1", "MK", "DM", "Demo Stool", "0", ""),
        ("BROKEN", "MK", "DM", "Broken Item", "0", ""),
        ("DUPE", "MK", "DM", "Duplicate", "0", ""),
        ("DUPE", "MK", "DM", "Duplicate again", "0", ""),
        ("SIDE1", "MK", "DM", "Demo Side Table", "900", "U2"),
        ("TABLE1", "MK", "DX", "Demo Table", "0", ""),
        *extra_articles,
    ]
    rows, texts = [], {}
    for index, (number, manufacturer, series, label, rel_obj, scheme) in enumerate(articles, 1):
        text_nr = f"T{index:04d}"
        rows.append(article_row(number, manufacturer, series, text_nr, rel_obj, scheme))
        texts[text_nr] = label
    write(db, "ocd_article.csv", "\n".join(rows))
    text_table(db, "ocd_artshorttext", texts)
    text_table(db, "ocd_propertytext", {"P1": "Material", "P2": "Size", "P3": "Colour"})
    text_table(db, "ocd_propvaluetext", {"V1": "Wood", "V2": "Metal", "V3": "Small", "V4": "Large"})
    write(db, "ocd_propertyclass.csv",
          "CHAIR1;1;DEMO_OPT;10;0\nSIDE1;1;DEMO_OPT2;10;0\nBROKEN;x;DEMO_OPT;10;0")
    write(db, "ocd_property.csv",
          "DEMO_OPT;Material;1;P1;0;C;1;0;1;0;0;0;C;0;\n"
          "DEMO_OPT;Size;2;P2;0;C;1;0;1;0;0;0;C;0;\n"
          "DEMO_OPT2;Size;1;P2;0;C;1;0;1;0;0;0;C;0;\n"
          "DEMO_OPT2;Colour;2;P3;0;C;1;0;1;0;0;0;C;0;")
    write(db, "ocd_propertyvalue.csv",
          "DEMO_OPT;Material;1;V1;0;0;0;EQ;W;;;;;\n"
          "DEMO_OPT;Material;2;V2;0;1;0;EQ;M;;;;;\n"
          "DEMO_OPT;Size;1;V3;0;1;0;EQ;S;;;;;\n"
          "DEMO_OPT;Size;2;V4;100;0;0;EQ;L;;;;;\n"
          "DEMO_OPT2;Size;1;V3;0;1;0;EQ;S;;;;;\n"
          "DEMO_OPT2;Size;2;V4;0;0;0;EQ;L;;;;;\n"
          "DEMO_OPT2;Colour;1;V1;0;0;0;EQ;R;;;;;\n"
          "DEMO_OPT2;Colour;2;V2;0;0;0;EQ;G;;;;;")
    write(db, "ocd_relationobj.csv", "100;1;000000000000000001;1;C\n900;1;000000000000000002;3;P")
    write(db, "ocd_relation.csv",
          '000000000000000001; 1;"Material = \'W\'"\n'
          '000000000000000002; 1;"$VARCOND = \'SIZE=\' + Size,"')
    # U2 ignores Colour, so the two colours of a size encode to the same final number.
    write(db, "ocd_codescheme.csv",
          'U1;@,@,@,@,@,@, ,DEMO_OPT:Material, ,DEMO_OPT:Size;"";"";0;"-";"X";1;"";""\n'
          'U2;@,@,@,@,@, ,DEMO_OPT2:Size;"";"";0;"-";"X";1;"";""')
    write(db, "ocd_price.csv",
          "CHAIR1;;S;B;;;100;1;EUR;20250101;99991231;1;\n"
          "CHAIR1;SIZE=L;S;X;;;25;1;EUR;20250101;99991231;1;\n"
          "CHAIR1;;S;B;;;90;1;GBP;20250101;99991231;1;\n"
          "SIDE1;;S;B;;;50;1;EUR;20250101;99991231;1;")
    return db


#: What the engine must produce for CHAIR1 (derived by hand from the data above, not from the engine).
CHAIR1_FINALS = ["CHAIR1 W S", "CHAIR1 W L", "CHAIR1 M S"]
CHAIR1_PRICES_EUR = {"CHAIR1 W S": "100.00", "CHAIR1 W L": "125.00", "CHAIR1 M S": "100.00"}
