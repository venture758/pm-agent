## Why

现有 Pipeline 在启动后默认逐步暂停等待人工确认，分析一条需求需要连续多次人工点击，流程成本高且不适合常规批量分析。需要把默认执行路径改为自动串行推进，仅在确实存在待确认结果或执行失败时暂停，让多数需求分析可以一次完成。

## What Changes

- 将 `/pipeline/start` 的默认模式改为自动执行，后端在后台连续推进 5 个分析节点
- 为 Pipeline 状态增加运行模式、运行状态、阻塞原因、运行实例标识和心跳时间，用于自动执行和恢复
- 自动模式遇到待确认节点时暂停，用户确认、修改、重分析或跳过后继续自动执行后续节点
- 前端 Intake 入口拆分为“自动分析”和“逐步确认”，并在自动模式下轮询状态、展示暂停原因和完成态摘要
- 保留手动逐步确认模式作为显式备用入口，兼容调试和精细干预场景

## Capabilities

### New Capabilities
- `pipeline-auto-execution`: Pipeline 支持默认自动执行、自动暂停与恢复续跑
- `pipeline-auto-execution-ui`: Intake 页支持自动分析入口、运行态轮询和暂停态交互

### Modified Capabilities

## Impact

- 修改 `backend-java/src/main/java/com/pmagent/backend/application/pipeline/PipelineService.java`，引入异步 runner 与新状态字段
- 修改 `backend-java/src/main/java/com/pmagent/backend/api/controller/WorkspacePipelineController.java`，扩展 `start` 请求契约
- 修改 `frontend/src/stores/workspace.js`、`frontend/src/views/IntakeView.vue`、`frontend/src/components/PipelinePanel.vue`、`frontend/src/components/ChatMessageBubble.vue`，适配自动模式 UI 和轮询
- 新增自动执行相关测试，覆盖后端状态机和前端 store/panel 行为
