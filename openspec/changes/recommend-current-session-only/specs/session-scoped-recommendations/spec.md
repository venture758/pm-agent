## ADDED Requirements

### Requirement: Recommendation generation SHALL be scoped to current session requirements
The system MUST generate recommendations only for requirements that belong to the current session, and MUST NOT include requirements from previous sessions.

#### Scenario: Current session and historical requirements coexist
- **WHEN** a workspace contains historical requirements and a non-empty current-session requirement ID set
- **THEN** recommendation generation only processes requirements whose IDs are in the current-session set
- **AND** no recommendation is generated for historical requirements outside that set

#### Scenario: Current session set is empty
- **WHEN** a user triggers recommendation generation but current-session requirement ID set is empty
- **THEN** the system returns a clear validation error indicating current session has no requirements to recommend

### Requirement: Session requirement set SHALL be maintained consistently across input flows
The system MUST maintain a persistent current-session requirement ID set in workspace state for both chat input and structured input.

#### Scenario: Chat input appends requirements in same session
- **WHEN** chat message parsing returns requirement IDs during an active session
- **THEN** the system adds parsed IDs into current-session requirement ID set with deduplication

#### Scenario: Structured draft update starts a new session
- **WHEN** structured draft content is saved
- **THEN** the system starts a new session context and resets current-session requirement ID set to the requirements derived from this draft

### Requirement: Session lifecycle SHALL avoid cross-session carry-over after confirmation
The system MUST reset current-session recommendation scope after a confirmation cycle is completed.

#### Scenario: Session is confirmed
- **WHEN** recommendation confirmations are successfully submitted
- **THEN** the system clears current-session requirement ID set
- **AND** the next recommendation generation requires new current-session input
