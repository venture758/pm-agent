"""Chat domain repository — chat sessions and messages."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from ..database import DatabaseStore


class ChatRepository:
    def __init__(self, database: DatabaseStore) -> None:
        self._db = database

    # ---- Sessions ----

    def create_session(self, workspace_id: str) -> dict[str, Any]:
        """Create a new chat session. Archives any existing active session first."""
        now = datetime.utcnow().isoformat()
        session_id = f"cs-{now.replace(':', '').replace('-', '').replace('.', '')}"
        ph = self._db.placeholder

        # Archive existing active sessions
        with self._db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE chat_sessions SET status = 'archived' "
                f"WHERE workspace_id = {ph} AND status = 'active'",
                (workspace_id,),
            )

            cur.execute(
                f"INSERT INTO chat_sessions "
                f"(session_id, workspace_id, created_at, last_active_at, status, last_message_preview) "
                f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
                (session_id, workspace_id, now, now, "active", ""),
            )
            conn.commit()

        return {
            "session_id": session_id,
            "created_at": now,
            "last_active_at": now,
            "status": "active",
        }

    def archive_session(self, workspace_id: str, session_id: str) -> None:
        """Mark a specific session as archived."""
        ph = self._db.placeholder
        with self._db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE chat_sessions SET status = 'archived' "
                f"WHERE workspace_id = {ph} AND session_id = {ph}",
                (workspace_id, session_id),
            )
            conn.commit()

    def list_sessions(self, workspace_id: str) -> list[dict[str, Any]]:
        """List sessions for a workspace, ordered by last_active_at DESC."""
        ph = self._db.placeholder
        with self._db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT session_id, workspace_id, created_at, last_active_at, status, last_message_preview "
                f"FROM chat_sessions WHERE workspace_id = {ph} "
                f"ORDER BY last_active_at DESC",
                (workspace_id,),
            )
            rows = cur.fetchall() or []

        result = []
        for row in rows:
            get = (lambda k: row[k]) if isinstance(row, dict) or hasattr(row, "keys") else None
            result.append({
                "session_id": str(get("session_id") if get else row[0]),
                "workspace_id": str(get("workspace_id") if get else row[1]),
                "created_at": str(get("created_at") if get else row[2]),
                "last_active_at": str(get("last_active_at") if get else row[3]),
                "status": str(get("status") if get else row[4]),
                "last_message_preview": str(get("last_message_preview") if get else row[5]),
            })
        return result

    def get_session(self, workspace_id: str, session_id: str) -> dict[str, Any] | None:
        """Get a single session by ID."""
        ph = self._db.placeholder
        with self._db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT session_id, workspace_id, created_at, last_active_at, status, last_message_preview "
                f"FROM chat_sessions WHERE workspace_id = {ph} AND session_id = {ph}",
                (workspace_id, session_id),
            )
            row = cur.fetchone()

        if not row:
            return None
        get = (lambda k: row[k]) if isinstance(row, dict) or hasattr(row, "keys") else None
        return {
            "session_id": str(get("session_id") if get else row[0]),
            "workspace_id": str(get("workspace_id") if get else row[1]),
            "created_at": str(get("created_at") if get else row[2]),
            "last_active_at": str(get("last_active_at") if get else row[3]),
            "status": str(get("status") if get else row[4]),
            "last_message_preview": str(get("last_message_preview") if get else row[5]),
        }

    def delete_session(self, workspace_id: str, session_id: str) -> None:
        """Delete a session and its messages."""
        ph = self._db.placeholder
        with self._db.connection() as conn:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM chat_messages WHERE workspace_id = {ph} AND session_id = {ph}", (workspace_id, session_id))
            cur.execute(f"DELETE FROM chat_sessions WHERE workspace_id = {ph} AND session_id = {ph}", (workspace_id, session_id))
            conn.commit()

    def get_active_session_id(self, workspace_id: str) -> str | None:
        """Return the active session ID, or None."""
        ph = self._db.placeholder
        with self._db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT session_id FROM chat_sessions "
                f"WHERE workspace_id = {ph} AND status = 'active' "
                f"ORDER BY last_active_at DESC LIMIT 1",
                (workspace_id,),
            )
            row = cur.fetchone()
        return str(row[0]) if row else None

    # ---- Messages ----

    def append_message(
        self,
        workspace_id: str,
        session_id: str,
        role: str,
        content: str,
        timestamp: str | None = None,
        parsed_requirements: list[dict] | None = None,
    ) -> int:
        """Append a message to a session. Returns the message seq."""
        import json
        now = timestamp or datetime.utcnow().isoformat()
        ph = self._db.placeholder

        parsed_json = ""
        if parsed_requirements:
            parsed_json = json.dumps(parsed_requirements, ensure_ascii=False)

        with self._db.connection() as conn:
            cur = conn.cursor()
            # Get next seq
            cur.execute(
                f"SELECT COALESCE(MAX(seq), 0) + 1 FROM chat_messages "
                f"WHERE session_id = {ph}",
                (session_id,),
            )
            seq = int(cur.fetchone()[0])

            cur.execute(
                f"INSERT INTO chat_messages (workspace_id, session_id, seq, role, content, timestamp, parsed_requirements_json) "
                f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
                (workspace_id, session_id, seq, role, content, now, parsed_json),
            )

            # Update session last_active_at and preview
            if role == "user":
                preview = content[:50]
                cur.execute(
                    f"UPDATE chat_sessions SET last_active_at = {ph}, last_message_preview = {ph} "
                    f"WHERE session_id = {ph}",
                    (now, preview, session_id),
                )
            conn.commit()

        return seq

    def load_messages(self, workspace_id: str, session_id: str) -> list[dict[str, Any]]:
        """Load messages for a session, ordered by seq ASC."""
        import json
        ph = self._db.placeholder
        with self._db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT role, content, timestamp, parsed_requirements_json, seq "
                f"FROM chat_messages WHERE workspace_id = {ph} AND session_id = {ph} "
                f"ORDER BY seq ASC",
                (workspace_id, session_id),
            )
            rows = cur.fetchall() or []

        result = []
        for row in rows:
            get = (lambda k: row[k]) if isinstance(row, dict) or hasattr(row, "keys") else None
            parsed = get("parsed_requirements_json") if get else row[3]
            result.append({
                "role": str(get("role") if get else row[0]),
                "content": str(get("content") if get else row[1]),
                "timestamp": str(get("timestamp") if get else row[2]),
                "parsed_requirements": json.loads(parsed) if parsed else [],
            })
        return result
