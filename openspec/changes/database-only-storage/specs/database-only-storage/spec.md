## ADDED Requirements

### Requirement: Application MUST require an explicit database backend
系统 MUST 在启动时要求显式提供数据库连接；未提供数据库连接时，系统 MUST 拒绝启动，而不是自动创建任何本地数据库或本地状态目录。

#### Scenario: Startup without database configuration
- **WHEN** 应用启动时未提供数据库连接配置
- **THEN** 系统返回明确错误并拒绝启动

#### Scenario: Startup with configured database
- **WHEN** 应用启动时已提供数据库连接配置
- **THEN** 系统使用该数据库作为唯一持久化后端

### Requirement: Runtime storage MUST not read or write local state files
系统 MUST 不再读取、写入或迁移本地 `state.json`、`workspace.json` 或任何等价的本地状态文件；agent 状态和工作区状态 MUST 仅来自数据库。

#### Scenario: Existing local workspace files are ignored
- **WHEN** 本地目录中存在历史 `workspace.json` 或 `state.json`
- **THEN** 运行时主流程不得读取这些文件作为状态来源

#### Scenario: Persisting workspace state
- **WHEN** 系统保存 agent 状态或工作区状态
- **THEN** 状态仅写入数据库，不创建本地状态文件或目录

### Requirement: Upload processing MUST not persist files to local filesystem
系统 MUST 不再将上传的 Excel 原始文件持久化到本地文件系统；上传处理 SHALL 在内存中完成解析，并仅将业务数据和必要元数据写入数据库。

#### Scenario: Upload module knowledge Excel
- **WHEN** 用户上传模块知识 Excel
- **THEN** 系统不在本地文件系统创建上传文件副本，且模块知识结果写入数据库

#### Scenario: Upload story or task Excel
- **WHEN** 用户上传故事或任务 Excel
- **THEN** 系统不在本地文件系统创建上传文件副本，且解析后的故事/任务数据写入数据库

### Requirement: Database SHALL remain the only source of persisted business history
系统 MUST 将确认历史、知识更新记录、上传元数据和其他业务历史视为数据库内数据，不得依赖本地目录或本地文件作为兼容回退来源。

#### Scenario: Query confirmation history
- **WHEN** 用户查询确认历史
- **THEN** 返回结果仅来自数据库中的确认记录数据

#### Scenario: Query latest workspace state
- **WHEN** 前端请求工作区详情
- **THEN** 返回结果仅来自数据库中的工作区状态和相关业务表
