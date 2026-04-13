## 1. 字段基线与数据模型

- [x] 1.1 从 `docs/导出列表_任务列表_0410191645.xlsx` 提取并固化任务模板表头清单（27 列）
- [x] 1.2 设计并实现 `EXCEL_HEADER -> db_column` 映射（包含必要别名与规范化规则）
- [x] 1.3 新增 `workspace_task_records` 的 MySQL DDL（字段列 + 唯一键 `workspace_id,task_code`）
- [x] 1.4 在 SQLite schema 初始化中新增 `workspace_task_records` 表定义

## 2. 后端导入能力

- [x] 2.1 新增 `pm_agent/task_excel_import.py`：任务 Excel 解析器，支持表头校验、空行过滤与类型转换
- [x] 2.2 在 `WorkspaceStore` 中实现任务记录 upsert（按 `workspace_id + task_code` 幂等）
- [x] 2.3 在 `WorkspaceStore` 中实现任务记录 load 方法（按 workspace_id 查询，支持按负责人/状态/项目筛选）
- [x] 2.4 新增 task-only 上传服务方法 `upload_task_file`，返回 `total/created/updated/failed` 与错误明细
- [x] 2.5 新增 API 路由 `POST /api/workspaces/{workspace_id}/uploads/task-only`（仅接收 `task_file`）并接入统一错误处理
- [x] 2.6 新增 API 路由 `GET /api/workspaces/{workspace_id}/tasks`（查询任务列表，支持 query 参数筛选）

## 3. 前端任务管理页

- [x] 3.1 新增任务管理页面 `TaskManagementView.vue`，包含上传入口与任务列表展示（集成到 DeliveryView 任务管理 tab）
- [x] 3.2 新增前端 API client 方法：`uploadTask`、`getTasks`
- [x] 3.3 新增前端 store 方法：`uploadTaskOnly`、`loadTasks`
- [x] 3.4 实现任务列表表格展示（27 列全覆盖，支持排序）
- [x] 3.5 实现任务列表筛选（负责人、状态、所属项目）
- [x] 3.6 展示导入结果摘要与失败明细（包括缺失列、行级错误）
- [x] 3.7 在路由中添加任务管理页入口（已有 DeliveryView 任务管理 tab 作为入口）

## 4. 兼容与数据迁移

- [x] 4.1 保持现有"故事+任务双文件同步"接口行为不变
- [x] 4.2 在 workspace payload 中新增 `latest_task_import` 字段，参照 `latest_story_import` 模式
- [x] 4.3 定义新旧任务数据读取优先级（新表优先，旧快照兜底）

## 5. 测试与验收

- [x] 5.1 增加任务表头校验与字段映射单元测试（含关键列缺失场景）
- [x] 5.2 增加 task-only 上传 API 集成测试（成功、部分失败、全失败）
- [x] 5.3 增加任务 upsert 幂等测试（首次导入=全部新增，二次导入=全部更新）
- [x] 5.4 增加前端任务管理页流程测试（上传状态、结果展示、错误提示、列表筛选）
- [x] 5.5 执行回归测试，确认故事导入/双文件同步/人员管理流程无回归
