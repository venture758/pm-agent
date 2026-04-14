## 1. 核心聚合函数

- [x] 1.1 在 `pm_agent/assignment.py` 中新增 `aggregate_workload_from_tasks(task_records: list[dict], members: list[MemberProfile]) -> dict[str, float]` 函数，按 owner 聚合未完成任务的 planned_person_days 总和，缺失 owner 回退到手动值
- [x] 1.2 为 `aggregate_workload_from_tasks()` 编写单元测试，覆盖有记录、无记录、已完成排除、空 owner 回退场景

## 2. 推荐评分集成

- [x] 2.1 修改 `pm_agent/assignment.py` 中 `recommend_assignments()` 函数签名，新增 `task_records: list[dict] | None = None` 参数
- [x] 2.2 在 `recommend_assignments()` 入口处调用 `aggregate_workload_from_tasks()` 构建 workload dict
- [x] 2.3 在评分循环中创建 MemberProfile 浅拷贝，覆盖 workload 字段后再传给 `_member_score()`

## 3. API 工作流集成

- [x] 3.1 修改 `pm_agent/api_service.py` 中 `generate_recommendations()`，在调用 `agent.recommend()` 时传入已加载的 task_records
- [x] 3.2 修改 `pm_agent/api_service.py` 中 `send_chat_message()`，在调用 `agent.parse_requirements_with_llm()` 时传入 task_records
- [x] 3.3 修改 `pm_agent/workflows.py` 中 `recommend()` 和 `parse_requirements_with_llm()` 函数签名，接收 task_records 参数

## 4. LLM 上下文更新

- [x] 4.1 修改 `pm_agent/workflows.py` 中 `parse_requirements_with_llm()`，在构建 member_context 前应用自动负载到成员 profile

## 5. 测试与验收

- [x] 5.1 为推荐评分集成编写测试：验证有任务记录时使用自动负载、无记录时使用手动值（AggregateWorkloadFromTasksTest 6 个用例）
- [x] 5.2 执行回归测试，确认无任务记录时推荐行为与之前完全一致（18 个测试全部通过）
- [x] 5.3 执行回归测试，确认推荐 API 接口行为不变（13 个 web_workbench 测试全部通过）
