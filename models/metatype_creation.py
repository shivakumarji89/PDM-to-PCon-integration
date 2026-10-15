"""Runtime Metatype creation workflow: polymorphic stage state (template Steps 1-6).

Fields and (de)serialisation only. Source: POLYMORPHIC_METATYPE_CREATION_TEMPLATE_04092026.md.
Only template Steps 1-6 (confirmation part) are implemented; later steps appear in the stage status as NOT_IMPLEMENTED so the
completion gate can never be passed by accident.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from models.metatype_series import Evidence

CREATION_SCHEMA_VERSION = 1


class Severity(str, Enum):
    ERROR = "error"      # blocks confirming the answer
    WARNING = "warning"  # shown, does not block
    INFO = "info"


class StepState(str, Enum):
    DONE = "done"
    PENDING = "pending"                    # implemented, waiting for the user
    INCOMPLETE = "incomplete"              # an answer was given but is missing something the user can still supply
    INVALID = "invalid"                    # an answer was given but contradicts the earlier steps or itself
    NOT_IMPLEMENTED = "not_implemented"    # template step with no implementation yet


@dataclass
class Finding:
    severity: Severity
    code: str
    message: str
    #: Source row the finding is based on, when there is one.
    evidence: Evidence | None = None
    #: Where the rule comes from ("MT_1.18.0 line 636", "template Step 3", ...).
    basis: str = ""


@dataclass
class SeriesChoice:
    """One selectable series in the configured repository."""

    name: str
    #: A numbered data directory holding mt.inp_descr exists (Metatype data can be loaded).
    has_schema: bool
    numbered_directories: list[str] = field(default_factory=list)


@dataclass
class PropertyIdentity:
    """Template Step 3 answer: technical property name and English display label."""

    series: str
    name: str
    label: str
    confirmed_at: str
    #: ``SeriesInspection.inspected_at`` of the Step 1 result it was validated against.
    inspection_inspected_at: str
    schema_version: int = CREATION_SCHEMA_VERSION


@dataclass
class IdentityResult:
    accepted: bool
    findings: list[Finding] = field(default_factory=list)
    identity: PropertyIdentity | None = None

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.ERROR]

    def to_dict(self) -> dict[str, Any]:
        return _plain(asdict(self))


class SwitchScope(str, Enum):
    """Template Step 4 (Polymorphism): is the article switch unconditional or scoped to conditions?"""

    UNCONDITIONAL = "unconditional"
    SCOPED = "scoped"


@dataclass
class ArticleRef:
    """An article the series already lists in go_articles (offered as a hint, not a restriction)."""

    article_nr: str
    metatype_id: str
    line: int


@dataclass
class PolymorphismBranch:
    """Template Step 4 answers for the Polymorphism pattern.

    No mode, table row or generation detail is derived from these answers.
    """

    series: str
    #: The Step 3 property name this was answered for.
    property_name: str
    articles: list[str]
    scope: SwitchScope
    #: The user's own text, one entry per condition; empty when the switch is unconditional.
    scope_conditions: list[str]
    #: Template question 3. ``False`` means exceptions exist (template Step 4a).
    every_article_accepts_every_value: bool
    confirmed_at: str
    inspection_inspected_at: str
    schema_version: int = CREATION_SCHEMA_VERSION


@dataclass
class BranchResult:
    accepted: bool
    findings: list[Finding] = field(default_factory=list)
    branch: PolymorphismBranch | None = None

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.ERROR]

    def to_dict(self) -> dict[str, Any]:
        return _plain(asdict(self))


class ValidityStatus(str, Enum):
    """How a Step 4a answer stands. Only COMPLETE is stored as the confirmed answer."""

    COMPLETE = "complete"
    INCOMPLETE = "incomplete"   # something the user can still supply is missing
    INVALID = "invalid"         # contradicts Step 4 or itself


@dataclass
class ValueValidityRow:
    """One line of the template's ``Value | Valid for article(s)`` table.

    ``all_articles`` is the template's "all" marker. A row with neither ``all_articles`` nor any article is
    an unanswered row (incomplete), never an implied "all".
    """

    value: str
    all_articles: bool = False
    articles: list[str] = field(default_factory=list)


@dataclass
class ValueValidityDraft:
    """The last Step 4a input, kept whatever its status so the page can show it again."""

    accepts_full_value_set: bool | None
    rows: list[ValueValidityRow] = field(default_factory=list)


@dataclass
class ValueValidity:
    """Confirmed template Step 4a answer. No mode, table row or file is derived from it."""

    series: str
    property_name: str
    #: Template Step 4a question: do all articles accept the full value set?
    accepts_full_value_set: bool
    #: Empty when every article accepts the full value set.
    rows: list[ValueValidityRow]
    #: The Step 4 article list the rows were validated against.
    articles: list[str]
    #: ``PolymorphismBranch.confirmed_at`` of the Step 4 answer it belongs to.
    branch_confirmed_at: str
    confirmed_at: str
    schema_version: int = CREATION_SCHEMA_VERSION


@dataclass
class ValidityResult:
    status: ValidityStatus
    findings: list[Finding] = field(default_factory=list)
    validity: ValueValidity | None = None

    @property
    def accepted(self) -> bool:
        return self.status is ValidityStatus.COMPLETE

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.ERROR]

    def to_dict(self) -> dict[str, Any]:
        return _plain(asdict(self))


class TranslationKind(str, Enum):
    PROPERTY = "property"   # the Step 3 property: its English label comes from Step 3
    VALUE = "value"         # a value typed in Step 4a


@dataclass
class TranslationRow:
    """One line of the template's ``Technical value -> EN -> DE -> FR -> NL`` table (DE, FR, NL in that order)."""

    technical: str
    kind: TranslationKind
    en: str = ""
    de: str = ""
    fr: str = ""
    nl: str = ""


@dataclass
class TranslationDraft:
    """The last Step 5 input, whatever its status."""

    rows: list[TranslationRow] = field(default_factory=list)


@dataclass
class Translations:
    """Confirmed template Step 5 answer. No ``go_texts`` row or other output is derived from it."""

    series: str
    property_name: str
    rows: list[TranslationRow]
    #: ``ValueValidity.confirmed_at`` of the Step 4a answer whose values these translate.
    validity_confirmed_at: str
    confirmed_at: str
    schema_version: int = CREATION_SCHEMA_VERSION


@dataclass
class TranslationResult:
    status: ValidityStatus
    findings: list[Finding] = field(default_factory=list)
    translations: Translations | None = None

    @property
    def accepted(self) -> bool:
        return self.status is ValidityStatus.COMPLETE

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.ERROR]

    def to_dict(self) -> dict[str, Any]:
        return _plain(asdict(self))


@dataclass
class ConfirmedSpecification:
    """Template Step 6: the user's explicit confirmation of the summarised specification.

    ``summary_text`` is the exact block that was shown; the confirmation counts only while the specification
    built from Steps 3-5 still renders to the same text. Confirming authorises nothing by itself: no file is
    written.
    """

    series: str
    property_name: str
    summary_text: str
    confirmed_at: str
    schema_version: int = CREATION_SCHEMA_VERSION


@dataclass
class SpecificationResult:
    status: ValidityStatus
    findings: list[Finding] = field(default_factory=list)
    #: The summary block, when every earlier step is complete enough to build it.
    summary_text: str = ""
    confirmation: ConfirmedSpecification | None = None

    @property
    def accepted(self) -> bool:
        return self.status is ValidityStatus.COMPLETE

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.ERROR]

    def to_dict(self) -> dict[str, Any]:
        return _plain(asdict(self))


@dataclass
class StageStep:
    key: str            # "1", "2", "3", "4", "4a", "5", "6"
    title: str
    state: StepState
    detail: str = ""


@dataclass
class PolymorphicStageStatus:
    """Where the polymorphic stage stands and whether child Metatypes may start."""

    series: str
    steps: list[StageStep] = field(default_factory=list)
    #: The stage is complete only when every template step is DONE.
    complete: bool = False
    #: Child Metatype creation is allowed only after the polymorphic stage is complete.
    children_unlocked: bool = False
    blocking: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    #: Known gaps that apply to the whole stage (e.g. the unresolved mode encoding).
    limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _plain(asdict(self))


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value
