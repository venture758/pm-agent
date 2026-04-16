## ADDED Requirements

### Requirement: System shall persist module snapshots before and after knowledge updates
The system SHALL persist independent module-level knowledge update records for every business module that is processed during a knowledge update run. Each record set MUST include the module snapshot before automatic update, the module snapshot after automatic update, and the session/workspace identifiers that tie the change to a specific confirmation-triggered knowledge update run.

#### Scenario: Persist before and after snapshots for changed modules
- **WHEN** a confirmation-triggered knowledge update run successfully applies automatic changes to one or more business modules
- **THEN** the system SHALL persist module-level records for each affected `module_key`
- **THEN** each record SHALL be queryable by `workspace_id` and `session_id`
- **THEN** each record SHALL include both `before_snapshot` and `after_snapshot`

#### Scenario: Persist module records even when no field value changes
- **WHEN** a knowledge update run evaluates a business module and determines that no field value changed after applying the update
- **THEN** the system SHALL still persist a module-level record for that `module_key`
- **THEN** the record SHALL explicitly identify that the module was processed with no effective field change

### Requirement: System shall expose structured diff summaries for module-level knowledge updates
The system SHALL calculate and persist a structured diff summary for every module-level knowledge update record so that users can observe which business module fields were added, removed, or modified by the Agent.

#### Scenario: Return field-level diff summary for a processed module
- **WHEN** a client queries the module-level records for a knowledge update session
- **THEN** the system SHALL return a diff summary for each processed module
- **THEN** the diff summary SHALL distinguish added, removed, and modified fields
- **THEN** the diff summary SHALL be derived from the persisted `before_snapshot` and `after_snapshot`

### Requirement: System shall expose module change records in confirmation-centered queries
The system SHALL expose module-level knowledge update change records through the existing confirmation-centered query surfaces, including the latest knowledge update summary and confirmation history details, so users can inspect the Agent's automatic module updates without leaving the confirmation workflow.

#### Scenario: Show latest module change summary after confirmation
- **WHEN** a confirmation request completes and the knowledge update run produces module-level records
- **THEN** the confirmation response SHALL include a summary of affected module count and module change availability
- **THEN** the workspace latest knowledge update payload SHALL indicate that module-level before/after records can be queried or displayed

#### Scenario: Show session-scoped module change details in confirmation history
- **WHEN** a client requests confirmation history for a workspace
- **THEN** each history item associated with a knowledge update run SHALL expose the corresponding module-level change records or their structured summary
- **THEN** the client SHALL be able to inspect each module's before snapshot, after snapshot, and diff summary in the confirmation workflow context

### Requirement: System shall preserve truthful semantics for skipped and failed knowledge update runs
The system MUST preserve truthful audit semantics when a knowledge update run is skipped or fails. The system SHALL keep the session-level status and error context, and SHALL NOT fabricate module-level after snapshots for runs that never applied module updates.

#### Scenario: Skip run without fabricated module snapshots
- **WHEN** a knowledge update run is skipped before module update processing begins
- **THEN** the system SHALL persist the session-level knowledge update status as `skipped`
- **THEN** the system SHALL NOT fabricate module-level before or after snapshots for that run

#### Scenario: Failed run keeps error context without fake after state
- **WHEN** a knowledge update run fails before finishing module update persistence
- **THEN** the system SHALL persist the session-level knowledge update status as `failed` with an error message
- **THEN** the system SHALL NOT fabricate module-level `after_snapshot` data for modules that were never successfully updated
