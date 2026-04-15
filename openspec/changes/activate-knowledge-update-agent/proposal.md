## Why

当前系统在“提交确认”后只执行规则式模块知识更新，LLM 知识更新 Agent 虽然已有 Prompt 和工作流函数，但没有接入确认链路，也没有持久化和展示出口。结果是“知识更新”能力只完成了一半，用户无法判断 Agent 是否触发、生成了什么建议、失败时发生了什么。

## What Changes

- 在确认提交成功后触发 LLM 知识更新流程，使用本次确认结果、模块知识摘要和最近确认历史生成知识更新建议
- 保留现有确定性规则更新作为基础行为；LLM 结果以“分析与建议”形式持久化，不阻塞确认提交成功
- 为每次知识更新建立与 confirmation session 关联的持久化记录，支持成功、跳过、失败三种状态
- 在工作区 payload 中返回最近一次知识更新摘要，并在确认历史中展示对应会话的知识更新状态与建议摘要
- 为知识更新 Agent 增加回归测试，覆盖成功、LLM 未配置、响应解析失败等场景

## Capabilities

### New Capabilities
- `knowledge-update-agent`: 在确认提交后触发、持久化并展示知识更新 Agent 的分析结果，包括状态、建议和会话关联

### Modified Capabilities
- 无

## Impact

- `pm_agent/workflows.py`: 将知识更新 Agent 从“仅定义方法”调整为确认后的实际调用链路
- `pm_agent/api_service.py`: 在确认提交后触发知识更新并返回最新摘要
- `pm_agent/workspace_models.py` / `pm_agent/models.py`: 新增知识更新记录模型
- `pm_agent/workspace_store.py` / 数据库表: 持久化知识更新记录并按 session 查询
- `frontend/src/stores/workspace.js` / `frontend/src/views/RecommendationsView.vue`: 展示最近一次知识更新结果与确认历史内的状态
- 测试：补充后端工作流、API、前端展示回归用例
