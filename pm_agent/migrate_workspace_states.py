"""Migration: Split workspace_states JSON payload into dedicated tables.

Reads existing workspace_states records, extracts chat sessions/messages,
requirements, and workspace metadata, then writes them to the new tables.

Usage:
    python -m pm_agent.migrate_workspace_states --database-url mysql://user:pass@host:3306/dbname

Dry run (no writes):
    python -m pm_agent.migrate_workspace_states --database-url mysql://user:pass@host:3306/dbname --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from urllib.parse import parse_qs, unquote, urlparse

logger = logging.getLogger(__name__)


def _json_default(obj):
    from decimal import Decimal

    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def parse_args():
    parser = argparse.ArgumentParser(description="Migrate workspace_states JSON to dedicated tables")
    parser.add_argument("--database-url", required=True, help="MySQL database URL, for example mysql://user:pass@host:3306/dbname")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    return parser.parse_args()


def get_connection(database_url: str):
    """Return a raw MySQL DBAPI connection."""
    parsed = urlparse(database_url)
    scheme = parsed.scheme.lower()
    if scheme not in {"mysql", "mysql+pymysql", "mysql+mysqlconnector", "mysql+mysqldb"}:
        if scheme == "sqlite":
            raise ValueError("项目仅支持 MySQL 数据库，迁移脚本不再支持 sqlite://")
        raise ValueError(f"不支持的数据库地址：{database_url}；项目仅支持 MySQL")
    database = unquote(parsed.path.lstrip("/"))
    if not database:
        raise ValueError("MySQL 连接串缺少数据库名，请使用 mysql://user:pass@host:3306/dbname")
    try:
        import pymysql

        driver = "pymysql"
        module = pymysql
    except ImportError:
        import mysql.connector

        driver = "mysql.connector"
        module = mysql.connector
    params = {
        "host": parsed.hostname or "127.0.0.1",
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": database,
        "charset": parse_qs(parsed.query).get("charset", ["utf8mb4"])[-1],
    }
    if driver == "mysql.connector":
        params["use_pure"] = True
    return module.connect(**params)


def load_workspace_states(conn):
    """Load all workspace_states rows."""
    cursor = conn.cursor()
    cursor.execute(f"SELECT workspace_id, payload FROM workspace_states")
    rows = cursor.fetchall()
    conn.commit()
    return rows


def migrate_one_workspace(conn, workspace_id: str, payload: str, dry_run: bool) -> dict:
    """Migrate a single workspace payload to new tables. Returns stats."""
    stats = {
        "workspace_id": workspace_id,
        "workspaces_created": 0,
        "sessions_created": 0,
        "messages_created": 0,
        "requirements_created": 0,
        "session_reqs_created": 0,
        "errors": [],
    }
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as e:
        stats["errors"].append(f"Invalid JSON: {e}")
        return stats

    ph = "%s"
    now = datetime.utcnow().isoformat()
    workspace_title = data.get("title") or workspace_id
    target_session_id = ""

    # 1. Upsert workspaces metadata
    if not dry_run:
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT INTO workspaces (workspace_id, title, created_at, updated_at) "
            f"VALUES ({ph}, {ph}, {ph}, {ph}) "
            f"ON DUPLICATE KEY UPDATE title=VALUES(title), updated_at=VALUES(updated_at)",
            (workspace_id, workspace_title, data.get("updated_at", now), data.get("updated_at", now)),
        )
        stats["workspaces_created"] = 1

    # 2. Migrate chat_sessions from payload
    chat_sessions = data.get("chat_sessions", [])
    active_session_id = data.get("active_session_id", "")

    if chat_sessions and not dry_run:
        cursor = conn.cursor()
        for session in chat_sessions:
            session_id = session.get("session_id")
            if not session_id:
                continue
            cursor.execute(
                f"INSERT INTO chat_sessions (session_id, workspace_id, created_at, last_active_at, status, last_message_preview) "
                f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}) "
                f"ON DUPLICATE KEY UPDATE "
                f"last_active_at=VALUES(last_active_at), status=VALUES(status), "
                f"last_message_preview=VALUES(last_message_preview)",
                (
                    session_id,
                    workspace_id,
                    session.get("created_at", now),
                    session.get("last_active_at", now),
                    session.get("status", "active"),
                    session.get("last_message_preview", ""),
                ),
            )
            stats["sessions_created"] += 1

    # 3. Migrate chat_messages from payload
    chat_messages = data.get("chat_messages", [])
    if chat_messages and not dry_run:
        # Find active session to associate messages with
        target_session_id = active_session_id
        if not target_session_id and chat_sessions:
            # Find the most recently active session
            active = [s for s in chat_sessions if s.get("status") == "active"]
            if active:
                target_session_id = max(active, key=lambda s: s.get("last_active_at", ""))["session_id"]

        if target_session_id:
            cursor = conn.cursor()
            for seq_idx, msg in enumerate(chat_messages):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                timestamp = msg.get("timestamp", now)
                parsed = msg.get("parsed_requirements", [])
                cursor.execute(
                    f"INSERT INTO chat_messages (workspace_id, session_id, seq, role, content, timestamp, parsed_requirements_json) "
                    f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})",
                    (
                        workspace_id,
                        target_session_id,
                        seq_idx + 1,
                        role,
                        content,
                        timestamp,
                        json.dumps(parsed, ensure_ascii=False, default=_json_default) if parsed else "",
                    ),
                )
                stats["messages_created"] += 1

    # 4. Migrate requirements from payload
    normalized_reqs = data.get("normalized_requirements", [])
    if normalized_reqs and not dry_run:
        cursor = conn.cursor()
        for req in normalized_reqs:
            req_id = req.get("requirement_id", "")
            if not req_id:
                continue
            cursor.execute(
                f"INSERT INTO requirements (workspace_id, requirement_id, title, source, priority, raw_text, complexity, risk, requirement_type, source_url, source_message, payload_json, created_at) "
                f"VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}) "
                f"ON DUPLICATE KEY UPDATE title=VALUES(title), payload_json=VALUES(payload_json)",
                (
                    workspace_id,
                    req_id,
                    req.get("title", ""),
                    req.get("source", "chat"),
                    req.get("priority", "中"),
                    req.get("raw_text", ""),
                    req.get("complexity", "中"),
                    req.get("risk", "中"),
                    req.get("requirement_type", ""),
                    req.get("source_url", ""),
                    req.get("source_message", ""),
                    json.dumps(req, ensure_ascii=False, default=_json_default),
                    now,
                ),
            )
            stats["requirements_created"] += 1

        # Also create session_requirements links
        session_req_ids = data.get("current_session_requirement_ids", [])
        if target_session_id and session_req_ids and not dry_run:
            for req_id in session_req_ids:
                cursor.execute(
                    f"INSERT INTO session_requirements (session_id, requirement_id) VALUES ({ph}, {ph}) "
                    f"ON DUPLICATE KEY UPDATE session_id=VALUES(session_id)",
                    (target_session_id, req_id),
                )
                stats["session_reqs_created"] += 1

    if not dry_run:
        conn.commit()

    return stats


def main():
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    conn = get_connection(args.database_url)
    mode = "DRY RUN" if args.dry_run else "MIGRATION"
    logger.info(f"Starting {mode} for {args.database_url} (scheme=mysql)")

    rows = load_workspace_states(conn)
    logger.info(f"Found {len(rows)} workspace(s) in workspace_states")

    total_stats = {
        "workspaces": 0,
        "sessions": 0,
        "messages": 0,
        "requirements": 0,
        "session_reqs": 0,
        "errors": 0,
    }

    for workspace_id, payload_text in rows:
        payload_str = payload_text if isinstance(payload_text, str) else payload_text.decode("utf-8")
        result = migrate_one_workspace(conn, workspace_id, payload_str, args.dry_run)
        total_stats["workspaces"] += result["workspaces_created"]
        total_stats["sessions"] += result["sessions_created"]
        total_stats["messages"] += result["messages_created"]
        total_stats["requirements"] += result["requirements_created"]
        total_stats["session_reqs"] += result["session_reqs_created"]
        total_stats["errors"] += len(result["errors"])
        for err in result["errors"]:
            logger.error(f"  {workspace_id}: {err}")

    logger.info(f"\n{mode} complete:")
    logger.info(f"  workspaces: {total_stats['workspaces']}")
    logger.info(f"  sessions:   {total_stats['sessions']}")
    logger.info(f"  messages:   {total_stats['messages']}")
    logger.info(f"  requirements: {total_stats['requirements']}")
    logger.info(f"  session_requirements: {total_stats['session_reqs']}")
    if total_stats["errors"]:
        logger.warning(f"  errors: {total_stats['errors']}")

    conn.close()
    return 0 if not total_stats["errors"] else 1


if __name__ == "__main__":
    sys.exit(main())
