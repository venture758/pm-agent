## Why

当前项目经理智能体在分配开发负责人时，仅依赖模块知识库（primary_owner、backup_owner、familiarity）和成员技能/负载进行确定性评分，完全忽略了任务明细表（`workspace_task_records`）中积累的历史数据。任务明细表包含了每个成员实际负责过的任务、模块路径、实际人天与计划人天对比、缺陷数等宝贵的历史参考信息。将这些历史数据纳入评分依据，可以使推荐更加精准——尤其是当模块知识库覆盖不足或需要跨模块调配人员时，任务历史能提供更真实的"谁做过类似工作"的判断依据。

## What Changes

- 在 `recommend_assignments()` 评分流程中加载并聚合任务明细表中的历史记录，按成员维度构建 `TaskHistoryProfile`
- 扩展 `_member_score()` 评分函数，新增任务历史相关评分因子：
  - 成员在匹配模块路径下有过任务记录（按 `module_path` 模糊匹配）加分
  - 成员有过"设计与编码"类型任务的历史经验加分
  - 成员在关联用户故事下有过任务记录加分
  - 成员实际人天与计划人天比值接近 1.0（估算准确）给予小幅加分
  - 成员在相关任务中缺陷数偏高给予小幅减分
- 在 LLM 提示词（`agent_prompt.py`）的成员上下文中补充任务历史摘要信息，使 LLM 在解析需求时也能感知团队成员的实战经验
- 在推荐结果的 `reasons` 中展示任务历史作为推荐依据（如"该成员在 金蝶征信->01-RPA 模块有 3 条任务记录"）

## Capabilities

### New Capabilities
- `task-history-in-assignment`: 基于任务明细表历史记录为开发分配提供评分依据，包括数据加载、聚合、评分集成与推荐理由展示

### Modified Capabilities
<!-- No existing specs are being modified -- this is a new capability layered onto the existing recommendation pipeline -->

## Impact

- `pm_agent/assignment.py`: `_member_score()` 和 `recommend_assignments()` 需要接收并消费 `TaskHistoryProfile`
- `pm_agent/workflows.py`: `recommend()` 方法需要加载任务历史并构建聚合 profile
- `pm_agent/agent_prompt.py`: `build_member_context()` 需要补充任务历史摘要
- `pm_agent/workspace_store.py`: 新增 `load_task_records_by_workspace_id()` 方法供工作流调用
- `pm_agent/models.py`: 可能需要新增 `TaskHistoryProfile` 数据类
- 不影响现有 API 接口行为，仅增强推荐质量
