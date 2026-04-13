## Why

当前故事管理页面缺少“用户故事 Excel 独立上传”能力，用户只能依赖其他流程间接同步，导致故事数据更新慢且易遗漏。为了让项目经理可以直接以平台导出为准进行维护，需要新增按 Excel 字段落库的导入链路，并确保导入结构与源表保持一致。

## What Changes

- 在故事管理页面新增“单独上传用户故事 Excel”入口，支持文件校验、上传、解析和结果反馈。
- 新增用户故事导入后端接口，按 Excel 表头字段进行映射、清洗和落库。
- 新增用户故事数据库模型（及迁移脚本），字段来源于用户提供的 Excel 模板列。
- 定义导入幂等策略（以用户故事编码为主键约束）与更新策略（存在则更新，不存在则新增）。
- 为导入链路补充失败明细与统计信息，便于排查字段格式问题。

## Capabilities

### New Capabilities
- `story-excel-upload-and-schema`: 故事管理页面支持独立上传用户故事 Excel，并基于 Excel 字段驱动数据库建模与入库。

### Modified Capabilities
- None.

## Impact

- Affected code:
  - `frontend/src/views`（故事管理页面上传入口与结果展示）
  - `frontend/src/api`（新增故事上传接口调用）
  - `pm_agent/api.py`、`pm_agent/api_service.py`（新增上传路由与服务编排）
  - `pm_agent/models.py`、`pm_agent/storage.py` 或 `pm_agent/database.py`（新增/扩展故事实体与持久化）
  - `db/`（新增或更新 MySQL DDL/迁移脚本）
- Data model: 新增用户故事字段集，字段与 Excel 表头保持一一对应（含中文标题到内部字段名映射）。
- APIs: 新增故事 Excel 上传接口及导入结果返回结构。
- Dependencies: 复用现有 Excel 解析能力（openpyxl/pandas）与当前数据库访问层。
