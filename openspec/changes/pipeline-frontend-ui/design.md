## Context

后端 Pipeline API 已实现 3 个路由：
- `POST /api/workspaces/{id}/pipeline/start` — 启动分析
- `GET /api/workspaces/{id}/pipeline/state` — 获取当前状态
- `POST /api/workspaces/{id}/pipeline/confirm` — 确认/修改/重分析/跳过步骤

前端 IntakeView 当前只有聊天对话框，发送消息后直接调用 `sendChatMessage`，用户在 chat 中收到 LLM 的文本回复。需要在此基础上增加 Pipeline 面板，让用户以逐步确认的方式管理需求分析流程。

## Goals / Non-Goals

**Goals:**
- 在 IntakeView 右侧/底部新增 PipelinePanel 组件，展示 5 步分析进度
- 用户在聊天中发送需求后，可选择"启动 Pipeline 分析"
- 每步展示结构化的建议数据（需求列表、人员分配、模块变更、梯队风险、待执行变更）
- 提供 4 种操作：确认、手动修改（内联编辑）、重新分析（弹出输入框）、跳过
- 全部步骤完成后，自动刷新 workspace 状态

**Non-Goals:**
- 不修改现有聊天对话功能
- 不实现推荐页面的改动（推荐页继续使用原有流程）
- 不涉及后端 API 改动（API 已就绪）

## Decisions

### 1. PipelinePanel 作为独立组件
PipelinePanel 独立于 ChatView，在 IntakeView 的右侧栏展示（桌面端）或底部抽屉展示（移动端）。这样聊天和 Pipeline 可以并行查看。

### 2. 触发方式
在 ChatView 的 LLM 回复消息下方新增"启动 Pipeline 分析"按钮。用户点击后调用 `start_analysis_pipeline`，Panel 自动展示第一步的结果。

### 3. 步骤结果展示
每步返回的数据格式不同，Panel 内部用 `v-if` 分支渲染：
- 需求解析：表格展示标题、优先级、复杂度、风险
- 人员匹配：卡片展示每条需求的开发/测试/B角分配
- 模块提炼：列表展示模块变更（创建/更新）
- 梯队分析：风险矩阵 + 成长路径
- 知识更新：汇总摘要 + 待执行变更列表

### 4. 状态管理
Pipeline 状态存储在 workspace store 中（`pipelineState` 字段），而非组件局部状态，确保路由切换后不丢失。

### 5. 手动修改采用弹窗而非行内编辑
行内编辑对于复杂数据结构（如人员匹配的多角色分配）过于复杂。使用弹窗展示 JSON 编辑器或表单，用户修改后提交。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| Pipeline 状态在 store 中，刷新页面后丢失 | 后端有持久化（通过 workspace），刷新后重新从后端加载 |
| 步骤数据复杂，渲染逻辑冗长 | Panel 内部拆分为 5 个子组件（各步专用的结果展示） |
| LLM 响应慢，用户等待焦虑 | 当前步骤显示 loading 状态和 LLM 降级提示 |
| 移动端屏幕空间不足 | 使用底部抽屉模式，可全屏展开 |
