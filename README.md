# 项目经理 Agent

这是一个面向软件研发团队的离线项目经理 Agent 最小实现，覆盖以下能力：

- 群评审需求列表解析
- 业务模块知识库导入与维护
- 基于模块负责人、B角、成员熟悉度和负载的分配推荐
- 项目经理确认后的故事/任务落地数据生成
- 每日 9 点故事/任务 Excel 导入同步
- 执行预警、团队负载热力图、单点依赖和成长建议

当前仓库还包含一个前后端分离的 Web 工作台：

- 后端：Python API，复用 `pm_agent` 领域逻辑
- 前端：Vue 单页应用，提供需求录入、业务模块维护、人员管理、推荐确认、交付管理（故事/任务）、监控和洞察页面

## 目录结构

- `pm_agent/workflows.py`
  提供 `ProjectManagerAgent` 统一工作流入口
- `pm_agent/api.py`
  提供 Web API 入口和 REST 路由
- `pm_agent/api_service.py`
  提供工作区应用服务，封装业务模块维护、人员管理、推荐、确认、上传和查询动作
- `pm_agent/workspace_store.py`
  提供工作区状态持久化，工作区状态和上传元数据仅保存在数据库
- `pm_agent/database.py`
  提供统一数据库存储（MySQL + SQLite）
- `db/schema.mysql.ddl.sql`
  MySQL 初始化和维护脚本使用的唯一 DDL 文件
  其中 `workspace_module_entries` 为业务模块明细表（大模块/功能模块/主负责人/B角多人/成员熟悉度三分类）
- `db/migrate.mysql.module-entries.sql`
  旧库迁移脚本（补齐 `BIGINT id` 主键、业务模块明细表、表注释和字段注释）
- `pm_agent/intake.py`
  负责群消息和导入需求解析
- `pm_agent/knowledge_base.py`
  负责模块知识库导入、匹配和自动更新
- `pm_agent/assignment.py`
  负责分配推荐、确认和故事/任务落地
- `pm_agent/platform_sync.py`
  负责故事/任务 Excel 离线 upsert
- `pm_agent/monitoring.py`
  负责执行预警
- `pm_agent/insights.py`
  负责负载、单点依赖和成长建议
- `frontend/`
  Vue 前端工程，包含工作台路由、状态管理和页面实现

## 典型用法

```python
from pm_agent import ProjectManagerAgent

agent = ProjectManagerAgent(database_url="mysql://user:pass@127.0.0.1:3306/pm_agent?charset=utf8mb4")
agent.sync_module_knowledge_base("docs/泾渭云后端业务模块划分、模块负责人、熟练度.xlsx")

message = """
1. 发票查验接口替换为长软新数据源需求 https://example.com/page1 优先级高
2. 安徽银税互动授权记录采集新入口 https://example.com/page2 优先级高
"""

requirements, members = agent.intake_requirements_from_chat(message)
recommendations = agent.recommend(requirements, members)
print(agent.render_group_reply(recommendations))

confirmed = agent.confirm(recommendations)
stories, tasks = agent.generate_platform_handoff(confirmed)
batch = agent.sync_daily_exports(
    "docs/导出列表_用户故事列表_0410191819.xlsx",
    "docs/导出列表_任务列表_0410191645.xlsx",
)
alerts = agent.monitor_execution()
insights = agent.generate_team_insights()
```

## 模块知识库维护规则

- 默认优先读取最新年度的“后端技术角度的业务模块”sheet
- 模块知识库记录：
  `大模块`、`功能模块`、`主要负责人`、`B角`、`成员熟悉程度`、来源 sheet、导入时间
- 每次确认分配后自动更新：
  分配历史、最近负责人痕迹、熟悉度建议值
- 主负责人和 B 角不自动覆盖，只生成建议值

## 每日 9 点导入流程

1. 从项目管理平台导出故事 Excel 和任务 Excel
2. 使用 `agent.sync_daily_exports()` 导入文件
3. 系统按 `用户故事编码` 和 `任务编号` 做新增或更新
4. 使用 `agent.monitor_execution()` 查看延期、阻塞、质量风险
5. 使用 `agent.generate_team_insights()` 查看负载、单点依赖和成长建议

## 测试

```bash
python3 -m unittest discover -s tests
```

## Web 工作台启动

默认配置文件：

```toml
config/pm_agent.toml
```

按环境加载逻辑：
- 默认环境：`dev`
- 可通过 `PM_AGENT_ENV` 或 `--env` 切换到 `test` / `prod`
- 可通过 `PM_AGENT_CONFIG` 或 `--config` 指向其他配置文件
- 覆盖优先级：`CLI 参数 > 环境变量 > 配置文件`

后端 API：

```bash
python3 -m pm_agent_web
```

初始化 MySQL（先建库，再执行 DDL）：

```bash
mysql -h127.0.0.1 -u<user> -p pm_agent < db/schema.mysql.ddl.sql
```

已有历史库升级：

```bash
mysql -h127.0.0.1 -u<user> -p pm_agent < db/migrate.mysql.module-entries.sql
```

故事管理页单独上传 Excel（`/uploads/story-only`）依赖 `workspace_story_records` 表。  
如果线上库未升级，可单独执行以下脚本完成迁移：

```bash
mysql -h127.0.0.1 -u<user> -p pm_agent < db/migrate.mysql.module-entries.sql
```

回滚策略：
- 回滚应用版本后可不删除 `workspace_story_records`（保留数据，接口不再读取即可）。
- 如需临时禁用功能，可前端隐藏“单独上传故事 Excel”入口，后端不调用 story-only 路由。

数据库连接是必填前置条件。现在默认从 `config/pm_agent.toml` 读取。

示例：

```bash
PM_AGENT_ENV=prod python3 -m pm_agent_web
```

如果要临时覆盖数据库地址，仍然可以：

```bash
python3 -m pm_agent_web --host 127.0.0.1 --port 8000 --database-url "sqlite:////absolute/path/to/pm_agent.db"
```

前端：

```bash
cd frontend
npm install
npm run dev
```

访问地址：

- 前端开发环境：`http://127.0.0.1:5173`
- 后端 API：`http://127.0.0.1:8000/api/health`

## 联调流程

1. 在 `人员管理` 页面维护团队成员画像，这是推荐和洞察的唯一成员入口
2. 在 `业务模块` 页面手工维护模块知识，或在 `需求输入` 页面上传模块知识库 Excel 做批量导入
3. 在 `需求输入` 页面粘贴群评审消息或录入结构化需求
4. 生成推荐并在 `推荐确认` 页面做人工调整
5. 在 `交付管理` 页面进行故事导入与故事/任务数据查看
6. 在 `执行监控` 和 `团队洞察` 页面查看风险和负载结果

## 变更记录

- 2026-04-13：交付页移除“上传与同步”模块，仅保留“故事管理/任务管理”两个 Tab；后端同步 API（如 `/uploads/platform-sync`）为兼容性仍保留。

## 人员与模块维护规则

- `人员管理` 页面维护的数据是推荐、监控和团队洞察的唯一成员来源，不再支持 intake 页面临时录入成员。
- `业务模块` 页面支持手工维护：
  `大模块`、`功能模块`、`主要负责人`、`B角`、`成员熟悉度`
- 模块知识库 Excel 导入仍保留，用于批量更新已有模块条目。
- 手工维护和 Excel 导入共用同一套模块知识条目，后续推荐会直接复用更新后的数据。
- 运行时不再读取 `.pm_agent_store/state.json`、`workspaces/*/workspace.json` 或任何本地上传目录。
- MySQL 环境建议统一通过 `db/schema.mysql.ddl.sql` 执行初始化和后续维护脚本。

## 前端测试

```bash
cd frontend
npm install
npm run test
npm run test:e2e
```
