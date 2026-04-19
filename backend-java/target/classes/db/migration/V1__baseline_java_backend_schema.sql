CREATE TABLE IF NOT EXISTS workspaces (
  id BIGINT NOT NULL AUTO_INCREMENT,
  workspace_id VARCHAR(255) NOT NULL,
  title VARCHAR(255) NOT NULL DEFAULT '',
  created_at VARCHAR(64) NOT NULL,
  updated_at VARCHAR(64) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_workspaces_workspace_id (workspace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS agent_states (
  id BIGINT NOT NULL AUTO_INCREMENT,
  state_key VARCHAR(64) NOT NULL,
  payload LONGTEXT NOT NULL,
  updated_at VARCHAR(64) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_agent_states_state_key (state_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chat_sessions (
  id BIGINT NOT NULL AUTO_INCREMENT,
  session_id VARCHAR(64) NOT NULL,
  workspace_id VARCHAR(255) NOT NULL,
  created_at VARCHAR(64) NOT NULL,
  last_active_at VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'active',
  last_message_preview VARCHAR(255) NOT NULL DEFAULT '',
  PRIMARY KEY (id),
  UNIQUE KEY uk_chat_sessions_session_id (session_id),
  KEY idx_chat_sessions_workspace_active (workspace_id, status, last_active_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chat_messages (
  id BIGINT NOT NULL AUTO_INCREMENT,
  workspace_id VARCHAR(255) NOT NULL,
  session_id VARCHAR(64) NOT NULL,
  seq INT NOT NULL,
  role VARCHAR(16) NOT NULL,
  content LONGTEXT NOT NULL,
  timestamp VARCHAR(64) NOT NULL,
  parsed_requirements_json LONGTEXT NOT NULL DEFAULT '',
  PRIMARY KEY (id),
  KEY idx_chat_messages_session_seq (session_id, seq),
  KEY idx_chat_messages_workspace_session (workspace_id, session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS requirements (
  id BIGINT NOT NULL AUTO_INCREMENT,
  workspace_id VARCHAR(255) NOT NULL,
  requirement_id VARCHAR(255) NOT NULL,
  title VARCHAR(500) NOT NULL DEFAULT '',
  source VARCHAR(64) NOT NULL DEFAULT 'chat',
  priority VARCHAR(32) NOT NULL DEFAULT '中',
  raw_text TEXT NOT NULL,
  complexity VARCHAR(32) NOT NULL DEFAULT '中',
  risk VARCHAR(32) NOT NULL DEFAULT '中',
  requirement_type VARCHAR(64) NOT NULL DEFAULT '',
  source_url VARCHAR(500) NOT NULL DEFAULT '',
  source_message TEXT NOT NULL,
  payload_json LONGTEXT NOT NULL,
  created_at VARCHAR(64) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_requirements_workspace_req (workspace_id, requirement_id),
  KEY idx_requirements_workspace_id (workspace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS session_requirements (
  id BIGINT NOT NULL AUTO_INCREMENT,
  session_id VARCHAR(64) NOT NULL,
  requirement_id VARCHAR(255) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_session_requirements_session_req (session_id, requirement_id),
  KEY idx_session_requirements_requirement (requirement_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS workspace_module_entries (
  id BIGINT NOT NULL AUTO_INCREMENT,
  workspace_id VARCHAR(255) NOT NULL,
  module_key VARCHAR(255) NOT NULL,
  big_module VARCHAR(255) NOT NULL,
  function_module VARCHAR(255) NOT NULL,
  primary_owner VARCHAR(255) NOT NULL,
  backup_owners_json JSON NOT NULL,
  familiar_members_json JSON NOT NULL,
  aware_members_json JSON NOT NULL,
  unfamiliar_members_json JSON NOT NULL,
  source_sheet VARCHAR(255) NOT NULL DEFAULT '',
  source_year INT NOT NULL DEFAULT 0,
  imported_at VARCHAR(64) NOT NULL,
  recent_assignees_json JSON NOT NULL,
  suggested_familiarity_json JSON NOT NULL,
  assignment_history_json LONGTEXT NOT NULL,
  updated_at VARCHAR(64) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_workspace_module_entries_workspace_key (workspace_id, module_key),
  KEY idx_workspace_module_entries_workspace_big_module (workspace_id, big_module)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS workspace_managed_members (
  id BIGINT NOT NULL AUTO_INCREMENT,
  workspace_id VARCHAR(255) NOT NULL,
  member_name VARCHAR(255) NOT NULL,
  role VARCHAR(64) NOT NULL,
  skills_json JSON NOT NULL,
  experience_level VARCHAR(64) NOT NULL,
  workload DECIMAL(10,4) NOT NULL DEFAULT 0,
  capacity DECIMAL(10,4) NOT NULL DEFAULT 1,
  constraints_json JSON NOT NULL,
  updated_at VARCHAR(64) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_workspace_managed_members_workspace_name (workspace_id, member_name),
  KEY idx_workspace_managed_members_workspace_role (workspace_id, role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS workspace_recommendations (
  id BIGINT NOT NULL AUTO_INCREMENT,
  workspace_id VARCHAR(255) NOT NULL,
  requirement_id VARCHAR(255) NOT NULL,
  payload_json LONGTEXT NOT NULL,
  created_at VARCHAR(64) NOT NULL,
  updated_at VARCHAR(64) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_workspace_recommendations_workspace_requirement (workspace_id, requirement_id),
  KEY idx_workspace_recommendations_workspace_id (workspace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS workspace_confirmation_records (
  id BIGINT NOT NULL AUTO_INCREMENT,
  workspace_id VARCHAR(255) NOT NULL,
  session_id VARCHAR(64) NOT NULL,
  confirmed_count INT NOT NULL,
  payload_json LONGTEXT NOT NULL,
  created_at VARCHAR(64) NOT NULL,
  PRIMARY KEY (id),
  KEY idx_workspace_confirmation_records_workspace_id (workspace_id),
  KEY idx_workspace_confirmation_records_session_id (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS workspace_story_records (
  id BIGINT NOT NULL AUTO_INCREMENT,
  workspace_id VARCHAR(255) NOT NULL,
  user_story_code VARCHAR(255) NOT NULL,
  user_story_name TEXT NULL,
  status VARCHAR(255) NULL,
  owner_names VARCHAR(255) NULL,
  tester_names VARCHAR(255) NULL,
  priority VARCHAR(64) NULL,
  detail_url TEXT NULL,
  project_name VARCHAR(255) NULL,
  developer_names VARCHAR(255) NULL,
  imported_at VARCHAR(64) NOT NULL,
  updated_at VARCHAR(64) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_workspace_story_records_workspace_story (workspace_id, user_story_code),
  KEY idx_workspace_story_records_workspace_id (workspace_id),
  KEY idx_workspace_story_records_project_name (workspace_id, project_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS workspace_task_records (
  id BIGINT NOT NULL AUTO_INCREMENT,
  workspace_id VARCHAR(255) NOT NULL,
  task_code VARCHAR(255) NOT NULL,
  related_story VARCHAR(255) NULL,
  name TEXT NULL,
  task_type VARCHAR(255) NULL,
  owner VARCHAR(255) NULL,
  status VARCHAR(255) NULL,
  estimated_start VARCHAR(64) NULL,
  estimated_end VARCHAR(64) NULL,
  planned_person_days DECIMAL(12,2) NULL,
  actual_person_days DECIMAL(12,2) NULL,
  defect_count DECIMAL(12,2) NULL,
  project_name VARCHAR(255) NULL,
  imported_at VARCHAR(64) NOT NULL,
  updated_at VARCHAR(64) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_workspace_task_records_workspace_task (workspace_id, task_code),
  KEY idx_workspace_task_records_workspace_id (workspace_id),
  KEY idx_workspace_task_records_owner (workspace_id, owner),
  KEY idx_workspace_task_records_status (workspace_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS workspace_insight_snapshots (
  id BIGINT NOT NULL AUTO_INCREMENT,
  workspace_id VARCHAR(255) NOT NULL,
  snapshot_at VARCHAR(64) NOT NULL,
  heatmap_json JSON NOT NULL,
  single_points_json JSON NOT NULL,
  growth_suggestions_json JSON NOT NULL,
  summary_json JSON NOT NULL,
  PRIMARY KEY (id),
  KEY idx_workspace_insight_snapshots_workspace_time (workspace_id, snapshot_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS workspace_knowledge_update_module_diff_records (
  id BIGINT NOT NULL AUTO_INCREMENT,
  workspace_id VARCHAR(255) NOT NULL,
  session_id VARCHAR(64) NOT NULL,
  requirement_id VARCHAR(255) NOT NULL,
  module_key VARCHAR(255) NOT NULL,
  changed TINYINT(1) NOT NULL DEFAULT 0,
  payload_json LONGTEXT NOT NULL,
  created_at VARCHAR(64) NOT NULL,
  PRIMARY KEY (id),
  KEY idx_workspace_knowledge_diff_workspace (workspace_id),
  KEY idx_workspace_knowledge_diff_session_req (session_id, requirement_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
