"""Price text blocks (``tCOMd_Text``, type ``price``) as PDM's pCon price update builds them.

Source of truth: ``PriceMaintenance.AddMissingGlobalPricingRecords`` (PDM). For
every global price (package, price list, variant condition) PDM

1. reads ``com_TextID`` from the existing ``tCOMd_GlobalPrice`` row, else
2. looks a text up by ``com_PackageId`` + ``com_TextName``, else
3. INSERTs ``tCOMd_Text (com_PackageId, com_TextTypeCode='price', com_TextName,
   <prefix>en/de/fr/nl/it ...)`` and re-reads its autonumber id,

and then INSERTs the global price with that ``com_TextID`` (level ``X``). The
article-price INSERT has no text column, so article prices never carry a text.
Existing links are never rewritten by the price-value update path.

This module holds the pure naming/schema rules so the exporter, the preview and
the UI agree on them.
"""
from __future__ import annotations

from typing import Any, Iterable

#: Languages PDM writes into a new price text, when the column exists.
LANGUAGES = ("en", "de", "fr", "nl", "it")

# Row-level text actions (shared vocabulary of export preview / result / UI).
ACTION_REUSE = "reuse"        # new price row links to a text already in the MDB
ACTION_CREATE = "create"      # new price row creates its text block
ACTION_LINK_NEW = "link_new"  # new price row links to a text created earlier this run
ACTION_PRESERVE = "preserve"  # existing price row keeps its existing text link
ACTION_UNLINKED = "unlinked"  # existing price row has no text link; left unchanged
ACTION_SKIP = "skip"          # new price row blocked: text mapping missing/ambiguous
ACTION_NONE = "none"          # no text operation applies (article prices)

ACTION_LABELS = {
    ACTION_REUSE: "Reuse existing text block",
    ACTION_CREATE: "Create new text block",
    ACTION_LINK_NEW: "Link to text block created in this export",
    ACTION_PRESERVE: "Preserve existing text reference",
    ACTION_UNLINKED: "Existing row has no text reference (unchanged)",
    ACTION_SKIP: "Skipped: text mapping missing or ambiguous",
    ACTION_NONE: "No text operation required",
}


def price_text_labels(variant_condition: str, product_code: str = "") -> tuple[str, str]:
    """``(com_TextName, display text)`` PDM derives for a global variant condition.

    * ``"ITEM 8=1FD"`` (space before ``=``): a surcharge row. Name ``8`` (the
      option id, shared by every value of the option); display ``Surcharge 8``.
    * any other condition without ``_``: name = the condition, display
      ``"<condition>  (<Product_Code>)"``.
    * a condition containing ``_``: name = display = the condition.
    """
    vc = variant_condition or ""
    display = vc
    if " " in vc and "=" in vc and vc.index(" ") < vc.index("="):
        display = "Surcharge " + vc[vc.index(" ") + 1:].split("=", 1)[0]
    elif "_" not in vc:
        display = f"{vc}  ({product_code})" if product_code else vc
    name = display.replace("Surcharge ", "")
    if "  (" in name:
        name = name[:name.index("  (")]
    return name, display


def text_column_prefix(columns: Iterable[str]) -> str:
    """PDM's ``GetPConTextColumnNamePrefixForWorkspace``: the first ``com_Text_*``
    column's name up to and including its last underscore (``com_Text_1_``)."""
    for name in columns:
        if name.startswith("com_Text_"):
            return name[:name.rindex("_") + 1]
    return ""


def language_columns(columns: Iterable[str]) -> list[str]:
    """The ``<prefix>en/de/fr/nl/it`` columns that exist in ``tCOMd_Text``."""
    cols = list(columns)
    prefix = text_column_prefix(cols)
    if not prefix:
        return []
    present = set(cols)
    return [prefix + lang for lang in LANGUAGES if prefix + lang in present]


def name_key(name: Any) -> str:
    """Text names compare case-insensitively, as Jet's ``=`` does in PDM's lookup."""
    return str(name or "").strip().casefold()


# Status of a price row's text block as the UI shows it.
STATUS_EXISTING = "existing"      # id read from the MDB (reused / preserved / imported)
STATUS_CREATED = "created"        # written by an export and read back
STATUS_NEW = "new"                # proposed: will be created, NOT written yet
STATUS_MISSING = "missing"        # a global row with no text reference
STATUS_BLOCKED = "blocked"        # missing/ambiguous mapping: row would not be inserted
STATUS_UNVERIFIED = "unverified"  # written but the read-back did not confirm it
STATUS_UNCHECKED = "unchecked"    # computed price not compared with an MDB yet
STATUS_NA = "n/a"                 # article prices carry no text block

ISSUE_STATUSES = (STATUS_MISSING, STATUS_BLOCKED, STATUS_UNVERIFIED)


def row_result_key(entry: dict) -> tuple:
    """``PriceRecord.key()`` of the record a row-level text result belongs to."""
    return (entry.get("table") == "tCOMd_GlobalPrice", entry.get("article_code", ""),
            entry.get("variant_condition", ""), entry.get("level", ""),
            str(entry.get("currency", "")).upper())


def record_result_key(record) -> tuple:
    return (record.is_global, record.article_code, record.variant_condition,
            record.level, (record.currency or "").upper())


def text_block_cells(record, result: dict | None = None, from_mdb: bool = False,
                     price_texts: dict[str, str] | None = None) -> tuple[str, str, str]:
    """``(Text Block ID, Text Block, status)`` of one price row.

    An id is only ever one that exists in the MDB: a text that an export would
    create is shown as "New (not written)" until a verified export wrote it.
    ``price_texts`` maps text name -> English content for imported MDBs.
    """
    if not record.is_global:
        return "\u2014", "", STATUS_NA
    name, display = price_text_labels(record.variant_condition, getattr(record, "product_code", ""))
    if result is not None:
        action, text_id = result.get("action"), result.get("text_id")
        label = result.get("text_content") or result.get("text_name") or name
        if action in (ACTION_REUSE, ACTION_PRESERVE):
            return str(text_id), _describe(result.get("text_name") or name, result.get("text_content")), STATUS_EXISTING
        if action in (ACTION_CREATE, ACTION_LINK_NEW):
            if text_id is not None and result.get("text_status") == STATUS_CREATED:
                return str(text_id), _describe(name, label), STATUS_CREATED
            if result.get("text_status") == STATUS_UNVERIFIED:
                return "Unverified", _describe(name, label), STATUS_UNVERIFIED
            return "New (not written)", _describe(name, display), STATUS_NEW
        if action == ACTION_UNLINKED:
            return "Missing", "no text reference on the existing row", STATUS_MISSING
        if action == ACTION_SKIP:
            return "Blocked", result.get("reason") or "text mapping missing or ambiguous", STATUS_BLOCKED
    if from_mdb:
        if getattr(record, "text_id", ""):
            content = (price_texts or {}).get(name_key(name), "")
            return str(record.text_id), _describe(name, content), STATUS_EXISTING
        return "Missing", "no text reference", STATUS_MISSING
    return "Not checked", f"{name} (proposed)", STATUS_UNCHECKED


def _describe(name: str, content: str | None) -> str:
    content = (content or "").strip()
    return f"{name} \u2014 {content}" if content and content != name else name
