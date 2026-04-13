## ADDED Requirements

### Requirement: Agent recommends development owner, testing owner, backup owner, and split suggestions
系统必须基于需求特征和成员画像为每条需求生成分配建议，包括推荐开发负责人、测试负责人、备选人，以及在需要拆分时给出拆分建议。

#### Scenario: Recommend owners for pending requirements
- **WHEN** 用户提交需求列表和团队成员画像
- **THEN** 系统返回需求与推荐开发负责人、测试负责人、备选人的映射关系
- **THEN** 系统对过大或风险过高、不适合单人承接的需求给出拆分建议

### Requirement: Agent balances workload during assignment
系统必须在分配时考虑成员当前负载和可用容量，除非没有更优选择，否则不得将工作分配给预计负载超限的成员。

#### Scenario: Avoid overloading a specialist
- **WHEN** 某成员技能最匹配但可用容量已经不足
- **THEN** 如果存在其他足够胜任的成员，系统优先推荐其他成员
- **THEN** 如果仍必须分配给该成员，系统记录过载风险

### Requirement: Agent supports unassigned outcomes when no valid owner exists
系统必须在没有合适负责人的情况下允许需求保持未分配状态，并明确标记原因，而不是强行给出无效分配。

#### Scenario: Keep a requirement unassigned for missing skill coverage
- **WHEN** 没有团队成员满足需求所需角色或技能
- **THEN** 系统将该需求标记为未分配
- **THEN** 系统说明阻止分配的能力缺口或约束条件

### Requirement: Agent supports manager confirmation and manual adjustment
系统必须支持项目经理对分配建议进行确认和人工调整，包括采纳推荐、改派负责人、拆分需求和添加协作人。

#### Scenario: Confirm or adjust a recommended assignment
- **WHEN** 项目经理审核推荐分配结果
- **THEN** 系统支持记录采纳、改派、拆分和添加协作人等动作
- **THEN** 确认后的分配状态成为后续执行监控的基线

### Requirement: Agent produces story and task handoff data for the project platform
系统必须将确认后的分配结果映射为项目管理平台中的故事和任务结构，并保留需求标题、故事负责人、开发参与人、测试人员、优先级、计划时间和相关任务负责人等信息。

#### Scenario: Prepare handoff after review confirmation
- **WHEN** 项目经理确认评审后的分配结果
- **THEN** 系统输出与项目平台字段对齐的故事级和任务级记录
- **THEN** 输出结果足以直接用于创建或更新故事和任务，而无需再次人工解释原始群消息

### Requirement: Agent uses story and task codes as offline upsert keys
系统必须在处理人工导出的 Excel 数据时，使用 `用户故事编码` 作为故事记录的主 upsert 键，使用 `任务编号` 作为任务记录的主 upsert 键。

#### Scenario: Update an existing story or task from daily export
- **WHEN** 导入的 Excel 行中包含已存在于 Agent 状态中的故事编码或任务编码
- **THEN** 系统更新现有记录而不是创建重复记录
- **THEN** 系统保留最新导入的平台字段和同步时间戳
