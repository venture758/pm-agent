# story-pagination Specification

## Requirements

### Requirement: Story list SHALL be queryable via paginated API
The system SHALL provide a paginated GET endpoint for story records, returning a subset of stories with pagination metadata (total count, page size, total pages).

#### Scenario: Default pagination returns first page
- **WHEN** a client requests `GET /api/workspaces/{id}/stories` without pagination parameters
- **THEN** the response returns the first 20 stories ordered by modified_time DESC, user_story_code
- **THEN** the response includes `page=1`, `page_size=20`, `total` (total record count), and `total_pages`

#### Scenario: Custom page and page size
- **WHEN** a client requests `GET /api/workspaces/{id}/stories?page=2&pageSize=10`
- **THEN** the response returns stories 11-20 ordered by modified_time DESC
- **THEN** the response includes `page=2`, `page_size=10`, `total`, and `total_pages`

#### Scenario: Empty workspace returns zero total
- **WHEN** a workspace has no story records
- **THEN** the response returns `"items": []`, `"total": 0`, `"total_pages": 1`

#### Scenario: Out-of-range page returns empty items
- **WHEN** a client requests a page number greater than total_pages
- **THEN** the response returns `"items": []` with the requested page number
- **THEN** `total` and `total_pages` remain accurate to the actual data

### Requirement: Story pagination SHALL support server-side search filtering
The system SHALL accept `keyword` query parameter to filter stories by user_story_code or story title, resetting results to matching records before applying pagination.

#### Scenario: Keyword filter returns matching stories
- **WHEN** a client requests `GET /api/workspaces/{id}/stories?keyword=US-100`
- **THEN** only stories whose code or title contains "US-100" are returned
- **THEN** `total` reflects the count of matching records, not the total workspace stories

### Requirement: Story pagination SHALL use LIMIT/OFFSET at database level
The system SHALL execute two queries: a `COUNT(*)` for total record count and a `SELECT ... LIMIT ? OFFSET ?` for the current page data. This ensures O(1) memory usage regardless of total record count.

#### Scenario: Large dataset does not cause memory issues
- **WHEN** a workspace contains 5000+ story records
- **THEN** a request for `page=1&pageSize=20` returns within acceptable latency
- **THEN** the database query uses LIMIT 20 OFFSET 0, not loading all 5000 records
