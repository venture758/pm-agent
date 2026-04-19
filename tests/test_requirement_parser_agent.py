from __future__ import annotations

import unittest

from pm_agent.agents.requirement_parser import RequirementParserAgent
from pm_agent.llm_client import LlmFallbackStats
from pm_agent.pipeline import PipelineContext


class FakeLlm:
    def chat_completion(self, messages):
        return (
            '{"mode":"requirement_analysis","requirements":[{"title":"测试需求","priority":"高","complexity":"中","risk":"低","skills":["Python"],"matched_modules":[],"dependency_hints":[],"blockers":[],"split_suggestion":"","analysis_factors":[]}],"reply":"已解析1条需求"}',
            LlmFallbackStats(final_tier="primary"),
        )

    def parse_json_response(self, text):
        import json
        return json.loads(text)


class TestRequirementParserAgent(unittest.TestCase):
    def test_execute(self):
        ctx = PipelineContext(
            workspace_id="w1",
            session_id="s1",
            user_message="需要一个用户登录接口",
        )
        ctx.profiles = [{"name": "张三", "role": "developer"}]
        ctx.module_entries = []

        agent = RequirementParserAgent(llm_client=FakeLlm())
        result = agent.execute(ctx)
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["requirements"]), 1)
        self.assertEqual(result["requirements"][0]["priority"], "高")
