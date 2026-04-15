## Context

当前 `WorkspaceState` 中 `chat_messages` 是单一列表，所有聊天记录无限累加。后端已有 `current_session_id` 和 `current_session_requirement_ids` 字段用于推荐范围控制，但没有多会话的消息存储能力。前端没有"新对话"或会话切换的 UI。

## Goals / Non-Goals

**Goals:**
- 用户能通过一键按钮开启全新需求对话，不受历史记录干扰
- 历史会话可回看、可切换，保留上下文追溯能力
- 后端支持多会话消息存储，通过 workspace JSON 持久化
- 推荐生成仅使用当前活跃会话的需求

**Non-Goals:**
- 不对聊天消息做服务端持久化迁移（仍存 workspace JSON）
- 不做消息级别的编辑/删除功能
- 不做跨 workspace 的会话管理
- 不做会话搜索/过滤（后续可扩展）

## Decisions

### Decision 1: 数据结构 — 扩展 WorkspaceState.chat_sessions

在 `WorkspaceState` 中新增 `chat_sessions` 字段，类型为 `list[ChatSession]`：

```python
@dataclass
class ChatSession:
    session_id: str          # "cs-" + uuid4().hex[:12]
    created_at: str          # ISO timestamp
    last_active_at: str      # ISO timestamp, updated on each message
    status: str              # "active" | "confirmed" | "archived"
    messages: list[dict]     # same structure as existing chat_messages
    requirement_ids: list[str]  # requirements parsed in this session
    last_message_preview: str = ""
```

向后兼容：保留 `workspace.chat_messages` 作为当前活跃会话消息的快捷引用（= `chat_sessions[last_active].messages`），确保旧代码不崩溃。

### Decision 2: 新会话创建在前端触发

"新对话" 按钮点击后，前端调用 `POST /api/workspaces/:id/chat/sessions` 创建新会话，然后切换到新会话。不在纯前端清空，确保后端状态一致。

### Decision 3: 活跃会话通过 active_session_id 标记

在 `WorkspaceState` 中新增 `active_session_id: str` 字段，指向 `chat_sessions` 中的当前活跃会话。加载 workspace 时，前端读取 `active_session_id` 并加载对应会话消息。

### Decision 4: 确认分配后自动创建新会话

`confirm_assignments()` 中，将当前 session 的 status 设为 "confirmed"，同时创建一个新 session 并设为 active。前端检测到状态变化后自动切换到新会话。

### Decision 5: 会话列表 UI 用侧边抽屉而非下拉

会话历史列表用侧边抽屉（drawer/sidebar）展示，因为：
- 可展示更多信息（时间、消息数、预览文字）
- 支持未来扩展（搜索、归档）
- 移动端可用 overlay 模式

### Alternatives Considered

**A. 前端本地创建新会话，延迟同步**
- 优点：响应更快
- 缺点：状态不一致风险（用户刷新/导航后丢失）
- 选择：不采用，后端优先

**B. 独立数据库表存储会话**
- 优点：查询效率更高，支持大规模
- 缺点：当前 workspace 数量小，增加复杂度
- 选择：不采用，workspace JSON 足够

## Risks / Trade-offs

[Workspace JSON 体积随会话增多而增大] → 会话列表只返回 metadata（不含 messages），messages 按需加载；超过 50 个会话时归档旧会话

[并发创建会话可能冲突] → 使用 session_id 作为唯一键，upsert 模式；前端加 loading 状态防止重复点击

[旧代码依赖 chat_messages 字段] → 保留 chat_messages 作为 active session messages 的别名，渐进迁移
