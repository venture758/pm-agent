## Context

当前平台同步模块（DeliveryView）是一个单页面，包含四个功能区块：上传与同步、故事/任务预览、同步批次明细、上传记录。故事和任务以两个表格形式堆叠在同一页面中，无法独立管理、筛选或导航。

技术栈：Vue 3 + Vue Router + Pinia，无子路由经验。当前 App.vue 的侧边栏导航是扁平的 7 个 step，"平台同步"是 Step 05。

## Goals / Non-Goals

**Goals:**
- 将故事和任务拆分为独立管理的子页面
- 在平台同步模块内部提供二级导航（标签页式）
- 每个子页面提供独立的搜索、筛选、操作能力
- 保持上传与同步作为该模块的入口页

**Non-Goals:**
- 不修改后端 API 或数据模型
- 不改变文件上传和同步的现有流程
- 不引入新的外部依赖

## Decisions

### 1. 二级导航采用内嵌标签页（Tab Bar），而非侧边栏嵌套

**Decision:** 在 DeliveryView 内部渲染一个水平标签栏（上传同步 | 故事管理 | 任务管理），不使用 Vue Router 子路由嵌套到侧边栏。

**Rationale:**
- 侧边栏已经是 7 个 step，再嵌套会显著增加视觉复杂度
- 标签页天然适合同一模块内的页面切换
- 保持 URL 结构简洁，无需 `/delivery/stories` `/delivery/tasks` 等多层路径
- 用 `ref` + `v-show` 控制子视图切换，无需路由配置改动

**Alternatives considered:**
- Vue Router 子路由：更正式但需要修改 router 和 App.vue 侧边栏逻辑，改动面大
- 下拉选择器：移动端友好但不如标签页直观

### 2. 故事和任务视图复用现有 handoff 数据，不新增 API 调用

**Decision:** 两个管理视图直接消费 `workspaceStore.workspace.handoff` 中的 stories 和 tasks 数据，在 store 层新增筛选和编辑 action。

**Rationale:** 后端已经返回完整的 handoff 数据，前端只需做本地过滤和就地编辑。

### 3. 父组件保持上传同步功能，子视图用 v-show 切换

**Decision:** DeliveryView.vue 作为容器组件，内部用三个子视图组件通过标签切换。不拆分为独立路由组件，而是作为内嵌子组件。

**Rationale:** 所有子视图共享同一个 handoff 数据源和上传上下文，内嵌组件减少数据传递复杂度。

## Risks / Trade-offs

- **[Risk]** 数据量大时，全部数据加载到前端后做筛选可能影响性能 → **Mitigation:** 使用 computed 属性做惰性过滤，Vue 的响应式系统会自动优化
- **[Risk]** v-show 切换三个视图会同时挂载到 DOM，内存占用增加 → **Mitigation:** 数据量可控（Excel 导入的故事/任务通常在数百条级别），如后续数据量增长可改为 v-if + keep-alive
- **[Trade-off]** 不使用子路由意味着 URL 不反映当前子视图状态，刷新后回到默认标签 → 可接受，因为用户在当前会话内切换频率高，跨会话恢复场景少
