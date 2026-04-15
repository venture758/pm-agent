-- pm-agent MySQL migration for module entry normalization
-- Target: MySQL 8+
-- Usage:
--   mysql -h127.0.0.1 -u<user> -p pm_agent < db/migrate.mysql.module-entries.sql

SET NAMES utf8mb4;

-- 1) workspace_states: ensure BIGINT id primary key and comments
CREATE TABLE IF NOT EXISTS workspace_states (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  workspace_id VARCHAR(255) NOT NULL COMMENT '工作区唯一标识',
  payload LONGTEXT NOT NULL COMMENT '工作区全量状态JSON快照',
  updated_at VARCHAR(64) NOT NULL COMMENT '更新时间(ISO8601)',
  PRIMARY KEY (id),
  UNIQUE KEY uk_workspace_states_workspace_id (workspace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作区状态快照表';

ALTER TABLE workspace_states
  ADD COLUMN IF NOT EXISTS id BIGINT NULL COMMENT '主键ID';

SET @seq_workspace := 0;
UPDATE workspace_states
SET id = (@seq_workspace := @seq_workspace + 1)
WHERE id IS NULL
ORDER BY workspace_id;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_states'
        AND index_name = 'uk_workspace_states_id'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_states ADD UNIQUE KEY uk_workspace_states_id (id)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 8) workspace_story_records: create table for standalone story Excel upload
CREATE TABLE IF NOT EXISTS workspace_story_records (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  user_story_code VARCHAR(255) NOT NULL COMMENT '用户故事编码',
  sequence_no INT NULL COMMENT '序号',
  user_story_name TEXT NULL COMMENT '用户故事名称',
  user_story_tag VARCHAR(255) NULL COMMENT '用户故事标签',
  status VARCHAR(255) NULL COMMENT '状态',
  remark TEXT NULL COMMENT '备注',
  plan_test_completion_time VARCHAR(64) NULL COMMENT '计划提测完成时间',
  related_task_count DECIMAL(12,2) NULL COMMENT '关联任务',
  planned_person_days DECIMAL(12,2) NULL COMMENT '计划人天',
  owner_names VARCHAR(255) NULL COMMENT '负责人',
  tester_names VARCHAR(255) NULL COMMENT '测试人员名称',
  requirement_owner_names VARCHAR(255) NULL COMMENT '需求人员名称',
  product VARCHAR(255) NULL COMMENT '产品',
  created_time VARCHAR(64) NULL COMMENT '创建时间',
  created_by VARCHAR(255) NULL COMMENT '创建人',
  actual_person_days DECIMAL(12,2) NULL COMMENT '实际人天',
  planned_dev_person_days DECIMAL(12,2) NULL COMMENT '计划开发人天',
  related_defect_count DECIMAL(12,2) NULL COMMENT '关联缺陷',
  version VARCHAR(255) NULL COMMENT '版本',
  priority VARCHAR(64) NULL COMMENT '优先级',
  absolute_priority DECIMAL(12,2) NULL COMMENT '绝对优先级',
  related_case_count DECIMAL(12,2) NULL COMMENT '关联用例',
  plan_trunk_test_completion_time VARCHAR(64) NULL COMMENT '计划主干测试完成时间',
  modified_time VARCHAR(64) NULL COMMENT '修改时间',
  acceptance_criteria TEXT NULL COMMENT '验收标准',
  detail_url TEXT NULL COMMENT '详细说明(URL)',
  project_status VARCHAR(255) NULL COMMENT '立项状态',
  iteration_phase VARCHAR(255) NULL COMMENT '迭代阶段',
  iteration_goal VARCHAR(255) NULL COMMENT '迭代目标',
  release_plan VARCHAR(255) NULL COMMENT '发布计划',
  release_window VARCHAR(255) NULL COMMENT '发布窗口',
  scrum_team VARCHAR(255) NULL COMMENT 'Scrum团队',
  product_group VARCHAR(255) NULL COMMENT '产品组',
  project_name VARCHAR(255) NULL COMMENT '所属项目',
  ksm_or_bug_no VARCHAR(255) NULL COMMENT 'KSM或BUG编号',
  story_type VARCHAR(255) NULL COMMENT '类型',
  cloud_name VARCHAR(255) NULL COMMENT '所属云',
  application_name VARCHAR(255) NULL COMMENT '所属应用',
  related_story VARCHAR(255) NULL COMMENT '关联故事',
  related_requirement VARCHAR(255) NULL COMMENT '关联需求',
  completed_time VARCHAR(64) NULL COMMENT '完成时间',
  plan_baseline_test_completion_time VARCHAR(64) NULL COMMENT '计划基线测试完成时间',
  developer_names VARCHAR(255) NULL COMMENT '开发人员名称',
  has_upgrade_notice VARCHAR(255) NULL COMMENT '是否有升级注意事项',
  change_type VARCHAR(255) NULL COMMENT '变动类型',
  imported_at VARCHAR(64) NOT NULL COMMENT '导入时间(ISO8601)',
  updated_at VARCHAR(64) NOT NULL COMMENT '更新时间(ISO8601)',
  PRIMARY KEY (id),
  UNIQUE KEY uk_workspace_story_records_workspace_story (workspace_id, user_story_code),
  KEY idx_workspace_story_records_workspace_id (workspace_id),
  CONSTRAINT fk_workspace_story_records_workspace_id
    FOREIGN KEY (workspace_id) REFERENCES workspace_states(workspace_id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作区故事明细表';

-- 4) workspace_recommendations: create/upgrade table with comments
CREATE TABLE IF NOT EXISTS workspace_recommendations (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  requirement_id VARCHAR(255) NOT NULL COMMENT '需求唯一标识',
  payload_json LONGTEXT NOT NULL COMMENT '推荐记录JSON快照',
  created_at VARCHAR(64) NOT NULL COMMENT '创建时间(ISO8601)',
  updated_at VARCHAR(64) NOT NULL COMMENT '更新时间(ISO8601)',
  PRIMARY KEY (id),
  UNIQUE KEY uk_workspace_recommendations_workspace_requirement (workspace_id, requirement_id),
  KEY idx_workspace_recommendations_workspace_id (workspace_id),
  CONSTRAINT fk_workspace_recommendations_workspace_id
    FOREIGN KEY (workspace_id) REFERENCES workspace_states(workspace_id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作区推荐确认明细表';

ALTER TABLE workspace_recommendations
  MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  MODIFY COLUMN workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  MODIFY COLUMN requirement_id VARCHAR(255) NOT NULL COMMENT '需求唯一标识',
  MODIFY COLUMN payload_json LONGTEXT NOT NULL COMMENT '推荐记录JSON快照',
  MODIFY COLUMN created_at VARCHAR(64) NOT NULL COMMENT '创建时间(ISO8601)',
  MODIFY COLUMN updated_at VARCHAR(64) NOT NULL COMMENT '更新时间(ISO8601)',
  COMMENT = '工作区推荐确认明细表';

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_recommendations'
        AND index_name = 'uk_workspace_recommendations_workspace_requirement'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_recommendations ADD UNIQUE KEY uk_workspace_recommendations_workspace_requirement (workspace_id, requirement_id)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_recommendations'
        AND index_name = 'idx_workspace_recommendations_workspace_id'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_recommendations ADD KEY idx_workspace_recommendations_workspace_id (workspace_id)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.table_constraints
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_recommendations'
        AND constraint_name = 'fk_workspace_recommendations_workspace_id'
        AND constraint_type = 'FOREIGN KEY'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_recommendations ADD CONSTRAINT fk_workspace_recommendations_workspace_id FOREIGN KEY (workspace_id) REFERENCES workspace_states(workspace_id) ON DELETE CASCADE'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 5) workspace_confirmation_records: create/upgrade table with comments
CREATE TABLE IF NOT EXISTS workspace_confirmation_records (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  session_id VARCHAR(64) NOT NULL COMMENT '确认提交所属会话ID',
  confirmed_count INT NOT NULL COMMENT '本次确认条数',
  payload_json LONGTEXT NOT NULL COMMENT '确认记录快照(JSON)',
  created_at VARCHAR(64) NOT NULL COMMENT '确认时间(ISO8601)',
  PRIMARY KEY (id),
  KEY idx_workspace_confirmation_records_workspace_id (workspace_id),
  KEY idx_workspace_confirmation_records_session_id (session_id),
  CONSTRAINT fk_workspace_confirmation_records_workspace_id
    FOREIGN KEY (workspace_id) REFERENCES workspace_states(workspace_id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作区确认记录表';

ALTER TABLE workspace_confirmation_records
  MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  MODIFY COLUMN workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  MODIFY COLUMN session_id VARCHAR(64) NOT NULL COMMENT '确认提交所属会话ID',
  MODIFY COLUMN confirmed_count INT NOT NULL COMMENT '本次确认条数',
  MODIFY COLUMN payload_json LONGTEXT NOT NULL COMMENT '确认记录快照(JSON)',
  MODIFY COLUMN created_at VARCHAR(64) NOT NULL COMMENT '确认时间(ISO8601)',
  COMMENT = '工作区确认记录表';

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_confirmation_records'
        AND index_name = 'idx_workspace_confirmation_records_workspace_id'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_confirmation_records ADD KEY idx_workspace_confirmation_records_workspace_id (workspace_id)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_confirmation_records'
        AND index_name = 'idx_workspace_confirmation_records_session_id'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_confirmation_records ADD KEY idx_workspace_confirmation_records_session_id (session_id)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.table_constraints
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_confirmation_records'
        AND constraint_name = 'fk_workspace_confirmation_records_workspace_id'
        AND constraint_type = 'FOREIGN KEY'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_confirmation_records ADD CONSTRAINT fk_workspace_confirmation_records_workspace_id FOREIGN KEY (workspace_id) REFERENCES workspace_states(workspace_id) ON DELETE CASCADE'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 6) workspace_knowledge_update_records: create/upgrade table with comments
CREATE TABLE IF NOT EXISTS workspace_knowledge_update_records (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  session_id VARCHAR(64) NOT NULL COMMENT '知识更新所属会话ID',
  status VARCHAR(32) NOT NULL COMMENT '运行状态(success/skipped/failed)',
  payload_json LONGTEXT NOT NULL COMMENT '知识更新记录快照(JSON)',
  created_at VARCHAR(64) NOT NULL COMMENT '触发时间(ISO8601)',
  PRIMARY KEY (id),
  KEY idx_workspace_knowledge_update_records_workspace_id (workspace_id),
  KEY idx_workspace_knowledge_update_records_session_id (session_id),
  CONSTRAINT fk_workspace_knowledge_update_records_workspace_id
    FOREIGN KEY (workspace_id) REFERENCES workspace_states(workspace_id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作区知识更新记录表';

ALTER TABLE workspace_knowledge_update_records
  MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  MODIFY COLUMN workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  MODIFY COLUMN session_id VARCHAR(64) NOT NULL COMMENT '知识更新所属会话ID',
  MODIFY COLUMN status VARCHAR(32) NOT NULL COMMENT '运行状态(success/skipped/failed)',
  MODIFY COLUMN payload_json LONGTEXT NOT NULL COMMENT '知识更新记录快照(JSON)',
  MODIFY COLUMN created_at VARCHAR(64) NOT NULL COMMENT '触发时间(ISO8601)',
  COMMENT = '工作区知识更新记录表';

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_knowledge_update_records'
        AND index_name = 'idx_workspace_knowledge_update_records_workspace_id'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_knowledge_update_records ADD KEY idx_workspace_knowledge_update_records_workspace_id (workspace_id)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_knowledge_update_records'
        AND index_name = 'idx_workspace_knowledge_update_records_session_id'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_knowledge_update_records ADD KEY idx_workspace_knowledge_update_records_session_id (session_id)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.table_constraints
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_knowledge_update_records'
        AND constraint_name = 'fk_workspace_knowledge_update_records_workspace_id'
        AND constraint_type = 'FOREIGN KEY'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_knowledge_update_records ADD CONSTRAINT fk_workspace_knowledge_update_records_workspace_id FOREIGN KEY (workspace_id) REFERENCES workspace_states(workspace_id) ON DELETE CASCADE'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- 7) workspace_managed_members: create/upgrade table with comments
CREATE TABLE IF NOT EXISTS workspace_managed_members (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  member_name VARCHAR(255) NOT NULL COMMENT '成员姓名',
  role VARCHAR(64) NOT NULL COMMENT '成员角色',
  skills_json JSON NOT NULL COMMENT '技能列表(JSON数组)',
  experience_level VARCHAR(64) NOT NULL COMMENT '经验等级',
  workload DECIMAL(10,4) NOT NULL DEFAULT 0 COMMENT '当前负载',
  capacity DECIMAL(10,4) NOT NULL DEFAULT 1 COMMENT '可用容量',
  constraints_json JSON NOT NULL COMMENT '约束列表(JSON数组)',
  updated_at VARCHAR(64) NOT NULL COMMENT '更新时间(ISO8601)',
  PRIMARY KEY (id),
  UNIQUE KEY uk_workspace_managed_members_workspace_name (workspace_id, member_name),
  KEY idx_workspace_managed_members_workspace_role (workspace_id, role),
  CONSTRAINT fk_workspace_managed_members_workspace_id
    FOREIGN KEY (workspace_id) REFERENCES workspace_states(workspace_id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作区人员管理明细表';

ALTER TABLE workspace_managed_members
  ADD COLUMN IF NOT EXISTS id BIGINT NULL COMMENT '主键ID',
  ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  ADD COLUMN IF NOT EXISTS member_name VARCHAR(255) NOT NULL COMMENT '成员姓名',
  ADD COLUMN IF NOT EXISTS role VARCHAR(64) NOT NULL COMMENT '成员角色',
  ADD COLUMN IF NOT EXISTS skills_json JSON NOT NULL COMMENT '技能列表(JSON数组)',
  ADD COLUMN IF NOT EXISTS experience_level VARCHAR(64) NOT NULL COMMENT '经验等级',
  ADD COLUMN IF NOT EXISTS workload DECIMAL(10,4) NOT NULL DEFAULT 0 COMMENT '当前负载',
  ADD COLUMN IF NOT EXISTS capacity DECIMAL(10,4) NOT NULL DEFAULT 1 COMMENT '可用容量',
  ADD COLUMN IF NOT EXISTS constraints_json JSON NOT NULL COMMENT '约束列表(JSON数组)',
  ADD COLUMN IF NOT EXISTS updated_at VARCHAR(64) NOT NULL COMMENT '更新时间(ISO8601)';

SET @seq_managed_member := 0;
UPDATE workspace_managed_members
SET id = (@seq_managed_member := @seq_managed_member + 1)
WHERE id IS NULL
ORDER BY workspace_id, member_name;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_managed_members'
        AND index_name = 'uk_workspace_managed_members_id'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_managed_members ADD UNIQUE KEY uk_workspace_managed_members_id (id)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE workspace_managed_members
  MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  MODIFY COLUMN workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  MODIFY COLUMN member_name VARCHAR(255) NOT NULL COMMENT '成员姓名',
  MODIFY COLUMN role VARCHAR(64) NOT NULL COMMENT '成员角色',
  MODIFY COLUMN skills_json JSON NOT NULL COMMENT '技能列表(JSON数组)',
  MODIFY COLUMN experience_level VARCHAR(64) NOT NULL COMMENT '经验等级',
  MODIFY COLUMN workload DECIMAL(10,4) NOT NULL DEFAULT 0 COMMENT '当前负载',
  MODIFY COLUMN capacity DECIMAL(10,4) NOT NULL DEFAULT 1 COMMENT '可用容量',
  MODIFY COLUMN constraints_json JSON NOT NULL COMMENT '约束列表(JSON数组)',
  MODIFY COLUMN updated_at VARCHAR(64) NOT NULL COMMENT '更新时间(ISO8601)',
  COMMENT = '工作区人员管理明细表';

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.key_column_usage
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_managed_members'
        AND constraint_name = 'PRIMARY'
        AND column_name = 'id'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_managed_members ADD PRIMARY KEY (id)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_managed_members'
        AND index_name = 'uk_workspace_managed_members_workspace_name'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_managed_members ADD UNIQUE KEY uk_workspace_managed_members_workspace_name (workspace_id, member_name)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_managed_members'
        AND index_name = 'idx_workspace_managed_members_workspace_role'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_managed_members ADD KEY idx_workspace_managed_members_workspace_role (workspace_id, role)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.table_constraints
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_managed_members'
        AND constraint_name = 'fk_workspace_managed_members_workspace_id'
        AND constraint_type = 'FOREIGN KEY'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_managed_members ADD CONSTRAINT fk_workspace_managed_members_workspace_id FOREIGN KEY (workspace_id) REFERENCES workspace_states(workspace_id) ON DELETE CASCADE'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE workspace_states
  MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID';

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.key_column_usage
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_states'
        AND constraint_name = 'PRIMARY'
        AND column_name <> 'id'
    ),
    'ALTER TABLE workspace_states DROP PRIMARY KEY',
    'SELECT 1'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.key_column_usage
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_states'
        AND constraint_name = 'PRIMARY'
        AND column_name = 'id'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_states ADD PRIMARY KEY (id)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_states'
        AND index_name = 'uk_workspace_states_workspace_id'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_states ADD UNIQUE KEY uk_workspace_states_workspace_id (workspace_id)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE workspace_states
  MODIFY COLUMN workspace_id VARCHAR(255) NOT NULL COMMENT '工作区唯一标识',
  MODIFY COLUMN payload LONGTEXT NOT NULL COMMENT '工作区全量状态JSON快照',
  MODIFY COLUMN updated_at VARCHAR(64) NOT NULL COMMENT '更新时间(ISO8601)',
  COMMENT = '工作区状态快照表';

-- 2) agent_states: ensure BIGINT id primary key and comments
CREATE TABLE IF NOT EXISTS agent_states (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  state_key VARCHAR(64) NOT NULL COMMENT 'Agent状态键(通常为global)',
  payload LONGTEXT NOT NULL COMMENT 'Agent状态JSON快照',
  updated_at VARCHAR(64) NOT NULL COMMENT '更新时间(ISO8601)',
  PRIMARY KEY (id),
  UNIQUE KEY uk_agent_states_state_key (state_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Agent状态快照表';

ALTER TABLE agent_states
  ADD COLUMN IF NOT EXISTS id BIGINT NULL COMMENT '主键ID';

SET @seq_agent := 0;
UPDATE agent_states
SET id = (@seq_agent := @seq_agent + 1)
WHERE id IS NULL
ORDER BY state_key;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = DATABASE()
        AND table_name = 'agent_states'
        AND index_name = 'uk_agent_states_id'
    ),
    'SELECT 1',
    'ALTER TABLE agent_states ADD UNIQUE KEY uk_agent_states_id (id)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE agent_states
  MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID';

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.key_column_usage
      WHERE table_schema = DATABASE()
        AND table_name = 'agent_states'
        AND constraint_name = 'PRIMARY'
        AND column_name <> 'id'
    ),
    'ALTER TABLE agent_states DROP PRIMARY KEY',
    'SELECT 1'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.key_column_usage
      WHERE table_schema = DATABASE()
        AND table_name = 'agent_states'
        AND constraint_name = 'PRIMARY'
        AND column_name = 'id'
    ),
    'SELECT 1',
    'ALTER TABLE agent_states ADD PRIMARY KEY (id)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = DATABASE()
        AND table_name = 'agent_states'
        AND index_name = 'uk_agent_states_state_key'
    ),
    'SELECT 1',
    'ALTER TABLE agent_states ADD UNIQUE KEY uk_agent_states_state_key (state_key)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE agent_states
  MODIFY COLUMN state_key VARCHAR(64) NOT NULL COMMENT 'Agent状态键(通常为global)',
  MODIFY COLUMN payload LONGTEXT NOT NULL COMMENT 'Agent状态JSON快照',
  MODIFY COLUMN updated_at VARCHAR(64) NOT NULL COMMENT '更新时间(ISO8601)',
  COMMENT = 'Agent状态快照表';

-- 3) workspace_module_entries: create/upgrade table with comments
CREATE TABLE IF NOT EXISTS workspace_module_entries (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  module_key VARCHAR(255) NOT NULL COMMENT '模块唯一键(大模块::功能模块)',
  big_module VARCHAR(255) NOT NULL COMMENT '大模块名称',
  function_module VARCHAR(255) NOT NULL COMMENT '功能模块名称',
  primary_owner VARCHAR(255) NOT NULL COMMENT '主要负责人(人员管理成员)',
  backup_owners_json JSON NOT NULL COMMENT 'B角成员列表(JSON数组)',
  familiar_members_json JSON NOT NULL COMMENT '熟悉成员列表(JSON数组)',
  aware_members_json JSON NOT NULL COMMENT '了解成员列表(JSON数组)',
  unfamiliar_members_json JSON NOT NULL COMMENT '不了解成员列表(JSON数组)',
  source_sheet VARCHAR(255) NOT NULL DEFAULT '' COMMENT '来源sheet或来源标识',
  source_year INT NOT NULL DEFAULT 0 COMMENT '来源年份',
  imported_at VARCHAR(64) NOT NULL COMMENT '导入/创建时间(ISO8601)',
  recent_assignees_json JSON NOT NULL COMMENT '最近分配成员列表(JSON数组)',
  suggested_familiarity_json JSON NOT NULL COMMENT '建议熟悉度调整(JSON对象)',
  assignment_history_json LONGTEXT NOT NULL COMMENT '分配历史(JSON数组)',
  updated_at VARCHAR(64) NOT NULL COMMENT '更新时间(ISO8601)',
  PRIMARY KEY (id),
  UNIQUE KEY uk_workspace_module_entries_workspace_key (workspace_id, module_key),
  KEY idx_workspace_module_entries_workspace_big_module (workspace_id, big_module),
  CONSTRAINT fk_workspace_module_entries_workspace_id
    FOREIGN KEY (workspace_id) REFERENCES workspace_states(workspace_id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作区业务模块明细表';

ALTER TABLE workspace_module_entries
  ADD COLUMN IF NOT EXISTS id BIGINT NULL COMMENT '主键ID',
  ADD COLUMN IF NOT EXISTS workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  ADD COLUMN IF NOT EXISTS module_key VARCHAR(255) NOT NULL COMMENT '模块唯一键(大模块::功能模块)',
  ADD COLUMN IF NOT EXISTS big_module VARCHAR(255) NOT NULL COMMENT '大模块名称',
  ADD COLUMN IF NOT EXISTS function_module VARCHAR(255) NOT NULL COMMENT '功能模块名称',
  ADD COLUMN IF NOT EXISTS primary_owner VARCHAR(255) NOT NULL COMMENT '主要负责人(人员管理成员)',
  ADD COLUMN IF NOT EXISTS backup_owners_json JSON NOT NULL COMMENT 'B角成员列表(JSON数组)',
  ADD COLUMN IF NOT EXISTS familiar_members_json JSON NOT NULL COMMENT '熟悉成员列表(JSON数组)',
  ADD COLUMN IF NOT EXISTS aware_members_json JSON NOT NULL COMMENT '了解成员列表(JSON数组)',
  ADD COLUMN IF NOT EXISTS unfamiliar_members_json JSON NOT NULL COMMENT '不了解成员列表(JSON数组)',
  ADD COLUMN IF NOT EXISTS source_sheet VARCHAR(255) NOT NULL DEFAULT '' COMMENT '来源sheet或来源标识',
  ADD COLUMN IF NOT EXISTS source_year INT NOT NULL DEFAULT 0 COMMENT '来源年份',
  ADD COLUMN IF NOT EXISTS imported_at VARCHAR(64) NOT NULL COMMENT '导入/创建时间(ISO8601)',
  ADD COLUMN IF NOT EXISTS recent_assignees_json JSON NOT NULL COMMENT '最近分配成员列表(JSON数组)',
  ADD COLUMN IF NOT EXISTS suggested_familiarity_json JSON NOT NULL COMMENT '建议熟悉度调整(JSON对象)',
  ADD COLUMN IF NOT EXISTS assignment_history_json LONGTEXT NOT NULL COMMENT '分配历史(JSON数组)',
  ADD COLUMN IF NOT EXISTS updated_at VARCHAR(64) NOT NULL COMMENT '更新时间(ISO8601)';

SET @seq_module_entry := 0;
UPDATE workspace_module_entries
SET id = (@seq_module_entry := @seq_module_entry + 1)
WHERE id IS NULL
ORDER BY workspace_id, module_key;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_module_entries'
        AND index_name = 'uk_workspace_module_entries_id'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_module_entries ADD UNIQUE KEY uk_workspace_module_entries_id (id)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

ALTER TABLE workspace_module_entries
  MODIFY COLUMN id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  MODIFY COLUMN workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  MODIFY COLUMN module_key VARCHAR(255) NOT NULL COMMENT '模块唯一键(大模块::功能模块)',
  MODIFY COLUMN big_module VARCHAR(255) NOT NULL COMMENT '大模块名称',
  MODIFY COLUMN function_module VARCHAR(255) NOT NULL COMMENT '功能模块名称',
  MODIFY COLUMN primary_owner VARCHAR(255) NOT NULL COMMENT '主要负责人(人员管理成员)',
  MODIFY COLUMN backup_owners_json JSON NOT NULL COMMENT 'B角成员列表(JSON数组)',
  MODIFY COLUMN familiar_members_json JSON NOT NULL COMMENT '熟悉成员列表(JSON数组)',
  MODIFY COLUMN aware_members_json JSON NOT NULL COMMENT '了解成员列表(JSON数组)',
  MODIFY COLUMN unfamiliar_members_json JSON NOT NULL COMMENT '不了解成员列表(JSON数组)',
  MODIFY COLUMN source_sheet VARCHAR(255) NOT NULL DEFAULT '' COMMENT '来源sheet或来源标识',
  MODIFY COLUMN source_year INT NOT NULL DEFAULT 0 COMMENT '来源年份',
  MODIFY COLUMN imported_at VARCHAR(64) NOT NULL COMMENT '导入/创建时间(ISO8601)',
  MODIFY COLUMN recent_assignees_json JSON NOT NULL COMMENT '最近分配成员列表(JSON数组)',
  MODIFY COLUMN suggested_familiarity_json JSON NOT NULL COMMENT '建议熟悉度调整(JSON对象)',
  MODIFY COLUMN assignment_history_json LONGTEXT NOT NULL COMMENT '分配历史(JSON数组)',
  MODIFY COLUMN updated_at VARCHAR(64) NOT NULL COMMENT '更新时间(ISO8601)',
  COMMENT = '工作区业务模块明细表';

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.key_column_usage
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_module_entries'
        AND constraint_name = 'PRIMARY'
        AND column_name = 'id'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_module_entries ADD PRIMARY KEY (id)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_module_entries'
        AND index_name = 'uk_workspace_module_entries_workspace_key'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_module_entries ADD UNIQUE KEY uk_workspace_module_entries_workspace_key (workspace_id, module_key)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.statistics
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_module_entries'
        AND index_name = 'idx_workspace_module_entries_workspace_big_module'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_module_entries ADD KEY idx_workspace_module_entries_workspace_big_module (workspace_id, big_module)'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @sql := (
  SELECT IF(
    EXISTS(
      SELECT 1
      FROM information_schema.table_constraints
      WHERE table_schema = DATABASE()
        AND table_name = 'workspace_module_entries'
        AND constraint_name = 'fk_workspace_module_entries_workspace_id'
        AND constraint_type = 'FOREIGN KEY'
    ),
    'SELECT 1',
    'ALTER TABLE workspace_module_entries ADD CONSTRAINT fk_workspace_module_entries_workspace_id FOREIGN KEY (workspace_id) REFERENCES workspace_states(workspace_id) ON DELETE CASCADE'
  )
);
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
