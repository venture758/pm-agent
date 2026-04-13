## Why

当前确认分配后会继续产出平台同步相关数据（stories/tasks），这与“仅做内部确认留痕”的使用场景不一致，也增加了无效数据和后续同步成本。需要将确认结果从“平台落地链路”解耦，改为只做内部记录。

## What Changes

- 调整确认分配后的行为：不再生成平台同步模块所需的 stories/tasks 数据。
- 新增确认记录持久化能力：将每次确认结果写入独立记录表，用于查询与审计。
- 保留确认 API 主流程与页面交互入口，但返回信息改为“已记录确认结果”。
- **BREAKING**: 依赖确认后 `handoff` 预览数据的流程将不再自动获得故事/任务预览。

## Capabilities

### New Capabilities
- `internal-confirmation-records`: 确认分配后仅记录内部确认结果，不触发平台同步数据生成。

### Modified Capabilities
- 无（当前 `openspec/specs/` 下无已发布能力需要做 delta）。

## Impact

- **后端服务**: `pm_agent/api_service.py` 的 `confirm_assignments` 流程需要改写，去掉 `generate_platform_handoff` 依赖。
- **数据存储**: 需要新增确认记录表（MySQL DDL + migration + SQLite schema）及对应 store 方法。
- **接口返回**: `handoff` 字段可能为空或仅保留历史结构壳，需要保持兼容但不再新增平台数据。
- **测试**: 需补充“确认后写入记录表、且不生成 stories/tasks”的回归测试。
