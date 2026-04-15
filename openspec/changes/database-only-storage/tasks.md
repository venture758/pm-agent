## 1. 启动与数据库配置

- [x] 1.1 修改 `pm_agent/database.py` 与相关配置，移除默认本地 SQLite 回退逻辑；缺失数据库连接时显式报错
- [x] 1.2 清理 `DEFAULT_STATE_ROOT`、`DEFAULT_STATE_FILE` 等仅服务于本地状态目录的运行时依赖
- [x] 1.3 更新启动入口与 README，明确数据库连接为必填前置条件

## 2. 状态存储层去本地化

- [x] 2.1 重构 `pm_agent/storage.py`，移除 `state.json` 读取、写入与迁移逻辑，使 agent 状态仅来自数据库
- [x] 2.2 重构 `pm_agent/workspace_store.py`，移除 `workspaces/<id>/` 目录创建、`workspace.json` 迁移和本地路径依赖
- [x] 2.3 清理代码中对 `.pm_agent_store` 本地目录语义的残留假设，保证工作区和历史记录只从数据库读取

## 3. 上传与导入链路去落盘化

- [x] 3.1 调整模块知识、故事、任务导入函数签名，使其支持 `bytes` / 内存流输入，而不要求文件路径
- [x] 3.2 修改 `pm_agent/api_service.py` 上传链路，移除 `save_upload(...stored_path...)` 的本地落盘路径，改为内存解析
- [x] 3.3 保留上传历史所需的元数据写入数据库，并移除对本地 `uploads/` 目录的任何持久化依赖

## 4. 测试与清理

- [x] 4.1 更新单元测试与集成测试，覆盖“未配置数据库启动失败”“本地文件不会被读取”“上传不落本地文件”场景
- [x] 4.2 清理或替换依赖本地 `workspace.json` / `state.json` / `uploads` 目录的旧测试
- [x] 4.3 执行数据库相关回归测试，确认 agent 状态、工作区状态、确认历史、上传导入链路均仅使用数据库
