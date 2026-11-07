"""Standalone valid-SKU generation over one OCD repository folder (``<range>/<region>/<version>/db``).

Pure orchestration of the existing engine pieces - no snapshot, no PDM, no pCon plugin:

    OcdCsvLoader (CSV + ``pdata.*.inp_descr`` schemas)  -> OcdDataset
    build_article_model                                  -> ArticleModel
    ConfigurationEngine.enumerate / finalize             -> valid configurations
    CodeSchemeEncoder                                    -> final article number
    PriceCalculator                                      -> price (needs currency + date)
    ofml_varcode                                         -> OBX ``ofmlvarcode``

User choices are limited to *vary* (default), *fixed* (one value) and *default* (the value
flagged ``is_default``). Pinning restricts a property's value list; relations and conditions
are still evaluated by the engine, never approximated here.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping, Sequence

from services.ocd_engine import diagnostics as dg
from services.ocd_engine import fabric
from services.ocd_engine import model as m
from services.ocd_engine.catalogue import texts_by_number
from services.ocd_engine.codescheme_engine import CodeSchemeEncoder
from services.ocd_engine.configuration_engine import ConfigurationEngine, EnumerationLimits
from services.ocd_engine.csv_loader import OcdCsvLoader, OcdDataset, build_article_model
from services.ocd_engine.obx_serialization import ofml_varcode
from services.ocd_engine.pricing import PriceCalculator, PriceResult, PriceRow, ymd
from services.ocd_engine.resolved import ResolvedConfiguration
from services.ocd_engine.structure import ArticleStructure, trace_article

MODE_VARY = "vary"
MODE_FIXED = "fixed"
MODE_DEFAULT = "default"

#: Safety net against runaway enumeration; reaching it is reported, never silent.
MAX_NODES = 5_000_000

_RELATION_TYPES = {
    m.PRECONDITION: "precondition", m.SELECTION: "selection condition", m.ACTION: "action",
    m.CONSTRAINT: "constraint", m.REACTION: "reaction", m.POST_REACTION: "post-reaction",
}
_REQUIRED_TABLES = ("article", "property", "propertyvalue")


class GenerationError(Exception):
    """The repository or the request cannot be processed; the message is shown to the user."""


@dataclass(frozen=True)
class PropertyRule:
    key: str                          # PropertyInfo.key (``Class:Property``)
    mode: str = MODE_VARY
    value: str = ""                   # the OCD ``value_from`` for MODE_FIXED


@dataclass(frozen=True)
class PropertyChoice:
    name: str
    label: str = ""
    candidate: bool = False        # the fabric/upholstery keyword search finds it (name or any language text)

    @property
    def display(self) -> str:
        return f"{self.name} - {self.label}" if self.label and self.label != self.name else self.name


@dataclass(frozen=True)
class RelationInfo:
    name: str
    kind: str                         # precondition, constraint, ...
    domain: str
    text: str


@dataclass(frozen=True)
class ValueInfo:
    value: str
    label: str = ""
    is_default: bool = False
    relations: tuple[RelationInfo, ...] = ()


@dataclass(frozen=True)
class PropertyInfo:
    key: str
    class_name: str
    name: str
    label: str
    scope: str
    values: tuple[ValueInfo, ...]
    relations: tuple[RelationInfo, ...] = ()
    restricted: bool = False          # values limited by the article's ArtBase

    @property
    def default_value(self) -> str | None:
        return next((v.value for v in self.values if v.is_default), None)


@dataclass(frozen=True)
class ArticleDescription:
    article_number: str
    label: str
    scheme_id: str
    properties: tuple[PropertyInfo, ...]
    relations: tuple[RelationInfo, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class GeneratedSku:
    index: int
    base_article: str
    series_id: str
    final_article: str
    variant_code: str
    ofml_varcode: str
    configuration_text: str
    label: str = ""
    values: tuple[tuple[str, str, str, str], ...] = ()      # (class, property, value, code)
    varconds: tuple[str, ...] = ()
    pricing_factors: tuple[tuple[str, float], ...] = ()
    scheme_id: str = ""
    price: Decimal | None = None
    currency: str = ""
    status: str = "ok"                                      # "ok" | "unpriced"
    message: str = ""


@dataclass
class GenerationOutcome:
    skus: list[GeneratedSku] = field(default_factory=list)
    nodes: int = 0
    pruned: int = 0
    invalid: int = 0                  # complete configurations rejected by the final relation check
    duplicates: int = 0               # valid configurations whose final article was already produced
    price_evaluations: int = 0        # distinct price keys looked up in the price table
    price_reused: int = 0             # SKUs priced from an earlier lookup with the same price key
    configurations: int = 0           # complete configurations the engine produced (before validation/dedup)
    inert_properties: tuple[str, ...] = ()   # read-only properties enumerated with one value only
    #: price-relation work: configurations finalised, relations actually executed, and the result-cache counters
    price_relation_stats: dict[str, int] = field(default_factory=dict)
    truncated: bool = False
    warnings: list[str] = field(default_factory=list)
    #: one line per fabric colour decision (selected type, mechanism, candidates, rejections, chosen colour and why)
    fabric_notes: list[str] = field(default_factory=list)

    @property
    def exportable(self) -> list[GeneratedSku]:
        return [s for s in self.skus if s.price is not None]

    @property
    def unpriced(self) -> int:
        return sum(1 for s in self.skus if s.price is None)


def _relation_infos(relations) -> tuple[RelationInfo, ...]:
    return tuple(RelationInfo(r.name, _RELATION_TYPES.get(r.rel_type, str(r.rel_type)), r.domain, r.text)
                 for r in relations)


def price_key(article_number: str, varconds: Sequence[str], factors: Mapping[str, float]) -> tuple:
    """Everything a price lookup reads from a configuration, normalised exactly as ``PriceCalculator.price`` does.

    The price is a function of the article, the variant conditions its price relations assigned and their
    factors; the date, currency, type and quantity are fixed for one generation. Configurations that differ
    only in values the price relations do not read (e.g. a colour) share this key, so their price is looked up
    once. The key comes from the evaluated relations, never from property or value names.
    """
    return ResolvedConfiguration.of(article_number, varconds, factors).price_key


def configuration_text(assignments) -> str:
    return "; ".join(f"{a.prop.name}={a.value.value}" for a in assignments
                     if a.value is not None and not a.hidden)


class OcdArticleGenerator:
    """One repository folder: describe articles, enumerate valid SKUs, price them."""

    def __init__(self, db_dir: str | Path, *, loader: OcdCsvLoader | None = None) -> None:
        self.db_dir = Path(db_dir)
        self._loader = loader or OcdCsvLoader()
        self._dataset: OcdDataset | None = None
        self._calculator: PriceCalculator | None = None
        self._texts: dict[str, dict[str, str]] = {}

    # ------------------------------------------------------------------ data
    @property
    def dataset(self) -> OcdDataset:
        if self._dataset is None:
            if not self.db_dir.is_dir():
                raise GenerationError(f"OCD data folder not found: {self.db_dir}")
            try:
                dataset = self._loader.load(self.db_dir)
                dataset._index()
            except (OSError, UnicodeDecodeError, ValueError, KeyError) as exc:
                raise GenerationError(f"Cannot read the OCD data in {self.db_dir}: {exc}") from exc
            missing = [t for t in _REQUIRED_TABLES if t not in dataset.tables]
            if missing:
                raise GenerationError(
                    f"{self.db_dir} has no data for table(s): {', '.join('ocd_' + t for t in missing)}.")
            self._dataset = dataset
        return self._dataset

    def _text(self, table: str, number: str) -> str:
        if table not in self._texts:
            self._texts[table] = texts_by_number(self.dataset.tables.get(table, []))
        return self._texts[table].get((number or "").strip(), "")

    def currencies(self) -> list[str]:
        """Currencies that occur in the price table, sorted."""
        return sorted({(r.get("currency") or "").strip().upper()
                       for r in self.dataset.tables.get("price", [])} - {""})

    def price_diagnostics(self, article_number: str, *, varconds: Sequence[str] = (), currency: str = "",
                          price_date: str, factors: Mapping[str, float] | None = None) -> list[str]:
        """Compact account of why an article/configuration does or does not get a price.

        Names the repository folder and price file, what the table holds for the article (types,
        currencies, date windows), the variant-condition keys the lookup uses, and for every key the
        candidate rows before and after each filter. Never lists the table itself.
        """
        currency = self.resolve_currency(currency)
        if not ymd(price_date):
            raise GenerationError("A price date is required.")
        calculator = self._price_calculator()
        rows = self.dataset.tables.get("price", [])
        price_file = self.db_dir / "ocd_price.csv"
        header = [f"repository folder: {self.db_dir}",
                  f"price table: {price_file if price_file.is_file() else '(no ocd_price.csv)'}, {len(rows)} row(s) loaded"]
        diagnosis = calculator.diagnose(article_number, varconds, price_date=price_date, currency=currency)
        priced = calculator.price(article_number, varconds, price_date=price_date, currency=currency,
                                   factors=dict(factors or {}))
        verdict = (f"result: {priced.total} {currency}" if priced.total is not None else
                   "result: unpriced - " + next((d.message for d in priced.diagnostics
                                                 if d.severity is dg.Severity.ERROR), "no price could be resolved"))
        notes = [d.message for d in priced.diagnostics if d.code == dg.PRICE_FROM_EXTRA_CHARGES]
        return header + diagnosis.lines() + notes + [verdict]

    def _build_model(self, article_number: str) -> m.ArticleModel:
        try:
            model = build_article_model(self.dataset, article_number)
        except (ValueError, KeyError) as exc:
            raise GenerationError(f"Malformed OCD data for article {article_number}: {exc}") from exc
        if model is None:
            raise GenerationError(f"Article {article_number} is not in {self.db_dir}.")
        return model

    # -------------------------------------------------------------- inspection
    def structure(self, article_number: str) -> ArticleStructure:
        """Base article -> encoding -> classes -> properties -> values, without enumerating."""
        self.dataset
        found = trace_article(self._dataset, article_number)
        if found is None:
            raise GenerationError(f"Article {article_number} is not in {self.db_dir}.")
        return found

    def describe(self, article_number: str) -> ArticleDescription:
        model = self._build_model(article_number)
        dataset = self.dataset
        article = dataset.articles[article_number]
        defaults = {
            (r["prop_class"], r["property"], r["value_from"]): r.get("is_default", "").strip() == "1"
            for rows in dataset.values.values() for r in rows
        }
        label_rows = {(r["prop_class"], r["property"]): r["prop_textnr"]
                      for rows in dataset.properties.values() for r in rows}
        value_text = {(r["prop_class"], r["property"], r["value_from"]): r.get("pval_textnr", "")
                      for rows in dataset.values.values() for r in rows}
        properties = []
        for prop in model.properties:
            allowed = prop.allowed_keys
            values = tuple(
                ValueInfo(
                    value=v.value,
                    label=self._text("propvaluetext", value_text.get((prop.class_name, prop.name, v.value), "")),
                    is_default=defaults.get((prop.class_name, prop.name, v.value), False),
                    relations=_relation_infos(v.relations),
                )
                for v in prop.values if allowed is None or v.key in allowed
            )
            properties.append(PropertyInfo(
                key=prop.key, class_name=prop.class_name, name=prop.name,
                label=self._text("propertytext", label_rows.get((prop.class_name, prop.name), "")),
                scope=prop.scope, values=values, relations=_relation_infos(prop.relations),
                restricted=allowed is not None,
            ))
        notes = tuple(str(d) for d in dataset.sink if d.article in ("", article_number)
                      and d.severity is not dg.Severity.INFO)
        return ArticleDescription(
            article_number=article_number, label=self._text("artshorttext", article.get("short_textnr", "")),
            scheme_id=model.scheme_id, properties=tuple(properties),
            relations=_relation_infos(model.article_relations), warnings=notes,
        )

    @staticmethod
    def estimate(properties: Sequence[PropertyInfo], rules: Sequence[PropertyRule] = ()) -> tuple[int, int]:
        """``(varied properties, naive upper bound)``: product of the value counts of varied properties."""
        pinned = {r.key for r in rules if r.mode != MODE_VARY}
        varied, bound = 0, 1
        for prop in properties:
            if prop.key in pinned or not prop.values:
                continue
            varied += 1
            bound *= len(prop.values)
        return varied, bound

    def fabric_property_choices(self, article_numbers: Sequence[str]) -> list["PropertyChoice"]:
        """Properties of the given articles for the one manual fabric-property selector.

        Read from the loaded tables only (no model is built): every property of the articles' classes that has
        values, once per name, with its Property-text label (preferred language) and whether the keyword search
        already finds it. Nothing here decides a property's role."""
        dataset = self.dataset
        seen: dict[str, PropertyChoice] = {}
        for number in article_numbers:
            for class_row in sorted(dataset.classes.get(number, []), key=lambda r: int(r["pos_class"] or 0)):
                for row in sorted(dataset.properties.get(class_row["prop_class"], []),
                                  key=lambda r: int(r["pos_prop"] or 0)):
                    name = row["property"]
                    if name.upper() in {k.upper() for k in seen} or not dataset.values.get((class_row["prop_class"], name)):
                        continue
                    labels = dataset.property_labels.get((row.get("prop_textnr") or "").strip(), ())
                    probe = m.PropertyDef(key=name, name=name, labels=tuple(labels))
                    seen[name] = PropertyChoice(name, self._text("propertytext", row.get("prop_textnr", "")),
                                                fabric.is_candidate(probe))
        return list(seen.values())

    # ---------------------------------------------------------------- generation
    def _apply_rules(self, model: m.ArticleModel, rules: Sequence[PropertyRule], warnings: list[str]):
        """``(restricted model, keys of the pinned properties)``."""
        by_key = {r.key: r for r in rules if r.mode != MODE_VARY}
        if not by_key:
            return model, frozenset()
        known = {p.key for p in model.properties}
        for key in by_key.keys() - known:
            warnings.append(f"{model.base_code}: property {key} is not offered by this article; rule skipped.")
        properties, pinned = [], set()
        for prop in model.properties:
            rule = by_key.get(prop.key)
            if rule is None:
                properties.append(prop)
                continue
            allowed = [v for v in prop.values if prop.allowed_keys is None or v.key in prop.allowed_keys]
            if rule.mode == MODE_FIXED:
                wanted = rule.value
            elif rule.mode == MODE_DEFAULT:
                wanted = self._default_value(prop)
                if wanted is None:
                    warnings.append(f"{model.base_code}: {prop.name} has no default value; it is varied.")
                    properties.append(prop)
                    continue
            else:
                raise GenerationError(f"Unknown rule mode {rule.mode!r} for {rule.key}.")
            kept = tuple(v for v in allowed if v.value == wanted)
            if not kept:
                raise GenerationError(
                    f"Value {wanted!r} is not offered for {prop.name} of article {model.base_code}.")
            properties.append(dataclasses.replace(prop, values=kept))
            pinned.add(prop.key)
        return dataclasses.replace(model, properties=tuple(properties)), frozenset(pinned)

    def _default_value(self, prop: m.PropertyDef) -> str | None:
        for row in self.dataset.values.get((prop.class_name, prop.name), []):
            if row.get("is_default", "").strip() == "1" and row["op_from"].upper() == "EQ":
                return row["value_from"]
        return None

    def _price_calculator(self) -> PriceCalculator:
        if self._calculator is None:
            try:
                self._calculator = PriceCalculator(
                    [PriceRow.from_csv(r) for r in self.dataset.tables.get("price", [])])
            except (InvalidOperation, ValueError, KeyError) as exc:
                raise GenerationError(f"Malformed price table in {self.db_dir}: {exc}") from exc
        return self._calculator

    def resolve_currency(self, currency: str) -> str:
        currency = (currency or "").strip().upper()
        if currency:
            return currency
        available = self.currencies()
        if len(available) == 1:
            return available[0]
        raise GenerationError(
            "Choose a currency" + (f" ({', '.join(available)})." if available else "; the repository has no prices."))

    def generate(self, article_numbers: Sequence[str], rules: Sequence[PropertyRule] = (), *,
                 currency: str = "", price_date: str,
                 max_configurations: None = None, fabric_default_only: bool = True, fabric_property: str = "",
                 shared_fabric: bool = False, reporter=None, price_relation_cache: bool = True,
                 price_cache_verify_every: int = 0) -> GenerationOutcome:
        """Every valid, unique SKU of ``article_numbers``; ``OperationCancelled`` propagates on cancel.

        ``fabric_property`` is the one optional manual choice (a property name, ``""`` = automatic discovery): it feeds
        the same resolver, and a choice that cannot be resolved raises :class:`GenerationError` before anything is
        enumerated, so every colour is never silently expanded.

        ``shared_fabric`` (default off - Betwixt has identical Back/Seat type lists and is generated independently): fabric positions that offer the same fabric types (e.g. Back/Arms and Seat) are
        one choice - every configuration carries the same type and colour in each of them (see
        :class:`~services.ocd_engine.configuration_engine.ConfigurationEngine`). ``False`` enumerates each position
        independently (the default).

        ``price_relation_cache`` (default on) memoises the price-relation run per distinct relation input within
        this call; ``False`` evaluates every relation for every configuration as before. The SKUs, prices and
        diagnostics are identical either way. ``price_cache_verify_every`` is for benchmarking (see
        :class:`~services.ocd_engine.varcond_engine.VarcondEngine`).

        There is no SKU cap: ``max_configurations`` exists so callers state "unlimited" explicitly and
        anything but ``None`` is refused rather than silently ignored.
        """
        if max_configurations is not None:
            raise GenerationError("SKU generation is not capped; max_configurations must be None.")
        if not article_numbers:
            raise GenerationError("Select at least one article.")
        if not ymd(price_date):
            raise GenerationError("A price date is required.")
        currency = self.resolve_currency(currency)
        calculator = self._price_calculator()
        dataset = self.dataset
        outcome = GenerationOutcome()
        seen: dict[str, tuple] = {}        # final article -> price key of the configuration that produced it
        priced_by_key: dict[tuple, PriceResult] = {}
        conflicting: set[str] = set()
        sink = dg.DiagnosticSink()

        for article_number in article_numbers:
            if reporter is not None:
                reporter.note(f"Enumerating {article_number}")
            full_model = self._build_model(article_number)
            # Ties come from the unrestricted model: a pin narrows the type lists and must not switch a tie off.
            analysis = (fabric.analyse_shared_fabric(full_model, fabric.discover(full_model, fabric_property).schemes)
                        if shared_fabric else fabric.SharedFabricAnalysis())
            ties = analysis.ties
            model, pinned = self._apply_rules(full_model, rules, outcome.warnings)
            scheme = dataset.code_scheme(model.scheme_id)
            encoder = CodeSchemeEncoder(scheme) if scheme is not None else None
            if encoder is None:
                outcome.warnings.append(
                    f"{article_number}: no code scheme ({model.scheme_id or 'none'}); the base number is the final number.")
            identity = None if scheme is not None and scheme.is_predefined else                 ([scheme.scheme] if scheme is not None else [])
            engine = ConfigurationEngine(
                model, sink=sink, limits=EnumerationLimits(max_nodes=MAX_NODES), identity_texts=identity,
                fabric_default_only=fabric_default_only, fabric_property=fabric_property,
                shared_fabric=shared_fabric, fabric_ties=ties, fabric_tie_skips=analysis.skipped,
                price_relation_cache=price_relation_cache, price_cache_verify_every=price_cache_verify_every,
                progress=(lambda st, a=article_number: reporter.note(
                    f"Enumerating {a}: {st.emitted:,} configuration(s), {st.nodes:,} node(s) evaluated, "
                    f"{len(outcome.skus):,} valid SKU(s)")) if reporter is not None else None)
            if engine.fabric_override_error:
                raise GenerationError(f"Fabric property {fabric_property!r} for {article_number}: "
                                      f"{engine.fabric_override_error}. Choose another property or Automatic.")
            if fabric_property and fabric_default_only and engine._fabric.override_missing:
                outcome.warnings.append(f"{article_number}: {engine._fabric.override_error}; automatic fabric "
                                        f"discovery was used.")
            series = (dataset.articles[article_number].get("series") or "").strip()
            label = self._text("artshorttext", dataset.articles[article_number].get("short_textnr", ""))
            produced = 0
            for config in engine.enumerate():
                if any(a.value is None and not a.hidden for a in config.assignments if a.prop.key in pinned):
                    # The pinned value is excluded by the relations here; the engine would leave the
                    # property unassigned, which is not the configuration the user asked for.
                    outcome.invalid += 1
                    continue
                result = engine.finalize(config.assignments)
                if not result.valid:
                    outcome.invalid += 1
                    continue
                if encoder is not None:
                    encoded = encoder.encode(article_number, engine.view(config.assignments, result.computed),
                                             sink, article_number)
                    if encoded is None:
                        outcome.invalid += 1
                        continue
                    final, variant = encoded.final_article, encoded.variant_code
                else:
                    final, variant = article_number, ""
                resolved = ResolvedConfiguration.of(article_number, result.varconds, result.pricing_factors)
                key = resolved.price_key
                if final in seen:
                    outcome.duplicates += 1
                    if seen[final] != key and final not in conflicting:
                        # One number, two price states: the kept SKU's price is not the other's.
                        conflicting.add(final)
                        outcome.warnings.append(
                            f"{final}: configurations that share this final article have different price "
                            f"conditions ({seen[final][1]} vs {key[1]}); the first one is kept.")
                    continue
                seen[final] = key
                priced = priced_by_key.get(key)
                if priced is None:
                    priced = priced_by_key[key] = calculator.price_resolved(
                        resolved, price_date=price_date, currency=currency)
                    outcome.price_evaluations += 1
                else:
                    outcome.price_reused += 1
                outcome.skus.append(self._sku(
                    len(outcome.skus) + 1, article_number, series, label, final, variant, model, config, result,
                    priced))
                produced += 1
                if reporter is not None and produced % 500 == 0:
                    reporter.note(f"Enumerating {article_number}: {engine.stats.emitted:,} configuration(s), "
                                  f"{produced:,} valid SKU(s)")
            outcome.fabric_notes.extend(f"{article_number}: {r.describe()}"
                                        for r in engine.fabric_resolutions.values() if r.selected)
            outcome.fabric_notes.extend(f"{article_number}: {tie.describe()}" for tie in engine.fabric_ties)
            outcome.fabric_notes.extend(f"{article_number}: {skip.describe()}" for skip in engine.fabric_tie_skips)
            outcome.nodes += engine.stats.nodes
            for name, count in engine.price_relation_stats.items():
                outcome.price_relation_stats[name] = outcome.price_relation_stats.get(name, 0) + count
            outcome.configurations += engine.stats.emitted
            outcome.inert_properties = tuple(dict.fromkeys(outcome.inert_properties + engine.stats.inert))
            outcome.pruned += engine.stats.pruned
            if engine.stats.truncated:
                outcome.truncated = True
                outcome.warnings.append(f"{article_number}: {engine.stats.reason}; the result is incomplete.")
            if reporter is not None:
                reporter.advance(f"{article_number}: {produced} valid SKU(s)")
        outcome.warnings.extend(str(d) for d in sink if d.severity is not dg.Severity.INFO
                                and d.code != dg.ENUMERATION_TRUNCATED)
        if outcome.unpriced:
            outcome.warnings.append(
                f"{outcome.unpriced} SKU(s) have no price in {currency} on {price_date}; they are not exported.")
        return outcome

    @staticmethod
    def _sku(index, article_number, series, label, final, variant, model, config, result,
             priced: PriceResult) -> GeneratedSku:
        message = ""
        if priced.total is None:
            reasons = [d.message for d in priced.diagnostics if d.severity is dg.Severity.ERROR]
            message = reasons[0] if reasons else "price could not be resolved"
        by_key = {a.prop.key: a for a in config.assignments}
        values = tuple(
            (a.prop.class_name, a.prop.name, a.value.value, a.value.encoded)
            for a in (by_key.get(p.key) for p in model.properties)
            if a is not None and a.value is not None and not a.hidden and a.prop.scope.upper() == "C"
        )
        return GeneratedSku(
            index=index, base_article=article_number, series_id=series, final_article=final,
            variant_code=variant, ofml_varcode=ofml_varcode(config.assignments, model),
            configuration_text=configuration_text(config.assignments), label=label, values=values,
            varconds=tuple(dict.fromkeys(x for x in result.varconds if x)),
            pricing_factors=tuple(result.pricing_factors.items()), scheme_id=model.scheme_id,
            price=priced.total, currency=priced.currency, status="ok" if priced.total is not None else "unpriced",
            message=message,
        )


__all__ = [
    "ArticleDescription", "GeneratedSku", "GenerationError", "GenerationOutcome", "MAX_NODES", "MODE_DEFAULT",
    "MODE_FIXED", "MODE_VARY", "OcdArticleGenerator", "PropertyChoice", "PropertyInfo", "PropertyRule", "RelationInfo", "ValueInfo",
    "configuration_text",
]
