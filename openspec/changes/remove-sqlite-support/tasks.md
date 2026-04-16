## 1. 数据库核心层 MySQL-only 化

- [x] 1.1 重构 `pm_agent/database.py`，删除 `sqlite://` 解析、`sqlite3` 依赖、SQLite 自动建表和占位符分支，只保留 MySQL 连接与错误处理
- [x] 1.2 统一数据库辅助接口的返回、占位符和异常语义，移除所有围绕 `scheme == "sqlite"` 的运行时判断
- [x] 1.3 校验启动入口与配置加载，对 SQLite URL 明确报错并给出 MySQL-only 指引

## 2. 仓储层与脚本清理

- [x] 2.1 重构 `pm_agent/workspace_store.py`，删除全部 SQLite 专用 SQL 分支、分页分支和行读取兼容逻辑
- [x] 2.2 重构 `pm_agent/repositories/requirement_repo.py` 等仓储代码，统一为 MySQL SQL 语义，不再保留 SQLite 特判
- [x] 2.3 清理 `pm_agent/migrate_workspace_states.py` 与其他维护脚本中的 SQLite URL、SQLite 连接和相关帮助文案，必要时改为纯 MySQL 脚本或删除脚本

## 3. 配置、文档与项目规范收口

- [x] 3.1 更新 `config/pm_agent.toml`、运行配置加载和启动帮助，只保留 MySQL 配置示例与环境约定
- [x] 3.2 更新 `README.md` 与相关文档，形成“项目只支持 MySQL”的明确规范，覆盖启动、建库、DDL、迁移和本地开发说明
- [x] 3.3 清理代码库中所有 SQLite 示例、注释、字符串常量和文档残留，确保项目对外表述为 MySQL-only

## 4. 测试基线与回归验证

- [x] 4.1 删除或替换基于 `sqlite:///`、`sqlite3.connect(...)` 的数据库测试夹具和断言路径
- [x] 4.2 重写数据库相关测试，使持久化、分页、历史记录、仓储行为等验证基于 MySQL 测试库或统一 MySQL 测试夹具
- [x] 4.3 执行 MySQL 相关回归测试，确认启动校验、仓储层、工作区状态、确认历史、分页与迁移脚本均满足 MySQL-only 规范
