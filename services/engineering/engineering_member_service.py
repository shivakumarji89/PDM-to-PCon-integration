"""Engineering member management service.

Moves an existing :class:`~models.member_article.MemberArticle` between
engineering families on an already-populated Snapshot. A member belongs to
exactly one family; moving relocates the **same instance** (never a copy).

It mutates only the ``members`` lists of ``snapshot.engineering.families`` and
never touches source data, PDM, the UI, or signals. No drag & drop, multi-select,
copy, builder, reduction, validation, assignment, or generation.
"""
from __future__ import annotations

from models.article import Article
from models.engineering_family import EngineeringFamily
from models.member_article import MemberArticle
from models.snapshot import Snapshot
from services.base_service import BaseService
from services.engineering.engineering_repository import EngineeringRepository


class EngineeringMemberService(BaseService):
    """Relocate members between engineering families (business logic only)."""

    def get_article(
        self, snapshot: Snapshot | None, member: MemberArticle | None
    ) -> Article | None:
        """Return the source Article that ``member`` represents, or ``None``.

        Read-only lookup by ``member.article_id`` against ``snapshot.articles``.
        Never mutates the snapshot or the engineering model.
        """
        if snapshot is None or member is None:
            return None
        article_id = getattr(member, "article_id", "")
        if not article_id:
            return None
        for article in snapshot.articles:
            if article.id == article_id:
                return article
        return None

    def get_member(
        self, snapshot: Snapshot | None, article: Article | None
    ) -> MemberArticle | None:
        """Return the member representing ``article``, or ``None``.

        Read-only lookup by ``article.id`` via :meth:`find_member`.
        """
        if snapshot is None or article is None:
            return None
        return self.find_member(snapshot, article.id)

    def find_member(
        self, snapshot: Snapshot | None, article_id: str | None
    ) -> MemberArticle | None:
        """Return the member whose ``article_id`` equals ``article_id``.

        Read-only scan across all engineering families; returns ``None`` when no
        member matches. Never mutates the snapshot or the engineering model.
        """
        if snapshot is None or snapshot.engineering is None or not article_id:
            return None
        for family in snapshot.engineering.families:
            for member in family.members:
                if member.article_id == article_id:
                    return member
        return None

    def get_member_family(
        self, snapshot: Snapshot | None, member: MemberArticle | None
    ) -> EngineeringFamily | None:
        """Return the family that currently owns ``member`` (by identity)."""
        if snapshot is None or snapshot.engineering is None or member is None:
            return None
        for family in snapshot.engineering.families:
            if any(m is member for m in family.members):
                return family
        return None

    def can_move(
        self,
        snapshot: Snapshot | None,
        member: MemberArticle | None,
        destination: EngineeringFamily | None,
    ) -> bool:
        """Whether ``member`` can be moved to ``destination``.

        Rejects: no snapshot, missing member/destination, member not found in
        any family, destination not part of this snapshot, and destination ==
        source.
        """
        if snapshot is None or snapshot.engineering is None:
            return False
        if member is None or destination is None:
            return False
        if destination not in snapshot.engineering.families:
            return False
        source = self.get_member_family(snapshot, member)
        if source is None:
            return False
        return destination is not source

    def move_member(
        self,
        snapshot: Snapshot | None,
        member: MemberArticle | None,
        destination: EngineeringFamily | None,
    ) -> bool:
        """Move ``member`` from its source family to ``destination``.

        Removes the exact instance from the source and appends the same instance
        to the destination - no duplicate, no copy. Returns ``True`` on success.
        """
        if not self.can_move(snapshot, member, destination):
            return False
        source = self.get_member_family(snapshot, member)
        for index, current in enumerate(source.members):
            if current is member:
                del source.members[index]
                break
        destination.members.append(member)
        return True

    def get_reduced_article(self, member: MemberArticle | None) -> str:
        """Return the member's reduced article (read-only, via the repository)."""
        return self._repository().get_reduced_article(member)

    def set_reduced_article(
        self, member: MemberArticle | None, value: str
    ) -> bool:
        """Set the member's reduced article. An empty/None value clears it."""
        if member is None:
            return False
        member.reduced_article = "" if value is None else value
        return True

    def auto_reduce(self, snapshot: Snapshot | None) -> int:
        """Stamp every member's ``reduced_article`` with its product base.

        Groups members by their article's product, computes the longest common
        prefix of each group's article codes (the proven per-product reduction:
        the shared prefix is the product code + its constant configuration, and
        the varying tail is the order-code remainder), and stamps that prefix on
        each member. Members without an article or code are skipped. Returns the
        number of members whose base changed.
        """
        if snapshot is None or snapshot.engineering is None:
            return 0
        groups: dict[str, list[tuple[MemberArticle, str]]] = {}
        for family in snapshot.engineering.families:
            for member in family.members:
                article = self.get_article(snapshot, member)
                code = (article.code if article is not None else "") or ""
                if not code:
                    continue
                product_id = str(getattr(article, "product_id", "") or "")
                groups.setdefault(product_id, []).append((member, code))
        updated = 0
        for rows in groups.values():
            base = self._longest_common_prefix([code for _member, code in rows])
            for member, _code in rows:
                if member.reduced_article != base:
                    member.reduced_article = base
                    updated += 1
        return updated

    @staticmethod
    def _longest_common_prefix(codes: list[str]) -> str:
        """Longest character prefix shared by every non-empty code."""
        codes = [c for c in codes if c]
        if not codes:
            return ""
        prefix = codes[0]
        for code in codes[1:]:
            limit = min(len(prefix), len(code))
            index = 0
            while index < limit and prefix[index] == code[index]:
                index += 1
            prefix = prefix[:index]
            if not prefix:
                break
        return prefix

    def get_long_description(self, member: MemberArticle | None) -> str:
        """Return the member's long description (read-only, via the repository)."""
        return self._repository().get_long_description(member)

    def set_long_description(
        self, member: MemberArticle | None, value: str
    ) -> bool:
        """Set the member's long description. An empty/None value clears it."""
        if member is None:
            return False
        member.long_description = "" if value is None else value
        return True

    def get_short_description(self, member: MemberArticle | None) -> str:
        """Return the member's short description (read-only, via the repository)."""
        return self._repository().get_short_description(member)

    def set_short_description(
        self, member: MemberArticle | None, value: str
    ) -> bool:
        """Set the member's short description. An empty/None value clears it."""
        if member is None:
            return False
        member.short_description = "" if value is None else value
        return True

    def set_relation_object(
        self, member: MemberArticle | None, value: str
    ) -> bool:
        """Set the member's relation object. An empty/None value clears it."""
        if member is None:
            return False
        member.relation_object = "" if value is None else value
        return True

    def set_code_scheme(
        self, member: MemberArticle | None, value: str
    ) -> bool:
        """Set the member's code scheme. An empty/None value clears it."""
        if member is None:
            return False
        member.code_scheme = "" if value is None else value
        return True

    def _repository(self) -> EngineeringRepository:
        """Reuse the context's engineering repository, else a stateless one."""
        repository = getattr(self.context, "engineering_repository", None)
        if repository is None:
            repository = EngineeringRepository(self.context)
        return repository
