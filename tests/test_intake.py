from __future__ import annotations

import unittest

from pm_agent.intake import parse_chat_requirements, parse_imported_requirements


class IntakeTest(unittest.TestCase):
    def test_parse_group_message(self) -> None:
        message = """
1. 发票查验接口替换为长软新数据源需求 https://example.com/1 优先级高
2. 20260331 安徽银税互动授权记录采集新入口，优先级：高
https://example.com/2
"""
        requirements = parse_chat_requirements(message)
        self.assertEqual(2, len(requirements))
        self.assertEqual("1", requirements[0].requirement_id)
        self.assertEqual("高", requirements[0].priority)
        self.assertIn("https://example.com/1", requirements[0].source_url)
        self.assertEqual("高", requirements[1].risk)
        self.assertTrue(requirements[1].split_suggestion is not None)

    def test_parse_imported_requirements_normalizes_numeric_id(self) -> None:
        requirements = parse_imported_requirements(
            [
                {
                    "id": 2.0,
                    "title": "发票补偿",
                    "raw_text": "发票补偿 优先级高",
                }
            ]
        )
        self.assertEqual(1, len(requirements))
        self.assertEqual("2", requirements[0].requirement_id)


if __name__ == "__main__":
    unittest.main()
