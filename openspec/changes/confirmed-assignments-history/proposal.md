## Why

确认推荐后，分配记录仅保存在 `workspace_confirmation_records` 数据库表中，前端没有任何入口可查看历史确认记录。用户无法追溯过去的分配决策，也无法按时间或会话浏览确认结果。

## What Changes

- 新增 `GET /api/workspaces/:id/confirmations` API 接口，返回确认记录列表，支持分页（page/pageSize）
- 在 `WorkspaceStore` 中新增 `load_confirmation_records()` 方法，按 created_at 降序查询并分页
- 前端新增「确认历史」页面，以可展开表格展示每次确认的会话 ID、时间、条目数和详细分配记录
- 在 `workspace.js` store 和 `api/client.js` 中新增对应方法

## Capabilities

### New Capabilities
- `confirmation-history`: 分页查询已提交的确认记录，包括会话维度概览和单条分配明细

### Modified Capabilities
- 无

## Impact

- `pm_agent/workspace_store.py`: 新增 `load_confirmation_records()` 方法
- `pm_agent/api_service.py`: 新增 `list_confirmation_records()` 方法，注册到 HTTP 路由
- `frontend/src/api/client.js`: 新增 `listConfirmationRecords()` 请求
- `frontend/src/stores/workspace.js`: 新增 `loadConfirmationHistory()` action
- `frontend/src/views/ConfirmationHistoryView.vue`: 新增确认历史页面组件
- `frontend/src/App.vue`: 导航栏新增「确认历史」入口
