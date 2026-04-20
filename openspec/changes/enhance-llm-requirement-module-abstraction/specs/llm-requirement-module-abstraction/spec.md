## ADDED Requirements

### Requirement: Requirement parsing SHALL output module ownership fields
The system SHALL output `big_module` and `function_module` for each parsed requirement in LLM-based requirement parsing results when a confident module match exists.

#### Scenario: Confident module match from knowledge context
- **WHEN** a user submits a requirement message and the system has matching module knowledge context
- **THEN** each matched requirement result SHALL include non-empty `big_module` and `function_module`
- **THEN** the returned module values SHALL correspond to an existing module entry in the workspace knowledge set

### Requirement: Requirement parsing SHALL use business module and task-history context
The system SHALL construct LLM parsing context using both business module knowledge and historical task name samples before requesting requirement parsing output.

#### Scenario: Parsing with both module and task history context available
- **WHEN** the workspace contains module entries and historical tasks
- **THEN** the parsing request context SHALL include module candidate information
- **THEN** the parsing request context SHALL include task name samples used for semantic grounding

#### Scenario: Parsing with missing task history
- **WHEN** the workspace has module entries but no historical tasks
- **THEN** the system SHALL still execute requirement parsing using module context
- **THEN** the result SHALL remain structurally valid without task-history evidence

### Requirement: Requirement parsing MUST NOT rely on historical module_path field
The system MUST NOT use historical `module_path` as a trusted matching signal during module attribution because the field quality is not reliable.

#### Scenario: Historical data contains inaccurate module_path
- **WHEN** historical tasks contain inaccurate or conflicting `module_path` values
- **THEN** the parsing context SHALL exclude `module_path` from matching inputs
- **THEN** module attribution SHALL still be determined from module knowledge and reliable text signals (such as task name and story name)

### Requirement: Requirement parsing SHALL return abstracted requirement summary and match evidence
The system SHALL output an abstracted summary and module match evidence for each parsed requirement so users can validate why a module assignment was produced.

#### Scenario: Return abstraction and evidence for matched requirement
- **WHEN** a requirement is parsed with a confident module match
- **THEN** the result SHALL include `abstract_summary` describing the normalized intent
- **THEN** the result SHALL include `match_evidence` capturing at least one concrete signal (such as keyword hit or historical task reference)

### Requirement: Requirement parsing SHALL provide explicit fallback for low-confidence matches
The system MUST NOT fabricate a confident module assignment when model confidence is insufficient. It SHALL return an explicit fallback state and candidate guidance.

#### Scenario: Low-confidence module match
- **WHEN** the parser cannot identify a reliable module mapping
- **THEN** the result SHALL set `match_status` to `needs_confirmation`
- **THEN** the result SHALL include candidate module options or textual reasons for manual confirmation
- **THEN** `big_module` and `function_module` SHALL be empty or marked as unresolved in a deterministic format
