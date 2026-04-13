## Why

当前"平台同步"页面（DeliveryView）将故事列表和任务列表混合在同一页面中展示，随着数据量增长，页面变得臃肿且难以管理。用户希望在平台同步模块下新增二级菜单，将故事和任务拆分为独立的子页面，各自提供完整的增删改查、筛选和管理能力，使工作流更清晰。

## What Changes

- 将"平台同步"步骤扩展为带二级导航的子路由结构
- 新增"故事管理"子页面：独立的故事列表，支持搜索、筛选、编辑和状态管理
- 新增"任务管理"子页面：独立的任务列表，支持搜索、筛选、编辑和状态管理
- 保留原有的"上传与同步"入口作为二级菜单的第一项
- 原 DeliveryView 拆分为三个子视图 + 一个父级布局容器

## Capabilities

### New Capabilities
- `story-management`: 故事的独立管理页面，包含列表展示、搜索筛选、详情编辑
- `task-management`: 任务的独立管理页面，包含列表展示、搜索筛选、详情编辑
- `delivery-sub-navigation`: 平台同步模块的二级侧边导航结构

### Modified Capabilities
<!-- 无现有 spec 需要修改 -->

## Impact

- `frontend/src/views/DeliveryView.vue` — 拆分为父级布局容器
- `frontend/src/views/StoryManagementView.vue` — 新建
- `frontend/src/views/TaskManagementView.vue` — 新建
- `frontend/src/router/index.js` — 新增子路由配置
- `frontend/src/App.vue` — 二级导航在侧边栏内的展示适配
- `frontend/src/stores/workspace.js` — 可能需要扩展 handoff 数据的筛选和编辑 action
