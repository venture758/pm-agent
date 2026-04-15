## Why

当前项目虽然已经把大部分业务数据写入数据库，但仍保留了多条本地存储路径：默认本地 SQLite、`state.json/workspace.json` 兼容迁移、上传文件落盘到 `.pm_agent_store/workspaces/.../uploads`。这导致“数据库不是唯一事实来源”，部署环境和数据治理都会出现分叉；既然你的数据全部来自数据库，这些本地持久化路径应该被彻底移除，而不是继续作为 fallback 存在。

## What Changes

- 移除默认本地状态根目录、默认本地 SQLite 数据库和基于本地文件的状态/工作区迁移逻辑
- **BREAKING**：应用启动时必须显式连接数据库；未提供数据库连接时，系统 MUST 拒绝启动，而不是自动创建本地数据库
- 移除 `state.json`、`workspace.json` 和 `.pm_agent_store/workspaces/.../uploads` 这类本地持久化路径
- **BREAKING**：上传处理不再将原始 Excel 文件保存到本地文件系统；如需保留上传历史，仅保留数据库中的元数据或二进制内容
- 将 Agent 状态、工作区状态、确认历史、知识更新记录、上传记录等全部视为数据库内数据，不再依赖本地目录作为兼容或回退来源
- 更新测试和运维说明，明确数据库是唯一持久化后端

## Capabilities

### New Capabilities
- `database-only-storage`: 以数据库作为唯一持久化来源，覆盖启动、状态存储、上传处理和历史记录存储，不再允许本地文件或本地默认数据库作为 fallback

### Modified Capabilities
- 无

## Impact

- `pm_agent/config.py` / `pm_agent/database.py`: 移除默认本地存储根目录和自动本地 SQLite 连接逻辑
- `pm_agent/storage.py` / `pm_agent/workspace_store.py`: 移除 `state.json`、`workspace.json`、`uploads/` 目录读写和迁移逻辑
- `pm_agent/api_service.py` / Excel 导入链路：上传文件改为数据库或内存处理，不再依赖本地落盘路径
- 数据库 schema / migration：如需保留上传历史，需要增加数据库字段或表来承接原有本地上传元数据/内容
- 启动参数、README、测试：需要改为显式数据库配置，并删除“本地自动存储”语义
