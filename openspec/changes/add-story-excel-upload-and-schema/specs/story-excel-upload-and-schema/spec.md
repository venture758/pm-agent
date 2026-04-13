## ADDED Requirements

### Requirement: Story management supports standalone story Excel upload
The system SHALL provide a dedicated story-upload entry in the story management workflow and SHALL allow uploading a user-story Excel file without requiring a task Excel file.

#### Scenario: Upload story Excel only
- **WHEN** the user selects a valid story Excel file and submits upload from the story management page
- **THEN** the backend accepts a request containing only `story_file`
- **THEN** the system starts story import processing without validating presence of `task_file`

#### Scenario: Missing file is rejected
- **WHEN** the user submits the standalone story upload request without `story_file`
- **THEN** the system returns a 4xx validation error with a clear message

### Requirement: Story upload validates template headers before import
The system SHALL validate Excel headers against the canonical story template and SHALL reject import when required headers are missing or mismatched.

#### Scenario: Template headers match canonical format
- **WHEN** the uploaded Excel header row matches the canonical template format
- **THEN** the system continues row parsing and import

#### Scenario: Required header is missing
- **WHEN** the uploaded Excel file does not contain `用户故事编码`
- **THEN** the system aborts import and returns an error that includes missing header names

### Requirement: Database model is field-driven by story Excel template
The system SHALL define a structured database model for story records where canonical Excel fields are mapped one-to-one to persisted columns, and SHALL include workspace-level scoping metadata.

#### Scenario: Canonical fields are persisted as structured columns
- **WHEN** a story row is imported
- **THEN** each canonical Excel field value is persisted to its mapped database column
- **THEN** the record includes `workspace_id` and import timestamp metadata

#### Scenario: Header mapping is deterministic
- **WHEN** the same canonical header name appears in repeated imports
- **THEN** the system maps it to the same database column name in every import

### Requirement: Story import is idempotent by user story code
The system SHALL use `workspace_id + 用户故事编码` as the uniqueness key for upsert behavior.

#### Scenario: New story creates record
- **WHEN** an imported `用户故事编码` does not exist for the workspace
- **THEN** the system creates a new story record

#### Scenario: Existing story updates record
- **WHEN** an imported `用户故事编码` already exists for the workspace
- **THEN** the system updates the existing story record instead of creating a duplicate

### Requirement: Story import normalizes data types consistently
The system SHALL normalize known typed fields (date/time, numeric, text) into consistent storage formats and SHALL preserve nullability for empty cells.

#### Scenario: Date and numeric values are normalized
- **WHEN** the Excel row includes date/time cells and numeric cells
- **THEN** the system stores normalized values according to field type rules

#### Scenario: Empty optional fields remain empty
- **WHEN** optional Excel cells are empty
- **THEN** the system stores null or empty values according to schema definition without conversion errors

### Requirement: Import response includes summary and row-level errors
The system SHALL return an import summary including total rows, created count, updated count, failed count, and row-level failure reasons.

#### Scenario: Import partially succeeds
- **WHEN** some rows pass validation and some rows fail
- **THEN** the system imports valid rows
- **THEN** the response includes failure details for each rejected row

#### Scenario: Import fully succeeds
- **WHEN** all rows pass validation
- **THEN** the response shows failed count as zero and includes created/updated totals
