## ADDED Requirements

### Requirement: Workload aggregation from task records
The system SHALL aggregate task records from `workspace_task_records` by `owner`, computing each member's current workload as the sum of `planned_person_days` for tasks with status "计划" or "进行中".

#### Scenario: Calculate workload from incomplete tasks
- **WHEN** task records exist with owners and planned_person_days values
- **THEN** each owner's workload equals the sum of planned_person_days for their incomplete tasks

#### Scenario: Only planned and in-progress tasks count
- **WHEN** task records include tasks with status "已完成"
- **THEN** completed tasks are excluded from the workload calculation

#### Scenario: Members with no task records fall back to manual workload
- **WHEN** a member has no task records as owner
- **THEN** the member's manually maintained workload value is used

#### Scenario: Members with zero planned_person_days
- **WHEN** a member has task records but all have planned_person_days = 0 or null
- **THEN** the calculated workload is 0, and the manual fallback is not applied

#### Scenario: Empty owner field is skipped
- **WHEN** a task record has an empty or null owner
- **THEN** the record is excluded from aggregation

### Requirement: Auto-workload applied in recommendation scoring
The system SHALL apply auto-calculated workload to MemberProfile objects before running the recommendation scoring algorithm, replacing the manually maintained workload field.

#### Scenario: Scoring uses auto-calculated workload
- **WHEN** recommendation scoring runs with task records available
- **THEN** the available capacity calculation (capacity - workload) uses the auto-calculated value

#### Scenario: No task records falls back gracefully
- **WHEN** no task records exist for the workspace
- **THEN** recommendation scoring uses manually maintained workload values and behavior is identical to current

### Requirement: Auto-workload displayed in LLM member context
The system SHALL display auto-calculated workload in the member context passed to the LLM for requirement parsing.

#### Scenario: Context shows calculated workload
- **WHEN** building member context for the LLM and a member has auto-calculated workload
- **THEN** the context line shows the calculated value (e.g., "负载=1.5/1.0")
