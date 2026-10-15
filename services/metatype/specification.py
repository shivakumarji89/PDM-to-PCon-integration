"""Template Step 6: the single-block summary shown before the user confirms.

The template lists what the block contains:

* Metatype type (Polymorphism / with Childs) - always Polymorphism here (the Childs branch does not exist yet);
* property name + EN/DE/FR/NL labels (Step 3 and Step 5);
* values (if any) + EN/DE/FR/NL labels (Step 4a values, Step 5 texts);
* article mapping (which article(s) per value / child);
* the per-article value validity / exceptions table from Step 4a, if any;
* any conditions/scoping noted in Step 4.

The Polymorphism branch has no child mapping and Step 4 lists the articles the property switches between, so
the article mapping is that list plus, per value, the Step 4a articles (``all`` for every article). Values
without a Step 4a row do not exist in this workflow.

Nothing is derived beyond what the user answered: no mode, table row, file name or output format. Pure and
filesystem-free; the text is deterministic so it can be compared to detect a changed specification.
"""
from __future__ import annotations

from models.metatype_creation import (
    PolymorphismBranch, PropertyIdentity, SwitchScope, TranslationRow, Translations, ValueValidity,
)

BASIS = "template Step 6 (confirmation before implementation)"


def _labels(row: TranslationRow) -> str:
    return f"EN: {row.en} | DE: {row.de} | FR: {row.fr} | NL: {row.nl}"


def build_summary(
    identity: PropertyIdentity, branch: PolymorphismBranch, validity: ValueValidity, translations: Translations,
) -> str:
    """Render the Step 6 block from the confirmed Step 3, 4, 4a and 5 answers."""
    prop, *values = translations.rows
    lines = [
        f"Specification for series {identity.series}",
        "",
        "Metatype type: Polymorphism",
        "",
        "Property name and labels:",
        f"  {prop.technical} - {_labels(prop)}",
        "",
        "Values and labels:",
    ]
    lines += [f"  {v.technical} - {_labels(v)}" for v in values] or ["  (none)"]

    lines += ["", "Article mapping:", f"  The property switches between: {', '.join(branch.articles)}"]
    rows = {r.value: r for r in validity.rows}
    for v in values:
        row = rows.get(v.technical)
        valid = "all articles" if row is None or row.all_articles else ", ".join(row.articles)
        lines.append(f"  Value {v.technical}: {valid}")
    if not values:
        lines.append("  (no values; every article accepts the full value set)")

    lines += ["", "Per-article value validity / exceptions (Step 4a):"]
    if validity.accepts_full_value_set:
        lines.append("  No exceptions: all articles accept the full value set.")
    else:
        lines += ["  | Value | Valid for article(s) |", "  |-------|----------------------|"]
        lines += [f"  | {r.value} | {'all' if r.all_articles else ', '.join(r.articles)} |" for r in validity.rows]

    lines += ["", "Conditions / scoping (Step 4):"]
    if branch.scope is SwitchScope.UNCONDITIONAL:
        lines.append("  The switch is unconditional.")
    else:
        lines.append("  The switch is scoped to:")
        lines += [f"  - {c}" for c in branch.scope_conditions]
    return "\n".join(lines)
