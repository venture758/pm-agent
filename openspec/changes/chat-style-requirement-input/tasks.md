## 1. 前端依赖引入

- [x] 1.1 安装 Element Plus 依赖（`npm install element-plus`）
- [x] 1.2 配置 Vite 按需引入（使用 Element Plus 组件级按需 import）

## 2. LLM 基础设施

- [x] 2.1 在 `pyproject.toml` 中新增 `openai>=1.0.0` 依赖
- [x] 2.2 在 `config.py` 中新增百炼配置常量（base URL、model、temperature、max_tokens、api_key 环境变量名）
- [x] 2.3 在 `pm_agent_web.py` 中支持通过环境变量传入 `--dashscope-api-key` 或读取 `DASHSCOPE_API_KEY`
- [x] 2.4 新建 `pm_agent/llm_client.py`：封装 OpenAI SDK 调用阿里云百炼，实现 `chat_completion(messages, temperature, max_tokens)` 方法
- [x] 2.5 在 `llm_client.py` 中实现重试逻辑（超时、RateLimit 错误自动重试 1 次）
- [x] 2.6 在 `llm_client.py` 中实现 JSON 响应解析器（从 LLM 返回文本中提取并解析 JSON，容忍 markdown code block 包裹）

## 3. 项目经理智能体 Prompt（三个子 Agent）

- [x] 3.1 新建 `pm_agent/agent_prompt.py`：定义统一的 System Prompt，包含三个 Agent 角色（需求理解、资源分配、知识更新）
- [x] 3.2 实现 Prompt 上下文构建函数（从 module_entries 构建 `module_context`，从 managed_members 构建 `member_context`，从负载构建 `load_snapshot`，从历史记录构建 `assignment_history`）
- [x] 3.3 实现 `parse_requirements_with_llm(user_message, module_context, member_context)` 函数：需求理解 Agent，组装 messages → 调用 LLM → 解析 JSON → 返回 `RequirementItem[]` + 自然语言回复
- [x] 3.4 实现 `generate_allocation_with_llm(requirements, member_context, load_snapshot)` 函数：资源分配 Agent，组合 LLM 建议与现有确定性评分算法
- [x] 3.5 实现 `update_knowledge_with_llm(confirmed_assignments, module_knowledge_summary, assignment_history)` 函数：知识更新 Agent，调用 LLM 获取优化建议并更新模块知识

## 4. 后端新增对话 API

- [x] 4.1 在 `api.py`（WSGI 路由）中新增 `POST /api/workspaces/:id/chat` 端点
- [x] 4.2 在 `api_service.py` 中新增 `send_chat_message()` 方法：调用 `parse_requirements_with_llm()`，更新 draft.chat_messages，追加 requirements
- [x] 4.3 在 `workspace_store.py` 中支持 `draft.chat_messages` 字段的持久化（JSON 序列化/反序列化）
- [x] 4.4 在 `workspace_models.py` 中更新 draft 数据模型，新增 `chat_messages` 字段
- [x] 4.5 确保 `getWorkspace` 返回时包含 `chat_messages` 历史

## 5. 前端 API 客户端与状态管理

- [x] 5.1 在 `api/client.js` 中新增 `sendChatMessage(workspaceId, message)` 方法
- [x] 5.2 在 `workspace.js` 中新增 `chatMessages` 状态字段
- [x] 5.3 在 `workspace.js` 中新增 `sendChatMessage` action（调用 API → 追加消息 → 更新 requirements）
- [x] 5.4 更新 `applyWorkspace` 以恢复对话历史

## 6. 聊天界面组件开发

- [x] 6.1 新建 `ChatInput.vue` 组件（`el-input` 输入框 + 发送按钮 + loading 状态）
- [x] 6.2 新建 `ChatMessageBubble.vue` 组件（用户气泡 / 智能体气泡，支持结构化需求展示）
- [x] 6.3 新建 `ChatView.vue` 组件（`el-scrollbar` 消息列表 + 自动滚动 + 欢迎引导）
- [x] 6.4 在 `IntakeView.vue` 中替换原有 textarea/表格区域为 `ChatView`
- [x] 6.5 保留底部"保存草稿"和"生成推荐"操作按钮
- [x] 6.6 添加消息发送的键盘快捷键（Enter 发送，Shift+Enter 换行）

## 7. 解析结果展示与兼容

- [x] 7.1 在智能体气泡中展示结构化解析结果（标题、优先级、风险、关联模块）
- [x] 7.2 保留"解析结果预览"面板，作为可折叠区域或使用快捷按钮触发
- [x] 7.3 确保 `generateRecommendations` 使用对话中已解析的结构化需求
- [x] 7.4 兼容现有 `draft.message_text` 和 `draft.requirement_rows` 字段（向后兼容）

## 8. 样式与体验优化

- [x] 8.1 聊天界面样式适配当前项目主题（暗色侧边栏 + 亮色内容区）
- [x] 8.2 消息发送时的 loading 动画（智能体"思考中"状态）
- [x] 8.3 空消息禁止发送 + 输入框自动聚焦
- [x] 8.4 对话区域使用 `el-scrollbar` 实现滚动，新消息自动滚动到底部

## 9. 测试与验证

- [x] 9.1 验证 LLM 调用连通性（API Key 配置正确，能收到 JSON 响应）
- [x] 9.2 验证单条需求发送 → LLM 解析 → 展示流程
- [x] 9.3 验证批量粘贴多条需求解析流程
- [x] 9.4 验证页面刷新后对话历史恢复
- [x] 9.5 验证"生成推荐"从聊天界面正常跳转
- [x] 9.6 验证空消息、特殊字符、超长消息、LLM 返回非 JSON 等边界情况
