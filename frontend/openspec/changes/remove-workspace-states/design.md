## Context

当前系统以 `workspace_states` 表为中心，所有模块数据（聊天、需求、成员、模块、推荐等）的读写都通过 `WorkspaceStore` 统一管理，以 JSON payload 序列化到单一表。虽然已逐步拆分出独立关联表（如 `workspace_managed_members`、`workspace_module_entries`），但核心状态仍混在 `workspace_states.payload` JSON 中，且 `save_workspace()` 每次调用都会全量序列化写入。

## Goals / Non-Goals

**Goals:**
- 移除 `workspace_states` 表及其 JSON 存储模式
- 各模块数据由各自独立表管理，模块间通过 `workspace_id` 关联
- 每个模块有自己的 Repository 类，负责专属 CRUD
- `WorkspaceState` 改为只读 DTO，仅用于聚合返回给前端
- 新增 `chat_sessions`、`chat_messages`、`requirements` 独立表

**Non-Goals:**
- 不改变 API 接口契约（前端无需感知后端存储重构）
- 不引入新的框架或中间件
- 不改变数据语义和业务逻辑

## Decisions

### 决策 1：用 Repository 模式替代单一 WorkspaceStore

**选择**：为每个模块创建独立 Repository 类（`ChatRepository`、`RequirementRepository`、`MemberRepository` 等），共享底层 `DatabaseStore` 连接。

**理由**：
- 每个 Repository 只负责一个领域的表，符合单一职责
- 共享 `DatabaseStore` 连接池，不增加基础设施复杂度
- `WorkspaceStore` 仍保留作为跨模块协调者，但只调用各 Repository 而非直接操作数据

**替代方案考虑**：
- 引入 ORM（SQLAlchemy）→ 过度工程，项目规模不需要
- 每个 Repository 独立管理连接 → 连接数爆炸，不合理

### 决策 2：保留轻量 `workspaces` 元数据表

**选择**：`workspaces` 表只存 `workspace_id`、`title`、`created_at`、`updated_at`，不含业务数据。

**理由**：
- 前端 App.vue 在切换 workspace 时仍需加载基础元信息
- 作为所有关联表的 FK 锚点，确保数据一致性

**替代方案考虑**：
- 完全删除 workspace 表，只靠 workspace_id 字符串 → 没有创建时间、更新时间追踪
- 用 Redis 存 workspace 元数据 → 增加依赖，无必要

### 决策 3：聊天模块拆为两张表

**选择**：
- `chat_sessions`：`session_id`、`workspace_id`、`created_at`、`last_active_at`、`status`、`last_message_preview`
- `chat_messages`：`id`、`workspace_id`、`session_id`、`role`、`content`、`timestamp`、`parsed_requirements_json`、`seq`

**理由**：
- 会话列表查询不需要加载消息内容（性能）
- 消息按 session 查询，`session_id` 索引即可
- `seq` 字段保证消息顺序

### 决策 4：需求表独立

**选择**：`requirements` 表存储所有已解析的需求项，按 `requirement_id` 去重。

**理由**：
- 需求项是当前 JSON payload 中最频繁修改的部分
- 独立表支持按 `requirement_id` 快速查询、更新、删除
- 会话的需求关联通过 `session_requirements` 中间表管理

### 决策 5：其余关联表移除 FK

**选择**：移除所有关联表对 `workspace_states` 的 FK 约束，改为 `workspace_id` 普通索引。

**理由**：
- `workspace_states` 将被删除，FK 必须移除
- 改为普通索引不改变查询行为
- CASCADE DELETE 语义由应用层保障（删除 workspace 时调用各 Repository）

**替代方案考虑**：
- FK 改为指向 `workspaces` 表 → 可以，但不如普通索引灵活（不需要级联删除约束）

### 决策 6：WorkspaceState 改为 DTO

**选择**：`WorkspaceState` 不再负责序列化和加载，只作为数据结构容器。所有加载逻辑在各 Repository 中。

**理由**：
- 避免 `WorkspaceState.from_dict()` 和 `asdict()` 的隐式 JSON 序列化
- Repository 返回强类型对象，DTO 在 Service 层组装

## Risks / Trade-offs

| 风险 | 缓解措施 |
|---|---|
| 数据迁移期间 JSON payload 与独立表不一致 | 迁移脚本先写新表，校验一致后再删除旧数据 |
| 跨模块组装 DTO 的性能（多个 Repository 查询） | 前端 `getWorkspace` 已轻量化，只返回核心字段 |
| `save_workspace()` 被 20+ 处调用，重构量大 | 分两步：先拆 Repository（保持 `save_workspace` 入口），再逐步消除调用 |
| SQLite 开发环境和 MySQL 生产环境双维护 | Repository 使用 `DatabaseStore` 占位符抽象，不直接写 SQL 字符串 |

## Migration Plan

1. **创建新表**：`workspaces`、`chat_sessions`、`chat_messages`、`requirements`、`session_requirements`
2. **数据迁移脚本**：从现有 JSON payload 拆分写入新表
3. **Repository 层**：逐个模块实现 Repository 类，替换 `WorkspaceStore` 中对应方法
4. **API 层验证**：确保所有接口返回结构与之前一致
5. **删除 `workspace_states`**：确认无残留引用后 DROP TABLE
6. **DDL 更新**：更新 `schema.mysql.ddl.sql` 和 `database.py` 的 SQLite 建表语句
