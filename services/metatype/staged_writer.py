"""Guarded persistence of a verified ``ArticleWritePlan`` to an *authorised staging working copy* (decision D8).

Nothing here runs by default. Writing needs, all at once:

1. an explicit :class:`StagingAuthorization` (a configured staging root *and* the name of whoever authorised it);
2. a staging root verified to be distinct from the production repository root and its working copy (neither
   contains the other; the nearest ``.svn`` ancestors differ), without a ``.svn`` component and without links;
3. every target file inside the staging root (a production path is mapped by its relative path), existing, a
   regular ``.csv`` file;
4. the target's current bytes hashing to the plan's original bytes (a changed or different file aborts the whole
   operation before anything is written);
5. a confirmation token equal to the plan's fingerprint, which is derived from the exact bytes to be written and is
   shown to the user in the review.

Then: back up each file (with SHA-256, outside both trees), write each through a same-directory temporary file and
an atomic ``os.replace``, re-read and re-verify; on the first failure restore every file already replaced. The
module never touches ``.svn``/``wc.db`` and never runs a version-control command.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

from services.metatype.article_write_plan import ArticleWritePlan, FilePlan, verify_file_plan

SVN_DIR = ".svn"


@dataclass(frozen=True)
class StagingAuthorization:
    staging_root: Path
    production_root: Path
    authorised_by: str


def load_authorization(staging_root: str, production_root: str, authorised_by: str
                       ) -> tuple[StagingAuthorization | None, list[str]]:
    """Build an authorization from configuration, or explain exactly what is missing."""
    missing: list[str] = []
    if not (staging_root or "").strip():
        missing.append("No staging working copy is configured (metatype_staging_root).")
    if not (authorised_by or "").strip():
        missing.append("Nobody has authorised writing to the staging working copy (metatype_staging_authorised_by).")
    if missing:
        return None, missing
    auth = StagingAuthorization(Path(staging_root), Path(production_root), authorised_by.strip())
    problems = verify_destination(auth)
    return (None, problems) if problems else (auth, [])


def _resolved(path: Path) -> Path:
    return Path(os.path.realpath(path))


def _is_inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def working_copy_root(path: Path) -> Path | None:
    for candidate in (path, *path.parents):
        if (candidate / SVN_DIR).exists():
            return candidate
    return None


def verify_destination(auth: StagingAuthorization) -> list[str]:
    problems: list[str] = []
    staging = auth.staging_root
    if not staging.is_dir():
        return [f"The staging root {staging} is not an existing directory."]
    real_staging, real_prod = _resolved(staging), _resolved(auth.production_root)
    if os.path.normcase(str(real_staging)) == os.path.normcase(str(real_prod)):
        problems.append("The staging root is the production repository root.")
    if _is_inside(real_prod, real_staging) or _is_inside(real_staging, real_prod):
        problems.append("The staging root and the production root contain one another.")
    if SVN_DIR in (p.casefold() for p in real_staging.parts):
        problems.append("The staging root lies inside Subversion metadata.")
    if os.path.normcase(str(real_staging)) != os.path.normcase(str(staging.absolute())) and staging.is_symlink():
        problems.append("The staging root is a link.")
    staging_wc, prod_wc = working_copy_root(real_staging), working_copy_root(real_prod)
    if staging_wc is not None and prod_wc is not None \
            and os.path.normcase(str(staging_wc)) == os.path.normcase(str(prod_wc)):
        problems.append(f"The staging root belongs to the same working copy as production ({prod_wc}).")
    return problems


def map_target(path: str, auth: StagingAuthorization) -> tuple[Path | None, str]:
    """The staging file a plan path corresponds to, or ``(None, reason)``."""
    source = _resolved(Path(path))
    staging, production = _resolved(auth.staging_root), _resolved(auth.production_root)
    if _is_inside(source, staging):
        target = source
    elif _is_inside(source, production):
        target = staging / source.relative_to(production)
    else:
        return None, f"{path} is neither under the staging root nor under the production root."
    real = _resolved(target)
    if not _is_inside(real, staging) or SVN_DIR in (p.casefold() for p in real.relative_to(staging).parts):
        return None, f"{target} is outside the approved staging destination."
    if target.suffix.lower() != ".csv":
        return None, f"{target.name} is not a .csv table."
    if not target.is_file() or target.is_symlink():
        return None, f"{target} does not exist in the staging copy as a regular file."
    return target, ""


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def plan_fingerprint(plan: ArticleWritePlan, auth: StagingAuthorization) -> str:
    """Token the user must confirm: it covers the destination and the exact before/after bytes of every file."""
    parts: list[str] = []
    for file_plan in plan.files:
        target, _ = map_target(file_plan.path, auth)
        parts.append(f"{target}|{sha256(file_plan.original)}|{sha256(file_plan.new)}")
    return sha256("\n".join(sorted(parts)).encode("utf-8"))[:16]


def review_text(plan: ArticleWritePlan, auth: StagingAuthorization) -> str:
    lines = [plan.review_text(), "", f"Destination (staging, authorised by {auth.authorised_by}): {auth.staging_root}"]
    for file_plan in plan.files:
        target, why = map_target(file_plan.path, auth)
        lines.append(f"  {file_plan.path} -> {target or 'NOT WRITABLE: ' + why}")
    lines.append(f"Confirmation token: {plan_fingerprint(plan, auth)}")
    return "\n".join(lines)


@dataclass
class FileOutcome:
    target: str
    backup: str = ""
    original_sha: str = ""
    new_sha: str = ""
    written: bool = False
    verified: bool = False


@dataclass
class WriteResult:
    success: bool = False
    files: list[FileOutcome] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    rolled_back: bool = False
    backup_dir: str = ""

    def summary(self) -> str:
        if self.success:
            return ("Written and verified: " + ", ".join(f.target for f in self.files)
                    + f". Backups in {self.backup_dir}.")
        state = "rolled back" if self.rolled_back else ("NOTHING written" if not any(f.written for f in self.files)
                                                         else "PARTIALLY written - manual rollback required")
        return f"Not written ({state}): " + " | ".join(self.problems)


def apply_plan(plan: ArticleWritePlan, auth: StagingAuthorization | None, confirmed_token: str,
               backup_root: Path) -> WriteResult:
    """Write the reviewed plan to the staging copy. Returns a result; never raises for expected failures."""
    result = WriteResult()
    if auth is None:
        result.problems.append("Writing is not authorised: no staging working copy is configured and approved.")
        return result
    result.problems.extend(verify_destination(auth))
    if not plan.ok:
        result.problems.append("The plan is not verified; it cannot be written.")
    if result.problems:
        return result
    targets: list[tuple[FilePlan, Path]] = []
    for file_plan in plan.files:
        target, why = map_target(file_plan.path, auth)
        if target is None:
            result.problems.append(why)
        else:
            targets.append((file_plan, target))
    if len({os.path.normcase(str(t)) for _, t in targets}) != len(targets):
        result.problems.append("Two plan files map to the same target.")
    if result.problems:
        return result
    if confirmed_token != plan_fingerprint(plan, auth):
        result.problems.append("The confirmation does not match the reviewed plan; nothing was written.")
        return result
    for file_plan, target in targets:                       # revalidate every hash before the first write
        current = target.read_bytes()
        if sha256(current) != sha256(file_plan.original):
            result.problems.append(f"{target} differs from the file the plan was computed from (changed or not an "
                                   "identical staging copy); nothing was written.")
    if result.problems:
        return result
    backup_dir = _backup_dir(backup_root, auth, result)
    if backup_dir is None:
        return result
    result.backup_dir = str(backup_dir)
    manifest = []
    for index, (file_plan, target) in enumerate(targets):
        backup = backup_dir / f"{index}_{target.name}"
        backup.write_bytes(file_plan.original)
        outcome = FileOutcome(str(target), str(backup), sha256(file_plan.original), sha256(file_plan.new))
        result.files.append(outcome)
        manifest.append({"target": str(target), "backup": str(backup), "original_sha256": outcome.original_sha,
                         "new_sha256": outcome.new_sha})
    (backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    for (file_plan, target), outcome in zip(targets, result.files):
        try:
            _atomic_write(target, file_plan.new)
            outcome.written = True
            reread = target.read_bytes()
            problems = [] if reread == file_plan.new else ["The re-read bytes differ from the planned bytes."]
            if not problems and file_plan.verifier is not None:
                problems = file_plan.verifier(reread)
            elif not problems and file_plan.columns:
                problems = verify_file_plan(FilePlan(file_plan.path, file_plan.changes, file_plan.original, reread),
                                            file_plan.columns)
            if problems:
                raise OSError("; ".join(problems))
            outcome.verified = True
        except OSError as exc:
            result.problems.append(f"{target}: {exc}")
            result.rolled_back = _restore(result.files)
            if not result.rolled_back:
                result.problems.append("Automatic rollback was incomplete; restore from " + str(backup_dir))
            return result
    result.success = True
    return result


def rollback(result: WriteResult) -> list[str]:
    """Restore the backed-up originals. A file that no longer holds the written bytes is left alone and reported."""
    problems: list[str] = []
    for outcome in result.files:
        target = Path(outcome.target)
        try:
            current = sha256(target.read_bytes())
        except OSError as exc:
            problems.append(f"{target}: {exc}")
            continue
        if current == outcome.original_sha:
            continue
        if outcome.written and current != outcome.new_sha:
            problems.append(f"{target} changed after it was written; it was not restored.")
            continue
        try:
            _atomic_write(target, Path(outcome.backup).read_bytes())
        except OSError as exc:
            problems.append(f"{target}: {exc}")
    return problems


def _restore(outcomes: list[FileOutcome]) -> bool:
    ok = True
    for outcome in outcomes:
        if not outcome.written:
            continue
        try:
            _atomic_write(Path(outcome.target), Path(outcome.backup).read_bytes())
            outcome.written = False
        except OSError:
            ok = False
    return ok


def _backup_dir(root: Path, auth: StagingAuthorization, result: WriteResult) -> Path | None:
    real_root = _resolved(root)
    for tree in (auth.staging_root, auth.production_root):
        if _is_inside(real_root, _resolved(tree)):
            result.problems.append("The backup location must lie outside the staging and production trees.")
            return None
    if working_copy_root(real_root) is not None and SVN_DIR in (p.casefold() for p in real_root.parts):
        result.problems.append("The backup location lies inside Subversion metadata.")
        return None
    path = real_root / time.strftime("metatype-backup-%Y%m%d-%H%M%S")
    try:
        path.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        result.problems.append(f"The backup directory cannot be created: {exc}")
        return None
    return path


def _atomic_write(target: Path, data: bytes) -> None:
    temp = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    try:
        with open(temp, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, target)
    finally:
        if temp.exists():
            try:
                temp.unlink()
            except OSError:
                pass
