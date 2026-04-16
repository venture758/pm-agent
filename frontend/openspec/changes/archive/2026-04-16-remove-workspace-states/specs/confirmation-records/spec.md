## REMOVED Requirements

### Requirement: Workspace FK constraint on confirmation records table
**Reason**: `workspace_states` table is being removed
**Migration**: `workspace_confirmation_records` retains `workspace_id` as a regular indexed column
