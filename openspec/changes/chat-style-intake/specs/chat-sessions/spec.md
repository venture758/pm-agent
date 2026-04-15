## ADDED Requirements

### Requirement: User SHALL be able to start a new chat session
The system SHALL provide a "新对话" (New Conversation) button on the intake page. When activated, the system SHALL create a new chat session with an empty message list. The previous session's messages SHALL be preserved and accessible.

#### Scenario: User clicks new conversation button
- **WHEN** the user clicks the "新对话" button on the intake page
- **THEN** a new chat session is created with an empty message list
- **THEN** the previous session's messages are preserved and accessible via the session list
- **THEN** the new session is set as the active session

#### Scenario: New conversation shows welcome state
- **WHEN** a new session is created and activated
- **THEN** the chat view displays the welcome guide message
- **THEN** the message list is empty except for the welcome guide

### Requirement: Chat sessions SHALL be persisted per workspace
The system SHALL store multiple chat sessions within each workspace. Each session SHALL have a unique session ID, creation timestamp, and a list of messages. The system SHALL persist sessions across page reloads via the workspace JSON state.

#### Scenario: Sessions survive page reload
- **WHEN** the user reloads the intake page
- **THEN** all previously created chat sessions are restored
- **THEN** the last active session is selected by default

#### Scenario: Session metadata is stored
- **THEN** each session record includes: session_id, created_at, last_active_at, message_count, and a truncated preview of the last user message

### Requirement: User SHALL be able to switch between sessions
The system SHALL display a session list/sidebar showing recent chat sessions. The user SHALL be able to click a session to view its messages. The system SHALL load the selected session's messages into the chat view.

#### Scenario: Session list displays recent sessions
- **WHEN** the user opens the session list
- **THEN** sessions are listed in reverse chronological order by last_active_at
- **THEN** each session item shows: creation time, message count, and last message preview

#### Scenario: User switches to a previous session
- **WHEN** the user clicks a session in the list
- **THEN** the chat view loads that session's messages
- **THEN** the selected session is marked as active

### Requirement: Backend SHALL provide session management APIs
The system SHALL provide RESTful endpoints for chat session management within a workspace. The endpoints SHALL support creating a new session, listing sessions, and retrieving a specific session's messages.

#### Scenario: Create new session
- **WHEN** client sends `POST /api/workspaces/{id}/chat/sessions` with `{ "title": "可选标题" }`
- **THEN** the system creates a new session with a unique session_id
- **THEN** the response includes the new session metadata and an empty message list
- **THEN** the new session is appended to the workspace's chat_sessions array

#### Scenario: List sessions
- **WHEN** client sends `GET /api/workspaces/{id}/chat/sessions`
- **THEN** the system returns a paginated list of sessions ordered by last_active_at descending
- **THEN** each session item includes: session_id, created_at, last_active_at, message_count, last_message_preview

#### Scenario: Get session messages
- **WHEN** client sends `GET /api/workspaces/{id}/chat/sessions/{sid}`
- **THEN** the system returns the session's full message list
- **THEN** each message includes: role, content, timestamp, parsed_requirements (if assistant message)

### Requirement: New session SHALL reset recommendation scope
The system SHALL reset `current_session_requirement_ids` when a new chat session is created. Subsequent messages in the new session SHALL generate requirements that belong to the new session only. The `generate_recommendations` endpoint SHALL only recommend requirements from the currently active session.

#### Scenario: Recommendations scoped to active session
- **WHEN** the user sends messages in a new session and clicks "生成建议"
- **THEN** only requirements parsed in the current session are included in recommendations
- **THEN** requirements from previous sessions are excluded

### Requirement: Confirmation SHALL implicitly create a new session
The system SHALL automatically create a new chat session after `confirm_assignments` is called. The previous session SHALL be marked as "confirmed" with a status flag. The user SHALL see a prompt suggesting to start a new round of requirements.

#### Scenario: Auto new session after confirmation
- **WHEN** the user confirms recommendations
- **THEN** a new chat session is created automatically
- **THEN** the previous session is marked with status: "confirmed"
- **THEN** the chat view switches to the new empty session
