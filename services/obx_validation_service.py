"""OBX validation service.

Parses incoming OBX files independently from the CET SIF workflow.
OBX parsing is format-specific; PDM pricing is reused through the existing
shared pricing implementation until OBX-specific mapping is added.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from services.base_service import BaseService
from services.sif_validation_service import SifOption, SifResult, SifValidationService


@dataclass
class ObxLine:
    """One configured purchasable article extracted from an OBX file."""

    seq: int
    base_article: str
    final_article: str
    features: dict[str, str] = field(default_factory=dict)
    currency: str = ""
    obx_price: float = 0.0
    qty: int = 1
    plc: str = ""
    source_date: str = ""

    @property
    def _final_tokens(self) -> list[str]:
        return self.final_article.strip().split()

    @property
    def base(self) -> str:
        tokens = self._final_tokens
        return tokens[0] if tokens else self.base_article

    @property
    def pl(self) -> float:
        return self.obx_price

    @property
    def sp(self) -> float:
        return self.obx_price

    @property
    def options(self) -> list[SifOption]:
        return [SifOption(code=code) for code in self._final_tokens[1:]]

    @property
    def sif_price(self) -> float:
        return self.obx_price


class ObxValidationService(BaseService):
    """Validate incoming OBX prices against PDM using shared pricing logic."""

    _CALIBRATION_SAMPLE = 10

    @staticmethod
    def _local_name(element: ET.Element) -> str:
        return element.tag.rsplit("}", 1)[-1]

    @classmethod
    def _children(cls, element: ET.Element, name: str):
        return [child for child in element.iter() if cls._local_name(child) == name]

    @staticmethod
    def _text(element: ET.Element | None) -> str:
        return (element.text or "").strip() if element is not None else ""

    @classmethod
    def _article_value(cls, article: ET.Element, article_type: str) -> str:
        for element in cls._children(article, "artNr"):
            if element.get("type", "").lower() == article_type.lower():
                return cls._text(element)
        return ""

    @classmethod
    def _features(cls, article: ET.Element) -> dict[str, str]:
        values: dict[str, str] = {}
        for feature in cls._children(article, "feature"):
            name = (feature.get("name") or "").strip()
            value = (feature.get("value") or "").strip()
            if name and value:
                values[name] = value
        return values

    @classmethod
    def _sale_price(cls, article: ET.Element) -> tuple[str, float]:
        prices = cls._children(article, "itemPrice")
        price = prices[0] if prices else None
        if price is None:
            return "", 0.0
        currency = (price.get("currency") or "").strip()
        try:
            value = float((price.get("value") or "0").replace(",", "."))
        except ValueError:
            value = 0.0
        return currency, value

    @classmethod
    def _price_date(cls, article: ET.Element) -> str:
        dates = cls._children(article, "priceDate")
        return (dates[0].get("value") or "").strip() if dates else ""

    def parse_obx(self, text: str) -> tuple[str, list[ObxLine]]:
        root = ET.fromstring(text)
        lines: list[ObxLine] = []
        file_currency = ""
        articles = [
            element for element in root.iter()
            if self._local_name(element) == "bskArticle"
        ]

        for article in articles:
            base_article = self._article_value(article, "base")
            final_article = self._article_value(article, "final")
            if not final_article:
                continue
            features = self._features(article)
            plc = features.pop("PLC", "")
            currency, obx_price = self._sale_price(article)
            source_date = self._price_date(article)
            if currency and not file_currency:
                file_currency = currency
            lines.append(
                ObxLine(
                    seq=len(lines) + 1,
                    base_article=base_article,
                    final_article=final_article,
                    features=features,
                    currency=currency,
                    obx_price=obx_price,
                    qty=1,
                    plc=plc,
                    source_date=source_date,
                )
            )
        return file_currency, lines

    def _pricing_service(self, operation_control=None) -> SifValidationService:
        if operation_control is None:
            return self.context.sif_validation_service
        from services.cancellable_sif_validation_service import CancellableSifValidationService
        return CancellableSifValidationService(self.context)

    @staticmethod
    def _candidate_sites(currency: str, repo, conn) -> list[int]:
        rows = repo._execute(
            "SELECT SiteId FROM Site WHERE UPPER(DomCurrCode) = UPPER(?) ORDER BY SiteId",
            (currency,),
            conn,
        )
        return [int(r.SiteId) for r in rows]

    def _resolve_site(self, currency, lines, pricing, repo, conn, calibration_date) -> int | None:
        return pricing.site_for_currency(currency, repo, conn, obx=True)

    @staticmethod
    def _validation_key(line: ObxLine) -> tuple[str, str]:
        """Identify one PDM pricing calculation independent of source price."""
        return (
            (line.currency or "").strip().upper(),
            " ".join(line.final_article.strip().upper().split()),
        )

    @staticmethod
    def _result_for_line(result: SifResult, line: ObxLine) -> SifResult:
        """Fan one PDM result back to a duplicate OBX source line.

        PDM price is shared, but the source price, sequence, quantity and date
        remain line-specific so duplicate rows are still independently reported.
        """
        status = result.status
        message = result.message
        if result.pdm_price is not None:
            if abs(line.sif_price - result.pdm_price) <= 0.005:
                status = "ok"
                message = ""
            else:
                status = "price_mismatch"
                message = (
                    f"price mismatch: OBX [{line.sif_price:.2f}] does NOT match "
                    f"PDM [{result.pdm_price:.2f}]"
                )
        return SifResult(
            seq=line.seq,
            sku=result.sku,
            plc=line.plc,
            qty=line.qty,
            source_date=line.source_date,
            sif_price=line.sif_price,
            pdm_price=result.pdm_price,
            status=status,
            message=message,
        )

    def _deduplicate(self, lines: list[ObxLine]) -> tuple[list[ObxLine], dict[tuple[str, str], list[ObxLine]]]:
        groups: dict[tuple[str, str], list[ObxLine]] = {}
        unique: list[ObxLine] = []
        for line in lines:
            key = self._validation_key(line)
            if key not in groups:
                groups[key] = []
                unique.append(line)
            groups[key].append(line)
        return unique, groups

    def validate(self, currency, lines, site=None, validation_date=None,
                 progress=None, stage=None, on_result=None, operation_control=None):
        pricing = self._pricing_service(operation_control)
        unique_lines, duplicate_groups = self._deduplicate(lines)
        expanded_results: list[SifResult] = []

        def handle_unique_result(result: SifResult) -> None:
            key = self._validation_key(next(
                line for line in unique_lines if line.seq == result.seq
            ))
            for line in duplicate_groups[key]:
                mapped = self._result_for_line(result, line)
                expanded_results.append(mapped)
                if on_result is not None:
                    on_result(mapped)

        if site is not None:
            pricing.validate(
                currency,
                unique_lines,
                site=site,
                obx=True,
                validation_date=validation_date,
                progress=progress,
                stage=stage,
                on_result=handle_unique_result,
                operation_control=operation_control,
            ) if operation_control is not None else pricing.validate(
                currency,
                unique_lines,
                site=site,
                obx=True,
                validation_date=validation_date,
                progress=progress,
                stage=stage,
                on_result=handle_unique_result,
            )
            return {currency: site}, sorted(expanded_results, key=lambda r: r.seq)

        from repositories.cancellable_pdm_repository import CancellablePDMRepository
        from repositories.pdm_repository import PDMRepository
        repo = (
            CancellablePDMRepository(self.context, operation_control)
            if operation_control is not None
            else PDMRepository(self.context)
        )
        conn = repo.get_connection()
        try:
            mydate = validation_date or pricing._server_date(repo, conn)
            groups: dict[str, list[ObxLine]] = {}
            for line in unique_lines:
                groups.setdefault(line.currency or currency, []).append(line)

            sites: dict[str, int | None] = {}
            for cur, group in groups.items():
                if operation_control is not None:
                    operation_control.checkpoint()
                calibration_date = next(
                    (line.source_date for line in group if line.source_date),
                    mydate,
                )
                resolved = self._resolve_site(
                    cur, group, pricing, repo, conn, calibration_date
                )
                if operation_control is not None:
                    pricing.validate(
                        cur, group, site=resolved, obx=True, validation_date=mydate,
                        progress=progress, stage=stage, on_result=handle_unique_result,
                        operation_control=operation_control,
                    )
                else:
                    _, group_results = pricing.validate(
                        cur, group, site=resolved, obx=True, validation_date=mydate,
                        progress=progress, stage=stage, on_result=handle_unique_result,
                    )
                    for result in group_results:
                        if not any(r.seq == result.seq for r in expanded_results):
                            handle_unique_result(result)
                sites[cur] = resolved
        finally:
            conn.close()

        return sites, sorted(expanded_results, key=lambda r: r.seq)

    def export_csv(self, path, currency, results) -> None:
        self._pricing_service().export_csv(path, currency, results, source_label="OBX")
