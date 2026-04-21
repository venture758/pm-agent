# 需求解析 RAG 优化设计

## 概述

当前需求解析（`ChatService` → `LlmService.parseRequirements`）将全量模块候选（≤80）、task 信号（≤120）、story 信号（≤120）组装成 30-80KB 的 JSON 上下文一次性发送给 LLM，存在以下问题：

1. **数据量过大** — 大量无关模块和历史信号成为噪音
2. **有效信号被淹没** — 关键匹配线索被冗余信息稀释，导致 LLM 模块归属不准
3. **响应延迟** — 大上下文导致 LLM 处理慢

本设计引入混合检索（BM25 + Embedding），将上下文压缩到 3-5KB，提升 LLM 解析准确率和速度。

## 架构设计

### 当前流程

```
用户消息 → 查询全量模块(≤80) + 全量task(≤120) + 全量story(≤120)
         → 组装大JSON上下文(30-80KB)
         → 单次LLM调用，输出解析结果
```

### 新流程

```
用户消息 → BM25倒排检索(Top-20) → Embedding精排(Top-8)
         → 关联精简task/story signal
         → 组装上下文(3-5KB)
         → LLM调用，精准匹配
```

## 组件设计

### 1. ModuleIndexer（新建）

**职责**：维护模块倒排索引，支持 BM25 检索

**存储**：内存，无外部依赖

**索引结构**：
- 倒排表：`Map<String, List<ModuleRef>>` — 分词 → 模块引用列表
- 正排表：`Map<String, ModuleDoc>` — moduleKey → 模块完整信息

**索引 Key 来源**：
- 模块名分词（大模块、功能模块）
- 模块关键词（`keywords` 字段）
- 所属人员名（`primaryOwner`、`backupOwners`）
- 熟练成员名（`familiarMembersJson`）

**分词策略**：
- 中文按字符 n-gram（2-3）+ 英文按空格/标点分词
- 去停用词（"的"、"管理"、"系统"等通用词降低权重）

**BM25 打分**：
- 对用户消息分词后，对每个模块计算 BM25 分数
- 返回 Top-20（`bm25TopN` 配置）

**数据加载**：
- 启动时通过 `ModuleEntryMapper` 加载全量模块
- 模块变更时支持重建（后续通过事件触发）

### 2. EmbeddingClient（新建）

**职责**：调用 Embedding API 获取文本向量，计算相似度

**端点**：复用 `OpenAiCompatibleLlmClient` 的 baseUrl，调用 `/embeddings` 端点

**输入**：
- query: 用户消息文本
- candidates: Top-20 模块的聚合文本（模块名 + 关键词 + 关联task名 拼接）

**输出**：
- 每个候选模块与用户消息的余弦相似度分数
- 按相似度降序排序

**失败处理**：
- Embedding API 调用失败 → 降级为纯 BM25 Top-5 返回
- 不阻断整体流程

### 3. HybridRetriever（新建）

**职责**：编排 BM25 + Embedding 两阶段混合检索

**流程**：
1. BM25 召回 Top-20 模块
2. 调用 EmbeddingClient 对 Top-20 精排，取 Top-8
3. 从 Top-8 模块反向关联 workspace 中的 task/story
4. 只取与 Top-8 模块相关的 task/story 作为 signal

**输出结构**：
```json
{
  "module_candidates": [
    {"big_module": "xx", "function_module": "xx", "keywords": [...], "retrieval_score": 0.85}
  ],
  "task_name_signals": ["关联的task名1", "关联的task名2"],
  "story_name_signals": ["关联的story名1", "关联的story名2"]
}
```

### 4. RequirementParseContextBuilder（修改）

**新增方法**：`buildByRetrieval(String message, String workspaceId)`

- 内部委托 `HybridRetriever` 执行检索
- 返回精简版上下文
- 保留原 `build()` 方法不动，作为兼容性兜底

### 5. ChatService（修改）

**修改点**：`send()` 方法中
- 调用 `buildByRetrieval(message, workspaceId)` 替换 `build()`
- 其余逻辑（消息持久化、LLM 调用、需求入库）完全不变

### 6. LlmService.parseRequirements（优化）

**Prompt 优化**：增加更明确的模块归属规则说明，减少幻觉

**payload 优化**：增加 `response_format: {"type": "json_object"}`（API 支持时）

## 数据量对比

| 字段 | 当前 | 优化后 | 压缩比 |
|------|------|--------|--------|
| module_candidates | ≤80个，含关键词 | Top-8，含关键词 | ~10x |
| task_name_signals | ≤120条 | 仅Top-8关联模块的task（5-15条） | ~8x |
| story_name_signals | ≤120条 | 仅Top-8关联模块的story（5-15条） | ~8x |
| 总上下文 | 30-80KB | 3-5KB | ~10x |

## 兜底策略

| 场景 | 处理方式 |
|------|----------|
| Embedding 调用失败 | 降级为 BM25 Top-5 |
| BM25 无匹配结果 | 返回全量 Top-10 默认候选 |
| Workspace 无数据 | 不传 module_candidates，LLM 自由解析，全部标记 needs_confirmation |
| LLM 返回解析失败 | 保持现有 defaultRequirement 逻辑 |

## 配置项

在 `LlmProviderProperties` 新增：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| embeddingModel | 空 | Embedding 模型名，为空时跳过精排 |
| retrievalTopK | 8 | 最终返回模块数量 |
| bm25TopN | 20 | BM25 召回数量 |
| embeddingEnabled | true | Embedding 开关，可随时关闭回退纯 BM25 |

## 不改动部分

- `LlmService.normalizeRequirementItem` — 后处理逻辑不变
- `PipelineService` — Pipeline 流程独立，不在此变更范围
- `ChatSessionMapper` / `ChatMessageMapper` — 持久化层不变
- 前端 UI — 返回结构完全一致，无需前端改动
