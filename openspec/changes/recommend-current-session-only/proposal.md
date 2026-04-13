## Why

当前“生成推荐”会基于工作区累计的全部 `normalized_requirements` 重新生成，导致历史会话中的旧需求也被重复推荐。用户在新一轮会话中只希望处理“本次输入”的需求，这个行为偏差会造成重复分配、误删和确认成本上升。

## What Changes

- 调整推荐生成范围：仅对“当前会话需求集”生成推荐，不再默认包含历史会话需求。
- 明确会话边界：在会话输入（聊天或结构化导入）时标记当前会话需求ID集合，生成推荐时按该集合过滤。
- 在空会话或会话需求无效时返回清晰错误提示，避免隐式回退到全量历史需求。
- 保持已确认分配、模块维护、人员维护行为不变。

## Capabilities

### New Capabilities
- `session-scoped-recommendations`: 推荐生成仅针对当前会话内需求，保证推荐结果与本轮输入一致。

### Modified Capabilities
- 无（当前 `openspec/specs/` 下无已发布能力需要做 delta）。

## Impact

- **后端服务**: `pm_agent/api_service.py` 的需求收集与 `generate_recommendations` 路径需要引入会话级过滤逻辑。
- **工作区模型与持久化**: `workspace_models.py`、`workspace_store.py` 需要增加“当前会话需求ID集合/会话标识”持久化字段。
- **输入链路**: 聊天录入与结构化导入在写入需求时需要同步更新会话集合。
- **测试**: 需新增“历史需求不参与当前推荐”的回归测试（service/api 层）。
