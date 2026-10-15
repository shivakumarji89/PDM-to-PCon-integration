"""Template Step 4a: validation of the value-by-value article validity answer.

Template Step 4a asks "Do all articles accept the full value set, or does any article only allow a subset
(or all values)?". If there are exceptions it goes **value by value**, building ``Value | Valid for
article(s)``; a value valid everywhere may be marked "all"; it keeps asking until every value is covered.

What the template leaves open, and what is therefore *not* decided here:

* where the value list comes from (the Polymorphism branch of Step 4 collects none): the user names the
  values, and this module cannot check that the list is the property's complete value set;
* what "unstated values default to all" means for values nobody names: they are simply not in the table;
* the ``go_propvalues`` / ``go_actions`` default-reachability check the template asks the implementer to do
  before finishing: it needs the property's default value and mechanism, so it is not performed.

Rules are limited to what the template's wording and the earlier answers require:

* INCOMPLETE (the user can still supply it): the question is unanswered; exceptions exist but no value is
  given; a value has no name; a value has neither articles nor "all".
* INVALID (contradiction): the answer differs from Step 4's third question; values are given although every
  article accepts the full set; a value is listed twice; "all" is combined with articles; an article is
  not in the Step 4 list or is repeated within a row.
* Warnings: exceptions are claimed but no row restricts anything; a Step 4 article is valid for no listed
  value.

Pure and filesystem-free.
"""
from __future__ import annotations

from collections.abc import Iterable

from models.metatype_creation import Finding, Severity, ValidityStatus, ValueValidityRow

Q = "template Step 4a (do all articles accept the full value set)"
VBV = "template Step 4a (value by value: valid for article(s))"
STEP4 = "template Step 4 (does every listed article accept every property value)"

INCOMPLETE_CODES = frozenset({"VALIDITY_UNANSWERED", "VALUES_MISSING", "VALUE_NAME_MISSING", "VALIDITY_MISSING"})
INVALID_CODES = frozenset({
    "VALIDITY_CONTRADICTS_STEP4", "VALUES_WITHOUT_EXCEPTIONS", "VALUE_DUPLICATE", "VALIDITY_ALL_AND_ARTICLES",
    "ARTICLE_NOT_IN_STEP4", "ARTICLE_DUPLICATE_IN_ROW",
})

#: Marker the page maps to ``all_articles``; matched case-insensitively.
ALL_MARKER = "all"


def parse_validity_cell(text: str) -> tuple[bool, list[str]]:
    """Read a "Valid for article(s)" cell: ``all`` or a comma-separated article list; blank means unanswered."""
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if len(parts) == 1 and parts[0].casefold() == ALL_MARKER:
        return True, []
    return False, parts


def validate_value_validity(
    accepts_full_value_set: bool | None,
    rows: Iterable[ValueValidityRow],
    step4_articles: list[str],
    step4_every_article_accepts_every_value: bool,
) -> tuple[ValidityStatus, list[Finding], list[ValueValidityRow]]:
    """Return ``(status, findings, cleaned rows)``. Only COMPLETE may be stored as the confirmed answer."""
    findings: list[Finding] = []

    def add(severity: Severity, code: str, message: str, basis: str) -> None:
        findings.append(Finding(severity, code, message, basis=basis))

    cleaned: list[ValueValidityRow] = []
    for row in rows:
        value = row.value.strip()
        articles = [a.strip() for a in row.articles if a and a.strip()]
        if not value and not articles and not row.all_articles:
            continue                                            # a blank line is not an answer
        cleaned.append(ValueValidityRow(value, row.all_articles, articles))

    if accepts_full_value_set is None:
        add(Severity.ERROR, "VALIDITY_UNANSWERED",
            "Answer whether all articles accept the full value set, or whether some allow only a subset.", Q)
    elif accepts_full_value_set != step4_every_article_accepts_every_value:
        add(Severity.ERROR, "VALIDITY_CONTRADICTS_STEP4",
            "This answer differs from Step 4's third question (every listed article accepts every value: "
            f"{'yes' if step4_every_article_accepts_every_value else 'no'}). Change one of them.", STEP4)
    elif accepts_full_value_set is True:
        if cleaned:
            add(Severity.ERROR, "VALUES_WITHOUT_EXCEPTIONS",
                "Values are listed although every article accepts the full value set; remove them or "
                "answer that exceptions exist.", Q)
        return _status(findings), findings, []

    if accepts_full_value_set is False:
        if not cleaned:
            add(Severity.ERROR, "VALUES_MISSING",
                "Exceptions exist: list the property values, one by one, and which article(s) each is valid for.",
                VBV)
        _check_rows(cleaned, step4_articles, findings)
    return _status(findings), findings, cleaned


def _check_rows(rows: list[ValueValidityRow], step4_articles: list[str], findings: list[Finding]) -> None:
    allowed = set(step4_articles)
    seen: set[str] = set()
    for row in rows:
        label = row.value or "(unnamed)"

        def add(severity: Severity, code: str, message: str) -> None:
            findings.append(Finding(severity, code, message, basis=VBV))

        if not row.value:
            add(Severity.ERROR, "VALUE_NAME_MISSING", "A line has articles but no value; name the value.")
        elif row.value in seen:
            add(Severity.ERROR, "VALUE_DUPLICATE", f"Value {row.value} is listed more than once.")
        seen.add(row.value)
        if row.all_articles and row.articles:
            add(Severity.ERROR, "VALIDITY_ALL_AND_ARTICLES",
                f"Value {label}: use either \"all\" or a list of articles, not both.")
        elif not row.all_articles and not row.articles:
            add(Severity.ERROR, "VALIDITY_MISSING",
                f"Value {label}: say which article(s) it is valid for, or mark it \"all\".")
        if len(set(row.articles)) != len(row.articles):
            add(Severity.ERROR, "ARTICLE_DUPLICATE_IN_ROW", f"Value {label}: an article is listed more than once.")
        for article in dict.fromkeys(row.articles):
            if article not in allowed:
                add(Severity.ERROR, "ARTICLE_NOT_IN_STEP4",
                    f"Value {label}: {article} is not one of the articles listed in Step 4.")

    answered = [r for r in rows if r.value and (r.all_articles or r.articles)]
    if answered and all(r.all_articles for r in answered) and len(answered) == len(rows):
        findings.append(Finding(
            Severity.WARNING, "NO_EXCEPTION_IN_TABLE",
            "Exceptions were reported but every listed value is valid for all articles.", basis=VBV))
    for article in step4_articles:
        if all(not r.all_articles and article not in r.articles for r in answered) and answered:
            findings.append(Finding(
                Severity.WARNING, "ARTICLE_ACCEPTS_NO_VALUE",
                f"{article} is not valid for any listed value.", basis=VBV))
    findings.append(Finding(
        Severity.INFO, "VALUE_SET_NOT_VERIFIED",
        "The template names no source for the property's values, so the list was not checked for "
        "completeness, and the go_propvalues/go_actions default-reachability check was not performed.",
        basis=VBV))


def _status(findings: list[Finding]) -> ValidityStatus:
    codes = {f.code for f in findings if f.severity is Severity.ERROR}
    if codes & INVALID_CODES:
        return ValidityStatus.INVALID
    return ValidityStatus.INCOMPLETE if codes else ValidityStatus.COMPLETE
