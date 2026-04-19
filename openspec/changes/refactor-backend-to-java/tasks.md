## 1. Java 工程与基础设施搭建

- [x] 1.1 创建 Java 21 + Maven + Spring Boot 项目骨架，按 `api/application/domain/infrastructure` 建立模块化单体目录
- [x] 1.2 引入 MyBatis、验证组件、统一异常处理、日志与配置管理依赖
- [x] 1.3 建立环境配置基线（dev/test/prod）与敏感配置读取规则（数据库、LLM key、超时重试）

## 2. `/api/v2` 契约与 Web 层落地

- [x] 2.1 按工作区能力定义 `/api/v2/workspaces/{workspaceId}/...` 路由分组并实现控制器骨架
- [x] 2.2 实现统一响应 envelope（`code/message/data`）与统一分页结构（`page/pageSize/total/items`）
- [x] 2.3 完成请求参数校验、错误码映射、全局异常处理与可观测日志字段标准化

## 3. 核心领域流程迁移（非 LLM）

- [x] 3.1 迁移成员与模块管理能力（增删改查、查询过滤、分页语义）
- [x] 3.2 迁移需求草稿、推荐生成、批量删除推荐、确认落地等核心流程
- [x] 3.3 迁移故事/任务导入与分页查询能力（包含过滤、空结果、边界页）
- [x] 3.4 迁移监控与洞察计算链路，确保结果可重复且来自持久化数据

## 4. LLM 与 Pipeline 能力迁移

- [x] 4.1 实现 LLM provider 抽象层（primary/fallback、超时、重试、失败降级）
- [x] 4.2 迁移 chat 会话与消息能力（会话创建、历史查询、删除、结构化需求持久化）
- [x] 4.3 迁移 pipeline 三类 API（start/state/confirm），并实现分步状态持久化和反馈重分析
- [x] 4.4 补齐 LLM 失败场景的受控错误响应与状态一致性保护

## 5. 数据库演进与全量迁移

- [x] 5.1 编写 schema 基线与增量 SQL 脚本，创建 Java 目标 schema 与必要索引
- [x] 5.2 实现全量迁移任务，覆盖 workspace、recommendation、confirmation、story/task、chat、pipeline 相关数据
- [x] 5.3 实现迁移校验脚本（行数对账、关键字段抽样、业务链路抽样）
- [x] 5.4 编写并固化回滚脚本（切流回退、快照恢复、日志记录）

## 6. 前后端联调与发布切换

- [x] 6.1 前端 API 客户端改造到 `/api/v2` 并完成页面请求模型适配
- [x] 6.2 建立契约测试与端到端冒烟清单，覆盖 intake、recommend、confirm、delivery、chat、pipeline、monitoring、insights
- [ ] 6.3 在预发执行至少一次全量迁移 + 切流演练，记录耗时与失败注入结果
- [ ] 6.4 维护窗执行生产切换并完成上线后观测、异常处置与 Python 写流量下线

## 7. 验收与文档收口

- [x] 7.1 输出发布 runbook（切换步骤、门禁条件、回滚触发条件）
- [x] 7.2 更新仓库运行文档与开发指南，声明 Java 后端为唯一生产实现
- [x] 7.3 形成迁移验收报告（契约通过率、数据一致性、关键链路稳定性）
