## ADDED Requirements

### Requirement: Task history profile aggregation
The system SHALL aggregate task records from `workspace_task_records` into per-member `TaskHistoryProfile` objects containing: total task count, design-and-coding task count, task counts grouped by module_path, task counts grouped by story_code, average actual-vs-planned person days ratio, and total defect count.

#### Scenario: Aggregate task history for a workspace with task records
- **WHEN** the recommendation pipeline runs for a workspace that has task records in the database
- **THEN** each member who appears as `owner` in the task records gets a `TaskHistoryProfile` with aggregated statistics

#### Scenario: No task records exist for workspace
- **WHEN** the recommendation pipeline runs for a workspace with no task records
- **THEN** the task history profile dict is empty and the scoring proceeds without task history factors

### Requirement: Task history scoring factors
The system SHALL incorporate task history as additional scoring factors in `_member_score()`, applied on top of existing module-knowledge-based scoring.

#### Scenario: Member has task records in matched module path
- **WHEN** a member has N task records whose `module_path` partially matches the requirement's matched module key
- **THEN** the member receives +1 point per matching task record, capped at +3 total

#### Scenario: Member has design-and-coding experience
- **WHEN** a member has at least one task record with `task_type` containing "设计" or "编码"
- **THEN** the member receives +1 point

#### Scenario: Member has task records under related story
- **WHEN** a requirement has an associated story code and a member has task records under that story
- **THEN** the member receives +1 point

#### Scenario: Member has accurate effort estimation
- **WHEN** a member's `avg_actual_vs_planned` ratio is between 0.8 and 1.2
- **THEN** the member receives +0.5 points

#### Scenario: Member has high defect rate
- **WHEN** a member's `total_defects` exceeds `total_tasks * 2`
- **THEN** the member receives -1 point

### Requirement: Task history in recommendation reasons
The system SHALL append task-history-related reasons to the recommendation output's `reasons` list when task history contributes to a member's score.

#### Scenario: Task history contributes positive score
- **WHEN** a member's task history adds points to their score
- **THEN** the `reasons` list includes a description like "该成员在 '{module_path}' 模块有 N 条任务记录"

#### Scenario: Task history does not contribute
- **WHEN** a member has no task records or task history score is zero
- **THEN** no task history reason is added to the reasons list

### Requirement: Task history in LLM member context
The system SHALL include a task history summary line in the member context passed to the LLM for requirement parsing, when task history exists for that member.

#### Scenario: Member has task history
- **WHEN** building member context for the LLM and a member has task records
- **THEN** the context includes a line: "{name}: 任务历史: {total_tasks}条任务, {design_coding_tasks}条设计与编码, 主要模块: {top_module_path}"

#### Scenario: Member has no task history
- **WHEN** building member context for the LLM and a member has no task records
- **THEN** no task history line is included for that member
