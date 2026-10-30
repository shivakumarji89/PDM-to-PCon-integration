"""Run a generate request against the plugin and validate the produced OBX."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from services.pcon_sdk_obx import protocol
from services.pcon_sdk_obx.bridge import PconPluginBridge
from services.pcon_sdk_obx.protocol import GenerationPlan, GenerationResult, JobProgress
from services.pcon_sdk_obx.validation_service import ObxOutputValidator, ObxValidationSummary


@dataclass
class GenerationOutcome:
    """Everything the page needs after one run."""

    result: GenerationResult
    validation: ObxValidationSummary | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        if self.errors or not self.result.exported:
            return False
        return self.validation is None or self.validation.ok


class PconObxGenerationService:
    """Orchestrate: plugin generate → OBX on disk → independent validation."""

    def __init__(self, bridge: PconPluginBridge, validator: ObxOutputValidator | None = None) -> None:
        self._bridge = bridge
        self._validator = validator or ObxOutputValidator()

    def generate(self, plan: GenerationPlan, *, reporter=None) -> GenerationOutcome:
        output = Path(plan.output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            # pCon overwrites; make the Workbench responsible for the stale
            # file so a failed export cannot be mistaken for a fresh one.
            output.unlink()

        state = {"begun": False, "processed": 0}

        def on_progress(progress: JobProgress) -> None:
            if reporter is None:
                return
            if progress.total and not state["begun"]:
                reporter.begin(progress.total, title="Generating configured articles",
                               subject=", ".join(a.article_number for a in plan.articles)[:80])
                state["begun"] = True
            while state["begun"] and state["processed"] < progress.processed:
                state["processed"] += 1
                reporter.advance(progress.message or f"Configured {state['processed']}/{progress.total}")
            if progress.message:
                reporter.note(progress.message)

        data = self._bridge.send(
            protocol.KIND_GENERATE, plan.to_dict(),
            timeout=self._bridge.settings.generate_timeout, on_progress=on_progress,
        )
        result = GenerationResult.from_dict(data)
        outcome = GenerationOutcome(result=result)
        if result.cancelled:
            outcome.errors.append("Generation was cancelled before the export.")
            return outcome
        if not result.exported:
            outcome.errors.append("pCon.planner reported that the OBX export did not succeed.")
            return outcome
        if not output.is_file():
            outcome.errors.append(f"Expected OBX file was not written: {output}")
            return outcome
        outcome.validation = self._validator.validate(output, result)
        if not outcome.validation.ok:
            outcome.errors.extend(outcome.validation.problems)
        return outcome


__all__ = ["GenerationOutcome", "PconObxGenerationService"]
