## Context

当前 `workspace_confirmation_records` 表已存储每次确认的记录（含 session_id、confirmed_count、payload_json、created_at），但没有任何 API 接口或前端页面可以查询这些数据。确认后的分配记录只对用户"消失"。

## Goals / Non-Goals

**Goals:**
- 新增分页查询 API，返回确认记录列表（含每条记录的分配明细）
- 前端新增「确认历史」页面，以可展开表格展示会话级概览和分配明细
- 支持按创建时间倒序排列

**Non-Goals:**
- 不修改确认记录的写入逻辑（仅新增读取接口）
- 不提供筛选、搜索功能（仅分页 + 倒序）
- 不改变 `ConfirmedAssignment` 的数据结构

## Decisions

### 1. API 接口设计

采用 `GET /api/workspaces/:id/confirmations?page=N&pageSize=N`，返回格式：

```json
{
  "workspace_id": "...",
  "items": [...],
  "page": 1,
  "page_size": 20,
  "total": 42,
  "total_pages": 3
}
```

**Alternatives considered:**
- POST 查询 → GET 更符合 REST 语义，且查询无副作用
- 将确认记录包含在 workspace payload 中 → 数据量大时会拖慢整个 workspace 加载

### 2. 数据库查询方式

在 `WorkspaceStore` 新增 `load_confirmation_records(workspace_id, page, page_size)`，使用 SQL `ORDER BY created_at DESC LIMIT/OFFSET` 分页。payload_json 反序列化后逐条返回。

SQLite 和 MySQL 均支持 LIMIT/OFFSET，无需差异化处理。

### 3. 前端页面形式

新建独立的 `ConfirmationHistoryView.vue` 页面，而非嵌入现有页面。理由：
- 确认历史是独立的用户旅程，与推荐确认页面职责分离
- 分页逻辑独立，不与其他页面的过滤/搜索状态耦合

### 4. 表格设计

一级行显示：确认时间、session ID、记录数量。展开后显示该次确认的所有分配明细（requirement_id、title、开发负责人、测试负责人、B角）。

## Risks / Trade-offs

- **[风险]** payload_json 包含完整 `ConfirmedAssignment` 对象，数据量可能较大 → **缓解**：分页默认 pageSize=20，用户仅展开感兴趣行
- **[风险]** 历史确认记录中的模块 key 可能已被删除 → **缓解**：前端仅展示记录中的快照数据，不反查当前模块状态
- **[权衡]** 不提供搜索/筛选 → 保持实现简洁，后续可按需添加
