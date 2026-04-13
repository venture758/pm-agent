## Why

当前工作台首页和多个业务页在首屏放置了统计卡片，主内容区中还额外挂着“工作区消息”模块，导致用户进入页面后需要先跨过摘要与系统提示区才能看到实际操作区和明细内容。现在需要把这些头部辅助模块移除，让页面更聚焦在当前任务和主操作上，降低视觉噪音。

## What Changes

- 移除工作台首页头部的全局指标卡片区域，不再展示“结构化需求”“推荐结果”“确认结果”“最新同步动作”等汇总卡片。
- 移除各业务页面页头或首屏中的统计卡片模块，包括以 `mini-stat-grid` / `mini-stat-card` 形式展示的数字摘要区。
- 移除工作台主内容区中的共享“工作区消息”模块，不再在每个页面正文前插入统一的消息面板。
- 保留页面标题、说明文案、操作按钮、状态标签和正文内容面板，不把“移除统计模块”扩散成整块首屏重做。
- 清理仅用于头部辅助模块的前端计算属性、组件引用和样式，避免残留空白区域、无用状态计算或未使用样式。

## Capabilities

### New Capabilities
- `workbench-header-simplification`: 约束项目经理工作台在首页和各业务页面中不再渲染头部统计卡片或共享消息面板，并保持页面标题、主操作和详细内容区域可直接访问。

### Modified Capabilities
- None.

## Impact

- Affected code: `frontend/src/App.vue`、`frontend/src/components/MessagePanel.vue`、`frontend/src/views/IntakeView.vue`、`frontend/src/views/RecommendationsView.vue`、`frontend/src/views/DeliveryView.vue`、`frontend/src/views/MonitoringView.vue`、`frontend/src/views/InsightsView.vue` 以及相关样式文件 `frontend/src/assets/main.css`。
- APIs: 无接口契约变化，后端 API 与数据结构保持不变。
- Dependencies: 无新增依赖。
- Systems: 仅影响前端展示层和相关测试断言，不改变推荐、确认、同步、监控或洞察的业务流程。
