"""Metatype module entry point for repository analysis.

Thin, Qt-free service the Metatype module calls. It resolves the configured
HMX root, runs the read-only scanner, keeps the latest result for the session
and exports it as JSON outside the repository.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from models.metatype_scan import MetatypeScanResult
from services.base_service import BaseService
from services.metatype.repository_scanner import MetatypeRepositoryScanner, format_scan_summary

_SESSION_KEY = "metatype.repository_scan"


class MetatypeRepositoryService(BaseService):
    """Run and retain read-only scans of the HMX Metatype repository."""

    def __init__(self, context) -> None:
        super().__init__(context)
        self._scanner = MetatypeRepositoryScanner()

    @property
    def default_root(self) -> str:
        return self.context.config.metatype_repository_root

    @property
    def last_result(self) -> MetatypeScanResult | None:
        result = self.context.workflow_session(_SESSION_KEY).get("result")
        return result if isinstance(result, MetatypeScanResult) else None

    def scan(self, root: str | Path | None = None) -> MetatypeScanResult:
        """Scan ``root`` (default: the configured HMX root) and remember the result."""
        result = self._scanner.scan(self.default_root if root is None else root)
        self.context.workflow_session(_SESSION_KEY)["result"] = result
        return result

    @staticmethod
    def summary_text(result: MetatypeScanResult) -> str:
        return format_scan_summary(result)

    @staticmethod
    def export_json(result: MetatypeScanResult, output_path: str | Path) -> Path:
        """Write ``result`` as JSON without touching anything in the scanned repository.

        The destination is rejected if it, or its parent, resolves into the
        repository (``..`` segments, symbolic links, directory junctions, or a
        repository root that is itself reached through a link). The check is
        repeated after creating parent folders, and the data is written to a
        uniquely named temporary file that is then moved over the destination:
        a pre-existing link or hard link at the destination is replaced, never
        written through.
        """
        target = Path(output_path)
        root = result.repository_root
        _check_destination(target, root)
        target.parent.mkdir(parents=True, exist_ok=True)
        _check_destination(target, root)
        descriptor, temporary = tempfile.mkstemp(dir=target.parent, prefix=target.name + ".", suffix=".tmp")
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                json.dump(result.to_dict(), handle, indent=2, ensure_ascii=False)
            _check_destination(Path(temporary), root)
            os.replace(temporary, target)
        except BaseException:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise
        return target


def _check_destination(target: Path, root: str) -> None:
    """Raise ``ValueError`` unless ``target`` is safely outside ``root``."""
    if not target.name or ":" in target.name:
        raise ValueError("The report file name is not valid (alternate data streams are not allowed).")
    if not str(root).strip():
        return
    # Compare literal and link-resolved forms of both paths, so a junction or
    # symlink on either side cannot hide the overlap.
    for candidate in (target, target.parent):
        for base in (root, os.path.realpath(root)):
            for path in (os.path.abspath(candidate), os.path.realpath(candidate)):
                if _is_within(path, base):
                    raise ValueError("The report must be saved outside the HMX repository.")


def _is_within(path: str, root: str) -> bool:
    left = os.path.normcase(os.path.abspath(path))
    right = os.path.normcase(os.path.abspath(root))
    try:
        return os.path.commonpath([left, right]) == right
    except ValueError:  # different drives
        return False
