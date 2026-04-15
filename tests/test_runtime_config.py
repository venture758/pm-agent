from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pm_agent.runtime_config import load_web_runtime_config


class RuntimeConfigTest(unittest.TestCase):
    def _write_config(self, root: str) -> Path:
        path = Path(root) / "pm_agent.toml"
        path.write_text(
            "\n".join(
                [
                    "[default]",
                    'host = "0.0.0.0"',
                    "port = 9000",
                    'static_root = "frontend/custom-dist"',
                    "",
                    "[dev]",
                    'database_url = "sqlite:////tmp/dev.db"',
                    'nvidia_api_key = "dev-key"',
                    "",
                    "[prod]",
                    'database_url = "mysql://prod:prod@127.0.0.1:3306/pm_agent"',
                ]
            ),
            encoding="utf-8",
        )
        return path

    def test_loads_default_and_env_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_config(tmpdir)

            config = load_web_runtime_config(config_path=path, env_name="dev", environ={})

            self.assertEqual("dev", config.env)
            self.assertEqual("0.0.0.0", config.host)
            self.assertEqual(9000, config.port)
            self.assertEqual("frontend/custom-dist", config.static_root)
            self.assertEqual("sqlite:////tmp/dev.db", config.database_url)
            self.assertEqual("dev-key", config.nvidia_api_key)

    def test_environment_variables_override_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_config(tmpdir)

            config = load_web_runtime_config(
                config_path=path,
                env_name="dev",
                environ={
                    "PM_AGENT_DATABASE_URL": "sqlite:////tmp/from-env.db",
                    "NVIDIA_NIM_API_KEY": "env-key",
                },
            )

            self.assertEqual("sqlite:////tmp/from-env.db", config.database_url)
            self.assertEqual("env-key", config.nvidia_api_key)

    def test_cli_overrides_environment_and_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = self._write_config(tmpdir)

            config = load_web_runtime_config(
                config_path=path,
                env_name="prod",
                environ={
                    "PM_AGENT_DATABASE_URL": "sqlite:////tmp/from-env.db",
                },
                cli_overrides={
                    "host": "127.0.0.1",
                    "port": 7000,
                    "database_url": "sqlite:////tmp/from-cli.db",
                },
            )

            self.assertEqual("127.0.0.1", config.host)
            self.assertEqual(7000, config.port)
            self.assertEqual("sqlite:////tmp/from-cli.db", config.database_url)


if __name__ == "__main__":
    unittest.main()
