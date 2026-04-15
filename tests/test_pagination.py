from __future__ import annotations

import tempfile
import unittest

from pm_agent.workspace_store import WorkspaceStore


def _create_test_store() -> WorkspaceStore:
    tmpdir = tempfile.mkdtemp()
    url = f"sqlite:///{tmpdir}/test.db"
    store = WorkspaceStore(database_url=url)
    return store


def _insert_story(store: WorkspaceStore, workspace_id: str, code: str, name: str, modified_time: str = "2026-01-01") -> None:
    with store.database.connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO workspace_story_records ("
            "workspace_id, user_story_code, user_story_name, modified_time, imported_at, updated_at"
            ") VALUES (?, ?, ?, ?, ?, ?)",
            (workspace_id, code, name, modified_time, "2026-01-01", "2026-01-01"),
        )


def _insert_task(store: WorkspaceStore, workspace_id: str, code: str, owner: str = "", status: str = "", project_name: str = "") -> None:
    with store.database.connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO workspace_task_records ("
            "workspace_id, task_code, name, owner, status, project_name, modified_time, imported_at, updated_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (workspace_id, code, code, owner, status, project_name, "2026-01-01", "2026-01-01", "2026-01-01"),
        )


class StoryPaginationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = _create_test_store()
        # Tables are auto-created by DatabaseStore._ensure_sqlite_schema()
        self.ws = "ws-pagination"
        for i in range(25):
            _insert_story(self.store, self.ws, f"US-{i:03d}", f"Story {i}", modified_time=f"2026-01-{(i % 28) + 1:02d}")

    def test_default_pagination_returns_first_page(self) -> None:
        items, total = self.store.load_story_records_paginated(self.ws, page=1, page_size=20)
        self.assertEqual(total, 25)
        self.assertEqual(len(items), 20)

    def test_second_page(self) -> None:
        items, total = self.store.load_story_records_paginated(self.ws, page=2, page_size=20)
        self.assertEqual(len(items), 5)

    def test_keyword_filter(self) -> None:
        items, total = self.store.load_story_records_paginated(self.ws, page=1, page_size=20, keyword="US-005")
        self.assertEqual(total, 1)
        self.assertEqual(len(items), 1)

    def test_empty_workspace(self) -> None:
        items, total = self.store.load_story_records_paginated("empty-ws", page=1, page_size=20)
        self.assertEqual(total, 0)
        self.assertEqual(len(items), 0)

    def test_out_of_range_page(self) -> None:
        items, total = self.store.load_story_records_paginated(self.ws, page=999, page_size=20)
        self.assertEqual(total, 25)
        self.assertEqual(len(items), 0)


class TaskPaginationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.store = _create_test_store()
        self.ws = "ws-task-pagination"
        for i in range(30):
            owner = "Alice" if i < 10 else ("Bob" if i < 20 else "")
            status = "进行中" if i < 15 else ("已完成" if i < 25 else "计划")
            project = "项目A" if i < 20 else "项目B"
            _insert_task(self.store, self.ws, f"TASK-{i:03d}", owner=owner, status=status, project_name=project)

    def test_pagination_without_filters(self) -> None:
        items, total = self.store.load_task_records_from_table(self.ws, page=1, page_size=20)
        self.assertEqual(total, 30)
        self.assertEqual(len(items), 20)

    def test_pagination_with_owner_filter(self) -> None:
        items, total = self.store.load_task_records_from_table(self.ws, page=1, page_size=20, owner="Alice")
        self.assertEqual(total, 10)
        self.assertEqual(len(items), 10)

    def test_pagination_with_status_filter(self) -> None:
        items, total = self.store.load_task_records_from_table(self.ws, page=1, page_size=20, status="进行中")
        self.assertEqual(total, 15)
        self.assertEqual(len(items), 15)

    def test_pagination_with_project_filter(self) -> None:
        items, total = self.store.load_task_records_from_table(self.ws, page=1, page_size=20, project_name="项目B")
        self.assertEqual(total, 10)
        self.assertEqual(len(items), 10)

    def test_out_of_range_page(self) -> None:
        items, total = self.store.load_task_records_from_table(self.ws, page=999, page_size=20)
        self.assertEqual(total, 30)
        self.assertEqual(len(items), 0)

    def test_backward_compatible_no_pagination(self) -> None:
        """Calling without page/page_size should return a plain list (backward compatible)."""
        result = self.store.load_task_records_from_table(self.ws, owner="Alice")
        # When no pagination params, returns list directly
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 10)


if __name__ == "__main__":
    unittest.main()
