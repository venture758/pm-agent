## ADDED Requirements

### Requirement: Delivery page SHALL not show upload-sync module
The system SHALL remove the `upload-sync` tab and its content panel from the delivery page UI.

#### Scenario: Tab list excludes upload-sync
- **WHEN** the user opens the delivery page
- **THEN** the tab list contains only `stories` and `tasks`
- **THEN** the page does not render a tab labeled "上传与同步"

#### Scenario: Upload-sync panel is not rendered
- **WHEN** the delivery page is rendered
- **THEN** no upload-sync form controls (story/task dual-file chooser and sync action button) are present in the DOM

### Requirement: Delivery page SHALL default to story management
The system SHALL set story management as the initial active tab after removing upload-sync.

#### Scenario: First load lands on stories
- **WHEN** the user enters the delivery page without tab state overrides
- **THEN** `stories` is the active tab
- **THEN** the story management panel is visible

### Requirement: Removal SHALL preserve backend compatibility
The system SHALL keep existing backend sync APIs callable during this change and SHALL scope changes to frontend module removal.

#### Scenario: Frontend module removed without API contract change
- **WHEN** this change is applied
- **THEN** no backend upload/sync endpoint is deleted or renamed as part of this change
- **THEN** frontend behavior changes are limited to tab structure and related UI state
