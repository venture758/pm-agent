## Context

当前 `MemberProfile.workload` 是人员在管理页面手动填写的值，不反映实际任务量。`workspace_task_records` 表包含每条任务的状态（计划/进行中/已完成）、owner 和 planned_person_days，可用于自动计算真实负载。

## Goals / Non-Goals

**Goals:**
- 从任务明细表按 owner 聚合未完成（状态 = "计划" 或 "进行中"）任务的 planned_person_days 总和
- 在推荐评分和 LLM 成员上下文中使用自动计算的负载
- 保留手动维护值作为兜底（成员无任务记录时使用）

**Non-Goals:**
- 不修改人员管理页面的手动维护入口（仍然保留，但仅作为无任务记录时的兜底）
- 不引入 real-time 负载计算（每次评分时一次性计算即可）
- 不改变 `MemberProfile` 的数据结构

## Decisions

### 1. 计算位置：在 `recommend_assignments()` 入口处完成

新增 `apply_auto_workload(members, task_records)` 函数，在评分循环前创建 MemberProfile 的浅拷贝，覆盖 workload 字段，然后传给现有的评分逻辑。这样：
- 不修改 `_member_score()` 的签名或行为
- 不污染原始 MemberProfile 对象
- 所有现有代码无需改动

**Alternatives considered:**
- 在 `_member_score()` 内部接收 task_records 并计算 → 增加函数签名复杂度，且每次评分都重复计算
- 在 `api_service` 层提前计算好 workload 再调 `recommend()` → 需要修改 MemberProfile 对象，耦合度高

### 2. 负载计算公式

```
workload = sum(planned_person_days for task where owner=member and status in ("计划", "进行中"))
fallback = member.workload (手动值)
```

- 使用 `planned_person_days` 而非 `actual_person_days`：计划任务还没有实际值，用 planned 更合理
- 已完成任务不计入当前负载：它们已经是历史，不占用当前容量
- 如果计算结果为 0 且成员有手动值，使用手动值

### 3. 任务记录来源复用

`workspace_store.load_task_records_by_workspace_id()` 已在上一轮改动中实现，直接复用。在 `api_service.generate_recommendations()` 和 `api_service.send_chat_message()` 中加载后传入。

## Risks / Trade-offs

- **[风险]** 任务记录中 owner 字段可能为空或与 MemberProfile.name 不一致 → **缓解**：聚合时按 normalized name 匹配，空 owner 跳过
- **[风险]** 导入的任务 Excel 数据不完整（部分任务缺少 planned_person_days） → **缓解**：默认 planned_person_days 为 0，不影响聚合
- **[权衡]** 计划中的任务用 planned 而非 actual 计算，可能高估 → **有意为之**：推荐时任务是"进行中"，实际人天可能为 0 或不准确
- **[风险]** 团队成员尚未导入任何任务记录 → **缓解**：兜底使用手动维护的 workload 值
