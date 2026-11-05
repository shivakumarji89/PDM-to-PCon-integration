"""Temporary OBX-compatible snapshot that hands generated articles to the OBX Validator.

The Validator only loads OBX XML (``ObxValidationPage._load_paths`` -> ``ObxValidationService.parse_obx``), so the
handoff is a temporary ``.obx`` file written by the same adapter and serializer as *Export OBX*
(``build_rows`` + ``ArticleObxService.render``). It lives in its own temp folder, never in the user's export
location, never in a PDM/MDB/repository snapshot, and is replaced or removed through this class only.

The Validator is not touched: the user loads the file with its normal *Load OBX...* action.
"""
from __future__ import annotations

import atexit
import shutil
import tempfile
import time
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from services.article_obx.article_obx_models import ArticleObxResult
from services.article_obx.article_obx_service import ArticleObxService
from services.article_obx.ocd_repository_obx import ObxExportError, build_rows
from services.obx_validation_service import ObxValidationService
from services.ocd_engine.generator import GeneratedSku

SNAPSHOT_FILE_NAME = "generated_articles.obx"
_ROOT_NAME = Path("mk_product_workbench") / "obx_validator_handoff"


@dataclass(frozen=True)
class ValidatorSnapshot:
    path: Path
    article_count: int
    skipped_unpriced: int = 0
    problems: tuple[str, ...] = field(default_factory=tuple)
    paths: tuple[Path, ...] = ()    # every part file, in order; ``path`` is the first

    @property
    def ok(self) -> bool:
        return not self.problems

    @property
    def files(self) -> tuple[Path, ...]:
        return self.paths or (self.path,)


STALE_AFTER_SECONDS = 24 * 3600

# The Validator reads a file as one string and hands it to expat, which cannot take a document of 2 GiB or more
# ("OverflowError: size does not fit in an int"). A snapshot that would exceed this is written as several complete
# OBX files instead (the Validator loads a list of files); nothing is dropped.
MAX_PART_BYTES = 1 << 30


def _split_rows(rows: list, render, max_bytes: int) -> list[tuple[list, str]]:
    """Render ``rows`` as one document, or as the fewest consecutive parts that each fit ``max_bytes``."""
    xml = render(rows)
    size = len(xml.encode("utf-8"))
    if size <= max_bytes or len(rows) < 2:
        return [(rows, xml)]
    parts = -(-size // int(max_bytes * 0.9))
    step = max(1, -(-len(rows) // max(parts, 2)))
    del xml
    result: list[tuple[list, str]] = []
    for start in range(0, len(rows), step):
        result.extend(_split_rows(rows[start:start + step], render, max_bytes))
    return result


def _final_key(final: str) -> str:
    return " ".join(final.split()).upper()


class ValidatorHandoff:
    """Owns at most one temporary snapshot; create() replaces it, clear() removes it."""

    def __init__(self, root: str | Path | None = None) -> None:
        self._root = Path(root) if root is not None else Path(tempfile.gettempdir()) / _ROOT_NAME
        self._current: ValidatorSnapshot | None = None

    @property
    def root(self) -> Path:
        return self._root

    @property
    def current(self) -> ValidatorSnapshot | None:
        return self._current

    def create(self, skus: Sequence[GeneratedSku], *, manufacturer_id: str, price_date: str,
               series_id: str = "") -> ValidatorSnapshot:
        self.purge_stale()
        rows = build_rows(skus, price_date)
        if not rows:
            raise ObxExportError("There is no priced SKU to hand to the OBX Validator.")
        service = ArticleObxService(None)
        parts = _split_rows(
            rows, lambda chunk: service.render(chunk, manufacturer_id=manufacturer_id, series_id=series_id),
            MAX_PART_BYTES)

        paths: list[Path] = []
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            folder = Path(tempfile.mkdtemp(prefix="handoff_", dir=self._root))
            for number, (chunk, xml) in enumerate(parts, 1):
                name = SNAPSHOT_FILE_NAME if len(parts) == 1 else \
                    f"{Path(SNAPSHOT_FILE_NAME).stem}_part{number:03d}{Path(SNAPSHOT_FILE_NAME).suffix}"
                path = folder / name
                try:
                    ArticleObxService.write(str(path), ArticleObxResult(rows=chunk, xml=xml))
                except OSError as exc:
                    raise ObxExportError(
                        f"Cannot write the temporary OBX snapshot part {number} of {len(parts)} "
                        f"({len(chunk)} article(s), {len(xml)} characters): {exc}") from exc
                paths.append(path)
        except OSError as exc:
            raise ObxExportError(f"Cannot write the temporary OBX snapshot: {exc}") from exc
        finally:
            parts = [(chunk, "") for chunk, _ in parts]     # release the serialized text before reading back

        # Judge the snapshot on the files the Validator will read, not on the generator's counters.
        problems: list[str] = []
        lines: list = []
        parser = ObxValidationService(None)
        for number, (path, (chunk, _)) in enumerate(zip(paths, parts), 1):
            try:
                _, part_lines = parser.parse_obx(path.read_text(encoding="utf-8"))
            except (OSError, ET.ParseError, OverflowError) as exc:
                problems.append(f"The temporary OBX part {number} of {len(paths)} ({path.stat().st_size} bytes) "
                                f"could not be read back: {exc}")
                continue
            lines.extend(part_lines)
        if not problems:
            missing = Counter(_final_key(r.permutation.final_article) for r in rows) - \
                Counter(_final_key(line.final_article) for line in lines)
            if missing:
                problems.append(f"{sum(missing.values())} article(s) are missing from the temporary OBX.")
            if len(lines) != len(rows):
                problems.append(f"The temporary OBX holds {len(lines)} article line(s); {len(rows)} were expected.")

        previous = self._current
        self._current = ValidatorSnapshot(path=paths[0], article_count=len(lines), skipped_unpriced=len(skus) - len(rows),
                                          problems=tuple(problems), paths=tuple(paths))
        if previous is not None:
            self._remove(previous.path.parent)
        return self._current

    def current_path(self) -> Path | None:
        """The snapshot file if it still exists (it may have been removed or expired), else None."""
        snapshot = self._current
        if snapshot is not None and snapshot.path.is_file():
            return snapshot.path
        return None

    def current_paths(self) -> list[Path]:
        """Every file of the snapshot, in order, if all of them still exist; otherwise an empty list."""
        snapshot = self._current
        if snapshot is not None and all(p.is_file() for p in snapshot.files):
            return list(snapshot.files)
        return []

    def purge_stale(self, max_age_seconds: float = STALE_AFTER_SECONDS) -> None:
        """Remove ``handoff_*`` folders of earlier sessions; never the current one, never anything else."""
        if not self._root.is_dir():
            return
        keep = self._current.path.parent.resolve() if self._current is not None else None
        for folder in self._root.glob("handoff_*"):
            try:
                if folder.is_dir() and folder.resolve() != keep and                         time.time() - folder.stat().st_mtime > max_age_seconds:
                    self._remove(folder)
            except OSError:
                continue

    def clear(self) -> None:
        if self._current is not None:
            self._remove(self._current.path.parent)
            self._current = None

    def _remove(self, folder: Path) -> None:
        # Only ever delete a folder this class created under its own root.
        try:
            if folder.parent.resolve() == self._root.resolve():
                shutil.rmtree(folder, ignore_errors=True)
        except OSError:
            pass


_SHARED: ValidatorHandoff | None = None


def shared_handoff() -> ValidatorHandoff:
    """The one handoff the generator writes and the Validator's "Load from Article OBX Generator" reads."""
    global _SHARED
    if _SHARED is None:
        _SHARED = ValidatorHandoff()
        atexit.register(_SHARED.clear)
    return _SHARED
