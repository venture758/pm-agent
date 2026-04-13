from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from pm_agent.story_excel_import import (
    CANONICAL_STORY_HEADERS,
    STORY_HEADER_COLUMN_MAP,
    StoryExcelHeaderError,
    import_story_excel,
)


class StoryExcelImportTest(unittest.TestCase):
    def _create_workbook(self, path: Path, headers: list[str], rows: list[list[object]]) -> None:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "列表数据"
        sheet.append(headers)
        for row in rows:
            sheet.append(row)
        workbook.save(path)

    def _build_row(self, story_code: str, story_name: str, *, seq: int = 1) -> list[object]:
        values = {header: None for header in CANONICAL_STORY_HEADERS}
        values["序号"] = seq
        values["用户故事名称"] = story_name
        values["状态"] = "计划"
        values["用户故事编码"] = story_code
        values["负责人"] = "李祥"
        values["测试人员名称"] = "余萍"
        values["优先级"] = "高"
        values["计划人天"] = 2
        values["计划开发人天"] = 1.5
        values["关联缺陷"] = 0
        values["详细说明（URL）"] = "https://example.com/story"
        values["开发人员名称"] = "李祥;王海林"
        values["修改时间"] = "2026-04-13 18:00:00"
        return [values[header] for header in CANONICAL_STORY_HEADERS]

    def test_import_story_excel_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "story.xlsx"
            self._create_workbook(
                file_path,
                CANONICAL_STORY_HEADERS,
                [self._build_row("PRJ-00731813", "发票查验接口替换")],
            )

            result = import_story_excel(file_path)
            self.assertEqual(1, result.total_rows)
            self.assertEqual(1, len(result.valid_rows))
            self.assertEqual(0, len(result.errors))

            row = result.valid_rows[0]
            self.assertEqual("PRJ-00731813", row["user_story_code"])
            self.assertEqual("发票查验接口替换", row["user_story_name"])
            self.assertEqual(2.0, row["planned_person_days"])
            self.assertEqual(1.5, row["planned_dev_person_days"])
            self.assertEqual("https://example.com/story", row["detail_url"])
            self.assertIn("user_story_code", row)
            self.assertEqual(len(CANONICAL_STORY_HEADERS), len(STORY_HEADER_COLUMN_MAP))

    def test_import_story_excel_missing_required_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "story.xlsx"
            headers = [header for header in CANONICAL_STORY_HEADERS if header != "用户故事编码"]
            row_values = ["示例" for _ in headers]
            self._create_workbook(file_path, headers, [row_values])

            with self.assertRaises(StoryExcelHeaderError) as context:
                import_story_excel(file_path)
            self.assertIn("用户故事编码", context.exception.missing_headers)


if __name__ == "__main__":
    unittest.main()
