from __future__ import annotations

import unittest
from pathlib import Path


class MysqlSchemaFileTest(unittest.TestCase):
    def test_schema_file_contains_required_tables(self) -> None:
        schema_path = Path("db/schema.mysql.ddl.sql")
        self.assertTrue(schema_path.exists(), "缺少唯一 MySQL DDL 文件：db/schema.mysql.ddl.sql")
        text = schema_path.read_text(encoding="utf-8").lower()
        self.assertIn("create table if not exists workspace_states", text)
        self.assertIn("create table if not exists agent_states", text)
        self.assertIn("create table if not exists workspace_module_entries", text)
        self.assertIn("create table if not exists workspace_managed_members", text)
        self.assertIn("create table if not exists workspace_recommendations", text)
        self.assertIn("create table if not exists workspace_confirmation_records", text)
        self.assertIn("create table if not exists workspace_knowledge_update_records", text)
        self.assertIn("create table if not exists workspace_story_records", text)
        self.assertIn("id bigint not null auto_increment", text)
        self.assertIn("primary key (id)", text)
        self.assertIn("unique key uk_workspace_states_workspace_id (workspace_id)", text)
        self.assertIn("unique key uk_agent_states_state_key (state_key)", text)
        self.assertIn("unique key uk_workspace_module_entries_workspace_key (workspace_id, module_key)", text)
        self.assertIn(
            "unique key uk_workspace_managed_members_workspace_name (workspace_id, member_name)",
            text,
        )
        self.assertIn(
            "unique key uk_workspace_recommendations_workspace_requirement (workspace_id, requirement_id)",
            text,
        )
        self.assertIn("key idx_workspace_confirmation_records_workspace_id (workspace_id)", text)
        self.assertIn("key idx_workspace_knowledge_update_records_workspace_id (workspace_id)", text)
        self.assertIn("backup_owners_json json not null", text)
        self.assertIn("familiar_members_json json not null", text)
        self.assertIn("aware_members_json json not null", text)
        self.assertIn("unfamiliar_members_json json not null", text)
        self.assertIn("skills_json json not null", text)
        self.assertIn("constraints_json json not null", text)
        self.assertIn("comment='工作区状态快照表'".lower(), text)
        self.assertIn("comment='agent状态快照表'".lower(), text)
        self.assertIn("comment='工作区业务模块明细表'".lower(), text)
        self.assertIn("comment='工作区人员管理明细表'".lower(), text)
        self.assertIn("comment='工作区推荐确认明细表'".lower(), text)
        self.assertIn("comment='工作区确认记录表'".lower(), text)
        self.assertIn("comment='工作区知识更新记录表'".lower(), text)
        self.assertIn("comment='工作区故事明细表'".lower(), text)
        self.assertIn("comment '主键id'".lower(), text)
        self.assertIn("comment '模块唯一键(大模块::功能模块)'".lower(), text)
        self.assertIn("comment '成员姓名'".lower(), text)
        self.assertIn("comment '需求唯一标识'".lower(), text)
        self.assertIn("comment '确认提交所属会话id'".lower(), text)
        self.assertIn("comment '知识更新所属会话id'".lower(), text)

    def test_migration_script_exists_and_mentions_comments(self) -> None:
        migration_path = Path("db/migrate.mysql.module-entries.sql")
        self.assertTrue(migration_path.exists(), "缺少迁移脚本：db/migrate.mysql.module-entries.sql")
        text = migration_path.read_text(encoding="utf-8").lower()
        self.assertIn("alter table workspace_states", text)
        self.assertIn("alter table agent_states", text)
        self.assertIn("alter table workspace_module_entries", text)
        self.assertIn("alter table workspace_managed_members", text)
        self.assertIn("alter table workspace_recommendations", text)
        self.assertIn("alter table workspace_confirmation_records", text)
        self.assertIn("alter table workspace_knowledge_update_records", text)
        self.assertIn("comment = '工作区业务模块明细表'".lower(), text)
        self.assertIn("comment = '工作区人员管理明细表'".lower(), text)
        self.assertIn("comment = '工作区推荐确认明细表'".lower(), text)
        self.assertIn("comment = '工作区确认记录表'".lower(), text)
        self.assertIn("comment = '工作区知识更新记录表'".lower(), text)


if __name__ == "__main__":
    unittest.main()
