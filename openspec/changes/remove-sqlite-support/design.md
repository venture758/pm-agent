## Context

当前代码中 SQLite 仍然是一个真实存在的二级数据库后端，而不是历史痕迹：
- `pm_agent/database.py` 仍负责 `sqlite://` 解析、`sqlite3` 连接、占位符切换和 SQLite 自动建表
- `workspace_store.py`、`requirement_repo.py` 等仓储层仍维护 `if scheme == "sqlite"` 的 SQL 分支
- `migrate_workspace_states.py`、运行配置和 README 仍接受 SQLite URL 和 SQLite 启动示例
- 多个测试直接通过 `sqlite:///...` 与 `sqlite3.connect(...)` 建立测试基线

这导致项目的数据库语义、DDL 来源、SQL 方言、测试方式和运维规范都处于双实现状态。既然项目规范明确使用 MySQL，就应该把 MySQL 定义为唯一允许的数据库后端，并把 SQLite 相关实现从代码库中彻底移除。

## Goals / Non-Goals

**Goals:**
- 项目运行时只支持 MySQL 连接串和 MySQL 驱动
- 删除数据库层、仓储层、存储层中的 SQLite 分支与 `sqlite3` 依赖
- 以 `db/schema.mysql.ddl.sql` 作为唯一 schema 基线，不再保留 SQLite 自动建表语义
- 清理配置文件、迁移脚本、README、测试和示例中的 SQLite 内容，形成明确的 MySQL-only 项目规范
- 让数据库相关测试与验收标准围绕 MySQL 展开，而不是用 SQLite 作为替代基线

**Non-Goals:**
- 不重构现有业务表模型和 API 语义
- 不引入 ORM、数据库抽象框架或新的持久化组件
- 不在本次变更中设计跨数据库兼容层
- 不保证继续支持把历史 SQLite 文件作为运行时或测试时回退来源

## Decisions

### 1. 数据库后端只保留 MySQL 协议与驱动
`DatabaseStore` 只接受 MySQL 连接串（如 `mysql://`、`mysql+pymysql://` 等允许的 MySQL 方言），并只加载 MySQL 驱动；删除 `sqlite://` URL 解析、`sqlite3` 连接和 SQLite row factory。

这样做的原因：
- 明确项目的唯一数据库标准
- 避免在连接、事务、占位符和 SQL 方言上维持双实现
- 保证线上、开发、自测和规范完全一致

**Alternatives considered:**
- 保留 SQLite 仅供测试使用：测试基线仍会偏离生产语义，问题会继续积累
- 保留 SQLite 但在文档里标记“不推荐”：实现成本依旧存在，不符合“去掉所有 SQLite 内容”的目标

### 2. 统一 SQL 语义，删除仓储层和存储层的分支判断
所有仓储层、工作区存储层和数据库辅助方法都按 MySQL 占位符、异常和 DDL 语义实现，不再根据 `scheme` 做分支判断。

这样做的原因：
- 当前大量 `if scheme == "sqlite"` 语句会持续放大维护面
- MySQL-only 后可以统一 SQL 模板、异常处理和表存在性约束
- 有利于后续把数据库规范固化到代码审查与测试标准中

**Alternatives considered:**
- 保留通用接口但内部仍分支：表面上统一，实际仍是双实现
- 引入 ORM 屏蔽差异：会扩大改造面，不符合本次目标

### 3. MySQL DDL 成为唯一 schema 权威来源
运行时不再自动创建 SQLite schema；所有数据库结构以前置执行 `db/schema.mysql.ddl.sql` 和后续 MySQL migration 为准。

这样做的原因：
- 让 schema 管理回到显式 DDL，而不是散落在 Python 代码里
- 避免运行时建表逻辑与 MySQL DDL 演进不同步
- 符合项目规范化管理方式

**Alternatives considered:**
- 保留运行时自动建表：对 MySQL 生产环境不可控，也会弱化 DDL 规范
- 同时维护 Python schema 和 SQL schema：双份真相，长期必然漂移

### 4. 测试策略改为 MySQL-only，纯逻辑单测与数据库测试分层
涉及数据库持久化的测试统一基于 MySQL；不依赖数据库的逻辑测试继续保留，但不能再用 SQLite 作为数据库替身。数据库测试可以通过专用测试库、环境变量或统一测试夹具启动。

这样做的原因：
- SQLite 会掩盖 MySQL 方言、索引、约束、分页、窗口函数等差异
- 让测试结果更接近真实运行环境
- 形成可审查的项目规范：数据库相关结论必须来自 MySQL

**Alternatives considered:**
- 全量测试都直接连 MySQL：可行，但会把纯逻辑测试也拖慢；因此保留“无数据库逻辑单测”与“数据库集成测试”分层

## Risks / Trade-offs

- **[风险]** 本地开发和测试准备成本提高 → **缓解**：补充统一的 MySQL 启动、建库、DDL 和测试说明，必要时提供标准化测试库约定
- **[风险]** 删除 SQLite 分支会牵涉多处存储代码 → **缓解**：按数据库层、仓储层、脚本/配置、测试四个批次逐层清理，并以全量回归测试收口
- **[风险]** 历史脚本或个人环境仍依赖 SQLite URL → **缓解**：在配置文件、README 和启动错误信息中明确禁止，并给出 MySQL 替代写法
- **[权衡]** 失去“零依赖 SQLite 快速测试”便利 → **有意为之**：项目规范优先于局部便利，必须保证数据库语义与生产一致

## Migration Plan

1. 在 proposal/spec 中明确 MySQL-only 规范，锁定项目边界
2. 清理 `pm_agent/database.py` 中的 SQLite URL、连接、建表和占位符逻辑
3. 清理仓储层、工作区存储层和脚本中的 SQLite 分支
4. 更新配置文件、运行示例、README 和项目规范，只保留 MySQL 约定
5. 重写数据库相关测试，删除 SQLite 基线并以 MySQL 回归验证

回滚策略：
- 若必须回滚，只能回退代码版本恢复 SQLite 相关实现
- 本次变更不设计运行时开关，因为“项目只支持 MySQL”本身就是规范约束

## Open Questions

- 是否只保留 `mysql://` 和 `mysql+pymysql://`，还是继续允许其他 MySQL 驱动前缀
- 历史 `migrate_workspace_states.py` 应该完全删除，还是保留为仅支持 MySQL 的一次性运维脚本
- 是否需要补一个项目级“本地 MySQL 测试库初始化脚本”，降低团队切换成本
