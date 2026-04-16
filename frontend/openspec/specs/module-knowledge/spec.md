## REMOVED Requirements

### Requirement: Workspace FK constraint on module entries table
**Reason**: `workspace_states` table is being removed; FK references are no longer valid
**Migration**: The `workspace_module_entries` table retains its `workspace_id` column as a regular indexed column. Data integrity is maintained by application-level workspace existence checks.
