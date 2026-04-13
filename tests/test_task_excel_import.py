from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from pm_agent.task_excel_import import (
    CANONICAL_TASK_HEADERS,
    TASK_HEADER_COLUMN_MAP,
    TaskExcelHeaderError,
    import_task_excel,
)


class TaskExcelImportTest(unittest.TestCase):
    def _create_workbook(self, path: Path, headers: list[str], rows: list[list[object]]) -> None:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "列表数据"
        sheet.append(headers)
        for row in rows:
            sheet.append(row)
        workbook.save(path)

    def _build_row(self, task_code: str, name: str, *, seq: int = 1) -> list[object]:
        values: dict[str, object] = {header: None for header in CANONICAL_TASK_HEADERS}
        values["序号"] = seq
        values["任务编号"] = task_code
        values["关联用户故事"] = "【示例】测试故事"
        values["任务名称"] = name
        values["任务类型"] = "产品迭代与运维->设计与编码"
        values["负责人"] = "王海林"
        values["状态"] = "进行中"
        values["预计开始时间"] = "2026-04-09"
        values["预计结束时间"] = "2026-04-10"
        values["计划人天"] = 0.3
        values["实际人天"] = 0.5
        values["产品"] = "金蝶征信"
        values["模块路径"] = "金蝶征信 -> 01-RPA"
        values["所属项目"] = "金蝶征信（2026资源池）"
        values["版本"] = "V2026.0.0"
        values["迭代阶段"] = None
        values["项目组"] = "金蝶征信"
        values["参与人"] = None
        values["客户名称"] = None
        values["缺陷总数"] = None
        values["关联代码"] = None
        values["创建人"] = "李文强"
        values["创建时间"] = "2026-04-09 09:12:28"
        values["修改人"] = "王海林"
        values["修改时间"] = "2026-04-10 14:53:24"
        return [values[header] for header in CANONICAL_TASK_HEADERS]

    def test_import_task_excel_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "task.xlsx"
            self._create_workbook(
                file_path,
                CANONICAL_TASK_HEADERS,
                [self._build_row("TK-00461976", "设计与编码")],
            )

            result = import_task_excel(file_path)
            self.assertEqual(1, result.total_rows)
            self.assertEqual(1, len(result.valid_rows))
            self.assertEqual(0, len(result.errors))

            row = result.valid_rows[0]
            self.assertEqual("TK-00461976", row["task_code"])
            self.assertEqual("设计与编码", row["name"])
            self.assertEqual("产品迭代与运维->设计与编码", row["task_type"])
            self.assertEqual("王海林", row["owner"])
            self.assertEqual("进行中", row["status"])
            self.assertEqual(0.3, row["planned_person_days"])
            self.assertEqual(0.5, row["actual_person_days"])
            self.assertEqual(len(CANONICAL_TASK_HEADERS), len(TASK_HEADER_COLUMN_MAP))

    def test_import_task_excel_missing_required_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "task.xlsx"
            headers = [header for header in CANONICAL_TASK_HEADERS if header != "任务编号"]
            row_values = ["示例" for _ in headers]
            self._create_workbook(file_path, headers, [row_values])

            with self.assertRaises(TaskExcelHeaderError) as context:
                import_task_excel(file_path)
            self.assertIn("任务编号", context.exception.missing_headers)

    def test_import_task_excel_missing_task_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "task.xlsx"
            self._create_workbook(file_path, CANONICAL_TASK_HEADERS, [
                self._build_row("", "无编号任务"),
                self._build_row("TK-001", "有编号任务"),
            ])

            result = import_task_excel(file_path)
            self.assertEqual(2, result.total_rows)
            self.assertEqual(1, len(result.valid_rows))
            self.assertEqual(1, len(result.errors))
            self.assertEqual("缺少任务编号", result.errors[0].reason)

    def test_import_task_excel_empty_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "task.xlsx"
            self._create_workbook(file_path, CANONICAL_TASK_HEADERS, [])

            result = import_task_excel(file_path)
            self.assertEqual(0, result.total_rows)
            self.assertEqual(0, len(result.valid_rows))

    def test_import_task_excel_real_file(self) -> None:
        real_path = Path(__file__).resolve().parent.parent / "docs" / "导出列表_任务列表_0410191645.xlsx"
        if real_path.exists():
            result = import_task_excel(real_path)
            self.assertGreater(result.total_rows, 0)
            self.assertGreater(len(result.valid_rows), 0)
            self.assertEqual(0, len(result.missing_headers))


if __name__ == "__main__":
    unittest.main()
