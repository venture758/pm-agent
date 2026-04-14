from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping, Optional
from uuid import uuid4

from .agent_prompt import (
    KNOWLEDGE_UPDATE_PROMPT,
    SYSTEM_PROMPT,
    build_assignment_history,
    build_member_context,
    build_module_context,
    build_module_knowledge_summary,
)
from .assignment import build_story_and_task_handoff, confirm_assignments, recommend_assignments, render_group_reply
from .config import WORKFLOW_CONFIGS
from .insights import build_load_heatmap, detect_single_points, suggest_growth_paths
from .intake import (
    build_profiles_from_module_entries,
    detect_assignment_blockers,
    normalize_team_profiles,
    parse_chat_requirements,
    parse_imported_requirements,
)
from .knowledge_base import (
    import_module_knowledge_from_excel,
    match_requirement_to_modules,
    merge_module_entries,
    update_module_knowledge_after_assignment,
)
from .llm_client import LlmClient
from .assignment import aggregate_workload_from_tasks, recommend_assignments
from .llm_client import LlmClient
from .models import AgentState, AssignmentRecommendation, ConfirmedAssignment, MemberProfile, RequirementItem
from .monitoring import generate_execution_alerts
from .platform_sync import sync_platform_exports
from .storage import LocalStateStore
from .utils import normalize_name, normalize_requirement_id
from .validators import (
    validate_confirmed_assignments,
    validate_import_batch,
    validate_recommendations,
    validate_team_insights,
)

logger = logging.getLogger(__name__)


class ProjectManagerAgent:
    def __init__(
        self,
        store_root: str | Path = ".pm_agent_store",
        database_url: str | None = None,
        dashscope_api_key: str = "",
    ) -> None:
        self.store = LocalStateStore(root=store_root, database_url=database_url)
        self.state: AgentState = self.store.load_state()
        self.workflow_configs = WORKFLOW_CONFIGS
        self._llm: LlmClient | None = None
        if dashscope_api_key:
            self._llm = LlmClient(api_key=dashscope_api_key)

    @property
    def llm_available(self) -> bool:
        return self._llm is not None

    def save(self) -> None:
        self.store.save_state(self.state)

    def sync_module_knowledge_base(self, excel_path: str | Path):
        imported_entries = import_module_knowledge_from_excel(excel_path)
        self.state.module_entries = merge_module_entries(self.state.module_entries, imported_entries)
        self.save()
        return list(self.state.module_entries.values())

    def build_member_profiles(self, team_rows: Optional[Iterable[Mapping[str, object]]] = None) -> list[MemberProfile]:
        if team_rows:
            explicit_profiles = normalize_team_profiles(team_rows)
        else:
            explicit_profiles = []
        profiles = build_profiles_from_module_entries(self.state.module_entries.values(), overrides=team_rows)
        if explicit_profiles:
            profiles_by_name = {profile.name: profile for profile in profiles}
            for profile in explicit_profiles:
                profiles_by_name[profile.name] = profile
            return list(profiles_by_name.values())
        return profiles

    def intake_requirements_from_chat(
        self,
        message_text: str,
        team_rows: Optional[Iterable[Mapping[str, object]]] = None,
    ) -> tuple[list[RequirementItem], list[MemberProfile]]:
        requirements = parse_chat_requirements(message_text)
        profiles = self.build_member_profiles(team_rows)
        detect_assignment_blockers(requirements, profiles)
        for requirement in requirements:
            match_requirement_to_modules(requirement, self.state.module_entries.values())
        return requirements, profiles

    def intake_requirements_from_import(
        self,
        rows: Iterable[Mapping[str, object]],
        team_rows: Optional[Iterable[Mapping[str, object]]] = None,
    ) -> tuple[list[RequirementItem], list[MemberProfile]]:
        requirements = parse_imported_requirements(rows)
        profiles = self.build_member_profiles(team_rows)
        detect_assignment_blockers(requirements, profiles)
        for requirement in requirements:
            match_requirement_to_modules(requirement, self.state.module_entries.values())
        return requirements, profiles

    def recommend(
        self,
        requirements: list[RequirementItem],
        members: Optional[list[MemberProfile]] = None,
        task_history: Optional[Mapping[str, object]] = None,
        task_records: Optional[list[dict[str, object]]] = None,
    ) -> list[AssignmentRecommendation]:
        profiles = members or self.build_member_profiles()
        recommendations = recommend_assignments(requirements, profiles, self.state.module_entries, task_history=task_history, task_records=task_records)
        validate_recommendations(recommendations)
        return recommendations

    def render_group_reply(self, recommendations: list[AssignmentRecommendation]) -> str:
        return render_group_reply(recommendations)

    def confirm(
        self,
        recommendations: list[AssignmentRecommendation],
        actions: Optional[Mapping[str, dict[str, object]]] = None,
    ) -> list[ConfirmedAssignment]:
        confirmed = confirm_assignments(recommendations, actions)
        validate_confirmed_assignments(confirmed)
        for assignment in confirmed:
            self.state.confirmed_assignments[assignment.requirement_id] = assignment
        self.state.module_entries = update_module_knowledge_after_assignment(self.state.module_entries, confirmed)
        self.save()
        return confirmed

    def generate_platform_handoff(self, confirmed_assignments: list[ConfirmedAssignment]):
        stories, tasks = build_story_and_task_handoff(confirmed_assignments)
        for story in stories:
            self.state.stories[story.user_story_code] = story
        for task in tasks:
            self.state.tasks[task.task_code] = task
        self.save()
        return stories, tasks

    def sync_daily_exports(self, story_excel_path: str | Path, task_excel_path: str | Path):
        batch = sync_platform_exports(self.state, story_excel_path, task_excel_path)
        validate_import_batch(batch)
        self.save()
        return batch

    def monitor_execution(self, today: Optional[date] = None):
        return generate_execution_alerts(self.state, today=today)

    def generate_team_insights(
        self,
        team_rows: Optional[Iterable[Mapping[str, object]]] = None,
    ) -> dict[str, object]:
        profiles = self.build_member_profiles(team_rows)
        heatmap = build_load_heatmap(self.state, profiles)
        single_points = detect_single_points(self.state)
        growth = suggest_growth_paths(self.state, profiles)
        validate_team_insights(heatmap, growth)
        return {
            "heatmap": heatmap,
            "single_points": single_points,
            "growth_suggestions": growth,
        }

    # ---------- LLM-backed chat methods ----------

    def parse_requirements_with_llm(
        self,
        user_message: str,
        members: Optional[list[MemberProfile]] = None,
        task_history: Optional[Mapping[str, object]] = None,
        task_records: Optional[list[dict[str, object]]] = None,
    ) -> tuple[list[RequirementItem], str]:
        """需求理解 Agent：调用 LLM 解析用户消息，返回 RequirementItem 列表和自然语言回复。"""
        if not self._llm:
            raise RuntimeError("LLM 未配置：请设置 --nvidia-api-key 或 NVIDIA_NIM_API_KEY")

        profiles = members or self.build_member_profiles()

        # Apply auto-workload to profiles before building LLM context
        auto_workloads = aggregate_workload_from_tasks(task_records or [], profiles) if task_records else None
        if auto_workloads is not None:
            profiles = [
                MemberProfile(
                    name=m.name,
                    role=m.role,
                    skills=list(m.skills),
                    experience_level=m.experience_level,
                    workload=auto_workloads.get(m.name, auto_workloads.get(normalize_name(m.name), m.workload)),
                    capacity=m.capacity,
                    constraints=list(m.constraints),
                    module_familiarity=dict(m.module_familiarity),
                )
                for m in profiles
            ]

        logger.info("[chat.llm] 构建上下文 member_count=%d module_count=%d", len(profiles), len(self.state.module_entries))
        module_context = build_module_context(self.state.module_entries.values())
        member_context = build_member_context(profiles, task_history=task_history)
        system_prompt = SYSTEM_PROMPT.format(
            module_context=module_context,
            member_context=member_context,
        )

        logger.info("[chat.llm] 发起 LLM 请求 prompt_len=%d user_msg_len=%d", len(system_prompt), len(user_message))
        response_text = self._llm.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]
        )
        logger.info("[chat.llm] LLM 返回 response_len=%d", len(response_text))

        parsed = self._llm.parse_json_response(response_text)
        requirements: list[RequirementItem] = []
        for idx, req_data in enumerate(parsed.get("requirements", []), 1):
            matched_keys = [m.get("key", "") for m in req_data.get("matched_modules", [])]
            requirement = RequirementItem(
                requirement_id=normalize_requirement_id(req_data.get("requirement_id")) or f"LLM-{uuid4().hex[:10]}-{idx}",
                title=req_data.get("title", ""),
                priority=req_data.get("priority", "中"),
                requirement_type=req_data.get("requirement_type", ""),
                complexity=req_data.get("complexity", "中"),
                risk=req_data.get("risk", "中"),
                skills=req_data.get("skills", []),
                dependency_hints=req_data.get("dependency_hints", []),
                blockers=req_data.get("blockers", []),
                split_suggestion=req_data.get("split_suggestion") or None,
                analysis_factors=req_data.get("analysis_factors", []),
                matched_module_keys=matched_keys,
                source="llm_chat",
                source_message=user_message,
                raw_text=user_message,
            )
            requirements.append(requirement)

        logger.info("[chat.llm] 解析需求 %d 条", len(requirements))
        detect_assignment_blockers(requirements, profiles)
        for requirement in requirements:
            match_requirement_to_modules(requirement, self.state.module_entries.values())

        reply = parsed.get("reply", "已解析需求")
        return requirements, reply

    def generate_knowledge_update_suggestions(self) -> dict[str, object]:
        """知识更新 Agent：调用 LLM 分析历史分配数据，给出优化建议。"""
        if not self._llm:
            return {"knowledge_updates": {}, "optimization_suggestions": [], "reply": "LLM 未配置"}

        module_summary = build_module_knowledge_summary(self.state.module_entries.values())
        history = build_assignment_history(self.state.confirmed_assignments.values())

        response_text = self._llm.chat_completion(
            messages=[
                {"role": "system", "content": KNOWLEDGE_UPDATE_PROMPT},
                {"role": "user", "content": f"模块知识库:\n{module_summary}\n\n分配历史:\n{history}"},
            ]
        )

        try:
            parsed = self._llm.parse_json_response(response_text)
        except ValueError:
            return {"knowledge_updates": {}, "optimization_suggestions": [], "reply": response_text[:200]}

        return {
            "knowledge_updates": parsed.get("knowledge_updates", {}),
            "optimization_suggestions": parsed.get("optimization_suggestions", []),
            "reply": parsed.get("reply", ""),
        }
