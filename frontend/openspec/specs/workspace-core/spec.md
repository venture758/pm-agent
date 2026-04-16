## ADDED Requirements

### Requirement: System MUST store workspace metadata independently
The system SHALL maintain a `workspaces` table containing only workspace identity and timestamps, with no business data stored as JSON payload.

#### Scenario: Create new workspace
- **WHEN** a new workspace is initialized with a workspace_id and title
- **THEN** a single row is inserted into `workspaces` with workspace_id, title, created_at, and updated_at

#### Scenario: Update workspace title
- **WHEN** a workspace title is updated
- **THEN** only the `workspaces` table row is updated, no JSON serialization occurs

### Requirement: Workspace metadata MUST NOT contain business data
The `workspaces` table SHALL only contain `workspace_id`, `title`, `created_at`, and `updated_at` columns. All business data MUST be stored in dedicated domain tables.

#### Scenario: Loading workspace metadata
- **WHEN** workspace metadata is loaded by workspace_id
- **THEN** the returned data contains only workspace_id, title, created_at, and updated_at
