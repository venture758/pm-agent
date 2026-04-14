from __future__ import annotations

import unittest

from pm_agent.assignment import aggregate_task_history, aggregate_workload_from_tasks, confirm_assignments, recommend_assignments
from pm_agent.models import MemberProfile, ModuleKnowledgeEntry, RequirementItem, TaskHistoryProfile


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


class AggregateWorkloadFromTasksTest(unittest.TestCase):
    def test_calculate_workload_from_incomplete_tasks(self) -> None:
        """Only "计划" and "进行中" tasks should count toward workload."""
        records = [
            {"owner": "张三", "status": "计划", "planned_person_days": 1.0},
            {"owner": "张三", "status": "进行中", "planned_person_days": 0.5},
            {"owner": "李四", "status": "计划", "planned_person_days": 0.3},
        ]
        members = [
            MemberProfile(name="张三", workload=0.0, capacity=1.0),
            MemberProfile(name="李四", workload=0.0, capacity=1.0),
        ]
        workloads = aggregate_workload_from_tasks(records, members)
        self.assertAlmostEqual(1.5, workloads["张三"])
        self.assertAlmostEqual(0.3, workloads["李四"])

    def test_completed_tasks_excluded(self) -> None:
        """Completed tasks should not count toward workload."""
        records = [
            {"owner": "张三", "status": "已完成", "planned_person_days": 2.0},
            {"owner": "张三", "status": "计划", "planned_person_days": 1.0},
        ]
        members = [MemberProfile(name="张三", workload=0.0, capacity=1.0)]
        workloads = aggregate_workload_from_tasks(records, members)
        self.assertAlmostEqual(1.0, workloads["张三"])

    def test_fallback_to_manual_workload(self) -> None:
        """Members with no task records should use manual workload."""
        records = [
            {"owner": "张三", "status": "计划", "planned_person_days": 1.0},
        ]
        members = [
            MemberProfile(name="张三", workload=0.0, capacity=1.0),
            MemberProfile(name="李四", workload=0.5, capacity=1.0),
        ]
        workloads = aggregate_workload_from_tasks(records, members)
        self.assertAlmostEqual(1.0, workloads["张三"])
        self.assertAlmostEqual(0.5, workloads["李四"])

    def test_empty_owner_skipped(self) -> None:
        """Records with empty owner should be skipped."""
        records = [
            {"owner": "", "status": "计划", "planned_person_days": 1.0},
            {"owner": None, "status": "计划", "planned_person_days": 0.5},
            {"owner": "  ", "status": "进行中", "planned_person_days": 0.3},
        ]
        members = [MemberProfile(name="张三", workload=0.0, capacity=1.0)]
        workloads = aggregate_workload_from_tasks(records, members)
        # Only fallback to manual value
        self.assertAlmostEqual(0.0, workloads["张三"])

    def test_zero_planned_person_days(self) -> None:
        """Tasks with planned_person_days=0 should not contribute."""
        records = [
            {"owner": "张三", "status": "计划", "planned_person_days": 0},
            {"owner": "张三", "status": "进行中", "planned_person_days": None},
        ]
        members = [MemberProfile(name="张三", workload=0.0, capacity=1.0)]
        workloads = aggregate_workload_from_tasks(records, members)
        # No task records with positive planned_person_days, so fallback to manual
        self.assertAlmostEqual(0.0, workloads["张三"])

    def test_no_records_fallback_all_manual(self) -> None:
        """When no task records exist, all members use manual workload."""
        members = [
            MemberProfile(name="张三", workload=0.3, capacity=1.0),
            MemberProfile(name="李四", workload=0.7, capacity=1.0),
        ]
        workloads = aggregate_workload_from_tasks([], members)
        self.assertAlmostEqual(0.3, workloads["张三"])
        self.assertAlmostEqual(0.7, workloads["李四"])


class AggregateTaskHistoryTest(unittest.TestCase):
    def test_aggregate_with_records(self) -> None:
        records = [
            {"owner": "张三", "task_type": "产品迭代与运维->设计与编码", "module_path": "金蝶征信 -> 01-RPA", "planned_person_days": 1.0, "actual_person_days": 1.1, "defect_count": 0},
            {"owner": "张三", "task_type": "产品迭代与运维->设计与编码", "module_path": "金蝶征信 -> 01-RPA", "planned_person_days": 0.5, "actual_person_days": 0.4, "defect_count": 1},
            {"owner": "李四", "task_type": "产品迭代与运维->测试验证", "module_path": "金蝶征信 -> 02-采集", "planned_person_days": 0.3, "actual_person_days": 0.3, "defect_count": 0},
        ]
        profiles = aggregate_task_history(records)
        self.assertIn("张三", profiles)
        self.assertEqual(2, profiles["张三"].total_tasks)
        self.assertEqual(2, profiles["张三"].design_coding_tasks)
        self.assertIn("金蝶征信 -> 01-RPA", profiles["张三"].module_path_counts)
        self.assertEqual(2, profiles["张三"].module_path_counts["金蝶征信 -> 01-RPA"])
        self.assertIn("李四", profiles)
        self.assertEqual(1, profiles["李四"].total_tasks)

    def test_aggregate_no_records(self) -> None:
        profiles = aggregate_task_history([])
        self.assertEqual({}, profiles)

    def test_aggregate_empty_owner_skipped(self) -> None:
        records = [{"owner": "", "task_type": "设计", "module_path": "test", "planned_person_days": 0, "actual_person_days": 0, "defect_count": 0}]
        profiles = aggregate_task_history(records)
        self.assertEqual({}, profiles)


class TaskHistoryScoringTest(unittest.TestCase):
    def test_task_history_module_match_bonus(self) -> None:
        """Module path matching should add +1 per matching task, capped at +3."""
        from pm_agent.assignment import _member_score

        req = RequirementItem(requirement_id="1", title="测试", matched_module_keys=["金蝶征信 -> 01-RPA"])
        member = MemberProfile(name="张三", workload=0.0, capacity=1.0)
        tp = TaskHistoryProfile(
            member_name="张三",
            total_tasks=5,
            design_coding_tasks=3,
            module_path_counts={"金蝶征信 -> 01-RPA": 2},
        )
        score, reasons = _member_score(req, member, None, task_profile=tp)
        # +2 for module match (2 tasks), +1 for design experience
        self.assertGreaterEqual(score, 3)
        self.assertTrue(any("任务记录" in r for r in reasons))

    def test_task_history_design_coding_bonus(self) -> None:
        """Design-and-coding experience should add +1."""
        from pm_agent.assignment import _member_score

        req = RequirementItem(requirement_id="1", title="测试", matched_module_keys=[])
        member = MemberProfile(name="张三", workload=0.0, capacity=1.0)
        tp = TaskHistoryProfile(member_name="张三", total_tasks=5, design_coding_tasks=3)
        score, reasons = _member_score(req, member, None, task_profile=tp)
        self.assertGreaterEqual(score, 1)
        self.assertTrue(any("设计与编码" in r for r in reasons))

    def test_task_history_high_defect_penalty(self) -> None:
        """High defect rate (>2 defects per task) should subtract -1."""
        from pm_agent.assignment import _member_score

        req = RequirementItem(requirement_id="1", title="测试", matched_module_keys=[])
        member = MemberProfile(name="张三", workload=0.0, capacity=1.0)
        tp = TaskHistoryProfile(member_name="张三", total_tasks=2, total_defects=5)
        score, reasons = _member_score(req, member, None, task_profile=tp)
        # Base availability is +2, defect penalty is -1, net = +1
        self.assertTrue(any("缺陷率" in r for r in reasons))
        # Verify the penalty is applied by comparing with a clean profile
        tp_clean = TaskHistoryProfile(member_name="张三", total_tasks=2, total_defects=0)
        score_clean, _ = _member_score(req, member, None, task_profile=tp_clean)
        self.assertLess(score, score_clean)  # Defect profile should score lower

    def test_task_history_estimation_accuracy_bonus(self) -> None:
        """Accurate estimation (0.8 <= ratio <= 1.2) should add +0.5."""
        from pm_agent.assignment import _member_score

        req = RequirementItem(requirement_id="1", title="测试", matched_module_keys=[])
        member = MemberProfile(name="张三", workload=0.0, capacity=1.0)
        tp = TaskHistoryProfile(member_name="张三", total_tasks=3, avg_actual_vs_planned=1.0)
        score, reasons = _member_score(req, member, None, task_profile=tp)
        self.assertGreaterEqual(score, 0.5)
        self.assertTrue(any("估算准确" in r for r in reasons))


class TaskHistoryIntegrationTest(unittest.TestCase):
    def test_recommend_with_task_history(self) -> None:
        """Task history should influence recommendations and appear in reasons."""
        requirement = RequirementItem(
            requirement_id="1",
            title="接口改造需求",
            matched_module_keys=["税务::发票接口"],
        )
        module_entry = ModuleKnowledgeEntry(
            key="税务::发票接口",
            big_module="税务",
            function_module="发票接口",
            primary_owner="",
        )
        members = [
            MemberProfile(name="李祥", workload=0.5, capacity=1.0),
            MemberProfile(name="王海林", workload=0.5, capacity=1.0),
        ]
        # 王海林 has task history in matching module
        task_history = {
            "王海林": TaskHistoryProfile(
                member_name="王海林",
                total_tasks=3,
                design_coding_tasks=2,
                module_path_counts={"税务::发票接口": 3},
            ),
            "李祥": TaskHistoryProfile(
                member_name="李祥",
                total_tasks=1,
                design_coding_tasks=0,
                module_path_counts={"其他模块": 1},
            ),
        }
        recommendations = recommend_assignments(
            [requirement], members, {module_entry.key: module_entry}, task_history=task_history,
        )
        rec = recommendations[0]
        # 王海林 should score higher due to task history
        self.assertEqual("王海林", rec.development_owner)
        # Reasons should include task history
        self.assertTrue(
            any("任务记录" in r or "设计与编码" in r for r in rec.reasons),
            f"Expected task history in reasons, got: {rec.reasons}",
        )
