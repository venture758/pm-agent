## Why

当前需求输入页面的聊天记录是单条无限增长的，用户无法开启新一轮需求对话。每次确认分配后，后端会清除 `current_session_id` 和 `current_session_requirement_ids`，但前端 `chat_messages` 列表永远不会清空，导致：

1. 用户无法直观地"重新开始"一轮需求输入
2. 历史聊天记录不可浏览，丢失了上下文追溯能力
3. 随着聊天增多，页面加载和消息渲染越来越重

需要实现"新对话"按钮：点击后清空当前聊天视图进入全新的对话，之前的聊天记录作为历史可回看。

## What Changes

- 在需求输入页面顶部新增 "新对话" 按钮
- 点击后：当前聊天清空，进入全新空白对话
- 历史对话以会话列表形式保留，可通过侧边栏或下拉切换回看
- 后端新增 `POST /api/workspaces/:id/chat/sessions` 接口创建新会话
- 后端新增 `GET /api/workspaces/:id/chat/sessions` 接口获取历史会话列表
- 后端新增 `GET /api/workspaces/:id/chat/sessions/:sid` 接口获取指定会话的聊天记录
- 每次确认分配后，自动创建新会话（隐式），但不强制清空前端聊天

## Capabilities

### New Capabilities
- `chat-sessions`: 多会话管理 — 支持在同一个 workspace 内创建、切换、浏览多个需求输入对话会话。包括新会话创建、历史会话列表获取、指定会话消息加载。

### Modified Capabilities
- `intake`（如有现有 spec）: 需求输入页面的 UI 交互增加 "新对话" 入口和历史会话切换

## Impact

- **前端**: `IntakeView.vue` / `ChatView.vue` 新增会话切换 UI；`workspace.js` store 新增会话相关 action；`client.js` 新增会话 API
- **后端**: `api_service.py` 新增 3 个会话 API 端点；`workspace_store.py` 可能需要扩展存储结构以支持多会话聊天
- **数据库**: `workspace_states` JSON 结构需扩展 `chat_sessions` 字段，存储多会话消息
