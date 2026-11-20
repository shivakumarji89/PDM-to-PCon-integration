"""Durable per-product store for raw Price Relation source rows.

The Maintenance Price Relation workflow reads each parent article's raw PDM rows
(:class:`~services.maintenance_varcond_service.ParentSource`) once and generates
every relation locally from them. This store persists those rows so a product's
relations are fetched from PDM only on first open or on an explicit reload, and
survive application restarts.

* One JSON file per scope (source database + product), under
  ``cache/pricing_relation_sources``; products never share a file.
* Writes are atomic (temp file + ``os.replace``) and guarded by a revision
  counter, so a stale writer can never replace newer data.
* A missing, corrupt, wrong-schema or wrong-scope file reads as "no cache"; it is
  never trusted partially. A parent that PDM reported as not found is a valid
  cached result (``found=False``), distinct from a failed fetch (nothing saved).
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import tempfile
import threading
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = 1
DEFAULT_DIR = Path(__file__).resolve().parents[1] / "cache" / "pricing_relation_sources"

_log = logging.getLogger(__name__)


class StaleRelationCacheError(RuntimeError):
    """The stored cache advanced since the writer read it; the write was refused."""


@dataclass(frozen=True)
class StoredRelationSources:
    revision: int
    sources: dict[str, Any]


def relation_scope(snapshot: Any, context: Any = None) -> str | None:
    """Stable cache scope for a loaded product, or ``None`` when it has no identity."""
    product = getattr(snapshot, "product", None)
    if product is None:
        return None
    ident = str(getattr(product, "id", "") or "").strip()
    code = str(getattr(product, "code", "") or getattr(product, "name", "") or "").strip()
    if not ident and not code:
        return None
    config = getattr(context, "config", None)
    source = (
        f"{getattr(config, 'pdm_server', '')}/{getattr(config, 'pdm_database', '')}"
        if config is not None else ""
    )
    return "|".join((source.casefold(), ident, code.casefold()))


def source_to_dict(source: Any) -> dict[str, Any]:
    return {
        "parent": source.parent,
        "found": bool(source.found),
        "prefix_length": int(source.prefix_length),
        "attributes": [[name, code] for name, code in source.attributes],
        "components": [
            [sub, int(quantity), sequence, features]
            for sub, quantity, sequence, features in source.components
        ],
        "increments": {
            sub: [[int(option_id), option2] for option_id, option2 in rows]
            for sub, rows in source.increments.items()
        },
        "warnings": list(source.warnings),
    }


def source_from_dict(data: Mapping[str, Any]) -> Any:
    from services.maintenance_varcond_service import ParentSource

    return ParentSource(
        parent=str(data["parent"]),
        found=bool(data["found"]),
        prefix_length=int(data["prefix_length"]),
        attributes=[(str(n), str(c)) for n, c in data["attributes"]],
        components=[
            (str(sub), int(q), str(seq), str(feat))
            for sub, q, seq, feat in data["components"]
        ],
        increments={
            str(sub): [(int(option_id), str(option2)) for option_id, option2 in rows]
            for sub, rows in data["increments"].items()
        },
        warnings=[str(w) for w in data["warnings"]],
    )


class RelationSourceStore:
    """Atomic, revision-checked JSON persistence of raw relation sources."""

    def __init__(self, directory: Path | str | None = None) -> None:
        self._dir = Path(directory) if directory is not None else DEFAULT_DIR
        self._lock = threading.Lock()

    def path_for(self, scope: str) -> Path:
        stem = re.sub(r"[^\w\-]+", "_", scope.lower()).strip("_")[:60] or "product"
        digest = hashlib.sha1(scope.encode("utf-8")).hexdigest()[:12]
        return self._dir / f"{stem}_{digest}.json"

    def load(self, scope: str) -> StoredRelationSources | None:
        """Return the validated stored sources, or ``None`` when absent/unusable."""
        path = self.path_for(scope)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if (
                payload["schema_version"] != SCHEMA_VERSION
                or payload["scope"] != scope
            ):
                return None
            sources = {
                str(code): source_from_dict(raw)
                for code, raw in payload["sources"].items()
            }
            if any(code != source.parent for code, source in sources.items()):
                return None
            return StoredRelationSources(int(payload["revision"]), sources)
        except FileNotFoundError:
            return None
        except (OSError, ValueError, KeyError, TypeError) as exc:
            _log.warning("Ignoring unusable relation cache %s: %s", path, exc)
            return None

    def revision(self, scope: str) -> int:
        stored = self.load(scope)
        return stored.revision if stored else 0

    def save(
        self, scope: str, sources: Mapping[str, Any], expected_revision: int,
        replace: bool = False,
    ) -> int:
        """Persist ``sources`` (merged into the stored set unless ``replace``).

        Raises :class:`StaleRelationCacheError` when the stored revision is no
        longer ``expected_revision``. Returns the new revision.
        """
        for code, source in sources.items():
            if getattr(source, "parent", None) != code:
                raise ValueError(f"invalid relation source for {code!r}")
        with self._lock:
            current = self.load(scope)
            current_revision = current.revision if current else 0
            if current_revision != expected_revision:
                raise StaleRelationCacheError(
                    f"relation cache advanced from revision {expected_revision} "
                    f"to {current_revision}"
                )
            merged = {} if replace or current is None else dict(current.sources)
            merged.update(sources)
            revision = current_revision + 1
            payload = {
                "schema_version": SCHEMA_VERSION,
                "scope": scope,
                "revision": revision,
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "sources": {code: source_to_dict(src) for code, src in merged.items()},
            }
            self._dir.mkdir(parents=True, exist_ok=True)
            path = self.path_for(scope)
            fd, tmp_name = tempfile.mkstemp(dir=self._dir, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(payload, handle, ensure_ascii=False)
                os.replace(tmp_name, path)
            except BaseException:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
                raise
            return revision
