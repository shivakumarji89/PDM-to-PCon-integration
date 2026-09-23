"""Subversion command-line integration used by the XOCD publish workflow.

The application commits only the configured XOCD folder/files. TortoiseSVN is
still supported for manual administration, while the official svn.exe client
is used for the unattended cleanup/update/add/commit workflow.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SvnStatus:
    revision: str = ""
    modified: bool = False
    unversioned: bool = False
    versioned: bool = False
    raw: str = ""


class XocdSvnService:
    """Locate and build the small set of SVN operations used by XOCD."""

    _TORTOISE_CANDIDATES = (
        Path(r"C:\Program Files\TortoiseSVN\bin\TortoiseProc.exe"),
        Path(r"C:\Program Files (x86)\TortoiseSVN\bin\TortoiseProc.exe"),
    )
    _SVN_CANDIDATES = (
        Path(r"C:\Program Files\TortoiseSVN\bin\svn.exe"),
        Path(r"C:\Program Files (x86)\TortoiseSVN\bin\svn.exe"),
        Path(r"C:\Program Files\SlikSvn\bin\svn.exe"),
    )
    # The production EXE can carry the complete Subversion CLI runtime inside
    # the PyInstaller bundle. Keeping the bundled path first means users do not
    # need to install the command-line client separately.
    _BUNDLED_SVN_RELATIVE = Path("tools") / "svn" / "bin" / "svn.exe"
    _BUNDLED_SVN_RELATIVE_FROZEN = Path("svn") / "bin" / "svn.exe"

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
    def svn_exe(cls) -> Path | None:
        """Return the SVN CLI used for unattended XOCD publishing."""
        override = os.environ.get("MK_WORKBENCH_SVN_EXE", "").strip()
        if override:
            candidate = Path(override).expanduser()
            if candidate.is_file():
                return candidate

        module_root = Path(__file__).resolve().parents[1]
        bundled = module_root / cls._BUNDLED_SVN_RELATIVE
        if bundled.is_file():
            return bundled

        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            frozen_bundled = Path(sys._MEIPASS) / cls._BUNDLED_SVN_RELATIVE_FROZEN
            if frozen_bundled.is_file():
                return frozen_bundled

        found = shutil.which("svn")
        if found:
            return Path(found)
        for candidate in cls._SVN_CANDIDATES:
            if candidate.is_file():
                return candidate
        return None

    @classmethod
    def subwcrev(cls) -> Path | None:
        for candidate in cls._SUBWCREV_CANDIDATES:
            if candidate.is_file():
                return candidate
        return None

    @classmethod
    def _svn_args(cls, command: str, path: Path, *extra: str) -> list[str]:
        exe = cls.svn_exe()
        if exe is None:
            raise FileNotFoundError(
                "No SVN command-line client is available. The production MK Workbench "
                "package should include its bundled SVN runtime; otherwise install "
                "the TortoiseSVN command-line tools or set MK_WORKBENCH_SVN_EXE."
            )
        return [str(exe), command, "--non-interactive", *extra, str(path)]

    @classmethod
    def _tortoise_args(cls, command: str, path: Path, *extra: str) -> list[str]:
        exe = cls.tortoise_proc()
        if exe is None:
            raise FileNotFoundError("TortoiseProc.exe was not found.")
        return [str(exe), f"/command:{command}", f"/path:{path}", *extra]

    @classmethod
    def tortoise_cleanup_args(cls, root: Path) -> list[str]:
        return cls._tortoise_args(
            "cleanup", root, "/cleanup", "/nodlg", "/noui", "/noprogressui"
        )

    @classmethod
    def tortoise_update_args(cls, path: Path) -> list[str]:
        return cls._tortoise_args("update", path, "/closeonend:2")

    @classmethod
    def tortoise_commit_args(cls, path: Path, message: str) -> list[str]:
        return cls._tortoise_args(
            "commit", path, f"/logmsg:{message}", "/closeonend:2"
        )

    @classmethod
    def cleanup_args(cls, working_copy_root: Path) -> list[str]:
        return cls._svn_args("cleanup", working_copy_root)

    @classmethod
    def update_args(cls, path: Path) -> list[str]:
        return cls._svn_args("update", path)

    @classmethod
    def status_args(cls, path: Path, show_updates: bool = False) -> list[str]:
        extra = ["--xml"]
        if show_updates:
            extra.insert(0, "--show-updates")
        return cls._svn_args("status", path, *extra)

    @classmethod
    def add_args(cls, paths: list[Path]) -> list[str]:
        exe = cls.svn_exe()
        if exe is None:
            raise FileNotFoundError(
                "No SVN command-line client is available for automated XOCD publish."
            )
        return [str(exe), "add", "--non-interactive", "--parents", *[str(path) for path in paths]]

    @classmethod
    def commit_args(cls, paths: list[Path], message: str) -> list[str]:
        exe = cls.svn_exe()
        if exe is None:
            raise FileNotFoundError(
                "No SVN command-line client is available for automated XOCD publish."
            )
        return [str(exe), "commit", "--non-interactive", "--message", message, *[str(path) for path in paths]]

    @classmethod
    def info_args(cls, path: Path) -> list[str]:
        return cls._svn_args("info", path)

    @classmethod
    def parse_status_items(cls, xml_text: str, base: Path) -> dict[Path, str]:
        """Return {local_path: wc-status item} from svn status XML."""
        if not xml_text.strip():
            return {}
        root = ET.fromstring(xml_text)
        base = base.resolve()
        result: dict[Path, str] = {}
        for entry in root.findall(".//entry"):
            raw = entry.get("path", "")
            status = entry.find("wc-status")
            if not raw or status is None:
                continue
            candidate = Path(raw)
            if not candidate.is_absolute():
                candidate = base / candidate
            result[candidate.resolve()] = status.get("item", "")
        return result

    @classmethod
    def parse_unversioned_paths(cls, xml_text: str, base: Path) -> set[Path]:
        """Return local paths whose SVN status is unversioned."""
        if not xml_text.strip():
            return set()
        root = ET.fromstring(xml_text)
        result: set[Path] = set()
        base = base.resolve()
        for entry in root.findall(".//entry"):
            status = entry.find("wc-status")
            if status is None or status.get("item") != "unversioned":
                continue
            raw = entry.get("path", "")
            if not raw:
                continue
            candidate = Path(raw)
            if not candidate.is_absolute():
                candidate = base / candidate
            result.add(candidate.resolve())
        return result

    @classmethod
    def has_remote_updates(cls, xml_text: str) -> bool:
        """Return True when svn status -u reports repository changes."""
        if not xml_text.strip():
            return False
        root = ET.fromstring(xml_text)
        for repos_status in root.findall(".//repos-status"):
            if repos_status.get("item") not in (None, "none", "normal"):
                return True
        return False

    @classmethod
    def run_local(cls, args: list[str]) -> int:
        completed = subprocess.run(args, check=False)
        return completed.returncode

    @classmethod
    def read_status(cls, path: Path) -> SvnStatus:
        """Read status for the exact supplied entry using SubWCRev."""
        exe = cls.subwcrev()
        if exe is None:
            raise FileNotFoundError(
                "SubWCRev.exe was not found in the TortoiseSVN installation."
            )

        with tempfile.TemporaryDirectory(prefix="mk_xocd_svn_") as tmp:
            template = Path(tmp) / "status.txt.in"
            output = Path(tmp) / "status.txt"
            template.write_text(
                "$WCREV$|$WCMODS?1:0$|$WCUNVER?1:0$|$WCRANGE$|"
                "$WCINSVN?1:0$",
                encoding="utf-8",
            )
            completed = subprocess.run(
                [str(exe), str(path), str(template), str(output)],
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode == 10:
                return SvnStatus(raw=completed.stderr or completed.stdout)
            if completed.returncode != 0:
                raise RuntimeError(
                    (completed.stderr or completed.stdout).strip()
                    or f"SubWCRev failed with code {completed.returncode}."
                )

            value = output.read_text(encoding="utf-8", errors="replace").strip()
            parts = value.split("|")
            if len(parts) != 5:
                raise RuntimeError(f"Unexpected SubWCRev output: {value}")

            revision, modified, unversioned, _range, versioned = parts

            # Use svn info as the authoritative check for the exact XOCD
            # folder instead of relying on SubWCRev's WCINSVN replacement.
            versioned_flag = versioned == "1"
            svn = cls.svn_exe()
            if svn is not None:
                info = subprocess.run(
                    [str(svn), "info", str(path)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                versioned_flag = info.returncode == 0

            return SvnStatus(
                revision=revision,
                modified=modified == "1",
                unversioned=unversioned == "1",
                versioned=versioned_flag,
                raw=completed.stdout,
            )

    @classmethod
    def find_working_copy_root(cls, path: Path) -> Path | None:
        current = path.resolve()
        for candidate in (current, *current.parents):
            if (candidate / ".svn").is_dir():
                return candidate
        return None
