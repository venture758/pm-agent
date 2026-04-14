# delivery-page-without-upload-sync Specification

## Requirements

### Requirement: Delivery page SHALL not show upload-sync module
The system SHALL remove the `upload-sync` tab and its content panel from the delivery page UI. The delivery page SHALL contain only `stories` and `tasks` tabs, both loading data via paginated server-side APIs.

#### Scenario: Tab list excludes upload-sync
- **WHEN** the user opens the delivery page
- **THEN** the tab list contains only `stories` and `tasks`
- **THEN** the page does not render a tab labeled "上传与同步"

#### Scenario: Upload-sync panel is not rendered
- **WHEN** the delivery page is rendered
- **THEN** no upload-sync form controls (story/task dual-file chooser and sync action button) are present in the DOM

### Requirement: Delivery page SHALL default to story management
The system SHALL set story management as the initial active tab after removing upload-sync. The story list SHALL load via the paginated `GET /api/workspaces/{id}/stories` endpoint, showing only the first page of results with pagination controls.

#### Scenario: First load lands on stories with pagination
- **WHEN** the user enters the delivery page without tab state overrides
- **THEN** `stories` is the active tab
- **THEN** the story management panel is visible
- **THEN** the story list displays the first page (default 20 items) with pagination controls
- **THEN** the page does NOT attempt to load all stories at once

#### Scenario: User can navigate story pages
- **WHEN** the user clicks a page number or next/prev button on the story list
- **THEN** the story list reloads with the corresponding page data
- **THEN** pagination controls update to reflect the new page position

### Requirement: Removal SHALL preserve backend compatibility
The system SHALL keep existing backend sync APIs callable during this change and SHALL scope changes to frontend module removal.

#### Scenario: Frontend module removed without API contract change
- **WHEN** this change is applied
- **THEN** no backend upload/sync endpoint is deleted or renamed as part of this change
- **THEN** frontend behavior changes are limited to tab structure and related UI state

### Requirement: Task list on delivery page SHALL use server-side pagination
The task list on the delivery page SHALL load via `GET /api/workspaces/{id}/tasks` with `page` and `pageSize` query parameters. The response SHALL include pagination metadata (`total`, `total_pages`, `page`, `page_size`). Client-side full-data filtering SHALL be replaced by server-side pagination with filter parameters.

#### Scenario: Task list loads paginated data on first render
- **WHEN** the user switches to the `tasks` tab
- **THEN** the task list requests `GET /api/workspaces/{id}/tasks?page=1&pageSize=20`
- **THEN** only 20 task records are displayed with pagination controls

#### Scenario: Task filtering resets to page 1
- **WHEN** the user changes a task filter (owner, status, or project_name)
- **THEN** the task list requests page 1 with the new filter parameters
- **THEN** pagination controls reset to reflect the filtered result set

#### Scenario: User can navigate task pages
- **WHEN** the user clicks a page number or next/prev button on the task list
- **THEN** the task list reloads with the corresponding page data
- **THEN** pagination controls update to reflect the new page position
