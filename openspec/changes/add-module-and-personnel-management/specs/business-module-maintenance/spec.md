## ADDED Requirements

### Requirement: Workbench MUST support manual maintenance of business module entries
系统必须允许用户在工作台中直接维护业务模块知识条目，不得仅依赖 Excel 导入作为唯一更新方式。

#### Scenario: Open the module maintenance view
- **WHEN** 用户进入业务模块维护页面
- **THEN** 系统展示当前工作区已有的模块条目列表
- **THEN** 用户可以直接发起新增、编辑或删除模块条目的操作

### Requirement: Business module maintenance MUST persist structured module knowledge fields
系统必须保存结构化的模块知识字段，至少包含大模块、功能模块、模块键、主要负责人、B角、成员熟悉度和来源信息。

#### Scenario: Save a module entry from the maintenance page
- **WHEN** 用户在页面中填写或编辑某个模块条目并提交保存
- **THEN** 系统以结构化方式保存该模块条目
- **THEN** 后续读取该条目时可以获得完整的模块负责人、B角和熟悉度信息

### Requirement: Business module maintenance MUST validate duplicate or invalid module data
系统必须在保存业务模块条目时校验重复模块键、缺失关键字段和非法成员映射，不得静默写入无效数据。

#### Scenario: Save a module entry with a duplicate key
- **WHEN** 用户保存的模块条目与现有条目使用相同模块键
- **THEN** 系统拒绝本次保存
- **THEN** 页面明确提示冲突原因，便于用户修正

### Requirement: Maintained module entries MUST be reusable by downstream recommendation flows
系统必须让页面维护后的模块知识条目成为推荐、洞察和知识库摘要的可复用输入，而不是只停留在维护页面展示。

#### Scenario: Generate recommendations after updating module ownership
- **WHEN** 用户在模块维护页面更新某功能模块的负责人后重新生成推荐
- **THEN** 系统在推荐过程中使用更新后的模块知识条目
- **THEN** 推荐结果和相关理由体现新的模块负责人或熟悉度依据
