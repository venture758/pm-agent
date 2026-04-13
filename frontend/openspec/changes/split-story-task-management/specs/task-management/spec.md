## ADDED Requirements

### Requirement: Task management sub-view
DeliveryView SHALL render a "任务管理" sub-view accessible via an inline tab bar. The view SHALL display all tasks from `workspaceStore.workspace.handoff.tasks` in an editable table with search and filter capabilities.

#### Scenario: Navigate to task management
- **WHEN** user clicks the "任务管理" tab in the delivery module
- **THEN** the task management sub-view is displayed showing all tasks

#### Scenario: Search tasks by keyword
- **WHEN** user enters a keyword in the task search input
- **THEN** the task list is filtered to show only tasks whose code, name, owner, or type matches the keyword (case-insensitive)

#### Scenario: Filter tasks by type
- **WHEN** user selects a task type from the type filter dropdown
- **THEN** the task list is filtered to show only tasks with the selected type

### Requirement: Task inline editing
The task management view SHALL allow inline editing of task fields including owner, task type, and planned person days. Changes SHALL be reflected in the workspace store's handoff data immediately.

#### Scenario: Edit task owner
- **WHEN** user modifies the owner field of a task and blurs the input
- **THEN** the updated value is persisted to `workspaceStore.workspace.handoff.tasks`

#### Scenario: Edit task planned person days
- **WHEN** user changes the planned person days of a task via the number input
- **THEN** the value is updated in the store and the table reflects the change

### Requirement: Task table display
The task table SHALL display the following columns: 任务编号 (task code), 任务名称 (name), 负责人 (owner), 类型 (type), 计划人天 (planned days). Each column SHALL be sortable by clicking the header.

#### Scenario: Display task data
- **WHEN** the task management view is rendered with handoff data
- **THEN** each task is shown as a row with code, name, owner, type, and planned days

#### Scenario: Empty task list
- **WHEN** there are no tasks in handoff data
- **THEN** an empty state message is displayed indicating no tasks exist
