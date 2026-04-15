## Context

当前确认提交流程是：

```text
confirm_assignments (api_service)
  -> self.agent.confirm(...)
    -> workflows.confirm(...)
      -> update_module_knowledge_after_assignment(...)
      -> save()
```

这条链路会更新 `assignment_history`、`recent_assignees` 和 `suggested_familiarity`，但不会触发 LLM 知识更新方法。`workflows.generate_knowledge_update_suggestions()` 已存在，却没有调用点，也没有持久化模型和 API/UI 出口。

系统同时存在两个约束：
- 提交确认是主链路，不能因为 LLM 不可用而失败
- 用户需要看到知识更新 Agent 是否真的执行，以及产出了什么

## Goals / Non-Goals

**Goals:**
- 在确认提交成功后自动触发知识更新 Agent
- 为每次运行记录 `session_id`、状态、结构化建议和摘要
- 在工作区和确认历史中暴露最近一次知识更新结果
- 保留现有规则式知识更新，确保 LLM 不可用时仍有基础知识沉淀

**Non-Goals:**
- 不引入新的异步任务系统、消息队列或独立 worker
- 不把 LLM 输出直接无审核写入 `familiar_members / aware_members / unfamiliar_members`
- 不建设完整的“知识更新运营后台”或批量审批页面

## Decisions

### 1. 执行策略：确认成功优先，知识更新为 best-effort side effect

确认提交流程继续先完成确定性确认和规则式知识库更新，再执行知识更新 Agent。知识更新运行结果不会改变确认接口的成功语义：

- 确认成功 + LLM 成功 -> `knowledge_update.status = success`
- 确认成功 + LLM 未配置 -> `knowledge_update.status = skipped`
- 确认成功 + LLM 调用/解析失败 -> `knowledge_update.status = failed`

这样可以确保“提交确认”不会因为外部模型服务而不可用，同时让失败可见、可追踪。

**Alternatives considered:**
- 引入异步队列后台执行 -> 架构更干净，但当前项目没有 worker 基础设施，超出本次范围
- 把知识更新放在确认前置步骤 -> 会把 LLM 可用性引入主流程，风险过高

### 2. 数据模型：新增 append-only 知识更新记录，并在工作区维护最新摘要

新增 `KnowledgeUpdateRecord` 模型，字段至少包括：
- `workspace_id`
- `session_id`
- `status` (`success | skipped | failed`)
- `triggered_at`
- `reply`
- `knowledge_updates`
- `optimization_suggestions`
- `error_message`

持久化采用两层结构：
- append-only 记录表：用于历史查询、审计和与确认记录联查
- `WorkspaceState.latest_knowledge_update`：用于页面首屏直接展示最近一次结果，避免每次额外查询

**Alternatives considered:**
- 只写 `workspace_states` JSON -> 最新结果可见，但没有按会话追溯能力
- 只扩展 `workspace_confirmation_records.payload_json` -> 勉强可用，但知识更新记录难以独立分页/查询，语义混杂

### 3. 结果语义：确定性更新继续直接写入，LLM 输出作为建议记录

保留 `update_module_knowledge_after_assignment()` 的当前职责，继续同步更新：
- `assignment_history`
- `recent_assignees`
- `suggested_familiarity`

知识更新 Agent 负责补充：
- 模块补全建议
- 熟悉度调整建议摘要
- 单点风险/负载平衡/流程优化建议

LLM 建议默认持久化为“建议结果”，不直接改写 canonical familiarity group，避免模型误判造成静默污染。

**Alternatives considered:**
- 直接把 LLM 输出写入模块熟悉度分组 -> 体感最强，但误更新代价高，且当前没有审核机制

### 4. API 暴露：工作区返回最近摘要，确认历史返回会话级状态

后端新增两个暴露面：
- `getWorkspace` payload 中加入 `latest_knowledge_update`
- 确认历史列表/详情返回每个 `session_id` 对应的知识更新状态和摘要计数

这样前端能同时满足：
- 提交后立即看到最近一次结果
- 在“确认历史”里追踪某次确认是否生成知识更新建议

### 5. 前端呈现：确认中心承担主展示，避免再分散入口

知识更新结果放在已有“确认中心”中展示：
- 推荐确认页签：提交成功后展示最近一次知识更新摘要卡片
- 确认历史页签：每个历史 session 展示知识更新状态，展开后查看建议摘要

不新增独立一级导航，继续保持“确认中心”作为确认与回收分析的统一入口。

## Risks / Trade-offs

- **[风险]** 知识更新在确认请求内执行会增加接口耗时 -> **缓解**：限定单次上下文长度，仅取最近 N 条历史；捕获异常并快速返回失败状态
- **[风险]** LLM 返回不稳定 JSON，导致结构化字段缺失 -> **缓解**：保留原始 `reply` 摘要和错误状态，结构化字段失败时写空对象
- **[风险]** 旧 workspace 无知识更新记录 -> **缓解**：读取时默认 `latest_knowledge_update = null`，历史接口返回无状态占位
- **[权衡]** 不直接自动应用 LLM 建议会让“生效感”弱一些 -> **有意为之**：优先可追踪、可解释，避免错误建议污染知识库

## Migration Plan

1. 新增知识更新记录存储结构和数据模型
2. 在确认提交流程中接入知识更新 Agent，写入 append-only 记录和最新摘要
3. 扩展工作区 payload 与确认历史接口
4. 在确认中心展示最近摘要和历史状态
5. 对已有 workspace 保持兼容：没有历史记录时显示“暂无知识更新记录”

回滚策略：
- 若新流程异常，可停用知识更新调用，仅保留已有确定性更新逻辑
- 已写入的知识更新记录保留，不影响确认记录和模块知识库读取

## Open Questions

- 确认历史页是否需要展示完整 `optimization_suggestions` 文本，还是先展示摘要计数和 `reply`
- 后续是否需要“采纳建议”操作，把某条知识更新建议显式应用到模块知识库
