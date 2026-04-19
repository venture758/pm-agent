from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from pm_agent.agents.module_extractor import ModuleExtractorAgent
from pm_agent.pipeline import PipelineContext


class FakeLlm:
    def chat_completion(self, messages):
        from pm_agent.llm_client import LlmFallbackStats
        return (
            '{"mode":"module_extraction","module_changes":[{"action":"create_big_module","big_module":"测试模块","function_module":"","primary_owner":"张三","rationale":"新业务领域"}],"reply":"提炼完成"}',
            LlmFallbackStats(final_tier="primary"),
        )

    def parse_json_response(self, text):
        return json.loads(text)


class TestModuleExtractorAgent(unittest.TestCase):
    def test_execute(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="需要一个测试模块")
        ctx.requirements = [{"requirement_id": "REQ-001", "title": "测试需求", "matched_modules": []}]
        ctx.module_entries = []
        ctx.assignment_suggestions = []

        agent = ModuleExtractorAgent(llm_client=FakeLlm())
        result = agent.execute(ctx)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["mode"], "module_extraction")
        self.assertEqual(len(result["module_changes"]), 1)
        self.assertEqual(result["module_changes"][0]["action"], "create_big_module")

    def test_build_user_prompt(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        ctx.requirements = [{"requirement_id": "REQ-001", "title": "需求A", "matched_modules": []}]
        ctx.module_entries = [{"key": "税务::发票", "primary_owner": "张三"}]
        ctx.assignment_suggestions = [{"requirement_id": "REQ-001", "development_owner": "李四", "testing_owner": "王五"}]

        agent = ModuleExtractorAgent(llm_client=FakeLlm())
        prompt = agent.build_user_prompt(ctx)
        self.assertIn("需求A", prompt)
        self.assertIn("税务::发票", prompt)
        self.assertIn("李四", prompt)

    def test_build_user_prompt_with_constraint(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        ctx.requirements = []
        ctx.module_entries = []
        ctx.assignment_suggestions = []
        ctx.step_constraints["module_extraction"] = "不要创建新模块"

        agent = ModuleExtractorAgent(llm_client=FakeLlm())
        prompt = agent.build_user_prompt(ctx)
        self.assertIn("不要创建新模块", prompt)

    def test_build_system_prompt(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        agent = ModuleExtractorAgent(llm_client=FakeLlm())
        system = agent.build_system_prompt(ctx)
        self.assertIn("模块知识管理专家", system)
        self.assertIn("module_extraction", system)

    def test_parse_response(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        text = json.dumps({
            "mode": "module_extraction",
            "module_changes": [
                {"action": "update_primary_owner", "big_module": "税务", "function_module": "发票", "primary_owner": "赵六", "rationale": "原负责人离职"}
            ],
            "reply": "已更新",
        })

        agent = ModuleExtractorAgent(llm_client=FakeLlm())
        result = agent.parse_response(text, ctx)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["mode"], "module_extraction")
        self.assertEqual(len(result["module_changes"]), 1)
        self.assertEqual(result["module_changes"][0]["action"], "update_primary_owner")
        self.assertEqual(result["reply"], "已更新")

    def test_execute_no_llm(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        agent = ModuleExtractorAgent(llm_client=None)
        result = agent.execute(ctx)
        self.assertEqual(result["status"], "skipped")
