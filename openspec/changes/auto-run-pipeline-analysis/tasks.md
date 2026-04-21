## 1. Backend Auto Execution

- [x] 1.1 扩展 Pipeline 状态模型，增加 `execution_mode`、`run_status`、`awaiting_confirmation`、`blocking_reason`、`run_id`、`last_heartbeat_at`
- [x] 1.2 在 `PipelineService` 中实现自动模式后台 runner、workspace 级并发保护和心跳超时失败
- [x] 1.3 调整 `start/state/confirm` 接口行为，支持自动模式暂停、恢复续跑和手动模式兼容

## 2. Frontend Intake Experience

- [x] 2.1 在聊天消息入口提供“自动分析”和“逐步确认”两个启动动作
- [x] 2.2 在 workspace store 中实现自动模式状态归一化与轮询控制
- [x] 2.3 在 Pipeline 面板中展示运行状态、阻塞原因、自动暂停后的人工处理按钮和完成态摘要

## 3. Verification

- [x] 3.1 补充后端 Pipeline 状态机测试，覆盖自动暂停、续跑完成、手动模式和心跳超时
- [x] 3.2 补充前端 store/panel 测试，覆盖自动轮询、暂停展示和恢复动作
- [x] 3.3 执行前端 build 与定向测试，确认契约和模板改动可通过构建
