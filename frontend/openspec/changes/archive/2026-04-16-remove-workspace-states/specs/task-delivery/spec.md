## REMOVED Requirements

### Requirement: Workspace FK constraint on task records table
**Reason**: `workspace_states` table is being removed
**Migration**: `workspace_task_records` retains `workspace_id` as a regular indexed column
