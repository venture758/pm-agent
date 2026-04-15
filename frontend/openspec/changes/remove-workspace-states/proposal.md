## Why

`workspace_states` 表当前以 JSON 文档方式存储整个工作区的核心状态（对话、会话、需求、画像等），但这是一个单体聚合表——所有模块的 CRUD 都通过 `WorkspaceStore.save_workspace()` 统一写入同一个 JSON blob。这导致：

1. **边界模糊**：聊天模块、需求模块、交付模块的数据混在一个 JSON 里，职责不清晰
2. **写入放大**：任何模块的修改都会序列化整个工作区状态再写入
3. **无法独立演进**：某个模块要增加字段或拆分数据，必须修改整个 payload 结构
4. **查询低效**：虽然已有独立关联表，但 JSON payload 中仍存了冗余数据（如 `chat_sessions`、`normalized_requirements`）

## What Changes

- **移除 `workspace_states` 表**及其 JSON payload 存储机制
- **保留 `workspaces` 轻量元数据表**（仅 workspace_id + title + 更新时间）
- **每个模块独立管理自己的数据表**：
  - 聊天模块：`chat_sessions`、`chat_messages` 独立表
  - 需求模块：`requirements` 独立表
  - 交付模块：`stories`、`tasks` 独立表（已有，移除 FK）
  - 人员模块：`managed_members` 独立表（已有，移除 FK）
  - 模块知识模块：`module_entries` 独立表（已有，移除 FK）
  - 推荐模块：`recommendations` 独立表（已有，移除 FK）
  - 确认模块：`confirmation_records` 独立表（已有，移除 FK）
  - 知识更新模块：`knowledge_update_records` 独立表（已有，移除 FK）
  - 洞察模块：`insight_snapshots` 独立表（已有，移除 FK）
  - 导入模块：`import_batches` 独立表（已有，移除 FK）
- **移除所有关联表对 `workspace_states` 的外键引用**，改为独立 `workspace_id` 索引
- **`WorkspaceStore` 拆分为各模块专属 Repository**，各自负责自己的 CRUD
- **`WorkspaceState` 聚合类改为只读 DTO**，用于跨模块组装返回给前端

## Capabilities

### New Capabilities
- `workspace-core`: workspace 元数据表（workspace_id, title, created_at, updated_at）
- `chat-domain`: 聊天会话与消息的独立存储与 CRUD
- `requirement-domain`: 需求项的独立存储与 CRUD
- `insight-domain`: 团队洞察的独立存储

### Modified Capabilities
- `module-knowledge`: 移除 workspace_states FK，模块知识表独立
- `member-management`: 移除 workspace_states FK，成员表独立
- `recommendation-assignment`: 移除 workspace_states FK，推荐表独立
- `confirmation-records`: 移除 workspace_states FK，确认记录独立
- `story-delivery`: 移除 workspace_states FK，故事表独立
- `task-delivery`: 移除 workspace_states FK，任务表独立
- `knowledge-update`: 移除 workspace_states FK，知识更新记录独立
- `import-batch`: 移除 workspace_states FK，导入批次独立

## Impact

- **后端**：`workspace_store.py` 重构为多 Repository 模式，`WorkspaceState` 改为 DTO，`database.py` 的 JSON 存储方法废弃
- **数据库**：`workspace_states` 表删除，新增 `chat_sessions`、`chat_messages`、`requirements` 表，其余关联表移除 FK 约束
- **前端**：API 响应结构不变（轻量级 getWorkspace 已不再依赖 payload），但各 mutation 接口的返回数据由各模块接口自行组装
- **迁移**：需要将现有 JSON payload 中的数据拆分迁移到各独立表
