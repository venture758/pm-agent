## Context

当前后端在 `generate_recommendations` 时优先使用 `workspace.normalized_requirements`，该集合是历史累计数据。聊天模式下 `send_chat_message` 会将新解析需求追加到该集合，导致新一轮“生成推荐”会把旧需求再次带出。用户期望推荐范围严格限定在“当前会话需求”。

系统约束：
- 现有前端已基于 `POST /api/workspaces/:id/recommendations` 触发推荐，无额外会话参数。
- `WorkspaceState` 已持久化到 DB，允许新增字段并向后兼容旧数据。
- 推荐结果已拆分到 `workspace_recommendations` 表，不需要调整表结构来实现会话过滤。

## Goals / Non-Goals

**Goals:**
- 明确定义并持久化“当前会话需求集合”。
- 推荐生成仅使用当前会话需求，不回扫历史会话需求。
- 在聊天输入和结构化输入两条链路都能正确维护会话范围。
- 不破坏现有推荐确认、删除、批量删除流程。

**Non-Goals:**
- 不引入新会话管理页面或复杂会话列表查询。
- 不改动推荐算法评分逻辑（仅改输入范围）。
- 不清理历史 `normalized_requirements` 数据（保留审计与回溯能力）。

## Decisions

### 1. 新增会话级需求索引字段
- **Decision**: 在 `WorkspaceState` 增加 `current_session_id` 与 `current_session_requirement_ids`（去重后的需求 ID 列表）。
- **Rationale**: 用最小结构改动实现推荐范围控制，不依赖前端传额外参数。
- **Alternatives considered**:
  - 仅用时间窗口筛选“最近 N 分钟需求”：不稳定且不可测试。
  - 每次生成前清空历史需求：会丢失历史信息，不可接受。

### 2. 输入链路维护当前会话集合
- **Decision**:
  - 聊天消息解析成功后，将本次解析出的需求 ID 合并进 `current_session_requirement_ids`。
  - 结构化草稿更新（`update_draft`）视为开启新会话，重建 `current_session_id`，并以当前输入解析结果覆盖会话需求集合。
  - 推荐确认成功后清空 `current_session_requirement_ids`，避免下一轮误带旧需求。
- **Rationale**: 聊天是多轮增量输入，结构化导入是批量覆盖输入，两者语义不同。
- **Alternatives considered**:
  - 每条聊天消息都开启新会话：会丢失同一轮多消息累积能力。
  - 仅靠前端“新建会话”按钮控制：后端无法保证一致性。

### 3. 推荐生成严格按会话过滤
- **Decision**: `generate_recommendations` 在构建输入需求时，仅取 `normalized_requirements` 中 ID 命中 `current_session_requirement_ids` 的条目；若为空则返回明确错误。
- **Rationale**: 把“会话范围”约束收敛在服务端，避免前端状态错乱带来脏数据推荐。
- **Alternatives considered**:
  - 前端传 `requirement_ids` 到推荐接口：需要改 API 协议，兼容成本更高。

### 4. 统一需求 ID 规范化
- **Decision**: 继续沿用 `normalize_requirement_id`，在会话集合写入和匹配时统一处理 `2` / `2.0` / 字符串差异。
- **Rationale**: 避免范围过滤和删除链路再次出现 ID 不一致问题。
- **Alternatives considered**:
  - 仅在生成时临时转换：遗漏其他链路，风险高。

## Risks / Trade-offs

- [会话边界语义仍有业务理解差异] → 通过文案明确“结构化保存会开启新会话；聊天会在同会话内累积”。
- [历史 `normalized_requirements` 持续增长] → 本次不处理归档；后续可新增定期清理策略。
- [老数据无会话字段] → 读取时提供默认值，生成前做空集合检查并返回引导提示。

## Migration Plan

1. 在 `workspace_models.py` 扩展字段并提供默认值，保证旧数据可反序列化。
2. 在 `workspace_store.py` 持久化新字段（JSON payload 即可，无需新增表）。
3. 在 `api_service.py` 的 `send_chat_message` / `update_draft` / `confirm_assignments` 更新会话集合维护逻辑。
4. 在 `generate_recommendations` 改为按会话集合过滤需求。
5. 增加 service/api 测试：
   - 历史需求 + 当前会话需求并存时，仅生成当前会话推荐；
   - 会话集合为空时返回预期错误；
   - 推荐确认后会话集合清空。
6. 灰度验证后上线；若出现异常，回滚到上个版本（字段为向后兼容新增，不影响回滚）。

## Open Questions

- 是否需要显式“开始新会话”按钮（当前方案先用后端规则推导）？
- 会话集合是否需要在 API 返回中暴露给前端做可视化提示？
