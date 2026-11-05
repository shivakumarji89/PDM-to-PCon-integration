"""pCon Basket paste contract for generated OBX files.

The MK OFML Testsuite's ``build_obx`` output is the reference that pCon Basket accepts: a ``<cutBuffer>``
holding ``<state sessionId>``, ``<versionInfo>``, ``<items>`` and a ``<docCalculationChanges>`` block, where
every ``<bskArticle>`` carries its own non-empty, unique ``basketId`` (a UUID) and has exactly one
``<itemCalculationChanges id>`` entry pointing back at it. Basket validates the paste against a schema; a
missing or empty ``basketId`` fails with ``XMLSchemaException: attribute 'basketId' is missing or empty``.

Neither tool can paste into Basket itself (the paste is a pCon action), so this module owns the two
things Workbench can do: write the identity envelope, and check a file against it *before* the user pastes.
"""
from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass

#: ``ppName`` of the Testsuite's ``docCalculationChanges`` (the pCon B2B price-calculation profile).
CALCULATION_PROFILE = "STDB2B_WBK"
ITEM_TYPES = {"BasketArticle", "BasketAggregate"}


class BasketPayloadError(ValueError):
    """The OBX would be rejected by Basket; the message lists every problem found."""

    def __init__(self, problems: list[str]):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


def new_basket_id() -> str:
    return str(uuid.uuid4())


def add_session_state(root: ET.Element, session_id: str | None = None) -> None:
    """``<state sessionId>`` - the Testsuite writes it first, before ``<versionInfo>``."""
    ET.SubElement(root, "state", {"sessionId": session_id or str(uuid.uuid4())})


def add_calculation_changes(root: ET.Element, basket_ids: list[str]) -> None:
    changes = ET.SubElement(root, "docCalculationChanges", {"ppName": CALCULATION_PROFILE})
    for basket_id in basket_ids:
        ET.SubElement(changes, "itemCalculationChanges", {"id": basket_id})


@dataclass(frozen=True)
class BasketPayload:
    """A checked OBX, ready to be pasted into (or imported by) Basket."""

    xml: str
    article_count: int
    basket_ids: tuple[str, ...]

    @property
    def data(self) -> bytes:
        return self.xml.encode("utf-8")


def prepare_basket_payload(xml: str) -> BasketPayload:
    """Check *xml* against the Basket contract and wrap it; raise :class:`BasketPayloadError` otherwise."""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as exc:
        raise BasketPayloadError([f"The OBX is not well-formed XML: {exc}"]) from exc
    problems: list[str] = []
    if root.tag != "cutBuffer":
        problems.append(f"The root element is <{root.tag}>, not <cutBuffer>.")
    articles = root.findall("./items/bskArticle")
    if not articles:
        problems.append("The OBX contains no <bskArticle>.")

    ids: list[str] = []
    for position, article in enumerate(articles, start=1):
        label = next((a.text for a in article.findall("artNr") if a.get("type") == "base" and a.text), f"#{position}")
        basket_id = (article.get("basketId") or "").strip()
        if not basket_id:
            problems.append(f"{label}: attribute 'basketId' is missing or empty")
        else:
            ids.append(basket_id)
        if article.get("itemType") not in ITEM_TYPES:
            problems.append(f"{label}: itemType must be one of {sorted(ITEM_TYPES)}")
        if not any(a.get("type") == "base" and (a.text or "").strip() for a in article.findall("artNr")):
            problems.append(f"{label}: no <artNr type=\"base\"> text")
    problems += [f"basketId {value!r} is used by {n} articles" for value, n in Counter(ids).items() if n > 1]

    changes = root.find("docCalculationChanges")
    if articles and changes is None:
        problems.append("The <docCalculationChanges> block is missing.")
    elif changes is not None:
        listed = Counter(c.get("id") for c in changes.findall("itemCalculationChanges"))
        for value in ids:
            if listed.get(value) != 1:
                problems.append(f"basketId {value!r} needs exactly one <itemCalculationChanges> entry")
        problems += [f"<itemCalculationChanges id={value!r}> matches no article" for value in listed if value not in ids]

    if problems:
        raise BasketPayloadError(problems)
    return BasketPayload(xml=xml, article_count=len(articles), basket_ids=tuple(ids))


def basket_problems(xml: str) -> list[str]:
    """Contract problems of *xml* as a list (empty when Basket would accept it)."""
    try:
        prepare_basket_payload(xml)
    except BasketPayloadError as exc:
        return exc.problems
    return []
