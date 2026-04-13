from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from pm_agent.platform_sync import sync_platform_exports
from pm_agent.models import AgentState
from pm_agent.monitoring import generate_execution_alerts


class SyncAndMonitoringTest(unittest.TestCase):
    def _create_story_workbook(self, path: Path) -> None:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "列表数据"
        sheet.append(["序号", "用户故事名称", "状态", "用户故事编码", "计划提测完成时间", "负责人", "测试人员名称", "优先级", "关联缺陷", "详细说明（URL）", "开发人员名称"])
        sheet.append([1, "发票需求", "开发中", "PRJ-1", "2026-04-01", "李祥", "余萍", "高", 1, "https://example.com/story", "李祥"])
        sheet.append(["合计"])
        workbook.save(path)

    def _create_task_workbook(self, path: Path) -> None:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "列表数据"
        sheet.append(["序号", "任务编号", "关联用户故事", "任务名称", "任务类型", "负责人", "状态", "预计开始时间", "预计结束时间", "计划人天", "实际人天", "缺陷总数"])
        sheet.append([1, "TK-1", "发票需求", "设计与编码【发票需求】", "设计与编码", "李祥", "进行中", "2026-04-01", "2026-04-02", 1.0, 0.0, 0])
        workbook.save(path)

    def test_sync_and_monitoring(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            story_path = Path(tmpdir) / "story.xlsx"
            task_path = Path(tmpdir) / "task.xlsx"
            self._create_story_workbook(story_path)
            self._create_task_workbook(task_path)
            state = AgentState()
            batch = sync_platform_exports(state, story_path, task_path, imported_at="2026-04-10T09:00:00")
            self.assertEqual(2, len(batch.actions))
            alerts = generate_execution_alerts(state)
            self.assertTrue(any(alert.story_code == "PRJ-1" for alert in alerts))


if __name__ == "__main__":
    unittest.main()
