## 1. 数据模型与加载

- [x] 1.1 在 `pm_agent/models.py` 中新增 `TaskHistoryProfile` dataclass，包含 member_name、total_tasks、design_coding_tasks、module_path_counts、story_task_counts、avg_actual_vs_planned、total_defects 字段
- [x] 1.2 在 `pm_agent/workspace_store.py` 中新增 `load_task_records_by_workspace_id(workspace_id)` 方法，执行 SQL 查询 `workspace_task_records` 表并返回 `list[dict]`

## 2. 聚合函数

- [x] 2.1 在 `pm_agent/assignment.py` 中新增 `aggregate_task_history(task_records: list[dict]) -> dict[str, TaskHistoryProfile]` 函数，按 owner 聚合为按成员名索引的 profile dict
- [x] 2.2 为 `aggregate_task_history()` 编写单元测试，覆盖有记录、无记录、空 owner 三种场景

## 3. 评分集成

- [x] 3.1 修改 `pm_agent/assignment.py` 中 `_member_score()` 函数签名，新增 `task_profile: TaskHistoryProfile | None` 参数
- [x] 3.2 在 `_member_score()` 中实现模块路径匹配加分（+1/条，上限 +3），使用 `module_path` 与 requirement 的 matched_module_key 做模糊匹配
- [x] 3.3 在 `_member_score()` 中实现"设计与编码"经验加分（+1），匹配 task_type 包含"设计"或"编码"
- [x] 3.4 在 `_member_score()` 中实现关联故事匹配加分（+1），匹配 story_task_counts 中是否有该 story
- [x] 3.5 在 `_member_score()` 中实现估算准确度加分（+0.5）和缺陷率扣分（-1）
- [x] 3.6 在 `_member_score()` 返回的 reasons 中追加任务历史相关原因描述
- [x] 3.7 修改 `recommend_assignments()` 函数签名，新增 `task_history: dict[str, TaskHistoryProfile] | None` 参数，并在评分循环中传递给 `_member_score()`

## 4. 工作流集成

- [x] 4.1 修改 `pm_agent/workflows.py` 中 `recommend()` 方法，在调用 `recommend_assignments()` 前加载任务记录并调用 `aggregate_task_history()` 构建 profile dict
- [x] 4.2 将聚合后的 task_history dict 传递给 `recommend_assignments()`

## 5. LLM 上下文补充

- [x] 5.1 修改 `pm_agent/agent_prompt.py` 中 `build_member_context()` 函数，新增 `task_history: dict[str, TaskHistoryProfile] | None` 参数
- [x] 5.2 在有任务历史的成员条目下追加摘要行："{name}: 任务历史: {total_tasks}条任务, {design_coding_tasks}条设计与编码, 主要模块: {top_module_path}"
- [x] 5.3 更新 `workflows.py` 中调用 `build_member_context()` 的位置，传入 task_history dict

## 6. 测试与验收

- [x] 6.1 为 `_member_score()` 新增测试用例：验证模块路径匹配加分、设计编码经验加分、故事匹配加分、估算准确度加分、缺陷率扣分
- [x] 6.2 为 `recommend_assignments()` 新增集成测试：传入 task_history 后验证推荐理由包含任务历史描述
- [x] 6.3 执行回归测试，确认无任务历史时推荐行为与之前一致（向后兼容）
- [x] 6.4 执行回归测试，确认推荐 API 接口行为不变
