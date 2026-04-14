## ADDED Requirements

### Requirement: Paginated confirmation records listing
The system SHALL provide an API endpoint that returns submitted confirmation records with pagination support, ordered by creation time descending.

#### Scenario: List records with default pagination
- **WHEN** a client requests `GET /api/workspaces/:id/confirmations` without page parameters
- **THEN** the system returns the first page of records with default page size (20), ordered by created_at descending

#### Scenario: List records with custom page and page size
- **WHEN** a client requests `GET /api/workspaces/:id/confirmations?page=2&pageSize=10`
- **THEN** the system returns the second page with up to 10 records, and includes total count and total pages in the response

#### Scenario: No confirmation records exist
- **WHEN** a workspace has no confirmation records
- **THEN** the system returns an empty list with total=0, total_pages=0

#### Scenario: Page exceeds available records
- **WHEN** a client requests a page number greater than total pages
- **THEN** the system returns an empty items array with the correct total count

### Requirement: Confirmation history displayed in frontend
The frontend SHALL display a dedicated "Confirmation History" page showing confirmed assignment records in an expandable table format with session-level summary and per-record detail.

#### Scenario: Display confirmation history table
- **WHEN** the user navigates to the Confirmation History page
- **THEN** the page shows a table with columns: session ID, confirmed time, record count, and an expand button for details

#### Scenario: Expand to view assignment details
- **WHEN** a user expands a confirmation record row
- **THEN** the page shows the list of confirmed assignments including requirement ID, title, development owner, testing owner, and backup owner

#### Scenario: Pagination controls displayed
- **WHEN** total records exceed the current page size
- **THEN** pagination controls are displayed allowing navigation between pages
