## 1. 数据库层 — 故事分页查询

- [x] 1.1 在 `pm_agent/workspace_store.py` 中新增 `load_story_records_paginated(workspace_id, page, page_size, keyword=None)` 方法，执行 COUNT(*) + SELECT LIMIT/OFFSET 两条 SQL，按 modified_time DESC, user_story_code 排序
- [x] 1.2 为 `load_story_records_paginated()` 编写单元测试，覆盖有记录、无记录、keyword 过滤、分页越界场景

## 2. 数据库层 — 任务分页改造

- [x] 2.1 在 `pm_agent/workspace_store.py` 中将 `load_task_records_from_table()` 改造为支持 `page`/`page_size` 参数，内部执行 COUNT(*) + SELECT LIMIT/OFFSET，保持可选的 `owner/status/project_name` 过滤
- [x] 2.2 为改造后的 `load_task_records_from_table()` 编写单元测试，验证分页 + 筛选组合场景

## 3. API 服务层

- [x] 3.1 在 `pm_agent/api_service.py` 中新增 `list_stories(workspace_id, page, page_size, keyword=None)` 方法，调用 `load_story_records_paginated()` 并返回分页响应格式
- [x] 3.2 修改 `pm_agent/api_service.py` 中 `get_tasks()` 方法，接受 `page/pageSize` 参数，调用改造后的 `load_task_records_from_table()` 并返回分页响应格式

## 4. API 路由层

- [x] 4.1 在 `pm_agent/api.py` 中新增 `GET /api/workspaces/:id/stories` 路由，解析 `page/pageSize/keyword` 查询参数
- [x] 4.2 修改 `pm_agent/api.py` 中 `GET /api/workspaces/:id/tasks` 路由，增加 `page/pageSize` 查询参数解析

## 5. 前端 API 与 Store

- [x] 5.1 在 `frontend/src/api/client.js` 中新增 `listStories(workspaceId, page, pageSize, keyword)` 方法，修改 `getTasks()` 增加分页参数
- [x] 5.2 在 `frontend/src/stores/workspace.js` 中新增 `storyPagination` 和 `taskPagination` 状态，新增 `loadStories(page, keyword)` 和 `loadTasks(page, filters)` action

## 6. 前端页面 — DeliveryView 改造

- [x] 6.1 在 `frontend/src/views/DeliveryView.vue` 中移除 `visibleStories` 和 `visibleTasks` 的 client-side 过滤 computed，改为从 store 分页状态直接渲染
- [x] 6.2 为故事列表添加分页控件（页码、上一页/下一页、总数），绑定 `loadStories()` action，筛选时重置 page=1
- [x] 6.3 为任务列表添加分页控件，绑定 `loadTasks()` action，筛选条件变化时重置 page=1

## 7. 测试与验收

- [x] 7.1 为 `GET /api/workspaces/:id/stories` 编写集成测试：默认分页、keyword 过滤、空记录、越界页
- [x] 7.2 为改造后的 `GET /api/workspaces/:id/tasks` 编写集成测试：分页参数、分页+筛选组合、越界页
- [x] 7.3 执行回归测试，确认推荐确认流程、确认历史等已有功能不受影响
