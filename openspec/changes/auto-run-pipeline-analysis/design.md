## Context

当前 Java 后端的 Pipeline API 已支持 `start/state/confirm` 三个接口，但执行模型是“启动首步 + 每步等待人工确认”。前端也按该模型渲染确认按钮。为降低操作成本，这次改动需要同时调整后端状态机、接口契约、前端 store 轮询和面板展示，因此属于跨后端与前端的协同改造。

## Goals / Non-Goals

**Goals:**
- 默认使用自动模式启动 Pipeline，并在同一 workspace 内保证单次只存在一个活跃 run
- 自动模式在后台顺序执行 5 个节点，并在命中待确认结果或失败时稳定暂停
- 前端能够区分 `queued/running/awaiting_confirmation/completed/failed`，自动轮询并在暂停时恢复人工操作按钮
- 保留显式手动模式，避免破坏已有逐步确认调试场景

**Non-Goals:**
- 不引入外部任务队列或分布式调度系统
- 不改变 5 个 Pipeline 节点的业务语义和 LLM prompt 内容
- 不改造推荐页、确认页等非 Intake Pipeline 入口

## Decisions

- 使用进程内 `ExecutorService` 作为 v1 runner，而不是引入异步基础设施。理由是当前仓库没有现成任务框架，单机内执行可以最小改动落地。
- 为 Pipeline 状态新增 `execution_mode`、`run_status`、`awaiting_confirmation`、`blocking_reason`、`run_id`、`last_heartbeat_at`。理由是前端需要可区分的运行态，后端也需要判断活跃 run 和超时失败。
- 自动模式的暂停条件采用显式规则：`requirement_parsing` 中只要出现 `match_status=needs_confirmation` 就暂停；其他步骤仅在结果显式给出 `requires_confirmation=true` 时暂停。理由是这与当前已实现数据结构兼容，且不会引入新的置信度阈值策略。
- 前端在自动模式运行中轮询 `/pipeline/state`，而不是等待服务端推送。理由是现有架构仅有 REST API，无 SSE/WebSocket 基础设施。
- 手动模式继续复用原 `confirm/modify/reanalyze/skip` 语义；自动模式暂停后也复用同一接口，并在处理后自动续跑。理由是避免新增额外恢复接口。

## Risks / Trade-offs

- [进程内 runner 在服务重启时丢失执行上下文] → 通过持久化状态和心跳超时把卡住的 run 标记为 `failed`，由用户重新启动
- [自动模式单 workspace 并发启动导致状态竞争] → 使用 workspace 级锁和活跃 run 判断拒绝重复启动
- [前端轮询增加请求频率] → 仅在 `auto + queued/running` 状态轮询，进入暂停、完成或失败即停止
- [暂停规则过宽或过窄影响体验] → v1 仅对显式待确认信号暂停，后续再根据线上数据细化
