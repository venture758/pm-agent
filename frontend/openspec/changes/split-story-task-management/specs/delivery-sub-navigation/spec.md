## ADDED Requirements

### Requirement: Inline tab navigation in delivery module
DeliveryView SHALL render a horizontal tab bar at the top of the content area with three tabs: "上传与同步" (default), "故事管理", and "任务管理". The active tab SHALL be visually highlighted and switching tabs SHALL show the corresponding sub-view while hiding others.

#### Scenario: Default tab is upload & sync
- **WHEN** user navigates to the delivery module
- **THEN** the "上传与同步" tab is active by default and the upload/sync view is displayed

#### Scenario: Switch to story management
- **WHEN** user clicks the "故事管理" tab
- **THEN** the story management sub-view is displayed and the tab is highlighted as active

#### Scenario: Switch to task management
- **WHEN** user clicks the "任务管理" tab
- **THEN** the task management sub-view is displayed and the tab is highlighted as active

### Requirement: Tab bar visual design
The tab bar SHALL use a clean pill-style design consistent with the project's warm terracotta design language. The active tab SHALL use the primary terracotta color (#ba5c3d) background with white text. Inactive tabs SHALL use a light navy background with navy text.

#### Scenario: Active tab styling
- **WHEN** a tab is active
- **THEN** it displays with a terracotta background, white text, and subtle shadow

#### Scenario: Inactive tab styling
- **WHEN** a tab is inactive
- **THEN** it displays with a light background and navy text, with hover state on mouseover

### Requirement: Tab counts display
Each tab SHALL display a count badge showing the number of items in its view (stories count for story tab, tasks count for task tab). The upload & sync tab SHALL show a sync status indicator instead of a count.

#### Scenario: Display story count
- **WHEN** there are 5 stories in handoff data
- **THEN** the "故事管理" tab shows "故事管理 (5)"

#### Scenario: Display task count
- **WHEN** there are 12 tasks in handoff data
- **THEN** the "任务管理" tab shows "任务管理 (12)"
