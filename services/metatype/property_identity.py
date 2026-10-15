"""Template Step 3 validation: the technical property name and English label.

Template Step 3 asks for (1) the technical property name, "matching the series' existing prefix
convention found in Step 1", and (2) the English display label. The only hard rules applied here come from
the manual (MT_1.18.0, go_types "Property Name", lines 636-641) and its CSV rules (section 2 item 5):

* the name starts with ``G`` followed by a capital letter; no umlauts, special characters or spaces;
* ``GType`` is reserved;
* field values contain no control characters (U+0000..U+001F, U+007F..U+009F).

Underscores are accepted: the template's own examples (``GATLAS_...``) and the real data use them, while the
manual's "no special characters" does not say whether they count. The Verus prompt's "no underscores" rule
is not applied: its scope is not established by the sources.

Not enforced, because no source makes them rules: "each word starts with a capital letter" (the manual says
"should" and does not define words), name length, and the language of the label. The prefix convention is a
warning, never an error. Which metatype receives the property is not asked in Step 3, so the manual's
"one entry per (metatype, property)" duplicate rule cannot be applied; an existing name is reported as a
warning with its source row.

Pure and filesystem-free: it consumes Step 1's :class:`SeriesConventions`.
"""
from __future__ import annotations

import re

from models.metatype_creation import Finding, Severity
from models.metatype_series import SeriesConventions

_NAME_START = re.compile(r"^G[A-Z]")
_NAME_CHARS = re.compile(r"^[A-Za-z0-9_]+$")
_CONTROL = re.compile(r"[\u0000-\u001f\u007f-\u009f]")
_RESERVED = ("GType",)
_NO_PREFIX = "(no underscore)"

MT_NAME_BASIS = "MT_1.18.0 go_types Property Name (line 636)"
TEMPLATE_BASIS = "template Step 3"


def validate_property_identity(name: str, label: str, series: SeriesConventions | None) -> list[Finding]:
    """Return every finding for the proposed ``name`` / ``label``; errors block confirmation."""
    findings: list[Finding] = []
    name = name.strip()
    label = label.strip()

    if not name:
        findings.append(Finding(Severity.ERROR, "NAME_EMPTY", "A technical property name is required.",
                                basis=TEMPLATE_BASIS))
    else:
        findings += _name_rules(name)
        if series is not None:
            findings += _series_rules(name, series)

    if not label:
        findings.append(Finding(Severity.ERROR, "LABEL_EMPTY", "An English display label is required.",
                                basis=TEMPLATE_BASIS))
    elif _CONTROL.search(label):
        findings.append(Finding(Severity.ERROR, "LABEL_CONTROL_CHARACTER",
                                "The label contains a control character.", basis="MT_1.18.0 section 2 item 5"))
    return findings


def _name_rules(name: str) -> list[Finding]:
    out: list[Finding] = []
    if not _NAME_START.match(name):
        out.append(Finding(Severity.ERROR, "NAME_START",
                           "The name must start with 'G' followed by a capital letter.", basis=MT_NAME_BASIS))
    if not _NAME_CHARS.match(name):
        out.append(Finding(Severity.ERROR, "NAME_CHARACTERS",
                           "The name may contain only ASCII letters, digits and underscores (no umlauts, "
                           "spaces or other special characters).", basis=MT_NAME_BASIS))
    if name in _RESERVED:
        out.append(Finding(Severity.ERROR, "NAME_RESERVED", f"{name} is a reserved property name.",
                           basis="MT_1.18.0 go_types (line 641)"))
    return out


def _series_rules(name: str, series: SeriesConventions) -> list[Finding]:
    out: list[Finding] = []
    existing = [e for e in series.types.defined_properties if len(e.values) > 1 and e.values[1] == name]
    if existing:
        metatypes = ", ".join(e.values[0] for e in existing[:3]) + (f" and {len(existing) - 3} more" if len(existing) > 3 else "")
        out.append(Finding(
            Severity.WARNING, "NAME_EXISTS",
            f"{name} is already defined for {metatypes} (go_types line {existing[0].line}); "
            "confirm that reusing it is intended.", existing[0], TEMPLATE_BASIS))
    counted = [p for p in series.types.property_prefixes if p.value != _NO_PREFIX]
    prefixes = [p.value for p in counted]
    if not prefixes:
        out.append(Finding(
            Severity.INFO, "PREFIX_NO_CONVENTION",
            f"{series.family_id} has no existing prefixed property to follow, so the prefix was not checked "
            "(the template says to adapt to the target series' own convention).", basis=TEMPLATE_BASIS))
    else:
        own = name.partition("_")[0] + "_" if "_" in name else ""
        if own not in prefixes:
            shown = ", ".join(prefixes[:5])
            out.append(Finding(
                Severity.WARNING, "PREFIX_MISMATCH",
                f"The name does not use a prefix this series already uses ({shown}).",
                counted[0].evidence[0] if counted[0].evidence else None, TEMPLATE_BASIS))
    return out
