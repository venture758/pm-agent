from __future__ import annotations

import json
import unittest

from pm_agent.agents.orchestrator import OrchestratorAgent
from pm_agent.llm_client import LlmFallbackStats
from pm_agent.pipeline import PIPELINE_STEPS, PipelineContext


class MockLlm:
    """模拟 LLM，根据 system prompt 内容判断当前步骤并返回对应响应。"""

    def chat_completion(self, messages):
        system = messages[0].get("content", "")
        if "requirement_analysis" in system:
            text = json.dumps({
                "mode": "requirement_analysis",
                "requirements": [
                    {
                        "title": "用户登录接口",
                        "priority": "高",
                        "complexity": "中",
                        "risk": "中",
                        "skills": ["Python"],
                        "matched_modules": [],
                        "dependency_hints": [],
                        "blockers": [],
                        "split_suggestion": "",
                        "analysis_factors": [],
                    }
                ],
                "reply": "已解析1条需求",
            })
        elif "personnel_matching" in system:
            text = json.dumps({
                "mode": "personnel_matching",
                "assignments": [
                    {
                        "requirement_id": "REQ-001",
                        "requirement_title": "用户登录接口",
                        "development_owner": "张三",
                        "testing_owner": "李四",
                        "backup_owner": "王五",
                        "collaborators": [],
                        "reasons": ["熟悉Python"],
                        "workload_snapshot": {"张三": 0.3},
                        "confidence": 0.8,
                    }
                ],
                "reply": "推荐分配完成",
            })
        elif "module_extraction" in system:
            text = json.dumps({
                "mode": "module_extraction",
                "module_changes": [],
                "reply": "无新模块需要提炼",
            })
        elif "team_analysis" in system:
            text = json.dumps({
                "mode": "team_analysis",
                "module_familiarity_matrix": {},
                "single_point_risks": [],
                "growth_paths": [],
                "reply": "未发现显著风险",
            })
        elif "knowledge_update" in system:
            text = json.dumps({
                "mode": "knowledge_update",
                "summary": {
                    "requirements_parsed": 1,
                    "personnel_assigned": 1,
                    "modules_created": 0,
                },
                "pending_changes": [],
                "reply": "汇总完成",
            })
        else:
            text = json.dumps({"mode": "unknown", "reply": ""})
        return (text, LlmFallbackStats(final_tier="primary"))

    def parse_json_response(self, text):
        return json.loads(text)


class TestPipelineE2E(unittest.TestCase):
    def test_full_pipeline_flow(self):
        """完整走完5个步骤：启动 -> 逐个确认 -> 完成。"""
        llm = MockLlm()
        orchestrator = OrchestratorAgent(llm_client=llm)

        # 步骤1: 启动，执行需求解析
        result = orchestrator.start("w1", "需要一个用户登录接口")
        self.assertEqual(result["step"], "requirement_parsing")
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["data"]["requirements"]), 1)

        # 确认步骤1 -> 进入步骤2（人员匹配）
        result = orchestrator.confirm_step("w1", "confirm")
        self.assertEqual(result["step"], "personnel_matching")
        self.assertEqual(result["status"], "success")

        # 确认步骤2 -> 进入步骤3（模块提炼）
        result = orchestrator.confirm_step("w1", "confirm")
        self.assertEqual(result["step"], "module_extraction")
        self.assertEqual(result["status"], "success")

        # 跳过步骤3 -> 进入步骤4（梯队分析）
        result = orchestrator.confirm_step("w1", "skip")
        self.assertEqual(result["step"], "team_analysis")
        self.assertEqual(result["status"], "success")

        # 确认步骤4 -> 进入步骤5（知识更新）
        result = orchestrator.confirm_step("w1", "confirm")
        self.assertEqual(result["step"], "knowledge_update")
        self.assertEqual(result["status"], "success")

        # 确认步骤5 -> 完成
        result = orchestrator.confirm_step("w1", "confirm")
        self.assertEqual(result["status"], "complete")

        # 验证最终状态
        state = orchestrator.get_state("w1")
        self.assertTrue(state["is_complete"])
        self.assertIsNone(state["current_step"])
        # 5个步骤都有结果
        self.assertEqual(len(state["step_results"]), len(PIPELINE_STEPS))

    def test_reanalyze_with_feedback(self):
        """重新分析并注入约束。"""
        llm = MockLlm()
        orchestrator = OrchestratorAgent(llm_client=llm)
        orchestrator.start("w2", "需要一个用户登录接口")

        # 确认步骤1 -> 进入步骤2（人员匹配）
        orchestrator.confirm_step("w2", "confirm")

        # 重新分析人员匹配，注入约束 "李祥这周不在"
        result = orchestrator.confirm_step("w2", "reanalyze", feedback="李祥这周不在")
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["step"], "personnel_matching")

        # 验证约束已保存
        state = orchestrator.get_state("w2")
        self.assertIn("personnel_matching", state["step_constraints"])
        self.assertIn("李祥", state["step_constraints"]["personnel_matching"])

    def test_pipeline_state_persistence_across_steps(self):
        """验证 Pipeline 数据在各步骤间正确传递。"""
        llm = MockLlm()
        orchestrator = OrchestratorAgent(llm_client=llm)

        # 启动并完成步骤1
        result = orchestrator.start("w3", "需要一个用户登录接口")
        self.assertEqual(result["step"], "requirement_parsing")

        # 确认步骤1，进入步骤2
        result = orchestrator.confirm_step("w3", "confirm")
        self.assertEqual(result["step"], "personnel_matching")

        # 验证步骤1的产出（requirements）已被保存到 context 中
        state = orchestrator.get_state("w3")
        self.assertEqual(len(state["requirements"]), 1)
        self.assertEqual(state["requirements"][0]["title"], "用户登录接口")
        self.assertEqual(state["step_results"]["requirement_parsing"]["status"], "confirmed")

    def test_complete_returns_correct_status(self):
        """确认所有步骤完成后返回 complete 状态。"""
        llm = MockLlm()
        orchestrator = OrchestratorAgent(llm_client=llm)
        orchestrator.start("w4", "需要一个用户登录接口")

        # 连续确认4次，从步骤1推进到步骤5执行完毕
        for _ in range(4):
            result = orchestrator.confirm_step("w4", "confirm")

        # 第5次确认（确认步骤5）应返回 complete
        result = orchestrator.confirm_step("w4", "confirm")
        self.assertEqual(result["status"], "complete")

        # 再次调用应仍返回 complete
        result = orchestrator.confirm_step("w4", "confirm")
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["reply"], "所有步骤已完成")


if __name__ == "__main__":
    unittest.main()
