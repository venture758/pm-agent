from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import parse_qs, unquote, urlparse

from .config import DEFAULT_DATABASE_FILENAME, DEFAULT_MYSQL_DDL_PATH, DEFAULT_STATE_ROOT


def _json_default(obj: Any) -> Any:
    """自定义 JSON 序列化默认值，处理 MySQL 返回的 Decimal 等类型。"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


class DatabaseStore:
    def __init__(self, root: str | Path = DEFAULT_STATE_ROOT, database_url: str | None = None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.database_url = self._resolve_database_url(database_url)
        self.scheme, self.connection_config = self._parse_database_url(self.database_url)
        self.mysql_driver: str | None = None
        self.mysql_module: Any = None
        if self.scheme == "mysql":
            self.mysql_driver, self.mysql_module = self._load_mysql_driver()
        else:
            self._ensure_sqlite_schema()

    def _resolve_database_url(self, database_url: str | None) -> str:
        candidate = database_url or os.getenv("PM_AGENT_DATABASE_URL")
        if candidate:
            return str(candidate)
        db_path = (self.root / DEFAULT_DATABASE_FILENAME).resolve()
        return f"sqlite:///{db_path}"

    def _parse_database_url(self, database_url: str) -> tuple[str, dict[str, Any]]:
        parsed = urlparse(database_url)
        scheme = parsed.scheme.lower()
        if scheme == "sqlite":
            if parsed.netloc and parsed.path:
                raw_path = f"//{parsed.netloc}{parsed.path}"
            else:
                raw_path = parsed.path
            path = Path(unquote(raw_path)).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            return "sqlite", {"path": str(path)}
        if scheme in {"mysql", "mysql+pymysql", "mysql+mysqlconnector", "mysql+mysqldb"}:
            database = unquote(parsed.path.lstrip("/"))
            if not database:
                raise ValueError("MySQL 连接串缺少数据库名，请使用 mysql://user:pass@host:3306/dbname")
            return (
                "mysql",
                {
                    "host": parsed.hostname or "127.0.0.1",
                    "port": parsed.port or 3306,
                    "user": unquote(parsed.username or ""),
                    "password": unquote(parsed.password or ""),
                    "database": database,
                    "params": {key: values[-1] for key, values in parse_qs(parsed.query).items()},
                },
            )
        raise ValueError(f"不支持的数据库地址：{database_url}")

    def _load_mysql_driver(self) -> tuple[str, Any]:
        try:
            import pymysql

            return "pymysql", pymysql
        except ImportError:
            pass
        try:
            import mysql.connector

            return "mysql.connector", mysql.connector
        except ImportError:
            pass
        try:
            import MySQLdb

            return "MySQLdb", MySQLdb
        except ImportError as exc:
            raise RuntimeError("未安装 MySQL 驱动，请安装 PyMySQL 或 mysql-connector-python") from exc

    @property
    def placeholder(self) -> str:
        return "?" if self.scheme == "sqlite" else "%s"

    @property
    def mysql_ddl_path(self) -> Path:
        return Path(DEFAULT_MYSQL_DDL_PATH)

    @contextmanager
    def connection(self) -> Iterator[Any]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _connect(self):
        if self.scheme == "sqlite":
            connection = sqlite3.connect(self.connection_config["path"])
            connection.row_factory = sqlite3.Row
            return connection

        params = dict(self.connection_config)
        params.pop("params", None)
        if self.mysql_driver == "pymysql":
            params["charset"] = self.connection_config["params"].get("charset", "utf8mb4")
            return self.mysql_module.connect(**params)
        if self.mysql_driver == "mysql.connector":
            params["charset"] = self.connection_config["params"].get("charset", "utf8mb4")
            return self.mysql_module.connect(**params)
        params["db"] = params.pop("database")
        params["passwd"] = params.pop("password")
        params["charset"] = self.connection_config["params"].get("charset", "utf8mb4")
        return self.mysql_module.connect(**params)

    def _ensure_sqlite_schema(self) -> None:
        statements = [
            (
                "CREATE TABLE IF NOT EXISTS workspace_states ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "workspace_id TEXT NOT NULL UNIQUE, "
                "payload TEXT NOT NULL, "
                "updated_at TEXT NOT NULL)"
            ),
            (
                "CREATE TABLE IF NOT EXISTS agent_states ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "state_key TEXT NOT NULL UNIQUE, "
                "payload TEXT NOT NULL, "
                "updated_at TEXT NOT NULL)"
            ),
            (
                "CREATE TABLE IF NOT EXISTS workspace_module_entries ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "workspace_id TEXT NOT NULL, "
                "module_key TEXT NOT NULL, "
                "big_module TEXT NOT NULL, "
                "function_module TEXT NOT NULL, "
                "primary_owner TEXT NOT NULL, "
                "backup_owners_json TEXT NOT NULL, "
                "familiar_members_json TEXT NOT NULL, "
                "aware_members_json TEXT NOT NULL, "
                "unfamiliar_members_json TEXT NOT NULL, "
                "source_sheet TEXT NOT NULL DEFAULT '', "
                "source_year INTEGER NOT NULL DEFAULT 0, "
                "imported_at TEXT NOT NULL, "
                "recent_assignees_json TEXT NOT NULL, "
                "suggested_familiarity_json TEXT NOT NULL, "
                "assignment_history_json TEXT NOT NULL, "
                "updated_at TEXT NOT NULL, "
                "UNIQUE(workspace_id, module_key))"
            ),
            (
                "CREATE TABLE IF NOT EXISTS workspace_managed_members ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "workspace_id TEXT NOT NULL, "
                "member_name TEXT NOT NULL, "
                "role TEXT NOT NULL, "
                "skills_json TEXT NOT NULL, "
                "experience_level TEXT NOT NULL, "
                "workload REAL NOT NULL DEFAULT 0, "
                "capacity REAL NOT NULL DEFAULT 1, "
                "constraints_json TEXT NOT NULL, "
                "updated_at TEXT NOT NULL, "
                "UNIQUE(workspace_id, member_name))"
            ),
            (
                "CREATE TABLE IF NOT EXISTS workspace_recommendations ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "workspace_id TEXT NOT NULL, "
                "requirement_id TEXT NOT NULL, "
                "payload_json TEXT NOT NULL, "
                "created_at TEXT NOT NULL, "
                "updated_at TEXT NOT NULL, "
                "UNIQUE(workspace_id, requirement_id))"
            ),
            (
                "CREATE TABLE IF NOT EXISTS workspace_confirmation_records ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "workspace_id TEXT NOT NULL, "
                "session_id TEXT NOT NULL, "
                "confirmed_count INTEGER NOT NULL, "
                "payload_json TEXT NOT NULL, "
                "created_at TEXT NOT NULL)"
            ),
            (
                "CREATE TABLE IF NOT EXISTS workspace_knowledge_update_records ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "workspace_id TEXT NOT NULL, "
                "session_id TEXT NOT NULL, "
                "status TEXT NOT NULL, "
                "payload_json TEXT NOT NULL, "
                "created_at TEXT NOT NULL)"
            ),
            (
                "CREATE TABLE IF NOT EXISTS workspace_insight_snapshots ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "workspace_id TEXT NOT NULL, "
                "snapshot_at TEXT NOT NULL, "
                "heatmap_json TEXT NOT NULL, "
                "single_points_json TEXT NOT NULL, "
                "growth_suggestions_json TEXT NOT NULL, "
                "summary_json TEXT NOT NULL)"
            ),
            (
                "CREATE TABLE IF NOT EXISTS workspace_story_records ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "workspace_id TEXT NOT NULL, "
                "user_story_code TEXT NOT NULL, "
                "sequence_no INTEGER, "
                "user_story_name TEXT, "
                "user_story_tag TEXT, "
                "status TEXT, "
                "remark TEXT, "
                "plan_test_completion_time TEXT, "
                "related_task_count REAL, "
                "planned_person_days REAL, "
                "owner_names TEXT, "
                "tester_names TEXT, "
                "requirement_owner_names TEXT, "
                "product TEXT, "
                "created_time TEXT, "
                "created_by TEXT, "
                "actual_person_days REAL, "
                "planned_dev_person_days REAL, "
                "related_defect_count REAL, "
                "version TEXT, "
                "priority TEXT, "
                "absolute_priority REAL, "
                "related_case_count REAL, "
                "plan_trunk_test_completion_time TEXT, "
                "modified_time TEXT, "
                "acceptance_criteria TEXT, "
                "detail_url TEXT, "
                "project_status TEXT, "
                "iteration_phase TEXT, "
                "iteration_goal TEXT, "
                "release_plan TEXT, "
                "release_window TEXT, "
                "scrum_team TEXT, "
                "product_group TEXT, "
                "project_name TEXT, "
                "ksm_or_bug_no TEXT, "
                "story_type TEXT, "
                "cloud_name TEXT, "
                "application_name TEXT, "
                "related_story TEXT, "
                "related_requirement TEXT, "
                "completed_time TEXT, "
                "plan_baseline_test_completion_time TEXT, "
                "developer_names TEXT, "
                "has_upgrade_notice TEXT, "
                "change_type TEXT, "
                "imported_at TEXT NOT NULL, "
                "updated_at TEXT NOT NULL, "
                "UNIQUE(workspace_id, user_story_code))"
            ),
            (
                "CREATE TABLE IF NOT EXISTS workspace_task_records ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "workspace_id TEXT NOT NULL, "
                "task_code TEXT NOT NULL, "
                "sequence_no INTEGER, "
                "related_story TEXT, "
                "name TEXT, "
                "task_type TEXT, "
                "owner TEXT, "
                "status TEXT, "
                "estimated_start TEXT, "
                "estimated_end TEXT, "
                "remark TEXT, "
                "completed_time TEXT, "
                "planned_person_days REAL, "
                "actual_person_days REAL, "
                "product TEXT, "
                "module_path TEXT, "
                "project_name TEXT, "
                "version TEXT, "
                "iteration_phase TEXT, "
                "project_group TEXT, "
                "participants TEXT, "
                "customer_name TEXT, "
                "defect_count REAL, "
                "related_code TEXT, "
                "created_by TEXT, "
                "created_time TEXT, "
                "modified_by TEXT, "
                "modified_time TEXT, "
                "imported_at TEXT NOT NULL, "
                "updated_at TEXT NOT NULL, "
                "UNIQUE(workspace_id, task_code))"
            ),
        ]
        with self.connection() as connection:
            cursor = connection.cursor()
            for statement in statements:
                cursor.execute(statement)

    def _raise_schema_hint_if_needed(self, exc: Exception) -> None:
        if self.scheme != "mysql":
            return
        text = str(exc).lower()
        if "1146" in text or "doesn't exist" in text or "does not exist" in text:
            raise RuntimeError(
                f"MySQL 表不存在，请先执行 DDL：{self.mysql_ddl_path}"
            ) from exc

    def load_json(self, table_name: str, key_column: str, key_value: str) -> dict[str, Any] | None:
        sql = f"SELECT payload FROM {table_name} WHERE {key_column} = {self.placeholder}"
        try:
            with self.connection() as connection:
                cursor = connection.cursor()
                cursor.execute(sql, (key_value,))
                row = cursor.fetchone()
        except Exception as exc:
            self._raise_schema_hint_if_needed(exc)
            raise
        if not row:
            return None
        if isinstance(row, sqlite3.Row):
            payload = row["payload"]
        else:
            payload = row[0]
        return json.loads(payload)

    def save_json(self, table_name: str, key_column: str, key_value: str, payload: dict[str, Any]) -> None:
        serialized = json.dumps(payload, ensure_ascii=False, default=_json_default)
        updated_at = payload.get("updated_at") or datetime.utcnow().isoformat()
        if self.scheme == "sqlite":
            sql = (
                f"INSERT INTO {table_name} ({key_column}, payload, updated_at) VALUES (?, ?, ?) "
                f"ON CONFLICT({key_column}) DO UPDATE SET payload = excluded.payload, updated_at = excluded.updated_at"
            )
        else:
            sql = (
                f"INSERT INTO {table_name} ({key_column}, payload, updated_at) VALUES (%s, %s, %s) "
                f"ON DUPLICATE KEY UPDATE payload = VALUES(payload), updated_at = VALUES(updated_at)"
            )
        try:
            with self.connection() as connection:
                cursor = connection.cursor()
                cursor.execute(sql, (key_value, serialized, updated_at))
        except Exception as exc:
            self._raise_schema_hint_if_needed(exc)
            raise
