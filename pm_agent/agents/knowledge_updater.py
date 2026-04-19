from __future__ import annotations

from typing import Any

from ..pipeline import PipelineContext
from .base import BaseAgent

KNOWLEDGE_UPDATER_SYSTEM = """\
你是知识管理汇总专家。汇总前面所有步骤的变更建议，生成待执行操作列表。

## 输出格式
{
  "mode": "knowledge_update",
  "summary": {
    "requirements_parsed": 0,
    "personnel_assigned": 0,
    "modules_created": 0,
    "familiarity_updates": 0,
    "risks_identified": 0
  },
  "pending_changes": [
    {
      "type": "create_module|update_familiarity|create_assignment",
      "data": {}
    }
  ],
  "reply": "汇总结果..."
}
"""


class KnowledgeUpdaterAgent(BaseAgent):
    """步骤5：知识更新汇总 Agent。"""
    mode = "knowledge_update"

    def build_system_prompt(self, ctx: PipelineContext) -> str:
        return KNOWLEDGE_UPDATER_SYSTEM

    def build_user_prompt(self, ctx: PipelineContext) -> str:
        parts = []
        parts.append(f"## 步骤1: 需求解析 — {len(ctx.requirements)} 条")
        parts.append(f"## 步骤2: 人员匹配 — {len(ctx.assignment_suggestions)} 条")
        parts.append(f"## 步骤3: 模块提炼 — {len(ctx.module_changes)} 条")
        parts.append(f"## 步骤4: 梯队分析")

        parts.append("\n请汇总以上所有步骤的变更，生成待执行操作列表 pending_changes。")

        constraint = ctx.step_constraints.get("knowledge_update", "")
        if constraint:
            parts.append(f"\n## 额外约束\n{constraint}")

        return "\n".join(parts)

    def parse_response(self, text: str, ctx: PipelineContext) -> dict[str, Any]:
        parsed = self._llm.parse_json_response(text)
        pending = parsed.get("pending_changes", [])
        return {
            "status": "success",
            "mode": self.mode,
            "summary": parsed.get("summary", {}),
            "pending_changes": pending,
            "reply": parsed.get("reply", ""),
            "data": {"pending_changes": pending, "summary": parsed.get("summary", {})},
        }
