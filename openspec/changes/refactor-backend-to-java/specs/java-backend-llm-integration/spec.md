## ADDED Requirements

### Requirement: Java backend SHALL provide chat-based requirement parsing with LLM fallback
The system MUST support chat message parsing into structured requirements through a primary LLM provider and MUST support configured fallback providers on timeout or upstream failure.

#### Scenario: Primary LLM succeeds
- **WHEN** a user sends a valid chat message for requirement intake
- **THEN** the system returns structured requirements and assistant reply text generated from primary provider output
- **AND** parsed requirements are persisted and linked to the active session

#### Scenario: Primary LLM fails and fallback is available
- **WHEN** primary provider request fails due to timeout or transient upstream error
- **THEN** the system retries using configured fallback provider
- **AND** the response includes parsed output without exposing internal provider secrets

### Requirement: Java backend SHALL persist multi-step pipeline state for progressive confirmation
The system MUST provide pipeline start, state query, and step confirmation APIs, and MUST persist per-workspace pipeline progress including current step, completed steps, and step results.

#### Scenario: User advances pipeline step by step
- **WHEN** the user starts pipeline and confirms each current step
- **THEN** the system moves to the next step and stores updated pipeline state
- **AND** `get pipeline state` returns the same persisted progress after page refresh

#### Scenario: User reanalyzes current step with feedback
- **WHEN** the user submits feedback using reanalyze action
- **THEN** the system reruns the current step with the new constraint
- **AND** previous step history remains auditable for the session

### Requirement: LLM-related failures SHALL return controlled degradations
The system MUST return structured, user-actionable error responses when all configured LLM tiers fail, and MUST avoid corrupting workspace state.

#### Scenario: All providers fail
- **WHEN** primary and fallback providers both fail for a request
- **THEN** the API returns a controlled error payload with retry guidance
- **AND** no partial requirement or pipeline state is committed for that failed action
