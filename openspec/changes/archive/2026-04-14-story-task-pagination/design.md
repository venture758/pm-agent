## Context

故事管理（stories）和任务管理（tasks）目前采用全量加载模式：

- **Stories**：`GET /api/workspaces/{id}` 在响应体 `handoff.stories` 中嵌入全部故事记录，通过 `load_story_records_from_table()` 无 LIMIT/OFFSET 查询
- **Tasks**：`GET /api/workspaces/{id}/tasks` 通过 `load_task_records_from_table()` 返回所有匹配记录，虽支持 `owner/status/project_name` 筛选但无分页
- **前端**：`DeliveryView.vue` 收到全量数据后，通过 `computed` 做 client-side 过滤和排序

当记录数达到几百条时，网络传输和前端渲染都成为性能瓶颈。

**技术栈约束**：
- 后端：WSGI dispatch router (`pm_agent/api.py`)，SQLite/MySQL 双支持
- 前端：Vue 3 + Pinia
- 已有分页模式：`confirmationHistory`（LIMIT/OFFSET + COUNT）、`ModuleManagementView`（默认 page_size=50）

## Goals / Non-Goals

**Goals:**
- 故事和任务列表改为服务端分页，每次只返回一页数据
- 保留现有筛选能力（筛选时重置到第 1 页）
- 遵循项目已有分页模式，保持 API 风格一致
- 默认 page_size=20（与确认历史一致）

**Non-Goals:**
- 不引入游标分页（OFFSET 模式足够）
- 不改变故事/任务的数据结构或字段
- 不改动其他消费 `GET /api/workspaces/{id}` 的客户端（如有）
- 不做虚拟滚动等前端优化（真分页后不需要）

## Decisions

### 1. 故事：从嵌入改为独立分页 API

**决策**：新增 `GET /api/workspaces/{id}/stories?page=&pageSize=` 独立分页接口

**理由**：
- 故事当前嵌入在 workspace 响应中，改造为独立接口更清晰，且可独立分页
- 原有 `GET /api/workspaces/{id}` 仍保留 `handoff.stories` 字段（向后兼容），但 DeliveryView 改用新分页接口
- 也可考虑直接在 workspace 接口加分页参数，但这会让 workspace 响应结构变得复杂

**替代方案**：在 workspace 接口加 `?include_stories=page&story_page=1` — 过于 hacky，不采纳。

### 2. 任务：在现有接口上扩展分页

**决策**：`GET /api/workspaces/{id}/tasks` 保持路径不变，新增 `page`/`pageSize` 查询参数，返回值增加 `total`/`total_pages` 等元信息

**理由**：
- 任务已有独立接口，只需扩展即可
- 保持 `owner/status/project_name` 筛选参数不变，与分页参数组合使用

### 3. 数据库层：统一 COUNT + LIMIT/OFFSET 模式

**决策**：每个分页查询执行两条 SQL：
1. `SELECT COUNT(*) FROM ... WHERE ...` — 获取总数
2. `SELECT * FROM ... WHERE ... ORDER BY ... LIMIT ? OFFSET ?` — 获取当前页

**理由**：
- 与 `load_confirmation_records()` 完全一致的模式
- SQLite 和 MySQL 都支持 COUNT 和 LIMIT/OFFSET
- 简单可靠，不需要子查询或窗口函数

### 4. 前端 Store：独立分页状态

**决策**：在 `workspace.js` 中新增 `storyPagination` 和 `taskPagination` 两个独立状态块，各自维护 `items/page/pageSize/total/total_pages`

**理由**：
- 与 `confirmationHistory` 模式一致
- 故事和任务独立翻页，互不干扰
- 筛选时重置 `page=1` 并重新请求

### 5. 前端组件：保留筛选+排序，改为服务端驱动

**决策**：
- 删除 `visibleStories` 和 `visibleTasks` 的 client-side 过滤 computed
- 筛选条件变化时调用 store action（带筛选参数 + page=1）
- 排序保留 client-side（当前页内排序），数据量小后性能无压力

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| 原有 `GET /api/workspaces/{id}` 的其他消费者依赖 `handoff.stories` 全量数据 | 保留原字段但为空数组或前 N 条，不删除字段 |
| 用户在筛选+翻页时可能迷路（不知道在哪一页） | 筛选时自动重置到第 1 页，UI 显示当前筛选条件 |
| COUNT 查询在大表上可能慢 | 当前数据量级不高（几百条），COUNT 开销可忽略；后续可加索引优化 |
| 前端路由不保留分页状态（刷新回到第 1 页） | 可接受；如需持久化可后续将 page 放入 URL query |
