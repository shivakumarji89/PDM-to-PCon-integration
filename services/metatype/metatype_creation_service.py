"""Runtime Metatype creation workflow: the polymorphic stage (template Steps 1-6 implemented up to the confirmation).

Independent of any PDM product or connection. The runtime sequence is:

1. ``list_series`` - the series folders of the configured HMX repository (a shallow directory listing; no
   repository scan, no classification).
2. ``start(series)`` - loads only that series' Step 1 tables (through the existing table loader and series
   inspector, no manual scan/inspect/resolve step) and records the pattern. The polymorphic stage is the
   first stage by the owner's instruction, so template Step 2 is answered as *Polymorphism Metatype*
   through the existing :class:`MetatypePatternService`; a child Metatype stage comes later.
3. ``submit_property_identity`` - template Step 3: technical property name and English label, validated
   by :mod:`services.metatype.property_identity`.
4. ``stage_status`` - the completion gate. The stage is complete only when every template step is done,
   and child Metatype creation is unlocked only then. The writing half of template Step 6 is not
   implemented, so the gate stays closed.
4a. ``submit_value_validity`` - template Step 4a: the value-by-value ``Value | Valid for article(s)`` table,
   validated by :mod:`services.metatype.value_validity` against the Step 4 article list.
5. ``submit_translations`` - template Step 5: DE, FR, NL (and EN for the values) for the Step 3 property and
   every Step 4a value, validated by :mod:`services.metatype.translations`.
6. ``specification_text`` / ``confirm_specification`` - template Step 6: the single-block summary of Steps
   3-5 (:mod:`services.metatype.specification`) and the user's explicit confirmation of it. Confirming writes
   nothing; the template's "implement after confirmation" half (editing the go_* files) is not implemented.

Read-only: nothing is written to the HMX repository and no build tool is run. State lives in the workflow
session so it survives page navigation.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from collections.abc import Iterable

from models.metatype_creation import (
    ArticleRef,
    BranchResult,
    ConfirmedSpecification,
    Finding,
    IdentityResult,
    PolymorphicStageStatus,
    PolymorphismBranch,
    PropertyIdentity,
    SeriesChoice,
    Severity,
    SpecificationResult,
    StageStep,
    StepState,
    SwitchScope,
    TranslationDraft,
    TranslationKind,
    TranslationResult,
    TranslationRow,
    Translations,
    ValidityResult,
    ValidityStatus,
    ValueValidity,
    ValueValidityDraft,
    ValueValidityRow,
)
from models.metatype_pattern import MetatypePattern
from models.metatype_context import MetatypeCreationContext
from models.metatype_series import SeriesInspection, SeriesStatus
from models.metatype_tables import TableLoadState
from services.base_service import BaseService
from services.metatype.metatype_table_loader import MetatypeTableLoader
from services.metatype.polymorphism_branch import validate_polymorphism_branch
from services.metatype.property_identity import validate_property_identity
from services.metatype.specification import BASIS as SPEC_BASIS, build_summary
from services.metatype.translations import expected_rows, validate_translations
from services.metatype.value_validity import validate_value_validity

SCHEMA_FILE = "mt.inp_descr"
_SESSION_KEY = "metatype.creation"

#: Template steps with no implementation yet (key, title, reason it is not available). "6w" is the second half
#: of template Step 6 (implement after confirmation); the confirmation half is step "6".
_NOT_IMPLEMENTED = (
    ("6w", "Writing the files (after confirmation)",
     "Not implemented; no component writes to the repository, the table mappings and mode encoding are open "
     "owner decisions, and build-tool approval is an open owner decision."),
)

#: Applies to the whole stage until the owner decides it.
LIMITATIONS = (
    "Mode encoding is unresolved: the manual defines mode bit 4 as \"controls the variant code\" while real "
    "polymorphic properties such as atlas GATLAS_Type use 131. No mode is generated or required by any step.",
    "Step 4a: the template names no source for the property's values, so the user's value list cannot be "
    "checked for completeness, and the go_propvalues/go_actions default-reachability check is not performed. "
    "Whether Step 4a may be skipped when no exceptions exist is an open owner decision: it is always asked.",
    "Step 5: the template collects no English text for a value, so the table asks for it; the legacy go_texts "
    "encoding is an open owner decision, so no go_texts row or other output is produced from the translations.",
    "Step 6: confirming the specification authorises nothing by itself. Editing go_types, go_propvalues, "
    "go_proporder, go_children, go_actions etc. is not implemented: the template gives no mapping from the "
    "answers to table rows.",
)


class MetatypeCreationService(BaseService):
    """Drive and gate the polymorphic Metatype stage."""

    # -- state ---------------------------------------------------------------------------------------------
    def _state(self) -> MetatypeCreationContext:
        session = self.context.workflow_session(_SESSION_KEY)
        value = session.get("context")
        if value is None:
            context = MetatypeCreationContext()
            for key in MetatypeCreationContext._FIELDS:
                if key in session:
                    context[key] = session[key]
            session.clear()
            session["context"] = context
            return context
        if not isinstance(value, MetatypeCreationContext):
            raise TypeError("metatype.creation context has an unexpected type")
        return value

    def _pattern_selection(self) -> PatternSelection | None:
        selection = self._state().pattern_selection
        return selection if selection is not None and selection.series == self.series else None

    @property
    def series(self) -> str:
        return str(self._state().get("series", ""))

    @property
    def inspection(self) -> SeriesInspection | None:
        value = self._state().get("inspection")
        return value if isinstance(value, SeriesInspection) else None

    @property
    def identity(self) -> PropertyIdentity | None:
        value = self._state().get("identity")
        return value if isinstance(value, PropertyIdentity) else None

    @property
    def branch(self) -> PolymorphismBranch | None:
        value = self._state().get("branch")
        return value if isinstance(value, PolymorphismBranch) else None

    @property
    def validity(self) -> ValueValidity | None:
        """The confirmed Step 4a answer."""
        value = self._state().get("validity")
        return value if isinstance(value, ValueValidity) else None

    @property
    def validity_draft(self) -> ValueValidityDraft | None:
        """The last Step 4a input, whatever its status (kept so the page can show it again)."""
        value = self._state().get("validity_draft")
        return value if isinstance(value, ValueValidityDraft) else None

    @property
    def translations(self) -> Translations | None:
        """The confirmed Step 5 answer."""
        value = self._state().get("translations")
        return value if isinstance(value, Translations) else None

    @property
    def translation_draft(self) -> TranslationDraft | None:
        value = self._state().get("translation_draft")
        return value if isinstance(value, TranslationDraft) else None

    @property
    def confirmation(self) -> ConfirmedSpecification | None:
        """The stored Step 6 confirmation (it may be stale; see ``confirmation_is_current``)."""
        value = self._state().get("confirmation")
        return value if isinstance(value, ConfirmedSpecification) else None

    @property
    def known_articles(self) -> list[ArticleRef] | None:
        """Articles of the loaded series' go_articles; ``None`` when that table could not be read."""
        value = self._state().get("known_articles")
        return value if isinstance(value, list) else None

    @property
    def root(self) -> str:
        return str(self.context.config.metatype_repository_root)

    # -- 1. series selection -------------------------------------------------------------------------------------
    def list_series(self, root: str | Path | None = None) -> list[SeriesChoice]:
        """Series folders of the repository. Shallow: one listing per series, no file content read."""
        base = Path(self.root if root is None else root)
        choices: list[SeriesChoice] = []
        try:
            entries = sorted(os.scandir(base), key=lambda e: e.name.casefold())
        except OSError:
            return choices
        for entry in entries:
            try:
                if entry.name.startswith(".") or not entry.is_dir() or entry.is_symlink():
                    continue
                numbered = sorted(c.name for c in os.scandir(entry.path)
                                  if c.name.isdigit() and c.is_dir() and not c.is_symlink())
                has_schema = any((Path(entry.path) / n / SCHEMA_FILE).is_file() for n in numbered)
            except OSError:
                continue
            choices.append(SeriesChoice(entry.name, has_schema, numbered))
        return choices

    # -- 2. load the series' data ---------------------------------------------------------------------------------
    def start(self, series: str, root: str | Path | None = None, directory: str | None = None) -> PolymorphicStageStatus:
        """Load or refresh a series without silently discarding creation answers."""
        state = self._state()
        if state.series and state.series != series and state.inspection is not None:
            state.pending_series = series
            status = self.stage_status()
            status.warnings.append(f"Series {state.series!r} is active. Explicitly discard its drafts before loading {series!r}.")
            return status
        if state.series != series:
            state.reset_for_series(series)
        else:
            state.pending_series = None
        inspection = self.context.metatype_series_service.inspect_series(series, root=root, directory=directory)
        state.inspection = inspection
        if self._series_loaded():
            from models.metatype_pattern import PatternSelectionResult
            warnings: list[str] = []
            if inspection.status.value == "insufficient":
                warnings.append("Step 1 found no usable Metatype examples in the series or the reference series.")
            elif inspection.status.value == "reference_only":
                warnings.append("Step 1 conventions come from reference series; the target has no examples.")
            if self.context.metatype_series_service.stale_sources(inspection):
                warnings.append("Source tables changed since Step 1 ran; consider re-inspecting.")
            selection = PatternSelection(
                series=inspection.target_series, pattern=MetatypePattern.POLYMORPHISM,
                selected_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                inspection_inspected_at=inspection.inspected_at, inspection_status=inspection.status.value)
            state.pattern_selection = selection
            state.pattern_status = SelectionStatus.SELECTED
            state.pattern_warnings = warnings
            state.known_articles = self._load_known_articles(inspection)
        state.touch()
        return self.stage_status()

    def discard_and_start(self, series: str, root: str | Path | None = None, directory: str | None = None) -> PolymorphicStageStatus:
        """Explicitly discard the current series answers before loading a different series."""
        self._state().reset_for_series(series)
        return self.start(series, root=root, directory=directory)
    # -- 3. property identity --------------------------------------------------------------------------------------
    def submit_property_identity(self, name: str, label: str) -> IdentityResult:
        """Template Step 3. Accepted (and stored) only when there is no error finding."""
        if not self._series_loaded():
            return IdentityResult(False, [Finding(
                Severity.ERROR, "SERIES_NOT_LOADED",
                "Select and load a series with Metatype data before naming the property.",
                basis="template Step 1")])
        inspection = self.inspection
        if self._pattern_selection() is None:
            return IdentityResult(False, [Finding(
                Severity.ERROR, "PATTERN_NOT_SELECTED", "The pattern has not been recorded for this series.",
                basis="template Step 2")])

        findings = validate_property_identity(name, label, inspection.target)
        if any(f.severity is Severity.ERROR for f in findings):
            return IdentityResult(False, findings)
        identity = PropertyIdentity(
            series=self.series, name=name.strip(), label=label.strip(),
            confirmed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            inspection_inspected_at=inspection.inspected_at,
        )
        self._state()["identity"] = identity
        return IdentityResult(True, findings, identity)

    # -- 4. polymorphism branch --------------------------------------------------------------------------------
    def submit_polymorphism_branch(
        self,
        articles: Iterable[str],
        scope: SwitchScope | str | None,
        scope_conditions: Iterable[str] = (),
        every_article_accepts_every_value: bool | None = None,
    ) -> BranchResult:
        """Template Step 4 (Polymorphism). Accepted (and stored) only when there is no error finding."""
        identity = self.identity
        if not self._series_loaded() or identity is None:
            return BranchResult(False, [Finding(
                Severity.ERROR, "STEP3_REQUIRED",
                "Confirm the property name and label (template Step 3) before answering Step 4.",
                basis="template Step 3")])
        pattern = self.context.metatype_pattern_service.selection_for(self.series)
        if pattern is None or pattern.pattern is not MetatypePattern.POLYMORPHISM:
            return BranchResult(False, [Finding(
                Severity.ERROR, "PATTERN_NOT_POLYMORPHISM",
                "Step 4 here is the Polymorphism branch; the recorded pattern is not Polymorphism.",
                basis="template Step 2")])

        findings, cleaned, scope_value, conditions = validate_polymorphism_branch(
            articles, scope, scope_conditions, every_article_accepts_every_value, self.known_articles)
        if any(f.severity is Severity.ERROR for f in findings):
            return BranchResult(False, findings)
        branch = PolymorphismBranch(
            series=self.series, property_name=identity.name, articles=cleaned, scope=scope_value,
            scope_conditions=conditions, every_article_accepts_every_value=bool(every_article_accepts_every_value),
            confirmed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            inspection_inspected_at=self.inspection.inspected_at,
        )
        state = self._state()
        state["branch"] = branch
        state.pop("validity", None)     # Step 4a belongs to the Step 4 answer it was validated against
        return BranchResult(True, findings, branch)

    # -- 4a. value validity per article --------------------------------------------------------------------------
    def submit_value_validity(
        self, accepts_full_value_set: bool | None, rows: Iterable[ValueValidityRow] = (),
    ) -> ValidityResult:
        """Template Step 4a. Only a COMPLETE answer becomes the confirmed one; the input is always kept as a draft."""
        branch = self.branch
        if branch is None:
            return ValidityResult(ValidityStatus.INCOMPLETE, [Finding(
                Severity.ERROR, "STEP4_REQUIRED",
                "Confirm the Polymorphism branch (template Step 4) before answering Step 4a.",
                basis="template Step 4")])
        rows = list(rows)
        status, findings, cleaned = validate_value_validity(
            accepts_full_value_set, rows, branch.articles, branch.every_article_accepts_every_value)
        state = self._state()
        state["validity_draft"] = ValueValidityDraft(accepts_full_value_set, rows)
        if status is not ValidityStatus.COMPLETE:
            return ValidityResult(status, findings)
        validity = ValueValidity(
            series=self.series, property_name=branch.property_name,
            accepts_full_value_set=bool(accepts_full_value_set), rows=cleaned, articles=list(branch.articles),
            branch_confirmed_at=branch.confirmed_at,
            confirmed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        state["validity"] = validity
        return ValidityResult(status, findings, validity)

    # -- 5. translations ---------------------------------------------------------------------------------------
    def expected_translation_rows(self) -> list[TranslationRow] | None:
        """The rows Step 5 must cover (property, then each Step 4a value); ``None`` until Step 4a is confirmed."""
        identity, validity = self.identity, self.validity
        if identity is None or validity is None:
            return None
        return expected_rows(identity.name, identity.label, (r.value for r in validity.rows))

    def translation_rows(self) -> list[TranslationRow]:
        """Expected rows filled with whatever the user last entered for the same technical value."""
        rows = self.expected_translation_rows() or []
        source = self.translations.rows if self.translations is not None else []
        entered = {r.technical: r for r in (self.translation_draft.rows if self.translation_draft else source)}
        for row in rows:
            old = entered.get(row.technical)
            if old is not None:
                row.de, row.fr, row.nl = old.de, old.fr, old.nl
                if row.kind is TranslationKind.VALUE:
                    row.en = old.en
        return rows

    def submit_translations(self, rows: Iterable[TranslationRow]) -> TranslationResult:
        """Template Step 5. Only a COMPLETE answer becomes the confirmed one; the input is always kept as a draft."""
        expected = self.expected_translation_rows()
        validity = self.validity
        if expected is None or validity is None:
            return TranslationResult(ValidityStatus.INCOMPLETE, [Finding(
                Severity.ERROR, "STEP4A_REQUIRED",
                "Confirm the value validity (template Step 4a) before translating.", basis="template Step 4a")])
        rows = list(rows)
        status, findings, cleaned = validate_translations(rows, expected)
        state = self._state()
        state["translation_draft"] = TranslationDraft(rows)
        if status is not ValidityStatus.COMPLETE:
            return TranslationResult(status, findings)
        translations = Translations(
            series=self.series, property_name=self.identity.name, rows=cleaned,
            validity_confirmed_at=validity.confirmed_at,
            confirmed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        state["translations"] = translations
        return TranslationResult(status, findings, translations)

    def _translations_current(self) -> bool:
        """True when the confirmed translations still cover exactly the current property, label and values."""
        confirmed, expected = self.translations, self.expected_translation_rows()
        return (confirmed is not None and expected is not None
                and [(r.technical, r.kind) for r in confirmed.rows] == [(r.technical, r.kind) for r in expected]
                and confirmed.rows[0].en == expected[0].en)

    # -- 6. confirmation -----------------------------------------------------------------------------------------
    def specification_text(self) -> str | None:
        """The Step 6 summary block, or ``None`` until Steps 1-5 are done, current and consistent."""
        return self._specification()[0]

    def _specification(self) -> tuple[str | None, list[Finding]]:
        problems: list[Finding] = []
        if self.inspection is None:
            return None, [Finding(Severity.ERROR, "SPEC_STEP_INCOMPLETE", "No series has been loaded.",
                                  basis=SPEC_BASIS)]
        open_steps = [s for s in self._core_steps() if s.state is not StepState.DONE]
        for step in open_steps:
            problems.append(Finding(Severity.ERROR, "SPEC_STEP_INCOMPLETE",
                                    f"Step {step.key} ({step.title}) is not complete: {step.detail or step.state.value}",
                                    basis=SPEC_BASIS))
        if open_steps:
            return None, problems
        identity, branch, validity, translations = self.identity, self.branch, self.validity, self.translations
        for name, label in ((branch.property_name, "Step 4"), (validity.property_name, "Step 4a")):
            if name != identity.name:
                problems.append(Finding(Severity.ERROR, "SPEC_PROPERTY_CHANGED",
                                        f"Step 3 now names {identity.name}, but {label} was answered for {name}; "
                                        f"review {label}.", basis=SPEC_BASIS))
        if problems:
            return None, problems
        return build_summary(identity, branch, validity, translations), []

    def confirm_specification(self) -> SpecificationResult:
        """Template Step 6, first half: the user's explicit confirmation of the summary. Writes nothing."""
        text, problems = self._specification()
        if text is None:
            invalid = any(f.code == "SPEC_PROPERTY_CHANGED" for f in problems)
            return SpecificationResult(ValidityStatus.INVALID if invalid else ValidityStatus.INCOMPLETE, problems)
        confirmation = ConfirmedSpecification(
            series=self.series, property_name=self.identity.name, summary_text=text,
            confirmed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        self._state()["confirmation"] = confirmation
        return SpecificationResult(ValidityStatus.COMPLETE, [], text, confirmation)

    def confirmation_is_current(self) -> bool:
        """True while the specification built from Steps 3-5 still reads exactly as it did when confirmed."""
        confirmation = self.confirmation
        return confirmation is not None and confirmation.summary_text == self.specification_text()

    def _confirmation_step(self) -> StageStep:
        title = "Confirmation of the specification"
        if self.confirmation_is_current():
            return StageStep("6", title, StepState.DONE, "Confirmed; nothing is written.")
        text, problems = self._specification()
        if text is None:
            return StageStep("6", title, StepState.PENDING, "Complete Steps 1-5 first.")
        detail = ("The specification changed since it was confirmed; review and confirm it again."
                  if self.confirmation is not None else "Review the summary and confirm it.")
        return StageStep("6", title, StepState.PENDING, detail)

    def _load_known_articles(self, inspection: SeriesInspection) -> list[ArticleRef] | None:
        """Read the series' go_articles once (the existing loader, one table) to hint at article numbers."""
        target = inspection.target
        loaded = MetatypeTableLoader().load_family(
            inspection.repository_root, inspection.target_series, target.directory or None, tables=["go_articles"])
        table = loaded.table("go_articles")
        if table is None or table.state not in (TableLoadState.VALID, TableLoadState.NO_DATA,
                                                TableLoadState.EMPTY, TableLoadState.MALFORMED):
            return None
        if "id" not in table.columns or "article_nr" not in table.columns:
            return None
        refs: list[ArticleRef] = []
        for row in table.rows:
            record = dict(zip(table.columns, row.trimmed()))
            if record["id"] != "_native_" and record["article_nr"]:   # _native_ is reserved (MT go_articles)
                refs.append(ArticleRef(record["article_nr"], record["id"], row.line))
        return refs

    # -- completion gate ---------------------------------------------------------------------------------------
    def stage_status(self) -> PolymorphicStageStatus:
        """Where the polymorphic stage stands; child Metatypes unlock only when every step is done."""
        status = PolymorphicStageStatus(series=self.series)
        inspection = self.inspection
        if inspection is None:
            status.steps = [StageStep("1", "Series data", StepState.PENDING, "Select a series and load it.")]
            status.steps += [self._validity_step(None, None), self._translation_step(None),
                             StageStep("6", "Confirmation of the specification", StepState.PENDING,
                                       "Complete Steps 1-5 first.")] + self._later_steps(StepState.NOT_IMPLEMENTED)
            status.blocking = ["No series has been loaded."]
            return status

        loaded = self._series_loaded()
        identity, branch = self.identity, self.branch
        status.steps = self._core_steps() + [self._confirmation_step()] + self._later_steps(StepState.NOT_IMPLEMENTED)

        status.blocking = [f"Step {s.key} ({s.title}): {s.detail or s.state.value}"
                           for s in status.steps if s.state is not StepState.DONE]
        status.complete = not status.blocking
        status.children_unlocked = status.complete
        status.warnings = list(self._state().get("pattern_warnings", []))
        status.limitations = list(LIMITATIONS)
        if branch is not None and identity is not None and branch.property_name != identity.name:
            status.warnings.append(
                f"Step 3 now names {identity.name}, but Step 4 was answered for {branch.property_name}; review Step 4.")
        if loaded and self.context.metatype_series_service.stale_sources(inspection):
            status.warnings.append("Source tables changed since the series was loaded; load it again.")
        return status

    def _core_steps(self) -> list[StageStep]:
        """Template Steps 1, 2, 3, 4, 4a and 5 (everything the Step 6 summary is built from)."""
        inspection = self.inspection
        loaded = self._series_loaded()
        target = inspection.target
        if loaded:
            step1_detail = f"{inspection.target_series}: {inspection.status.value}"
            if target is not None and target.notes:
                step1_detail += f" ({len(target.notes)} note(s))"
        else:
            notes = target.notes if target is not None else inspection.messages
            step1_detail = "; ".join(notes[:2]) or "The series could not be loaded."
        pattern = self.context.metatype_pattern_service.selection_for(self.series)
        identity = self.identity
        branch = self.branch
        validity = self.validity
        return [
            StageStep("1", "Series data", StepState.DONE if loaded else StepState.PENDING, step1_detail),
            StageStep("2", "Pattern: Polymorphism Metatype",
                      StepState.DONE if pattern is not None and pattern.pattern is MetatypePattern.POLYMORPHISM
                      else StepState.PENDING, "Recorded for the polymorphic stage."),
            StageStep("3", "Property name and English label",
                      StepState.DONE if identity is not None else StepState.PENDING,
                      f"{identity.name} - {identity.label}" if identity is not None else "Not yet confirmed."),
            StageStep("4", "Polymorphism branch: articles, scope, values",
                      StepState.DONE if branch is not None else StepState.PENDING, self._branch_detail(branch)),
            self._validity_step(branch, validity),
            self._translation_step(validity),
        ]

    def _series_loaded(self) -> bool:
        """True when the target series' own tables could be loaded (it may still have no Metatype yet)."""
        inspection = self.inspection
        return (inspection is not None and inspection.target is not None
                and inspection.target.status is not SeriesStatus.FAILED)

    def can_start_children(self) -> bool:
        return self.stage_status().children_unlocked

    @staticmethod
    def _branch_detail(branch: PolymorphismBranch | None) -> str:
        if branch is None:
            return "Not yet answered."
        scope = branch.scope.value if branch.scope is SwitchScope.UNCONDITIONAL else (
            f"scoped ({len(branch.scope_conditions)} condition(s))")
        values = "every article accepts every value" if branch.every_article_accepts_every_value else (
            "value exceptions exist (see Step 4a)")
        return f"{len(branch.articles)} article(s), {scope}, {values}"

    def _validity_step(self, branch: PolymorphismBranch | None, validity: ValueValidity | None) -> StageStep:
        title = "Value validity per article"
        if validity is not None:
            detail = ("all articles accept the full value set" if validity.accepts_full_value_set
                      else f"{len(validity.rows)} value(s) with per-article validity")
            return StageStep("4a", title, StepState.DONE, detail)
        if branch is None:
            return StageStep("4a", title, StepState.PENDING, "Answer Step 4 first.")
        draft = self.validity_draft
        if draft is None:
            return StageStep("4a", title, StepState.PENDING, "Not yet answered.")
        status, findings, _ = validate_value_validity(
            draft.accepts_full_value_set, draft.rows, branch.articles, branch.every_article_accepts_every_value)
        problems = "; ".join(f.message for f in findings if f.severity is Severity.ERROR)
        if status is ValidityStatus.INVALID:
            return StageStep("4a", title, StepState.INVALID, f"Last answer is invalid: {problems}")
        return StageStep("4a", title, StepState.INCOMPLETE, f"Last answer is incomplete: {problems}")

    def _translation_step(self, validity: ValueValidity | None) -> StageStep:
        title = "Translations (DE, FR, NL)"
        expected = self.expected_translation_rows()
        if validity is None or expected is None:
            return StageStep("5", title, StepState.PENDING, "Answer Step 4a first.")
        if self._translations_current():
            return StageStep("5", title, StepState.DONE, f"{len(expected)} row(s) translated")
        stale = self.translations is not None
        draft = self.translation_draft
        if draft is None:
            detail = ("The property or values changed since the translations were confirmed; confirm them again."
                      if stale else "Not yet answered.")
            return StageStep("5", title, StepState.PENDING, detail)
        keys = {r.technical for r in expected}     # draft rows for removed values are stale, not wrong
        status, findings, _ = validate_translations([r for r in draft.rows if r.technical in keys], expected)
        problems = "; ".join(f.message for f in findings if f.severity is Severity.ERROR)
        if status is ValidityStatus.INVALID:
            return StageStep("5", title, StepState.INVALID, f"Last answer is invalid: {problems}")
        return StageStep("5", title, StepState.INCOMPLETE, f"Last answer is incomplete: {problems}")

    @staticmethod
    def _later_steps(state: StepState) -> list[StageStep]:
        return [StageStep(key, title, state, detail) for key, title, detail in _NOT_IMPLEMENTED]

    # -- presentation ---------------------------------------------------------------------------------------------
    def summary_text(self) -> str:
        status = self.stage_status()
        lines = [f"Polymorphic Metatype stage - {status.series or 'no series'}"]
        marks = {StepState.DONE: "[done]", StepState.PENDING: "[todo]", StepState.NOT_IMPLEMENTED: "[not available yet]",
                 StepState.INCOMPLETE: "[incomplete]", StepState.INVALID: "[invalid]"}
        lines += [f"  {marks[s.state]} Step {s.key}: {s.title}" + (f" - {s.detail}" if s.detail else "")
                  for s in status.steps]
        lines.append("Child Metatypes: " + ("unlocked" if status.children_unlocked
                                           else "locked until the polymorphic stage is complete"))
        lines += [f"  WARNING {w}" for w in status.warnings]
        lines += [f"  LIMITATION {item}" for item in status.limitations]
        return "\n".join(lines)

    @staticmethod
    def findings_text(result: IdentityResult | BranchResult | ValidityResult | TranslationResult
                      | SpecificationResult) -> str:
        if isinstance(result, (ValidityResult, TranslationResult, SpecificationResult)):
            what = {ValidityResult: "Value validity", TranslationResult: "Translations",
                    SpecificationResult: "Specification"}[type(result)]
            head = f"{what} confirmed." if result.accepted else f"{what} not accepted ({result.status.value})."
        else:
            what = "Polymorphism branch" if isinstance(result, BranchResult) else "Property identity"
            head = f"{what} confirmed." if result.accepted else f"{what} not accepted."
        lines = [head]
        for f in result.findings:
            where = f" [{f.evidence.table} line {f.evidence.line}]" if f.evidence is not None else ""
            basis = f" ({f.basis})" if f.basis else ""
            lines.append(f"  {f.severity.value.upper()} {f.code}: {f.message}{where}{basis}")
        return "\n".join(lines)
