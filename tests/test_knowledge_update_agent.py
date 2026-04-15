from __future__ import annotations

import tempfile
import unittest

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


class KnowledgeUpdateAgentTest(unittest.TestCase):
    def _sqlite_url(self, root: str) -> str:
        return f"sqlite:///{root}/pm_agent.db"

    def test_generate_knowledge_update_suggestions_skips_when_llm_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ProjectManagerAgent(database_url=self._sqlite_url(tmpdir))

            result = agent.generate_knowledge_update_suggestions([])

            self.assertEqual("skipped", result["status"])
            self.assertEqual("LLM 未配置", result["reply"])
            self.assertEqual({}, result["knowledge_updates"])

    def test_generate_knowledge_update_suggestions_returns_success_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ProjectManagerAgent(database_url=self._sqlite_url(tmpdir))
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
        with tempfile.TemporaryDirectory() as tmpdir:
            agent = ProjectManagerAgent(database_url=self._sqlite_url(tmpdir))
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
