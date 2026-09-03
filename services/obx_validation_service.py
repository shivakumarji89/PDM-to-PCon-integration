"""OBX validation service.

Parses incoming OBX files independently from the CET SIF workflow.
OBX parsing is format-specific; PDM pricing is reused through the existing
shared pricing implementation until OBX-specific mapping is added.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from services.base_service import BaseService
from services.sif_validation_service import SifValidationService


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

    # Temporary compatibility properties for the existing shared pricing flow.
    # These can be removed when OBX -> PDM mapping has its own input contract.
    @property
    def base(self) -> str:
        return self.base_article

    @property
    def pl(self) -> float:
        return self.obx_price

    @property
    def sp(self) -> float:
        return self.obx_price


class ObxValidationService(BaseService):
    """Validate incoming OBX prices against PDM using shared pricing logic."""

    @staticmethod
    def _local_name(element: ET.Element) -> str:
        """Return an XML tag name without an optional namespace."""
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

        sale_price = next(
            (price for price in prices if (price.get("type") or "").lower() == "sale"),
            None,
        )
        price = sale_price or (prices[0] if prices else None)

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
        """Parse configured OBX articles using the XML structure directly."""
        root = ET.fromstring(text)
        lines: list[ObxLine] = []
        file_currency = ""

        articles = [
            element
            for element in root.iter()
            if self._local_name(element) == "bskArticle"
        ]

        for seq, article in enumerate(articles, start=1):
            base_article = self._article_value(article, "base")
            final_article = self._article_value(article, "final")

            # A final article is the minimum requirement for a validation line.
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

    def _pricing_service(self) -> SifValidationService:
        """Resolve the existing shared PDM pricing implementation."""
        return self.context.sif_validation_service

    def validate(self, currency, lines, **kwargs):
        """Reuse shared PDM pricing until OBX-specific mapping is introduced."""
        return self._pricing_service().validate(currency, lines, **kwargs)

    def export_csv(self, path, currency, results) -> None:
        """Reuse the existing report writer until OBX-specific reporting differs."""
        self._pricing_service().export_csv(path, currency, results)
