"""OBX export of SKUs generated straight from an OCD repository folder.

Adapter only: :class:`GeneratedSku` -> ``ArticlePermutation``/``ArticlePrice`` rows, serialized by the
existing ``ArticleObxService`` renderer (the same XML writer the repository Article OBX uses). The
file is then re-read with the QA ``ObxValidationService`` parser so success is judged on the file,
not on the generator's own counters.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from services.article_obx.article_obx_models import (
    ArticleConfigurationValue,
    ArticleObxResult,
    ArticleObxRow,
    ArticlePermutation,
    ArticlePrice,
)
from services.article_obx.article_obx_service import ArticleObxService
from services.article_obx.basket_contract import basket_problems
from services.obx_validation_service import ObxValidationService
from services.ocd_engine.generator import GeneratedSku


class ObxExportError(Exception):
    """The OBX file could not be written; the message is shown to the user."""


@dataclass
class ObxExportSummary:
    path: str
    exported: int = 0
    skipped_unpriced: int = 0
    article_lines: int = 0
    missing_final_articles: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


@dataclass
class ReferenceComparison:
    reference_lines: int = 0
    generated_lines: int = 0
    matched: list[str] = field(default_factory=list)
    missing_in_generated: list[str] = field(default_factory=list)
    extra_in_generated: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def identical(self) -> bool:
        return not self.problems and not self.missing_in_generated and not self.extra_in_generated


def _normalise(final: str) -> str:
    return " ".join(final.split()).upper()


def build_rows(skus: Sequence[GeneratedSku], price_date: str) -> list[ArticleObxRow]:
    """Priced SKUs as serializer rows; unpriced SKUs have no row (the serializer needs a price)."""
    rows = []
    for sku in skus:
        if sku.price is None:
            continue
        values = tuple(
            ArticleConfigurationValue(kind="property", entity_id=f"{cls}:{name}", value_id=f"{cls}:{name}:{value}",
                                      name=name, value=value, code=code, display_order=order)
            for order, (cls, name, value, code) in enumerate(sku.values)
        )
        permutation = ArticlePermutation(
            article_id=sku.base_article, product_id="", base_code=sku.base_article,
            final_article=sku.final_article, variant_code=sku.variant_code,
            variant_condition=" ".join(sku.varconds), variant_conditions=sku.varconds,
            pricing_factors=sku.pricing_factors, code_scheme_id=sku.scheme_id, name=sku.label,
            description=sku.label, properties=values, ofml_varcode=sku.ofml_varcode, series_id=sku.series_id,
        )
        price = ArticlePrice(
            article_id=sku.base_article, article_code=sku.final_article, currency=sku.currency,
            effective_date=price_date, site_id=1, total_price=float(sku.price),
        )
        rows.append(ArticleObxRow(permutation=permutation, price=price))
    return rows


def export_obx(skus: Sequence[GeneratedSku], path: str | Path, *, manufacturer_id: str,
               price_date: str, series_id: str = "") -> ObxExportSummary:
    """Write the OBX atomically (temp file, then replace) and validate what landed on disk."""
    target = Path(path)
    if target.suffix.lower() != ".obx":
        raise ObxExportError("The output file must use the .obx extension.")
    rows = build_rows(skus, price_date)
    summary = ObxExportSummary(path=str(target), exported=len(rows), skipped_unpriced=len(skus) - len(rows))
    if not rows:
        raise ObxExportError("There is no priced SKU to export.")
    xml = ArticleObxService(None).render(rows, manufacturer_id=manufacturer_id, series_id=series_id)
    temp = target.with_name(target.name + ".tmp")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        ArticleObxService.write(str(temp), ArticleObxResult(rows=rows, xml=xml))
        os.replace(temp, target)
    except OSError as exc:
        temp.unlink(missing_ok=True)
        raise ObxExportError(f"Cannot write {target}: {exc}") from exc

    try:
        _, lines = ObxValidationService(None).parse_obx(target.read_text(encoding="utf-8"))
    except (OSError, ET.ParseError) as exc:
        summary.problems.append(f"The written OBX could not be read back: {exc}")
        return summary
    summary.article_lines = len(lines)
    summary.problems += basket_problems(target.read_text(encoding="utf-8"))
    missing = Counter(_normalise(r.permutation.final_article) for r in rows) - \
        Counter(_normalise(line.final_article) for line in lines)
    summary.missing_final_articles = sorted(missing.elements())
    if summary.missing_final_articles:
        summary.problems.append(f"{len(summary.missing_final_articles)} article(s) are missing from the OBX.")
    if len(lines) != len(rows):
        summary.problems.append(f"The OBX holds {len(lines)} article line(s); {len(rows)} were expected.")
    return summary


def compare_with_reference(generated_path: str | Path, reference_path: str | Path) -> ReferenceComparison:
    """Final article numbers of the generated OBX against a reference OBX (e.g. one pCon produced)."""
    comparison = ReferenceComparison()
    parser = ObxValidationService(None)
    try:
        _, reference = parser.parse_obx(Path(reference_path).read_text(encoding="utf-8"))
        _, generated = parser.parse_obx(Path(generated_path).read_text(encoding="utf-8"))
    except (OSError, ET.ParseError) as exc:
        comparison.problems.append(f"Cannot compare OBX files: {exc}")
        return comparison
    wanted = Counter(_normalise(line.final_article) for line in reference)
    found = Counter(_normalise(line.final_article) for line in generated)
    comparison.reference_lines, comparison.generated_lines = len(reference), len(generated)
    comparison.matched = sorted((wanted & found).elements())
    comparison.missing_in_generated = sorted((wanted - found).elements())
    comparison.extra_in_generated = sorted((found - wanted).elements())
    return comparison


__all__ = ["ObxExportError", "ObxExportSummary", "ReferenceComparison", "build_rows", "compare_with_reference",
           "export_obx"]
