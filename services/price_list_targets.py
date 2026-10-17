"""Target price lists for the Pricing MDB export.

The operator names one target list per currency (EUR, GBP). This module turns
those names plus the MDB's existing ``tCOMd_PriceList2`` rows and the computation
date into a validated plan per currency: reuse an existing list, create a new
one, or block with a reason. Nothing here touches the MDB.

Rules (all verified against the real OCD MDB):

* Labels match ignoring case and space/underscore/hyphen (``EURO 2026_2`` ==
  ``EURO_2026_2``), but the operator's chosen display name is what a new list gets.
* A reused list must have the same currency and its validity must cover the
  computation date; otherwise the export is blocked (no silent fall-back to a
  historical list).
* Several lists with the same normalized label: the one whose label equals the
  chosen name exactly wins; otherwise a single region-linked list wins; otherwise
  the plan is blocked as ambiguous. Ignored look-alikes are reported.
* Never create a list whose label already belongs to a list of another currency
  or to a differently-spelled list that already matches.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Sequence

DATE_MIN = "19000101"
DATE_MAX = "99991231"
_MAX_NAME = 50
_NAME_OK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _\-]*$")


def normalize_mdb_date(value: Any, fallback: str) -> str:
    """Normalize Access bridge dates (``/Date(ms)/``, ISO, ``YYYYMMDD``) to ``YYYYMMDD``."""
    if value is None:
        return fallback
    if isinstance(value, datetime):
        return value.strftime("%Y%m%d")
    if hasattr(value, "strftime") and not isinstance(value, str):
        try:
            return value.strftime("%Y%m%d")
        except (TypeError, ValueError):
            pass
    text = str(value).strip()
    if not text:
        return fallback
    match = re.fullmatch(r"/Date\((-?\d+)(?:[+-]\d{4})?\)/", text)
    if match:
        try:
            instant = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(
                milliseconds=int(match.group(1)))
            try:
                return instant.astimezone().strftime("%Y%m%d")
            except (OverflowError, OSError):
                # Windows cannot convert dates near year 9999 (Access's 9999-12-31
                # "no end" validity): shift by the current offset instead.
                offset = datetime.now().astimezone().utcoffset() or timedelta(0)
                return (instant + offset).strftime("%Y%m%d")
        except (ValueError, OverflowError, OSError):
            return fallback
    digits = re.sub(r"\D", "", text)
    if len(digits) >= 8:
        candidate = digits[:8]
        try:
            datetime.strptime(candidate, "%Y%m%d")
            return candidate
        except ValueError:
            return fallback
    return fallback


def label_key(label: Any) -> str:
    """Label identity that ignores case and space/underscore/hyphen differences."""
    return re.sub(r"[\s_\-]+", "_", str(label or "").strip().upper())


def computation_date(records: Iterable[Any]) -> str:
    """The date the prices were computed for (``YYYYMMDD``): the most common
    ``valid_from`` of the records. Empty when no record carries one - the caller
    must then ask for a recompute rather than substitute today's date."""
    counts: dict[str, int] = {}
    for record in records:
        day = normalize_mdb_date(getattr(record, "valid_from", ""), "")
        if day:
            counts[day] = counts.get(day, 0) + 1
    return max(counts, key=lambda d: (counts[d], d)) if counts else ""


def currency_token(currency: str) -> str:
    ccy = (currency or "").strip().upper()
    return "EURO" if ccy == "EUR" else ccy


def validate_name(name: str) -> str:
    """Empty string when the list name is acceptable, else the reason."""
    text = (name or "").strip()
    if not text:
        return "Enter a price list name."
    if len(text) > _MAX_NAME:
        return f"Name is longer than {_MAX_NAME} characters."
    if not _NAME_OK.match(text):
        return "Use letters, digits, space, underscore or hyphen only."
    if label_key(text) == "DEFAULT":
        return "'default' is reserved."
    return ""


@dataclass
class ListTargetPlan:
    """The validated target list for one currency."""

    currency: str
    name: str
    label: str = ""
    action: str = "blocked"        # reuse | create | blocked
    list_id: Any = None            # existing id (reuse); None until created
    date_from: str = ""
    date_to: str = ""
    linked: bool = False
    matched_ids: list = field(default_factory=list)
    ignored_ids: list = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors and self.action in ("reuse", "create")

    def as_dict(self) -> dict[str, Any]:
        return {
            "currency": self.currency, "name": self.name, "action": self.action,
            "list_id": self.list_id, "date_from": self.date_from, "date_to": self.date_to,
            "linked": self.linked, "matched_ids": list(self.matched_ids),
            "ignored_ids": list(self.ignored_ids), "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


def default_names(
    currencies: Sequence[str], comp_date: str, existing_lists: Sequence[dict[str, Any]],
    snapshot_lists: Sequence[Any] = (),
) -> dict[str, str]:
    """Prefilled target names. A list the snapshot already names for a currency
    wins; otherwise ``EURO_<year>`` / ``GBP_<year>``, moving to the sole mid-year
    suffix ``_2`` when the base list exists but does not cover the computation date."""
    names: dict[str, str] = {}
    year = comp_date[:4] if len(comp_date) == 8 else ""
    for ccy in dict.fromkeys((c or "").strip().upper() for c in currencies if c):
        named = next((str(getattr(p, "label", "") or getattr(p, "id", ""))
                      for p in snapshot_lists
                      if (getattr(p, "currency", "") or "").strip().upper() == ccy), "")
        if named:
            names[ccy] = named.replace(" ", "_")
            continue
        base = f"{currency_token(ccy)}_{year}" if year else currency_token(ccy)
        chosen = base
        for suffix in ("", "_2"):
            candidate = base + suffix
            same = [r for r in existing_lists
                    if label_key(r.get("com_PriceListLabel")) == label_key(candidate)
                    and str(r.get("sys_ISOCurrencyCode") or "").strip().upper() == ccy]
            chosen = candidate
            if not same:
                break
            if any(_covers(r, comp_date) for r in same):
                break
        names[ccy] = chosen
    return names


def _covers(row: dict[str, Any], day: str) -> bool:
    start = normalize_mdb_date(row.get("com_PriceValidFrom"), DATE_MIN)
    end = normalize_mdb_date(row.get("com_PriceValidTo"), DATE_MAX)
    return bool(day) and start <= day <= end


def resolve_targets(
    names: dict[str, str], existing_lists: Sequence[dict[str, Any]],
    linked_ids: set[str], comp_date: str,
) -> dict[str, ListTargetPlan]:
    """Validate ``{currency: chosen name}`` against the MDB (see module docstring)."""
    plans: dict[str, ListTargetPlan] = {}
    for ccy, raw in names.items():
        ccy = (ccy or "").strip().upper()
        name = (raw or "").strip()
        plan = ListTargetPlan(currency=ccy, name=name)
        plans[ccy] = plan
        problem = validate_name(name)
        if problem:
            plan.errors.append(problem)
            continue
        if not comp_date:
            plan.errors.append("Prices carry no computation date; recompute prices.")
            continue
        key = label_key(name)
        same_ccy = [r for r in existing_lists
                    if str(r.get("sys_ISOCurrencyCode") or "").strip().upper() == ccy]
        matches = [r for r in same_ccy if label_key(r.get("com_PriceListLabel")) == key]
        other = [r for r in existing_lists if r not in same_ccy
                 and label_key(r.get("com_PriceListLabel")) == key]
        plan.matched_ids = [r.get("com_PriceListID") for r in matches]
        chosen = None
        if len(matches) == 1:
            chosen = matches[0]
        elif len(matches) > 1:
            exact = [r for r in matches
                     if str(r.get("com_PriceListLabel") or "").strip().casefold() == name.casefold()]
            linked = [r for r in matches if str(r.get("com_PriceListID")) in linked_ids]
            if len(exact) == 1:
                chosen = exact[0]
            elif len(linked) == 1:
                chosen = linked[0]
            else:
                plan.errors.append(
                    f"'{name}' matches {len(matches)} {ccy} price lists "
                    f"(ids {', '.join(str(i) for i in plan.matched_ids)}); "
                    "enter the exact label of the list to use.")
                continue
            plan.ignored_ids = [r.get("com_PriceListID") for r in matches if r is not chosen]
            plan.warnings.append(
                f"Also matches list id(s) {', '.join(str(i) for i in plan.ignored_ids)}; ignored.")
        if chosen is not None:
            plan.action = "reuse"
            plan.list_id = chosen.get("com_PriceListID")
            plan.date_from = normalize_mdb_date(chosen.get("com_PriceValidFrom"), DATE_MIN)
            plan.date_to = normalize_mdb_date(chosen.get("com_PriceValidTo"), DATE_MAX)
            plan.linked = str(plan.list_id) in linked_ids
            if not plan.date_from <= comp_date <= plan.date_to:
                plan.errors.append(
                    f"List '{chosen.get('com_PriceListLabel')}' (id {plan.list_id}) is valid "
                    f"{plan.date_from}-{plan.date_to}, which does not cover the computation date "
                    f"{comp_date}. Choose another name (e.g. a new list).")
            elif not plan.linked:
                plan.warnings.append(
                    "List is not linked to a distribution region; pCon will not read prices written to it.")
            continue
        if other:
            plan.errors.append(
                f"'{name}' is already the label of a list in another currency "
                f"(id {other[0].get('com_PriceListID')}); choose a different name.")
            continue
        plan.action = "create"
        plan.date_from, plan.date_to = comp_date, DATE_MAX
        covering = [r for r in same_ccy if _covers(r, comp_date)]
        if covering:
            plan.warnings.append(
                "A new list overlaps existing " + ccy + " list(s) valid on this date: "
                + ", ".join(f"{r.get('com_PriceListLabel')} (id {r.get('com_PriceListID')})" for r in covering)
                + ". Existing lists are not changed.")
        plan.warnings.append(
            "New list is not linked to a distribution region; pCon will not read it until it is linked.")
    keys: dict[str, str] = {}
    for ccy, plan in plans.items():
        k = label_key(plan.name)
        if k and k in keys:
            plan.errors.append(f"Same name as the {keys[k]} list; EUR and GBP lists must differ.")
        keys.setdefault(k, ccy)
    return plans
