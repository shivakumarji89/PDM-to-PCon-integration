"""Separate, explicit, opt-in ``ebmkdb.exe`` build step (decision D10). Never runs implicitly.

``plan_build`` only inspects (it lists what would run and what would be overwritten); ``run_build`` executes the
tool only when the caller passes the plan's confirmation token *and* the build was authorised separately from
staged writing. The tool is run directly (``ebmkdb.exe mt.inp_descr <series>.ebase``) in the series folder, never
through ``make_ebase.bat`` (it ends in a blocking ``pause``). The folder must lie inside the authorised staging root.
"""
from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from services.metatype.staged_writer import (
    StagingAuthorization, _is_inside, _resolved, sha256, verify_destination,
)

TOOL = "ebmkdb.exe"
DESCRIPTOR = "mt.inp_descr"


@dataclass
class BuildPlan:
    series_dir: Path
    command: list[str] = field(default_factory=list)
    output: Path | None = None
    warnings: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    token: str = ""

    @property
    def ok(self) -> bool:
        return not self.problems and bool(self.command)

    def review_text(self) -> str:
        lines = [f"Build step (NOT run): {' '.join(self.command) or '(unavailable)'}", f"Working folder: {self.series_dir}"]
        lines += [f"  WARNING: {w}" for w in self.warnings] + [f"  PROBLEM: {p}" for p in self.problems]
        if self.ok:
            lines.append(f"Confirmation token: {self.token}")
        return "\n".join(lines)


@dataclass
class BuildResult:
    ran: bool = False
    returncode: int | None = None
    output: str = ""
    problems: list[str] = field(default_factory=list)


def plan_build(series_dir: Path, auth: StagingAuthorization | None, build_authorised: bool) -> BuildPlan:
    plan = BuildPlan(Path(series_dir))
    if auth is None:
        plan.problems.append("No authorised staging working copy; the build step is unavailable.")
        return plan
    if not build_authorised:
        plan.problems.append("Running ebmkdb.exe has not been authorised by the owner (decision D10).")
    plan.problems.extend(verify_destination(auth))
    folder = plan.series_dir
    if not folder.is_dir() or not _is_inside(_resolved(folder), _resolved(auth.staging_root)):
        plan.problems.append("The series folder is not inside the authorised staging root.")
        return plan
    if not (folder / TOOL).is_file():
        plan.problems.append(f"{TOOL} is not present in the series folder.")
    if not (folder / DESCRIPTOR).is_file():
        plan.problems.append(f"{DESCRIPTOR} is not present in the series folder.")
    if plan.problems:
        return plan
    name = next((p.stem for p in folder.glob("*.ebase")), folder.parent.name)
    plan.output = folder / f"{name}.ebase"
    plan.command = [str(folder / TOOL), DESCRIPTOR, plan.output.name]
    plan.warnings = [
        f"{plan.output.name} will be (re)generated; the previous file is overwritten"
        + (" (it exists now)." if plan.output.exists() else " (it does not exist yet)."),
        "The tool has no content validation: a malformed table can yield a broken database.",
        "Review the generated files in the working copy before committing; the application never runs Subversion.",
    ]
    previous = sha256(plan.output.read_bytes()) if plan.output.exists() else "none"
    plan.token = sha256(f"{plan.command}|{previous}".encode())[:16]
    return plan


def run_build(plan: BuildPlan, confirmed_token: str, runner: Callable[..., object] = subprocess.run,
              timeout: float = 120.0) -> BuildResult:
    result = BuildResult()
    if not plan.ok:
        result.problems.append("The build plan is not valid.")
        return result
    if confirmed_token != plan.token:
        result.problems.append("The confirmation does not match the reviewed build plan; nothing was run.")
        return result
    expected = sha256(f"{plan.command}|{sha256(plan.output.read_bytes()) if plan.output.exists() else 'none'}"
                      .encode())[:16]
    if expected != plan.token:
        result.problems.append("The existing database changed since the review; nothing was run.")
        return result
    try:
        done = runner(plan.command, cwd=str(plan.series_dir), capture_output=True, text=True, timeout=timeout,
                      stdin=subprocess.DEVNULL, check=False)
    except (OSError, subprocess.SubprocessError) as exc:
        result.problems.append(f"The build tool could not be run: {exc}")
        return result
    result.ran = True
    result.returncode = done.returncode
    result.output = (done.stdout or "") + (done.stderr or "")
    if done.returncode != 0:
        result.problems.append(f"The build tool exited with code {done.returncode}.")
    return result
