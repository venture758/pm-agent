from __future__ import annotations

import argparse
import logging
from wsgiref.simple_server import make_server

from pm_agent.api import create_api_app
from pm_agent.runtime_config import load_web_runtime_config

## lsof -nP -iTCP:8000 -sTCP:LISTEN
def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Run the project manager agent web API.")
    parser.add_argument("--env", default=None, help="Config environment name. Defaults to PM_AGENT_ENV or dev.")
    parser.add_argument("--config", default=None, help="Config file path. Defaults to PM_AGENT_CONFIG or config/pm_agent.toml.")
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", default=None, type=int)
    parser.add_argument("--static-root", default=None)
    parser.add_argument(
        "--database-url",
        default=None,
        help="Optional override. Example: mysql://user:pass@127.0.0.1:3306/pm_agent?charset=utf8mb4",
    )
    parser.add_argument(
        "--nvidia-api-key",
        default=None,
        help="Optional override for NVIDIA NIM API Key",
    )
    args = parser.parse_args()
    runtime = load_web_runtime_config(
        config_path=args.config,
        env_name=args.env,
        cli_overrides={
            "host": args.host,
            "port": args.port,
            "static_root": args.static_root,
            "database_url": args.database_url,
            "nvidia_api_key": args.nvidia_api_key,
        },
    )
    if not runtime.database_url:
        parser.error(
            f"缺少数据库连接配置：请在 {runtime.config_path} 的 [{runtime.env}] 或 [default] 段配置 database_url，"
            "或设置 PM_AGENT_DATABASE_URL，或传入 --database-url"
        )

    app = create_api_app(
        static_root=runtime.static_root,
        database_url=runtime.database_url,
        dashscope_api_key=runtime.nvidia_api_key,
    )
    with make_server(runtime.host, runtime.port, app) as server:
        print(f"pm-agent web api listening on http://{runtime.host}:{runtime.port} (env={runtime.env})")
        server.serve_forever()


if __name__ == "__main__":
    main()
