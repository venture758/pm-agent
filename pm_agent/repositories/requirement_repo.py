"""Requirement domain repository — requirements and session mappings."""
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Iterable, Mapping

from ..database import DatabaseStore
from ..utils import normalize_requirement_id


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


class RequirementRepository:
    def __init__(self, database: DatabaseStore) -> None:
        self._db = database

    def upsert_requirements(
        self,
        workspace_id: str,
        requirements: Iterable[Mapping[str, Any]],
    ) -> int:
        """Upsert a batch of requirements. Returns count inserted/updated."""
        ph = self._db.placeholder
        now = datetime.utcnow().isoformat()
        count = 0

        with self._db.connection() as conn:
            cur = conn.cursor()
            for req in requirements:
                req_id = normalize_requirement_id(req.get("requirement_id", ""))
                if not req_id:
                    continue
                base_sql = (
                    f"INSERT INTO requirements "
                    f"(workspace_id, requirement_id, title, source, priority, raw_text, complexity, risk, requirement_type, source_url, source_message, payload_json, created_at) "
                    f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}) "
                    f"ON DUPLICATE KEY UPDATE "
                    f"title=VALUES(title), payload_json=VALUES(payload_json)"
                )
                cur.execute(
                    base_sql,
                    (
                        workspace_id,
                        req_id,
                        str(req.get("title", "")),
                        str(req.get("source", "chat")),
                        str(req.get("priority", "中")),
                        str(req.get("raw_text", "")),
                        str(req.get("complexity", "中")),
                        str(req.get("risk", "中")),
                        str(req.get("requirement_type", "")),
                        str(req.get("source_url", "")),
                        str(req.get("source_message", "")),
                        json.dumps(dict(req), ensure_ascii=False, default=_json_default),
                        now,
                    ),
                )
                count += 1
            conn.commit()

        return count

    def list_requirements(self, workspace_id: str) -> list[dict[str, Any]]:
        """List all requirements for a workspace in insertion order."""
        ph = self._db.placeholder
        with self._db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT requirement_id, payload_json FROM requirements "
                f"WHERE workspace_id = {ph} ORDER BY id",
                (workspace_id,),
            )
            rows = cur.fetchall() or []

        result = []
        for row in rows:
            get = (lambda k: row[k]) if isinstance(row, dict) or hasattr(row, "keys") else None
            payload = json.loads(get("payload_json") if get else row[1])
            result.append(payload)
        return result

    def associate_session_requirements(
        self,
        session_id: str,
        requirement_ids: Iterable[str],
    ) -> int:
        """Link requirements to a session. Returns count linked."""
        ph = self._db.placeholder
        count = 0

        with self._db.connection() as conn:
            cur = conn.cursor()
            for req_id in requirement_ids:
                norm_id = normalize_requirement_id(req_id)
                if not norm_id:
                    continue
                sql = (
                    f"INSERT INTO session_requirements (session_id, requirement_id) "
                    f"VALUES ({ph}, {ph}) "
                    f"ON DUPLICATE KEY UPDATE session_id=session_id"
                )
                cur.execute(sql, (session_id, norm_id))
                count += 1
            conn.commit()

        return count

    def clear_session_requirements(self, session_id: str) -> None:
        """Remove all requirement links for a session."""
        ph = self._db.placeholder
        with self._db.connection() as conn:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM session_requirements WHERE session_id = {ph}", (session_id,))
            conn.commit()

    def get_session_requirement_ids(self, session_id: str) -> list[str]:
        """Get requirement IDs associated with a session."""
        ph = self._db.placeholder
        with self._db.connection() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT requirement_id FROM session_requirements WHERE session_id = {ph}",
                (session_id,),
            )
            rows = cur.fetchall() or []
        return [str(row[0]) if not isinstance(row, dict) else str(row["requirement_id"]) for row in rows]
