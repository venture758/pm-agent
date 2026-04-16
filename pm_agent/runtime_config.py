from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse


DEFAULT_CONFIG_PATH = Path("config/pm_agent.toml")
DEFAULT_ENV_NAME = "dev"


@dataclass(frozen=True)
class WebRuntimeConfig:
    env: str
    config_path: Path
    host: str
    port: int
    static_root: str
    database_url: str
    nvidia_api_key: str


def load_web_runtime_config(
    *,
    config_path: str | Path | None = None,
    env_name: str | None = None,
    cli_overrides: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> WebRuntimeConfig:
    envvars = dict(os.environ if environ is None else environ)
    resolved_env = str(env_name or envvars.get("PM_AGENT_ENV") or DEFAULT_ENV_NAME)
    resolved_path = Path(config_path or envvars.get("PM_AGENT_CONFIG") or DEFAULT_CONFIG_PATH)
    file_values = _load_config_file(resolved_path, resolved_env)
    overrides = dict(cli_overrides or {})

    host = _resolve_value("host", file_values, envvars, overrides, default="127.0.0.1")
    port_raw = _resolve_value("port", file_values, envvars, overrides, default=8000)
    static_root = _resolve_value("static_root", file_values, envvars, overrides, default="frontend/dist")
    database_url = _resolve_value("database_url", file_values, envvars, overrides, default="")
    nvidia_api_key = _resolve_value("nvidia_api_key", file_values, envvars, overrides, default="")
    normalized_database_url = _validate_database_url(str(database_url or ""), resolved_path, resolved_env)

    return WebRuntimeConfig(
        env=resolved_env,
        config_path=resolved_path,
        host=str(host),
        port=int(port_raw),
        static_root=str(static_root),
        database_url=normalized_database_url,
        nvidia_api_key=str(nvidia_api_key or ""),
    )


def _load_config_file(path: Path, env_name: str) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = tomllib.loads(path.read_text(encoding="utf-8"))
    default_section = payload.get("default") or {}
    env_section = payload.get(env_name) or {}
    if not isinstance(default_section, dict):
        raise ValueError(f"配置文件 default 段格式错误: {path}")
    if not isinstance(env_section, dict):
        raise ValueError(f"配置文件 {env_name} 段格式错误: {path}")
    return {**default_section, **env_section}


def _resolve_value(
    key: str,
    file_values: Mapping[str, Any],
    environ: Mapping[str, str],
    overrides: Mapping[str, Any],
    *,
    default: Any,
) -> Any:
    cli_value = overrides.get(key)
    if cli_value not in (None, ""):
        return cli_value

    env_key = {
        "host": "PM_AGENT_HOST",
        "port": "PM_AGENT_PORT",
        "static_root": "PM_AGENT_STATIC_ROOT",
        "database_url": "PM_AGENT_DATABASE_URL",
        "nvidia_api_key": "NVIDIA_NIM_API_KEY",
    }[key]
    env_value = environ.get(env_key)
    if env_value not in (None, ""):
        return env_value

    file_value = file_values.get(key)
    if file_value not in (None, ""):
        return file_value

    return default


def _validate_database_url(database_url: str, config_path: Path, env_name: str) -> str:
    if not database_url:
        return ""
    scheme = urlparse(database_url).scheme.lower()
    if scheme == "sqlite":
        raise ValueError(
            f"项目仅支持 MySQL 数据库；请在 {config_path} 的 [{env_name}] 或 [default] 段配置 mysql:// 连接串，"
            "或设置 PM_AGENT_DATABASE_URL 为 MySQL 地址"
        )
    if scheme not in {"mysql", "mysql+pymysql", "mysql+mysqlconnector", "mysql+mysqldb"}:
        raise ValueError(f"不支持的数据库地址：{database_url}；项目仅支持 MySQL")
    return database_url
