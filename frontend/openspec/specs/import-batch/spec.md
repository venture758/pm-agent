## REMOVED Requirements

### Requirement: Workspace FK constraint on import batch table
**Reason**: `workspace_states` table is being removed
**Migration**: `workspace_import_batches` retains `workspace_id` as a regular indexed column
