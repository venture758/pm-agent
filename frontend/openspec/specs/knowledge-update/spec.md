## REMOVED Requirements

### Requirement: Workspace FK constraint on knowledge update records table
**Reason**: `workspace_states` table is being removed
**Migration**: `workspace_knowledge_update_records` retains `workspace_id` as a regular indexed column
