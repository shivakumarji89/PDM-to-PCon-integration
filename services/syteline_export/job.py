"""Safe execution wrapper around the transliterated ExportThread pipeline.

Responsibilities that the legacy thread did not (or could not) provide:

* validate the configuration before anything is written;
* refuse to start when another user holds the per-site extract lock (the legacy guard is
  disabled by an ``& 0`` at ExportThread.cs:2233, so legacy silently overwrote the lock);
  a deliberate ``take_over`` policy is available;
* write into a staging directory and publish to the real output folder only after the run
  finishes, so a failed or cancelled run never leaves partial or mixed output behind and
  never clobbers the previous good output;
* map every outcome to exactly one explicit status (success / completed_with_errors /
  cancelled / failed / blocked) with the recorded legacy MsgBox errors and warnings;
* always release the lock this job acquired and close every database session.
"""
from __future__ import annotations

import logging
import os
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from services.syteline_export.config import SyteLineExportConfig
from services.syteline_export.pipeline.db import ExportDb
from services.syteline_export.pipeline.run_base import ExportAborted

LOGGER = logging.getLogger("syteline_export")

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def legacy_effective_date(text: str) -> str:
    """ISO ``yyyy-MM-dd`` -> the legacy ``dd-MMM-yyyy`` (InvariantCulture, SytelineExport.cs:3695).

    SQL Server reads ``19-Oct-2026`` the same way under every SET LANGUAGE/DATEFORMAT, whereas a
    ``yyyy-MM-dd`` string can be misread as ``yyyy-dd-MM`` on a day-first server. Other text is
    passed through unchanged.
    """
    import re
    match = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", (text or "").strip())
    if not match or not 1 <= int(match.group(2)) <= 12:
        return text
    return f"{match.group(3)}-{_MONTHS[int(match.group(2)) - 1]}-{match.group(1)}"

Status = Literal["success", "completed_with_errors", "cancelled", "failed", "blocked"]
LockPolicy = Literal["refuse", "take_over"]


@dataclass(frozen=True)
class ExportResult:
    status: Status
    message: str
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    files: tuple[str, ...] = ()
    items_total: int = 0
    items_processed: int = 0
    stage: str = ""
    duration_seconds: float = 0.0
    lock_holder: str = ""

    @property
    def published(self) -> bool:
        return bool(self.files)


class ExportJob:
    """One export run. ``execute`` is blocking; call ``cancel`` from another thread."""

    def __init__(
        self,
        config: SyteLineExportConfig,
        db: ExportDb,
        *,
        run_factory: Callable[[ExportDb], object] | None = None,
        lock_policy: LockPolicy = "refuse",
        user_name: str | None = None,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        self._config = config
        self._db = db
        self._lock_policy = lock_policy
        self._user_name = user_name or os.environ.get("USERNAME") or os.environ.get("USER") or "unknown"
        self._status_callback = status_callback
        self._run_factory = run_factory
        self._run = None
        self._cancel_requested = False

    # ------------------------------------------------------------------ public
    def cancel(self) -> None:
        """Request cancellation; honoured at the legacy `_abortThread` check points."""
        self._cancel_requested = True
        if self._run is not None:
            self._run.abort_thread()

    def execute(self) -> ExportResult:
        started = time.monotonic()
        errors = self._config.validate_for_execution()
        if errors:
            return self._result("failed", "Configuration is invalid: " + " ".join(errors), started,
                                errors=errors)
        holder = ""
        try:
            holder = self._current_lock_holder()
        except Exception as exc:  # cannot read the lock: do not guess, do not export
            LOGGER.exception("Could not read Site.ExtractUser")
            self._safe_close()
            return self._result("failed", f"Could not check the site extract lock: {exc}", started,
                                errors=(str(exc),))
        if holder and self._lock_policy != "take_over":
            self._safe_close()
            return self._result(
                "blocked",
                f"{holder} is currently extracting data from this site. Only one concurrent extract "
                "per site is permitted. Use take-over only if that extract is known to be dead.",
                started, lock_holder=holder,
            )

        if holder:  # take_over: clear the dead holder's lock so the run owns it and releases it itself
            try:
                self._db.execute("c1", "UPDATE Site SET ExtractUser = NULL WHERE SiteId = ?",
                                 (self._config.site_id,), stage="lock-takeover")
            except Exception as exc:
                LOGGER.exception("Could not take over the site extract lock")
                self._safe_close()
                return self._result("failed", f"Could not take over the site extract lock: {exc}",
                                    started, errors=(str(exc),), lock_holder=holder)
            LOGGER.warning("Took over the extract lock held by %s for site %s", holder, self._config.site_id)
        staging = self._make_staging_dir()
        run = self._new_run(staging)
        self._run = run
        if self._cancel_requested:
            run.abort_thread()
        run._extract_user_acquired = True  # release only what this job took (stage 42 / finally)
        try:
            outcome = self._drive(run)
        except BaseException:  # pragma: no cover - defensive; _drive handles Exception
            self._discard(staging)
            self._safe_close()
            raise
        finally:
            self._run = None
        files: tuple[str, ...] = ()
        if outcome in ("success", "completed_with_errors"):
            try:
                files = self._publish(staging)
            except Exception as exc:
                LOGGER.exception("Publishing export output failed")
                self._discard(staging)
                self._safe_close()
                return self._result("failed", f"Export finished but its output could not be published: {exc}",
                                    started, errors=tuple(run.errors) + (str(exc),), run=run)
        else:
            self._discard(staging)
        self._safe_close()
        message = {
            "success": "Export completed successfully.",
            "completed_with_errors": "Export completed with errors; review them before using the output.",
            "cancelled": "Export cancelled; no output was published.",
            "failed": "Export failed; no output was published.",
        }[outcome]
        return self._result(outcome, message, started, files=files, run=run)

    # ----------------------------------------------------------------- internals
    def _current_lock_holder(self) -> str:
        rows = self._db.query("c1", "SELECT ExtractUser FROM Site WITH (NOLOCK) WHERE SiteId = ?",
                              (self._config.site_id,), stage="lock-check")
        value = rows[0].get("ExtractUser") if rows else None
        return "" if value is None else str(value).strip()

    def _new_run(self, staging: Path):
        if self._run_factory is not None:
            run = self._run_factory(self._db)
        else:
            from services.syteline_export.pipeline.run import ExportRun
            run = ExportRun(self._db, status_callback=self._status_callback)
        arguments = dict(self._config.legacy_thread_arguments())
        # legacy builds paths by concatenation (directory + "temp\\"), so the separator is required
        arguments["directory"] = str(staging) + os.sep
        arguments["effectiveDate"] = legacy_effective_date(str(arguments.get("effectiveDate", "")))
        run.init_thread(**arguments)
        return run

    def _drive(self, run) -> str:
        try:
            run.exec_thread()
        except ExportAborted:
            return "cancelled"
        except Exception as exc:
            LOGGER.exception("SyteLine export failed at stage %s", getattr(run, "threadStage", "?"))
            run.errors.append(f"[stage {run.threadStage}] {type(exc).__name__}: {exc}")
            return "failed"
        if run._abortThread:
            return "cancelled"
        if getattr(run, "fatal_error", None) is not None or not getattr(run, "outputs_written", False):
            # the legacy catch swallowed an exception, or the run stopped before writing outputs:
            # never publish what may be a partial export
            return "failed"
        return "completed_with_errors" if run.errors else "success"

    def _make_staging_dir(self) -> Path:
        root = Path(self._config.output_directory).expanduser()
        staging = root / f".syteline-staging-{uuid.uuid4().hex[:12]}"
        staging.mkdir(parents=False, exist_ok=False)
        return staging

    def _publish(self, staging: Path) -> tuple[str, ...]:
        """Move staged files into the real output folder (same relative layout), replacing atomically."""
        root = Path(self._config.output_directory).expanduser()
        published: list[str] = []
        files = sorted(path for path in staging.rglob("*") if path.is_file())
        # Prepare destinations first so a missing folder fails before any file is replaced.
        for source in files:
            (root / source.relative_to(staging)).parent.mkdir(parents=True, exist_ok=True)
        for source in files:
            target = root / source.relative_to(staging)
            os.replace(source, target)
            published.append(str(target))
        self._discard(staging)
        return tuple(published)

    @staticmethod
    def _discard(staging: Path) -> None:
        shutil.rmtree(staging, ignore_errors=True)

    def _safe_close(self) -> None:
        try:
            self._db.close()
        except Exception:  # closing must never mask the result
            LOGGER.exception("Closing export database sessions failed")

    def _result(self, status: Status, message: str, started: float, *, errors=(), warnings=(),
                files=(), lock_holder: str = "", run=None) -> ExportResult:
        if run is not None:
            errors = tuple(errors) or tuple(run.errors)
            warnings = tuple(warnings) or tuple(run.warnings)
        v = getattr(run, "v", None)
        items = getattr(v, "item_rows", None) if v is not None else None
        return ExportResult(
            status=status, message=message, errors=tuple(errors), warnings=tuple(warnings),
            files=tuple(files),
            items_total=len(items) if items is not None else 0,
            items_processed=getattr(run, "items_processed", 0) if run is not None else 0,
            stage=getattr(run, "threadStage", "") if run is not None else "",
            duration_seconds=time.monotonic() - started, lock_holder=lock_holder,
        )
