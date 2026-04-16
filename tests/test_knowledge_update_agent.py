from __future__ import annotations

import unittest

from mysql_test_utils import ensure_mysql_schema, get_test_database_url, reset_mysql_test_data
from pm_agent.models import ConfirmedAssignment, ModuleKnowledgeEntry
from pm_agent.workflows import ProjectManagerAgent


class FakeLlm:
    def __init__(self, *, response_text: str = "", parsed: dict | None = None, chat_error: Exception | None = None, parse_error: Exception | None = None) -> None:
        self.response_text = response_text
        self.parsed = parsed or {}
        self.chat_error = chat_error
        self.parse_error = parse_error

    def chat_completion(self, messages, **_kwargs) -> str:
        if self.chat_error is not None:
            raise self.chat_error
        return self.response_text

    def parse_json_response(self, _text: str) -> dict:
        if self.parse_error is not None:
            raise self.parse_error
        return self.parsed


@unittest.skipUnless(get_test_database_url(), "PM_AGENT_TEST_DATABASE_URL 未配置")
class KnowledgeUpdateAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.database_url = get_test_database_url()
        assert self.database_url is not None
        self.store = ensure_mysql_schema(self.database_url)
        reset_mysql_test_data(self.store)

    def test_generate_knowledge_update_suggestions_skips_when_llm_unavailable(self) -> None:
        agent = ProjectManagerAgent(database_url=self.database_url)

        result = agent.generate_knowledge_update_suggestions([])

        self.assertEqual("skipped", result["status"])
        self.assertEqual("LLM 未配置", result["reply"])
        self.assertEqual({}, result["knowledge_updates"])

    def test_generate_knowledge_update_suggestions_returns_success_payload(self) -> None:
        agent = ProjectManagerAgent(database_url=self.database_url)
        agent.state.module_entries = {
            "税务::发票接口": ModuleKnowledgeEntry(
                key="税务::发票接口",
                big_module="税务",
                function_module="发票接口",
                primary_owner="李祥",
                familiar_members=["李祥"],
            )
        }
        assignment = ConfirmedAssignment(
            requirement_id="R-1",
            title="发票修复",
            module_key="税务::发票接口",
            development_owner="李祥",
            testing_owner="余萍",
        )
        agent.state.confirmed_assignments = {assignment.requirement_id: assignment}
        agent._llm = FakeLlm(
            response_text='{"reply":"建议培养B角"}',
            parsed={
                "reply": "建议培养B角",
                "knowledge_updates": {
                    "suggested_familiarity": [{"member": "余萍", "to": "了解"}],
                    "suggested_modules": [],
                },
                "optimization_suggestions": [{"type": "single_point", "suggestion": "培养 B 角"}],
            },
        )

        result = agent.generate_knowledge_update_suggestions([assignment])

        self.assertEqual("success", result["status"])
        self.assertEqual("建议培养B角", result["reply"])
        self.assertEqual(1, len(result["optimization_suggestions"]))
        self.assertEqual(1, len(result["knowledge_updates"]["suggested_familiarity"]))

    def test_generate_knowledge_update_suggestions_handles_parse_failure(self) -> None:
        agent = ProjectManagerAgent(database_url=self.database_url)
        agent._llm = FakeLlm(
            response_text="not-json",
            parse_error=ValueError("无法解析 JSON"),
        )

        result = agent.generate_knowledge_update_suggestions([])

        self.assertEqual("failed", result["status"])
        self.assertEqual("not-json", result["reply"])
        self.assertIn("无法解析 JSON", result["error_message"])


if __name__ == "__main__":
    unittest.main()
