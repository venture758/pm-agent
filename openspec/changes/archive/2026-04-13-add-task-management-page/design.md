## Context

当前仅支持"故事+任务"双文件同步，且任务数据仅存在内存状态快照中。本次变更需要在已有架构（`frontend` + `pm_agent/api.py` + `pm_agent/api_service.py` + `WorkspaceStore`）上增加一条独立的任务导入链路，并确保数据库模型覆盖 Excel 模板字段。样例文件来自 `docs/导出列表_任务列表_0410191645.xlsx`（表头 27 列）。

相关角色：项目经理（上传与查看任务列表）、开发（维护字段映射与模型）、测试（验证字段映射、幂等、异常处理）。

## Goals / Non-Goals

**Goals:**
- 在交付页提供单独上传任务列表 Excel 的能力，不依赖故事文件。
- 新增数据库任务表，字段覆盖模板 Excel 表头（27 列），支持按任务编号幂等 upsert。
- 返回导入统计与错误明细，便于用户快速定位格式问题。
- 任务管理页展示入库任务列表，支持基础筛选（负责人、状态、所属项目）。
- 保持现有"故事+任务同步"能力可用，不引入行为回归。

**Non-Goals:**
- 不在本次实现任务字段的在线编辑回写数据库。
- 不引入"任意 Excel 动态建表"能力；仅支持约定模板字段。
- 不改造故事导入模型与故事管理流程。

## Decisions

### 1) 新增独立任务上传接口
- 决策：新增 `POST /api/workspaces/{workspace_id}/uploads/task-only`，仅接收 `task_file`。
- 理由：当前双文件接口有强耦合校验（必须同时存在 story_file/task_file），不适合单独任务上传。
- 备选方案：扩展原接口支持可选 task_file。
  - 未选原因：会让原语义变复杂，兼容分支多，影响已有调用和测试。

### 2) 使用"固定字段映射 + 显式列模型"
- 决策：根据模板表头建立固定数据库模型（27 列 + 元信息列），并在代码中维护 `EXCEL_HEADER -> db_column` 映射。
- 理由：SQL DDL、查询和索引都要求稳定列定义；动态建表/动态加列会显著提高迁移和运维复杂度。
- 备选方案：单 JSON 列存整行。
  - 未选原因：难以做字段级查询、筛选和约束。

### 3) 以"任务编号"作为业务主键做 upsert
- 决策：`workspace_id + task_code` 唯一约束，导入时执行"存在更新，不存在新增"。
- 理由：任务编号（TK-xxxxxx）是平台侧稳定键，适合作为幂等导入主键。

### 4) 表头严格校验，允许受控别名
- 决策：默认要求模板列完整匹配；对已知小差异（例如空格、全角/半角）做规范化匹配；缺失关键列直接失败。
- 理由：减少误导入风险，避免列错位导致数据污染。

### 5) 复用故事导入的表结构设计模式
- 决策：参照 `workspace_story_records` 的设计，新增 `workspace_task_records`（MySQL + SQLite），保留 `imported_at` 和 `updated_at` 元信息列。
- 理由：与现有故事表设计模式一致，降低维护成本。

## Excel 字段映射

模板表头（27 列）-> 内部字段名（snake_case）：

| 序号 | Excel 表头 | db_column | 类型 |
|------|-----------|-----------|------|
| 1 | 序号 | sequence_no | DECIMAL |
| 2 | 任务编号 | task_code | VARCHAR |
| 3 | 关联用户故事 | related_story | VARCHAR |
| 4 | 任务名称 | name | TEXT |
| 5 | 任务类型 | task_type | VARCHAR |
| 6 | 负责人 | owner | VARCHAR |
| 7 | 状态 | status | VARCHAR |
| 8 | 预计开始时间 | estimated_start | VARCHAR |
| 9 | 预计结束时间 | estimated_end | VARCHAR |
| 10 | 备注 | remark | TEXT |
| 11 | 完成时间 | completed_time | VARCHAR |
| 12 | 计划人天 | planned_person_days | DECIMAL |
| 13 | 实际人天 | actual_person_days | DECIMAL |
| 14 | 产品 | product | VARCHAR |
| 15 | 模块路径 | module_path | VARCHAR |
| 16 | 所属项目 | project_name | VARCHAR |
| 17 | 版本 | version | VARCHAR |
| 18 | 迭代阶段 | iteration_phase | VARCHAR |
| 19 | 项目组 | project_group | VARCHAR |
| 20 | 参与人 | participants | VARCHAR |
| 21 | 客户名称 | customer_name | VARCHAR |
| 22 | 缺陷总数 | defect_count | DECIMAL |
| 23 | 关联代码 | related_code | VARCHAR |
| 24 | 创建人 | created_by | VARCHAR |
| 25 | 创建时间 | created_time | VARCHAR |
| 26 | 修改人 | modified_by | VARCHAR |
| 27 | 修改时间 | modified_time | VARCHAR |

## Risks / Trade-offs

- [风险] 模板列名变更导致导入失败率上升
  → Mitigation: 维护列名别名表，导入响应给出"缺失列/未知列"详情。
- [风险] 27 列映射实现中出现字段错配
  → Mitigation: 增加字段映射单测（头部->列名、类型转换、空值处理）和端到端导入测试。
- [风险] 现有 `platform_sync.py` 中的 `import_task_records` 与新的解析器存在逻辑重叠
  → Mitigation: 新解析器仅用于独立上传，`platform_sync.py` 保留原行为用于双文件同步，两者互不干扰。
- [权衡] 固定模型提升可维护性，但对模板变更的弹性降低
  → Mitigation: 通过迁移脚本与版本化映射逐步演进字段。

## Migration Plan

1. 新增数据库表 `workspace_task_records` 的 DDL（MySQL）和 SQLite schema 创建语句。
2. 新增后端任务 Excel 解析器：读取任务 Excel，执行表头校验、类型转换与 upsert。
3. 新增独立上传 API 与 service 方法，返回导入摘要（总数/新增/更新/失败）。
4. 前端交付页新增"单独上传任务列表 Excel"交互与结果提示。
5. 任务管理页展示已入库任务列表，支持基础筛选。
6. 执行回归测试，确认故事导入/双文件同步流程无回归。

回滚策略：
- 接口层回滚到旧版本，不再暴露 task-only 上传入口。
- 保留新增表不删除（避免数据丢失）；读取路径回退到旧快照结构。

## Open Questions

- 任务管理页是否需要在首次访问时展示空状态引导用户上传？（建议：是）
- 是否需要对任务列表实现分页？（建议：初期不做，数据量可控后再加）
