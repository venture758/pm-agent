from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from ..llm_client import LlmClient
from ..pipeline import PIPELINE_STEPS, PipelineContext, PipelineStore
from .base import BaseAgent
from .requirement_parser import RequirementParserAgent
from .personnel_matcher import PersonnelMatcherAgent
from .module_extractor import ModuleExtractorAgent
from .team_analyzer import TeamAnalyzerAgent
from .knowledge_updater import KnowledgeUpdaterAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """编排 Agent：管理 Pipeline 的串行执行流程。"""

    def __init__(self, llm_client: LlmClient | None = None) -> None:
        self._llm = llm_client
        self._store = PipelineStore()
        self._agents: dict[str, BaseAgent] = {
            "requirement_parsing": RequirementParserAgent(llm_client),
            "personnel_matching": PersonnelMatcherAgent(llm_client),
            "module_extraction": ModuleExtractorAgent(llm_client),
            "team_analysis": TeamAnalyzerAgent(llm_client),
            "knowledge_update": KnowledgeUpdaterAgent(llm_client),
        }

    def start(
        self,
        workspace_id: str,
        user_message: str,
        profiles: list | None = None,
        module_entries: list | None = None,
        task_records: list | None = None,
    ) -> dict[str, Any]:
        """启动分析 Pipeline，执行步骤1。"""
        ctx = PipelineContext(
            workspace_id=workspace_id,
            session_id=f"pipeline-{datetime.now(timezone.utc).isoformat()}",
            user_message=user_message,
            profiles=profiles or [],
            module_entries=module_entries or [],
            task_records=task_records or [],
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._store.save(ctx)
        return self._execute_current_step(ctx)

    def get_state(self, workspace_id: str) -> dict[str, Any] | None:
        """获取 Pipeline 当前状态。"""
        ctx = self._store.load(workspace_id)
        if not ctx:
            return None
        return ctx.to_dict()

    def confirm_step(
        self,
        workspace_id: str,
        action: str,
        modifications: dict | None = None,
        feedback: str | None = None,
    ) -> dict[str, Any]:
        """确认/修改/重新分析当前步骤。"""
        ctx = self._store.load(workspace_id)
        if not ctx:
            raise ValueError("Pipeline 不存在，请先启动分析")
        if ctx.is_complete:
            return {"status": "complete", "reply": "所有步骤已完成"}

        step_name = ctx.current_step

        if action == "confirm":
            # 记录当前步骤结果，进入下一步
            self._save_step_result(ctx, step_name, "confirmed")
            ctx.current_step_index += 1
            self._store.save(ctx)

            if ctx.is_complete:
                return {"status": "complete", "reply": "所有步骤已完成", "step_progress": ctx.step_progress}
            return self._execute_current_step(ctx)

        elif action == "modify":
            # 用户手动修改结果
            if modifications:
                self._apply_modifications(ctx, step_name, modifications)
            self._save_step_result(ctx, step_name, "modified")
            ctx.current_step_index += 1
            self._store.save(ctx)

            if ctx.is_complete:
                return {"status": "complete", "reply": "所有步骤已完成", "step_progress": ctx.step_progress}
            return self._execute_current_step(ctx)

        elif action == "reanalyze":
            # 重新分析，注入约束
            if feedback:
                ctx.step_constraints[step_name] = feedback
            self._store.save(ctx)
            return self._execute_current_step(ctx)

        elif action == "skip":
            self._save_step_result(ctx, step_name, "skipped")
            ctx.current_step_index += 1
            self._store.save(ctx)

            if ctx.is_complete:
                return {"status": "complete", "reply": "所有步骤已完成", "step_progress": ctx.step_progress}
            return self._execute_current_step(ctx)

        elif action == "execute":
            # 第5步专用：执行 pending_changes
            return {"status": "executed", "reply": "待执行变更已提交"}

        else:
            raise ValueError(f"不支持的操作: {action}")

    def _execute_current_step(self, ctx: PipelineContext) -> dict[str, Any]:
        """执行当前步骤。"""
        step_name = ctx.current_step
        agent = self._agents.get(step_name)
        if not agent:
            return {"status": "error", "reply": f"未知步骤: {step_name}"}

        result = agent.execute(ctx)

        # 将结果存储到 context
        self._save_step_result(ctx, step_name, result.get("status", "success"))

        # 把数据写入 ctx 对应字段
        self._populate_context(ctx, step_name, result)

        # 保存 LLM 统计
        if result.get("llm_stats"):
            ctx.llm_stats.append(result["llm_stats"])

        self._store.save(ctx)

        return {
            "status": result.get("status", "success"),
            "step": step_name,
            "reply": result.get("reply", ""),
            "data": result.get("data", {}),
            "step_progress": ctx.step_progress,
        }

    def _save_step_result(self, ctx: PipelineContext, step_name: str, status: str) -> None:
        ctx.step_results[step_name] = {"status": status}

    def _populate_context(self, ctx: PipelineContext, step_name: str, result: dict[str, Any]) -> None:
        data = result.get("data", {})
        if step_name == "requirement_parsing":
            ctx.requirements = data.get("requirements", [])
        elif step_name == "personnel_matching":
            ctx.assignment_suggestions = data.get("assignments", [])
        elif step_name == "module_extraction":
            ctx.module_changes = data.get("module_changes", [])
        elif step_name == "team_analysis":
            ctx.team_analysis = data
        elif step_name == "knowledge_update":
            ctx.pending_changes = data.get("pending_changes", [])

    def _apply_modifications(self, ctx: PipelineContext, step_name: str, modifications: dict) -> None:
        if step_name == "requirement_parsing":
            ctx.requirements = modifications.get("requirements", ctx.requirements)
        elif step_name == "personnel_matching":
            ctx.assignment_suggestions = modifications.get("assignments", ctx.assignment_suggestions)
        elif step_name == "module_extraction":
            ctx.module_changes = modifications.get("module_changes", ctx.module_changes)
        elif step_name == "team_analysis":
            ctx.team_analysis.update(modifications)
        elif step_name == "knowledge_update":
            ctx.pending_changes = modifications.get("pending_changes", ctx.pending_changes)
