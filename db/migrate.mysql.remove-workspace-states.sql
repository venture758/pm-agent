-- Migration: Remove workspace_states JSON blob storage
-- Split workspace payload into dedicated tables per domain.
-- Usage:
--   mysql -h127.0.0.1 -uroot -p pm_agent < db/migrate.mysql.remove-workspace-states.sql

-- ============================================================
-- 1. New: workspaces (lightweight metadata)
-- ============================================================
CREATE TABLE IF NOT EXISTS workspaces (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  workspace_id VARCHAR(255) NOT NULL COMMENT '工作区唯一标识',
  title VARCHAR(255) NOT NULL DEFAULT '' COMMENT '工作区标题',
  created_at VARCHAR(64) NOT NULL COMMENT '创建时间(ISO8601)',
  updated_at VARCHAR(64) NOT NULL COMMENT '更新时间(ISO8601)',
  PRIMARY KEY (id),
  UNIQUE KEY uk_workspaces_workspace_id (workspace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作区元数据表';

-- ============================================================
-- 2. New: chat_sessions
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_sessions (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  session_id VARCHAR(64) NOT NULL COMMENT '会话唯一标识',
  workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  created_at VARCHAR(64) NOT NULL COMMENT '创建时间(ISO8601)',
  last_active_at VARCHAR(64) NOT NULL COMMENT '最后活跃时间(ISO8601)',
  status VARCHAR(32) NOT NULL DEFAULT 'active' COMMENT '状态: active|archived|confirmed',
  last_message_preview VARCHAR(255) NOT NULL DEFAULT '' COMMENT '最后一条消息预览',
  PRIMARY KEY (id),
  UNIQUE KEY uk_chat_sessions_session_id (session_id),
  KEY idx_chat_sessions_workspace_active (workspace_id, status, last_active_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天会话表';

-- ============================================================
-- 3. New: chat_messages
-- ============================================================
CREATE TABLE IF NOT EXISTS chat_messages (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  session_id VARCHAR(64) NOT NULL COMMENT '关联会话ID',
  seq INT NOT NULL COMMENT '消息序号',
  role VARCHAR(16) NOT NULL COMMENT '消息角色: user|assistant|system',
  content LONGTEXT NOT NULL COMMENT '消息内容',
  timestamp VARCHAR(64) NOT NULL COMMENT '消息时间(ISO8601)',
  parsed_requirements_json LONGTEXT NOT NULL DEFAULT '' COMMENT '解析后的需求JSON(仅assistant消息)',
  PRIMARY KEY (id),
  KEY idx_chat_messages_session_seq (session_id, seq)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='聊天消息表';

-- ============================================================
-- 4. New: requirements
-- ============================================================
CREATE TABLE IF NOT EXISTS requirements (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  requirement_id VARCHAR(255) NOT NULL COMMENT '需求唯一标识',
  title VARCHAR(500) NOT NULL DEFAULT '' COMMENT '需求标题',
  source VARCHAR(64) NOT NULL DEFAULT 'chat' COMMENT '来源',
  priority VARCHAR(32) NOT NULL DEFAULT '中' COMMENT '优先级',
  raw_text TEXT NOT NULL COMMENT '原始文本',
  complexity VARCHAR(32) NOT NULL DEFAULT '中' COMMENT '复杂度',
  risk VARCHAR(32) NOT NULL DEFAULT '中' COMMENT '风险等级',
  requirement_type VARCHAR(64) NOT NULL DEFAULT '' COMMENT '需求类型',
  source_url VARCHAR(500) NOT NULL DEFAULT '' COMMENT '来源URL',
  source_message TEXT NOT NULL COMMENT '来源消息',
  payload_json LONGTEXT NOT NULL COMMENT '完整需求JSON快照',
  created_at VARCHAR(64) NOT NULL COMMENT '创建时间(ISO8601)',
  PRIMARY KEY (id),
  UNIQUE KEY uk_requirements_workspace_req (workspace_id, requirement_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='需求明细表';

-- ============================================================
-- 5. New: session_requirements (many-to-many)
-- ============================================================
CREATE TABLE IF NOT EXISTS session_requirements (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  session_id VARCHAR(64) NOT NULL COMMENT '关联会话ID',
  requirement_id VARCHAR(255) NOT NULL COMMENT '关联需求ID',
  PRIMARY KEY (id),
  UNIQUE KEY uk_session_requirements_session_req (session_id, requirement_id),
  KEY idx_session_requirements_requirement (requirement_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话-需求关联表';

-- ============================================================
-- 6. Remove FK constraints from all related tables
-- ============================================================

-- workspace_module_entries
ALTER TABLE workspace_module_entries
  DROP FOREIGN KEY IF EXISTS fk_workspace_module_entries_workspace_id;

-- workspace_managed_members
ALTER TABLE workspace_managed_members
  DROP FOREIGN KEY IF EXISTS fk_workspace_managed_members_workspace_id;

-- workspace_recommendations
ALTER TABLE workspace_recommendations
  DROP FOREIGN KEY IF EXISTS fk_workspace_recommendations_workspace_id;

-- workspace_confirmation_records
ALTER TABLE workspace_confirmation_records
  DROP FOREIGN KEY IF EXISTS fk_workspace_confirmation_records_workspace_id;

-- workspace_knowledge_update_records
ALTER TABLE workspace_knowledge_update_records
  DROP FOREIGN KEY IF EXISTS fk_workspace_knowledge_update_records_workspace_id;

-- workspace_insight_snapshots
ALTER TABLE workspace_insight_snapshots
  DROP FOREIGN KEY IF EXISTS fk_workspace_insight_snapshots_workspace_id;

-- workspace_story_records
ALTER TABLE workspace_story_records
  DROP FOREIGN KEY IF EXISTS fk_workspace_story_records_workspace_id;

-- workspace_task_records
ALTER TABLE workspace_task_records
  DROP FOREIGN KEY IF EXISTS fk_workspace_task_records_workspace_id;

-- workspace_import_batches (if exists)
ALTER TABLE workspace_import_batches
  DROP FOREIGN KEY IF EXISTS fk_workspace_import_batches_workspace_id;

-- ============================================================
-- 7. Drop workspace_states table (data migrated)
-- ============================================================
DROP TABLE IF EXISTS workspace_states;
