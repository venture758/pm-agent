## 1. 数据存储层

- [x] 1.1 在 `pm_agent/workspace_store.py` 中新增 `load_confirmation_records(workspace_id, page, page_size)` 方法，按 created_at 降序分页查询 workspace_confirmation_records 表
- [x] 1.2 为 `load_confirmation_records()` 编写单元测试，覆盖有记录、无记录、分页越界场景

## 2. API 服务层

- [x] 2.1 在 `pm_agent/api_service.py` 中新增 `list_confirmation_records(workspace_id, page, page_size)` 方法
- [x] 2.2 在 `pm_agent/api.py` 中新增 `GET /api/workspaces/:id/confirmations` 路由

## 3. 前端 API 与 Store

- [x] 3.1 在 `frontend/src/api/client.js` 中新增 `listConfirmationRecords(workspaceId, page, pageSize)` 方法
- [x] 3.2 在 `frontend/src/stores/workspace.js` 中新增 `loadConfirmationHistory()` action 及相关状态

## 4. 前端页面

- [x] 4.1 创建 `frontend/src/views/ConfirmationHistoryView.vue`，实现可展开表格 + 分页控件
- [x] 4.2 在 `frontend/src/App.vue` 导航栏中新增「确认历史」入口，在 `frontend/src/router/index.js` 中注册路由

## 5. 测试与验收

- [x] 5.1 为 API 接口编写集成测试：验证分页参数、空记录、越界页（3 个新测试用例）
- [x] 5.2 执行回归测试，确认现有推荐确认流程不受影响（16 个测试全部通过）
