## Why

当前平台导出任务列表后，缺少独立上传任务 Excel 的能力。现有平台同步仅支持"故事+任务"双文件同步，且任务数据仅存储在内存状态快照中，未持久化到数据库。项目经理需要直接上传任务 Excel 进行维护，并基于任务字段做查询、筛选和导入记录管理。

## What Changes

- 在交付页新增"单独上传任务列表 Excel"入口，支持文件校验、上传、解析和结果反馈。
- 新增任务导入后端接口，按 Excel 表头字段（27 列）进行映射、清洗和落库。
- 新增任务数据库模型 `workspace_task_records`，字段来源于用户提供的 Excel 模板列。
- 定义导入幂等策略（以任务编号为主键约束）与更新策略（存在则更新，不存在则新增）。
- 为导入链路补充失败明细与统计信息，便于排查字段格式问题。
- 任务管理页展示已入库任务列表，支持按负责人、状态、所属项目等筛选。

## Capabilities

### New Capabilities
- `task-management`: 任务管理页面支持独立上传任务列表 Excel，并基于 Excel 字段驱动数据库建模与入库。

### Modified Capabilities
- None.

## Impact

- Affected code:
  - `frontend/src/views`（任务管理页上传入口、列表展示与结果反馈）
  - `frontend/src/api/client.js`（新增任务上传、列表查询接口调用）
  - `pm_agent/api.py`、`pm_agent/api_service.py`（新增上传路由与服务编排）
  - `pm_agent/task_excel_import.py`（新增）任务 Excel 解析器
  - `pm_agent/workspace_store.py`（新增任务表 upsert / load 方法）
  - `db/schema.mysql.ddl.sql`（新增 `workspace_task_records` 表 DDL）
- Data model: 新增 `TaskRecord` 字段集，覆盖 Excel 模板 27 列（含中文标题到内部字段名映射）。
- APIs: 新增任务 Excel 上传接口 `POST /api/workspaces/{workspace_id}/uploads/task-only` 及任务列表查询接口。
- Dependencies: 复用现有 Excel 解析能力（openpyxl）、数据库访问层和导入模式。
