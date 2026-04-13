from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from pm_agent.knowledge_base import import_module_knowledge_from_excel, update_module_knowledge_after_assignment
from pm_agent.models import ConfirmedAssignment


class ModuleKnowledgeBaseTest(unittest.TestCase):
    def _create_workbook(self, path: Path) -> None:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "2025泾渭云后端技术角度的业务模块"
        sheet.append(["主要负责人", "B角", "大模块", "功能模块", "李祥", "王海林"])
        sheet.append(["", "", "", "", "李祥", "王海林"])
        sheet.append(["何永乐", "王海林", "网关", "api加解密方式：v2，v4", "熟悉", "了解"])
        sheet.append(["", "", "", "api加解密方式：v5", "了解", "熟悉"])
        workbook.save(path)

    def test_import_module_knowledge(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "module.xlsx"
            self._create_workbook(path)
            entries = import_module_knowledge_from_excel(path)
            self.assertEqual(2, len(entries))
            self.assertEqual("何永乐", entries[0].primary_owner)
            self.assertEqual("王海林", entries[1].backup_owner)

    def test_update_module_knowledge_after_assignment(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "module.xlsx"
            self._create_workbook(path)
            entries = {entry.key: entry for entry in import_module_knowledge_from_excel(path)}
            updated = update_module_knowledge_after_assignment(
                entries,
                [
                    ConfirmedAssignment(
                        requirement_id="1",
                        title="网关需求",
                        module_key="网关::api加解密方式：v2，v4",
                        development_owner="李祥",
                        testing_owner="王海林",
                    )
                ],
            )
            entry = updated["网关::api加解密方式：v2，v4"]
            self.assertEqual(1, len(entry.assignment_history))
            self.assertIn("李祥", entry.recent_assignees)


if __name__ == "__main__":
    unittest.main()
