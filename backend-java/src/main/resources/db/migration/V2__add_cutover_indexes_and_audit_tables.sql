SET @db_name = DATABASE();

SET @sql = IF(
  (SELECT COUNT(1)
     FROM information_schema.statistics
    WHERE table_schema = @db_name
      AND table_name = 'workspace_task_records'
      AND index_name = 'idx_workspace_task_records_project_status') = 0,
  'ALTER TABLE workspace_task_records ADD KEY idx_workspace_task_records_project_status (workspace_id, project_name, status)',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF(
  (SELECT COUNT(1)
     FROM information_schema.statistics
    WHERE table_schema = @db_name
      AND table_name = 'workspace_story_records'
      AND index_name = 'idx_workspace_story_records_status_owner') = 0,
  'ALTER TABLE workspace_story_records ADD KEY idx_workspace_story_records_status_owner (workspace_id, status, owner_names)',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql = IF(
  (SELECT COUNT(1)
     FROM information_schema.statistics
    WHERE table_schema = @db_name
      AND table_name = 'chat_messages'
      AND index_name = 'idx_chat_messages_workspace_timestamp') = 0,
  'ALTER TABLE chat_messages ADD KEY idx_chat_messages_workspace_timestamp (workspace_id, timestamp)',
  'SELECT 1'
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

CREATE TABLE IF NOT EXISTS migration_audit_logs (
  id BIGINT NOT NULL AUTO_INCREMENT,
  migration_batch_id VARCHAR(64) NOT NULL,
  source_database VARCHAR(128) NOT NULL,
  target_database VARCHAR(128) NOT NULL,
  phase VARCHAR(64) NOT NULL,
  table_name VARCHAR(128) NOT NULL,
  source_count BIGINT NOT NULL DEFAULT 0,
  target_count BIGINT NOT NULL DEFAULT 0,
  status VARCHAR(32) NOT NULL,
  detail TEXT NULL,
  created_at VARCHAR(64) NOT NULL,
  PRIMARY KEY (id),
  KEY idx_migration_audit_batch_phase (migration_batch_id, phase),
  KEY idx_migration_audit_table (table_name, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS deployment_cutover_events (
  id BIGINT NOT NULL AUTO_INCREMENT,
  event_id VARCHAR(64) NOT NULL,
  stage VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL,
  operator VARCHAR(128) NOT NULL,
  detail TEXT NULL,
  created_at VARCHAR(64) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_deployment_cutover_events_event_id (event_id),
  KEY idx_deployment_cutover_events_stage_status (stage, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
