"""Persistent repository ↔ PDM links used by Maintenance.

The registry stores confirmed relationships so Maintenance can reopen a known
published repository without rediscovering the PDM relationship.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from services.base_service import BaseService


class MaintenanceRepositoryLinkService(BaseService):
    """Persist and query confirmed Repository ↔ PDM relationships."""

    VERSION = 1
    OCD_FILE = "pcr_data_com_ocd.mdb"

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
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(document, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        temporary.replace(path)

    def list_connections(self) -> list[dict[str, Any]]:
        """Return established links, ordered by repository path."""
        values = list(self._read()["connections"].values())
        return sorted(
            values,
            key=lambda item: str(item.get("repository", {}).get("path", "")).casefold(),
        )

    def get(self, repository_path: str | Path) -> dict[str, Any] | None:
        return self._read()["connections"].get(self._key(repository_path))

    def inspect_repository(self, repository_path: str | Path) -> dict[str, Any]:
        """Read only package identity needed to establish a link."""
        folder = Path(repository_path)
        if not folder.is_dir():
            raise ValueError("Selected repository folder does not exist.")

        mdb_path = folder / self.OCD_FILE
        if not mdb_path.is_file():
            raise ValueError(
                f"Repository does not contain {self.OCD_FILE}."
            )

        rows = self.context.mdb_service.read_table(
            mdb_path,
            "SELECT reg_ProgramCode, reg_VersionMajor, reg_VersionMinor, "
            "reg_VersionBuild FROM tCOMd_Package",
        )
        row = rows[0] if rows else {}
        version_parts = [
            row.get("reg_VersionMajor"),
            row.get("reg_VersionMinor"),
            row.get("reg_VersionBuild"),
        ]
        version = ".".join(str(value) for value in version_parts) if all(
            value is not None for value in version_parts
        ) else ""

        return {
            "path": str(folder.resolve()),
            "name": folder.name,
            "code": str(row.get("reg_ProgramCode") or folder.name),
            "version": version,
            "ocd_path": str(mdb_path),
        }

    def establish(
        self,
        *,
        repository: dict[str, Any],
        pdm_candidate: Any,
    ) -> dict[str, Any]:
        """Persist a confirmed repository/product relationship."""
        document = self._read()
        connections = document["connections"]
        key = self._key(repository["path"])
        now = datetime.now(timezone.utc).isoformat()
        existing = connections.get(key, {})

        connection = {
            "repository": {
                "path": repository["path"],
                "name": repository["name"],
                "code": repository["code"],
                "category": str(getattr(pdm_candidate, "category", "") or ""),
                "version": repository.get("version", ""),
            },
            "pdm": {
                "product_id": str(getattr(pdm_candidate, "id", "") or ""),
                "product_name": str(getattr(pdm_candidate, "name", "") or ""),
                "product_code": str(getattr(pdm_candidate, "code", "") or ""),
                "category": str(getattr(pdm_candidate, "category", "") or ""),
                "range": str(getattr(pdm_candidate, "range_name", "") or ""),
                "catalogue": str(getattr(pdm_candidate, "description", "") or ""),
            },
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

    def touch(self, repository_path: str | Path) -> dict[str, Any] | None:
        """Mark an existing link as used."""
        document = self._read()
        connection = document["connections"].get(self._key(repository_path))
        if connection is None:
            return None
        connection.setdefault("connection", {})["last_used_at"] = (
            datetime.now(timezone.utc).isoformat()
        )
        self._write(document)
        return connection
