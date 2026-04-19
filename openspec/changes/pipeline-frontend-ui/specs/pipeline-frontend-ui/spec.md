## ADDED Requirements

### Requirement: Pipeline 进度条展示
系统必须在 IntakeView 中展示分析进度条，包含 5 个步骤：需求解析、人员匹配、模块提炼、梯队分析、知识更新。每个步骤显示状态图标：已完成（✅）、当前步骤（▶️）、待处理（⬜）。

#### Scenario: 展示初始进度
- **WHEN** 用户启动 Pipeline 分析
- **THEN** 进度条显示 5 个步骤，第一步为"当前步骤"，其余为"待处理"

#### Scenario: 展示步骤完成状态
- **WHEN** 用户确认当前步骤后
- **THEN** 当前步骤标记为"已完成"，下一步标记为"当前步骤"

### Requirement: 当前步骤建议结果展示
系统必须根据当前步骤的类型，以结构化方式展示 LLM 返回的建议结果。

#### Scenario: 需求解析步骤展示
- **WHEN** 当前步骤为需求解析
- **THEN** 以表格形式展示每条需求的标题、优先级、复杂度、风险、所需技能

#### Scenario: 人员匹配步骤展示
- **WHEN** 当前步骤为人员匹配
- **THEN** 以卡片形式展示每条需求的开发负责人、测试人、B角、协作人、推荐理由、置信度

#### Scenario: 模块提炼步骤展示
- **WHEN** 当前步骤为模块提炼
- **THEN** 以列表形式展示模块变更：变更类型（新建大模块/新建子模块/更新负责人）、模块名称、变更理由

#### Scenario: 梯队分析步骤展示
- **WHEN** 当前步骤为梯队分析
- **THEN** 展示单点风险列表（模块、风险成员、严重程度、建议）和成长路径列表

#### Scenario: 知识更新步骤展示
- **WHEN** 当前步骤为知识更新
- **THEN** 展示汇总统计（需求解析数、人员分配数、模块创建数、熟悉度更新数、风险识别数）和待执行变更列表

### Requirement: 确认操作
用户确认当前步骤后，系统必须调用确认 API 进入下一步，并展示下一步的建议结果。

#### Scenario: 确认最后一步
- **WHEN** 用户在知识更新步骤点击确认
- **THEN** 调用确认 API（action=execute），关闭 Pipeline 面板，刷新 workspace 数据

#### Scenario: 确认中间步骤
- **WHEN** 用户在非最后一步点击确认
- **THEN** 调用确认 API（action=confirm），展示下一步的建议结果

### Requirement: 手动修改操作
用户可以对当前步骤的建议结果进行手动修改，修改后进入下一步。

#### Scenario: 修改需求解析结果
- **WHEN** 用户点击修改按钮并编辑需求条目
- **THEN** 调用确认 API（action=modify, modifications=编辑后的数据），进入下一步

#### Scenario: 修改人员匹配结果
- **WHEN** 用户点击修改按钮并调整人员分配
- **THEN** 调用确认 API（action=modify, modifications=修改后的数据），进入下一步

### Requirement: 重新分析操作
用户可以触发重新分析，输入反馈约束后 LLM 以新约束重新生成当前步骤的建议。

#### Scenario: 重新分析注入约束
- **WHEN** 用户点击重新分析并输入反馈（如"李祥这周不在"）
- **THEN** 调用确认 API（action=reanalyze, feedback=用户输入），重新执行当前步骤

### Requirement: 跳过操作
用户可以跳过当前步骤直接进入下一步。

#### Scenario: 跳过中间步骤
- **WHEN** 用户点击跳过按钮
- **THEN** 调用确认 API（action=skip），展示下一步的建议结果

### Requirement: Pipeline 状态持久化
Pipeline 状态在页面刷新或路由切换后必须保留。

#### Scenario: 刷新后恢复状态
- **WHEN** 用户在 Pipeline 中间步骤刷新页面
- **THEN** 重新从后端加载 Pipeline 当前状态，恢复进度条和当前步骤数据

### Requirement: Loading 状态
系统在 LLM 处理当前步骤时必须展示 loading 指示。

#### Scenario: 步骤执行中
- **WHEN** Pipeline 正在调用 LLM 执行某一步
- **THEN** 当前步骤显示 loading 动画和"分析中..."文字，操作按钮禁用
