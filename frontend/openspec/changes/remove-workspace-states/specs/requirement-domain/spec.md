## ADDED Requirements

### Requirement: System MUST store requirements in a dedicated table
The system SHALL store parsed requirement items in a `requirements` table with columns for requirement_id, workspace_id, title, source, priority, raw_text, complexity, risk, and other fields from RequirementItem. Requirements are NOT stored in any JSON payload.

#### Scenario: Save parsed requirements
- **WHEN** requirements are parsed from a chat message
- **THEN** each requirement is upserted into the `requirements` table by requirement_id within the workspace

#### Scenario: List requirements for a workspace
- **WHEN** requirements are loaded for a workspace_id
- **THEN** all requirements are returned in insertion order

### Requirement: System MUST track session-to-requirements mapping
The system SHALL maintain a `session_requirements` table linking session_id to requirement_id, enabling per-session requirement scoping.

#### Scenario: Associate requirements with session
- **WHEN** new requirements are parsed in a session
- **THEN** the session_requirements table is updated with the session_id and each new requirement_id

#### Scenario: Clear session requirements on new conversation
- **WHEN** a new conversation session is created
- **THEN** no requirements are associated with the new session initially
