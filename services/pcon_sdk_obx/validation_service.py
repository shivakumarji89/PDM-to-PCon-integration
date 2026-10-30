"""Validate an OBX written by pCon.planner against the configurations we asked for.

The parser is the existing QA one (``ObxValidationService.parse_obx``), so the
file is judged by the same rules the OBX Validation workflow applies. This
module only adds the cross-check between what the plugin reported and what the
file actually contains.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
import xml.etree.ElementTree as ET

from services.obx_validation_service import ObxLine, ObxValidationService
from services.pcon_sdk_obx.protocol import GenerationResult


@dataclass
class ObxValidationSummary:
    path: str
    well_formed: bool = False
    recovered_tail: bool = False
    article_lines: int = 0
    expected_articles: int = 0
    missing_final_articles: list[str] = field(default_factory=list)
    unexpected_final_articles: list[str] = field(default_factory=list)
    lines_without_price: int = 0
    problems: list[str] = field(default_factory=list)
    lines: list[ObxLine] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems


class ObxOutputValidator:
    """Independent check of the exported file; never trusts the plugin counts."""

    def __init__(self, parser: ObxValidationService | None = None) -> None:
        self._parser = parser or ObxValidationService(None)

    @staticmethod
    def _normalise(final: str) -> str:
        return " ".join(final.split()).upper()

    def validate(self, path: Path | str, result: GenerationResult | None = None) -> ObxValidationSummary:
        path = Path(path)
        summary = ObxValidationSummary(path=str(path))
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            summary.problems.append(f"Cannot read OBX file: {exc}")
            return summary
        if not text.strip():
            summary.problems.append("OBX file is empty.")
            return summary

        try:
            ET.fromstring(text)
            summary.well_formed = True
        except ET.ParseError as exc:
            summary.problems.append(f"OBX is not well-formed XML: {exc}")

        try:
            _, lines = self._parser.parse_obx(text)
        except ET.ParseError as exc:
            summary.problems.append(f"OBX could not be parsed: {exc}")
            return summary
        summary.recovered_tail = bool(getattr(self._parser, "last_parse_recovered", False))
        if summary.recovered_tail:
            summary.problems.append("OBX export is truncated; only the completed articles were readable.")
        summary.lines = lines
        summary.article_lines = len(lines)
        summary.lines_without_price = sum(1 for line in lines if not line.currency)

        if result is not None:
            expected = [c for c in result.configurations if c.status == "ok" and c.final_article]
            summary.expected_articles = len(expected)
            wanted = Counter(self._normalise(c.final_article) for c in expected)
            found = Counter(self._normalise(line.final_article) for line in lines)
            missing = wanted - found
            extra = found - wanted
            summary.missing_final_articles = sorted(missing.elements())
            summary.unexpected_final_articles = sorted(extra.elements())
            if summary.missing_final_articles:
                summary.problems.append(
                    f"{len(summary.missing_final_articles)} generated article(s) are missing from the OBX."
                )
            if not lines:
                summary.problems.append("OBX contains no basket articles.")
        return summary


@dataclass
class ReferenceComparison:
    """Generated final articles versus a reference OBX (e.g. one pCon produced by hand)."""

    reference_path: str
    reference_lines: int = 0
    generated_lines: int = 0
    matched: list[str] = field(default_factory=list)
    missing_in_generated: list[str] = field(default_factory=list)
    extra_in_generated: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def identical(self) -> bool:
        return not self.problems and not self.missing_in_generated and not self.extra_in_generated


class ReferenceObxComparer:
    """Parity check: the SDK-driven output against a known pCon-generated OBX."""

    def __init__(self, parser: ObxValidationService | None = None) -> None:
        self._parser = parser or ObxValidationService(None)

    def compare(self, generated_path: Path | str, reference_path: Path | str) -> ReferenceComparison:
        comparison = ReferenceComparison(reference_path=str(reference_path))
        try:
            _, reference = self._parser.parse_obx(Path(reference_path).read_text(encoding="utf-8"))
            _, generated = self._parser.parse_obx(Path(generated_path).read_text(encoding="utf-8"))
        except (OSError, ET.ParseError) as exc:
            comparison.problems.append(f"Cannot compare OBX files: {exc}")
            return comparison
        norm = ObxOutputValidator._normalise
        wanted = Counter(norm(line.final_article) for line in reference)
        found = Counter(norm(line.final_article) for line in generated)
        comparison.reference_lines = len(reference)
        comparison.generated_lines = len(generated)
        comparison.matched = sorted((wanted & found).elements())
        comparison.missing_in_generated = sorted((wanted - found).elements())
        comparison.extra_in_generated = sorted((found - wanted).elements())
        return comparison


__all__ = ["ObxOutputValidator", "ObxValidationSummary", "ReferenceComparison", "ReferenceObxComparer"]
