## REMOVED Requirements

### Requirement: Workspace FK constraint on story records table
**Reason**: `workspace_states` table is being removed
**Migration**: `workspace_story_records` retains `workspace_id` as a regular indexed column
