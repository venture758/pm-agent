## ADDED Requirements

### Requirement: Data migration SHALL move all production workspace history to Java schema
The system MUST migrate all required historical records from the existing Python-backed MySQL structures into the Java target schema before traffic cutover.

#### Scenario: Full migration execution completes
- **WHEN** migration is executed in a cutover window
- **THEN** all required domain datasets (workspace state, members, modules, recommendations, confirmations, stories, tasks, chat, pipeline-related records) are migrated
- **AND** migration output includes table-level counts and mismatch summary

### Requirement: Cutover SHALL enforce validation gates before traffic switch
The system MUST execute pre-switch validation checks and MUST block traffic switch when validation fails.

#### Scenario: Validation gate passes
- **WHEN** schema migration, data migration, and smoke checks all pass
- **THEN** the release process allows switching production traffic to Java backend
- **AND** switch event and validation evidence are recorded in deployment logs

#### Scenario: Validation gate fails
- **WHEN** any required migration validation fails
- **THEN** traffic remains on Python backend
- **AND** deployment status is marked failed with actionable error report

### Requirement: Cutover process SHALL support deterministic rollback
The system MUST provide rollback steps that restore service through Python backend and recover database state from pre-cutover snapshot when needed.

#### Scenario: Rollback is triggered during cutover
- **WHEN** post-switch smoke checks fail within rollback window
- **THEN** traffic is switched back to Python backend
- **AND** database state is restored according to rollback runbook
- **AND** rollback completion is logged with timestamp and operator context
