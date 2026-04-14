from __future__ import annotations

import logging
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from .assignment import aggregate_task_history
from .insights import build_load_heatmap, compute_insight_summary, detect_single_points, suggest_growth_paths
from .intake import (
    detect_assignment_blockers,
    enrich_member_profiles,
    normalize_team_profiles,
    parse_chat_requirements,
    parse_imported_requirements,
)
from .knowledge_base import import_module_knowledge_from_excel, match_requirement_to_modules, merge_module_entries
from .models import MemberProfile, ModuleKnowledgeEntry, RequirementItem
from .story_excel_import import import_story_excel, row_to_story_record
from .task_excel_import import import_task_excel, row_to_task_record
from .utils import normalize_name, normalize_requirement_id, normalize_text, safe_float, split_names, unique_list
from .validators import validate_team_insights
from .workflows import ProjectManagerAgent
from .workspace_models import WorkspaceState
from .workspace_store import WorkspaceStore

ROLE_OPTIONS = {"developer", "tester", "qa", "test"}
FAMILIARITY_OPTIONS = {"不了解", "了解", "熟悉"}

logger = logging.getLogger(__name__)


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


class WorkspaceService:
    def __init__(
        self,
        store_root: str | Path = ".pm_agent_store",
        database_url: str | None = None,
        dashscope_api_key: str = "",
    ) -> None:
        self.agent = ProjectManagerAgent(
            store_root=store_root,
            database_url=database_url,
            dashscope_api_key=dashscope_api_key,
        )
        self.workspaces = WorkspaceStore(root=store_root, database_url=database_url)

    def get_workspace(self, workspace_id: str) -> dict[str, Any]:
        return self._build_workspace_payload(self._load_workspace(workspace_id))

    def update_draft(self, workspace_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        content_updated = any(key in payload for key in ("draft_mode", "message_text", "requirement_rows"))
        if "title" in payload:
            workspace.title = normalize_text(payload.get("title")) or workspace.workspace_id
        if "draft_mode" in payload:
            workspace.draft_mode = normalize_text(payload.get("draft_mode")) or "chat"
        if "message_text" in payload:
            workspace.message_text = str(payload.get("message_text") or "")
        if "requirement_rows" in payload:
            workspace.requirement_rows = list(payload.get("requirement_rows") or [])
        if content_updated:
            workspace.current_session_id = self._new_session_id()
            parsed_requirements = self._parse_requirements_from_workspace_draft(workspace)
            if parsed_requirements:
                workspace.normalized_requirements = self._merge_workspace_requirements(
                    workspace.normalized_requirements,
                    parsed_requirements,
                )
                self._set_current_session_requirement_ids(workspace, parsed_requirements)
            else:
                workspace.current_session_requirement_ids = []
        workspace.team_rows = []
        workspace.messages = ["草稿已保存"]
        workspace.updated_at = datetime.utcnow().isoformat()
        self.workspaces.save_workspace(workspace)
        return self._build_workspace_payload(workspace)

    def send_chat_message(self, workspace_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        logger.info("[chat] 收到请求 workspace_id=%s", workspace_id)
        workspace = self._load_workspace(workspace_id)
        user_message = normalize_text(payload.get("message"))
        if not user_message:
            raise ValueError("消息内容不能为空")
        if not workspace.current_session_id:
            workspace.current_session_id = self._new_session_id()

        # Append user message to history
        user_msg = {
            "role": "user",
            "content": user_message,
            "timestamp": datetime.utcnow().isoformat(),
        }
        workspace.chat_messages.append(user_msg)

        # Call LLM to parse
        logger.info("[chat] 构建成员画像 workspace_id=%s", workspace_id)
        profiles = self._build_managed_member_profiles(workspace)
        logger.info("[chat] 调用 LLM 解析需求 workspace_id=%s", workspace_id)
        # 加载任务历史用于 LLM 成员上下文
        task_records = self.workspaces.load_task_records_by_workspace_id(workspace_id)
        task_history = aggregate_task_history(task_records)
        requirements, reply = self.agent.parse_requirements_with_llm(user_message, profiles, task_history=task_history, task_records=task_records)
        logger.info("[chat] LLM 返回完成 workspace_id=%s 需求数=%d reply_len=%d", workspace_id, len(requirements), len(reply))

        # Append assistant reply
        assistant_msg = {
            "role": "assistant",
            "content": reply,
            "timestamp": datetime.utcnow().isoformat(),
            "parsed_requirements": [_jsonable(r) for r in requirements],
        }
        workspace.chat_messages.append(assistant_msg)

        for req in requirements:
            req.requirement_id = normalize_requirement_id(req.requirement_id) or req.requirement_id
        workspace.normalized_requirements = self._merge_workspace_requirements(
            workspace.normalized_requirements,
            requirements,
        )
        self._append_current_session_requirement_ids(workspace, requirements)
        logger.info("[chat] 合并需求完成 workspace_id=%s 累计=%d", workspace_id, len(workspace.normalized_requirements))

        # Sync modules to agent state for module matching
        self._sync_workspace_modules_to_agent(workspace)
        for req in requirements:
            match_requirement_to_modules(req, workspace.module_entries)
        logger.info("[chat] 模块匹配完成 workspace_id=%s", workspace_id)

        workspace.messages = [f"已解析 {len(requirements)} 条需求"]
        workspace.updated_at = datetime.utcnow().isoformat()
        logger.info("[chat] 保存工作区 workspace_id=%s", workspace_id)
        self.workspaces.save_workspace(workspace)
        return self._build_workspace_payload(workspace)

    def list_module_entries(self, workspace_id: str, query: Mapping[str, Any] | None = None) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        query_payload = self._module_query_payload(query)
        filtered_entries = [
            entry
            for entry in self._sorted_module_entries(workspace.module_entries)
            if self._match_module_entry(entry, query_payload)
        ]
        total = len(filtered_entries)
        total_pages = max(1, (total + query_payload["page_size"] - 1) // query_payload["page_size"])
        page = min(query_payload["page"], total_pages)
        offset = (page - 1) * query_payload["page_size"]
        paged_entries = filtered_entries[offset : offset + query_payload["page_size"]]
        return self._build_workspace_payload(
            workspace,
            module_entries=paged_entries,
            module_page={
                "page": page,
                "page_size": query_payload["page_size"],
                "total": total,
                "total_pages": total_pages,
                "filters": {
                    "big_module": query_payload["big_module"],
                    "function_module": query_payload["function_module"],
                    "primary_owner": query_payload["primary_owner"],
                },
            },
        )

    def create_module_entry(self, workspace_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        entry = self._module_entry_from_payload(workspace, payload)
        entries = self._module_entry_map(workspace)
        if entry.key in entries:
            raise ValueError(f"模块键已存在：{entry.key}")
        entries[entry.key] = entry
        workspace.module_entries = self._sorted_module_entries(entries.values())
        workspace.messages = [f"已新增模块 {entry.key}"]
        workspace.updated_at = datetime.utcnow().isoformat()
        self.workspaces.save_workspace(workspace)
        return self._build_workspace_payload(workspace)

    def update_module_entry(self, workspace_id: str, module_key: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        entries = self._module_entry_map(workspace)
        resolved_key = self._resolve_module_entry_key(entries, module_key, payload)
        existing = entries.get(resolved_key) if resolved_key else None
        if existing is None:
            raise ValueError("未找到要更新的模块条目")
        entry = self._module_entry_from_payload(workspace, payload, existing=existing)
        if entry.key != resolved_key and entry.key in entries:
            raise ValueError(f"模块键已存在：{entry.key}")
        entries.pop(resolved_key, None)
        entries[entry.key] = entry
        workspace.module_entries = self._sorted_module_entries(entries.values())
        workspace.messages = [f"已更新模块 {entry.key}"]
        workspace.updated_at = datetime.utcnow().isoformat()
        self.workspaces.save_workspace(workspace)
        return self._build_workspace_payload(workspace)

    def delete_module_entry(self, workspace_id: str, module_key: str) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        entries = self._module_entry_map(workspace)
        if module_key not in entries:
            raise ValueError("未找到要删除的模块条目")
        entries.pop(module_key)
        workspace.module_entries = self._sorted_module_entries(entries.values())
        workspace.messages = [f"已删除模块 {module_key}"]
        workspace.updated_at = datetime.utcnow().isoformat()
        self.workspaces.save_workspace(workspace)
        return self._build_workspace_payload(workspace)

    def list_managed_members(self, workspace_id: str) -> dict[str, Any]:
        return self._build_workspace_payload(self._load_workspace(workspace_id))

    def create_managed_member(self, workspace_id: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        member = self._member_profile_from_payload(payload)
        members = self._managed_member_map(workspace)
        normalized = normalize_name(member.name)
        if normalized in members:
            raise ValueError(f"成员已存在：{member.name}")
        members[normalized] = member
        workspace.managed_members = self._sorted_members(members.values())
        workspace.messages = [f"已新增成员 {member.name}"]
        workspace.updated_at = datetime.utcnow().isoformat()
        self.workspaces.save_workspace(workspace)
        return self._build_workspace_payload(workspace)

    def update_managed_member(self, workspace_id: str, member_name: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        members = self._managed_member_map(workspace)
        lookup_key = normalize_name(member_name)
        logger.info("[member.update] 更新成员 workspace_id=%s name=%r", workspace_id, member_name)
        existing = members.get(lookup_key)
        if existing is None:
            raise ValueError("未找到要更新的成员")
        member = self._member_profile_from_payload(payload)
        new_normalized = normalize_name(member.name)
        old_normalized = normalize_name(member_name)
        if new_normalized != old_normalized and new_normalized in members:
            raise ValueError(f"成员已存在：{member.name}")
        members.pop(old_normalized, None)
        members[new_normalized] = member
        workspace.managed_members = self._sorted_members(members.values())
        workspace.module_entries = self._rename_member_references(workspace.module_entries, existing.name, member.name)
        workspace.messages = [f"已更新成员 {member.name}"]
        workspace.updated_at = datetime.utcnow().isoformat()
        self.workspaces.save_workspace(workspace)
        return self._build_workspace_payload(workspace)

    def delete_managed_member(self, workspace_id: str, member_name: str) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        members = self._managed_member_map(workspace)
        existing = members.pop(normalize_name(member_name), None)
        if existing is None:
            raise ValueError("未找到要删除的成员")
        workspace.managed_members = self._sorted_members(members.values())
        workspace.module_entries = self._remove_member_references(workspace.module_entries, existing.name)
        workspace.messages = [f"已删除成员 {existing.name}"]
        workspace.updated_at = datetime.utcnow().isoformat()
        self.workspaces.save_workspace(workspace)
        return self._build_workspace_payload(workspace)

    def generate_recommendations(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        session_requirement_ids = self._normalized_session_ids(workspace.current_session_requirement_ids)
        if not session_requirement_ids:
            raise ValueError("当前会话没有可推荐需求，请先输入本轮需求")
        requirements, members = self._intake_workspace(workspace, session_requirement_ids=set(session_requirement_ids))
        self._sync_workspace_modules_to_agent(workspace)
        # 加载任务历史用于推荐评分
        task_records = self.workspaces.load_task_records_by_workspace_id(workspace_id)
        task_history = aggregate_task_history(task_records)
        recommendations = self.agent.recommend(requirements, members, task_history=task_history, task_records=task_records)
        workspace.normalized_requirements = self._merge_workspace_requirements(
            workspace.normalized_requirements,
            requirements,
        )
        workspace.member_profiles = members
        workspace.recommendations = recommendations
        workspace.messages = [f"已生成 {len(recommendations)} 条分配建议"]
        workspace.updated_at = datetime.utcnow().isoformat()
        self.workspaces.save_workspace(workspace)
        return self._build_workspace_payload(workspace)

    def delete_recommendation(self, workspace_id: str, requirement_id: str) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        normalized = normalize_requirement_id(requirement_id)
        if not normalized:
            raise ValueError("缺少要删除的推荐ID")
        before = len(workspace.recommendations)
        workspace.recommendations = [
            recommendation
            for recommendation in workspace.recommendations
            if normalize_requirement_id(recommendation.requirement_id) != normalized
        ]
        deleted_count = before - len(workspace.recommendations)
        if deleted_count <= 0:
            workspace.messages = [f"推荐 {normalized} 不存在或已删除"]
            return self._build_workspace_payload(workspace)
        workspace.messages = [f"已删除推荐 {normalized}"]
        workspace.updated_at = datetime.utcnow().isoformat()
        self.workspaces.save_workspace(workspace)
        return self._build_workspace_payload(workspace)

    def batch_delete_recommendations(
        self,
        workspace_id: str,
        requirement_ids: list[Any] | None = None,
    ) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        ids = []
        for item in requirement_ids or []:
            value = normalize_requirement_id(item)
            if value and value not in ids:
                ids.append(value)
        if not ids:
            raise ValueError("缺少要删除的推荐ID列表")
        ids_set = set(ids)
        before = len(workspace.recommendations)
        workspace.recommendations = [
            recommendation
            for recommendation in workspace.recommendations
            if normalize_requirement_id(recommendation.requirement_id) not in ids_set
        ]
        deleted_count = before - len(workspace.recommendations)
        workspace.messages = [f"已删除 {deleted_count} 条推荐"]
        workspace.updated_at = datetime.utcnow().isoformat()
        self.workspaces.save_workspace(workspace)
        return self._build_workspace_payload(workspace)

    def confirm_assignments(
        self,
        workspace_id: str,
        actions: Mapping[str, dict[str, object]] | None = None,
    ) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        if not workspace.recommendations:
            raise ValueError("当前工作区没有可确认的推荐结果")
        self._sync_workspace_modules_to_agent(workspace)
        session_id = workspace.current_session_id or self._new_session_id()
        confirmed = self.agent.confirm(workspace.recommendations, actions)
        workspace.module_entries = self._sorted_module_entries(self.agent.state.module_entries.values())
        workspace.confirmed_assignments = confirmed
        workspace.recommendations = []
        workspace.current_session_id = ""
        workspace.current_session_requirement_ids = []
        workspace.handoff_stories = []
        workspace.handoff_tasks = []
        workspace.messages = [f"已确认 {len(confirmed)} 条需求，已记录确认结果（未进入平台同步）"]
        workspace.updated_at = datetime.utcnow().isoformat()
        self.workspaces.append_confirmation_record(
            workspace_id=workspace.workspace_id,
            session_id=session_id,
            confirmed_assignments=confirmed,
            created_at=workspace.updated_at,
        )
        self.workspaces.save_workspace(workspace)
        return self._build_workspace_payload(workspace)

    def upload_module_knowledge(self, workspace_id: str, filename: str, content: bytes) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        upload = self.workspaces.save_upload(workspace_id, "module-knowledge", filename, content)
        imported_entries = import_module_knowledge_from_excel(upload.stored_path)
        if not workspace.managed_members:
            raise ValueError("请先在人员管理页面维护成员，再导入业务模块知识库")
        valid_names = self._managed_member_name_set(workspace)
        for entry in imported_entries:
            self._validate_module_entry_members(entry, valid_names)
        merged_entries = merge_module_entries(self._module_entry_map(workspace), imported_entries)
        workspace.module_entries = self._sorted_module_entries(merged_entries.values())
        workspace.uploads.append(upload)
        workspace.messages = [f"模块知识库导入完成，共 {len(imported_entries)} 条"]
        workspace.updated_at = datetime.utcnow().isoformat()
        self.workspaces.save_workspace(workspace)
        return self._build_workspace_payload(workspace)

    def sync_platform_files(
        self,
        workspace_id: str,
        story_file: tuple[str, bytes],
        task_file: tuple[str, bytes],
    ) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        story_upload = self.workspaces.save_upload(workspace_id, "story-export", story_file[0], story_file[1])
        task_upload = self.workspaces.save_upload(workspace_id, "task-export", task_file[0], task_file[1])
        batch = self.agent.sync_daily_exports(story_upload.stored_path, task_upload.stored_path)
        workspace.uploads.extend([story_upload, task_upload])
        workspace.latest_sync_batch = batch
        workspace.messages = [f"平台同步完成，批次 {batch.batch_id} 共 {len(batch.actions)} 个动作"]
        workspace.updated_at = datetime.utcnow().isoformat()
        self.workspaces.save_workspace(workspace)
        return self._build_workspace_payload(workspace)

    def upload_story_file(
        self,
        workspace_id: str,
        story_file: tuple[str, bytes],
    ) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        story_upload = self.workspaces.save_upload(workspace_id, "story-export-only", story_file[0], story_file[1])
        parsed = import_story_excel(story_upload.stored_path)
        created_count, updated_count = self.workspaces.upsert_story_records_to_table(
            workspace_id=workspace_id,
            story_rows=parsed.valid_rows,
            updated_at=datetime.utcnow().isoformat(),
        )
        table_rows = self.workspaces.load_story_records_from_table(workspace_id)
        workspace.handoff_stories = [row_to_story_record(item) for item in table_rows]
        workspace.uploads.append(story_upload)
        failed_count = len(parsed.errors)
        summary = {
            "total": parsed.total_rows,
            "created": created_count,
            "updated": updated_count,
            "failed": failed_count,
            "errors": [{"row": item.row, "reason": item.reason} for item in parsed.errors],
            "missing_headers": parsed.missing_headers,
            "unknown_headers": parsed.unknown_headers,
        }
        workspace.latest_story_import = summary
        workspace.messages = [
            f"故事导入完成，总计 {parsed.total_rows} 行，新增 {created_count}，更新 {updated_count}，失败 {failed_count}"
        ]
        workspace.updated_at = datetime.utcnow().isoformat()
        self.workspaces.save_workspace(workspace)
        return self._build_workspace_payload(workspace)

    def upload_task_file(
        self,
        workspace_id: str,
        task_file: tuple[str, bytes],
    ) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        task_upload = self.workspaces.save_upload(workspace_id, "task-export-only", task_file[0], task_file[1])
        parsed = import_task_excel(task_upload.stored_path)
        created_count, updated_count = self.workspaces.upsert_task_records_to_table(
            workspace_id=workspace_id,
            task_rows=parsed.valid_rows,
            updated_at=datetime.utcnow().isoformat(),
        )
        workspace.uploads.append(task_upload)
        failed_count = len(parsed.errors)
        summary = {
            "total": parsed.total_rows,
            "created": created_count,
            "updated": updated_count,
            "failed": failed_count,
            "errors": [{"row": item.row, "reason": item.reason} for item in parsed.errors],
            "missing_headers": parsed.missing_headers,
            "unknown_headers": parsed.unknown_headers,
        }
        workspace.latest_task_import = summary
        workspace.messages = [
            f"任务导入完成，总计 {parsed.total_rows} 行，新增 {created_count}，更新 {updated_count}，失败 {failed_count}"
        ]
        workspace.updated_at = datetime.utcnow().isoformat()
        self.workspaces.save_workspace(workspace)
        return self._build_workspace_payload(workspace)

    def get_tasks(
        self,
        workspace_id: str,
        query: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        query = query or {}
        owner = normalize_text(query.get("owner")) or None
        status = normalize_text(query.get("status")) or None
        project_name = normalize_text(query.get("project_name")) or None

        table_rows = self.workspaces.load_task_records_from_table(
            workspace_id,
            owner=owner,
            status=status,
            project_name=project_name,
        )
        tasks = [row_to_task_record(item) for item in table_rows]
        return {
            "workspace_id": workspace_id,
            "tasks": _jsonable(tasks),
            "total": len(tasks),
        }

    def get_monitoring(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        return {
            "workspace_id": workspace.workspace_id,
            "alerts": _jsonable(self.agent.monitor_execution()),
            "latest_sync_batch": _jsonable(workspace.latest_sync_batch),
        }

    def get_insights(self, workspace_id: str) -> dict[str, Any]:
        workspace = self._load_workspace(workspace_id)
        self._sync_workspace_modules_to_agent(workspace)
        profiles = self._build_managed_member_profiles(workspace)
        heatmap = build_load_heatmap(self.agent.state, profiles)
        single_points = detect_single_points(self.agent.state)
        growth = suggest_growth_paths(self.agent.state, profiles)
        validate_team_insights(heatmap, growth)
        summary = compute_insight_summary(heatmap, single_points, growth)
        self.workspaces.save_insight_snapshot(
            workspace_id,
            _jsonable(heatmap),
            _jsonable(single_points),
            _jsonable(growth),
            summary,
        )
        return {
            "workspace_id": workspace.workspace_id,
            "insights": _jsonable(
                {
                    "heatmap": heatmap,
                    "single_points": single_points,
                    "growth_suggestions": growth,
                }
            ),
            "summary": summary,
        }

    def get_insight_history(self, workspace_id: str, limit: int = 20) -> dict[str, Any]:
        history = self.workspaces.load_insight_history(workspace_id, limit=limit)
        return {
            "workspace_id": workspace_id,
            "history": history,
        }

    def list_confirmation_records(
        self,
        workspace_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        items, total = self.workspaces.load_confirmation_records(workspace_id, page, page_size)
        total_pages = max(1, (total + page_size - 1) // page_size)
        return {
            "workspace_id": workspace_id,
            "items": _jsonable(items),
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        }

    def _load_workspace(self, workspace_id: str) -> WorkspaceState:
        workspace = self.workspaces.load_workspace(workspace_id)
        changed = False
        if not workspace.module_entries and self.agent.state.module_entries:
            workspace.module_entries = self._sorted_module_entries(self.agent.state.module_entries.values())
            changed = True
        if not workspace.managed_members:
            if workspace.team_rows:
                workspace.managed_members = self._sorted_members(normalize_team_profiles(workspace.team_rows))
                workspace.team_rows = []
                changed = True
            elif workspace.member_profiles:
                workspace.managed_members = self._sorted_members(workspace.member_profiles)
                changed = True
        if workspace.team_rows:
            workspace.team_rows = []
            changed = True
        if changed:
            workspace.updated_at = datetime.utcnow().isoformat()
            self.workspaces.save_workspace(workspace)
        return workspace

    def _intake_workspace(
        self,
        workspace: WorkspaceState,
        session_requirement_ids: set[str] | None = None,
    ) -> tuple[list[Any], list[MemberProfile]]:
        if workspace.normalized_requirements:
            requirements = list(workspace.normalized_requirements)
        elif workspace.message_text.strip() and workspace.draft_mode != "structured":
            requirements = parse_chat_requirements(workspace.message_text)
        elif workspace.requirement_rows:
            requirements = parse_imported_requirements(workspace.requirement_rows)
        elif workspace.message_text.strip():
            requirements = parse_chat_requirements(workspace.message_text)
        else:
            raise ValueError("工作区缺少需求输入，请先录入群消息或导入需求数据")
        for requirement in requirements:
            requirement.requirement_id = normalize_requirement_id(requirement.requirement_id) or requirement.requirement_id
        if session_requirement_ids is not None:
            normalized_session_ids = {normalize_requirement_id(item) for item in session_requirement_ids if normalize_requirement_id(item)}
            requirements = [
                requirement
                for requirement in requirements
                if normalize_requirement_id(requirement.requirement_id) in normalized_session_ids
            ]
            if not requirements:
                raise ValueError("当前会话没有可推荐需求，请先输入本轮需求")
        profiles = self._build_managed_member_profiles(workspace)
        detect_assignment_blockers(requirements, profiles)
        for requirement in requirements:
            match_requirement_to_modules(requirement, workspace.module_entries)
        return requirements, profiles

    def _parse_requirements_from_workspace_draft(self, workspace: WorkspaceState) -> list[RequirementItem]:
        if workspace.requirement_rows:
            return parse_imported_requirements(workspace.requirement_rows)
        if workspace.message_text.strip():
            return parse_chat_requirements(workspace.message_text)
        return []

    def _new_session_id(self) -> str:
        return f"session-{uuid4().hex[:12]}"

    def _normalized_session_ids(self, requirement_ids: list[Any] | None) -> list[str]:
        normalized_ids: list[str] = []
        for item in requirement_ids or []:
            normalized = normalize_requirement_id(item)
            if normalized and normalized not in normalized_ids:
                normalized_ids.append(normalized)
        return normalized_ids

    def _set_current_session_requirement_ids(
        self,
        workspace: WorkspaceState,
        requirements: list[RequirementItem],
    ) -> None:
        workspace.current_session_requirement_ids = self._normalized_session_ids(
            [requirement.requirement_id for requirement in requirements]
        )

    def _append_current_session_requirement_ids(
        self,
        workspace: WorkspaceState,
        requirements: list[RequirementItem],
    ) -> None:
        current_ids = self._normalized_session_ids(workspace.current_session_requirement_ids)
        for requirement in requirements:
            normalized = normalize_requirement_id(requirement.requirement_id)
            if normalized and normalized not in current_ids:
                current_ids.append(normalized)
        workspace.current_session_requirement_ids = current_ids

    def _merge_workspace_requirements(
        self,
        current_requirements: list[RequirementItem],
        new_requirements: list[RequirementItem],
    ) -> list[RequirementItem]:
        merged: list[RequirementItem] = []
        index_by_id: dict[str, int] = {}
        for requirement in current_requirements:
            normalized = normalize_requirement_id(requirement.requirement_id)
            if not normalized:
                continue
            requirement.requirement_id = normalized
            if normalized in index_by_id:
                merged[index_by_id[normalized]] = requirement
            else:
                index_by_id[normalized] = len(merged)
                merged.append(requirement)
        for requirement in new_requirements:
            normalized = normalize_requirement_id(requirement.requirement_id)
            if not normalized:
                continue
            requirement.requirement_id = normalized
            existing_index = index_by_id.get(normalized)
            if existing_index is None:
                index_by_id[normalized] = len(merged)
                merged.append(requirement)
            else:
                merged[existing_index] = requirement
        return merged

    def _build_managed_member_profiles(self, workspace: WorkspaceState) -> list[MemberProfile]:
        if not workspace.managed_members:
            raise ValueError("当前工作区缺少成员，请先在人员管理页面维护团队成员")
        return enrich_member_profiles(workspace.managed_members, workspace.module_entries)

    def _sync_workspace_modules_to_agent(self, workspace: WorkspaceState) -> None:
        self.agent.state.module_entries = self._module_entry_map(workspace)

    def _module_entry_map(self, workspace: WorkspaceState) -> dict[str, ModuleKnowledgeEntry]:
        return {entry.key: entry for entry in workspace.module_entries}

    def _managed_member_map(self, workspace: WorkspaceState) -> dict[str, MemberProfile]:
        return {normalize_name(member.name): member for member in workspace.managed_members}

    def _managed_member_name_set(self, workspace: WorkspaceState) -> set[str]:
        return {normalize_name(member.name) for member in workspace.managed_members}

    def _validate_module_entry_members(self, entry: ModuleKnowledgeEntry, valid_names: set[str]) -> None:
        if normalize_name(entry.primary_owner) not in valid_names:
            raise ValueError(f"主要负责人未在人员管理中维护：{entry.primary_owner}")
        for backup_owner in entry.backup_owners:
            if normalize_name(backup_owner) not in valid_names:
                raise ValueError(f"B角未在人员管理中维护：{backup_owner}")
        for member_name, level in entry.familiarity_by_member.items():
            if normalize_name(member_name) not in valid_names:
                raise ValueError(f"模块熟悉度中存在未维护的成员：{member_name}")
            if level not in FAMILIARITY_OPTIONS:
                raise ValueError(f"不支持的熟悉度等级：{level}")

    def _module_entry_from_payload(
        self,
        workspace: WorkspaceState,
        payload: Mapping[str, Any],
        existing: ModuleKnowledgeEntry | None = None,
    ) -> ModuleKnowledgeEntry:
        big_module = normalize_text(payload.get("big_module"))
        function_module = normalize_text(payload.get("function_module"))
        primary_owner = normalize_text(payload.get("primary_owner"))
        backup_owners = self._normalize_name_list(payload.get("backup_owners"))
        if not backup_owners and payload.get("backup_owner"):
            backup_owners = self._normalize_name_list(payload.get("backup_owner"))
        if not big_module:
            raise ValueError("大模块不能为空")
        if not function_module:
            raise ValueError("功能模块不能为空")
        if not primary_owner:
            raise ValueError("主要负责人不能为空")
        if not workspace.managed_members:
            raise ValueError("请先在人员管理页面维护成员，再维护业务模块")
        familiar_members, aware_members, unfamiliar_members = self._normalize_familiarity_groups(payload)
        self._validate_module_entry_members(
            ModuleKnowledgeEntry(
                key=f"{big_module}::{function_module}",
                big_module=big_module,
                function_module=function_module,
                primary_owner=primary_owner,
                backup_owners=backup_owners,
                familiar_members=familiar_members,
                aware_members=aware_members,
                unfamiliar_members=unfamiliar_members,
            ),
            self._managed_member_name_set(workspace),
        )
        key = f"{big_module}::{function_module}"
        imported_at = existing.imported_at if existing else datetime.utcnow().isoformat()
        source_sheet = normalize_text(payload.get("source_sheet")) or (existing.source_sheet if existing else "manual")
        source_year = int(payload.get("source_year") or (existing.source_year if existing else datetime.utcnow().year))
        return ModuleKnowledgeEntry(
            key=key,
            big_module=big_module,
            function_module=function_module,
            primary_owner=primary_owner,
            backup_owners=backup_owners,
            familiar_members=familiar_members,
            aware_members=aware_members,
            unfamiliar_members=unfamiliar_members,
            source_sheet=source_sheet,
            source_year=source_year,
            imported_at=imported_at,
            recent_assignees=list(existing.recent_assignees) if existing else [],
            suggested_familiarity=dict(existing.suggested_familiarity) if existing else {},
            assignment_history=list(existing.assignment_history) if existing else [],
        )

    def _member_profile_from_payload(self, payload: Mapping[str, Any]) -> MemberProfile:
        name = normalize_text(payload.get("name"))
        role = normalize_text(payload.get("role")) or "developer"
        if not name:
            raise ValueError("成员姓名不能为空")
        if role not in ROLE_OPTIONS:
            raise ValueError(f"不支持的成员角色：{role}")
        workload = safe_float(payload.get("workload"))
        capacity = safe_float(payload.get("capacity"), default=1.0)
        if workload < 0:
            raise ValueError("成员负载不能为负数")
        if capacity <= 0:
            raise ValueError("成员容量必须大于 0")
        raw_skills = payload.get("skills")
        raw_constraints = payload.get("constraints")
        return MemberProfile(
            name=name,
            role=role,
            skills=unique_list(raw_skills if isinstance(raw_skills, list) else split_names(raw_skills)),
            experience_level=normalize_text(payload.get("experience_level") or payload.get("experience")) or "中",
            workload=workload,
            capacity=capacity,
            constraints=unique_list(
                raw_constraints if isinstance(raw_constraints, list) else split_names(raw_constraints)
            ),
        )

    def _normalize_familiarity_map(self, payload: Mapping[str, Any]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for key, value in dict(payload).items():
            member_name = normalize_text(key)
            level = normalize_text(value)
            if not member_name or not level:
                continue
            if level == "一般":
                level = "了解"
            if level not in FAMILIARITY_OPTIONS:
                continue
            normalized[member_name] = level
        return normalized

    def _normalize_name_list(self, values: Any) -> list[str]:
        if values is None:
            return []
        if isinstance(values, list):
            raw_values = values
        else:
            raw_values = split_names(values)
        normalized: list[str] = []
        for item in raw_values:
            name = normalize_text(item)
            if name and name not in normalized:
                normalized.append(name)
        return normalized

    def _normalize_familiarity_groups(self, payload: Mapping[str, Any]) -> tuple[list[str], list[str], list[str]]:
        level_map: dict[str, str] = {}

        for member in self._normalize_name_list(payload.get("unfamiliar_members")):
            level_map[member] = "不了解"
        for member in self._normalize_name_list(payload.get("aware_members")):
            level_map[member] = "了解"
        for member in self._normalize_name_list(payload.get("familiar_members")):
            level_map[member] = "熟悉"

        for member, level in self._normalize_familiarity_map(payload.get("familiarity_by_member") or {}).items():
            level_map[member] = level

        familiar_members = [member for member, level in level_map.items() if level == "熟悉"]
        aware_members = [member for member, level in level_map.items() if level == "了解"]
        unfamiliar_members = [member for member, level in level_map.items() if level == "不了解"]
        return familiar_members, aware_members, unfamiliar_members

    def _module_query_payload(self, query: Mapping[str, Any] | None) -> dict[str, Any]:
        query = dict(query or {})
        page = int(query.get("page") or 1)
        page_size = int(query.get("page_size") or 50)
        return {
            "page": max(page, 1),
            "page_size": max(min(page_size, 500), 1),
            "big_module": normalize_text(query.get("big_module")),
            "function_module": normalize_text(query.get("function_module")),
            "primary_owner": normalize_text(query.get("primary_owner")),
        }

    def _contains_fuzzy(self, source: str, keyword: str) -> bool:
        return not keyword or keyword.lower() in normalize_text(source).lower()

    def _match_module_entry(self, entry: ModuleKnowledgeEntry, query: Mapping[str, Any]) -> bool:
        return (
            self._contains_fuzzy(entry.big_module, str(query.get("big_module") or ""))
            and self._contains_fuzzy(entry.function_module, str(query.get("function_module") or ""))
            and self._contains_fuzzy(entry.primary_owner, str(query.get("primary_owner") or ""))
        )

    def _resolve_module_entry_key(
        self,
        entries: Mapping[str, ModuleKnowledgeEntry],
        module_key: str,
        payload: Mapping[str, Any] | None = None,
    ) -> str | None:
        payload = payload or {}
        candidates: list[str] = []

        direct_key = normalize_text(module_key)
        if direct_key:
            candidates.append(direct_key)

        for field in ("original_key", "module_key", "key"):
            field_key = normalize_text(payload.get(field))
            if field_key:
                candidates.append(field_key)

        payload_big_module = normalize_text(payload.get("big_module"))
        payload_function_module = normalize_text(payload.get("function_module"))
        if payload_big_module and payload_function_module:
            candidates.append(f"{payload_big_module}::{payload_function_module}")

        seen: set[str] = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            if candidate in entries:
                return candidate
        return None

    def _rename_member_references(
        self,
        entries: list[ModuleKnowledgeEntry],
        old_name: str,
        new_name: str,
    ) -> list[ModuleKnowledgeEntry]:
        renamed: list[ModuleKnowledgeEntry] = []
        old_normalized = normalize_name(old_name)
        for entry in entries:
            familiarity = {}
            for member_name, level in entry.familiarity_by_member.items():
                familiarity[new_name if normalize_name(member_name) == old_normalized else member_name] = level
            suggested = {}
            for member_name, level in entry.suggested_familiarity.items():
                suggested[new_name if normalize_name(member_name) == old_normalized else member_name] = level
            recent = [new_name if normalize_name(name) == old_normalized else name for name in entry.recent_assignees]
            entry.primary_owner = new_name if normalize_name(entry.primary_owner) == old_normalized else entry.primary_owner
            entry.backup_owners = [
                new_name if normalize_name(owner) == old_normalized else owner
                for owner in entry.backup_owners
            ]
            entry.familiarity_by_member = familiarity
            entry.suggested_familiarity = suggested
            entry.recent_assignees = recent
            renamed.append(entry)
        return self._sorted_module_entries(renamed)

    def _remove_member_references(
        self,
        entries: list[ModuleKnowledgeEntry],
        member_name: str,
    ) -> list[ModuleKnowledgeEntry]:
        target = normalize_name(member_name)
        updated: list[ModuleKnowledgeEntry] = []
        for entry in entries:
            entry.familiarity_by_member = {
                key: value for key, value in entry.familiarity_by_member.items() if normalize_name(key) != target
            }
            entry.suggested_familiarity = {
                key: value for key, value in entry.suggested_familiarity.items() if normalize_name(key) != target
            }
            entry.recent_assignees = [name for name in entry.recent_assignees if normalize_name(name) != target]
            entry.backup_owners = [name for name in entry.backup_owners if normalize_name(name) != target]
            if normalize_name(entry.primary_owner) == target:
                entry.primary_owner = ""
            updated.append(entry)
        return self._sorted_module_entries(updated)

    def _sorted_module_entries(self, entries: Any) -> list[ModuleKnowledgeEntry]:
        return sorted(list(entries), key=lambda item: (item.big_module, item.function_module, item.key))

    def _sorted_members(self, members: Any) -> list[MemberProfile]:
        return sorted(list(members), key=lambda item: item.name)

    def _knowledge_base_summary(self, workspace: WorkspaceState) -> dict[str, Any]:
        entries = list(workspace.module_entries)
        return {
            "entry_count": len(entries),
            "sample_keys": [entry.key for entry in entries[:5]],
        }

    def _build_workspace_payload(
        self,
        workspace: WorkspaceState,
        module_entries: list[ModuleKnowledgeEntry] | None = None,
        module_page: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload_entries = module_entries if module_entries is not None else workspace.module_entries
        table_story_rows = self.workspaces.load_story_records_from_table(workspace.workspace_id)
        handoff_stories = [row_to_story_record(item) for item in table_story_rows] if table_story_rows else workspace.handoff_stories
        payload_module_page = dict(module_page or {})
        if "total" not in payload_module_page:
            payload_module_page = {
                "page": 1,
                "page_size": len(payload_entries) if payload_entries else 50,
                "total": len(payload_entries),
                "total_pages": 1,
                "filters": {"big_module": "", "function_module": "", "primary_owner": ""},
            }
        return {
            "workspace_id": workspace.workspace_id,
            "title": workspace.title or workspace.workspace_id,
            "updated_at": workspace.updated_at,
            "draft": {
                "draft_mode": workspace.draft_mode,
                "message_text": workspace.message_text,
                "requirement_rows": workspace.requirement_rows,
                "team_rows": [],
                "chat_messages": workspace.chat_messages,
                "current_session_id": workspace.current_session_id,
                "current_session_requirement_ids": workspace.current_session_requirement_ids,
            },
            "requirements": _jsonable(workspace.normalized_requirements),
            "members": _jsonable(workspace.member_profiles),
            "managed_members": _jsonable(workspace.managed_members),
            "module_entries": _jsonable(payload_entries),
            "module_page": payload_module_page,
            "recommendations": _jsonable(workspace.recommendations),
            "confirmed_assignments": _jsonable(workspace.confirmed_assignments),
            "handoff": {
                "stories": _jsonable(handoff_stories),
                "tasks": _jsonable(workspace.handoff_tasks),
            },
            "latest_sync_batch": _jsonable(workspace.latest_sync_batch),
            "latest_story_import": _jsonable(workspace.latest_story_import),
            "latest_task_import": _jsonable(workspace.latest_task_import),
            "uploads": _jsonable(workspace.uploads),
            "messages": list(workspace.messages),
            "knowledge_base_summary": self._knowledge_base_summary(workspace),
            "group_reply_preview": (
                self.agent.render_group_reply(workspace.recommendations)
                if workspace.recommendations
                else ""
            ),
        }
