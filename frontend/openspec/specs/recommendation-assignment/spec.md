## REMOVED Requirements

### Requirement: Workspace FK constraint on recommendations table
**Reason**: `workspace_states` table is being removed
**Migration**: `workspace_recommendations` retains `workspace_id` as a regular indexed column
