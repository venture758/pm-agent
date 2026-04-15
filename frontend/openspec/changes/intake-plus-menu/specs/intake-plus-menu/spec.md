## ADDED Requirements

### Requirement: Intake page SHALL use a split layout with collapsible sidebar
The system SHALL render the intake page as a two-panel layout: a left sidebar for session navigation and a right main area for the chat view. The sidebar SHALL be collapsible, with a toggle button to show/hide. When collapsed, only a narrow icon bar or hamburger button remains visible.

#### Scenario: Default desktop layout with sidebar
- **WHEN** the user opens the intake page on a desktop viewport (width >= 860px)
- **THEN** the sidebar is visible on the left side
- **THEN** the chat area occupies the remaining right space

#### Scenario: Sidebar can be collapsed
- **WHEN** the user clicks the sidebar collapse toggle
- **THEN** the sidebar narrows to an icon-only strip or hides completely
- **THEN** the chat area expands to fill the freed space

### Requirement: Sidebar SHALL contain a new conversation button at the top
The system SHALL render a "新对话" (New Chat) button as the first element in the sidebar. When clicked, it SHALL create a new session, clear the chat view, and set it as the active session.

#### Scenario: User clicks new conversation in sidebar
- **WHEN** the user clicks the "新对话" button in the sidebar
- **THEN** a new session is created via the API
- **THEN** the chat view is cleared to show the welcome guide
- **THEN** the new session is set as active and highlighted in the sidebar

### Requirement: Sidebar SHALL list session history grouped by time
The system SHALL display the session list below the "新对话" button, ordered by last_active_at descending. Each session item SHALL show a message preview and a relative time label. Clicking a session SHALL load its messages into the chat view and mark it as active.

#### Scenario: Session list shows recent sessions
- **WHEN** the user views the sidebar
- **THEN** sessions are listed in reverse chronological order
- **THEN** each session item shows: truncated message preview and relative time

#### Scenario: User switches to a session
- **WHEN** the user clicks a session in the sidebar
- **THEN** the chat view loads that session's messages
- **THEN** the selected session is visually highlighted as active

### Requirement: Mobile layout SHALL hide sidebar by default
The system SHALL hide or overlay the sidebar on narrow viewports (width < 860px). The user SHALL be able to open the sidebar via a hamburger toggle in the header. The sidebar SHALL display as an overlay when opened on mobile.

#### Scenario: Mobile sidebar toggle
- **WHEN** the user clicks the hamburger icon on a narrow viewport
- **THEN** the sidebar slides in from the left as an overlay
- **THEN** clicking outside the sidebar closes it

### Requirement: Main chat area SHALL show welcome state when empty
The system SHALL display a welcome guide in the center of the chat area when the active session has no messages. The welcome guide SHALL include a title, brief description, and the chat input at the bottom.

#### Scenario: Welcome state displays
- **WHEN** the active session has no messages
- **THEN** the chat area shows the welcome guide centered
- **THEN** the chat input is visible at the bottom
