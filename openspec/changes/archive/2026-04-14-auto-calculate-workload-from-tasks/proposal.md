## Why

当前成员的 workload（负载）值完全依赖人员在管理页面手动维护，既不反映真实任务量，也容易过时或遗漏。系统中已经存在 `workspace_task_records` 任务明细表，包含每条任务的状态（计划/进行中/已完成）、负责人和计划人天。利用这些实际数据自动计算当前负载，可以使推荐评分中的可用容量判断更加准确，减少人为维护的负担。

## What Changes

- 新增 `compute_member_workload_from_tasks()` 函数：从 `workspace_task_records` 表按 owner 聚合，计算每个成员的当前负载 = sum(planned_person_days) for 未完成任务（状态 = "计划" 或 "进行中"）
- 在 `recommend()` 评分流程中，自动计算负载覆盖手动维护的 workload 值
- 在 `parse_requirements_with_llm()` 的成员上下文中，使用自动计算的负载替代手动值
- 保留手动维护 workload 的兜底逻辑：如果没有任务记录，回退到手动维护值
- **BREAKING**：`MemberProfile.workload` 的语义从"手动填写的负载"变为"从任务明细自动计算的负载（有兜底）"

## Capabilities

### New Capabilities
- `auto-workload-calculation`: 基于任务明细表未完成记录自动计算成员当前负载，包括数据聚合、状态过滤、手动兜底

### Modified Capabilities
- 无

## Impact

- `pm_agent/assignment.py`: 新增 `compute_member_workload_from_tasks()` 函数，在 `recommend_assignments()` 中应用自动负载
- `pm_agent/api_service.py`: 在 `generate_recommendations()` 和 `send_chat_message()` 中传入任务记录用于负载计算
- `pm_agent/workflows.py`: `recommend()` 和 `parse_requirements_with_llm()` 接收任务记录参数
- `pm_agent/agent_prompt.py`: `build_member_context()` 展示自动计算的负载值
- 前端人员管理页面可选保留手动 workload 维护入口，但优先级低于自动计算
