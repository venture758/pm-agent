from __future__ import annotations

from typing import Any

from ..pipeline import PipelineContext
from .base import BaseAgent

PERSONNEL_MATCHER_SYSTEM = """\
你是研发团队的人员匹配专家。基于需求解析结果和团队成员信息，为每条需求推荐开发、测试、B角和协作人。

## 输出格式
你必须回复一个合法的 JSON 对象：
{
  "mode": "personnel_matching",
  "assignments": [
    {
      "requirement_id": "REQ-001",
      "requirement_title": "...",
      "development_owner": "姓名",
      "testing_owner": "姓名",
      "backup_owner": "姓名",
      "collaborators": ["姓名"],
      "reasons": ["推荐理由1", "推荐理由2"],
      "workload_snapshot": {"姓名": 0.3},
      "confidence": 0.85
    }
  ],
  "reply": "推荐分配..."
}

## 匹配规则
- 综合技能匹配度、模块熟悉度、当前负载、历史任务表现
- 避免给同一人分配过多高优先级需求
- 每个需求至少有一主一备
- 如果信息不足，相应字段留空字符串或空数组
"""


class PersonnelMatcherAgent(BaseAgent):
    """步骤2：人员匹配 Agent。"""
    mode = "personnel_matching"

    def build_system_prompt(self, ctx: PipelineContext) -> str:
        return PERSONNEL_MATCHER_SYSTEM

    def build_user_prompt(self, ctx: PipelineContext) -> str:
        parts = []
        parts.append("## 需求列表")
        for req in ctx.requirements:
            parts.append(
                f"- [{req.get('requirement_id', '')}] {req.get('title', '')} "
                f"(优先级: {req.get('priority', '中')})"
            )
            if req.get("skills"):
                parts.append(f"  所需技能: {', '.join(req['skills'])}")

        parts.append("\n## 团队成员")
        for m in ctx.profiles:
            name = m.get("name", "")
            role = m.get("role", "")
            skills = m.get("skills", [])
            workload = m.get("workload", 0)
            capacity = m.get("capacity", 1)
            parts.append(
                f"- {name}: 角色={role}, 技能={skills}, 负载={workload}/{capacity}"
            )

        constraint = ctx.step_constraints.get("personnel_matching", "")
        if constraint:
            parts.append(f"\n## 额外约束\n{constraint}")

        return "\n".join(parts)

    def parse_response(self, text: str, ctx: PipelineContext) -> dict[str, Any]:
        parsed = self._llm.parse_json_response(text)
        assignments = parsed.get("assignments", [])
        return {
            "status": "success",
            "mode": self.mode,
            "assignments": assignments,
            "reply": parsed.get("reply", ""),
            "data": {"assignments": assignments},
        }
