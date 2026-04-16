from __future__ import annotations

import os
import unittest
from pathlib import Path

from pm_agent.database import DatabaseStore


TEST_TABLES = [
    "session_requirements",
    "chat_messages",
    "chat_sessions",
    "requirements",
    "workspace_task_records",
    "workspace_story_records",
    "workspace_insight_snapshots",
    "workspace_knowledge_update_records",
    "workspace_knowledge_update_module_diff_records",
    "workspace_confirmation_records",
    "workspace_recommendations",
    "workspace_managed_members",
    "workspace_module_entries",
    "workspaces",
    "workspace_states",
    "agent_states",
]


def get_test_database_url() -> str | None:
    return os.getenv("PM_AGENT_TEST_DATABASE_URL")


def require_test_database_url() -> str:
    database_url = get_test_database_url()
    if not database_url:
        raise unittest.SkipTest("PM_AGENT_TEST_DATABASE_URL 未配置")
    return database_url


def ensure_mysql_schema(database_url: str) -> DatabaseStore:
    store = DatabaseStore(database_url=database_url)
    ddl = Path("db/schema.mysql.ddl.sql").read_text(encoding="utf-8")
    statements = [statement.strip() for statement in ddl.split(";") if statement.strip()]
    with store.connection() as connection:
        cursor = connection.cursor()
        for statement in statements:
            cursor.execute(statement)
    return store


def reset_mysql_test_data(store: DatabaseStore) -> None:
    with store.connection() as connection:
        cursor = connection.cursor()
        for table in TEST_TABLES:
            cursor.execute(f"DELETE FROM {table}")
