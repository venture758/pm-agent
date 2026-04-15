## ADDED Requirements

### Requirement: Confirmation SHALL trigger a knowledge update run
系统 MUST 在用户提交确认后，为同一个 confirmation session 触发一次知识更新运行，并使用本次确认结果、当前模块知识摘要和最近确认历史作为输入上下文。

#### Scenario: Successful run after confirmation
- **WHEN** 用户提交确认且确认结果成功保存
- **THEN** 系统为该 `session_id` 启动一次知识更新运行，并生成知识更新结果记录

#### Scenario: LLM unavailable does not block confirmation
- **WHEN** 用户提交确认时 LLM 未配置或知识更新 Agent 被显式禁用
- **THEN** 确认提交 MUST 仍然成功，且知识更新记录状态为 `skipped`

#### Scenario: LLM response failure does not roll back confirmation
- **WHEN** 知识更新 Agent 调用失败或返回无法解析的响应
- **THEN** 确认提交 MUST 仍然成功，且知识更新记录状态为 `failed`

### Requirement: Knowledge update runs SHALL be persisted per session
系统 MUST 按 confirmation session 持久化知识更新运行结果，至少包含状态、摘要、结构化建议、错误信息和触发时间，并允许读取最近一次结果。

#### Scenario: Persist structured result for a session
- **WHEN** 某次确认对应的知识更新运行完成
- **THEN** 系统保存与该 `session_id` 关联的知识更新记录，包含 `knowledge_updates`、`optimization_suggestions` 和 `reply`

#### Scenario: Load latest result on workspace fetch
- **WHEN** 前端请求工作区详情
- **THEN** 返回 payload MUST 包含最近一次知识更新记录的摘要，若不存在则返回空值

### Requirement: Deterministic knowledge updates SHALL remain active
系统 MUST 在知识更新 Agent 运行成功、跳过或失败的所有情况下，继续执行现有的确定性模块知识更新逻辑。

#### Scenario: Deterministic update survives skipped LLM run
- **WHEN** 用户提交确认且知识更新 Agent 状态为 `skipped`
- **THEN** 模块知识库中的 `assignment_history`、`recent_assignees` 和 `suggested_familiarity` 仍然完成更新

#### Scenario: Deterministic update survives failed LLM run
- **WHEN** 用户提交确认且知识更新 Agent 状态为 `failed`
- **THEN** 模块知识库中的确定性更新结果仍然被保存

### Requirement: Confirmation center SHALL expose knowledge update status and summary
系统 MUST 在确认中心中展示最近一次知识更新摘要，并在确认历史中展示每个 confirmation session 对应的知识更新状态和摘要信息。

#### Scenario: Show latest knowledge update after confirmation
- **WHEN** 用户提交确认后重新加载工作区或停留在确认中心
- **THEN** 页面展示最近一次知识更新的状态、摘要和建议数量

#### Scenario: Show session-linked knowledge update in history
- **WHEN** 用户查看确认历史列表并展开某个 `session_id`
- **THEN** 页面展示该 session 对应的知识更新状态，以及可读的建议摘要或失败原因
