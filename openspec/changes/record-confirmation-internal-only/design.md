## Context

目前 `confirm_assignments` 会在确认后调用 `generate_platform_handoff`，生成 stories/tasks 并进入平台同步预览链路。该行为适合“确认即准备同步”的场景，但对“仅内部确认备案”的场景是过度动作。用户当前诉求是确认后只保留内部记录，不再流转到平台同步模块。

系统现状：
- 确认结果当前主要保存在 `workspace.confirmed_assignments`（workspace payload）中。
- 持久化层已经有 MySQL DDL + migration + SQLite 自动建表机制。
- 前端交互依赖确认接口返回成功与消息，不强依赖 `handoff` 一定有数据。

## Goals / Non-Goals

**Goals:**
- 确认后不再生成平台同步预览数据（stories/tasks）。
- 新增独立确认记录表，持久化每次确认的记录快照，便于后续审计或统计。
- 保持确认 API 路由、请求结构和成功流程兼容。
- 提供明确消息提示“仅内部记录，不触发平台同步”。

**Non-Goals:**
- 不删除现有平台同步功能（上传 Excel 同步入口继续保留）。
- 不改造推荐生成、删除、批量删除链路。
- 不引入新的前端页面（仅保持现有页面可工作）。

## Decisions

### 1. 确认流程与平台同步解耦
- **Decision**: 在 `api_service.confirm_assignments` 中移除 `generate_platform_handoff` 调用，不再写入 `handoff_stories/handoff_tasks`。
- **Rationale**: 从流程源头阻断“确认即同步准备”的隐式耦合，符合“只记录”的目标。
- **Alternatives considered**:
  - 增加布尔开关控制是否生成 handoff：会增加接口复杂度和调用分支。
  - 前端隐藏 handoff：后端仍生成无效数据，治标不治本。

### 2. 新增确认记录表
- **Decision**: 新增 `workspace_confirmation_records`（主键 `BIGINT`），记录字段包含 `workspace_id`、`session_id`、`confirmed_count`、`payload_json`、`created_at`。
- **Rationale**: 将“确认行为日志”与 workspace 主表解耦，支持历史追溯和后续报表分析。
- **Alternatives considered**:
  - 仅写入 `workspace_states.payload`：查询历史成本高，难做增量分析。
  - 使用现有推荐表复用：语义不匹配。

### 3. store 层增加确认记录写入方法
- **Decision**: 在 `workspace_store.py` 增加 `append_confirmation_record(...)`，由 service 在确认成功后调用。
- **Rationale**: 复用现有 DB 抽象与异常处理路径，减少服务层 SQL 泄露。
- **Alternatives considered**:
  - 在 service 直接写 SQL：破坏分层，重复处理数据库方言差异。

### 4. 保持 API 兼容但弱化 handoff
- **Decision**: 保持返回结构中的 `handoff` 字段存在，但其数据为空列表；消息改为“已记录确认结果（未进入平台同步）”。
- **Rationale**: 避免前端因字段缺失报错，同时清晰传达行为变化。
- **Alternatives considered**:
  - 删除 `handoff` 字段：会产生明显兼容风险。

## Risks / Trade-offs

- [既有用户习惯“确认后看到平台预览”] → 通过明确文案提示行为变更，并在变更说明中标注 BREAKING。
- [新增记录表需要双库（MySQL/SQLite）同时维护] → 在 DDL、migration、sqlite schema 与单测中同步覆盖。
- [历史 `confirmed_assignments` 与记录表双写存在冗余] → 保留冗余以换取查询便利，后续可按需要收敛。

## Migration Plan

1. 新增确认记录表定义：
   - 更新 `db/schema.mysql.ddl.sql`
   - 更新 `db/migrate.mysql.*.sql`
   - 更新 SQLite `_ensure_sqlite_schema`
2. 在 `workspace_store.py` 增加插入确认记录方法。
3. 在 `confirm_assignments` 中改为：
   - 仅生成 confirmed assignments
   - 清空 recommendations
   - 清空 handoff 数据
   - 调用 store 追加确认记录
4. 更新消息文案与相关测试断言。
5. 运行后端/前端回归测试并验证确认接口响应。

## Open Questions

- 是否需要新增“确认记录查询 API”供前端直接浏览历史确认批次？
- 记录表的 `payload_json` 是否需要拆结构化字段（如负责人、模块）用于后续统计加速？
