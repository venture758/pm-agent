# Java Backend Cutover Smoke Checklist

## Preconditions

- Java backend deployed and healthy: `GET /api/v2/health` returns `code=0`.
- Schema migration SQL (`V1/V2`) applied successfully.
- Source and target database validation script passed:
  - `backend-java/scripts/migration/validate_migration.sh <source_db> <target_db>`

## Contract Smoke (API Envelope + Core Routes)

1. `GET /api/v2/health`
2. `PUT /api/v2/workspaces/{workspaceId}/draft`
3. `POST /api/v2/workspaces/{workspaceId}/chat`
4. `POST /api/v2/workspaces/{workspaceId}/recommendations`
5. `POST /api/v2/workspaces/{workspaceId}/confirmations`
6. `POST /api/v2/workspaces/{workspaceId}/uploads/platform-sync`
7. `GET /api/v2/workspaces/{workspaceId}/stories?page=1&pageSize=20`
8. `GET /api/v2/workspaces/{workspaceId}/tasks?page=1&pageSize=20`
9. `GET /api/v2/workspaces/{workspaceId}/monitoring`
10. `GET /api/v2/workspaces/{workspaceId}/insights`
11. `POST /api/v2/workspaces/{workspaceId}/pipeline/start`
12. `GET /api/v2/workspaces/{workspaceId}/pipeline/state`
13. `POST /api/v2/workspaces/{workspaceId}/pipeline/confirm`

Expected for every endpoint:

- Envelope fields always present: `code/message/data`.
- Success response has `code=0`.
- List endpoints return `data.page/data.pageSize/data.total/data.items`.

## Business Smoke (End-to-End)

1. Intake: send one chat message and verify parsed requirements persisted.
2. Recommend: generate recommendations and verify at least one assignment.
3. Confirm: submit confirmation and verify confirmation record created.
4. Delivery: import story/task excel and verify pagination query data appears.
5. Monitoring/Insights: verify alerts and insight summary can be queried.
6. Pipeline: run start -> confirm -> state; verify state persistence across refresh.

## Controlled Failure Smoke

1. Configure invalid primary LLM endpoint with valid fallback.
2. Send chat and pipeline requests.
3. Verify fallback succeeds and no provider secrets appear in response.
4. Configure both primary/fallback invalid.
5. Verify API returns controlled `LLM_UNAVAILABLE` response and no partial state commit.
