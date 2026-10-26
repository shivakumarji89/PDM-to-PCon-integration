"""ExportRun: the composed, transliterated ExportThread.execThread (ExportThread.cs 2096-7483).

The stage mixins hold the logic (one per contiguous line range); this module only reproduces
the *control flow* of execThread: one ``try`` around everything (2194), the per-item loop
``while (sqlDataReader.Read() && !_abortThread)`` (2474-5426), and the global post stages.

Control-flow facts verified in the C# source:
* 2517 ``if (_exportMaterialsForPDMReport & !_superProductsOnly) { ... }`` encloses the option-report
  load and stages 10-17 (lines 2517-4200). When it is not entered ``v.option_rows`` is None and
  stages 10-17 are skipped (P02-P04).
* 3579-3586 (stage 17 start) sets ``num7 = 0; num8 = -1`` between the P03 and P04 ranges.
* The ``else`` at 4350 encloses the 20.9+ tail; P06 reads ``v.p05_else_branch`` itself.
* After an exception the catch (7432) reports and the finally (7455) always runs.
"""
from __future__ import annotations
from core.cancellation import OperationCancelled, cancellation_scope

from services.syteline_export.pipeline.helpers_fabric import HelpersFabricMixin
from services.syteline_export.pipeline.helpers_misc import HelpersMiscMixin
from services.syteline_export.pipeline.io_output import IoMixin
from services.syteline_export.pipeline.run_base import ExportAborted, ExportRunBase, Flow
from services.syteline_export.pipeline.stage_p00_setup import P00Mixin
from services.syteline_export.pipeline.stage_p01_item_head import P01Mixin
from services.syteline_export.pipeline.stage_p02_option_rows import P02Mixin
from services.syteline_export.pipeline.stage_p03_materials import P03Mixin
from services.syteline_export.pipeline.stage_p04_feature_templates import P04Mixin
from services.syteline_export.pipeline.stage_p05_item_row import P05Mixin
from services.syteline_export.pipeline.stage_p06_item_tail import P06Mixin
from services.syteline_export.pipeline.stage_p07_converted_rows import P07Mixin
from services.syteline_export.pipeline.stage_p08_postprocess import P08Mixin
from services.syteline_export.pipeline.stage_p09_patches import P09Mixin
from services.syteline_export.pipeline.stage_p10_bom import P10Mixin
from services.syteline_export.pipeline.stage_p11_finish import P11Mixin


class ExportRun(
    IoMixin, HelpersFabricMixin, HelpersMiscMixin,
    P00Mixin, P01Mixin, P02Mixin, P03Mixin, P04Mixin, P05Mixin, P06Mixin,
    P07Mixin, P08Mixin, P09Mixin, P10Mixin, P11Mixin,
    ExportRunBase,
):
    """One export run. Create a new instance per export (legacy ExportThread state is not reusable)."""

    def exec_thread(self) -> None:
        """execThread. Returns normally for success *and* for legacy-swallowed failures; inspect
        ``self.errors`` and ``self.fatal_error``. Raises ExportAborted only for explicit aborts."""
        self.fatal_error = None
        self.items_processed = 0
        try:
            self.check_abort()
            flow = self.p00_setup()
            if flow is Flow.RETURN:
                return
            if self._cancel_requested:      # p00 resets _abortThread (2100); re-apply a pending cancel
                self._abortThread = True
            self._run_item_loop()
            for stage in (self.p07_converted_rows, self.p08_postprocess,
                          self.p09_item_material_patches, self.p10_bom):
                self.check_abort()
                if stage() is Flow.RETURN:
                    return
            self.check_abort()
            self.p11_write_outputs()
            self.check_abort()
            self.outputs_written = True
        except _ReturnFromExec:
            return                      # C# `return;` inside the try: the finally still runs
        except OperationCancelled:
            raise
        except Exception as exc:
            # ExportThread.cs 7432: the catch reports and the run ends. The port additionally records
            # the exception so the caller can refuse to publish partial output.
            self.fatal_error = exc
            self.p11_on_error(exc)
        finally:
            with cancellation_scope(None):
                self.p11_finally()

    # ExportThread.cs 2474-5426
    def _run_item_loop(self) -> None:
        v = self.v
        for row in v.item_rows:
            self.check_abort()
            if self._abortThread:       # while (sqlDataReader.Read() && !_abortThread)
                break
            v.sqlDataReader = row
            flow = self._run_one_item()
            self.items_processed += 1
            if flow is Flow.NEXT_ITEM:
                continue
            if flow is Flow.BREAK_ITEMS:
                break
            if flow is Flow.RETURN:
                raise _ReturnFromExec()

    def _run_one_item(self) -> Flow | None:
        v = self.v
        flow = self.p01_item_head()
        if flow is not None:
            return flow
        if v.option_rows is not None:          # 2517 block (stages 10-17)
            for stage in (self.p02_option_rows, self.p03_materials):
                self.check_abort()
                flow = stage()
                if flow is not None:
                    return flow
            self.threadStage = "17"             # 3579-3581
            v.num7 = 0
            v.num8 = -1
            flow = self.p04_feature_templates()
            if flow is not None:
                return flow
        for stage in (self.p05_item_row_and_renumber, self.p06_item_tail):
            self.check_abort()
            flow = stage()
            if flow is not None:
                return flow
        return None


class _ReturnFromExec(Exception):
    """Internal: a stage executed a C# ``return;`` from execThread."""
