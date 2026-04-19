from __future__ import annotations

from typing import Any

from ..pipeline import PipelineContext
from .base import BaseAgent

TEAM_ANALYZER_SYSTEM = """\
你是团队梯队分析专家。分析团队对各业务模块的熟悉度分布，发现单点风险，建议成长路径。

## 输出格式
{
  "mode": "team_analysis",
  "module_familiarity_matrix": {
    "税务::发票接口": {
      "familiar": ["李祥"],
      "aware": ["张三"],
      "unfamiliar": ["王五"]
    }
  },
  "single_point_risks": [
    {
      "module_key": "税务::发票接口",
      "risk_member": "李祥",
      "severity": "high|medium|low",
      "suggestion": "建议..."
    }
  ],
  "growth_paths": [
    {
      "member": "王五",
      "target_module": "税务::发票接口",
      "current_level": "不了解",
      "target_level": "了解",
      "path": "先参与..."
    }
  ],
  "reply": "分析结果..."
}

## 规则
- 只有一人熟悉某模块时标记为单点风险
- 成长路径应具体可行
- 如果某模块所有人都了解，不标记风险
"""


class TeamAnalyzerAgent(BaseAgent):
    """步骤4：梯队分析 Agent。"""
    mode = "team_analysis"

    def build_system_prompt(self, ctx: PipelineContext) -> str:
        return TEAM_ANALYZER_SYSTEM

    def build_user_prompt(self, ctx: PipelineContext) -> str:
        parts = []
        parts.append("## 团队成员")
        for m in ctx.profiles:
            name = m.get("name", m) if isinstance(m, dict) else m.name
            parts.append(f"- {name}")

        parts.append("\n## 模块知识库")
        for e in ctx.module_entries:
            key = e.get("key", "") if isinstance(e, dict) else e.key
            fam = e.get("familiar_members", []) if isinstance(e, dict) else e.familiar_members
            awr = e.get("aware_members", []) if isinstance(e, dict) else e.aware_members
            unf = e.get("unfamiliar_members", []) if isinstance(e, dict) else e.unfamiliar_members
            parts.append(f"- {key}: 熟悉={fam}, 了解={awr}, 不了解={unf}")

        parts.append("\n## 本次人员匹配结果")
        for a in ctx.assignment_suggestions:
            parts.append(f"- {a.get('requirement_id', '')}: 开发={a.get('development_owner', '')}")

        constraint = ctx.step_constraints.get("team_analysis", "")
        if constraint:
            parts.append(f"\n## 额外约束\n{constraint}")

        return "\n".join(parts)

    def parse_response(self, text: str, ctx: PipelineContext) -> dict[str, Any]:
        parsed = self._llm.parse_json_response(text)
        return {
            "status": "success",
            "mode": self.mode,
            "module_familiarity_matrix": parsed.get("module_familiarity_matrix", {}),
            "single_point_risks": parsed.get("single_point_risks", []),
            "growth_paths": parsed.get("growth_paths", []),
            "reply": parsed.get("reply", ""),
            "data": {
                "module_familiarity_matrix": parsed.get("module_familiarity_matrix", {}),
                "single_point_risks": parsed.get("single_point_risks", []),
                "growth_paths": parsed.get("growth_paths", []),
            },
        }
