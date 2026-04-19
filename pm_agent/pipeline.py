from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import MemberProfile, ModuleKnowledgeEntry, RequirementItem, TaskRecord


# Pipeline 步骤枚举
PIPELINE_STEPS = [
    "requirement_parsing",
    "personnel_matching",
    "module_extraction",
    "team_analysis",
    "knowledge_update",
]

STEP_LABELS = {
    "requirement_parsing": "需求解析",
    "personnel_matching": "人员匹配",
    "module_extraction": "模块提炼",
    "team_analysis": "梯队分析",
    "knowledge_update": "知识更新",
}


@dataclass
class PipelineContext:
    """分析 Pipeline 的共享上下文。"""
    workspace_id: str
    session_id: str
    user_message: str

    # 已有数据（从 DB 加载）
    profiles: list[MemberProfile] = field(default_factory=list)
    module_entries: list[ModuleKnowledgeEntry] = field(default_factory=list)
    task_records: list[TaskRecord] = field(default_factory=list)

    # 逐步产出
    requirements: list[dict] = field(default_factory=list)        # 步骤1产出
    assignment_suggestions: list[dict] = field(default_factory=list)  # 步骤2产出
    module_changes: list[dict] = field(default_factory=list)      # 步骤3产出
    team_analysis: dict = field(default_factory=dict)             # 步骤4产出
    pending_changes: list[dict] = field(default_factory=list)     # 步骤5产出

    # 约束反馈
    step_constraints: dict[str, str] = field(default_factory=dict)

    # 状态
    current_step_index: int = 0
    step_results: dict[str, dict] = field(default_factory=dict)   # {step_name: {"status": ..., "reply": ..., "data": ...}}
    started_at: str = ""
    llm_stats: list[dict] = field(default_factory=list)

    @property
    def current_step(self) -> str | None:
        if self.current_step_index < len(PIPELINE_STEPS):
            return PIPELINE_STEPS[self.current_step_index]
        return None

    @property
    def is_complete(self) -> bool:
        return self.current_step_index >= len(PIPELINE_STEPS)

    @property
    def step_progress(self) -> list[dict[str, str]]:
        result = []
        for i, step in enumerate(PIPELINE_STEPS):
            if i < self.current_step_index:
                status = "completed"
            elif i == self.current_step_index:
                status = "current"
            else:
                status = "pending"
            result.append({"step": step, "label": STEP_LABELS[step], "status": status})
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "session_id": self.session_id,
            "user_message": self.user_message,
            "current_step": self.current_step,
            "current_step_index": self.current_step_index,
            "is_complete": self.is_complete,
            "step_progress": self.step_progress,
            "step_results": self.step_results,
            "requirements": self.requirements,
            "assignment_suggestions": self.assignment_suggestions,
            "module_changes": self.module_changes,
            "team_analysis": self.team_analysis,
            "pending_changes": self.pending_changes,
            "step_constraints": self.step_constraints,
            "llm_stats": self.llm_stats,
            "started_at": self.started_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineContext":
        ctx = cls(
            workspace_id=data.get("workspace_id", ""),
            session_id=data.get("session_id", ""),
            user_message=data.get("user_message", ""),
            current_step_index=data.get("current_step_index", 0),
            step_results=data.get("step_results", {}),
            started_at=data.get("started_at", ""),
        )
        ctx.requirements = data.get("requirements", [])
        ctx.assignment_suggestions = data.get("assignment_suggestions", [])
        ctx.module_changes = data.get("module_changes", [])
        ctx.team_analysis = data.get("team_analysis", {})
        ctx.pending_changes = data.get("pending_changes", [])
        ctx.step_constraints = data.get("step_constraints", {})
        ctx.llm_stats = data.get("llm_stats", [])
        return ctx


class PipelineStore:
    """Pipeline 状态的内存存储（后续可持久化到 DB）。"""

    _instance: "PipelineStore | None" = None

    def __new__(cls) -> "PipelineStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._pipelines: dict[str, PipelineContext] = {}
        return cls._instance

    def save(self, ctx: PipelineContext) -> None:
        self._pipelines[ctx.workspace_id] = ctx

    def load(self, workspace_id: str) -> PipelineContext | None:
        return self._pipelines.get(workspace_id)

    def delete(self, workspace_id: str) -> None:
        self._pipelines.pop(workspace_id, None)

    def clear(self) -> None:
        self._pipelines.clear()
