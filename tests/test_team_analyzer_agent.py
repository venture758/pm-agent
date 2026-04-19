from __future__ import annotations

import json
import unittest

from pm_agent.agents.team_analyzer import TeamAnalyzerAgent
from pm_agent.llm_client import LlmFallbackStats
from pm_agent.pipeline import PipelineContext


class FakeLlm:
    def __init__(self, *, response_text: str = "", parsed: dict | None = None) -> None:
        self.response_text = response_text
        self.parsed = parsed or {}

    def chat_completion(self, messages):
        return (self.response_text, LlmFallbackStats(final_tier="primary"))

    def parse_json_response(self, text: str) -> dict:
        return self.parsed


class TestTeamAnalyzerAgent(unittest.TestCase):
    def test_build_system_prompt_returns_constant(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        agent = TeamAnalyzerAgent()
        system = agent.build_system_prompt(ctx)
        self.assertIn("团队梯队分析专家", system)
        self.assertIn("single_point_risks", system)
        self.assertIn("growth_paths", system)

    def test_build_user_prompt_with_dict_data(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        ctx.profiles = [{"name": "张三"}, {"name": "李四"}]
        ctx.module_entries = [
            {
                "key": "税务::发票接口",
                "familiar_members": ["李祥"],
                "aware_members": ["张三"],
                "unfamiliar_members": ["王五"],
            }
        ]
        ctx.assignment_suggestions = [
            {"requirement_id": "REQ-001", "development_owner": "张三"}
        ]

        agent = TeamAnalyzerAgent()
        user = agent.build_user_prompt(ctx)

        self.assertIn("## 团队成员", user)
        self.assertIn("张三", user)
        self.assertIn("李四", user)
        self.assertIn("税务::发票接口", user)
        self.assertIn("熟悉=['李祥']", user)
        self.assertIn("了解=['张三']", user)
        self.assertIn("不了解=['王五']", user)
        self.assertIn("REQ-001", user)
        self.assertIn("张三", user)

    def test_build_user_prompt_with_constraints(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        ctx.step_constraints = {"team_analysis": "王五下周请假"}

        agent = TeamAnalyzerAgent()
        user = agent.build_user_prompt(ctx)

        self.assertIn("额外约束", user)
        self.assertIn("王五下周请假", user)

    def test_parse_response(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        parsed = {
            "module_familiarity_matrix": {
                "税务::发票接口": {
                    "familiar": ["李祥"],
                    "aware": ["张三"],
                    "unfamiliar": ["王五"],
                }
            },
            "single_point_risks": [
                {
                    "module_key": "税务::发票接口",
                    "risk_member": "李祥",
                    "severity": "high",
                    "suggestion": "建议培养B角",
                }
            ],
            "growth_paths": [
                {
                    "member": "王五",
                    "target_module": "税务::发票接口",
                    "current_level": "不了解",
                    "target_level": "了解",
                    "path": "先参与需求分析",
                }
            ],
            "reply": "分析完成",
        }
        agent = TeamAnalyzerAgent(llm_client=FakeLlm(parsed=parsed))
        result = agent.parse_response("dummy text", ctx)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["mode"], "team_analysis")
        self.assertEqual(result["reply"], "分析完成")
        self.assertIn("税务::发票接口", result["module_familiarity_matrix"])
        self.assertEqual(len(result["single_point_risks"]), 1)
        self.assertEqual(result["single_point_risks"][0]["severity"], "high")
        self.assertEqual(len(result["growth_paths"]), 1)
        self.assertEqual(result["growth_paths"][0]["member"], "王五")
        self.assertIn("module_familiarity_matrix", result["data"])
        self.assertIn("single_point_risks", result["data"])
        self.assertIn("growth_paths", result["data"])

    def test_execute_full_flow(self):
        """Test full execute with LLM, verifying llm_stats included."""
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        ctx.profiles = [{"name": "张三"}]
        ctx.module_entries = []
        ctx.assignment_suggestions = []

        response_text = json.dumps({
            "mode": "team_analysis",
            "module_familiarity_matrix": {},
            "single_point_risks": [],
            "growth_paths": [],
            "reply": "完成",
        })
        agent = TeamAnalyzerAgent(llm_client=FakeLlm(
            response_text=response_text,
            parsed={
                "module_familiarity_matrix": {},
                "single_point_risks": [],
                "growth_paths": [],
                "reply": "完成",
            },
        ))
        result = agent.execute(ctx)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["mode"], "team_analysis")
        self.assertIn("llm_stats", result)

    def test_execute_skips_when_no_llm(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        agent = TeamAnalyzerAgent()
        result = agent.execute(ctx)
        self.assertEqual(result["status"], "skipped")
        self.assertIn("LLM", result["reply"])


if __name__ == "__main__":
    unittest.main()
