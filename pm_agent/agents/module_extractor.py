from __future__ import annotations

from typing import Any

from ..pipeline import PipelineContext
from .base import BaseAgent

MODULE_EXTRACTOR_SYSTEM = """\
你是模块知识管理专家。从需求中识别新的业务模块/子模块，或更新现有模块的归属关系。

## 输出格式
{
  "mode": "module_extraction",
  "module_changes": [
    {
      "action": "create_big_module|create_function_module|update_primary_owner|update_backup_owners",
      "big_module": "...",
      "function_module": "...",
      "primary_owner": "...",
      "rationale": "..."
    }
  ],
  "reply": "提炼结果..."
}

## 规则
- 仅当需求涉及新的业务领域时才创建新模块
- 不要为单一需求创建过多模块
- 模块名称应简洁且有意义
"""


class ModuleExtractorAgent(BaseAgent):
    """步骤3：模块提炼 Agent。"""
    mode = "module_extraction"

    def build_system_prompt(self, ctx: PipelineContext) -> str:
        return MODULE_EXTRACTOR_SYSTEM

    def build_user_prompt(self, ctx: PipelineContext) -> str:
        parts = []
        parts.append("## 需求列表")
        for req in ctx.requirements:
            parts.append(f"- [{req.get('requirement_id', '')}] {req.get('title', '')}")
            if req.get("matched_modules"):
                mods = ", ".join(m.get("key", str(m)) for m in req["matched_modules"])
                parts.append(f"  关联模块: {mods}")

        parts.append("\n## 当前模块知识库")
        for e in ctx.module_entries:
            key = e.get("key", "") if isinstance(e, dict) else e.key
            owner = e.get("primary_owner", "") if isinstance(e, dict) else e.primary_owner
            parts.append(f"- {key} (负责人: {owner})")

        parts.append("\n## 人员匹配结果")
        for a in ctx.assignment_suggestions:
            parts.append(f"- {a.get('requirement_id', '')}: 开发={a.get('development_owner', '')}, 测试={a.get('testing_owner', '')}")

        constraint = ctx.step_constraints.get("module_extraction", "")
        if constraint:
            parts.append(f"\n## 额外约束\n{constraint}")

        return "\n".join(parts)

    def parse_response(self, text: str, ctx: PipelineContext) -> dict[str, Any]:
        parsed = self._llm.parse_json_response(text)
        changes = parsed.get("module_changes", [])
        return {
            "status": "success",
            "mode": self.mode,
            "module_changes": changes,
            "reply": parsed.get("reply", ""),
            "data": {"module_changes": changes},
        }
