## 1. 数据库 Schema 变更

- [ ] 1.1 创建 `workspaces` 表 DDL（id, workspace_id, title, created_at, updated_at）
- [ ] 1.2 创建 `chat_sessions` 表 DDL（session_id, workspace_id, created_at, last_active_at, status, last_message_preview）
- [ ] 1.3 创建 `chat_messages` 表 DDL（id, workspace_id, session_id, role, content, timestamp, parsed_requirements_json, seq）
- [ ] 1.4 创建 `requirements` 表 DDL（requirement_id, workspace_id, title, source, priority, raw_text, complexity, risk, requirement_type, source_url, source_message, payload_json, created_at）
- [ ] 1.5 创建 `session_requirements` 中间表 DDL（session_id, requirement_id）
- [ ] 1.6 移除所有关联表对 `workspace_states` 的 FK 约束（module_entries, managed_members, recommendations, confirmation_records, story_records, task_records, knowledge_update_records, insight_snapshots, import_batches）
- [ ] 1.7 更新 `schema.mysql.ddl.sql` 完整 DDL
- [ ] 1.8 更新 `database.py` 中 `_ensure_sqlite_schema()` 的建表语句

## 2. 数据迁移

- [ ] 2.1 编写迁移脚本：从现有 JSON payload 拆分写入新表（chat_sessions, chat_messages, requirements）
- [ ] 2.2 编写迁移脚本：验证新旧表数据一致性
- [ ] 2.3 在测试环境验证迁移脚本

## 3. Repository 层 — 新模块

- [ ] 3.1 实现 `ChatRepository`（create_session, archive_active_session, append_message, load_messages, list_sessions, delete_session）
- [ ] 3.2 实现 `RequirementRepository`（upsert_requirements, list_requirements, associate_session_requirements, clear_session_requirements）
- [ ] 3.3 实现 `WorkspaceMetaRepository`（get_workspace, update_workspace, create_workspace）

## 4. Repository 层 — 现有模块改造

- [ ] 4.1 为 `MemberRepository` 移除 `_save_managed_members_to_table` 中的 workspace_states 关联逻辑
- [ ] 4.2 为 `ModuleRepository` 移除 `_save_module_entries_to_table` 中的 workspace_states 关联逻辑
- [ ] 4.3 为 `RecommendationRepository` 移除 `_save_recommendations_to_table` 中的 workspace_states 关联逻辑
- [ ] 4.4 确认其他 Repository（knowledge_update, story, task, confirmation, insight, import_batch）不依赖 workspace_states

## 5. WorkspaceStore 重构

- [ ] 5.1 `WorkspaceStore` 引入各 Repository 依赖（chat, requirement, workspace_meta, member, module, recommendation）
- [ ] 5.2 重写 `load_workspace()` 为各 Repository 查询 + DTO 组装
- [ ] 5.3 移除 `save_workspace()` 的 JSON payload 序列化逻辑
- [ ] 5.4 `send_chat_message` 改为调用 `ChatRepository` + `RequirementRepository`
- [ ] 5.5 `create_chat_session` 改为调用 `ChatRepository`
- [ ] 5.6 `generate_recommendations` 改为调用 `RecommendationRepository`
- [ ] 5.7 移除 `_build_workspace_payload()` 和 `_build_workspace_payload_light()`

## 6. API 层适配

- [ ] 6.1 确认 `get_workspace` 返回结构不变（从 DTO 组装而非 JSON payload）
- [ ] 6.2 确认各 mutation 接口返回结构不变
- [ ] 6.3 移除 `api_service.py` 中对 `WorkspaceState.from_dict()` 的依赖

## 7. WorkspaceState 改为 DTO

- [ ] 7.1 移除 `WorkspaceState.from_dict()` 方法（不再从 JSON 反序列化）
- [ ] 7.2 `WorkspaceState` 保留为纯数据容器，各字段由各 Repository 返回数据组装
- [ ] 7.3 移除 `WorkspaceUpload` 从 JSON 序列化的路径

## 8. 清理

- [ ] 8.1 从 `database.py` 移除 `save_json` / `load_json` 相关方法
- [ ] 8.2 删除 `workspace_states` 表（MySQL + SQLite）
- [ ] 8.3 移除 `pm_agent/database.py` 中的 SQLite workspace_states 建表语句
- [ ] 8.4 运行全量测试验证

## 9. 验证

- [ ] 9.1 前端 `getWorkspace` 接口返回正确
- [ ] 9.2 聊天发送消息流程完整（创建会话 → 存储消息 → 返回）
- [ ] 9.3 需求解析流程完整
- [ ] 9.4 推荐生成流程完整
- [ ] 9.5 会话列表/切换/删除流程完整
- [ ] 9.6 运行 `pytest` 全量测试通过
