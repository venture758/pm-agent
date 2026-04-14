from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import uuid4

from .config import DEFAULT_STATE_ROOT
from .database import DatabaseStore
from .models import AssignmentRecommendation, MemberProfile, ModuleKnowledgeEntry, StoryRecord
from .story_excel_import import STORY_DB_COLUMNS, row_to_story_record
from .task_excel_import import TASK_DB_COLUMNS, row_to_task_record


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")
from .utils import normalize_requirement_id
from .workspace_models import WorkspaceState, WorkspaceUpload


class WorkspaceStore:
    def __init__(self, root: str | Path = DEFAULT_STATE_ROOT, database_url: str | None = None) -> None:
        self.base_root = Path(root)
        self.root = self.base_root / "workspaces"
        self.root.mkdir(parents=True, exist_ok=True)
        self.database = DatabaseStore(root=self.base_root, database_url=database_url)
        self._migrate_legacy_workspaces_if_needed()

    def workspace_dir(self, workspace_id: str) -> Path:
        directory = self.root / workspace_id
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def uploads_dir(self, workspace_id: str) -> Path:
        directory = self.workspace_dir(workspace_id) / "uploads"
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def load_workspace(self, workspace_id: str) -> WorkspaceState:
        payload = self.database.load_json("workspace_states", "workspace_id", workspace_id)
        workspace = WorkspaceState.from_dict(payload) if payload else WorkspaceState(workspace_id=workspace_id, title=workspace_id)
        workspace.current_session_requirement_ids = self._normalize_session_ids(workspace.current_session_requirement_ids)
        table_members = self._load_managed_members_from_table(workspace_id)
        if table_members:
            workspace.managed_members = table_members
        elif workspace.managed_members:
            workspace.managed_members = self._sorted_members(workspace.managed_members)
            self._save_managed_members_to_table(workspace_id, workspace.managed_members, workspace.updated_at)
        table_entries = self._load_module_entries_from_table(workspace_id)
        if table_entries:
            workspace.module_entries = table_entries
        table_recommendations = self._load_recommendations_from_table(workspace_id)
        if table_recommendations:
            workspace.recommendations = table_recommendations
        elif workspace.recommendations:
            # Compatibility path: migrate legacy recommendations from workspace payload into dedicated table.
            self.save_workspace(workspace)
        table_stories = self.load_story_records_from_table(workspace_id)
        if table_stories:
            workspace.handoff_stories = [row_to_story_record(item) for item in table_stories]
        return workspace

    def save_workspace(self, workspace: WorkspaceState) -> None:
        workspace.current_session_requirement_ids = self._normalize_session_ids(workspace.current_session_requirement_ids)
        payload = asdict(workspace)
        payload["managed_members"] = []
        payload["recommendations"] = []
        self.database.save_json("workspace_states", "workspace_id", workspace.workspace_id, payload)
        self._save_managed_members_to_table(workspace.workspace_id, workspace.managed_members, workspace.updated_at)
        self._save_module_entries_to_table(workspace.workspace_id, workspace.module_entries, workspace.updated_at)
        self._save_recommendations_to_table(workspace.workspace_id, workspace.recommendations, workspace.updated_at)

    def append_confirmation_record(
        self,
        workspace_id: str,
        session_id: str,
        confirmed_assignments: list[Any],
        created_at: str | None = None,
    ) -> None:
        timestamp = created_at or datetime.utcnow().isoformat()
        payload_items: list[dict[str, Any]] = []
        for item in confirmed_assignments:
            if hasattr(item, "__dataclass_fields__"):
                payload_items.append(asdict(item))
            elif isinstance(item, dict):
                payload_items.append(dict(item))
            else:
                payload_items.append({"value": str(item)})
        record_payload = {
            "workspace_id": workspace_id,
            "session_id": str(session_id or ""),
            "confirmed_count": len(payload_items),
            "confirmed_assignments": payload_items,
        }
        if self.database.scheme == "sqlite":
            insert_sql = (
                "INSERT INTO workspace_confirmation_records ("
                "workspace_id, session_id, confirmed_count, payload_json, created_at"
                ") VALUES (?, ?, ?, ?, ?)"
            )
        else:
            insert_sql = (
                "INSERT INTO workspace_confirmation_records ("
                "workspace_id, session_id, confirmed_count, payload_json, created_at"
                ") VALUES (%s, %s, %s, %s, %s)"
            )
        try:
            with self.database.connection() as connection:
                cursor = connection.cursor()
                cursor.execute(
                    insert_sql,
                    (
                        workspace_id,
                        str(session_id or ""),
                        len(payload_items),
                        json.dumps(record_payload, ensure_ascii=False, default=_json_default),
                        timestamp,
                    ),
                )
        except Exception as exc:
            self.database._raise_schema_hint_if_needed(exc)
            raise

    def load_confirmation_records(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """分页查询确认记录，按 created_at 降序排列。返回 (items, total_count)。"""
        ph = self.database.placeholder
        count_sql = (
            f"SELECT COUNT(*) FROM workspace_confirmation_records WHERE workspace_id = {ph}"
        )
        data_sql = (
            "SELECT session_id, confirmed_count, payload_json, created_at "
            f"FROM workspace_confirmation_records WHERE workspace_id = {ph} "
            "ORDER BY created_at DESC"
        )
        if self.database.scheme == "sqlite":
            data_sql += " LIMIT ? OFFSET ?"
        else:
            data_sql += " LIMIT %s OFFSET %s"

        offset = max(page - 1, 0) * page_size

        try:
            with self.database.connection() as connection:
                cursor = connection.cursor()
                cursor.execute(count_sql, (workspace_id,))
                row = cursor.fetchone()
                total = int(row[0] if isinstance(row, tuple) else row["COUNT(*)"]) if row else 0

                if total == 0:
                    return [], 0

                cursor.execute(data_sql, (workspace_id, page_size, offset))
                rows = cursor.fetchall() or []
        except Exception as exc:
            message = str(exc).lower()
            if "workspace_confirmation_records" in message and ("doesn't exist" in message or "no such table" in message):
                return [], 0
            self.database._raise_schema_hint_if_needed(exc)
            raise

        items: list[dict[str, Any]] = []
        for row in rows:
            get = (lambda key: row[key]) if isinstance(row, dict) or hasattr(row, "keys") else None
            payload_text = get("payload_json") if get else row[2]
            payload = json.loads(payload_text)
            items.append({
                "session_id": str(get("session_id") if get else row[0]),
                "confirmed_count": int(get("confirmed_count") if get else row[1]),
                "confirmed_assignments": payload.get("confirmed_assignments", []),
                "created_at": str(get("created_at") if get else row[3]),
            })
        return items, total

    def save_upload(self, workspace_id: str, kind: str, filename: str, content: bytes) -> WorkspaceUpload:
        target_dir = self.uploads_dir(workspace_id) / kind
        target_dir.mkdir(parents=True, exist_ok=True)
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "-", filename).strip("-") or f"{kind}.bin"
        target_path = target_dir / f"{uuid4().hex[:8]}-{safe_name}"
        target_path.write_bytes(content)
        return WorkspaceUpload(
            kind=kind,
            original_name=filename,
            stored_path=str(target_path),
        )

    def _migrate_legacy_workspaces_if_needed(self) -> None:
        for workspace_file in self.root.glob("*/workspace.json"):
            workspace_id = workspace_file.parent.name
            if self.database.load_json("workspace_states", "workspace_id", workspace_id) is not None:
                continue
            payload = json.loads(workspace_file.read_text(encoding="utf-8"))
            workspace = WorkspaceState.from_dict(payload)
            workspace.current_session_requirement_ids = self._normalize_session_ids(workspace.current_session_requirement_ids)
            normalized_payload = asdict(workspace)
            normalized_payload["managed_members"] = []
            normalized_payload["recommendations"] = []
            self.database.save_json("workspace_states", "workspace_id", workspace_id, normalized_payload)
            self._save_managed_members_to_table(workspace_id, workspace.managed_members, workspace.updated_at)
            self._save_module_entries_to_table(workspace_id, workspace.module_entries, workspace.updated_at)
            self._save_recommendations_to_table(workspace_id, workspace.recommendations, workspace.updated_at)

    def _load_managed_members_from_table(self, workspace_id: str) -> list[MemberProfile]:
        sql = (
            "SELECT member_name, role, skills_json, experience_level, workload, capacity, constraints_json "
            f"FROM workspace_managed_members WHERE workspace_id = {self.database.placeholder} "
            "ORDER BY member_name"
        )
        try:
            with self.database.connection() as connection:
                cursor = connection.cursor()
                cursor.execute(sql, (workspace_id,))
                rows = cursor.fetchall() or []
        except Exception as exc:
            self.database._raise_schema_hint_if_needed(exc)
            raise
        members: list[MemberProfile] = []
        for row in rows:
            get = (lambda key: row[key]) if isinstance(row, dict) or hasattr(row, "keys") else None
            members.append(
                MemberProfile(
                    name=str(get("member_name") if get else row[0]),
                    role=str(get("role") if get else row[1]),
                    skills=json.loads(get("skills_json") if get else row[2]),
                    experience_level=str(get("experience_level") if get else row[3]),
                    workload=float(get("workload") if get else row[4]),
                    capacity=float(get("capacity") if get else row[5]),
                    constraints=json.loads(get("constraints_json") if get else row[6]),
                )
            )
        return members

    def _load_module_entries_from_table(self, workspace_id: str) -> list[ModuleKnowledgeEntry]:
        sql = (
            "SELECT module_key, big_module, function_module, primary_owner, backup_owners_json, "
            "familiar_members_json, aware_members_json, unfamiliar_members_json, source_sheet, source_year, "
            "imported_at, recent_assignees_json, suggested_familiarity_json, assignment_history_json "
            f"FROM workspace_module_entries WHERE workspace_id = {self.database.placeholder} "
            "ORDER BY big_module, function_module, module_key"
        )
        try:
            with self.database.connection() as connection:
                cursor = connection.cursor()
                cursor.execute(sql, (workspace_id,))
                rows = cursor.fetchall() or []
        except Exception as exc:
            self.database._raise_schema_hint_if_needed(exc)
            raise
        entries: list[ModuleKnowledgeEntry] = []
        for row in rows:
            get = (lambda key: row[key]) if isinstance(row, dict) or hasattr(row, "keys") else None
            values = {
                "key": get("module_key") if get else row[0],
                "big_module": get("big_module") if get else row[1],
                "function_module": get("function_module") if get else row[2],
                "primary_owner": get("primary_owner") if get else row[3],
                "backup_owners": json.loads(get("backup_owners_json") if get else row[4]),
                "familiar_members": json.loads(get("familiar_members_json") if get else row[5]),
                "aware_members": json.loads(get("aware_members_json") if get else row[6]),
                "unfamiliar_members": json.loads(get("unfamiliar_members_json") if get else row[7]),
                "source_sheet": get("source_sheet") if get else row[8],
                "source_year": int(get("source_year") if get else row[9]),
                "imported_at": get("imported_at") if get else row[10],
                "recent_assignees": json.loads(get("recent_assignees_json") if get else row[11]),
                "suggested_familiarity": json.loads(get("suggested_familiarity_json") if get else row[12]),
                "assignment_history": json.loads(get("assignment_history_json") if get else row[13]),
            }
            entries.append(ModuleKnowledgeEntry.from_payload(values))
        return entries

    def _save_module_entries_to_table(
        self,
        workspace_id: str,
        entries: list[ModuleKnowledgeEntry],
        updated_at: str,
    ) -> None:
        delete_sql = f"DELETE FROM workspace_module_entries WHERE workspace_id = {self.database.placeholder}"
        if self.database.scheme == "sqlite":
            insert_sql = (
                "INSERT INTO workspace_module_entries ("
                "workspace_id, module_key, big_module, function_module, primary_owner, "
                "backup_owners_json, familiar_members_json, aware_members_json, unfamiliar_members_json, "
                "source_sheet, source_year, imported_at, recent_assignees_json, suggested_familiarity_json, "
                "assignment_history_json, updated_at"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            )
        else:
            insert_sql = (
                "INSERT INTO workspace_module_entries ("
                "workspace_id, module_key, big_module, function_module, primary_owner, "
                "backup_owners_json, familiar_members_json, aware_members_json, unfamiliar_members_json, "
                "source_sheet, source_year, imported_at, recent_assignees_json, suggested_familiarity_json, "
                "assignment_history_json, updated_at"
                ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
            )
        try:
            with self.database.connection() as connection:
                cursor = connection.cursor()
                cursor.execute(delete_sql, (workspace_id,))
                for entry in entries:
                    cursor.execute(
                        insert_sql,
                        (
                            workspace_id,
                            entry.key,
                            entry.big_module,
                            entry.function_module,
                            entry.primary_owner,
                            json.dumps(entry.backup_owners, ensure_ascii=False, default=_json_default),
                            json.dumps(entry.familiar_members, ensure_ascii=False, default=_json_default),
                            json.dumps(entry.aware_members, ensure_ascii=False, default=_json_default),
                            json.dumps(entry.unfamiliar_members, ensure_ascii=False, default=_json_default),
                            entry.source_sheet,
                            int(entry.source_year or 0),
                            entry.imported_at,
                            json.dumps(entry.recent_assignees, ensure_ascii=False, default=_json_default),
                            json.dumps(entry.suggested_familiarity, ensure_ascii=False, default=_json_default),
                            json.dumps([asdict(item) for item in entry.assignment_history], ensure_ascii=False, default=_json_default),
                            updated_at,
                        ),
                    )
        except Exception as exc:
            self.database._raise_schema_hint_if_needed(exc)
            raise

    def _save_managed_members_to_table(
        self,
        workspace_id: str,
        members: list[MemberProfile],
        updated_at: str,
    ) -> None:
        delete_sql = f"DELETE FROM workspace_managed_members WHERE workspace_id = {self.database.placeholder}"
        if self.database.scheme == "sqlite":
            insert_sql = (
                "INSERT INTO workspace_managed_members ("
                "workspace_id, member_name, role, skills_json, experience_level, workload, capacity, "
                "constraints_json, updated_at"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            )
        else:
            insert_sql = (
                "INSERT INTO workspace_managed_members ("
                "workspace_id, member_name, role, skills_json, experience_level, workload, capacity, "
                "constraints_json, updated_at"
                ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            )
        try:
            with self.database.connection() as connection:
                cursor = connection.cursor()
                cursor.execute(delete_sql, (workspace_id,))
                for member in self._sorted_members(members):
                    cursor.execute(
                        insert_sql,
                        (
                            workspace_id,
                            member.name,
                            member.role,
                            json.dumps(member.skills, ensure_ascii=False, default=_json_default),
                            member.experience_level,
                            float(member.workload),
                            float(member.capacity),
                            json.dumps(member.constraints, ensure_ascii=False, default=_json_default),
                            updated_at,
                        ),
                    )
        except Exception as exc:
            self.database._raise_schema_hint_if_needed(exc)
            raise

    def _load_recommendations_from_table(self, workspace_id: str) -> list[AssignmentRecommendation]:
        sql = (
            "SELECT requirement_id, payload_json "
            f"FROM workspace_recommendations WHERE workspace_id = {self.database.placeholder} "
            "ORDER BY id"
        )
        try:
            with self.database.connection() as connection:
                cursor = connection.cursor()
                cursor.execute(sql, (workspace_id,))
                rows = cursor.fetchall() or []
        except Exception as exc:
            self.database._raise_schema_hint_if_needed(exc)
            raise
        recommendations: list[AssignmentRecommendation] = []
        for row in rows:
            get = (lambda key: row[key]) if isinstance(row, dict) or hasattr(row, "keys") else None
            row_requirement_id = normalize_requirement_id(get("requirement_id") if get else row[0])
            payload_text = get("payload_json") if get else row[1]
            payload = json.loads(payload_text)
            payload_requirement_id = normalize_requirement_id(payload.get("requirement_id"))
            if payload_requirement_id != row_requirement_id:
                payload["requirement_id"] = row_requirement_id
            else:
                payload["requirement_id"] = payload_requirement_id
            recommendations.append(AssignmentRecommendation(**payload))
        return recommendations

    def _save_recommendations_to_table(
        self,
        workspace_id: str,
        recommendations: list[AssignmentRecommendation],
        updated_at: str,
    ) -> None:
        delete_sql = f"DELETE FROM workspace_recommendations WHERE workspace_id = {self.database.placeholder}"
        if self.database.scheme == "sqlite":
            insert_sql = (
                "INSERT INTO workspace_recommendations ("
                "workspace_id, requirement_id, payload_json, created_at, updated_at"
                ") VALUES (?, ?, ?, ?, ?)"
            )
        else:
            insert_sql = (
                "INSERT INTO workspace_recommendations ("
                "workspace_id, requirement_id, payload_json, created_at, updated_at"
                ") VALUES (%s, %s, %s, %s, %s)"
            )
        timestamp = updated_at or ""
        try:
            with self.database.connection() as connection:
                cursor = connection.cursor()
                cursor.execute(delete_sql, (workspace_id,))
                for recommendation in recommendations:
                    payload = asdict(recommendation)
                    normalized_requirement_id = normalize_requirement_id(payload.get("requirement_id"))
                    payload["requirement_id"] = normalized_requirement_id
                    cursor.execute(
                        insert_sql,
                        (
                            workspace_id,
                            normalized_requirement_id,
                            json.dumps(payload, ensure_ascii=False, default=_json_default),
                            timestamp,
                            timestamp,
                        ),
                    )
        except Exception as exc:
            self.database._raise_schema_hint_if_needed(exc)
            raise

    def upsert_story_records_to_table(
        self,
        workspace_id: str,
        story_rows: list[dict[str, Any]],
        *,
        updated_at: str,
        imported_at: str | None = None,
    ) -> tuple[int, int]:
        if not story_rows:
            return 0, 0

        created_count = 0
        updated_count = 0
        imported_at_value = imported_at or updated_at or datetime.utcnow().isoformat()
        story_codes = {
            str(row.get("user_story_code") or "").strip()
            for row in story_rows
            if str(row.get("user_story_code") or "").strip()
        }
        if not story_codes:
            return 0, 0

        select_existing_sql = (
            "SELECT user_story_code "
            f"FROM workspace_story_records WHERE workspace_id = {self.database.placeholder}"
        )

        insert_columns = ["workspace_id", *STORY_DB_COLUMNS, "imported_at", "updated_at"]
        if self.database.scheme == "sqlite":
            placeholders = ", ".join("?" for _ in insert_columns)
            update_columns = [column for column in STORY_DB_COLUMNS if column != "user_story_code"] + [
                "imported_at",
                "updated_at",
            ]
            update_clause = ", ".join(f"{column}=excluded.{column}" for column in update_columns)
            upsert_sql = (
                f"INSERT INTO workspace_story_records ({', '.join(insert_columns)}) "
                f"VALUES ({placeholders}) "
                "ON CONFLICT(workspace_id, user_story_code) DO UPDATE SET "
                f"{update_clause}"
            )
        else:
            placeholders = ", ".join("%s" for _ in insert_columns)
            update_columns = [column for column in STORY_DB_COLUMNS if column != "user_story_code"] + [
                "imported_at",
                "updated_at",
            ]
            update_clause = ", ".join(f"{column}=VALUES({column})" for column in update_columns)
            upsert_sql = (
                f"INSERT INTO workspace_story_records ({', '.join(insert_columns)}) "
                f"VALUES ({placeholders}) "
                f"ON DUPLICATE KEY UPDATE {update_clause}"
            )

        try:
            with self.database.connection() as connection:
                cursor = connection.cursor()
                cursor.execute(select_existing_sql, (workspace_id,))
                rows = cursor.fetchall() or []
                existing_codes = {
                    str((row["user_story_code"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]) or "")
                    for row in rows
                }
                for story_row in story_rows:
                    story_code = str(story_row.get("user_story_code") or "").strip()
                    if not story_code:
                        continue
                    is_update = story_code in existing_codes
                    values = [
                        workspace_id,
                        *[story_row.get(column) for column in STORY_DB_COLUMNS],
                        imported_at_value,
                        updated_at,
                    ]
                    cursor.execute(upsert_sql, tuple(values))
                    if is_update:
                        updated_count += 1
                    else:
                        created_count += 1
                        existing_codes.add(story_code)
        except Exception as exc:
            self.database._raise_schema_hint_if_needed(exc)
            raise

        return created_count, updated_count

    def load_story_records_paginated(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 20,
        keyword: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """分页查询故事记录，按 modified_time DESC, user_story_code 排序。返回 (items, total_count)。"""
        ph = self.database.placeholder
        base_conditions = [f"workspace_id = {ph}"]
        params: list[Any] = [workspace_id]

        if keyword:
            base_conditions.append(f"(user_story_code LIKE {ph} OR user_story_name LIKE {ph})")
            like_kw = f"%{keyword}%"
            params.extend([like_kw, like_kw])

        where_clause = " AND ".join(base_conditions)
        select_columns = ", ".join(STORY_DB_COLUMNS)
        count_sql = f"SELECT COUNT(*) FROM workspace_story_records WHERE {where_clause}"
        data_sql = f"SELECT {select_columns} FROM workspace_story_records WHERE {where_clause} ORDER BY modified_time DESC, user_story_code"
        if self.database.scheme == "sqlite":
            data_sql += " LIMIT ? OFFSET ?"
        else:
            data_sql += " LIMIT %s OFFSET %s"

        offset = max(page - 1, 0) * page_size

        try:
            with self.database.connection() as connection:
                cursor = connection.cursor()
                cursor.execute(count_sql, params)
                row = cursor.fetchone()
                total = int(row[0] if isinstance(row, tuple) else row[0]) if row else 0

                if total == 0:
                    return [], 0

                cursor.execute(data_sql, params + [page_size, offset])
                rows = cursor.fetchall() or []
        except Exception as exc:
            message = str(exc).lower()
            if "workspace_story_records" in message and ("doesn't exist" in message or "no such table" in message):
                return [], 0
            self.database._raise_schema_hint_if_needed(exc)
            raise

        results: list[dict[str, Any]] = []
        for row in rows:
            get = (lambda key: row[key]) if isinstance(row, dict) or hasattr(row, "keys") else None
            payload: dict[str, Any] = {}
            for index, column in enumerate(STORY_DB_COLUMNS):
                payload[column] = get(column) if get else row[index]
            results.append(payload)
        return results, total

    def load_story_records_from_table(self, workspace_id: str) -> list[dict[str, Any]]:
        select_columns = ", ".join(STORY_DB_COLUMNS)
        sql = (
            f"SELECT {select_columns} "
            f"FROM workspace_story_records WHERE workspace_id = {self.database.placeholder} "
            "ORDER BY modified_time DESC, user_story_code"
        )
        try:
            with self.database.connection() as connection:
                cursor = connection.cursor()
                cursor.execute(sql, (workspace_id,))
                rows = cursor.fetchall() or []
        except Exception as exc:
            message = str(exc).lower()
            if "workspace_story_records" in message and ("doesn't exist" in message or "no such table" in message):
                return []
            self.database._raise_schema_hint_if_needed(exc)
            raise

        results: list[dict[str, Any]] = []
        for row in rows:
            get = (lambda key: row[key]) if isinstance(row, dict) or hasattr(row, "keys") else None
            payload: dict[str, Any] = {}
            for index, column in enumerate(STORY_DB_COLUMNS):
                payload[column] = get(column) if get else row[index]
            results.append(payload)
        return results

    def upsert_task_records_to_table(
        self,
        workspace_id: str,
        task_rows: list[dict[str, Any]],
        *,
        updated_at: str,
        imported_at: str | None = None,
    ) -> tuple[int, int]:
        if not task_rows:
            return 0, 0

        created_count = 0
        updated_count = 0
        imported_at_value = imported_at or updated_at or datetime.utcnow().isoformat()
        task_codes = {
            str(row.get("task_code") or "").strip()
            for row in task_rows
            if str(row.get("task_code") or "").strip()
        }
        if not task_codes:
            return 0, 0

        select_existing_sql = (
            "SELECT task_code "
            f"FROM workspace_task_records WHERE workspace_id = {self.database.placeholder}"
        )

        insert_columns = ["workspace_id", *TASK_DB_COLUMNS, "imported_at", "updated_at"]
        if self.database.scheme == "sqlite":
            placeholders = ", ".join("?" for _ in insert_columns)
            update_columns = [column for column in TASK_DB_COLUMNS if column != "task_code"] + [
                "imported_at",
                "updated_at",
            ]
            update_clause = ", ".join(f"{column}=excluded.{column}" for column in update_columns)
            upsert_sql = (
                f"INSERT INTO workspace_task_records ({', '.join(insert_columns)}) "
                f"VALUES ({placeholders}) "
                "ON CONFLICT(workspace_id, task_code) DO UPDATE SET "
                f"{update_clause}"
            )
        else:
            placeholders = ", ".join("%s" for _ in insert_columns)
            update_columns = [column for column in TASK_DB_COLUMNS if column != "task_code"] + [
                "imported_at",
                "updated_at",
            ]
            update_clause = ", ".join(f"{column}=VALUES({column})" for column in update_columns)
            upsert_sql = (
                f"INSERT INTO workspace_task_records ({', '.join(insert_columns)}) "
                f"VALUES ({placeholders}) "
                f"ON DUPLICATE KEY UPDATE {update_clause}"
            )

        try:
            with self.database.connection() as connection:
                cursor = connection.cursor()
                cursor.execute(select_existing_sql, (workspace_id,))
                rows = cursor.fetchall() or []
                existing_codes = {
                    str((row["task_code"] if isinstance(row, dict) or hasattr(row, "keys") else row[0]) or "")
                    for row in rows
                }
                for task_row in task_rows:
                    task_code = str(task_row.get("task_code") or "").strip()
                    if not task_code:
                        continue
                    is_update = task_code in existing_codes
                    raw_values = [task_row.get(column) for column in TASK_DB_COLUMNS]
                    values = [
                        workspace_id,
                        *[json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v for v in raw_values],
                        imported_at_value,
                        updated_at,
                    ]
                    cursor.execute(upsert_sql, values)
                    if is_update:
                        updated_count += 1
                    else:
                        created_count += 1
        except Exception as exc:
            message = str(exc).lower()
            if "workspace_task_records" in message and ("doesn't exist" in message or "no such table" in message):
                raise RuntimeError(
                    f"任务表不存在，请先执行 DDL 创建 workspace_task_records"
                ) from exc
            raise

        return created_count, updated_count

    def load_task_records_by_workspace_id(
        self,
        workspace_id: str,
    ) -> list[dict[str, Any]]:
        """加载工作区全部任务记录，供推荐评分流程消费。"""
        select_columns = ", ".join(TASK_DB_COLUMNS)
        sql = f"SELECT {select_columns} FROM workspace_task_records WHERE workspace_id = {self.database.placeholder}"

        try:
            with self.database.connection() as connection:
                cursor = connection.cursor()
                cursor.execute(sql, [workspace_id])
                rows = cursor.fetchall() or []
        except Exception as exc:
            message = str(exc).lower()
            if "workspace_task_records" in message and ("doesn't exist" in message or "no such table" in message):
                return []
            self.database._raise_schema_hint_if_needed(exc)
            raise

        results: list[dict[str, Any]] = []
        for row in rows:
            get = (lambda key: row[key]) if isinstance(row, dict) or hasattr(row, "keys") else None
            payload: dict[str, Any] = {}
            for index, column in enumerate(TASK_DB_COLUMNS):
                value = get(column) if get else row[index]
                if column == "participants" and isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        pass
                payload[column] = value
            results.append(payload)
        return results

    def load_task_records_from_table(
        self,
        workspace_id: str,
        *,
        owner: str | None = None,
        status: str | None = None,
        project_name: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> tuple[list[dict[str, Any]], int] | list[dict[str, Any]]:
        select_columns = ", ".join(TASK_DB_COLUMNS)
        conditions = [f"workspace_id = {self.database.placeholder}"]
        params: list[Any] = [workspace_id]

        if owner:
            conditions.append(f"owner = {self.database.placeholder}")
            params.append(owner)
        if status:
            conditions.append(f"status = {self.database.placeholder}")
            params.append(status)
        if project_name:
            conditions.append(f"project_name = {self.database.placeholder}")
            params.append(project_name)

        where_clause = " AND ".join(conditions)

        use_pagination = page is not None and page_size is not None
        if use_pagination:
            count_sql = f"SELECT COUNT(*) FROM workspace_task_records WHERE {where_clause}"

        order_clause = " ORDER BY modified_time DESC, task_code"
        if use_pagination:
            if self.database.scheme == "sqlite":
                order_clause += " LIMIT ? OFFSET ?"
            else:
                order_clause += " LIMIT %s OFFSET %s"

        sql = f"SELECT {select_columns} FROM workspace_task_records WHERE {where_clause}{order_clause}"

        try:
            with self.database.connection() as connection:
                cursor = connection.cursor()
                if use_pagination:
                    offset = max(page - 1, 0) * page_size
                    cursor.execute(count_sql, params)
                    row = cursor.fetchone()
                    total = int(row[0] if isinstance(row, tuple) else row[0]) if row else 0

                    if total == 0:
                        return [], 0

                    cursor.execute(sql, params + [page_size, offset])
                else:
                    cursor.execute(sql, params)
                rows = cursor.fetchall() or []
        except Exception as exc:
            message = str(exc).lower()
            if "workspace_task_records" in message and ("doesn't exist" in message or "no such table" in message):
                if use_pagination:
                    return [], 0
                return []
            self.database._raise_schema_hint_if_needed(exc)
            raise

        results: list[dict[str, Any]] = []
        for row in rows:
            get = (lambda key: row[key]) if isinstance(row, dict) or hasattr(row, "keys") else None
            payload: dict[str, Any] = {}
            for index, column in enumerate(TASK_DB_COLUMNS):
                value = get(column) if get else row[index]
                if column == "participants" and isinstance(value, str):
                    try:
                        value = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        pass
                payload[column] = value
            results.append(payload)
        if use_pagination:
            return results, total
        return results

    def _sorted_members(self, members: list[MemberProfile]) -> list[MemberProfile]:
        return sorted(list(members), key=lambda item: item.name)

    def _normalize_session_ids(self, requirement_ids: list[str] | None) -> list[str]:
        normalized_ids: list[str] = []
        for item in requirement_ids or []:
            normalized = normalize_requirement_id(item)
            if normalized and normalized not in normalized_ids:
                normalized_ids.append(normalized)
        return normalized_ids

    def save_insight_snapshot(
        self,
        workspace_id: str,
        heatmap: list[dict[str, Any]],
        single_points: list[dict[str, Any]],
        growth_suggestions: list[dict[str, Any]],
        summary: dict[str, Any],
    ) -> None:
        snapshot_at = datetime.utcnow().isoformat()
        if self.database.scheme == "sqlite":
            insert_sql = (
                "INSERT INTO workspace_insight_snapshots ("
                "workspace_id, snapshot_at, heatmap_json, single_points_json, "
                "growth_suggestions_json, summary_json"
                ") VALUES (?, ?, ?, ?, ?, ?)"
            )
        else:
            insert_sql = (
                "INSERT INTO workspace_insight_snapshots ("
                "workspace_id, snapshot_at, heatmap_json, single_points_json, "
                "growth_suggestions_json, summary_json"
                ") VALUES (%s, %s, %s, %s, %s, %s)"
            )
        try:
            with self.database.connection() as connection:
                cursor = connection.cursor()
                cursor.execute(
                    insert_sql,
                    (
                        workspace_id,
                        snapshot_at,
                        json.dumps(heatmap, ensure_ascii=False, default=_json_default),
                        json.dumps(single_points, ensure_ascii=False, default=_json_default),
                        json.dumps(growth_suggestions, ensure_ascii=False, default=_json_default),
                        json.dumps(summary, ensure_ascii=False, default=_json_default),
                    ),
                )
        except Exception as exc:
            self.database._raise_schema_hint_if_needed(exc)
            raise

    def load_insight_history(self, workspace_id: str, limit: int = 20) -> list[dict[str, Any]]:
        ph = self.database.placeholder
        sql = (
            "SELECT id, snapshot_at, heatmap_json, single_points_json, "
            "growth_suggestions_json, summary_json "
            f"FROM workspace_insight_snapshots WHERE workspace_id = {ph} "
            "ORDER BY snapshot_at DESC LIMIT ?"
            if self.database.scheme == "sqlite"
            else (
                "SELECT id, snapshot_at, heatmap_json, single_points_json, "
                "growth_suggestions_json, summary_json "
                f"FROM workspace_insight_snapshots WHERE workspace_id = {ph} "
                "ORDER BY snapshot_at DESC LIMIT %s"
            )
        )
        try:
            with self.database.connection() as connection:
                cursor = connection.cursor()
                cursor.execute(sql, (workspace_id, limit))
                rows = cursor.fetchall() or []
        except Exception as exc:
            self.database._raise_schema_hint_if_needed(exc)
            raise
        results: list[dict[str, Any]] = []
        for row in rows:
            get = (lambda key: row[key]) if isinstance(row, dict) or hasattr(row, "keys") else None
            results.append(
                {
                    "id": int(get("id") if get else row[0]),
                    "snapshot_at": str(get("snapshot_at") if get else row[1]),
                    "heatmap": json.loads(get("heatmap_json") if get else row[2]),
                    "single_points": json.loads(get("single_points_json") if get else row[3]),
                    "growth_suggestions": json.loads(get("growth_suggestions_json") if get else row[4]),
                    "summary": json.loads(get("summary_json") if get else row[5]),
                }
            )
        return results
