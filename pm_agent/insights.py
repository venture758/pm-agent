from __future__ import annotations

from collections import Counter, defaultdict

from .config import FAMILIARITY_SCORES
from .knowledge_base import module_entry_coverage
from .models import AgentState, GrowthSuggestion, HeatmapEntry, MemberProfile, SinglePointRisk
from .utils import normalize_name


def build_load_heatmap(state: AgentState, members: list[MemberProfile]) -> list[HeatmapEntry]:
    task_loads: defaultdict[str, float] = defaultdict(float)
    for task in state.tasks.values():
        task_loads[normalize_name(task.owner)] += task.planned_person_days or 0.0
    heatmap: list[HeatmapEntry] = []
    for member in members:
        load = member.workload + task_loads[normalize_name(member.name)]
        capacity = member.capacity or 1.0
        utilization = load / capacity if capacity else load
        if utilization >= 1:
            level = "高"
        elif utilization >= 0.6:
            level = "中"
        else:
            level = "低"
        heatmap.append(
            HeatmapEntry(
                member=member.name,
                load=round(load, 2),
                capacity=capacity,
                utilization=round(utilization, 2),
                level=level,
                sources=["当前负载", "平台任务工时"],
            )
        )
    return sorted(heatmap, key=lambda item: item.utilization, reverse=True)


def detect_single_points(state: AgentState) -> list[SinglePointRisk]:
    risks: list[SinglePointRisk] = []
    owner_counter = Counter(assignment.development_owner for assignment in state.confirmed_assignments.values() if assignment.development_owner)
    for entry in state.module_entries.values():
        coverage = module_entry_coverage(entry)
        if coverage <= 1 and entry.primary_owner:
            risks.append(
                SinglePointRisk(
                    member=entry.primary_owner,
                    module_key=entry.key,
                    reason="模块只有单一熟悉成员覆盖",
                    related_requirements=[history.requirement_id for history in entry.assignment_history[-3:]],
                )
            )
        if owner_counter.get(entry.primary_owner, 0) >= 2:
            risks.append(
                SinglePointRisk(
                    member=entry.primary_owner,
                    module_key=entry.key,
                    reason="同一成员承接了多个模块或需求的核心工作",
                    related_requirements=[history.requirement_id for history in entry.assignment_history[-3:]],
                )
            )
    return risks


def suggest_growth_paths(state: AgentState, members: list[MemberProfile]) -> list[GrowthSuggestion]:
    suggestions: list[GrowthSuggestion] = []
    member_map = {normalize_name(member.name): member for member in members}
    for entry in state.module_entries.values():
        for member_name, familiarity in entry.familiarity_by_member.items():
            member = member_map.get(normalize_name(member_name))
            if not member:
                continue
            if member.capacity - member.workload <= 0.2:
                continue
            if familiarity != "了解":
                continue
            suggestions.append(
                GrowthSuggestion(
                    member=member.name,
                    module_key=entry.key,
                    suggestion=f"建议让 {member.name} 在 {entry.function_module} 模块中以协作人身份参与一项需求。",
                    rationale="成员具备基础了解且当前仍有可用容量，适合通过结对方式提升熟悉度。",
                )
            )
    return suggestions


def compute_insight_summary(
    heatmap: list[HeatmapEntry],
    single_points: list[SinglePointRisk],
    growth_suggestions: list[GrowthSuggestion],
) -> dict[str, Any]:
    member_count = len(heatmap)
    high_load = sum(1 for h in heatmap if h.level == "高")
    mid_load = sum(1 for h in heatmap if h.level == "中")
    low_load = sum(1 for h in heatmap if h.level == "低")
    avg_utilization = round(sum(h.utilization for h in heatmap) / member_count, 2) if member_count else 0.0

    # Health score: start at 100, deduct for risks and overload
    score = 100.0
    score -= high_load * 8  # each overloaded member
    score -= len(single_points) * 5  # each single point risk
    if avg_utilization > 0.9:
        score -= 15
    elif avg_utilization > 0.75:
        score -= 5
    score = max(0, min(100, round(score)))

    return {
        "team_health_score": score,
        "high_load_count": high_load,
        "mid_load_count": mid_load,
        "low_load_count": low_load,
        "single_point_risk_count": len(single_points),
        "growth_opportunity_count": len(growth_suggestions),
        "member_count": member_count,
        "avg_utilization": avg_utilization,
    }
