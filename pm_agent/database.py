from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import parse_qs, unquote, urlparse

from .config import DEFAULT_MYSQL_DDL_PATH


def _json_default(obj: Any) -> Any:
    """自定义 JSON 序列化默认值，处理 MySQL 返回的 Decimal 等类型。"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


class DatabaseStore:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = self._resolve_database_url(database_url)
        self.scheme, self.connection_config = self._parse_database_url(self.database_url)
        self.mysql_driver: str | None = None
        self.mysql_module: Any = None
        self.mysql_driver, self.mysql_module = self._load_mysql_driver()

    def _resolve_database_url(self, database_url: str | None) -> str:
        candidate = database_url
        if candidate is None:
            candidate = os.environ.get("PM_AGENT_DATABASE_URL")
        if candidate:
            return str(candidate)
        raise ValueError("缺少数据库连接配置：请传入 database_url 或设置 PM_AGENT_DATABASE_URL")

    def _parse_database_url(self, database_url: str) -> tuple[str, dict[str, Any]]:
        parsed = urlparse(database_url)
        scheme = parsed.scheme.lower()
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
        if scheme == "sqlite":
            raise ValueError("项目仅支持 MySQL 数据库，禁止使用 sqlite:// 连接串")
        raise ValueError(f"不支持的数据库地址：{database_url}；项目仅支持 MySQL")

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
        return "%s"

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

    def _raise_schema_hint_if_needed(self, exc: Exception) -> None:
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
        return json.loads(row[0])

    def save_json(self, table_name: str, key_column: str, key_value: str, payload: dict[str, Any]) -> None:
        serialized = json.dumps(payload, ensure_ascii=False, default=_json_default)
        updated_at = payload.get("updated_at") or datetime.utcnow().isoformat()
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
