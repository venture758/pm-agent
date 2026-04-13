## 1. 数据模型与存储扩展

- [x] 1.1 新增确认记录表结构（MySQL DDL、MySQL migration、SQLite schema）并补充表名与字段注释
- [x] 1.2 在 `workspace_store.py` 增加确认记录写入方法（按批次落一条记录）
- [x] 1.3 确认记录写入使用统一序列化结构（workspace_id、session_id、confirmed_count、payload_json、created_at）

## 2. 确认流程重构（去平台同步）

- [x] 2.1 修改 `api_service.confirm_assignments`：移除 `generate_platform_handoff` 调用
- [x] 2.2 确认成功后仅保留 confirmed_assignments 与消息，不再新增 handoff stories/tasks
- [x] 2.3 调用 store 写入确认记录，并将返回文案改为“已记录确认结果（未进入平台同步）”

## 3. 接口兼容与返回结构

- [x] 3.1 保持确认接口路由与请求参数不变（兼容现有前端）
- [x] 3.2 保持响应中 `handoff` 结构字段存在，但 `stories/tasks` 为空数组
- [x] 3.3 检查前端相关页面在无 handoff 预览数据时不报错

## 4. 测试与回归

- [x] 4.1 新增后端测试：确认后不生成 stories/tasks
- [x] 4.2 新增后端测试：确认后确认记录表新增一条记录且字段正确
- [x] 4.3 更新现有测试断言以适配“仅内部记录”新行为
- [x] 4.4 运行 `python3 -m unittest discover -s tests` 和前端关键测试并修复回归
