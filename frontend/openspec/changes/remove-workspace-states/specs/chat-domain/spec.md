## ADDED Requirements

### Requirement: System MUST store chat sessions in a dedicated table
The system SHALL store chat session metadata in a `chat_sessions` table independent of any JSON payload. Each session contains session_id, workspace_id, timestamps, status, and last_message_preview.

#### Scenario: Create chat session
- **WHEN** a new chat session is created for a workspace
- **THEN** a row is inserted into `chat_sessions` with session_id, workspace_id, created_at, last_active_at, and status="active"

#### Scenario: Archive a chat session
- **WHEN** a new session is created and a previous active session exists
- **THEN** the previous session's status is updated to "archived" before inserting the new session

#### Scenario: List sessions for a workspace
- **WHEN** sessions are listed for a workspace_id
- **THEN** sessions are returned ordered by last_active_at DESC

### Requirement: System MUST store chat messages in a dedicated table
The system SHALL store individual chat messages in a `chat_messages` table with `id`, `workspace_id`, `session_id`, `role`, `content`, `timestamp`, `parsed_requirements_json`, and `seq` (sequence number). Messages are NOT stored in any JSON payload.

#### Scenario: Append user message
- **WHEN** a user sends a message in a session
- **THEN** a row is inserted into `chat_messages` with role="user", the content, and the next seq value for that session

#### Scenario: Append assistant reply with parsed requirements
- **WHEN** the assistant replies to a message
- **THEN** a row is inserted into `chat_messages` with role="assistant", content, and parsed_requirements_json containing the structured requirements

#### Scenario: Load messages for a session
- **WHEN** messages are loaded for a session_id
- **THEN** messages are returned ordered by seq ASC

### Requirement: Chat messages MUST be scoped to sessions
Each message row MUST reference a session_id. Loading messages without a session_id SHALL return an error.

#### Scenario: Load messages with invalid session
- **WHEN** messages are requested for a non-existent session_id
- **THEN** the system returns an empty list, not an error
