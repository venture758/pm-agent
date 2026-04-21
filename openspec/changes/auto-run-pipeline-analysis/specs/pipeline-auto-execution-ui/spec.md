## ADDED Requirements

### Requirement: Intake UI SHALL expose auto and manual pipeline entry points
系统必须在 Intake 聊天分析入口同时提供自动分析和逐步确认两种启动方式。

#### Scenario: User starts auto analysis
- **WHEN** 用户在聊天消息操作区点击“自动分析”
- **THEN** 前端以 `execution_mode=auto` 调用 Pipeline 启动接口
- **THEN** 打开 Pipeline 面板并展示自动运行状态

#### Scenario: User starts manual analysis
- **WHEN** 用户在聊天消息操作区点击“逐步确认”
- **THEN** 前端以 `execution_mode=manual` 调用 Pipeline 启动接口
- **THEN** Pipeline 面板立即展示当前步骤结果和人工操作按钮

### Requirement: Intake UI SHALL poll auto pipeline state while it is running
系统必须在自动模式处于排队或运行状态时自动轮询 Pipeline 状态，并在终态时停止轮询。

#### Scenario: Auto mode is queued or running
- **WHEN** Pipeline 状态为 `queued` 或 `running`
- **THEN** 前端按固定间隔调用 `GET /pipeline/state`
- **THEN** 面板根据返回状态更新当前步骤与结果展示

#### Scenario: Auto mode reaches terminal state
- **WHEN** Pipeline 状态变为 `awaiting_confirmation`、`completed` 或 `failed`
- **THEN** 前端停止轮询
- **THEN** 页面保留最后一次返回的状态供用户查看和操作

### Requirement: Intake UI SHALL distinguish running, paused, completed and failed auto states
系统必须在 Pipeline 面板中明确展示自动模式的运行态、暂停态、完成态和失败态，并在暂停态展示阻塞原因。

#### Scenario: Auto mode is running
- **WHEN** 面板收到 `run_status=running`
- **THEN** 显示“后台正在连续执行后续节点”等运行提示
- **THEN** 隐藏人工确认、修改、重分析和跳过按钮

#### Scenario: Auto mode pauses for confirmation
- **WHEN** 面板收到 `run_status=awaiting_confirmation` 且 `awaiting_confirmation=true`
- **THEN** 显示 `blocking_reason`
- **THEN** 恢复人工确认、修改、重分析和跳过按钮

#### Scenario: Auto mode completes or fails
- **WHEN** 面板收到 `run_status=completed` 或 `run_status=failed`
- **THEN** 显示完成摘要或失败提示
- **THEN** 不再展示运行中的 loading 状态

### Requirement: Intake UI SHALL refresh workspace data after auto pipeline completion
系统必须在自动模式完成后刷新工作区数据，以便页面展示最新分析结果。

#### Scenario: Auto pipeline completes
- **WHEN** 自动模式进入 `completed`
- **THEN** 前端提示分析完成并刷新当前 workspace 数据
- **THEN** 面板保留完成摘要，直到用户手动关闭
