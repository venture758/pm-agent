## 1. 后端数据模型扩展

- [x] 1.1 在 `pm_agent/models.py` 中新增 `ChatSession` dataclass，包含 session_id, created_at, last_active_at, status, messages, requirement_ids, last_message_preview 字段
- [x] 1.2 在 `pm_agent/models.py` 的 `WorkspaceState` 中新增 `chat_sessions: list[ChatSession]` 和 `active_session_id: str` 字段
- [x] 1.3 在 `pm_agent/workspace_store.py` 的 `save_workspace` 中确保新字段被序列化到 JSON
- [x] 1.4 在 `pm_agent/workspace_store.py` 的 `load_workspace` 中确保新字段从 JSON 反序列化（兼容旧数据无 chat_sessions 的情况）

## 2. 后端 API 端点

- [x] 2.1 在 `pm_agent/api_service.py` 中新增 `POST /api/workspaces/{id}/chat/sessions` — 创建新聊天会话
- [x] 2.2 在 `pm_agent/api_service.py` 中新增 `GET /api/workspaces/{id}/chat/sessions` — 列出所有会话（按 last_active_at 倒序，仅返回 metadata，不含 messages）
- [x] 2.3 在 `pm_agent/api_service.py` 中新增 `GET /api/workspaces/{id}/chat/sessions/{sid}` — 获取指定会话的完整消息列表
- [x] 2.4 在 `GET /api/workspaces/{id}` 响应中包含 `active_session_id` 和 `session_list`（metadata）
- [x] 2.5 修改 `POST /api/workspaces/{id}/chat` — 将新消息追加到 active session 的 messages 中，更新 last_active_at

## 3. 推荐范围与会话联动

- [x] 3.1 创建新会话时重置 `current_session_requirement_ids` 为空列表
- [x] 3.2 修改 `send_chat_message` 中需求注册逻辑，将新需求同时注册到 active session 的 requirement_ids
- [x] 3.3 修改 `generate_recommendations` 仅使用 active session 的 requirement_ids
- [x] 3.4 修改 `confirm_assignments` 中逻辑：将当前 session status 设为 "confirmed"，自动创建新 session 并设为 active

## 4. 前端 API 客户端

- [x] 4.1 在 `frontend/src/api/client.js` 中新增 `createChatSession(workspaceId, title?)` 方法
- [x] 4.2 在 `frontend/src/api/client.js` 中新增 `listChatSessions(workspaceId)` 方法
- [x] 4.3 在 `frontend/src/api/client.js` 中新增 `getChatSession(workspaceId, sessionId)` 方法
- [x] 4.4 在 `frontend/src/api/client.js` 中修改 `sendChatMessage` 支持可选 `session_id` 参数

## 5. 前端 Store

- [x] 5.1 在 `frontend/src/stores/workspace.js` 中新增 `chatSessions` 状态数组和 `activeSessionId` 状态
- [x] 5.2 在 `frontend/src/stores/workspace.js` 中新增 `createNewSession()` action
- [x] 5.3 在 `frontend/src/stores/workspace.js` 中新增 `switchSession(sessionId)` action
- [x] 5.4 在 `frontend/src/stores/workspace.js` 中新增 `loadSessions()` action
- [x] 5.5 修改 `applyWorkspace` 以同步 `active_session_id` 和 `chat_sessions` metadata

## 6. 前端 UI

- [x] 6.1 在 `IntakeView.vue` 顶部新增 "新对话" 按钮
- [x] 6.2 在 `IntakeView.vue` 中新增会话列表侧边抽屉（按时间倒序，显示创建时间、消息数、预览文字）
- [x] 6.3 实现点击会话切换消息列表的逻辑
- [x] 6.4 确认分配后自动切换到新会话（后端通知后前端响应）
- [x] 6.5 移动端适配：会话抽屉在窄屏下使用 overlay 模式

## 7. 验证

- [x] 7.1 验证新对话按钮功能：创建、切换、消息隔离
- [x] 7.2 验证页面刷新后会话列表和活跃会话正确恢复
- [x] 7.3 验证推荐生成仅使用当前会话的需求
- [x] 7.4 验证确认分配后自动创建新会话
