## 1. Pipeline API 客户端方法

- [x] 1.1 在 `frontend/src/api/client.js` 中新增 3 个 Pipeline API 方法：
  - `startPipeline(workspaceId)` — `POST /api/workspaces/{id}/pipeline/start`
  - `getPipelineState(workspaceId)` — `GET /api/workspaces/{id}/pipeline/state`
  - `confirmPipelineStep(workspaceId, stepKey, action, modifications?, feedback?)` — `POST /api/workspaces/{id}/pipeline/confirm`，body: `{ step_key, action, modifications?, feedback? }`

## 2. Pipeline Store 状态管理

- [x] 2.1 在 `frontend/src/stores/workspace.js` 的 state 中新增 `pipelineState` 字段（初始为 `null`），结构包含：`status`, `current_step`, `step_progress`, `step_results`, `step_constraints`, `llm_stats`
- [x] 2.2 在 workspace store 的 actions 中新增 3 个方法：
  - `async startPipeline()` — 调用 `apiClient.startPipeline`，将结果存入 `pipelineState`
  - `async loadPipelineState()` — 调用 `apiClient.getPipelineState`，恢复 `pipelineState`
  - `async confirmPipelineStep(stepKey, action, options)` — 调用 `apiClient.confirmPipelineStep`，更新 `pipelineState`
- [x] 2.3 在 workspace store 中新增 `pipelineActive` computed getter（`pipelineState && pipelineState.status !== 'completed' && pipelineState.status !== 'cancelled'`）

## 3. PipelinePanel 组件

- [x] 3.1 创建 `frontend/src/components/PipelinePanel.vue`，包含：
  - Props: `pipelineState` (object)
  - Emits: `confirm`, `modify`, `reanalyze`, `skip`
  - 顶部：5 步进度条（需求解析 → 人员匹配 → 模块提炼 → 梯队分析 → 知识更新）
  - 中部：当前步骤的结果展示区域（根据 step key 分支渲染）
  - 底部：操作按钮区（确认、修改、重新分析、跳过）
- [x] 3.2 实现进度条组件：每步显示状态图标（✓ 已完成 / ▶ 当前步骤 / · 待处理），当前步骤显示 loading 动画和"分析中..."文字
- [x] 3.3 实现需求解析结果展示：表格形式，列：标题、优先级、复杂度、风险、所需技能
- [x] 3.4 实现人员匹配结果展示：卡片形式，字段：开发负责人、测试人、B角、协作人、推荐理由、置信度
- [x] 3.5 实现模块提炼结果展示：列表形式，字段：变更类型（新建大模块/新建子模块/更新负责人）、模块名称、变更理由
- [x] 3.6 实现梯队分析结果展示：单点风险列表（模块、风险成员、严重程度、建议）+ 成长路径列表
- [x] 3.7 实现知识更新结果展示：汇总统计（需求解析数、人员分配数、模块创建数、熟悉度更新数、风险识别数）+ 待执行变更列表

## 4. 操作交互

- [x] 4.1 实现确认按钮：调用 `confirmPipelineStep` with `action=confirm`（最后一步用 `action=execute`），成功后更新面板展示下一步结果
- [x] 4.2 实现修改按钮：弹出 Element Plus Dialog，展示当前步骤数据的可编辑表单，用户修改后调用 `confirmPipelineStep` with `action=modify` + modifications
- [x] 4.3 实现重新分析按钮：弹出 Element Plus MessageBox 输入框，用户输入反馈约束后调用 `confirmPipelineStep` with `action=reanalyze` + feedback
- [x] 4.4 实现跳过按钮：调用 `confirmPipelineStep` with `action=skip`
- [x] 4.5 Loading 状态处理：当 `step_results[current_step]` 为 pending 时，禁用所有操作按钮，当前步骤显示 loading 动画

## 5. IntakeView 集成

- [x] 5.1 在 `frontend/src/views/IntakeView.vue` 中导入 PipelinePanel 组件，在 main-area 右侧添加 PipelinePanel（桌面端），移动端为底部抽屉
- [x] 5.2 在 ChatView 的 LLM 回复消息中新增"启动 Pipeline 分析"按钮，点击后调用 `workspaceStore.startPipeline()`
- [x] 5.3 在 IntakeView 的 `onMounted` 中检查 `pipelineState` 是否存在，如果存在则自动调用 `loadPipelineState()` 恢复进度
- [x] 5.4 Pipeline 全部完成后，自动关闭面板并刷新 workspace 数据（调用 `loadWorkspace()`）
- [x] 5.5 为 IntakeView 添加响应式布局：桌面端 PipelinePanel 在右侧栏展示（宽 420px），移动端通过底部抽屉展示

## 6. 测试

- [x] 6.1 创建 `frontend/src/components/__tests__/PipelinePanel.test.js`，测试：
  - 进度条渲染（5 步，不同状态图标）
  - 各步骤结果展示（数据驱动）
  - 操作按钮触发（confirm/modify/reanalyze/skip）
  - Loading 状态（按钮禁用，loading 动画显示）
