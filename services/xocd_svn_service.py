"""TortoiseSVN integration used by the XOCD publish workflow.

The application deliberately uses TortoiseProc.exe rather than a Git command
or a repository-wide SVN commit. Every commit target passed by this service is
the configured XOCD folder only.

SubWCRev.exe is used for the final local working-copy check because it is
installed with TortoiseSVN and can report local modifications/unversioned items
without requiring the standalone svn.exe CLI.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SvnStatus:
    revision: str = ""
    modified: bool = False
    unversioned: bool = False
    raw: str = ""


class XocdSvnService:
    """Build and execute the small set of TortoiseSVN operations used by XOCD."""

    def __init__(self, context=None) -> None:
        self.context = context

    _TORTOISE_CANDIDATES = (
        Path(r"C:\Program Files\TortoiseSVN\bin\TortoiseProc.exe"),
        Path(r"C:\Program Files (x86)\TortoiseSVN\bin\TortoiseProc.exe"),
    )
    _SUBWCREV_CANDIDATES = (
        Path(r"C:\Program Files\TortoiseSVN\bin\SubWCRev.exe"),
        Path(r"C:\Program Files (x86)\TortoiseSVN\bin\SubWCRev.exe"),
    )

    @classmethod
    def tortoise_proc(cls) -> Path | None:
        for candidate in cls._TORTOISE_CANDIDATES:
            if candidate.is_file():
                return candidate
        found = os.environ.get("TORTOISEPROC")
        if found and Path(found).is_file():
            return Path(found)
        return None

    @classmethod
    def subwcrev(cls) -> Path | None:
        for candidate in cls._SUBWCREV_CANDIDATES:
            if candidate.is_file():
                return candidate
        return None

    @classmethod
    def _args(cls, command: str, path: Path, *extra: str) -> list[str]:
        proc = cls.tortoise_proc()
        if proc is None:
            raise FileNotFoundError(
                "TortoiseSVN was not found. Install TortoiseSVN before using "
                "Export to XOCD."
            )
        return [
            str(proc),
            f"/command:{command}",
            f"/path:{path}",
            *extra,
        ]

    @classmethod
    def cleanup_args(cls, working_copy_root: Path) -> list[str]:
        # Cleanup is deliberately limited to the SVN working-copy maintenance
        # operation. It never uses /revert, /delunversioned or /delignored.
        return cls._args(
            "cleanup",
            working_copy_root,
            "/cleanup",
            "/nodlg",
            "/noui",
            "/noprogressui",
        )

    @classmethod
    def update_args(cls, path: Path) -> list[str]:
        return cls._args("update", path, "/closeonend:2")

    @classmethod
    def commit_args(cls, xocd_folder: Path, message: str) -> list[str]:
        # The commit boundary is intentionally the XOCD folder itself.
        return cls._args(
            "commit",
            xocd_folder,
            f"/logmsg:{message}",
            "/closeonend:2",
        )

    @classmethod
    def run_local(cls, args: list[str]) -> int:
        completed = subprocess.run(args, check=False)
        return completed.returncode

    @classmethod
    def read_status(cls, path: Path) -> SvnStatus:
        """Read status for one working-copy path using SubWCRev."""
        exe = cls.subwcrev()
        if exe is None:
            raise FileNotFoundError(
                "SubWCRev.exe was not found in the TortoiseSVN installation."
            )

        with tempfile.TemporaryDirectory(prefix="mk_xocd_svn_") as tmp:
            template = Path(tmp) / "status.txt.in"
            output = Path(tmp) / "status.txt"
            template.write_text(
                "$WCREV$|$WCMODS?1:0$|$WCUNVER?1:0$|$WCRANGE$",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [str(exe), str(path), str(template), str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode == 10:
                # The XOCD folder can be unversioned during initial setup.
                return SvnStatus(raw=completed.stderr or completed.stdout)
            if completed.returncode != 0:
                raise RuntimeError(
                    (completed.stderr or completed.stdout).strip()
                    or f"SubWCRev failed with code {completed.returncode}."
                )

            value = output.read_text(encoding="utf-8", errors="replace").strip()
            parts = value.split("|")
            if len(parts) != 4:
                raise RuntimeError(f"Unexpected SubWCRev output: {value}")

            revision, modified, unversioned, _range = parts
            return SvnStatus(
                revision=revision,
                modified=modified == "true",
                unversioned=unversioned == "true",
                raw=completed.stdout,
            )

    @classmethod
    def find_working_copy_root(cls, path: Path) -> Path | None:
        current = path.resolve()
        for candidate in (current, *current.parents):
            if (candidate / ".svn").is_dir():
                return candidate
        return None
