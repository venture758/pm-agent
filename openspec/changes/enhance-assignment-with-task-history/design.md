## Context

当前推荐系统的评分完全依赖 `ModuleKnowledgeEntry`（模块知识库中的 primary_owner、backup_owner、familiarity）和 `MemberProfile`（技能、负载、经验等级）。但系统中已经存在 `workspace_task_records` 表，记录了每个成员实际负责任务的历史数据，包括 module_path、task_type（如"设计与编码"）、actual_person_days、defects 等。这些数据没有被评分流程消费。

## Goals / Non-Goals

**Goals:**
- 在 `recommend_assignments()` 评分中引入任务历史作为加分项
- 按成员聚合任务历史，生成 `TaskHistoryProfile` 供评分函数使用
- 在推荐理由中展示任务历史依据
- 在 LLM 成员上下文中补充任务历史摘要

**Non-Goals:**
- 不修改任务明细表的数据结构或 DDL
- 不改变现有 API 接口契约
- 不替换模块知识库的评分权重，只是增量补充
- 不引入新的 LLM 调用

## Decisions

### 1. 数据加载策略：在 `recommend()` 入口处一次性加载全部任务记录

在 `workflows.py` 的 `recommend()` 方法中，调用 `workspace_store.load_task_records_by_workspace_id()` 一次性获取当前工作区的全部任务记录，然后按 `owner` 聚合成 `TaskHistoryProfile` dict。这样避免了在评分循环中重复查询数据库。

**Alternatives considered:**
- 每次评分时按需查询：会导致 N*M 次数据库查询，性能差
- 在 `_intake_workspace()` 中顺便加载：耦合了 intake 和 task 两个无关流程

### 2. `TaskHistoryProfile` 数据结构

```python
@dataclass
class TaskHistoryProfile:
    member_name: str
    total_tasks: int                          # 总任务数
    design_coding_tasks: int                  # "设计与编码"类型任务数
    module_path_counts: dict[str, int]        # 按 module_path 聚合的任务数
    story_task_counts: dict[str, int]         # 按 story_code 聚合的任务数
    avg_actual_vs_planned: float              # 平均 actual_person_days / planned_person_days
    total_defects: int                        # 总缺陷数
```

### 3. 评分因子集成到 `_member_score()`

在现有评分基础上，新增以下加分项（小权重，不颠覆现有评分体系）：

| 因子 | 分值 | 说明 |
|---|---|---|
| 匹配模块路径有任务记录 | +1 ~ +3 | 按该成员在匹配 module_path 下的任务数计分，最多 +3（每条 +1，上限 3） |
| 有"设计与编码"经验 | +1 | `design_coding_tasks > 0` 即加分 |
| 匹配关联用户故事有任务 | +1 | 成员在该 story 下有任务记录 |
| 估算准确度高 | +0.5 | `0.8 <= avg_actual_vs_planned <= 1.2` |
| 缺陷率偏高 | -1 | `total_defects > total_tasks * 2`（平均每个任务超 2 个缺陷） |

### 4. 推荐理由展示

在 `_member_score()` 返回的 reasons 列表中追加任务历史相关的原因描述，例如：
- `"该成员在 '金蝶征信 -> 01-RPA' 模块有 3 条任务记录"`
- `"该成员有 5 条设计与编码任务经验"`
- `"该成员在关联故事下有 2 条任务记录"`

### 5. LLM 成员上下文补充

在 `agent_prompt.py` 的 `build_member_context()` 中，为每个成员追加一行任务历史摘要：
```
- {name}: 任务历史: {total_tasks}条任务, {design_coding_tasks}条设计与编码, 主要模块: {top_module_path}
```
如果没有任务历史则不显示此行。

## Risks / Trade-offs

- **[风险]** 任务记录中的 `module_path` 格式与 `ModuleKnowledgeEntry` 的 key 可能不完全一致 → **缓解**：使用模糊匹配（`in` 检查），而非精确匹配
- **[风险]** 大量任务记录时聚合性能 → **缓解**：`load_task_records_by_workspace_id()` 使用单次 SQL 查询 + Python dict 聚合，通常任务量在百级以内
- **[权衡]** 任务历史评分权重较小（+1 ~ +3），不会颠覆模块知识库的主导地位 → 这是有意为之，任务历史是补充而非替代
- **[风险]** 旧数据中没有 task_type 字段或值为空 → **缓解**：`task_type` 匹配使用宽松条件（包含"设计"或"编码"关键字即算）
