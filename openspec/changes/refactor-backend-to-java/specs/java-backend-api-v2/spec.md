## ADDED Requirements

### Requirement: Java backend SHALL expose versioned workspace APIs under v2
The system MUST expose all workspace-facing backend capabilities via `/api/v2/workspaces/{workspaceId}/...` and MUST support at least health, draft, members, modules, recommendations, confirmations, stories, tasks, uploads, chat, pipeline, monitoring, and insights routes.

#### Scenario: Client calls v2 workspace routes
- **WHEN** the frontend requests a supported workspace capability
- **THEN** the request is handled by a route under `/api/v2/workspaces/{workspaceId}/...`
- **AND** the response does not require legacy Python route compatibility mapping

### Requirement: API responses SHALL use unified envelope and pagination contract
The system MUST return response envelopes in the format `code`, `message`, and `data` for success and failure cases. For list queries, the system MUST provide unified pagination fields: `page`, `pageSize`, `total`, and `items`.

#### Scenario: Paginated list endpoint succeeds
- **WHEN** a client requests a paginated list such as stories or tasks
- **THEN** the response body includes `code`, `message`, `data.page`, `data.pageSize`, `data.total`, and `data.items`
- **AND** `data.items` contains only records in the requested page window

#### Scenario: Validation failure occurs
- **WHEN** the client submits an invalid request payload
- **THEN** the response includes non-success `code` and a machine-readable `message`
- **AND** the response format still follows `code/message/data`

### Requirement: Frontend migration SHALL complete against v2 contract in one release
The system MUST ship frontend and Java backend together so all production UI calls use v2 endpoints in the same release window.

#### Scenario: Production build is cut over
- **WHEN** the release is deployed during the cutover window
- **THEN** frontend API client targets only v2 endpoints
- **AND** no production page requires v1 Python backend endpoints to operate
