-- pm-agent MySQL schema
-- Usage:
--   mysql -h127.0.0.1 -uroot -p pm_agent < db/schema.mysql.ddl.sql

-- ============================================================
-- Core: workspaces metadata
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

CREATE TABLE IF NOT EXISTS agent_states (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  state_key VARCHAR(64) NOT NULL COMMENT 'Agent状态键(通常为global)',
  payload LONGTEXT NOT NULL COMMENT 'Agent状态JSON快照',
  updated_at VARCHAR(64) NOT NULL COMMENT '更新时间(ISO8601)',
  PRIMARY KEY (id),
  UNIQUE KEY uk_agent_states_state_key (state_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Agent状态快照表';

-- ============================================================
-- Chat domain
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
-- Requirements domain
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

CREATE TABLE IF NOT EXISTS session_requirements (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  session_id VARCHAR(64) NOT NULL COMMENT '关联会话ID',
  requirement_id VARCHAR(255) NOT NULL COMMENT '关联需求ID',
  PRIMARY KEY (id),
  UNIQUE KEY uk_session_requirements_session_req (session_id, requirement_id),
  KEY idx_session_requirements_requirement (requirement_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会话-需求关联表';

-- ============================================================
-- Related tables (no FK to workspace_states — independent by workspace_id)
-- ============================================================

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
  KEY idx_workspace_module_entries_workspace_big_module (workspace_id, big_module)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作区业务模块明细表';

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
  KEY idx_workspace_managed_members_workspace_role (workspace_id, role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作区人员管理明细表';

CREATE TABLE IF NOT EXISTS workspace_recommendations (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  requirement_id VARCHAR(255) NOT NULL COMMENT '需求唯一标识',
  payload_json LONGTEXT NOT NULL COMMENT '推荐记录JSON快照',
  created_at VARCHAR(64) NOT NULL COMMENT '创建时间(ISO8601)',
  updated_at VARCHAR(64) NOT NULL COMMENT '更新时间(ISO8601)',
  PRIMARY KEY (id),
  UNIQUE KEY uk_workspace_recommendations_workspace_requirement (workspace_id, requirement_id),
  KEY idx_workspace_recommendations_workspace_id (workspace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作区推荐确认明细表';

CREATE TABLE IF NOT EXISTS workspace_confirmation_records (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  session_id VARCHAR(64) NOT NULL COMMENT '确认提交所属会话ID',
  confirmed_count INT NOT NULL COMMENT '本次确认条数',
  payload_json LONGTEXT NOT NULL COMMENT '确认记录快照(JSON)',
  created_at VARCHAR(64) NOT NULL COMMENT '确认时间(ISO8601)',
  PRIMARY KEY (id),
  KEY idx_workspace_confirmation_records_workspace_id (workspace_id),
  KEY idx_workspace_confirmation_records_session_id (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作区确认记录表';

CREATE TABLE IF NOT EXISTS workspace_knowledge_update_records (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  session_id VARCHAR(64) NOT NULL COMMENT '知识更新所属会话ID',
  status VARCHAR(32) NOT NULL COMMENT '运行状态(success/skipped/failed)',
  payload_json LONGTEXT NOT NULL COMMENT '知识更新记录快照(JSON)',
  created_at VARCHAR(64) NOT NULL COMMENT '触发时间(ISO8601)',
  PRIMARY KEY (id),
  KEY idx_workspace_knowledge_update_records_workspace_id (workspace_id),
  KEY idx_workspace_knowledge_update_records_session_id (session_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作区知识更新记录表';

CREATE TABLE IF NOT EXISTS workspace_knowledge_update_module_diff_records (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  session_id VARCHAR(64) NOT NULL COMMENT '知识更新所属会话ID',
  requirement_id VARCHAR(255) NOT NULL COMMENT '需求唯一标识',
  module_key VARCHAR(255) NOT NULL COMMENT '模块唯一键(大模块::功能模块)',
  changed TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否产生实际字段变更',
  payload_json LONGTEXT NOT NULL COMMENT '模块更新前后记录快照(JSON)',
  created_at VARCHAR(64) NOT NULL COMMENT '创建时间(ISO8601)',
  PRIMARY KEY (id),
  KEY idx_workspace_knowledge_update_module_diff_workspace (workspace_id),
  KEY idx_workspace_knowledge_update_module_diff_session_req (session_id, requirement_id),
  KEY idx_workspace_knowledge_update_module_diff_module_key (module_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作区知识更新模块前后记录表';

CREATE TABLE IF NOT EXISTS workspace_insight_snapshots (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  snapshot_at VARCHAR(64) NOT NULL COMMENT '快照时间(ISO8601)',
  heatmap_json JSON NOT NULL COMMENT '成员负载热力图快照(JSON数组)',
  single_points_json JSON NOT NULL COMMENT '单点依赖风险快照(JSON数组)',
  growth_suggestions_json JSON NOT NULL COMMENT '成长建议快照(JSON数组)',
  summary_json JSON NOT NULL COMMENT '聚合指标(JSON对象：team_health_score, high_load_count 等)',
  PRIMARY KEY (id),
  KEY idx_workspace_insight_snapshots_workspace_time (workspace_id, snapshot_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='团队洞察快照表';

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
  KEY idx_workspace_story_records_workspace_id (workspace_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作区故事明细表';

CREATE TABLE IF NOT EXISTS workspace_task_records (
  id BIGINT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  workspace_id VARCHAR(255) NOT NULL COMMENT '关联工作区标识',
  task_code VARCHAR(255) NOT NULL COMMENT '任务编号',
  sequence_no INT NULL COMMENT '序号',
  related_story VARCHAR(255) NULL COMMENT '关联用户故事',
  name TEXT NULL COMMENT '任务名称',
  task_type VARCHAR(255) NULL COMMENT '任务类型',
  owner VARCHAR(255) NULL COMMENT '负责人',
  status VARCHAR(255) NULL COMMENT '状态',
  estimated_start VARCHAR(64) NULL COMMENT '预计开始时间',
  estimated_end VARCHAR(64) NULL COMMENT '预计结束时间',
  remark TEXT NULL COMMENT '备注',
  completed_time VARCHAR(64) NULL COMMENT '完成时间',
  planned_person_days DECIMAL(12,2) NULL COMMENT '计划人天',
  actual_person_days DECIMAL(12,2) NULL COMMENT '实际人天',
  product VARCHAR(255) NULL COMMENT '产品',
  module_path VARCHAR(255) NULL COMMENT '模块路径',
  project_name VARCHAR(255) NULL COMMENT '所属项目',
  version VARCHAR(255) NULL COMMENT '版本',
  iteration_phase VARCHAR(255) NULL COMMENT '迭代阶段',
  project_group VARCHAR(255) NULL COMMENT '项目组',
  participants VARCHAR(255) NULL COMMENT '参与人',
  customer_name VARCHAR(255) NULL COMMENT '客户名称',
  defect_count DECIMAL(12,2) NULL COMMENT '缺陷总数',
  related_code VARCHAR(255) NULL COMMENT '关联代码',
  created_by VARCHAR(255) NULL COMMENT '创建人',
  created_time VARCHAR(64) NULL COMMENT '创建时间',
  modified_by VARCHAR(255) NULL COMMENT '修改人',
  modified_time VARCHAR(64) NULL COMMENT '修改时间',
  imported_at VARCHAR(64) NOT NULL COMMENT '导入时间(ISO8601)',
  updated_at VARCHAR(64) NOT NULL COMMENT '更新时间(ISO8601)',
  PRIMARY KEY (id),
  UNIQUE KEY uk_workspace_task_records_workspace_task (workspace_id, task_code),
  KEY idx_workspace_task_records_workspace_id (workspace_id),
  KEY idx_workspace_task_records_owner (workspace_id, owner),
  KEY idx_workspace_task_records_status (workspace_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='工作区任务明细表';
