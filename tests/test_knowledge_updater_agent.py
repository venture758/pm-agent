from __future__ import annotations

import json
import unittest

from pm_agent.agents.knowledge_updater import KnowledgeUpdaterAgent
from pm_agent.llm_client import LlmFallbackStats
from pm_agent.pipeline import PipelineContext


class FakeLlm:
    def __init__(
        self,
        *,
        response_text: str = "",
        parsed: dict | None = None,
        parse_error: Exception | None = None,
    ) -> None:
        self.response_text = response_text
        self.parsed = parsed or {}
        self.parse_error = parse_error

    def chat_completion(self, messages):
        return (self.response_text, LlmFallbackStats(final_tier="primary"))

    def parse_json_response(self, text: str) -> dict:
        if self.parse_error is not None:
            raise self.parse_error
        return self.parsed


class TestKnowledgeUpdaterAgent(unittest.TestCase):
    def test_execute_success(self):
        ctx = PipelineContext(
            workspace_id="w1",
            session_id="s1",
            user_message="需要一个用户登录接口",
        )
        ctx.requirements = [{"requirement_id": "REQ-001", "title": "登录接口"}]
        ctx.assignment_suggestions = [
            {"requirement_id": "REQ-001", "development_owner": "张三"}
        ]
        ctx.module_changes = [{"action": "create_function_module", "big_module": "认证", "function_module": "登录"}]
        ctx.team_analysis = {"single_point_risks": []}

        llm = FakeLlm(
            response_text=json.dumps({
                "mode": "knowledge_update",
                "summary": {
                    "requirements_parsed": 1,
                    "personnel_assigned": 1,
                    "modules_created": 1,
                    "familiarity_updates": 0,
                    "risks_identified": 0,
                },
                "pending_changes": [
                    {"type": "create_module", "data": {"big_module": "认证", "function_module": "登录"}},
                ],
                "reply": "汇总完成",
            }),
            parsed={
                "mode": "knowledge_update",
                "summary": {
                    "requirements_parsed": 1,
                    "personnel_assigned": 1,
                    "modules_created": 1,
                    "familiarity_updates": 0,
                    "risks_identified": 0,
                },
                "pending_changes": [
                    {"type": "create_module", "data": {"big_module": "认证", "function_module": "登录"}},
                ],
                "reply": "汇总完成",
            },
        )

        agent = KnowledgeUpdaterAgent(llm_client=llm)
        result = agent.execute(ctx)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["mode"], "knowledge_update")
        self.assertEqual(result["reply"], "汇总完成")
        self.assertEqual(len(result["pending_changes"]), 1)
        self.assertEqual(result["pending_changes"][0]["type"], "create_module")
        self.assertEqual(result["summary"]["requirements_parsed"], 1)
        self.assertIn("llm_stats", result)

    def test_execute_no_llm(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        agent = KnowledgeUpdaterAgent(llm_client=None)
        result = agent.execute(ctx)
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reply"], "LLM 未配置，跳过")

    def test_execute_with_constraints(self):
        ctx = PipelineContext(
            workspace_id="w1",
            session_id="s1",
            user_message="test",
        )
        ctx.step_constraints["knowledge_update"] = "不要修改现有模块负责人"

        llm = FakeLlm(
            response_text=json.dumps({
                "mode": "knowledge_update",
                "summary": {"requirements_parsed": 0, "personnel_assigned": 0, "modules_created": 0, "familiarity_updates": 0, "risks_identified": 0},
                "pending_changes": [],
                "reply": "已考虑约束",
            }),
            parsed={
                "mode": "knowledge_update",
                "summary": {"requirements_parsed": 0, "personnel_assigned": 0, "modules_created": 0, "familiarity_updates": 0, "risks_identified": 0},
                "pending_changes": [],
                "reply": "已考虑约束",
            },
        )

        agent = KnowledgeUpdaterAgent(llm_client=llm)
        result = agent.execute(ctx)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["reply"], "已考虑约束")

    def test_build_user_prompt_summarizes_steps(self):
        ctx = PipelineContext(
            workspace_id="w1",
            session_id="s1",
            user_message="test",
        )
        ctx.requirements = [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        ctx.assignment_suggestions = [{"id": "1"}, {"id": "2"}]
        ctx.module_changes = [{"action": "create"}]

        agent = KnowledgeUpdaterAgent()
        prompt = agent.build_user_prompt(ctx)

        self.assertIn("3 条", prompt)
        self.assertIn("2 条", prompt)
        self.assertIn("1 条", prompt)
        self.assertIn("步骤1", prompt)
        self.assertIn("步骤2", prompt)
        self.assertIn("步骤3", prompt)
        self.assertIn("步骤4", prompt)

    def test_build_system_prompt(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        agent = KnowledgeUpdaterAgent()
        system = agent.build_system_prompt(ctx)
        self.assertIn("知识管理汇总专家", system)
        self.assertIn("knowledge_update", system)


if __name__ == "__main__":
    unittest.main()
