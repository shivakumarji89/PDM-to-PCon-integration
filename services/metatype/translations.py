"""Template Step 5: validation of the translation table.

Template Step 5 ("Translations (always last)"): once the technical structure (property, values, article
mapping and any Step 4a exceptions) is defined, ask for translations of every label and value collected so
far, in the fixed order German, French, Dutch, and present them as a table (Technical value -> EN -> DE -> FR
-> NL) for the user to confirm or correct.

Which rows there are comes from the earlier steps: the Step 3 property (English label from Step 3) and every
value typed in Step 4a. The template collects no English label for a value, so the table asks for it.

Rules are limited to the template's wording:

* INCOMPLETE (the user can still supply it): a DE, FR or NL text is empty; a value's English text is empty.
* INVALID: a technical value in the answer is not one of the expected rows, or appears twice.

Not decided here, because the template does not say: text length or character rules, whether a translation may
equal the English text, the ``go_texts`` row format and encoding. Nothing is derived from the answer.

Pure and filesystem-free.
"""
from __future__ import annotations

from collections.abc import Iterable

from models.metatype_creation import Finding, Severity, TranslationKind, TranslationRow, ValidityStatus

BASIS = "template Step 5 (translations: German, French, Dutch)"
LANGUAGES = (("de", "German"), ("fr", "French"), ("nl", "Dutch"))   # the template's fixed order

INVALID_CODES = frozenset({"TRANSLATION_ROW_UNKNOWN", "TRANSLATION_ROW_DUPLICATE"})


def expected_rows(property_name: str, property_label: str, values: Iterable[str]) -> list[TranslationRow]:
    """The rows Step 5 must cover: the property first, then each Step 4a value in the order it was entered."""
    rows = [TranslationRow(property_name, TranslationKind.PROPERTY, en=property_label)]
    rows += [TranslationRow(v, TranslationKind.VALUE) for v in dict.fromkeys(values)]
    return rows


def validate_translations(
    submitted: Iterable[TranslationRow], expected: list[TranslationRow],
) -> tuple[ValidityStatus, list[Finding], list[TranslationRow]]:
    """Return ``(status, findings, rows in expected order)``. Only COMPLETE may be stored as confirmed."""
    findings: list[Finding] = []

    def add(code: str, message: str) -> None:
        findings.append(Finding(Severity.ERROR, code, message, basis=BASIS))

    by_key: dict[str, TranslationRow] = {}
    keys = {r.technical for r in expected}
    for row in submitted:
        key = row.technical.strip()
        if key not in keys:
            add("TRANSLATION_ROW_UNKNOWN", f"{key or '(blank)'} is not a property or value from the earlier steps.")
        elif key in by_key:
            add("TRANSLATION_ROW_DUPLICATE", f"{key} appears more than once.")
        else:
            by_key[key] = row

    cleaned: list[TranslationRow] = []
    for want in expected:
        got = by_key.get(want.technical)
        row = TranslationRow(want.technical, want.kind, want.en if want.kind is TranslationKind.PROPERTY
                             else (got.en.strip() if got else ""),
                             *(((getattr(got, code) if got else "").strip()) for code, _ in LANGUAGES))
        cleaned.append(row)
        if want.kind is TranslationKind.VALUE and not row.en:
            add("TRANSLATION_MISSING_EN", f"{row.technical}: give its English text.")
        for code, name in LANGUAGES:
            if not getattr(row, code):
                add("TRANSLATION_MISSING", f"{row.technical}: the {name} text is missing.")

    codes = {f.code for f in findings}
    if codes & INVALID_CODES:
        return ValidityStatus.INVALID, findings, cleaned
    return (ValidityStatus.INCOMPLETE if findings else ValidityStatus.COMPLETE), findings, cleaned
