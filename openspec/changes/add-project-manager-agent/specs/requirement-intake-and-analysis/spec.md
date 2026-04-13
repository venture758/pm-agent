## ADDED Requirements

### Requirement: Agent accepts requirement intake from import and chat
系统必须支持通过导入和聊天两种方式接收需求列表，并在生成分配建议前将其标准化为结构化需求项。

#### Scenario: Parse imported or conversational requirement input
- **WHEN** 用户通过文件导入或聊天对话提供需求列表
- **THEN** 系统返回标准化后的需求集合
- **THEN** 系统保留足够的结构化信息以支撑后续分析和分配

### Requirement: Agent parses review-group requirement list format
系统必须解析团队评审群中的需求列表格式，包括编号项、需求标题、需求链接和优先级标注。

#### Scenario: Parse product manager review message
- **WHEN** 产品经理在群里发送带有链接和优先级说明的编号需求列表
- **THEN** 系统为每个编号项提取一条结构化需求记录
- **THEN** 系统保留原始消息文本和需求链接以便追溯

### Requirement: Agent analyzes requirement type, complexity, and risk
系统必须在生成分配建议前识别每条需求的类型、复杂度和交付风险，并提取所需技能、截止约束和依赖线索。

#### Scenario: Analyze new requirements in the pending pool
- **WHEN** 有新需求进入待分配池
- **THEN** 系统为该需求给出类型、复杂度和风险判断
- **THEN** 系统记录影响这些判断的主要因素

### Requirement: Agent normalizes team member information into assignable profiles
系统必须将团队成员输入转换为可分配画像，包含角色、技能标签、经验水平、当前负载、可用容量和分配约束。

#### Scenario: Build member profiles from staffing input
- **WHEN** 用户提供包含技能和当前工作状态的成员信息
- **THEN** 系统返回结构化成员画像集合
- **THEN** 每个画像都包含足够的信息用于评估适配度和可分配性

### Requirement: Agent detects assignment blockers before matching
系统必须在匹配前识别分配阻塞项，包括需求属性缺失、容量不足、技能未知或依赖未解决，并在标准化结果中标记这些阻塞项。

#### Scenario: Detect missing staffing capacity
- **WHEN** 需求列表超过输入中描述的团队可用容量
- **THEN** 系统将该输入标记为存在分配阻塞
- **THEN** 系统指出是哪些需求或成员约束导致无法直接分配
