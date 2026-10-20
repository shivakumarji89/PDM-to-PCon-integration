"""Complete in-memory plan for creating one polymorphic property (template Step 6 onward). Never writes.

Rows produced, all from explicit inputs (nothing is invented; every unresolved decision is a *blocker* that keeps
the plan from being ``ok``):

* ``go_types``      one row ``owner;property;ch;default;mode;filter`` (format/default/filter: ``property_rules``;
                    mode: ``encode_mode`` - blocked until the mode policy is confirmed, decision D4).
* ``go_properties`` one row per article ``owner;ConfigID;property;value;;`` from the explicit per-article values
                    (decision D2); the ConfigID is the article's existing prm_key, never inferred.
* ``go_propvalues`` rows ``owner;property;value;condition`` only from explicit conditions. When Step 4a recorded
                    exceptions and no condition was given the plan is blocked: the condition is a BoolExpr over other
                    property values and is not derivable from the interview.
* ``go_proporder``  rows ``value;number`` only from explicit numbers (1..255, ``uint8``); if given they must cover every value.
* ``go_texts``      rows ``key;language;text`` from the confirmed Step 5 translations (property label + each value),
                    language-major (all ``en`` rows, then ``de``, ``fr``, ``nl``, as the real files are laid out).
                    Non-ASCII text in an empty/ASCII-only file is blocked until an encoding is chosen (D5).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from models.metatype_articles import ArticleReconciliation
from models.metatype_creation import Translations
from services.metatype.article_write_plan import ArticleWritePlan
from services.metatype.property_rules import (
    ArticleValueTable, ModeDecision, ModePolicy, PropertyFormat, build_property_format, encode_mode,
)
from services.metatype.table_append import LANGUAGES, plan_append, validate_row
from services.metatype.text_encoding import Encoding

TABLE_ORDER = ("go_types", "go_properties", "go_propvalues", "go_proporder", "go_texts")


@dataclass
class CreationInputs:
    owner: str | None
    property_name: str
    values: list[str]
    default: str
    filter_names: str = ""
    article_values: ArticleValueTable | None = None
    mode_policy: ModePolicy = field(default_factory=ModePolicy)
    order: dict[str, int] = field(default_factory=dict)             # explicit sort numbers per value (optional)
    conditions: dict[str, str] = field(default_factory=dict)        # explicit go_propvalues condition per value
    exceptions_recorded: bool = False                               # Step 4a: some article does not accept all values
    translations: Translations | None = None
    text_fallback_encoding: Encoding | None = None                  # owner decision D5; None = undecided


@dataclass
class CreationPlan:
    plan: ArticleWritePlan
    mode: ModeDecision | None = None
    format: PropertyFormat | None = None
    blockers: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.blockers and self.plan.ok

    def review_text(self) -> str:
        head = [f"Property creation plan for {self.plan.series} (computed in memory; NOTHING has been written):"]
        head += [f"  BLOCKED: {b}" for b in self.blockers]
        return "\n".join(head) + "\n" + self.plan.review_text()


def plan_property_creation(result: ArticleReconciliation | None, inputs: CreationInputs) -> CreationPlan:
    plan = ArticleWritePlan(result.series if result is not None else "")
    out = CreationPlan(plan)
    blockers = out.blockers
    if result is None or result.status.value == "failed" or result.loader_result is None:
        blockers.append("No usable series data is loaded.")
        return out
    loaded = result.loader_result
    name = inputs.property_name.strip(" \t")
    if not name:
        blockers.append("The property name (Step 3) is missing.")
    if not inputs.owner:
        blockers.append("The owner Metatype is not resolved (choose it explicitly when ambiguous).")
    elif inputs.owner not in result.references.get("metatype_ids", frozenset()):
        blockers.append(f"{inputs.owner} owns no go_types rows in this series (or go_types was not read).")
    values = [v.strip(" \t") for v in inputs.values if v.strip(" \t")]
    out.format = build_property_format(values, inputs.default, inputs.filter_names)
    blockers.extend(out.format.problems)
    values_ok = not out.format.problems

    table = inputs.article_values
    if table is None:
        blockers.append("No per-article values were entered (decision D2: every article's value is explicit).")
    else:
        if table.allowed_values != values:
            blockers.append("The per-article value table was built for a different value list.")
        blockers.extend(table.problems())
        column = result.roles.get("metatypeid")
        for article in table.articles:
            owners = {r.values.get(column, "").strip(" \t") for r in result.rows
                      if r.identity is not None and r.identity[2] == article} if column else set()
            if inputs.owner and owners != {inputs.owner}:
                blockers.append(f"{article} belongs to {', '.join(sorted(owners)) or 'no Metatype'}, not to the owner "
                                f"{inputs.owner}.")

    for value, number in inputs.order.items():
        blockers.extend(validate_row("go_proporder", [value, str(number)]))
        if value not in values:
            blockers.append(f"A sort number was given for {value!r}, which is not a value of the property.")
    if inputs.order and set(values) - set(inputs.order) and values_ok:
        blockers.append("Sort numbers must cover every value: " + ", ".join(sorted(set(values) - set(inputs.order))) + ".")
    for value in inputs.conditions:
        if value not in values:
            blockers.append(f"A condition was given for {value!r}, which is not a value of the property.")
    if inputs.exceptions_recorded and not inputs.conditions:
        blockers.append("Step 4a recorded per-article exceptions, but no go_propvalues condition was supplied; the "
                        "condition (a BoolExpr over other property values) cannot be derived from the interview.")
    out.mode = encode_mode(inputs.mode_policy, bool(inputs.order), bool(inputs.conditions))
    blockers.extend(out.mode.problems)

    texts = _text_rows(inputs, values, blockers)
    if blockers:
        return out

    owner = inputs.owner
    rows: dict[str, list[list[str]]] = {
        "go_types": [[owner, name, out.format.format, out.format.default, str(out.mode.mode), out.format.filter]],
        "go_properties": _property_rows(owner, name, table),
        "go_propvalues": [[owner, name, v, c] for v, c in inputs.conditions.items()],
        "go_proporder": [[v, str(n)] for v, n in inputs.order.items()],
        "go_texts": texts,
    }
    for table_name in TABLE_ORDER:
        if not rows[table_name]:
            continue
        file_plan = plan_append(table_name, loaded.table(table_name), rows[table_name],
                                fallback=inputs.text_fallback_encoding)
        plan.files.append(file_plan)
        plan.problems.extend(file_plan.problems)
    if len({f.path for f in plan.files}) != len(plan.files):
        plan.problems.append("Two tables map to the same file.")
    return out


def _property_rows(owner: str, name: str, table: ArticleValueTable) -> list[list[str]]:
    seen: dict[str, str] = {}
    rows: list[list[str]] = []
    for article in table.articles:
        config = table.config_ids[article].strip(" \t")
        if config not in seen:
            seen[config] = table.assigned[article]
            rows.append([owner, config, name, table.assigned[article], "", ""])
    return rows


def _text_rows(inputs: CreationInputs, values: list[str], blockers: list[str]) -> list[list[str]]:
    tr = inputs.translations
    if tr is None:
        blockers.append("The Step 5 translations are not confirmed.")
        return []
    by_key = {r.technical.strip(" \t"): r for r in tr.rows}
    wanted = [inputs.property_name.strip(" \t"), *values]
    missing = [k for k in wanted if k not in by_key]
    if missing:
        blockers.append("Translations are missing for: " + ", ".join(missing) + ".")
        return []
    rows: list[list[str]] = []
    for language in LANGUAGES:
        for key in wanted:
            text = getattr(by_key[key], language).strip(" \t")
            if not text:
                blockers.append(f"{key}: the {language} text is empty.")
            rows.append([key, language, text])
    return rows
