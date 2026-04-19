from __future__ import annotations

import unittest

from pm_agent.agents.personnel_matcher import PersonnelMatcherAgent
from pm_agent.llm_client import LlmFallbackStats
from pm_agent.pipeline import PipelineContext


class FakeLlm:
    def chat_completion(self, messages):
        return (
            '{"mode":"personnel_matching",'
            '"assignments":[{"requirement_id":"REQ-001","requirement_title":"用户登录接口",'
            '"development_owner":"张三","testing_owner":"李四","backup_owner":"王五",'
            '"collaborators":[],"reasons":["熟悉Python"],"workload_snapshot":{"张三":0.3},'
            '"confidence":0.8}],'
            '"reply":"推荐分配完成"}',
            LlmFallbackStats(final_tier="primary"),
        )

    def parse_json_response(self, text):
        import json
        return json.loads(text)


class TestPersonnelMatcherAgent(unittest.TestCase):
    def test_execute(self):
        ctx = PipelineContext(
            workspace_id="w1",
            session_id="s1",
            user_message="需要一个用户登录接口",
        )
        ctx.requirements = [
            {
                "requirement_id": "REQ-001",
                "title": "用户登录接口",
                "priority": "高",
                "skills": ["Python"],
            },
        ]
        ctx.profiles = [
            {
                "name": "张三",
                "role": "developer",
                "skills": ["Python", "Java"],
                "workload": 0.3,
                "capacity": 1,
            },
            {
                "name": "李四",
                "role": "tester",
                "skills": ["Python", "自动化测试"],
                "workload": 0.2,
                "capacity": 1,
            },
        ]

        agent = PersonnelMatcherAgent(llm_client=FakeLlm())
        result = agent.execute(ctx)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["mode"], "personnel_matching")
        self.assertEqual(len(result["assignments"]), 1)
        self.assertEqual(result["assignments"][0]["development_owner"], "张三")
        self.assertEqual(result["assignments"][0]["testing_owner"], "李四")
        self.assertEqual(result["assignments"][0]["confidence"], 0.8)
        self.assertIn("llm_stats", result)

    def test_build_user_prompt(self):
        ctx = PipelineContext(
            workspace_id="w1",
            session_id="s1",
            user_message="test",
        )
        ctx.requirements = [
            {
                "requirement_id": "REQ-001",
                "title": "登录接口",
                "priority": "高",
                "skills": ["Python", "FastAPI"],
            },
        ]
        ctx.profiles = [
            {
                "name": "张三",
                "role": "developer",
                "skills": ["Python"],
                "workload": 0.5,
                "capacity": 1,
            },
        ]

        agent = PersonnelMatcherAgent(llm_client=FakeLlm())
        prompt = agent.build_user_prompt(ctx)

        self.assertIn("## 需求列表", prompt)
        self.assertIn("REQ-001", prompt)
        self.assertIn("登录接口", prompt)
        self.assertIn("优先级: 高", prompt)
        self.assertIn("所需技能: Python, FastAPI", prompt)
        self.assertIn("## 团队成员", prompt)
        self.assertIn("张三", prompt)
        self.assertIn("developer", prompt)

    def test_build_user_prompt_with_constraint(self):
        ctx = PipelineContext(
            workspace_id="w1",
            session_id="s1",
            user_message="test",
        )
        ctx.requirements = []
        ctx.profiles = []
        ctx.step_constraints["personnel_matching"] = "李祥这周不在"

        agent = PersonnelMatcherAgent(llm_client=FakeLlm())
        prompt = agent.build_user_prompt(ctx)

        self.assertIn("## 额外约束", prompt)
        self.assertIn("李祥这周不在", prompt)

    def test_build_system_prompt(self):
        ctx = PipelineContext(
            workspace_id="w1",
            session_id="s1",
            user_message="test",
        )
        agent = PersonnelMatcherAgent(llm_client=FakeLlm())
        system = agent.build_system_prompt(ctx)

        self.assertIn("人员匹配专家", system)
        self.assertIn("personnel_matching", system)

    def test_parse_response(self):
        ctx = PipelineContext(
            workspace_id="w1",
            session_id="s1",
            user_message="test",
        )
        text = (
            '{"mode":"personnel_matching",'
            '"assignments":[{"requirement_id":"REQ-002","requirement_title":"支付接口",'
            '"development_owner":"王五","testing_owner":"","backup_owner":"赵六",'
            '"collaborators":["孙七"],"reasons":["有支付经验"],'
            '"workload_snapshot":{"王五":0.6},"confidence":0.9}],'
            '"reply":"匹配完成"}'
        )

        agent = PersonnelMatcherAgent(llm_client=FakeLlm())
        result = agent.parse_response(text, ctx)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["mode"], "personnel_matching")
        self.assertEqual(len(result["assignments"]), 1)
        self.assertEqual(result["assignments"][0]["development_owner"], "王五")
        self.assertEqual(result["assignments"][0]["backup_owner"], "赵六")
        self.assertEqual(result["reply"], "匹配完成")

    def test_skipped_without_llm(self):
        ctx = PipelineContext(
            workspace_id="w1",
            session_id="s1",
            user_message="test",
        )
        agent = PersonnelMatcherAgent(llm_client=None)
        result = agent.execute(ctx)

        self.assertEqual(result["status"], "skipped")
