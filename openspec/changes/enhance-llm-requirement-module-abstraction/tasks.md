## 1. 解析上下文构建

- [x] 1.1 在 Java 需求解析服务中新增模块上下文构建器，输出去重后的 `big_module/function_module` 候选集合与关键词摘要
- [x] 1.2 新增历史任务名称样本提取逻辑（去噪、去重、条数上限），并接入解析 prompt 上下文
- [x] 1.3 在上下文构建中显式排除历史 `module_path` 字段，避免其参与模块匹配
- [x] 1.4 增加上下文截断与排序策略，保证模块与任务样本在 token 限额内可控

## 2. LLM 输出与后端契约扩展

- [x] 2.1 扩展需求解析 prompt 与输出 schema，要求返回 `big_module`、`function_module`、`abstract_summary`、`match_evidence`、`match_status`
- [x] 2.2 实现解析结果校验与默认值回填，低置信场景统一返回 `needs_confirmation`
- [x] 2.3 更新解析响应 DTO/映射层，确保 `/api/v2/workspaces/{workspaceId}/chat` 返回新字段且保持向后兼容
- [x] 2.4 如需持久化新字段，补齐实体、Mapper、SQL 与迁移脚本，并保证旧数据读取兼容

## 3. 前端展示与交互

- [x] 3.1 在需求录入/确认相关视图展示 `big_module`、`function_module` 与 `abstract_summary`
- [x] 3.2 为 `needs_confirmation` 场景增加显式提示，展示候选模块或匹配理由
- [x] 3.3 保持旧字段渲染逻辑兼容，避免新字段缺失导致页面异常

## 4. 测试与验收

- [x] 4.1 增加后端单测：覆盖高置信匹配、无历史任务、低置信降级三类解析结果
- [x] 4.2 增加后端单测：当历史 `module_path` 错误时，验证解析上下文不注入该字段且模块归属不受其干扰
- [x] 4.3 增加 API 契约测试：校验新字段输出结构与向后兼容行为
- [x] 4.4 增加前端联调用例：校验新字段展示与 `needs_confirmation` 提示流程
- [x] 4.5 执行端到端冒烟：从需求输入到推荐确认，验证模块归属与抽象提炼可被后续流程消费
