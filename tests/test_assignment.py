from __future__ import annotations

import unittest

from pm_agent.assignment import confirm_assignments, recommend_assignments
from pm_agent.models import MemberProfile, ModuleKnowledgeEntry, RequirementItem


class AssignmentTest(unittest.TestCase):
    def test_recommend_assignments(self) -> None:
        requirement = RequirementItem(
            requirement_id="1",
            title="发票查验接口替换为长软新数据源需求",
            priority="高",
            complexity="中高",
            risk="高",
            skills=["发票", "接口"],
            matched_module_keys=["税务::发票接口"],
        )
        module_entry = ModuleKnowledgeEntry(
            key="税务::发票接口",
            big_module="税务",
            function_module="发票接口",
            primary_owner="李祥",
            backup_owners=["王海林"],
            familiar_members=["李祥"],
            aware_members=["王海林"],
        )
        members = [
            MemberProfile(name="李祥", skills=["发票", "接口"], workload=0.2, capacity=1.0, module_familiarity={module_entry.key: "熟悉"}),
            MemberProfile(name="王海林", skills=["发票"], workload=0.1, capacity=1.0, module_familiarity={module_entry.key: "了解"}),
            MemberProfile(name="余萍", role="tester", skills=["测试"], workload=0.3, capacity=1.0),
        ]
        recommendations = recommend_assignments([requirement], members, {module_entry.key: module_entry})
        recommendation = recommendations[0]
        self.assertEqual("李祥", recommendation.development_owner)
        self.assertEqual("王海林", recommendation.backup_owner)
        self.assertEqual("余萍", recommendation.testing_owner)

    def test_confirm_assignments(self) -> None:
        recommendation = recommend_assignments(
            [
                RequirementItem(
                    requirement_id="1",
                    title="示例需求",
                    matched_module_keys=[],
                )
            ],
            [MemberProfile(name="张三", workload=0.0, capacity=1.0)],
            {},
        )[0]
        confirmed = confirm_assignments([recommendation], {"1": {"action": "accept"}})
        self.assertEqual("accept", confirmed[0].action_log[0])

    def test_confirm_assignments_skip_deleted_action(self) -> None:
        recommendation = recommend_assignments(
            [
                RequirementItem(
                    requirement_id="1",
                    title="示例需求",
                    matched_module_keys=[],
                )
            ],
            [MemberProfile(name="张三", workload=0.0, capacity=1.0)],
            {},
        )[0]
        confirmed = confirm_assignments([recommendation], {"1": {"action": "delete"}})
        self.assertEqual(0, len(confirmed))

    def test_confirm_assignments_normalizes_requirement_id(self) -> None:
        recommendation = recommend_assignments(
            [
                RequirementItem(
                    requirement_id="2.0",
                    title="示例需求",
                    matched_module_keys=[],
                )
            ],
            [MemberProfile(name="张三", workload=0.0, capacity=1.0)],
            {},
        )[0]
        confirmed = confirm_assignments(
            [recommendation],
            {"2": {"action": "reassign", "development_owner": "李四"}},
        )
        self.assertEqual("2", confirmed[0].requirement_id)
        self.assertEqual("李四", confirmed[0].development_owner)


if __name__ == "__main__":
    unittest.main()
