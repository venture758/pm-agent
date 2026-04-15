## 1. 数据模型与持久化

- [x] 1.1 在 `pm_agent/models.py` 与 `pm_agent/workspace_models.py` 中新增知识更新记录模型，并为 `WorkspaceState` 增加 `latest_knowledge_update` 字段
- [x] 1.2 在 `pm_agent/workspace_store.py` / 数据库层新增知识更新记录的 append-only 存储与按 `workspace_id + session_id` 查询能力
- [x] 1.3 更新工作区加载与保存逻辑，兼容无知识更新记录的旧 workspace

## 2. 知识更新 Agent 接线

- [x] 2.1 重构 `pm_agent/workflows.py` 中的知识更新方法，使其返回统一的运行结果结构（`status`、`reply`、`knowledge_updates`、`optimization_suggestions`、`error_message`）
- [x] 2.2 修改 `pm_agent/api_service.py` 的 `confirm_assignments()`，在确认成功和确定性知识更新完成后触发知识更新 Agent
- [x] 2.3 为 `LLM 未配置`、`调用失败`、`JSON 解析失败` 三类场景写入 `skipped/failed` 状态，且不影响确认接口成功返回

## 3. API 与返回载荷

- [x] 3.1 扩展工作区 payload，返回 `latest_knowledge_update`
- [x] 3.2 扩展确认历史查询结果，按 `session_id` 返回对应知识更新状态、摘要和失败原因
- [x] 3.3 保持现有确认记录接口兼容，未命中知识更新记录时返回空值而非报错

## 4. 确认中心展示

- [x] 4.1 更新 `frontend/src/stores/workspace.js`，接收并缓存最近一次知识更新摘要及确认历史中的知识更新字段
- [x] 4.2 更新 `frontend/src/views/RecommendationsView.vue`，在确认中心展示最近一次知识更新状态、摘要和建议数量
- [x] 4.3 在确认历史子页签中展示每个 session 的知识更新状态，并在展开态显示摘要或失败原因

## 5. 测试与验收

- [x] 5.1 为后端新增单元测试，覆盖知识更新成功、跳过、失败时的数据落库与确认主流程不回滚
- [x] 5.2 为 Web/API 层新增集成测试，覆盖工作区 payload 和确认历史返回知识更新字段
- [x] 5.3 为前端确认中心新增测试，覆盖最近一次知识更新展示和历史 session 状态展示
- [x] 5.4 执行回归测试，确认现有“提交确认”与模块知识规则更新行为保持兼容
