from __future__ import annotations

import argparse
import logging
import os
from wsgiref.simple_server import make_server

from pm_agent.api import create_api_app

## lsof -nP -iTCP:8000 -sTCP:LISTEN
def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Run the project manager agent web API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--store-root", default=".pm_agent_store")
    parser.add_argument("--static-root", default="frontend/dist")
    parser.add_argument("--database-url", default="mysql://root:@Admin123456@127.0.0.1:3306/pm_agent?charset=utf8mb4")
    parser.add_argument(
        "--nvidia-api-key",
        default=os.environ.get("NVIDIA_NIM_API_KEY", "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"),
        help="NVIDIA NIM API Key",
    )
    args = parser.parse_args()

    app = create_api_app(
        store_root=args.store_root,
        static_root=args.static_root,
        database_url=args.database_url,
        dashscope_api_key=args.nvidia_api_key,
    )
    with make_server(args.host, args.port, app) as server:
        print(f"pm-agent web api listening on http://{args.host}:{args.port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
