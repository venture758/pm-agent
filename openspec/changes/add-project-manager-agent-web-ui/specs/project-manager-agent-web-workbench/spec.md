## ADDED Requirements

### Requirement: Web workbench provides a shared project-manager workspace
系统必须提供浏览器可访问的项目经理工作台，并在同一工作区内保存当前需求输入、成员信息、模块知识库状态、推荐结果、确认结果和最近一次同步摘要。

#### Scenario: Reopen an existing workspace after generating recommendations
- **WHEN** 用户在页面中录入需求并生成过分配推荐后再次进入该工作区
- **THEN** 系统恢复该工作区最近一次保存的需求、成员和推荐结果
- **THEN** 系统不要求用户重新录入已经保存在工作区中的数据

### Requirement: Web workbench uses a separated Vue frontend and backend API
系统必须采用前后端分离架构，前端使用 Vue 构建单页应用，后端提供独立 API 供工作区、推荐、确认、上传和监控查询调用。

#### Scenario: Load workspace data through backend API
- **WHEN** 用户打开 Vue 工作台中的某个工作区页面
- **THEN** 前端通过后端 API 获取该工作区的当前数据和状态摘要
- **THEN** 前端不依赖服务端模板直接渲染工作区页面

### Requirement: Web workbench supports requirement intake and recommendation generation from pages
系统必须允许用户通过页面录入群评审消息、导入需求数据或维护团队成员信息，并直接触发现有需求分析与分配推荐流程。

#### Scenario: Generate recommendations from chat-style requirement input
- **WHEN** 用户在工作台页面粘贴群评审需求列表并补充团队成员信息
- **THEN** 系统调用需求解析、阻塞识别和分配推荐流程生成结构化推荐结果
- **THEN** 页面展示每条需求的模块命中、推荐负责人、备选人、测试负责人、拆分建议和阻塞信息

### Requirement: Web workbench supports module knowledge-base file upload and status feedback
系统必须支持用户在页面中上传模块知识库 Excel 文件，并在导入后反馈导入结果、来源文件和更新后的知识库可用状态。

#### Scenario: Import a module knowledge-base file from the workbench
- **WHEN** 用户在工作台上传模块知识库 Excel 文件
- **THEN** 系统保存该文件并调用现有知识库导入流程更新模块知识库
- **THEN** 页面展示上传文件名、导入完成状态和可用于后续推荐的知识库摘要

### Requirement: Web workbench supports manager confirmation and platform handoff preview
系统必须允许项目经理在页面中对推荐结果执行采纳、改派、拆分需求和添加协作人等确认动作，并展示确认后的故事和任务落地预览。

#### Scenario: Adjust recommendation and preview platform handoff
- **WHEN** 项目经理在推荐结果页面修改某条需求的负责人并提交确认
- **THEN** 系统保存确认结果并生成与项目平台字段对齐的故事和任务预览数据
- **THEN** 页面展示变更后的负责人、动作记录和对应的故事/任务预览

### Requirement: Web workbench supports daily Excel sync and monitoring views
系统必须允许用户在页面上传故事列表和任务列表 Excel，并在导入完成后查看同步结果、执行预警和团队洞察。

#### Scenario: Review sync result and execution alerts after file upload
- **WHEN** 用户在工作台上传每日导出的故事 Excel 和任务 Excel
- **THEN** 系统执行离线同步并记录本次批次的新增或更新结果
- **THEN** 页面展示同步批次摘要、风险预警以及最新团队负载和单点依赖信息

### Requirement: Web workbench surfaces validation and blocker feedback inline
系统必须在页面交互中显式展示字段缺失、文件导入失败、技能缺口、容量不足和其他业务阻塞信息，不得把失败结果静默转换为成功状态。

#### Scenario: Show blockers when recommendation generation cannot fully assign work
- **WHEN** 用户提交的需求存在技能缺口或团队容量不足
- **THEN** 系统在页面中展示对应需求的阻塞原因和未分配说明
- **THEN** 系统保留用户输入内容，便于用户修正后再次生成推荐

### Requirement: Web workbench APIs return structured results for Vue state updates
系统必须为推荐生成、确认提交、文件上传和监控查询返回结构化响应，至少包含业务数据、校验错误、工作区标识和可供前端更新状态的操作结果。

#### Scenario: Update the Vue state after confirming assignments
- **WHEN** 项目经理在前端提交确认调整操作
- **THEN** 后端 API 返回确认后的分配结果、平台落地预览和相关工作区状态更新信息
- **THEN** 前端基于该结构化响应刷新页面而无需重新拼接业务字段
