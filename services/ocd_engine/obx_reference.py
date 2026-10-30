"""Read pCon-exported OBX files for reference comparison (no generation here).

Only fields the engine can reproduce from OCD data are extracted: base/final/
varcode/ofmlvarcode numbers, the features pCon resolved, the price and its
date/currency. ``geometryChecksum``, ``addStateCode`` and ``appData`` are
runtime-derived by pCon and deliberately not read.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReferenceArticle:
    base: str
    final: str = ""
    varcode: str = ""
    ofml_varcode: str = ""
    price: str = ""                       # itemPrice type=sale, as written
    currency: str = ""
    price_date: str = ""                  # priceDate value, as written
    features: tuple[tuple[str, str, str], ...] = ()      # (name, value, flags)
    price_components: tuple[tuple[str, str], ...] = ()   # (name, percentage text)


def _artnr(item: ET.Element, kind: str) -> str:
    for node in item.findall("artNr"):
        if node.get("type") == kind:
            return (node.text or "").strip()
    return ""


def read_reference_obx(path: str | Path) -> list[ReferenceArticle]:
    root = ET.parse(path).getroot()
    items = root.find("items")
    out: list[ReferenceArticle] = []
    for item in (items if items is not None else []):
        if item.tag != "bskArticle":
            continue
        sale = next((p for p in item.findall("itemPrice")
                     if p.get("type") == "sale" and p.get("pd") is None), None)
        if sale is None:
            sale = next((p for p in item.findall("itemPrice") if p.get("type") == "sale"), None)
        date = item.find("priceDate")
        features = tuple(
            (f.get("name", ""), f.get("value", ""), f.get("flags", ""))
            for f in item.findall("./features/feature")
        )
        components = tuple(
            ((c.findtext("name") or "").strip(), c.get("value", ""))
            for c in item.findall("./priceComponents/priceComponent")
        )
        out.append(ReferenceArticle(
            base=_artnr(item, "base"), final=_artnr(item, "final"),
            varcode=_artnr(item, "varcode"), ofml_varcode=_artnr(item, "ofmlvarcode"),
            price=sale.get("value", "") if sale is not None else "",
            currency=sale.get("currency", "") if sale is not None else "",
            price_date=date.get("value", "") if date is not None else "",
            features=features, price_components=components,
        ))
    return out
