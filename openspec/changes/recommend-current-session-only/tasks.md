## 1. 工作区会话模型扩展

- [x] 1.1 在 `workspace_models.py` 新增 `current_session_id` 与 `current_session_requirement_ids` 字段，并补充默认值与反序列化兼容
- [x] 1.2 在 `workspace_store.py` 验证新字段随 `workspace_states.payload` 正常持久化与加载
- [x] 1.3 为会话需求ID集合写入与读取统一使用 `normalize_requirement_id`

## 2. 输入链路维护当前会话需求集合

- [x] 2.1 在 `send_chat_message` 中将本次解析出的需求 ID 合并进当前会话集合（去重）
- [x] 2.2 在 `update_draft`（结构化输入）中重建会话上下文并覆盖当前会话集合
- [x] 2.3 在 `confirm_assignments` 成功后清空当前会话需求集合，防止跨会话残留

## 3. 推荐生成范围收敛

- [x] 3.1 在 `generate_recommendations` 中仅按当前会话集合过滤输入需求并生成推荐
- [x] 3.2 当当前会话集合为空时返回清晰错误提示，不回退到历史全量需求
- [x] 3.3 保证推荐删除、批量删除、确认流程继续基于统一需求ID规范工作

## 4. 测试与回归

- [x] 4.1 新增 service 层测试：历史需求与当前会话需求并存时只生成当前会话推荐
- [x] 4.2 新增 API 路由测试：当前会话为空时返回预期错误信息
- [x] 4.3 新增确认后测试：`current_session_requirement_ids` 被清空且下一轮需重新输入
- [x] 4.4 运行 `python3 -m unittest discover -s tests` 并修复回归
