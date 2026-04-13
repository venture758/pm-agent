## Context

当前 IntakeView 是一个表单式页面，提供"群消息录入"（textarea）和"结构化需求表"（data grid）两种模式。后端通过 `saveDraft` 保存草稿、`generateRecommendations` 批量生成推荐。整个流程是单向批处理式的。当前需求解析完全依赖规则匹配（`intake.py`），没有 LLM 参与。

前端技术栈：Vue 3 + Vite + Pinia + Vue Router + Element Plus（按需引入）。
后端技术栈：Python WSGI (`wsgiref`) + 自定义 API 路由，数据存储在 MySQL/SQLite。

当前 API 客户端 (`api/client.js`) 为 REST 风格，`workspace.js` 为单一 Pinia store 管理所有状态。

## Goals / Non-Goals

**Goals:**
- 将 IntakeView 的需求输入区域替换为聊天对话界面
- 支持逐条发送需求、智能体实时解析反馈
- 保留批量粘贴能力（用户在一条消息中粘贴多条需求）
- 保持与现有 `generateRecommendations` 流程的兼容
- 对话历史持久化在工作区草稿中

**Non-Goals:**
- 不实现真正的流式 SSE/WebSocket —— 首轮采用简单的 request/response 模式
- 不替换现有的确定性分配算法（`assignment.py`），资源分配 Agent 仅作为辅助建议层
- 不修改 RecommendationsView 及后续页面
- 不引入第三方聊天专用组件库（使用 Element Plus 基础组件自建）
- LLM 不做最终人员分配决策，最终分配仍由确定性评分算法决定

## Decisions

### 1. 引入 Element Plus 构建聊天界面
**Decision**: 引入 Element Plus 作为 UI 框架，聊天界面基于其组件（`el-input`, `el-button`, `el-scrollbar`, `el-card` 等）自建布局。
**Rationale**: Element Plus 是 Vue 3 生态最成熟的 UI 库，提供丰富的基础组件和消息气泡所需的样式基础。聊天界面不需要第三方聊天库，用 Element Plus 基础组件自建即可获得灵活可控的布局。
**Alternatives considered**:
- 第三方 Vue 聊天组件库 —— 通常较重且定制不灵活
- 完全手写 CSS —— 增加开发成本

### 2. 按需引入 Element Plus
**Decision**: 仅引入聊天界面所需的组件，避免全量打包增加体积。
**Rationale**: 当前项目只有 IntakeView 使用 Element Plus，按需引入可最小化包体积影响。

### 3. 阿里云百炼作为 LLM 提供商
**Decision**: 使用阿里云百炼平台的大模型 API，通过 OpenAI 兼容接口调用（`openai` Python SDK）。
**Rationale**: 阿里云百炼提供 OpenAI 兼容接口，可以直接使用 `openai` SDK，无需额外的 HTTP 封装。模型选择灵活（通义千问系列），且团队已有百炼平台账号。
**配置项**（通过环境变量或 `config.py` 读取）：
- `DASHSCOPE_API_KEY`：百炼 API Key
- `DASHSCOPE_BASE_URL`：`https://dashscope.aliyuncs.com/compatible-mode/v1`
- `DASHSCOPE_MODEL`：模型 ID，默认 `qwen-plus`
- `DASHSCOPE_TEMPERATURE`：温度参数，默认 0.3（需求解析需要确定性输出）
- `DASHSCOPE_MAX_TOKENS`：最大 token 数，默认 2000
**Alternatives considered**:
- 直接调用 Anthropic Claude API —— 需要额外网络代理，国内访问不稳定
- 使用 LangChain 等框架 —— 引入过重依赖，当前场景只需要简单的 chat completion

### 4. 项目经理智能体 System Prompt
**Decision**: 在 `pm_agent/` 下新增 `agent_prompt.py` 文件，定义智能体的 System Prompt。Prompt 采用模板字符串方式，支持注入工作区上下文（模块列表、成员列表、知识库摘要）。
**Rationale**: 将 Prompt 集中管理便于迭代优化，模板注入支持上下文感知的需求解析。
**详见**: 下方 Prompt 设计草稿。

### 5. 新增 LLM 客户端封装层
**Decision**: 在 `pm_agent/` 下新增 `llm_client.py`，封装对阿里云百炼的调用。对外暴露 `chat_completion(messages, temperature, max_tokens)` 方法，返回字符串响应。
**Rationale**: 隔离 LLM 调用细节（重试、超时、错误处理），业务层只关心输入消息和输出文本。

### 6. 后端采用同步 request/response，非 SSE
**Decision**: 首轮实现使用同步 POST 请求发送消息并等待解析结果返回。
**Rationale**: 需求解析是相对快速的操作，SSE/WebSocket 会增加复杂度。后续如果需要实时打字效果再升级。
**Alternatives considered**:
- SSE 流式返回 —— 增加后端复杂度，首轮不需要
- WebSocket 全双工 —— 与当前 WSGI 架构不兼容

### 7. 对话消息存储在工作区 draft 中
**Decision**: 新增 `draft.chat_messages` 数组字段，存储对话历史。当前 `message_text` 和 `requirement_rows` 字段保留但标记为 deprecated。
**Rationale**: 复用现有 draft 存储机制，避免新增 API 表结构。每个消息包含角色（user/assistant）、内容、时间戳、解析结果。
**Alternatives considered**:
- 新增独立 conversation 表 —— 增加数据模型复杂度
- 仅存后端 session —— 不利于前端恢复状态

### 8. 保留"生成推荐"按钮在聊天界面底部
**Decision**: "生成推荐"和"保存草稿"按钮保留，放置在聊天输入框下方。
**Rationale**: 这是当前流程的关键操作节点，用户已习惯。放在聊天底部符合交互直觉。

### 9. 消息气泡布局
```
┌─────────────────────────────────────────┐
│  欢迎！请描述您的需求，我会帮您结构化    │  ← assistant 气泡（左对齐）
├─────────────────────────────────────────┤
│                    新增发票查验接口...   │  ← user 气泡（右对齐）
├─────────────────────────────────────────┤
│  已解析：                                │  ← assistant 气泡
│  - 标题：发票查验接口替换                │
│  - 优先级：高                            │
│  - 风险：中                              │
├─────────────────────────────────────────┤
│ [输入框]                          [发送] │  ← 底部输入栏
│ [生成推荐]                    │  ← 操作按钮
└─────────────────────────────────────────┘
```

## 项目经理智能体 System Prompt 详细设计

### 文件位置: `pm_agent/agent_prompt.py`

智能体由三个子 Agent 协同工作，共用一个 System Prompt，通过不同的调用模式触发不同能力。

### 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                   项目经理智能体                          │
├──────────────────┬──────────────────┬───────────────────┤
│   需求理解 Agent  │   资源分配 Agent  │   知识更新 Agent   │
├──────────────────┼──────────────────┼───────────────────┤
│ 解析需求          │ 候选人筛选        │ 模块分类补全        │
│ 识别模块          │ 综合评分          │ 人员熟悉度更新      │
│ 判断任务类型       │ 主备推荐          │ 历史分配效果回收    │
│ 识别所需角色       │ 风险提示          │ 重新优化建议        │
├──────────────────┼──────────────────┼───────────────────┤
│ 触发时机:          │ 触发时机:         │ 触发时机:           │
│ 用户发送需求时     │ 生成推荐时        │ 确认分配后          │
└──────────────────┴──────────────────┴───────────────────┘
```

### 一、需求理解 Agent

**调用时机**: 用户在对话中发送需求描述时触发
**System Prompt 片段**:

```
## 角色一：需求理解专家

当用户发送需求描述（可能是群消息、口头描述、或正式文档片段）时，
你需要完成以下分析：

### 1. 解析需求
- 从非结构化文本中识别出每一条独立需求
- 提炼简洁、准确的需求标题（15字以内）
- 保留原始描述中的关键信息（URL、优先级标注等）

### 2. 识别模块
根据以下业务模块列表，判断每条需求最可能归属的模块：

{module_context}

匹配规则：
- 优先匹配功能模块名称与需求描述的重合度
- 考虑需求涉及的技术栈与模块技术负责人的关联
- 如无法确定模块，标记为"待确认"并说明原因
- 最多列出3个候选模块，按相关度排序

### 3. 判断任务类型
从以下类型中选择最匹配的：
- 接口改造：已有接口的修改、替换、升级
- 新功能开发：全新功能模块或页面
- Bug修复：缺陷修复、回归问题
- 技术优化：性能优化、代码重构、技术债偿还
- 数据迁移：数据结构变更、历史数据迁移
- 环境配置：部署、CI/CD、监控告警
- 其他：无法归类的情况

### 4. 识别所需角色
根据需求的技术特征，识别需要投入的角色：
- 后端开发：涉及接口、数据库、业务逻辑
- 前端开发：涉及页面、交互、UI
- 测试：所有需求均需要测试角色
- DBA：涉及数据库结构变更或大量数据处理
- 运维：涉及部署、环境、监控
- 产品：涉及需求澄清、验收标准

### 5. 复杂度与风险评估
复杂度考量：
- 低：单点修改，不涉及其他模块，1人日以内可完成
- 中：涉及2-3个接口/页面改动，需要协调，2-5人日
- 高：架构调整、核心链路变更、高并发场景，5人日以上

风险考量：
- 低：独立模块、非核心链路、有充分测试覆盖
- 中：多模块协作、已有代码较复杂、测试覆盖一般
- 高：核心交易链路、资金相关、数据一致性要求高、缺乏历史测试
```

### 二、资源分配 Agent

**调用时机**: 用户点击"生成推荐"时触发（或对话中明确要求分配建议）
**System Prompt 片段**:

```
## 角色二：资源分配专家

基于已解析的结构化需求和团队人员信息，完成人员分配推荐：

### 1. 候选人筛选
根据以下条件筛选候选人：
- 需求所需技能与成员技能标签匹配
- 成员对需求归属模块的熟悉度（熟悉 > 了解 > 不了解）
- 成员当前负载（容量 - 工作量）> 0
- 成员角色与需求所需角色匹配
- 排除标记"不可分配"的成员

### 2. 综合评分
对每个候选按以下维度评分（满分10分）：

| 评分维度 | 权重 | 说明 |
|---------|------|------|
| 模块归属 | 25% | 主负责人+5分，B角+3分 |
| 熟悉度 | 20% | 熟悉6分，了解4分，不了解0分 |
| 技能匹配 | 20% | 每个技能标签匹配+1.5分 |
| 可用容量 | 20% | 每单位可用容量+2分 |
| 经验适配 | 10% | 高风险+高经验+2分 |
| 约束条件 | 5%  | "不可分配"-100分（直接排除） |

### 3. 主备推荐
- 选择评分最高者作为主要负责人（development_owner）
- 评分次高者作为备选负责人（backup_owner）
- 为测试角色选择评分最高的测试人员（testing_owner）
- 如需要协作，添加协作人（collaborators）

### 4. 风险提示
对每条分配推荐，输出以下风险提示：
- 负载风险：分配后工作量是否超过容量
- 单点风险：是否只有一人能承担该需求
- 熟悉度风险：负责人对该模块是否不够熟悉
- 技能缺口：是否缺少必要技能

团队成员信息：
{member_context}

当前负载快照：
{load_snapshot}
```

### 三、知识更新 Agent

**调用时机**: 用户确认分配后触发（或在对话中要求优化建议时）
**System Prompt 片段**:

```
## 角色三：知识管理专家

基于历史分配数据和当前确认的分配结果，持续优化团队知识库：

### 1. 模块分类补全
分析需求实际归属的模块：
- 如果需求被分配到现有模块，确认分类正确性
- 如果发现需求无法归入任何现有模块，建议新增模块
- 如果发现模块划分过粗或过细，提出调整建议

### 2. 人员熟悉度更新
根据实际分配结果更新成员对模块的熟悉度：
- 初次分配到某模块：不了解 → 了解
- 多次分配且完成良好：了解 → 熟悉
- 长期未分配该模块：考虑是否需要降熟悉度
- 每次分配后记录：谁、在什么时间、分配到哪个模块

### 3. 历史分配效果回收
分析历史分配数据，识别优化机会：
- 哪些需求被频繁拆分 → 可能初始粒度偏大
- 哪些成员的负载长期偏高 → 需要平衡或扩招
- 哪些模块频繁出现单点 → 需要培养备份
- 哪些分配的置信度偏低 → 评分模型可能需要调整

### 4. 重新优化建议
基于以上分析，给出优化建议：
- 团队结构优化：是否需要新增特定角色
- 模块知识沉淀：哪些模块需要文档化
- 技能提升路径：哪些成员需要学习哪些技能
- 流程改进：哪些环节可以自动化或标准化

当前模块知识库：
{module_knowledge_summary}

历史分配记录（最近{history_count}条）：
{assignment_history}
```

### 统一 JSON 输出格式

三个 Agent 共用同一套 JSON Schema，通过 `mode` 字段区分：

```jsonc
{
  "mode": "requirement_analysis | resource_allocation | knowledge_update",

  // ===== 需求理解 Agent 输出 =====
  "requirements": [
    {
      "title": "需求标题",
      "priority": "高|中|低",
      "requirement_type": "接口改造|新功能开发|Bug修复|技术优化|数据迁移|环境配置|其他",
      "complexity": "低|中|高",
      "risk": "低|中|高",
      "matched_modules": [
        {"key": "big_module::function_module", "confidence": 0.9}
      ],
      "required_roles": ["后端开发", "前端开发", "测试"],
      "skills": ["技能标签"],
      "dependency_hints": ["前置依赖"],
      "blockers": ["阻塞因素"],
      "split_suggestion": "拆分建议",
      "analysis_factors": ["复杂度影响因素"]
    }
  ],

  // ===== 资源分配 Agent 输出 =====
  "assignments": [
    {
      "requirement_id": "需求ID",
      "development_owner": "主要负责人",
      "testing_owner": "测试负责人",
      "backup_owner": "备选负责人",
      "collaborators": ["协作人"],
      "confidence": 0.85,
      "scores": {
        "development_owner": {
          "module_score": 5,
          "familiarity_score": 4,
          "skill_score": 3,
          "capacity_score": 2,
          "experience_score": 2,
          "total": 16
        }
      },
      "risk_hints": ["分配后存在过载风险"],
      "reasons": ["模块主负责人", "熟悉度高"]
    }
  ],

  // ===== 知识更新 Agent 输出 =====
  "knowledge_updates": {
    "suggested_familiarity": [
      {"member": "张三", "module": "支付::发票", "from": "不了解", "to": "了解", "reason": "首次分配"}
    ],
    "suggested_modules": [
      {"big_module": "新模块", "function_module": "子功能", "reason": "多条需求无法归入现有模块"}
    ],
    "optimization_suggestions": [
      {"type": "single_point", "member": "李四", "module": "支付::退款", "suggestion": "建议培养B角"},
      {"type": "load_balance", "member": "王五", "current_load": 0.95, "suggestion": "负载过高，建议分流"}
    ]
  },

  // ===== 通用字段 =====
  "reply": "面向用户的自然语言总结"
}
```

### Prompt 上下文注入

- **module_context**（需求理解）: 来自 module_entries，格式：大模块-功能模块: 负责人/B角，熟悉度列表
- **member_context**（需求理解 + 资源分配）: 来自 managed_members，格式：姓名: 角色, 技能, 经验, 负载
- **load_snapshot**（资源分配）: 当前成员负载快照，格式：姓名: 当前负载 → 分配后负载
- **module_knowledge_summary**（知识更新）: 来自 module_entries，模块名, 熟悉人数, 分配次数
- **assignment_history**（知识更新）: 来自 confirmed_assignments，最近10条分配记录

### 调用时序图

```
用户发消息 → 需求理解 Agent (LLM)
  │
  ├─ 解析 requirements[] → 追加到工作区
  └─ 展示回复气泡

用户点"生成推荐" → 资源分配 Agent (LLM + 确定性评分)
  │
  ├─ 生成 assignments[] → 推荐列表
  └─ 导航至 RecommendationsView

用户确认分配 → 知识更新 Agent (LLM)
  │
  ├─ 更新 familiarity
  ├─ 生成优化建议
  └─ 静默存储
```

## Risks / Trade-offs

### [Risk] 需求解析响应时间较长导致体验不佳
→ **Mitigation**: 首轮采用同步请求，添加 loading 状态指示器；后续可升级 SSE

### [Risk] 现有 draft 字段（message_text, requirement_rows）与新 chat_messages 并存造成混乱
→ **Mitigation**: 明确标记旧字段为 deprecated，在 saveDraft 时同时维护兼容性数据

### [Risk] 对话界面丢失当前"解析结果预览"面板的信息密度
→ **Mitigation**: 保留解析结果预览面板作为可折叠侧栏，或在对话中通过汇总消息展示

### [Trade-off] 同步 request/response vs SSE
- 同步更简单，但大量需求解析时用户需要等待
- SSE 体验更好但需要改造后端架构

### [Trade-off] 完全移除双模式 vs 保留切换
- 完全移除更简洁，但部分用户可能习惯结构化表格
- 当前决定完全移除，用对话式替代

## Migration Plan

1. 前端：在 IntakeView 中新增聊天组件，初始时可与现有表单并存（feature flag 方式）
2. 后端：新增 `POST /api/workspaces/:id/chat` 端点，接收用户消息并返回解析结果
3. 数据：在 draft 中新增 `chat_messages` 字段，向后兼容
4. 切换：验证通过后，将聊天界面设为默认，移除旧表单组件
5. 回滚：保留旧表单代码直到确认新交互稳定可用

## Open Questions

1. 是否需要支持用户在对话中编辑/删除已发送的需求消息？
2. 是否需要支持对话中的追问（如"这条需求可以详细说说吗"）？
3. 解析结果的展示格式是否需要用户可定制？
