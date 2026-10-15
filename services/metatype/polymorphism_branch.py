"""Template Step 4, Polymorphism branch: validation of the user's three answers.

Template Step 4 ("If Polymorphism was chosen") asks, one at a time:

1. which articles the property should switch between;
2. whether the switch is unconditional or scoped to certain other conditions (parent property, region, etc.);
3. whether every listed article accepts every property value, or whether there are exceptions (see Step 4a).

The template defines no format for articles or conditions and no completion rule beyond "answered", so the
rules here are limited to what the questions themselves require:

* the article list is not empty and names no article twice (an error: the same article cannot be switched to
  twice); fewer than two articles is a warning because the template says "switch between";
* an article the series' ``go_articles`` does not list is a warning (it may be a new article), not an error;
* "scoped" needs at least one condition, and "unconditional" must not come with conditions;
* the third question must be answered. "No exceptions" and "exceptions exist" are both accepted; the
  value-by-value table the template asks for in Step 4a is **not** collected here.

Conditions are kept as the user's text. They are not parsed or validated as OFML expressions: the template
does not say how they must be written. No mode bit is derived from any answer.

Pure and filesystem-free.
"""
from __future__ import annotations

from collections.abc import Iterable

from models.metatype_creation import ArticleRef, Finding, Severity, SwitchScope

Q1 = "template Step 4 (which articles the property switches between)"
Q2 = "template Step 4 (unconditional or scoped)"
Q3 = "template Step 4 (does every listed article accept every property value)"


def validate_polymorphism_branch(
    articles: Iterable[str],
    scope: SwitchScope | str | None,
    scope_conditions: Iterable[str],
    every_article_accepts_every_value: bool | None,
    known_articles: list[ArticleRef] | None,
) -> tuple[list[Finding], list[str], SwitchScope | None, list[str]]:
    """Return ``(findings, cleaned articles, scope, cleaned conditions)``; errors block confirmation."""
    findings: list[Finding] = []

    cleaned = [a.strip() for a in articles if a and a.strip()]
    seen: set[str] = set()
    for article in cleaned:
        if article in seen:
            findings.append(Finding(Severity.ERROR, "ARTICLE_DUPLICATE",
                                    f"{article} is listed more than once.", basis=Q1))
        seen.add(article)
    unique = list(dict.fromkeys(cleaned))
    if not unique:
        findings.append(Finding(Severity.ERROR, "ARTICLES_EMPTY",
                                "List the articles the property should switch between.", basis=Q1))
    elif len(unique) < 2:
        findings.append(Finding(Severity.WARNING, "ARTICLES_SINGLE",
                                "Only one article is listed; the property is meant to switch between articles.",
                                basis=Q1))
    if known_articles is None:
        findings.append(Finding(Severity.INFO, "ARTICLES_UNVERIFIED",
                                "The series' go_articles could not be read, so the articles were not checked "
                                "against it.", basis=Q1))
    elif unique:
        listed = {a.article_nr: a for a in known_articles}
        for article in unique:
            if article not in listed:
                findings.append(Finding(
                    Severity.WARNING, "ARTICLE_UNKNOWN",
                    f"{article} is not an article of this series (go_articles); fine if it is a new article.",
                    basis=Q1))

    chosen: SwitchScope | None
    try:
        chosen = SwitchScope(scope) if scope is not None else None
    except ValueError:
        chosen = None
    conditions = [c.strip() for c in scope_conditions if c and c.strip()]
    if chosen is None:
        findings.append(Finding(Severity.ERROR, "SCOPE_MISSING",
                                "Choose whether the switch is unconditional or scoped to conditions.", basis=Q2))
    elif chosen is SwitchScope.SCOPED and not conditions:
        findings.append(Finding(Severity.ERROR, "SCOPE_CONDITIONS_MISSING",
                                "A scoped switch needs at least one condition (parent property, region, ...).",
                                basis=Q2))
    elif chosen is SwitchScope.UNCONDITIONAL and conditions:
        findings.append(Finding(Severity.ERROR, "SCOPE_CONDITIONS_UNEXPECTED",
                                "Conditions were given but the switch is marked unconditional.", basis=Q2))

    if every_article_accepts_every_value is None:
        findings.append(Finding(Severity.ERROR, "VALUES_UNANSWERED",
                                "Answer whether every listed article accepts every property value.", basis=Q3))
    elif every_article_accepts_every_value is False:
        findings.append(Finding(
            Severity.INFO, "VALUE_EXCEPTIONS_RECORDED",
            "Exceptions exist: the template continues with Step 4a (value by value), which is not "
            "implemented yet. Only the answer is recorded.", basis=Q3))
    return findings, unique, chosen, conditions
