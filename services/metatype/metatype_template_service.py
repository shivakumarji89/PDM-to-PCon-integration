"""Safe initialization of a new Metatype series from the bundled empty template archive."""
from __future__ import annotations

import os
import tempfile
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


ARCHIVE_NAME = "_emptyMT.zip"
SCHEMA_NAME = "mt.inp_descr"


@dataclass(frozen=True)
class TemplateInitializationResult:
    status: str
    series: str
    target: str
    copied: tuple[str, ...] = ()
    existing: tuple[str, ...] = ()
    message: str = ""


class MetatypeTemplateService:
    """Initializes only on explicit user request; never overwrites existing files."""

    def __init__(self, repository_root: str | Path, archive_path: str | Path | None = None):
        self.repository_root = Path(repository_root).expanduser()
        self.archive_path = Path(archive_path) if archive_path else (
            Path(__file__).resolve().parents[2] / "resources" / ARCHIVE_NAME
        )

    def series_directories(self, series: str) -> list[Path]:
        if not series or series in {".", ".."} or Path(series).name != series or "/" in series or "\\" in series:
            raise ValueError("Invalid series name.")
        root = self.repository_root.resolve()
        candidate = (root / series)
        if candidate.is_symlink():
            raise ValueError("The selected series directory cannot be a symbolic link.")
        candidate = candidate.resolve()
        if candidate.parent != root:
            raise ValueError("The selected series is outside the configured repository.")
        if not candidate.is_dir():
            raise FileNotFoundError(f"Series directory does not exist: {candidate}")
        return sorted(
            (p for p in candidate.iterdir() if p.is_dir() and not p.is_symlink() and p.name.isdigit()),
            key=lambda p: (int(p.name), p.name),
        )

    def _template_names(self) -> tuple[str, ...]:
        """Return safe, flat template filenames from the bundled archive."""
        if not self.archive_path.is_file():
            return ()
        try:
            with zipfile.ZipFile(self.archive_path, "r") as archive:
                names: list[str] = []
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    parts = PurePosixPath(info.filename).parts
                    if parts and parts[0] == "_emptyMT":
                        parts = parts[1:]
                    if not parts or any(part in {"", ".", ".."} for part in parts) or len(parts) != 1:
                        return ()
                    name = parts[0]
                    if name.lower() in {"desktop.ini", "thumbs.db"}:
                        continue
                    names.append(name)
                if SCHEMA_NAME not in names:
                    return ()
                return tuple(names)
        except (zipfile.BadZipFile, OSError, EOFError, RuntimeError, NotImplementedError):
            # Initialization will report archive errors after user confirmation.
            return ()

    def inspect(self, series: str) -> TemplateInitializationResult:
        numbered = self.series_directories(series)
        template_names = self._template_names()
        required = set(template_names)

        # The schema and option-type catalogue identify an established Metatype.
        # Do not backfill missing ancillary templates into an existing project: those
        # files may have been intentionally omitted or customized by its owner.
        core_files = {SCHEMA_NAME, "go_types.csv"}
        if required and core_files.issubset(required):
            for directory in numbered:
                present = {p.name for p in directory.iterdir() if p.is_file() and not p.is_symlink()}
                if core_files.issubset(present):
                    return TemplateInitializationResult(
                        "existing", series, str(directory),
                        existing=tuple(sorted(present.intersection(required))),
                        message="Existing Metatype detected. No files were changed.",
                    )

        # A directory containing only some template files is a conflict, not a
        # target for automatic repair, because initialization must never overwrite.

        target = numbered[0] if numbered else self.repository_root / series / "1"
        if required and target.is_dir():
            present_names = {p.name for p in target.iterdir() if p.is_file() or p.is_symlink()}
            conflicts = tuple(sorted(present_names.intersection(required)))
            if conflicts:
                return TemplateInitializationResult(
                    "conflict", series, str(target), existing=conflicts,
                    message="Template files already exist. No files were changed. Conflicting template entries: "
                            + ", ".join(conflicts),
                )
        return TemplateInitializationResult(
            "empty", series, str(target),
            message="No conflicting template files found. Templates can be copied after explicit confirmation.",
        )

    def initialize(self, series: str) -> TemplateInitializationResult:
        """Copy every archive member into the selected series' data directory, refusing conflicts."""
        state = self.inspect(series)
        if state.status in {"existing", "conflict"}:
            return state
        if not self.archive_path.is_file():
            raise FileNotFoundError(f"Bundled Metatype templates are missing: {self.archive_path}")

        root = self.repository_root.resolve()
        series_dir = (root / series).resolve()
        if series_dir.parent != root or not series_dir.is_dir() or series_dir.is_symlink():
            raise ValueError("The selected series path is not a safe directory.")
        numbered = self.series_directories(series)
        target = numbered[0] if numbered else series_dir / "1"
        if target.exists() and (target.is_symlink() or not target.is_dir()):
            raise ValueError("The Metatype target path is not a regular directory.")

        try:
            return self._extract(series, target)
        except (zipfile.BadZipFile, zlib.error, EOFError, RuntimeError, NotImplementedError) as exc:
            raise ValueError(f"Bundled Metatype template archive is corrupt or unreadable: {exc}") from exc

    def _extract(self, series: str, target: Path) -> TemplateInitializationResult:
        with zipfile.ZipFile(self.archive_path, "r") as archive:
            members: list[tuple[zipfile.ZipInfo, str]] = []
            for info in archive.infolist():
                if info.is_dir():
                    continue
                member = PurePosixPath(info.filename)
                parts = member.parts
                # The supplied archive wraps all templates in _emptyMT/.
                if parts and parts[0] == "_emptyMT":
                    parts = parts[1:]
                if not parts or any(part in {"", ".", ".."} for part in parts):
                    raise ValueError(f"Unsafe template path in archive: {info.filename}")
                if len(parts) != 1:
                    raise ValueError(f"Unexpected nested template path: {info.filename}")
                name = parts[0]
                if name.lower() in {"desktop.ini", "thumbs.db"}:
                    continue
                mode = info.external_attr >> 16
                if mode and (mode & 0o170000) == 0o120000:
                    raise ValueError(f"Symbolic links are not allowed in templates: {info.filename}")
                members.append((info, name))

            if not members or SCHEMA_NAME not in {name for _, name in members}:
                raise ValueError("Template archive is incomplete: mt.inp_descr is missing.")
            destination_paths = [target / name for _, name in members]
            conflicts = [p.name for p in destination_paths if p.exists() or p.is_symlink()]
            if conflicts:
                return TemplateInitializationResult(
                    "conflict", series, str(target), existing=tuple(sorted(conflicts)),
                    message="No files were copied because template-name conflicts already exist: "
                            + ", ".join(sorted(conflicts)),
                )

            target.mkdir(parents=True, exist_ok=True)
            # Stage all bytes before publishing any template file.
            staging = Path(tempfile.mkdtemp(prefix=".metatype-template-", dir=str(target)))
            staged: list[tuple[Path, Path]] = []
            try:
                for info, name in members:
                    staged_path = staging / name
                    with archive.open(info, "r") as src, staged_path.open("xb") as dst:
                        while True:
                            chunk = src.read(1024 * 1024)
                            if not chunk:
                                break
                            dst.write(chunk)
                    staged.append((staged_path, target / name))
                # Recheck immediately before publishing to avoid replacing a concurrent file.
                conflicts = [dest.name for _, dest in staged if dest.exists() or dest.is_symlink()]
                if conflicts:
                    return TemplateInitializationResult(
                        "conflict", series, str(target), existing=tuple(sorted(conflicts)),
                        message="No files were copied because files appeared during initialization.",
                    )
                published: list[Path] = []
                try:
                    for src, dest in staged:
                        # Hard-link publication fails if the destination already exists.
                        os.link(src, dest)
                        published.append(dest)
                except BaseException:
                    for dest in published:
                        try:
                            dest.unlink()
                        except OSError:
                            pass
                    raise
            finally:
                for child in staging.iterdir():
                    try:
                        child.unlink()
                    except OSError:
                        pass
                try:
                    staging.rmdir()
                except OSError:
                    pass

        copied = tuple(sorted(p.name for p in target.iterdir() if p.name in {n for _, n in members}))
        return TemplateInitializationResult(
            "initialized", series, str(target), copied=copied,
            message=f"Initialized Metatype templates: {len(copied)} files copied.",
        )
