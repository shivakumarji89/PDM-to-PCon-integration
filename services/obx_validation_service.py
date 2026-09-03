"""OBX validation service.

Parses incoming OBX files independently from the CET SIF workflow and reuses
only the proven shared PDM pricing/validation logic from SifValidationService.
OBX-specific PDM term mapping will be added here in the next phase.
"""
from __future__ import annotations

import re

from services.base_service import BaseService
from services.sif_validation_service import SifLine, SifValidationService


class ObxValidationService(BaseService):
    """Validate incoming OBX prices against PDM using shared pricing logic."""

    @staticmethod
    def _num(value: str) -> float:
        return SifValidationService._num(value)

    def parse_obx(self, text: str) -> tuple[str, list[SifLine]]:
        """Parse OBX articles using the existing legacy-compatible behavior."""
        lines: list[SifLine] = []
        currency = "EUR"

        currency_match = re.search(
            r"<itemPrice\b[^>]*\bcurrency=['\"]([^'\"]+)['\"]",
            text,
            re.IGNORECASE,
        )
        if currency_match:
            currency = currency_match.group(1).strip()

        article_matches = list(
            re.finditer(
                r"<artNr\s+type=['\"]final['\"][^>]*>",
                text,
                re.IGNORECASE,
            )
        )

        for seq, match in enumerate(article_matches, start=1):
            start = match.end()
            end_tag = text.find("</", start)
            if end_tag == -1:
                continue

            sku = re.sub(r" {2,}", " ", text[start:end_tag].strip())

            if seq < len(article_matches):
                item_end = article_matches[seq].start()
                item_text = text[start:item_end]
            else:
                item_text = text[start:]

            plc = ""
            plc_match = re.search(
                r"<feature\s+name=['\"]PLC['\"]\s+value=['\"]([^'\"]*)['\"]",
                item_text,
                re.IGNORECASE,
            )
            if plc_match:
                plc = plc_match.group(1).strip()

            source_date = ""
            date_match = re.search(
                r"<priceDate\b[^>]*\bvalue=['\"]([^'\"]*)['\"]",
                item_text,
                re.IGNORECASE,
            )
            if date_match:
                source_date = date_match.group(1).strip()

            price = 0.0
            price_match = re.search(
                r"<itemPrice\b[^>]*\bvalue=['\"]([^'\"]*)['\"]",
                item_text,
                re.IGNORECASE,
            )
            if price_match:
                price_text = price_match.group(1).strip().lower().replace("nan", "")
                if price_text:
                    price = self._num(price_text)

            lines.append(
                SifLine(
                    seq=seq,
                    base=sku,
                    currency=currency,
                    pl=price,
                    sp=price,
                    qty=1,
                    plc=plc,
                    source_date=source_date,
                )
            )

        return currency, lines

    def _pricing_service(self) -> SifValidationService:
        """Resolve the existing shared PDM pricing implementation."""
        return self.context.sif_validation_service

    def validate(self, currency, lines, **kwargs):
        """Reuse the proven base/increment/effective-date PDM pricing flow."""
        return self._pricing_service().validate(currency, lines, **kwargs)

    def export_csv(self, path, currency, results) -> None:
        """Reuse the existing report writer until OBX-specific reporting differs."""
        self._pricing_service().export_csv(path, currency, results)
