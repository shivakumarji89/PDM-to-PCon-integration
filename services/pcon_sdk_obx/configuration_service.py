"""Build and validate a generation plan from the user's property choices.

The plan never pre-computes combinations. It only tells the plugin which
properties to enumerate (``vary``), which to pin (``fixed``) and which to
leave at pCon's default. The plugin walks pCon's live ``ValueSet`` after each
``SetValue`` so dependent properties and OFML relations are respected by the
product data itself, never approximated here.
"""
from __future__ import annotations

from dataclasses import dataclass

from services.pcon_sdk_obx.protocol import (
    MODE_DEFAULT,
    MODE_FIXED,
    MODE_VARY,
    ArticleProperty,
    ArticleSelection,
    CatalogArticle,
    CatalogPackage,
    GenerationPlan,
    PropertyRule,
)


class PlanValidationError(ValueError):
    """The requested plan cannot be sent to the plugin as-is."""


@dataclass(frozen=True)
class PropertyEstimate:
    """Upper bound of configurations if every varied property were independent."""

    varied: int
    upper_bound: int


class PconConfigurationService:
    """Pure helper: no SDK calls, no I/O."""

    MAX_CONFIGURATIONS_LIMIT = 20000

    @staticmethod
    def selectable_properties(properties: list[ArticleProperty]) -> list[ArticleProperty]:
        """Properties the user may vary or pin: visible, editable choice lists."""
        return [
            p for p in properties
            if p.is_choice and p.choices and p.editable and not p.hidden
        ]

    @classmethod
    def estimate(cls, properties: list[ArticleProperty], rules: tuple[PropertyRule, ...],
                 vary_all: bool = True) -> PropertyEstimate:
        """Upper bound = product of the *initial* value-set sizes of varied properties.

        It is only a ceiling for the search: pCon withdraws values as relations
        apply, so the real count is usually far lower, and properties that only
        appear after a choice are not known yet. It is still the right number
        to show before starting a run.
        """
        by_key = {p.key: p for p in properties}
        varied = 0
        bound = 1
        if vary_all:
            excluded = {r.key for r in rules if r.mode != MODE_VARY}
            keys = [p.key for p in cls.selectable_properties(properties) if p.key not in excluded]
        else:
            keys = [r.key for r in rules if r.mode == MODE_VARY]
        for key in keys:
            prop = by_key.get(key)
            count = len(prop.choices) if prop is not None else 1
            varied += 1
            bound *= max(1, count)
        return PropertyEstimate(varied=varied, upper_bound=bound)

    def build_plan(self, *, package: CatalogPackage, series_id: str,
                   articles: list[CatalogArticle], properties: list[ArticleProperty],
                   rules: list[PropertyRule], output_path: str,
                   max_configurations: int = 500, discard_unsaved_planning: bool = False,
                   price_date: str = "", vary_all: bool = True,
                   deduplicate: bool = True) -> GenerationPlan:
        if not articles:
            raise PlanValidationError("Select at least one base article.")
        if not output_path.strip():
            raise PlanValidationError("Choose an output OBX file.")
        if not output_path.lower().endswith(".obx"):
            raise PlanValidationError("The output file must use the .obx extension.")
        if max_configurations <= 0 or max_configurations > self.MAX_CONFIGURATIONS_LIMIT:
            raise PlanValidationError(
                f"Maximum configurations must be between 1 and {self.MAX_CONFIGURATIONS_LIMIT}."
            )
        if series_id and series_id not in package.program_ids:
            raise PlanValidationError(
                f"Series {series_id!r} is not one of the package programs {list(package.program_ids)}."
            )

        by_key = {p.key: p for p in properties}
        cleaned: list[PropertyRule] = []
        seen: set[str] = set()
        for rule in rules:
            if rule.key in seen:
                raise PlanValidationError(f"Property {rule.key!r} is listed twice.")
            seen.add(rule.key)
            if rule.mode == MODE_DEFAULT and not vary_all:
                continue  # explicit mode: "default" rows carry no instruction
            prop = by_key.get(rule.key)
            if prop is None:
                raise PlanValidationError(f"Property {rule.key!r} is not part of the inspected article.")
            if rule.mode == MODE_FIXED and prop.choices and rule.value_key not in {c.key for c in prop.choices}:
                raise PlanValidationError(
                    f"Value {rule.value_key!r} is not currently offered for {prop.name or prop.key}. "
                    "Dependent properties may hide it; inspect the article again."
                )
            cleaned.append(rule)
        return GenerationPlan(
            manufacturer_id=package.manufacturer_id,
            series_id=series_id,
            catalog_package=package.package_name,
            articles=tuple(
                ArticleSelection(a.article_number, a.variant_code, a.package_name) for a in articles
            ),
            rules=tuple(cleaned),
            output_path=output_path,
            max_configurations=int(max_configurations),
            discard_unsaved_planning=bool(discard_unsaved_planning),
            price_date=price_date,
            vary_all=bool(vary_all),
            deduplicate=bool(deduplicate),
        )


__all__ = ["PconConfigurationService", "PlanValidationError", "PropertyEstimate",
           "MODE_DEFAULT", "MODE_FIXED", "MODE_VARY"]
