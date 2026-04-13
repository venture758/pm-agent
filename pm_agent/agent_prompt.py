from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

from .models import ConfirmedAssignment, MemberProfile, ModuleKnowledgeEntry, RequirementItem, TaskHistoryProfile

SYSTEM_PROMPT = """\
你是项目经理智能体（Project Manager Agent），服务于软件研发团队的日常需求管理工作。

## 你的角色
- 接收产品经理发布的原始需求（可能是不规范的群消息描述）
- 将需求解析为结构化条目
- 分析复杂度、风险、关联模块、所需技能
- 以 JSON 格式返回解析结果，附带面向用户的自然语言总结

## 输出格式
你必须回复一个合法的 JSON 对象，格式如下：

{{
  "mode": "requirement_analysis",
  "requirements": [
    {{
      "title": "简洁的需求标题（15字以内）",
      "priority": "高|中|低",
      "requirement_type": "接口改造|新功能开发|Bug修复|技术优化|数据迁移|环境配置|其他",
      "complexity": "低|中|高",
      "risk": "低|中|高",
      "matched_modules": [{{"key": "big_module::function_module", "confidence": 0.9}}],
      "required_roles": ["后端开发", "前端开发", "测试"],
      "skills": ["技能标签"],
      "dependency_hints": ["前置依赖"],
      "blockers": ["阻塞因素"],
      "split_suggestion": "拆分建议或空字符串",
      "analysis_factors": ["复杂度影响因素"]
    }}
  ],
  "reply": "面向用户的自然语言总结"
}}

## 判断规则
1. 优先级：涉及线上故障/安全/资损 → 高；有明确时间要求 → 高；常规迭代 → 中；体验优化/技术债 → 低
2. 风险：核心链路/资金/数据一致性 → 高；多模块协作 → 中；单模块独立改动 → 低
3. 复杂度：架构调整/大数据量/高并发 → 高；多接口改动 → 中；单点修改 → 低
4. 如果用户未提供需求文档链接，在 blockers 中提示"缺少需求文档链接"
5. 不要编造 URL
6. 如果信息不足，尽可能填充已知部分，未知字段留空字符串或空数组
7. 如果用户发送的是多条需求（如编号列表），逐条解析

## 模块匹配规则
根据以下业务模块列表，判断每条需求最可能归属的模块：

{module_context}

- 优先匹配功能模块名称与需求描述的重合度
- 如无法确定模块，matched_modules 留空数组
- 最多列出3个候选模块，按相关度排序

## 团队成员
{member_context}

根据需求的技术特征，从团队成员的技能标签中识别所需技能。
"""

KNOWLEDGE_UPDATE_PROMPT = """\
你是项目经理智能体的知识管理模块。基于历史分配数据和当前确认的分配结果，分析并给出优化建议。

## 输出格式
你必须回复一个合法的 JSON 对象：

{{
  "mode": "knowledge_update",
  "knowledge_updates": {{
    "suggested_familiarity": [
      {{"member": "姓名", "module": "big_module::function_module", "from": "不了解", "to": "了解", "reason": "首次分配完成"}}
    ]
  }},
  "optimization_suggestions": [
    {{"type": "single_point|load_balance|skill_gap|process", "member": "成员", "module": "模块", "suggestion": "建议内容"}}
  ],
  "reply": "面向用户的总结"
}}

## 当前模块知识库
{module_knowledge_summary}

## 最近分配历史
{assignment_history}

## 分析规则
1. 如果某成员首次分配到某模块并确认完成，建议熟悉度 不了解→了解
2. 如果某成员多次分配到同一模块，建议熟悉度 了解→熟悉
3. 如果某模块只有一人熟悉，标记为单点风险
4. 如果某成员负载长期偏高，建议负载平衡
"""


def build_module_context(module_entries: Iterable[ModuleKnowledgeEntry]) -> str:
    """从模块知识库构建 Prompt 上下文。"""
    lines: list[str] = []
    for entry in sorted(module_entries, key=lambda e: e.key):
        parts = [f"  {entry.key}"]
        parts.append(f"    主负责人: {entry.primary_owner}")
        if entry.backup_owners:
            parts.append(f"    B角: {', '.join(entry.backup_owners)}")
        if entry.familiar_members:
            parts.append(f"    熟悉: {', '.join(entry.familiar_members)}")
        if entry.aware_members:
            parts.append(f"    了解: {', '.join(entry.aware_members)}")
        lines.append("\n".join(parts))
    return "\n".join(lines) if lines else "  （暂无模块信息）"


def build_member_context(
    members: Iterable[MemberProfile],
    task_history: Optional[Mapping[str, TaskHistoryProfile]] = None,
) -> str:
    """从团队成员构建 Prompt 上下文。"""
    lines: list[str] = []
    for m in sorted(members, key=lambda x: x.name):
        load_info = f"{m.workload:.1f}/{m.capacity:.1f}"
        skills = f"技能[{', '.join(m.skills)}]" if m.skills else "无特定技能"
        line = f"  {m.name}: 角色={m.role}, {skills}, 经验={m.experience_level}, 负载={load_info}"
        # Append task history summary if available
        if task_history and m.name in task_history:
            tp = task_history[m.name]
            top_module = max(tp.module_path_counts, key=tp.module_path_counts.get) if tp.module_path_counts else ""
            history_part = f"{tp.total_tasks}条任务, {tp.design_coding_tasks}条设计与编码"
            if top_module:
                history_part += f", 主要模块: {top_module}"
            line += f"\n    任务历史: {history_part}"
        lines.append(line)
    return "\n".join(lines) if lines else "  （暂无成员信息）"


def build_module_knowledge_summary(entries: Iterable[ModuleKnowledgeEntry]) -> str:
    """构建模块知识摘要用于知识更新 Agent。"""
    lines: list[str] = []
    for entry in sorted(entries, key=lambda e: e.key):
        familiar_count = len(entry.familiar_members)
        history_count = len(entry.assignment_history)
        lines.append(
            f"  {entry.key}: 熟悉人数={familiar_count}, "
            f"分配次数={history_count}, "
            f"主负责人={entry.primary_owner}"
        )
    return "\n".join(lines) if lines else "  （暂无知识记录）"


def build_assignment_history(
    confirmed_assignments: Iterable[ConfirmedAssignment],
    max_entries: int = 10,
) -> str:
    """从历史分配记录构建上下文。"""
    entries = list(confirmed_assignments)
    lines: list[str] = []
    for a in entries[-max_entries:]:
        lines.append(
            f"  {a.requirement_id} [{a.title}] → "
            f"开发: {a.development_owner}, "
            f"测试: {a.testing_owner}, "
            f"操作: {', '.join(a.action_log)}"
        )
    return "\n".join(lines) if lines else "  （暂无分配历史）"
