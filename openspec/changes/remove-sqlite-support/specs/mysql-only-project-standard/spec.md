## ADDED Requirements

### Requirement: Application MUST support MySQL as the only database backend
系统 MUST 仅支持 MySQL 作为数据库后端。运行时配置、数据库连接解析和驱动加载 MUST 拒绝 SQLite 及其他非 MySQL 数据库协议。

#### Scenario: Startup with MySQL configuration
- **WHEN** 应用启动时提供合法的 MySQL 数据库连接配置
- **THEN** 系统使用该 MySQL 连接作为唯一持久化后端启动成功

#### Scenario: Startup with SQLite configuration
- **WHEN** 应用启动时提供 `sqlite://` 或等价 SQLite 数据库连接配置
- **THEN** 系统返回明确错误并拒绝启动

### Requirement: Runtime storage and repositories MUST NOT contain SQLite branches
数据库访问层、仓储层和工作区存储层 MUST 不再包含 SQLite 专用连接、建表、占位符或 SQL 分支逻辑；所有持久化行为 SHALL 基于 MySQL 语义实现。

#### Scenario: Database layer initialization
- **WHEN** 系统初始化数据库访问层
- **THEN** 运行时不得创建 SQLite schema，也不得加载 `sqlite3` 作为可选后端

#### Scenario: Repository persistence
- **WHEN** 仓储层或工作区存储层执行查询、插入、更新或删除
- **THEN** 相关 SQL 与异常处理逻辑仅基于 MySQL 实现，不再根据 SQLite 做条件分支

### Requirement: Project configuration and scripts MUST standardize on MySQL-only rules
项目配置文件、启动入口、迁移脚本、运维命令和使用文档 MUST 统一以 MySQL 为唯一数据库规范，不得再给出 SQLite 示例、回退路径或测试基线说明。

#### Scenario: Runtime configuration
- **WHEN** 开发者查看默认配置文件或启动帮助信息
- **THEN** 其中只出现 MySQL 连接配置和 MySQL 环境约定

#### Scenario: Migration and maintenance scripts
- **WHEN** 开发者执行数据库迁移或维护脚本
- **THEN** 脚本输入、帮助信息和实现逻辑只支持 MySQL，不再解析或处理 SQLite URL

### Requirement: Database-related tests MUST validate MySQL-only behavior
凡是验证数据库持久化、DDL、查询语义、分页、历史记录或仓储行为的测试 MUST 以 MySQL 作为唯一数据库基线，且不得使用 SQLite 作为替代验证手段。

#### Scenario: Running persistence tests
- **WHEN** 执行数据库相关测试套件
- **THEN** 测试前置条件、夹具或环境变量应指向 MySQL，而不是临时 SQLite 数据库

#### Scenario: Reviewing test fixtures
- **WHEN** 开发者维护数据库相关测试代码
- **THEN** 代码库中不得新增基于 `sqlite:///` 或 `sqlite3.connect(...)` 的测试夹具与断言路径
