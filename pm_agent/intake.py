from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

from .models import MemberProfile, RequirementItem
from .utils import (
    classify_requirement_type,
    extract_terms,
    extract_urls,
    infer_complexity,
    infer_risk,
    infer_split_suggestion,
    normalize_name,
    normalize_requirement_id,
    normalize_text,
    parse_priority,
    safe_float,
    split_names,
    split_numbered_blocks,
    strip_urls,
    unique_list,
)


def parse_chat_requirements(message_text: str) -> list[RequirementItem]:
    requirements: list[RequirementItem] = []
    for block_id, block_text in split_numbered_blocks(message_text):
        urls = extract_urls(block_text)
        priority = parse_priority(block_text)
        title = strip_urls(block_text)
        title = title.replace(f"优先级：{priority}", "").replace(f"优先级:{priority}", "")
        title = title.replace(f"优先级{priority}", "").strip(" -；;")
        complexity, complexity_factors = infer_complexity(title)
        risk, risk_factors = infer_risk(title, priority, complexity)
        requirement = RequirementItem(
            requirement_id=normalize_requirement_id(block_id),
            title=title,
            source_url=urls[0] if urls else "",
            priority=priority,
            raw_text=block_text,
            source="chat",
            source_message=message_text,
            requirement_type=classify_requirement_type(title),
            complexity=complexity,
            risk=risk,
            skills=extract_terms(title),
            analysis_factors=unique_list(complexity_factors + risk_factors),
            split_suggestion=infer_split_suggestion(title, complexity, risk),
        )
        if not requirement.source_url:
            requirement.blockers.append("缺少需求文档链接")
        requirements.append(requirement)
    return requirements


def parse_imported_requirements(rows: Iterable[Mapping[str, Any]]) -> list[RequirementItem]:
    requirements: list[RequirementItem] = []
    for index, row in enumerate(rows, 1):
        title = normalize_text(row.get("title") or row.get("需求标题") or row.get("name"))
        raw_text = normalize_text(row.get("raw_text") or title)
        priority = normalize_text(row.get("priority") or row.get("优先级")) or parse_priority(raw_text)
        complexity, complexity_factors = infer_complexity(raw_text)
        risk, risk_factors = infer_risk(raw_text, priority, complexity)
        requirement = RequirementItem(
            requirement_id=normalize_requirement_id(row.get("id") or row.get("需求编号") or index),
            title=title or f"需求{index}",
            source_url=normalize_text(row.get("url") or row.get("链接") or row.get("详细说明（URL）")),
            priority=priority or "中",
            raw_text=raw_text,
            source="import",
            source_message=raw_text,
            requirement_type=classify_requirement_type(raw_text),
            complexity=complexity,
            risk=risk,
            skills=extract_terms(raw_text),
            analysis_factors=unique_list(complexity_factors + risk_factors),
            split_suggestion=infer_split_suggestion(raw_text, complexity, risk),
        )
        if not requirement.title:
            requirement.blockers.append("缺少需求标题")
        requirements.append(requirement)
    return requirements


def normalize_team_profiles(rows: Iterable[Mapping[str, Any]]) -> list[MemberProfile]:
    profiles: list[MemberProfile] = []
    for row in rows:
        name = normalize_text(row.get("name") or row.get("姓名") or row.get("成员"))
        if not name:
            continue
        profile = MemberProfile(
            name=name,
            role=normalize_text(row.get("role") or row.get("角色")) or "developer",
            skills=unique_list(
                split_names(row.get("skills") or row.get("技能") or row.get("skills_tags") or "")
            ),
            experience_level=normalize_text(row.get("experience") or row.get("经验等级")) or "中",
            workload=safe_float(row.get("workload") or row.get("当前负载") or row.get("load")),
            capacity=safe_float(row.get("capacity") or row.get("可用容量") or 1.0, default=1.0),
            constraints=unique_list(
                split_names(row.get("constraints") or row.get("约束") or row.get("特殊约束") or "")
            ),
        )
        profiles.append(profile)
    return profiles


def build_profiles_from_module_entries(
    module_entries: Iterable[Any],
    overrides: Optional[Iterable[Mapping[str, Any]]] = None,
) -> list[MemberProfile]:
    override_map = {normalize_name(profile.name): profile for profile in normalize_team_profiles(overrides or [])}
    members: dict[str, MemberProfile] = {}
    for entry in module_entries:
        for member_name, familiarity in entry.familiarity_by_member.items():
            normalized = normalize_name(member_name)
            profile = members.get(normalized)
            if profile is None:
                base = override_map.get(normalized)
                profile = base or MemberProfile(name=member_name)
                members[normalized] = profile
            if entry.key not in profile.module_familiarity:
                profile.module_familiarity[entry.key] = familiarity
            else:
                profile.module_familiarity[entry.key] = max(
                    profile.module_familiarity[entry.key],
                    familiarity,
                    key=lambda label: {"不了解": 0, "了解": 2, "熟悉": 3}.get(label, 0),
                )
            if familiarity in {"了解", "熟悉"}:
                profile.skills = unique_list(profile.skills + [entry.big_module, entry.function_module])
    for normalized, override in override_map.items():
        if normalized not in members:
            members[normalized] = override
    return sorted(members.values(), key=lambda item: item.name)


def enrich_member_profiles(
    members: Iterable[MemberProfile],
    module_entries: Iterable[Any],
) -> list[MemberProfile]:
    profiles: dict[str, MemberProfile] = {
        normalize_name(member.name): MemberProfile(
            name=member.name,
            role=member.role,
            skills=list(member.skills),
            experience_level=member.experience_level,
            workload=member.workload,
            capacity=member.capacity,
            constraints=list(member.constraints),
            module_familiarity=dict(member.module_familiarity),
        )
        for member in members
        if normalize_name(member.name)
    }
    for entry in module_entries:
        for member_name, familiarity in entry.familiarity_by_member.items():
            profile = profiles.get(normalize_name(member_name))
            if profile is None:
                continue
            current = profile.module_familiarity.get(entry.key)
            if current:
                profile.module_familiarity[entry.key] = max(
                    current,
                    familiarity,
                    key=lambda label: {"不了解": 0, "了解": 2, "熟悉": 3}.get(label, 0),
                )
            else:
                profile.module_familiarity[entry.key] = familiarity
            if familiarity in {"了解", "熟悉"}:
                profile.skills = unique_list(profile.skills + [entry.big_module, entry.function_module])
    return sorted(profiles.values(), key=lambda item: item.name)


def detect_assignment_blockers(requirements: list[RequirementItem], members: list[MemberProfile]) -> None:
    total_available_capacity = sum(max(member.capacity - member.workload, 0.0) for member in members)
    if members and total_available_capacity < len(requirements) * 0.2:
        for requirement in requirements:
            requirement.blockers.append("团队整体可用容量偏低")
    for requirement in requirements:
        if not requirement.skills:
            requirement.blockers.append("未识别到明确技能标签")
        if not any(member.capacity > member.workload for member in members):
            requirement.blockers.append("当前没有可用成员")
