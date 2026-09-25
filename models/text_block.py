"""TextBlock domain model.

An OCD ``tCOMd_Text`` row: a named text block (the ``com_TextName`` key) with
its per-language strings, categorised by ``type_code`` (``com_TextTypeCode``).
Fields only - no logic.
"""
from __future__ import annotations

from dataclasses import dataclass, field, field

#: Known OCD text-type codes (``tCOMd_Text.com_TextTypeCode``), in display order.
TEXT_TYPE_CODES: tuple[str, ...] = (
    "artshort",
    "artlong",
    "property",
    "propvalue",
    "option",
    "optionvalue",
    "propclass",
    "prophint",
    "price",
)


@dataclass
class TextBlock:
    """One localized text block. Mirrors an OCD ``tCOMd_Text`` row."""

    name: str = ""
    type_code: str = ""
    de: str = ""
    en: str = ""
    fr: str = ""
    nl: str = ""
    translations: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Keep legacy language fields and dynamic translations aligned."""
        for language in ("de", "en", "fr", "nl"):
            value = getattr(self, language, "")
            if value and language not in self.translations:
                self.translations[language] = value
        for language, value in self.translations.items():
            if language in ("de", "en", "fr", "nl"):
                setattr(self, language, value or "")

    def get_language(self, language: str) -> str:
        return self.translations.get(language, getattr(self, language, "") or "")

    def set_language(self, language: str, value: str) -> None:
        value = "" if value is None else value
        self.translations[language] = value
        if language in ("de", "en", "fr", "nl"):
            setattr(self, language, value)
    # All language translations discovered in the source. The four legacy
    # fields above remain for compatibility with existing PDM workflows.
    translations: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Keep legacy language fields and the dynamic translation map aligned."""
        for language in ("de", "en", "fr", "nl"):
            value = getattr(self, language, "")
            if value and language not in self.translations:
                self.translations[language] = value
        for language, value in self.translations.items():
            if language in ("de", "en", "fr", "nl"):
                setattr(self, language, value or "")

    def get_language(self, language: str) -> str:
        return self.translations.get(language, getattr(self, language, "") or "")

    def set_language(self, language: str, value: str) -> None:
        value = "" if value is None else value
        self.translations[language] = value
        if language in ("de", "en", "fr", "nl"):
            setattr(self, language, value)
