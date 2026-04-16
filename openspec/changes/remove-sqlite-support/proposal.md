## Why

当前项目虽然以 MySQL 作为主数据库，但代码、运行配置、迁移脚本、测试和文档里仍保留了大量 SQLite 分支。这会让项目在数据库能力、SQL 方言、DDL 管理、测试基线和运行规范上长期处于“双栈”状态；既然你的生产与项目规范都明确使用 MySQL，就应该把 SQLite 从项目中彻底移除，并把 MySQL 作为唯一允许的数据库后端。

## What Changes

- **BREAKING**：项目运行时仅支持 MySQL；`database_url` 不再接受 `sqlite://` 协议，也不再保留任何 SQLite 兼容分支
- **BREAKING**：删除 `pm_agent/database.py`、仓储层和工作区存储层中的 SQLite 连接、占位符、建表与查询分支，统一按 MySQL 语义实现
- **BREAKING**：删除仅用于 SQLite 的测试、测试夹具、运行示例和配置项，所有数据库相关测试改为基于 MySQL 或对数据库接口做纯逻辑隔离
- 统一项目规范：数据库初始化、迁移、测试前置条件、配置示例、README 和运行文档全部明确为 MySQL-only
- 清理独立脚本与工具中的 SQLite 兼容说明和路径，确保迁移、运维、开发、自测都围绕 MySQL 展开

## Capabilities

### New Capabilities
- `mysql-only-project-standard`: 规定项目只允许 MySQL 作为数据库后端，覆盖运行时、仓储层、配置、脚本、测试和文档规范

### Modified Capabilities
- 无

## Impact

- `pm_agent/database.py`、`pm_agent/workspace_store.py`、`pm_agent/repositories/requirement_repo.py`：删除 SQLite 分支和本地 sqlite3 依赖
- `pm_agent_web.py`、`pm_agent/runtime_config.py`、`config/pm_agent.toml`：配置文件与启动约定收敛为 MySQL-only
- `pm_agent/migrate_workspace_states.py` 及相关运维脚本：移除 SQLite URL 解析和 SQLite 迁移语义
- `tests/`：删除或重写基于 SQLite 的单测与集成测试基线
- `README.md` 与项目规范文档：统一为 MySQL 初始化、运行和验证方式
