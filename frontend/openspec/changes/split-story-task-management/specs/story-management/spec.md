## ADDED Requirements

### Requirement: Story management sub-view
DeliveryView SHALL render a "故事管理" sub-view accessible via an inline tab bar. The view SHALL display all stories from `workspaceStore.workspace.handoff.stories` in an editable table with search and filter capabilities.

#### Scenario: Navigate to story management
- **WHEN** user clicks the "故事管理" tab in the delivery module
- **THEN** the story management sub-view is displayed showing all stories

#### Scenario: Search stories by keyword
- **WHEN** user enters a keyword in the story search input
- **THEN** the story list is filtered to show only stories whose code, name, owner, or tester matches the keyword (case-insensitive)

#### Scenario: Filter stories by priority
- **WHEN** user selects a priority level from the priority filter dropdown
- **THEN** the story list is filtered to show only stories with the selected priority

### Requirement: Story inline editing
The story management view SHALL allow inline editing of story fields including owner, tester, and priority. Changes SHALL be reflected in the workspace store's handoff data immediately.

#### Scenario: Edit story owner
- **WHEN** user modifies the owner field of a story and blurs the input
- **THEN** the updated value is persisted to `workspaceStore.workspace.handoff.stories`

#### Scenario: Edit story priority
- **WHEN** user changes the priority of a story via the dropdown
- **THEN** the priority is updated in the store and the table reflects the change

### Requirement: Story table display
The story table SHALL display the following columns: 编码 (code), 名称 (name), 负责人 (owner), 测试 (tester), 优先级 (priority). Each column SHALL be sortable by clicking the header.

#### Scenario: Display story data
- **WHEN** the story management view is rendered with handoff data
- **THEN** each story is shown as a row with code, name, owner, tester, and priority

#### Scenario: Empty story list
- **WHEN** there are no stories in handoff data
- **THEN** an empty state message is displayed indicating no stories exist
