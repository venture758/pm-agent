## REMOVED Requirements

### Requirement: Workspace FK constraint on insight snapshots table
**Reason**: `workspace_states` table is being removed
**Migration**: `workspace_insight_snapshots` retains `workspace_id` as a regular indexed column
