---
date: 2026-04-17
status: draft
author: claude-code
---

# Team Leader Agent — 多 Agent 协作架构设计

## 1. 背景与目标

当前的 `ProjectManagerAgent` 是一个单一 Agent，通过一个巨型 prompt 承担需求解析、人员匹配、模块匹配、知识更新等多个职责。随着能力扩展（模块提炼、梯队分析），prompt 将变得不可维护。

**目标**：将研发经理 Agent 拆分为 5 个子 Agent，由 Orchestrator 串行调度，每步输出建议后暂停等待用户确认，实现辅助决策模式。

**一句话总结**：将研发经理脑壳里面的东西以及要做的事情全面让这个 agent 接管。

## 2. 核心设计决策

| 决策 | 选择 |
|------|------|
| 自主性 | 辅助决策 — 所有建议需人审核确认 |
| 知识自治 | 主动采集 — 从需求中提炼新模块、从外部数据源构建知识 |
| 梯队建设 | 以业务模块为核心的人员熟悉度体系 |
| 模块新增 | 需求解析时触发，自动提炼为新模块（待确认） |
| LLM 使用 | 全部子 Agent 使用 LLM |
| 协作模式 | 串行 — 每步确认后才进入下一步 |
| 跳步 | 允许 — 每步可跳过，直接进入下一步 |
| 数据层 | MySQL only |
| LLM 容灾 | 多模型自动降级 — 主模型失败自动切换到备用模型 |

## 3. LLM 多模型策略

### 3.1 模型分级

```
Tier-1 (主模型):  Qwen-Max / Qwen-Plus  (强推理，用于需求解析、人员匹配、模块提炼)
Tier-2 (备用):    GPT-4o / DeepSeek-V3   (中等，用于梯队分析、知识更新)
Tier-3 (兜底):    Qwen-Turbo / GPT-4o-mini (快速便宜，用于重试降级)
```

### 3.2 自动切换规则

```
请求发出 ──▶ 主模型(Tier-1)
              │
              ├── 成功 ──▶ 返回结果
              │
              ├── 超时/HTTP错误 (连续 2 次) ──▶ 自动降级到 Tier-2
              │
              ├── JSON解析失败 ──▶ 重试一次(Tier-1) ──▶ 仍失败 ──▶ 降级到 Tier-2
              │
              └── 内容质量差 (空数组/字段缺失) ──▶ 降级到 Tier-2
              │
              ▼
            Tier-2 重试 ──▶ 成功/失败 ──▶ 仍失败 ──▶ 降级到 Tier-3
              │
              ▼
            Tier-3 兜底 ──▶ 无论成功失败都返回，标记 warning
```

### 3.3 配置

在 `config.py` 中新增模型配置：

```python
MODEL_CONFIG = {
    "primary": {
        "base_url": "...",
        "api_key_env": "NVIDIA_NIM_API_KEY",
        "model": "qwen-max",
        "temperature": 0.3,
        "max_tokens": 4096,
        "timeout": 60,
    },
    "fallback": {
        "base_url": "...",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4o",
        "temperature": 0.3,
        "max_tokens": 4096,
        "timeout": 30,
    },
    "last_resort": {
        "base_url": "...",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 2048,
        "timeout": 15,
    },
}
```

### 3.4 响应质量校验

新增 `validate_llm_output()` 函数，检查：
- JSON 是否合法
- 必填字段是否存在
- 枚举值是否在允许范围内（如 priority 必须是 高/中/低）
- 列表字段是否为空（如 requirements 不能为空数组）

校验失败触发降级。

## 4. 整体架构

```
┌─────────────────────────────────────────────┐
│               前端（Web UI）                   │
│  需求输入 → 查看建议 → 确认/修改/重新分析/跳过  │
└────────────────┬────────────────────────────┘
                 │ HTTP/JSON
                 ▼
┌─────────────────────────────────────────────┐
│            WorkspaceService                   │
│         (API 层 + 状态管理)                    │
│                                               │
│  ┌─────────────────────────────────────────┐ │
│  │           Orchestrator Agent             │ │
│  │   接收需求 → 串行分发 → 汇总 → 建议       │ │
│  └──┬───────────────────────────────────┬──┘ │
│     │                                   │     │
│  ┌──▼──┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──▼──┐ │
│  │需求  │ │人员  │ │模块  │ │梯队  │ │知识  │ │
│  │解析  │ │匹配  │ │提炼  │ │分析  │ │更新  │ │
│  │Agent │ │Agent │ │Agent │ │Agent │ │Agent │ │
│  │ LLM  │ │ LLM  │ │ LLM  │ │ LLM  │ │ LLM  │ │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────┐
│              MySQL Database                  │
│  requirements / module_entries / members     │
│  sessions / assignments / chat_messages      │
└─────────────────────────────────────────────┘
```

## 4. 流程

```
步骤1          步骤2          步骤3          步骤4          步骤5
需求解析  ──▶  人员匹配  ──▶  模块提炼  ──▶  梯队分析  ──▶  知识更新
  LLM          LLM          LLM          LLM          LLM(汇总)
  │             │             │             │             │
确认?         确认?         确认?         确认?         写入?
  │             │             │             │             │
  ▼             ▼             ▼             ▼             ▼
Requirement   Assignment   Module       Team         Pending
Items         Suggestions  Changes      Analysis     Changes
                                                      │
                                              ┌───────┘
                                              │ 确认后写入 MySQL
                                              ▼
                                           完成
```

每步用户可操作：
- **确认** → 进入下一步
- **手动修改** → 用户直接编辑建议结果，修改后进入下一步
- **重新分析** → 用户输入反馈（如"李祥这周不在"），LLM 带新约束重新执行
- **跳过** → 直接进入下一步（第5步的跳过即"直接写入"）

## 5. 共享上下文

```python
@dataclass
class PipelineContext:
    workspace_id: str
    session_id: str
    user_message: str
    
    # 已有数据
    profiles: list[MemberProfile]
    module_entries: list[ModuleKnowledgeEntry]
    task_records: list[TaskRecord]
    
    # 逐步产出
    requirements: list[RequirementItem]       # 步骤1产出
    assignment_suggestions: list[dict]        # 步骤2产出
    module_changes: list[dict]                # 步骤3产出
    team_analysis: dict                       # 步骤4产出
    pending_changes: list[dict]               # 步骤5产出
    
    # 约束反馈（用户重新分析时注入）
    step_constraints: dict[str, str]          # {step_name: constraint_text}
```

## 6. 子 Agent 接口

### 6.1 需求解析 Agent

**职责**：将自然语言需求解析为结构化条目

**输入**：`user_message` + `profiles` + `module_entries` + `task_records`
**输出**：

```json
{
  "mode": "requirement_analysis",
  "requirements": [
    {
      "title": "...",
      "priority": "高|中|低",
      "requirement_type": "接口改造|新功能|Bug修复|技术优化|数据迁移|环境配置|其他",
      "complexity": "低|中|高",
      "risk": "低|中|高",
      "skills": ["..."],
      "matched_modules": [{"key": "big::func", "confidence": 0.9}],
      "dependency_hints": ["..."],
      "blockers": ["..."],
      "split_suggestion": "...",
      "analysis_factors": ["..."]
    }
  ],
  "reply": "已解析 N 条需求..."
}
```

**Prompt 来源**：当前 `SYSTEM_PROMPT`（基本不需要改）

---

### 6.2 人员匹配 Agent

**职责**：为每条需求推荐开发、测试、B 角、协作人

**输入**：`requirements` + `profiles` + `task_records` + `step_constraints["personnel_matching"]`
**输出**：

```json
{
  "mode": "personnel_matching",
  "assignments": [
    {
      "requirement_id": "REQ-001",
      "requirement_title": "...",
      "development_owner": "李祥",
      "testing_owner": "张三",
      "backup_owner": "王海林",
      "collaborators": ["余萍"],
      "reasons": ["熟悉税务模块", "当前负载低"],
      "workload_snapshot": {"李祥": 0.3, "张三": 0.1},
      "confidence": 0.85
    }
  ],
  "reply": "推荐分配：REQ-001 分配给李祥..."
}
```

**关键规则（注入到 prompt）**：
- 综合技能匹配度、模块熟悉度、当前负载、历史任务表现
- 避免给同一人分配过多高优先级需求
- 每个需求至少有一主一备
- 尊重 `step_constraints` 中的用户约束（如"李祥这周不在"）

---

### 6.3 模块提炼 Agent

**职责**：从需求中识别新模块/子模块，更新模块归属关系

**输入**：`requirements` + `module_entries` + `assignment_suggestions` + `step_constraints["module_extraction"]`
**输出**：

```json
{
  "mode": "module_extraction",
  "module_changes": [
    {
      "action": "create_big_module",
      "big_module": "风控",
      "function_modules": [{"function_module": "黑名单校验"}],
      "rationale": "从需求 REQ-003 中提炼出新的业务领域"
    },
    {
      "action": "create_function_module",
      "big_module": "税务",
      "function_module": "汇算清缴",
      "rationale": "需求 REQ-005 涉及税务新场景"
    },
    {
      "action": "update_primary_owner",
      "module_key": "税务::发票接口",
      "primary_owner": "李祥",
      "rationale": "李祥为熟悉该模块的唯一人员"
    }
  ],
  "reply": "从需求中提炼出 1 个大模块、1 个子模块"
}
```

**变更类型**：
- `create_big_module` — 新建大模块及子模块
- `create_function_module` — 在现有大模块下新建子模块
- `update_primary_owner` — 更新主负责人
- `update_backup_owners` — 更新 B 角

所有变更标记为 pending，确认后写入。

---

### 6.4 梯队分析 Agent

**职责**：分析团队对各模块的熟悉度分布，发现单点风险，建议成长路径

**输入**：`profiles` + `module_entries` + `assignment_suggestions` + `task_records` + `step_constraints["team_analysis"]`
**输出**：

```json
{
  "mode": "team_analysis",
  "module_familiarity_matrix": {
    "税务::发票接口": {
      "familiar": ["李祥"],
      "aware": ["张三"],
      "unfamiliar": ["王五"]
    }
  },
  "single_point_risks": [
    {
      "module_key": "税务::发票接口",
      "risk_member": "李祥",
      "severity": "high",
      "suggestion": "建议培养 B 角，张三已了解，可安排跟练"
    }
  ],
  "growth_paths": [
    {
      "member": "王五",
      "target_module": "税务::发票接口",
      "current_level": "不了解",
      "target_level": "了解",
      "path": "先参与发票接口相关小需求，由李祥带练"
    }
  ],
  "reply": "发现 1 个单点风险，建议 1 条成长路径"
}
```

---

### 6.5 知识更新 Agent（汇总）

**职责**：汇总前 4 步的所有变更建议，生成待执行操作列表

**输入**：全部前 4 步的产出 + `step_constraints["knowledge_update"]`
**输出**：

```json
{
  "mode": "knowledge_update",
  "summary": {
    "requirements_parsed": 3,
    "personnel_assigned": 3,
    "modules_created": 1,
    "familiarity_updates": 2,
    "risks_identified": 1
  },
  "pending_changes": [
    {
      "type": "create_module",
      "data": {"big_module": "风控", ...}
    },
    {
      "type": "update_familiarity",
      "data": {"module_key": "税务::发票接口", "member": "张三", "from": "不了解", "to": "了解"}
    },
    {
      "type": "create_assignment",
      "data": {"requirement_id": "REQ-001", "development_owner": "李祥", ...}
    }
  ],
  "reply": "完成 3 条需求解析、3 项分配、1 个新模块创建、2 项熟悉度更新"
}
```

用户确认后，执行 `pending_changes` 写入 MySQL。

## 7. API 设计

在现有 `api_service.py` 上新增：

```python
class WorkspaceService:
    # 新增：启动分析 pipeline
    def start_analysis_pipeline(self, workspace_id: str, user_message: str) -> dict[str, Any]
    
    # 新增：获取当前 pipeline 状态
    def get_pipeline_state(self, workspace_id: str) -> dict[str, Any]
    
    # 新增：确认当前步骤
    def confirm_pipeline_step(self, workspace_id: str, step: str, action: str, modifications: dict | None = None, feedback: str | None = None) -> dict[str, Any]
```

**action 值**：
- `"confirm"` — 确认，进入下一步
- `"modify"` — 手动修改，传入 `modifications`
- `"reanalyze"` — 重新分析，传入 `feedback`
- `"skip"` — 跳过当前步骤
- `"execute"` — 第5步专用，执行 pending_changes

## 8. 前端交互设计

在现有 `/workspaces/{id}/intake` 页面基础上，新增一个**分析进度面板**：

```
┌──────────────────────────────────────────────────────────┐
│  分析进度                                                  │
│                                                          │
│  [✅] 1. 需求解析  (已完成)                                │
│  [▶️] 2. 人员匹配  (当前步骤)                              │
│  [⬜] 3. 模块提炼                                           │
│  [⬜] 4. 梯队分析                                           │
│  [⬜] 5. 知识更新                                           │
│                                                          │
├──────────────────────────────────────────────────────────┤
│  当前步骤：人员匹配                                        │
│                                                          │
│  REQ-001: 开发→李祥 | 测试→张三 | B角→王海林                │
│         理由: 熟悉税务模块, 当前负载 0.3                    │
│  REQ-002: 开发→王海林 | 测试→李祥                           │
│         理由: 熟悉接口, 有同类经验                          │
│                                                          │
│  [✅ 确认]  [✏️ 修改]  [🔄 重新分析]  [⏭️ 跳过]              │
└──────────────────────────────────────────────────────────┘
```

## 9. 文件结构变更

在现有代码基础上：

```
pm_agent/
├── agents/                          # 新增目录
│   ├── __init__.py
│   ├── orchestrator.py              # Orchestrator Agent
│   ├── requirement_parser.py        # 需求解析 Agent
│   ├── personnel_matcher.py         # 人员匹配 Agent
│   ├── module_extractor.py          # 模块提炼 Agent
│   ├── team_analyzer.py             # 梯队分析 Agent
│   └── knowledge_updater.py         # 知识更新 Agent
├── pipeline.py                      # PipelineContext + 流程管理
├── llm_client.py                    # 已有，复用
├── models.py                        # 已有，可能扩展
├── api_service.py                   # 新增 pipeline 相关 API 方法
└── agent_prompt.py                  # 新增各子 Agent 的 prompt
```

## 10. 与现有代码的关系

- **保留**：`LlmClient`、`models.py` 中的数据类、Repository 层、`api.py` 路由
- **改造**：`ProjectManagerAgent` 变为 Orchestrator 的封装，原有方法（如 `parse_requirements_with_llm`）迁移到对应子 Agent
- **新增**：5 个子 Agent 类、PipelineContext、新 API 方法
- **兼容**：原有 API 路由不变，新增 `/api/workspaces/{id}/pipeline/*` 路由

## 12. 风险与缓解

| 风险 | 缓解 |
|------|------|
| LLM 响应不稳定 | 多模型自动降级（Tier-1 → Tier-2 → Tier-3），每步允许"重新分析"，用户可手动修改覆盖 |
| 串行流程延迟大 | 每步独立，前端展示进度条，用户可随时暂停/跳过 |
| 知识库自治误判 | 所有变更标记 pending，必须人确认才写入 |
| 前端 token 消耗 | 全部使用 LLM，需关注调用成本，降级策略可降低主模型失败后的重试开销 |
| 主模型持续不可用 | 降级日志记录 + 告警，管理员可通过配置切换默认主模型 |
