"""Engineering text service.

Derives and maintains the snapshot's OCD text blocks (``tCOMd_Text`` rows). The
Text workflow authors one :class:`~models.text_block.TextBlock` per article
(short/long), property and property value, keyed by the same text-block naming
the Class Creation workspace uses. Read/derive + edit only - no database writes.
"""
from __future__ import annotations

from models.article import Article
from models.snapshot import Snapshot
from models.text_block import TextBlock
from services.base_service import BaseService

# The four OCD language columns (``com_Text_1_<lang>``), authoritative order.
LANGUAGES: tuple[str, ...] = ("de", "en", "fr", "nl")


def text_block_name(name: str) -> str:
    """MDB text-block key from a name: drop a trailing ``(variant)`` and join
    capitalised words with ``_`` (e.g. ``'Top Material'`` -> ``'Top_Material'``).
    Mirrors ``ClassCreationPage._text_block`` so both workspaces agree.
    """
    base = (name or "").strip()
    if base.endswith(")") and "(" in base:
        base = base[: base.rfind("(")].strip()
    words = base.replace("-", " ").replace("_", " ").split()
    return "_".join(w[:1].upper() + w[1:] for w in words if w)


class EngineeringTextService(BaseService):
    """Build and edit the active snapshot's text blocks."""

    def ensure_text_blocks(self, snapshot: Snapshot | None) -> list[TextBlock]:
        """Return the snapshot's text blocks, deriving them once if empty so
        the user's later edits are preserved across refreshes."""
        if snapshot is None:
            return []
        if not snapshot.text_blocks:
            snapshot.text_blocks = self.build_text_blocks(snapshot)
        return snapshot.text_blocks

    def rebuild_text_blocks(self, snapshot: Snapshot | None) -> list[TextBlock]:
        """Force a fresh derivation, discarding any prior blocks (and edits)."""
        if snapshot is None:
            return []
        snapshot.text_blocks = self.build_text_blocks(snapshot)
        return snapshot.text_blocks

    def build_text_blocks(self, snapshot: Snapshot) -> list[TextBlock]:
        """Derive text blocks from the snapshot's articles, properties and
        property values. Deterministic and de-duplicated by (type_code, name)."""
        blocks: list[TextBlock] = []
        seen: set[tuple[str, str]] = set()

        def add(type_code: str, name: str, en: str) -> None:
            if not name:
                return
            key = (type_code, name)
            if key in seen:
                return
            seen.add(key)
            blocks.append(TextBlock(name=name, type_code=type_code, en=en or ""))

        articles: dict[str, Article] = {
            str(a.id): a for a in snapshot.articles if a.id is not None
        }

        # Article short/long text, keyed by the article's base (reduced) code.
        for family in snapshot.engineering.families:
            for member in family.members:
                article = articles.get(str(member.article_id))
                code = member.reduced_article or (article.code if article else "")
                short = member.short_description or (
                    self.context.product_type_name(article.product_id)
                    if article is not None else ""
                ) or (article.description if article else "")
                long_text = member.long_description or (
                    self.context.product_type_name(article.product_id)
                    if article is not None
                    else ""
                ) or (article.name if article else "")
                add("artshort", code, short)
                add("artlong", code, long_text)

        # Property + property-value text. A value's text block is keyed by
        # ``<Property>_<code>`` (e.g. ``LegStyle_T``), using the value's own
        # order code or, for configuration values, the resolved code.
        resolved = self.context.engineering_class_service.resolve_config_codes(snapshot)
        for prop in snapshot.properties:
            prop_key = text_block_name(prop.name)
            add("property", prop_key, prop.name)
            codes = resolved.get(str(prop.id), {})
            for value in prop.values:
                code = (
                    (value.code or "").strip() or codes.get(str(value.id), "")
                ).replace("#", "")
                if code:
                    add("propvalue", f"{prop_key}_{code}", value.value)

        # Option + option-value text (options carry their own order codes).
        for option in snapshot.options:
            opt_key = text_block_name(option.name)
            add("option", opt_key, option.name)
            for value in getattr(option, "values", []):
                code = (value.code or "").strip().replace("#", "")
                if code:
                    add("optionvalue", f"{opt_key}_{code}", value.value)

        return blocks

    def set_language(
        self, block: TextBlock | None, language: str, value: str
    ) -> bool:
        """Set one language string on a text block. Returns True on change."""
        if block is None or language not in LANGUAGES:
            return False
        setattr(block, language, "" if value is None else value)
        return True

    def fill_empty_from_en(self, blocks) -> int:
        """Copy each block's English into its empty other-language fields (never
        overwriting an existing translation). Returns the number of fields set."""
        filled = 0
        for block in blocks or []:
            if not block.en:
                continue
            for language in ("de", "fr", "nl"):
                if not getattr(block, language):
                    setattr(block, language, block.en)
                    filled += 1
        return filled

    @staticmethod
    def is_untranslated(block: TextBlock) -> bool:
        """True when any of the four language strings is empty."""
        return not (block.de and block.en and block.fr and block.nl)

