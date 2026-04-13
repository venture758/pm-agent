from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Mapping, Optional

from .models import (
    AssignmentRecommendation,
    ConfirmedAssignment,
    MemberProfile,
    ModuleKnowledgeEntry,
    RequirementItem,
    StoryRecord,
    TaskRecord,
)
from .utils import (
    complexity_score,
    familiarity_score,
    normalize_name,
    normalize_requirement_id,
    normalize_text,
    priority_score,
    risk_score,
    unique_list,
)


def _member_score(
    requirement: RequirementItem,
    member: MemberProfile,
    module_entry: Optional[ModuleKnowledgeEntry],
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    if module_entry:
        familiarity = member.module_familiarity.get(module_entry.key) or module_entry.familiarity_by_member.get(member.name, "")
        familiarity_value = familiarity_score(familiarity)
        if normalize_name(member.name) == normalize_name(module_entry.primary_owner):
            score += 5
            reasons.append(f"命中模块主负责人：{module_entry.primary_owner}")
        elif normalize_name(member.name) in {normalize_name(owner) for owner in module_entry.backup_owners}:
            score += 3
            reasons.append(f"命中模块B角：{', '.join(module_entry.backup_owners)}")
        score += familiarity_value * 2
        if familiarity:
            reasons.append(f"模块熟悉度：{familiarity}")
    skill_overlap = len(set(member.skills) & set(requirement.skills))
    if skill_overlap:
        score += skill_overlap * 1.5
        reasons.append("技能标签命中")
    availability = max(member.capacity - member.workload, 0.0)
    score += availability * 2
    reasons.append(f"可用容量：{availability:.2f}")
    if availability <= 0:
        score -= 4
    if requirement.risk == "高" and member.experience_level in {"高", "资深"}:
        score += 2
        reasons.append("高风险需求优先匹配高经验成员")
    if any("不可分配" in item for item in member.constraints):
        score -= 100
    return score, reasons


def recommend_assignments(
    requirements: Iterable[RequirementItem],
    members: Iterable[MemberProfile],
    module_lookup: Mapping[str, ModuleKnowledgeEntry],
) -> list[AssignmentRecommendation]:
    member_list = list(members)
    recommendations: list[AssignmentRecommendation] = []
    for requirement in requirements:
        matched_module = module_lookup.get(requirement.matched_module_keys[0]) if requirement.matched_module_keys else None
        dev_candidates: list[tuple[MemberProfile, float, list[str]]] = []
        test_candidates: list[tuple[MemberProfile, float, list[str]]] = []
        for member in member_list:
            score, reasons = _member_score(requirement, member, matched_module)
            if member.role in {"qa", "tester", "test"}:
                test_candidates.append((member, score, reasons))
            else:
                dev_candidates.append((member, score, reasons))
        dev_candidates.sort(key=lambda item: item[1], reverse=True)
        test_candidates.sort(key=lambda item: item[1], reverse=True)
        recommendation = AssignmentRecommendation(
            requirement_id=normalize_requirement_id(requirement.requirement_id),
            title=requirement.title,
            module_key=matched_module.key if matched_module else "",
            module_name=matched_module.function_module if matched_module else "",
            split_suggestion=requirement.split_suggestion,
        )
        if not dev_candidates or dev_candidates[0][1] <= 0:
            recommendation.unassigned_reason = "没有找到满足条件的开发负责人"
            recommendation.reasons = unique_list(requirement.blockers + ["缺少可用开发成员"])
            recommendations.append(recommendation)
            continue
        best_dev, best_score, dev_reasons = dev_candidates[0]
        recommendation.development_owner = best_dev.name
        recommendation.reasons = unique_list(dev_reasons + requirement.analysis_factors)
        recommendation.confidence = round(best_score / 10.0, 2)
        recommendation.workload_snapshot[best_dev.name] = best_dev.workload + max(0.1, complexity_score(requirement.complexity) * 0.1)
        if len(dev_candidates) > 1 and dev_candidates[1][1] > 0:
            recommendation.backup_owner = dev_candidates[1][0].name
        if test_candidates and test_candidates[0][1] > -50:
            recommendation.testing_owner = test_candidates[0][0].name
        if recommendation.module_name:
            recommendation.reasons.append(f"命中模块：{recommendation.module_name}")
        if recommendation.workload_snapshot[best_dev.name] > best_dev.capacity:
            recommendation.reasons.append("分配后存在过载风险")
        recommendations.append(recommendation)
    return recommendations


def render_group_reply(recommendations: Iterable[AssignmentRecommendation]) -> str:
    lines: list[str] = []
    for index, recommendation in enumerate(recommendations, 1):
        assignee = f"@{recommendation.development_owner}" if recommendation.development_owner else "待分配"
        backup = f"（@{recommendation.backup_owner}）" if recommendation.backup_owner else ""
        tester = f" @{recommendation.testing_owner}" if recommendation.testing_owner else ""
        split = f" 拆分建议：{recommendation.split_suggestion}" if recommendation.split_suggestion else ""
        lines.append(f"{index}.{recommendation.title} {assignee}{backup}{tester}{split}".strip())
    return "\n".join(lines)


def confirm_assignments(
    recommendations: Iterable[AssignmentRecommendation],
    actions: Optional[Mapping[str, dict[str, object]]] = None,
) -> list[ConfirmedAssignment]:
    action_map = {
        normalize_requirement_id(key): value
        for key, value in (actions or {}).items()
        if normalize_requirement_id(key)
    }
    confirmed: list[ConfirmedAssignment] = []
    for recommendation in recommendations:
        requirement_id = normalize_requirement_id(recommendation.requirement_id)
        action = action_map.get(requirement_id, {})
        action_type = normalize_text(action.get("action")) or "accept"
        if action_type in {"delete", "remove", "discard"}:
            continue
        record = ConfirmedAssignment(
            requirement_id=requirement_id,
            title=recommendation.title,
            module_key=recommendation.module_key,
            development_owner=normalize_text(action.get("development_owner")) or recommendation.development_owner,
            testing_owner=normalize_text(action.get("testing_owner")) or recommendation.testing_owner,
            backup_owner=normalize_text(action.get("backup_owner")) or recommendation.backup_owner,
            collaborators=unique_list(action.get("collaborators", recommendation.collaborators) or []),
            reasons=recommendation.reasons,
            split_suggestion=normalize_text(action.get("split_suggestion")) or recommendation.split_suggestion,
            unassigned_reason=recommendation.unassigned_reason,
        )
        record.action_log.append(action_type)
        if action_type == "reassign":
            record.action_log.append("已人工改派负责人")
        if action_type == "split":
            record.action_log.append("已人工拆分需求")
        if action_type == "add-collaborator":
            record.action_log.append("已添加协作人")
        confirmed.append(record)
    return confirmed


def build_story_and_task_handoff(confirmed_assignments: Iterable[ConfirmedAssignment]) -> tuple[list[StoryRecord], list[TaskRecord]]:
    stories: list[StoryRecord] = []
    tasks: list[TaskRecord] = []
    for assignment in confirmed_assignments:
        story_code = assignment.story_code or f"NEW-STORY-{assignment.requirement_id}"
        story = StoryRecord(
            user_story_code=story_code,
            name=assignment.title,
            user_story_name=assignment.title,
            status="需求评审完成",
            owner=assignment.development_owner,
            tester=assignment.testing_owner,
            developers=unique_list([assignment.development_owner] + assignment.collaborators),
            priority="高" if "高" in "".join(assignment.reasons) else "中",
            related_requirement_id=assignment.requirement_id,
        )
        task_list: list[TaskRecord] = [
            TaskRecord(
                task_code=f"NEW-TASK-{assignment.requirement_id}-DEV",
                story_code=story_code,
                story_name=assignment.title,
                name=f"设计与编码【{assignment.title}】",
                task_type="产品迭代与运维->设计与编码",
                owner=assignment.development_owner,
                status="计划",
                planned_person_days=max(0.5, 0.5 + len(assignment.collaborators) * 0.1),
                participants=assignment.collaborators,
                related_requirement_id=assignment.requirement_id,
            )
        ]
        if assignment.testing_owner:
            task_list.append(
                TaskRecord(
                    task_code=f"NEW-TASK-{assignment.requirement_id}-QA",
                    story_code=story_code,
                    story_name=assignment.title,
                    name=f"测试验证【{assignment.title}】",
                    task_type="产品迭代与运维->测试验证",
                    owner=assignment.testing_owner,
                    status="计划",
                    planned_person_days=0.3,
                    related_requirement_id=assignment.requirement_id,
                )
            )
        assignment.story_code = story_code
        assignment.task_codes = [task.task_code for task in task_list]
        stories.append(story)
        tasks.extend(task_list)
    return stories, tasks
