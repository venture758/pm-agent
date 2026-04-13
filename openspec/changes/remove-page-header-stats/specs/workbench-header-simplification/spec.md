## ADDED Requirements

### Requirement: Workbench shell MUST omit global header metric cards
系统必须在项目经理工作台主内容区中移除首页头部的全局指标卡片区域，不再通过独立统计卡展示结构化需求数、推荐结果数、确认结果数或最新同步动作数。

#### Scenario: Open a workspace shell page
- **WHEN** 用户进入任意工作区页面并看到工作台主内容区
- **THEN** 页面不渲染全局 `metric-grid` 风格的头部统计卡片区域
- **THEN** 页面仍展示当前视图标题、工作区说明和必要状态标签

### Requirement: Business views MUST omit page-level summary stat cards
系统必须在需求输入、推荐确认、平台同步、执行监控和团队洞察等业务页面中移除页头或首屏的数字统计卡片模块，不得继续以成组卡片方式展示总数、分项数或最近批次等摘要。

#### Scenario: Open a business view with summary cards today
- **WHEN** 用户进入任一包含页头统计卡片的业务页面
- **THEN** 页面不再渲染 `mini-stat-grid` 或等价的数字摘要卡片模块
- **THEN** 页面正文中的表格、明细卡片、预览区和上传区保持可访问

### Requirement: Header simplification MUST preserve primary actions and readable layout
系统必须在移除统计模块后保留页面标题、主要操作按钮和关键说明信息，并确保页面首屏不会因为删除统计容器而出现明显空白占位或破损布局。

#### Scenario: Use a page after header stats are removed
- **WHEN** 用户打开已移除头部统计模块的页面
- **THEN** 用户仍可直接执行该页原有主操作，例如保存草稿、提交确认、执行同步、刷新预警或刷新洞察
- **THEN** 页面头部与正文之间的布局保持连贯，不出现专门为已删除统计模块保留的空白区域

### Requirement: Workbench shell MUST omit the shared workspace message panel
系统必须在工作台壳层中移除共享的“工作区消息”面板，不得在每个页面正文前统一插入消息列表、错误提示或消息计数模块。

#### Scenario: Open any workspace page after shell cleanup
- **WHEN** 用户进入任意工作区页面
- **THEN** 页面不渲染标题为“工作区消息”的共享消息面板
- **THEN** 页面直接展示当前视图的正文内容，而不是先展示系统消息列表模块
