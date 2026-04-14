/opsx:propose 故事管理，任务管理 列表数据量太大导致前端页面加载太卡，请采用真分页    ## Why

故事管理（stories）和任务管理（tasks）列表当前一次性加载全部数据，无分页机制。当 workspace 中故事/任务记录达到数百条时，前端页面渲染严重卡顿，用户体验下降。需要引入服务端分页，只加载当前页数据，降低网络传输和前端渲染压力。

## What Changes

- **故事列表**：新增独立分页查询 API，替代当前嵌入在 `GET /api/workspaces/{id}` 中的全量加载
- **任务列表**：改造现有 `GET /api/workspaces/{id}/tasks` 接口，在已有的 `owner/status/project_name` 筛选基础上增加 `page/pageSize` 分页参数，返回总数及分页元信息
- **数据库查询**：故事和任务查询均改为 `LIMIT/OFFSET` 模式，并额外提供 `COUNT` 查询获取总数
- **前端 DeliveryView**：将故事和任务的 client-side 全量过滤+渲染改为 server-side 分页加载，保留现有筛选能力（筛选时重置到第 1 页）
- **前端 Store**：新增故事和任务的分页状态管理，复用已有的 confirmationHistory 分页模式

## Capabilities

### New Capabilities
- `story-pagination`: 故事列表服务端分页能力，包括独立分页查询 API、分页状态管理、前端分页渲染

### Modified Capabilities
- `delivery-page-without-upload-sync`: 故事和任务列表的加载方式从全量改为分页，交付页面的交互模式发生变化（翻页/跳页替代全量滚动），但交付页面仍保留 stories 和 tasks 两个 tab 的核心功能不变

## Impact

- **Backend**: `pm_agent/workspace_store.py` 新增故事分页查询方法；`pm_agent/api_service.py` 修改 `get_tasks()` 增加分页返回值；`pm_agent/api.py` 新增故事分页路由、修改任务路由
- **Frontend**: `frontend/src/views/DeliveryView.vue` 重写数据加载逻辑；`frontend/src/stores/workspace.js` 新增分页状态和 action
- **API**: `GET /api/workspaces/{id}` 返回体中 `handoff.stories` 将不再包含全量故事（**BREAKING** — 但当前仅 DeliveryView 消费此字段，影响可控）；`GET /api/workspaces/{id}/tasks` 返回值结构增加分页元字段
