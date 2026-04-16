"""Workspace metadata repository — lightweight workspace info."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from ..database import DatabaseStore


class WorkspaceMetaRepository:
    def __init__(self, database: DatabaseStore) -> None:
        self._db = database

    def get_workspace(self, workspace_id: str) -> dict[str, Any] | None:
        """Get workspace metadata."""
        ph = self._db.placeholder
        with self._db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT workspace_id, title, created_at, updated_at "
                f"FROM workspaces WHERE workspace_id = {ph}",
                (workspace_id,),
            )
            row = cur.fetchone()

        if not row:
            return None
        get = (lambda k: row[k]) if isinstance(row, dict) or hasattr(row, "keys") else None
        return {
            "workspace_id": str(get("workspace_id") if get else row[0]),
            "title": str(get("title") if get else row[1]),
            "created_at": str(get("created_at") if get else row[2]),
            "updated_at": str(get("updated_at") if get else row[3]),
        }

    def create_workspace(self, workspace_id: str, title: str = "") -> dict[str, Any]:
        """Create or get workspace metadata."""
        now = datetime.utcnow().isoformat()
        ph = self._db.placeholder
        title = title or workspace_id

        with self._db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"INSERT INTO workspaces (workspace_id, title, created_at, updated_at) "
                f"VALUES ({ph}, {ph}, {ph}, {ph}) "
                f"ON DUPLICATE KEY UPDATE title = VALUES(title), updated_at = VALUES(updated_at)",
                (workspace_id, title, now, now),
            )
            conn.commit()

        return {
            "workspace_id": workspace_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
        }

    def update_workspace(self, workspace_id: str, title: str | None = None) -> dict[str, Any]:
        """Update workspace fields."""
        now = datetime.utcnow().isoformat()
        ph = self._db.placeholder

        with self._db.connection() as conn:
            cur = conn.cursor()
            if title is not None:
                cur.execute(
                    f"UPDATE workspaces SET title = {ph}, updated_at = {ph} WHERE workspace_id = {ph}",
                    (title, now, workspace_id),
                )
            else:
                cur.execute(
                    f"UPDATE workspaces SET updated_at = {ph} WHERE workspace_id = {ph}",
                    (now, workspace_id),
                )
            conn.commit()

        return self.get_workspace(workspace_id) or {}
