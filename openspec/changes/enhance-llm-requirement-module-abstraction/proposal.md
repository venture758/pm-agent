## Why

当前 LLM 需求解析结果主要聚焦需求标题与优先级，缺少可直接用于分配与追踪的模块归属信息。随着项目模块数量和历史任务数据增长，人工补录“大模块/功能模块”和手工抽象需求语义的成本明显上升，影响推荐链路效率与一致性。

## What Changes

- 在需求解析结果中新增模块归属字段，至少包含 `big_module`、`function_module`。
- 要求 LLM 在解析时结合业务模块知识库与历史任务名称上下文，输出模块匹配结论与抽象提炼后的需求表述。
- 明确不依赖历史数据中的 `module_path` 字段作为匹配依据（该字段质量不稳定），历史上下文仅使用更可靠的任务名称/故事名称等文本信号。
- 增加模块匹配证据字段（如命中关键词、参考任务名称、匹配置信度或理由），便于人工校验与回溯。
- 当无法高置信命中模块时，返回明确的“待确认”状态与候选模块，避免静默误匹配。
- 将上述结果接入现有需求持久化与后续推荐流程，确保前后端可读取与展示。

## Capabilities

### New Capabilities
- `llm-requirement-module-abstraction`: 让需求解析阶段基于模块知识和历史任务上下文输出模块归属与抽象提炼结果，并提供可审计的匹配依据。

### Modified Capabilities
- None.

## Impact

- Affected backend:
  - `backend-java` 需求解析服务（LLM prompt 组装、响应解析、降级策略）
  - 需求相关 API DTO 与返回结构（聊天解析、结构化需求入口）
  - 需求持久化模型与映射（如需新增字段）
- Affected frontend:
  - 需求录入/确认页面对新字段的展示与校验提示
- Affected data/contracts:
  - `/api/v2/workspaces/{workspaceId}/chat` 等解析相关接口契约
  - 与模块知识库、历史任务查询的上下文拼装逻辑
