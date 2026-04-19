## Why

后端 Pipeline 多 Agent 架构（5 步子 Agent + Orchestrator + 3 个 API）已实现，但前端缺少对应的交互界面。当前 `/workspaces/{id}/intake` 页面只有聊天对话框，用户在发送需求后看到的是 LLM 的原始文本回复，无法按设计文档的流程逐步确认需求解析、人员匹配、模块提炼、梯队分析、知识更新等步骤。需要实现分析进度面板，让用户以辅助决策模式逐步审查和确认每一步的输出。

## What Changes

- 在 IntakeView 中新增**分析进度面板**：显示 5 个步骤的完成状态（已完成/当前/待处理）
- 在聊天消息后，用户触发"生成推荐"时自动启动 Pipeline，展示当前步骤的建议结果
- 为每一步提供 4 个操作按钮：确认（进入下一步）、手动修改、重新分析（输入反馈）、跳过
- 新增 Pipeline 相关的 API 调用方法到 workspace store
- 修改现有的推荐生成流程，改为 Pipeline 串行模式

## Capabilities

### New Capabilities

- `pipeline-frontend-ui`: 前端分析进度面板，包括步骤进度条、当前步骤建议展示、4 种操作按钮（确认/修改/重新分析/跳过）
- `pipeline-api-integration`: 前端与后端 Pipeline API 的集成，包括 start_pipeline、get_pipeline_state、confirm_pipeline_step 三个 API 调用

### Modified Capcapabilities

- `intake-chat-flow`: 现有的聊天对话流程中，生成推荐环节改为通过 Pipeline 串行执行，而非直接生成推荐列表

## Impact

- 新增: `frontend/src/components/PipelinePanel.vue` — 分析进度面板组件
- 修改: `frontend/src/views/IntakeView.vue` — 集成 PipelinePanel
- 修改: `frontend/src/stores/workspace.js` — 新增 pipeline API 调用方法
- 新增: `frontend/src/components/__tests__/PipelinePanel.test.js` — PipelinePanel 测试
- 后端 API 路由已存在（`/api/workspaces/{id}/pipeline/*`），前端只需对接
