## ADDED Requirements

### Requirement: Pipeline SHALL support auto execution mode by default
系统必须支持在启动 Pipeline 时指定执行模式，并且在未显式指定时默认使用自动执行模式。

#### Scenario: Start pipeline in auto mode by default
- **WHEN** 客户端调用 `POST /api/v2/workspaces/{workspaceId}/pipeline/start` 且未提供 `execution_mode`
- **THEN** 系统按 `execution_mode=auto` 创建新的 pipeline run
- **THEN** 返回结果包含 `run_id`、`execution_mode`、`run_status`、`current_step` 和步骤进度信息

#### Scenario: Start pipeline in manual mode explicitly
- **WHEN** 客户端调用 `POST /api/v2/workspaces/{workspaceId}/pipeline/start` 且提供 `execution_mode=manual`
- **THEN** 系统仅执行当前首个步骤
- **THEN** 返回结果标记为等待人工确认，而不自动推进后续步骤

### Requirement: Auto pipeline SHALL run steps in the background and persist progress
系统必须在自动模式下后台顺序执行全部 5 个节点，并在每一步完成后持久化当前步骤、步骤结果、历史记录和心跳时间。

#### Scenario: Auto pipeline continues through non-blocking steps
- **WHEN** 自动模式的当前步骤成功执行且结果不需要人工确认
- **THEN** 系统将当前步骤标记为完成并自动推进到下一步骤
- **THEN** `GET /pipeline/state` 返回最新持久化进度

#### Scenario: Auto pipeline completes final step
- **WHEN** 自动模式成功执行到 `knowledge_update` 且无需暂停
- **THEN** 系统将 `run_status` 标记为 `completed`
- **THEN** 系统清空 `current_step` 并保留完整步骤结果与历史记录

### Requirement: Auto pipeline SHALL pause on confirmation-required output
系统必须在自动模式命中需要人工确认的结果时暂停执行，并向前端暴露阻塞原因。

#### Scenario: Requirement parsing produces needs_confirmation result
- **WHEN** `requirement_parsing` 结果中任一需求的 `match_status` 为 `needs_confirmation`
- **THEN** 系统将 `run_status` 标记为 `awaiting_confirmation`
- **THEN** 系统在状态中返回 `awaiting_confirmation=true` 和 `blocking_reason`

#### Scenario: Later step explicitly requests confirmation
- **WHEN** 非首步骤结果显式返回 `requires_confirmation=true`
- **THEN** 系统暂停自动流程并保留当前步骤为活动步骤
- **THEN** 后续步骤不得继续执行，直到用户提交处理动作

### Requirement: Auto pipeline SHALL resume after user action on a paused step
系统必须允许用户在自动模式暂停后通过统一确认接口处理当前步骤，并在可继续时自动续跑后续节点。

#### Scenario: User confirms paused step
- **WHEN** 自动模式处于 `awaiting_confirmation` 且用户提交 `action=confirm`
- **THEN** 系统将当前步骤标记为完成
- **THEN** 系统恢复自动执行并继续推进后续步骤

#### Scenario: User modifies or skips paused step
- **WHEN** 自动模式处于 `awaiting_confirmation` 且用户提交 `action=modify` 或 `action=skip`
- **THEN** 系统更新当前步骤结果或跳过状态
- **THEN** 系统继续自动执行剩余步骤

#### Scenario: User reanalyzes paused step and result still blocks
- **WHEN** 自动模式处于 `awaiting_confirmation` 且用户提交 `action=reanalyze`
- **THEN** 系统重新生成当前步骤结果
- **THEN** 如果新结果仍要求人工确认，系统保持 `awaiting_confirmation` 状态且不推进后续步骤

### Requirement: Pipeline SHALL fail stale or broken auto runs safely
系统必须在自动模式执行失败或后台 runner 丢失时返回可恢复的失败状态，而不是无限停留在运行中。

#### Scenario: Background execution raises an exception
- **WHEN** 自动模式在执行任一步骤时发生异常
- **THEN** 系统将 `run_status` 标记为 `failed`
- **THEN** 系统在状态中保留失败原因和已完成步骤记录

#### Scenario: Running pipeline heartbeat expires
- **WHEN** `GET /pipeline/state` 发现自动模式的 `last_heartbeat_at` 超过允许超时时间且当前无活跃 runner
- **THEN** 系统将该 run 标记为 `failed`
- **THEN** 客户端后续查询不得再把该 run 视为运行中
