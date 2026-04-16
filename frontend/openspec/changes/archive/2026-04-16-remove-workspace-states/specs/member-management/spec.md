## REMOVED Requirements

### Requirement: Workspace FK constraint on managed members table
**Reason**: `workspace_states` table is being removed
**Migration**: `workspace_managed_members` retains `workspace_id` as a regular indexed column
