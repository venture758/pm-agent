## ADDED Requirements

### Requirement: Agent provides a team load heatmap
系统必须基于当前分配结果、导出的故事和任务工作量以及成员可用容量生成团队负载热力图，以便项目经理识别过载和低利用成员。

#### Scenario: View current team load distribution
- **WHEN** 项目经理请求查看当前团队负载概览
- **THEN** 系统返回成员级负载热力图或等价的结构化负载摘要
- **THEN** 输出结果可以直接识别过载成员和低利用成员

### Requirement: Agent identifies single points of dependency
系统必须通过分析需求负责人集中度、稀缺技能覆盖情况、故事或任务负责人集中度以及协作模式识别单点依赖。

#### Scenario: Detect concentration risk on one specialist
- **WHEN** 多个关键需求或专业性需求依赖同一成员或稀缺技能
- **THEN** 系统标记单点依赖风险
- **THEN** 系统说明导致集中风险的需求、技能或成员

### Requirement: Agent supports capability growth suggestions
系统必须基于历史分配、技能缺口和依赖集中度给出能力成长建议，包括旁路学习、结对协作或分阶段接手等方式。

#### Scenario: Suggest growth path for a new team member
- **WHEN** 团队中存在有可用容量且具备相邻技能的新成员
- **THEN** 系统为其推荐适合练手的需求、结对机会或协作角色
- **THEN** 建议同时兼顾交付安全和能力成长目标

### Requirement: Agent maintains a module knowledge base
系统必须基于业务模块划分 Excel 建立模块知识库，至少记录大模块、功能模块、主要负责人、B角、成员熟悉程度、来源 sheet 和导入时间。

#### Scenario: Build module knowledge base from Excel
- **WHEN** 用户导入模块划分、模块负责人和熟练度 Excel
- **THEN** 系统创建或更新模块知识库条目
- **THEN** 每条知识库条目都保留来源 sheet、模块层级和成员熟悉度矩阵

### Requirement: Agent uses module ownership and familiarity in assignment
系统必须在需求分配时使用模块负责人、B角和成员熟悉程度作为重要决策因子，并在输出中体现命中的模块知识依据。

#### Scenario: Recommend owner based on module knowledge
- **WHEN** 某需求命中已有模块知识库中的功能模块
- **THEN** 系统优先考虑对应模块负责人、B角和高熟悉度成员
- **THEN** 系统在分配理由中说明命中的模块和知识库依据

### Requirement: Agent updates the module knowledge base after assignment
系统必须在每次需求分配完成后自动更新模块知识库中的分配历史、最近负责记录和熟悉度建议值。

#### Scenario: Refresh knowledge base after confirmed assignment
- **WHEN** 某条需求的分配结果被确认
- **THEN** 系统将该次分配写入对应模块知识库条目的历史记录
- **THEN** 系统更新相关成员的最近负责痕迹和熟悉度建议信息
