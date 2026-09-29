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

# Legacy/default language order. Repository MDB imports extend this from the
# actual ``tCOMd_Text`` columns present in the source.
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
        """Derive every text-bearing engineering item into editable text blocks.

        The Text workflow is the single authoring surface for article short/long
        text, property/value text, and option/value text. Source records are
        never omitted merely because an engineering family, code, or translation
        is missing.
        """
        blocks: list[TextBlock] = []
        seen: set[tuple[str, str]] = set()

        def add(type_code: str, name: str, en: str = "") -> None:
            name = (name or "").strip()
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

        # Article text must exist for every article, not only family members.
        member_by_article: dict[str, object] = {}
        for family in snapshot.engineering.families:
            for member in family.members:
                member_by_article.setdefault(str(member.article_id), member)

        for article_id, article in articles.items():
            member = member_by_article.get(article_id)
            code = (
                getattr(member, "reduced_article", "") if member is not None else ""
            ) or article.code
            short = (
                getattr(member, "short_description", "") if member is not None else ""
            ) or article.description or article.name
            long_text = (
                getattr(member, "long_description", "") if member is not None else ""
            ) or article.description or article.name
            add("artshort", code, short)
            add("artlong", code, long_text)

        # Property and property-value text.
        resolved = self.context.engineering_class_service.resolve_config_codes(snapshot)
        for prop in snapshot.properties:
            prop_key = text_block_name(prop.name or prop.code)
            if not prop_key:
                continue
            add("property", prop_key, prop.name or prop.code)
            codes = resolved.get(str(prop.id), {})
            for value in prop.values:
                code = (
                    (value.code or "").strip()
                    or codes.get(str(value.id), "").strip()
                ).replace("#", "")
                if code:
                    suffix = code
                elif value.id:
                    suffix = f"id_{value.id}"
                else:
                    suffix = text_block_name(value.value)
                if suffix:
                    add("propvalue", f"{prop_key}_{suffix}", value.value)

        # Option and option-value text.
        for option in snapshot.options:
            opt_key = text_block_name(option.name or option.code)
            if not opt_key:
                continue
            add("option", opt_key, option.name or option.code)
            for value in getattr(option, "values", []):
                code = (value.code or "").strip().replace("#", "")
                if code:
                    suffix = code
                elif value.id:
                    suffix = f"id_{value.id}"
                else:
                    suffix = text_block_name(value.value)
                if suffix:
                    add("optionvalue", f"{opt_key}_{suffix}", value.value)

        return blocks

    @staticmethod
    def languages_for_block(block: TextBlock | None) -> tuple[str, ...]:
        """Return all languages carried by a text block, standard languages first."""
        if block is None:
            return LANGUAGES
        extras = [lang for lang in block.translations if lang not in LANGUAGES]
        return LANGUAGES + tuple(sorted(extras))

    @classmethod
    def languages_for_blocks(cls, blocks) -> tuple[str, ...]:
        """Return the union of all languages present in the supplied blocks."""
        extras: set[str] = set()
        for block in blocks or []:
            extras.update(lang for lang in block.translations if lang not in LANGUAGES)
        return LANGUAGES + tuple(sorted(extras))

    def set_language(
        self, block: TextBlock | None, language: str, value: str
    ) -> bool:
        """Set any language carried by the active text source."""
        if block is None or not language:
            return False
        block.set_language(language, value)
        return True

    def fill_empty_from_en(self, blocks) -> int:
        """Copy each block's English into its empty other-language fields (never
        overwriting an existing translation). Returns the number of fields set."""
        filled = 0
        for block in blocks or []:
            if not block.en:
                continue
            for language in self.languages_for_block(block):
                if language == "en":
                    continue
                if not block.get_language(language):
                    block.set_language(language, block.en)
                    filled += 1
        return filled

    @staticmethod
    def is_untranslated(block: TextBlock) -> bool:
        """True when any of the four language strings is empty."""
        return any(not block.get_language(language) for language in EngineeringTextService.languages_for_block(block))

