## Why

当前后端基于 Python，已承载工作区、推荐确认、导入同步、聊天解析和 pipeline 多步骤分析等核心能力。随着能力持续扩展，跨模块维护成本和演进一致性压力明显增大，需要统一到 Java 技术栈并完成一次性替换，以支撑后续长期迭代。

## What Changes

- 新建 Java 后端（`Java 21 + Spring Boot + MyBatis`）并按模块化单体落地工作区全量能力。
- **BREAKING**：后端 API 重设计为 `/api/v2/workspaces/{workspaceId}/...`，前端同批次改造，不保留旧 API 兼容层。
- 实现与现有业务等价的核心流程：需求录入、推荐生成、确认落地、故事/任务查询、上传导入、监控与洞察。
- 保留并迁移 LLM 能力（chat 解析、会话、pipeline 分步确认、降级与重试）。
- 使用版本化 SQL 脚本管理数据库变更并执行历史数据全量迁移，采用维护窗一次性切换到 Java 后端。

## Capabilities

### New Capabilities
- `java-backend-api-v2`: 版本化 API 与统一响应契约，支撑前后端同步改造后的全部工作台调用。
- `java-backend-domain-workflows`: Java 实现工作区核心业务流程（成员/模块/推荐/确认/导入/查询/监控洞察）。
- `java-backend-llm-integration`: Java 实现 chat 与 pipeline 的 LLM 调用、状态推进和降级策略。
- `java-backend-data-migration-cutover`: 全量数据迁移、维护窗切换、回滚与校验机制。

### Modified Capabilities
- 无。现有领域规格作为业务目标被 Java 后端继承，本次新增平台级能力规格来定义迁移与新 API 契约。

## Impact

- 新增 Java 工程（Maven）及分层模块：`api/application/domain/infrastructure`。
- 新增数据库迁移与版本管理：版本化 SQL 迁移脚本、迁移执行器、切换与回滚 runbook。
- 前端 API 调用层与页面数据模型需同步切换到 `/api/v2` 契约。
- 运维与发布流程调整为维护窗直切，要求发布前完成全量迁移演练与冒烟基线。
