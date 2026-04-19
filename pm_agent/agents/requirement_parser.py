from __future__ import annotations

from typing import Any

from ..agent_prompt import SYSTEM_PROMPT, build_member_context, build_module_context
from ..models import MemberProfile, ModuleKnowledgeEntry
from ..pipeline import PipelineContext
from .base import BaseAgent


class RequirementParserAgent(BaseAgent):
    """Step 1: requirement parsing agent."""

    mode = "requirement_analysis"

    def build_system_prompt(self, ctx: PipelineContext) -> str:
        module_entries = [
            ModuleKnowledgeEntry(
                key=e.get("key", ""),
                big_module=e.get("big_module", ""),
                function_module=e.get("function_module", ""),
                primary_owner=e.get("primary_owner", ""),
                backup_owners=e.get("backup_owners", []),
                familiar_members=e.get("familiar_members", []),
                aware_members=e.get("aware_members", []),
                unfamiliar_members=e.get("unfamiliar_members", []),
            )
            for e in ctx.module_entries
        ]
        module_ctx = build_module_context(module_entries)

        # profiles may be list[dict] or list[MemberProfile]
        members: list[MemberProfile] = []
        for p in ctx.profiles:
            if isinstance(p, dict):
                members.append(MemberProfile(
                    name=p.get("name", ""),
                    role=p.get("role", "developer"),
                    skills=p.get("skills", []),
                    experience_level=p.get("experience_level", "中"),
                    workload=p.get("workload", 0.0),
                    capacity=p.get("capacity", 1.0),
                ))
            else:
                members.append(p)
        member_ctx = build_member_context(members)

        return SYSTEM_PROMPT.format(module_context=module_ctx, member_context=member_ctx)

    def build_user_prompt(self, ctx: PipelineContext) -> str:
        constraint = ctx.step_constraints.get("requirement_parsing", "")
        base = ctx.user_message
        if constraint:
            return f"{base}\n\n## 额外约束\n{constraint}"
        return base

    def parse_response(self, text: str, ctx: PipelineContext) -> dict[str, Any]:
        parsed = self._llm.parse_json_response(text) if self._llm else {}

        requirements = []
        for idx, req_data in enumerate(parsed.get("requirements", []), 1):
            requirements.append({
                "requirement_id": req_data.get("requirement_id", f"REQ-{idx:03d}"),
                "title": req_data.get("title", ""),
                "priority": req_data.get("priority", "中"),
                "requirement_type": req_data.get("requirement_type", ""),
                "complexity": req_data.get("complexity", "中"),
                "risk": req_data.get("risk", "中"),
                "skills": req_data.get("skills", []),
                "matched_modules": req_data.get("matched_modules", []),
                "dependency_hints": req_data.get("dependency_hints", []),
                "blockers": req_data.get("blockers", []),
                "split_suggestion": req_data.get("split_suggestion", ""),
                "analysis_factors": req_data.get("analysis_factors", []),
            })

        return {
            "status": "success",
            "mode": self.mode,
            "requirements": requirements,
            "reply": parsed.get("reply", "已解析需求"),
            "data": {"requirements": requirements},
        }
