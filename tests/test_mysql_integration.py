from __future__ import annotations

import os
import unittest
from pathlib import Path

from pm_agent.api_service import WorkspaceService
from pm_agent.database import DatabaseStore


@unittest.skipUnless(os.getenv("PM_AGENT_TEST_DATABASE_URL"), "PM_AGENT_TEST_DATABASE_URL 未配置")
class MysqlIntegrationTest(unittest.TestCase):
    def test_service_flow_on_mysql(self) -> None:
        database_url = os.environ["PM_AGENT_TEST_DATABASE_URL"]
        store = DatabaseStore(database_url=database_url)
        ddl = Path("db/schema.mysql.ddl.sql").read_text(encoding="utf-8")
        statements = [statement.strip() for statement in ddl.split(";") if statement.strip()]

        with store.connection() as connection:
            cursor = connection.cursor()
            for statement in statements:
                cursor.execute(statement)
            cursor.execute("DELETE FROM workspace_recommendations")
            cursor.execute("DELETE FROM workspace_module_entries")
            cursor.execute("DELETE FROM workspace_managed_members")
            cursor.execute("DELETE FROM workspace_states")
            cursor.execute("DELETE FROM agent_states")

        service = WorkspaceService(database_url=database_url)
        service.create_managed_member(
            "mysql-test",
            {
                "name": "李祥",
                "role": "developer",
                "skills": "税务",
                "experience": "高",
                "workload": 0.1,
                "capacity": 1.0,
            },
        )
        payload = service.create_module_entry(
            "mysql-test",
            {
                "big_module": "税务",
                "function_module": "发票接口",
                "primary_owner": "李祥",
                "backup_owners": ["李祥"],
                "familiar_members": ["李祥"],
            },
        )
        self.assertEqual("mysql-test", payload["workspace_id"])
        service.update_draft(
            "mysql-test",
            {
                "message_text": "1. 发票接口改造 https://example.com/1 优先级高",
            },
        )
        recommendation_payload = service.generate_recommendations("mysql-test")
        self.assertEqual(1, len(recommendation_payload["recommendations"]))

        with store.connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT COUNT(1) FROM workspace_module_entries WHERE workspace_id = %s",
                ("mysql-test",),
            )
            module_count = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(1) FROM workspace_managed_members WHERE workspace_id = %s",
                ("mysql-test",),
            )
            member_count = cursor.fetchone()[0]
            cursor.execute(
                "SELECT COUNT(1) FROM workspace_recommendations WHERE workspace_id = %s",
                ("mysql-test",),
            )
            recommendation_count = cursor.fetchone()[0]
        self.assertEqual(1, module_count)
        self.assertEqual(1, member_count)
        self.assertEqual(1, recommendation_count)


if __name__ == "__main__":
    unittest.main()
