## ADDED Requirements

### Requirement: Confirmation SHALL persist internal records without generating platform handoff
After recommendation confirmation is submitted, the system MUST persist the confirmation result as an internal record and MUST NOT generate platform handoff stories/tasks.

#### Scenario: Confirm assignments successfully
- **WHEN** user submits confirmation actions for an existing recommendation set
- **THEN** system stores the confirmed assignments in workspace state
- **AND** system writes one confirmation record entry to the confirmation record table
- **AND** system does not create new handoff stories or handoff tasks

### Requirement: Confirmation record storage SHALL be queryable and durable
The system MUST store each confirmation batch in a dedicated persistence table with workspace scope and payload snapshot.

#### Scenario: Persist one confirmation batch
- **WHEN** one confirmation request completes successfully
- **THEN** one row is inserted into confirmation record table with workspace identifier, confirmed count, payload snapshot, and timestamp

### Requirement: Confirmation API response SHALL remain backward compatible
The confirmation API response MUST keep existing top-level structure compatibility while reflecting the new internal-only behavior.

#### Scenario: Confirm response contains no new handoff data
- **WHEN** confirmation succeeds
- **THEN** response still includes `handoff` object shape
- **AND** `handoff.stories` and `handoff.tasks` are empty arrays
- **AND** response message states that confirmation is recorded internally and not synced to platform
