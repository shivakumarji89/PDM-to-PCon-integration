"""Persistent repository ↔ PDM connection registry.

Discovery results are temporary evidence. Once a user starts work from a selected
PDM series, the established relationship is stored centrally so future
maintenance can reopen the known source instead of rediscovering it.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.base_service import BaseService


class RepositoryConnectionService(BaseService):
    """Central persistent knowledge store for established repository links."""

    VERSION = 1

    @property
    def _path(self) -> Path:
        return Path(self.context.config.repository_connection_registry)

    @staticmethod
    def _key(repository_path: str | Path) -> str:
        return str(Path(repository_path).resolve()).casefold()

    def _read(self) -> dict[str, Any]:
        path = self._path
        if not path.is_file():
            return {"version": self.VERSION, "connections": {}}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("connections"), dict):
                return data
        except (OSError, json.JSONDecodeError):
            pass
        return {"version": self.VERSION, "connections": {}}

    def _write(self, document: dict[str, Any]) -> None:
        path = self._path
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(
            json.dumps(document, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temp.replace(path)

    def get(self, repository_path: str | Path) -> dict[str, Any] | None:
        """Return the established connection for a repository, if one exists."""
        return self._read()["connections"].get(self._key(repository_path))

    def establish(
        self,
        *,
        repository_path: str | Path,
        repository_name: str,
        repository_code: str,
        repository_category: str,
        pdm_candidate: dict[str, Any],
        engineering_summary: dict[str, Any] | None = None,
        discovery: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Persist a confirmed working relationship and its current evidence."""
        document = self._read()
        connections = document["connections"]
        key = self._key(repository_path)
        now = datetime.now(timezone.utc).isoformat()

        existing = connections.get(key, {})
        connection = {
            "repository": {
                "path": str(Path(repository_path)),
                "name": repository_name,
                "code": repository_code,
                "category": repository_category,
            },
            "pdm": {
                "product_id": str(pdm_candidate.get("id") or ""),
                "product_name": str(pdm_candidate.get("name") or ""),
                "product_code": str(pdm_candidate.get("code") or ""),
                "category": str(pdm_candidate.get("category") or ""),
                "range": str(
                    pdm_candidate.get("range_name")
                    or pdm_candidate.get("range")
                    or ""
                ),
                "catalogue": str(
                    pdm_candidate.get("catalogue")
                    or pdm_candidate.get("catalogue_name")
                    or ""
                ),
                "lead_time": pdm_candidate.get("lead_time"),
            },
            "discovery": discovery
            or existing.get("discovery", {
                "status": "not_recorded",
                "catalogues": [],
            }),
            "engineering": engineering_summary
            or existing.get("engineering", {
                "article_count": None,
                "article_length": None,
                "links": [],
            }),
            "connection": {
                "status": "established",
                "established_at": existing.get("connection", {}).get(
                    "established_at", now
                ),
                "last_used_at": now,
            },
        }
        connections[key] = connection
        self._write(document)
        return connection

    def update_engineering(
        self,
        repository_path: str | Path,
        **values: Any,
    ) -> dict[str, Any] | None:
        """Update stored engineering knowledge without rediscovering the PDM link."""
        document = self._read()
        connection = document["connections"].get(self._key(repository_path))
        if connection is None:
            return None
        engineering = connection.setdefault("engineering", {})
        engineering.update(values)
        connection.setdefault("connection", {})["last_used_at"] = (
            datetime.now(timezone.utc).isoformat()
        )
        self._write(document)
        return connection
